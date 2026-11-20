# Live frame grab + saves binary sky-mask PNG
import base64
import io
import os
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from PIL import Image

router = APIRouter(tags=["masking"])
templates = Jinja2Templates(directory="frontend/templates")

DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
MASK_PATH = DATA_DIR / "config" / "sky_mask.png"

class MaskPayload(BaseModel):
    mask_data_url: str

@router.get("/mask", response_class=HTMLResponse)
def mask_editor_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="mask.html",
        context={"mask_exists": MASK_PATH.exists()},
    )

@router.post("/api/mask/save")
def save_sky_mask(payload: MaskPayload):
    MASK_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Strip "data:image/png;base64," header
    _, encoded = payload.mask_data_url.split(",", 1)
    raw_bytes = base64.b64decode(encoded)

    # Convert to strict 8-bit binary mask: 0 = masked out, 255 = active sky
    img = Image.open(io.BytesIO(raw_bytes)).convert("L")
    binary_mask = img.point(lambda p: 0 if p < 128 else 255, mode="L")
    binary_mask.save(MASK_PATH, format="PNG")

    return JSONResponse({"status": "saved", "path": str(MASK_PATH)})