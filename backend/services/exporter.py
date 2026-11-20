# Bundles FITS + SHA-256 proof + LaTeX/PDF into .zip
import io
import json
import os
from pathlib import Path
import zipfile
import yaml

DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
CORE_CONFIG_PATH = DATA_DIR / "config" / "core_config.yaml"
TEX_TEMPLATE_PATH = Path("presets/templates/report_template.tex")

def _load_core_config() -> dict:
    if CORE_CONFIG_PATH.exists():
        return yaml.safe_load(CORE_CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return {}

def _build_dev_fits_placeholder(event: dict, site: dict) -> bytes:
    """Minimal valid 2880-byte FITS primary header block for Dev Mode testing."""
    cards = [
        f"{'SIMPLE':8}= {'T':>20}",
        f"{'BITPIX':8}= {16:>20}",
        f"{'NAXIS':8}= {0:>20}",
        f"{'OBSERVER':8}= '{site.get('observer_id', 'DEV-NODE')}'",
        f"{'DATE-OBS':8}= '{event['timestamp_utc']}'",
        f"{'AXIOMID':8}= '{event['id']}'",
        f"{'SHA256':8}= '{event['signature_sha256'][:48]}'",
        "END",
    ]
    header = "".join(c.ljust(80)[:80] for c in cards).encode("ascii")
    padding = (2880 - (len(header) % 2880)) % 2880
    return header + (b" " * padding)

def build_event_zip(event: dict) -> io.BytesIO:
    cfg = _load_core_config()
    site = cfg.get("site", {})
    sensor = cfg.get("sensor", {})

    fits_path = Path(event["fits_path"])
    fits_filename = fits_path.name
    fits_bytes = (
        fits_path.read_bytes()
        if fits_path.exists()
        else _build_dev_fits_placeholder(event, site)
    )

    proof = {
        "event_id": event["id"],
        "timestamp_utc": event["timestamp_utc"],
        "attestation_valid": bool(event["attestation_valid"]),
        "signature_sha256": event["signature_sha256"],
        "fits_filename": fits_filename,
        "site": site,
    }

    tex = TEX_TEMPLATE_PATH.read_text(encoding="utf-8")
    replacements = {
        "{{ event_id }}": event["id"],
        "{{ observer_id }}": str(site.get("observer_id", "UNCONFIGURED")),
        "{{ timestamp_utc }}": event["timestamp_utc"],
        "{{ attestation_status }}": "VERIFIED (ATECC608A)" if event["attestation_valid"] else "UNVERIFIED",
        "{{ summary }}": event.get("summary", ""),
        "{{ latitude }}": str(site.get("latitude", "N/A")),
        "{{ longitude }}": str(site.get("longitude", "N/A")),
        "{{ elevation_m }}": str(site.get("elevation_m", "N/A")),
        "{{ exposure_ms }}": str(sensor.get("exposure_ms", "N/A")),
        "{{ gain }}": str(sensor.get("gain", "N/A")),
        "{{ fits_filename }}": fits_filename,
        "{{ signature_sha256 }}": event["signature_sha256"],
    }
    for k, v in replacements.items():
        tex = tex.replace(k, v)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(fits_filename, fits_bytes)
        zf.writestr("provenance_proof.json", json.dumps(proof, indent=2))
        zf.writestr(f"{event['id']}_report.tex", tex)
    buf.seek(0)
    return buf