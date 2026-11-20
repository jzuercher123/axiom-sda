from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from backend.routers.hardware import get_hardware_status
from backend.services.config_writer import list_presets, write_node_configs

router = APIRouter(tags=["wizard"])
templates = Jinja2Templates(directory="frontend/templates")

@router.get("/", response_class=HTMLResponse)
def wizard_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="wizard.html",
        context={
            "hw": get_hardware_status(),
            "presets": list_presets(),
            "saved": False,
        },
    )

@router.post("/wizard/save", response_class=HTMLResponse)
def save_wizard(
    request: Request,
    observer_id: str = Form(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    elevation_m: float = Form(0.0),
    profile_key: str = Form(...),
    spacetrack_user: str = Form(""),
):
    write_node_configs(
        observer_id=observer_id,
        latitude=latitude,
        longitude=longitude,
        elevation_m=elevation_m,
        profile_key=profile_key,
        spacetrack_user=spacetrack_user,
    )
    return templates.TemplateResponse(
        request=request,
        name="wizard.html",
        context={
            "hw": get_hardware_status(),
            "presets": list_presets(),
            "saved": True,
        },
    )