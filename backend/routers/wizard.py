import json
import os
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from backend.routers.hardware import get_hardware_status
from backend.services.config_writer import list_presets, write_node_configs


class WizardConfigState(BaseModel):
    observer_id: str = Field(default="OBS-IL-01", min_length=1)
    latitude: float = Field(default=40.4842)
    longitude: float = Field(default=-88.9937)
    elevation_m: float = Field(default=250.0)
    profile_key: str = Field(default="dark_sky")
    spacetrack_user: str = Field(default="")
    data_source: Literal["synthetic", "replay", "live"] = Field(default="synthetic")
    replay_file_path: str = Field(default="")


def _get_data_dir() -> Path:
    base = Path(os.getenv("AXIOM_DATA_DIR", "data"))
    (base / "config").mkdir(parents=True, exist_ok=True)
    return base


def _save_wizard_state(state: WizardConfigState) -> Path:
    cfg_path = _get_data_dir() / "config" / "node_config.json"
    cfg_path.write_text(state.model_dump_json(indent=2), encoding="utf-8")
    return cfg_path


def _load_wizard_state() -> WizardConfigState:
    cfg_path = _get_data_dir() / "config" / "node_config.json"
    if not cfg_path.exists():
        return WizardConfigState()
    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        return WizardConfigState(**data)
    except Exception:
        return WizardConfigState()


router = APIRouter(tags=["wizard"])
templates = Jinja2Templates(directory="frontend/templates")


@router.get("/", response_class=HTMLResponse)
def wizard_page(request: Request):
    state = _load_wizard_state()
    return templates.TemplateResponse(
        request=request,
        name="wizard.html",
        context={
            "hw": get_hardware_status(),
            "presets": list_presets(),
            "config": state,
            "saved": False,
        },
    )


@router.post("/wizard/save")
def save_wizard(
    request: Request,
    observer_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    elevation_m: float = Form(250.0),
    profile_key: str = Form(...),
    spacetrack_user: str = Form(""),
    data_source: Literal["synthetic", "replay", "live"] = Form("synthetic"),
    replay_file_path: str = Form(""),
):
    write_node_configs(
        observer_id=observer_id,
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        profile_key=profile_key,
        spacetrack_user=spacetrack_user,
    )

    state = WizardConfigState(
        observer_id=observer_id.strip() or "OBS-IL-01",
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        profile_key=profile_key,
        spacetrack_user=spacetrack_user.strip(),
        data_source=data_source,
        replay_file_path=replay_file_path.strip(),
    )
    _save_wizard_state(state)

    return RedirectResponse(url="/dashboard", status_code=303)