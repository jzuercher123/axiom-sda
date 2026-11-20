# Event feed, attestation verification, and ZMQ listener
from datetime import datetime, timezone
import hashlib
import uuid
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from backend.db.database import get_conn, init_db
from backend.routers.hardware import get_hardware_status
from backend.services.tle_sync import get_catalog_status
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from backend.services.exporter import build_event_zip

router = APIRouter(tags=["events"])
templates = Jinja2Templates(directory="frontend/templates")

init_db()

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY created_at DESC LIMIT 50"
        ).fetchall()

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "hw": get_hardware_status(),
            "tle": get_catalog_status(),
            "events": [dict(r) for r in rows],
        },
    )

@router.post("/api/events/simulate")
def simulate_leo_event():
    """Dev-mode helper: inserts a mock hardware-attested LEO detection."""
    event_id = f"EVT-{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    summary = (
        "Uncataloged LEO object detected traversing NW->SE at 0.84 deg/s "
        "(est. altitude 540 km, no TLE match within 0.5 deg)."
    )
    sig = hashlib.sha256(f"{event_id}:{ts}".encode()).hexdigest()

    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO events (id, timestamp_utc, summary, fits_path, signature_sha256, attestation_valid)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_id, ts, summary, f"data/events/{event_id}.fits", sig, 1),
        )
    return RedirectResponse(url="/dashboard", status_code=303)


@router.get("/api/events/{event_id}/export")
def export_event_bundle(event_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Event not found")

    zip_buf = build_event_zip(dict(row))
    headers = {"Content-Disposition": f'attachment; filename="{event_id}_academic_bundle.zip"'}
    return StreamingResponse(zip_buf, media_type="application/zip", headers=headers)