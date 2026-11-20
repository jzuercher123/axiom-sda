# Camera, I2C ATECC608A, CPU temp, and disk health checks
from pathlib import Path
import platform
import shutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/hardware", tags=["hardware"])

def _read_pi_cpu_temp() -> float | None:
    thermal_file = Path("/sys/class/thermal/thermal_zone0/temp")
    if thermal_file.exists():
        return round(int(thermal_file.read_text().strip()) / 1000.0, 1)
    return None

@router.get("/status")
def get_hardware_status():
    is_linux = platform.system() == "Linux"
    disk = shutil.disk_usage("/")

    return {
        "platform": platform.system(),
        "camera_detected": Path("/dev/video0").exists() if is_linux else False,
        "atecc608a_i2c_bus": Path("/dev/i2c-1").exists() if is_linux else False,
        "cpu_temp_c": _read_pi_cpu_temp(),
        "disk_free_gb": round(disk.free / (1024**3), 2),
        "disk_total_gb": round(disk.total / (1024**3), 2),
    }

from backend.services.tle_sync import sync_tle_catalog, get_catalog_status

@router.post("/tle/sync")
def trigger_tle_sync():
    return sync_tle_catalog()

@router.get("/tle/status")
def tle_status():
    return get_catalog_status()