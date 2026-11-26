from dataclasses import dataclass
import logging
from logging.handlers import RotatingFileHandler
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

from desktop.paths import get_sda_root


@dataclass
class ManagedService:
    name: str
    cmd: list[str]
    cwd: pathlib.Path
    env: dict[str, str]
    proc: subprocess.Popen | None = None
    log_file: pathlib.Path | None = None


class ProcessManager:
    def __init__(self, data_dir: pathlib.Path, workspace_root: pathlib.Path):
        self.data_dir = data_dir
        self.workspace_root = workspace_root
        self.sda_root = get_sda_root()
        self.log_dir = data_dir / "logs"
        self.services: list[ManagedService] = []
        self._handles: list[object] = []

        self.logger = logging.getLogger("axiom.desktop.proc")
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = RotatingFileHandler(
                self.log_dir / "desktop.log",
                maxBytes=2 * 1024 * 1024,
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self.logger.addHandler(handler)

    def _build_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env.setdefault("ZMQ_CORE_ENDPOINT", "tcp://127.0.0.1:5555")
        env.setdefault("ZMQ_UI_PUB_ENDPOINT", "tcp://127.0.0.1:5556")
        env.setdefault("ZMQ_AGENT_SUB_ENDPOINT", "tcp://127.0.0.1:5556")
        env.setdefault("OLLAMA_HOST", "http://127.0.0.1:11434")
        env["AXIOM_DATA_DIR"] = str(self.data_dir)
        env["PYTHONUNBUFFERED"] = "1"
        return env

    def _discover_services(self) -> list[ManagedService]:
        env = self._build_env()
        python_exe = sys.executable

        agents_dir = self.workspace_root / "axiom_agents"
        core_bin = self.workspace_root / "axiom_kernel" / "build" / (
            "sda_node.exe" if os.name == "nt" else "sda_node"
        )

        discovered: list[ManagedService] = []

        # 1. Core C++ sensor/provenance node (optional if running replay/external source)
        if core_bin.exists():
            discovered.append(
                ManagedService(
                    name="axiom-core",
                    cmd=[str(core_bin)],
                    cwd=core_bin.parent,
                    env=env,
                    log_file=self.log_dir / "axiom-core.log",
                )
            )
        else:
            self.logger.info("sda_node binary not found at %s; skipping core process.", core_bin)

        # 2. 4-Layer Python Agent Fleet
        run_fleet = agents_dir / "run_fleet.py"
        if run_fleet.exists():
            agent_env = env.copy()
            agent_env["PYTHONPATH"] = str(agents_dir)
            discovered.append(
                ManagedService(
                    name="axiom-agents",
                    cmd=[python_exe, str(run_fleet)],
                    cwd=agents_dir,
                    env=agent_env,
                    log_file=self.log_dir / "axiom-agents.log",
                )
            )

        # 3. FastAPI / Uvicorn Dashboard Backend
        if (self.sda_root / "backend" / "main.py").exists():
            sda_env = env.copy()
            sda_env["PYTHONPATH"] = str(self.sda_root)
            discovered.append(
                ManagedService(
                    name="axiom-sda",
                    cmd=[
                        python_exe,
                        "-m",
                        "uvicorn",
                        "backend.main:app",
                        "--host",
                        "127.0.0.1",
                        "--port",
                        "8000",
                    ],
                    cwd=self.sda_root,
                    env=sda_env,
                    log_file=self.log_dir / "axiom-sda.log",
                )
            )

        return discovered

    def start_all(self) -> None:
        self.stop_all()
        self.services = self._discover_services()
        flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0

        for svc in self.services:
            assert svc.log_file is not None
            fh = open(svc.log_file, "a", encoding="utf-8", buffering=1)
            self._handles.append(fh)
            svc.proc = subprocess.Popen(
                svc.cmd,
                cwd=str(svc.cwd),
                env=svc.env,
                stdout=fh,
                stderr=subprocess.STDOUT,
                creationflags=flags,
            )
            self.logger.info("Started %s (PID %s)", svc.name, svc.proc.pid)

    def stop_all(self) -> None:
        for svc in reversed(self.services):
            if svc.proc and svc.proc.poll() is None:
                self.logger.info("Stopping %s (PID %s)", svc.name, svc.proc.pid)
                svc.proc.terminate()
                try:
                    svc.proc.wait(timeout=4)
                except subprocess.TimeoutExpired:
                    svc.proc.kill()
            svc.proc = None
        self.services = []

        for fh in self._handles:
            try:
                fh.close()
            except Exception:
                pass
        self._handles = []

    def wait_for_http(self, url: str = "http://127.0.0.1:8000", timeout_s: float = 20.0) -> bool:
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=1.0) as resp:
                    if resp.status < 500:
                        return True
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.25)
        return False

    def status_snapshot(self) -> dict[str, bool]:
        return {
            svc.name: (svc.proc is not None and svc.proc.poll() is None)
            for svc in self.services
        }