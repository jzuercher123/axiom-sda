import json
import os
from pathlib import Path
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/diagnostics", tags=["diagnostics"])


def _data_dir() -> Path:
    return Path(os.getenv("AXIOM_DATA_DIR", "data"))


def _tail_lines(path: Path, max_lines: int = 150) -> list[str]:
    if not path.exists():
        return []
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return lines[-max_lines:]


@router.get("/summary")
def diagnostics_summary(lines: int = Query(default=150, ge=10, le=1000)):
    data_dir = _data_dir()
    log_dir = data_dir / "logs"
    cfg_path = data_dir / "config" / "node_config.json"

    config_data = {}
    if cfg_path.exists():
        try:
            config_data = json.loads(cfg_path.read_text(encoding="utf-8"))
        except Exception:
            config_data = {"_error": "Failed to parse node_config.json"}

    log_names = ["desktop.log", "axiom-core.log", "axiom-agents.log", "axiom-sda.log"]
    logs = {name: _tail_lines(log_dir / name, lines) for name in log_names}

    return {
        "data_dir": str(data_dir),
        "log_dir": str(log_dir),
        "config": config_data,
        "logs": logs,
    }