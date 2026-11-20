# Scheduled Space-Track / CelesTrak TLE fetcher
from datetime import datetime, timezone
import os
from pathlib import Path
import httpx

DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
CATALOG_DIR = DATA_DIR / "catalog"
TLE_PATH = CATALOG_DIR / "leo.tle"

# Public CelesTrak active satellites GP data in 3-line TLE format
CELESTRAK_ACTIVE_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=tle"

def sync_tle_catalog(timeout_s: float = 20.0) -> dict:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)

    with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
        resp = client.get(CELESTRAK_ACTIVE_URL)
        resp.raise_for_status()
        tle_text = resp.text.strip()

    TLE_PATH.write_text(tle_text + "\n", encoding="utf-8", newline="\n")

    # Standard 3-line TLE: Name + Line 1 + Line 2
    lines = [ln for ln in tle_text.splitlines() if ln.strip()]
    object_count = len(lines) // 3

    return {
        "status": "synced",
        "source": "celestrak",
        "object_count": object_count,
        "path": str(TLE_PATH),
        "synced_at_utc": datetime.now(timezone.utc).isoformat(),
    }

def get_catalog_status() -> dict:
    if not TLE_PATH.exists():
        return {"synced": False, "object_count": 0, "last_modified_utc": None}

    lines = [ln for ln in TLE_PATH.read_text(encoding="utf-8").splitlines() if ln.strip()]
    mtime = datetime.fromtimestamp(TLE_PATH.stat().st_mtime, tz=timezone.utc).isoformat()
    return {
        "synced": True,
        "object_count": len(lines) // 3,
        "last_modified_utc": mtime,
    }