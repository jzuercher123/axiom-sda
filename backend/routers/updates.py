# Safe pinned release pull + health-check rollback
import platform
import shutil
import subprocess
from pathlib import Path
from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["updates"])
templates = Jinja2Templates(directory="frontend/templates")

VERSIONS_FILE = Path("versions.env")
BACKUP_FILE = Path("versions.env.bak")
ROLLBACK_SCRIPT = Path("scripts/rollback.sh")


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    data = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            data[k.strip()] = v.strip()
    return data


def _write_env_file(path: Path, data: dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in data.items()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


@router.get("/updates", response_class=HTMLResponse)
def updates_page(request: Request, msg: str = ""):
    return templates.TemplateResponse(
        request=request,
        name="updates.html",
        context={
            "versions": _parse_env_file(VERSIONS_FILE),
            "has_backup": BACKUP_FILE.exists(),
            "platform": platform.system(),
            "msg": msg,
        },
    )


@router.post("/api/updates/apply")
def apply_update(
    core_tag: str = Form(...),
    agents_tag: str = Form(...),
):
    current = _parse_env_file(VERSIONS_FILE)
    if VERSIONS_FILE.exists():
        shutil.copy2(VERSIONS_FILE, BACKUP_FILE)

    current["AXIOM_CORE_TAG"] = core_tag.strip()
    current["AXIOM_AGENTS_TAG"] = agents_tag.strip()
    _write_env_file(VERSIONS_FILE, current)

    if platform.system() == "Linux":
        result = subprocess.run(
            ["docker", "compose", "--env-file", str(VERSIONS_FILE), "up", "-d"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            subprocess.run(["bash", str(ROLLBACK_SCRIPT)], check=False)
            return RedirectResponse(
                url="/updates?msg=Update+failed.+Automatically+rolled+back+to+previous+release.",
                status_code=303,
            )
        return RedirectResponse(
            url="/updates?msg=Updated+pinned+tags+and+restarted+containers.",
            status_code=303,
        )

    return RedirectResponse(
        url="/updates?msg=Updated+versions.env+(Dev+Mode:+container+restart+skipped).",
        status_code=303,
    )


@router.post("/api/updates/rollback")
def trigger_rollback():
    if not BACKUP_FILE.exists():
        return RedirectResponse(
            url="/updates?msg=No+backup+versions.env.bak+found.",
            status_code=303,
        )

    if platform.system() == "Linux" and ROLLBACK_SCRIPT.exists():
        subprocess.run(["bash", str(ROLLBACK_SCRIPT)], check=False)
    else:
        shutil.copy2(BACKUP_FILE, VERSIONS_FILE)

    return RedirectResponse(
        url="/updates?msg=Rolled+back+to+previous+pinned+release.",
        status_code=303,
    )