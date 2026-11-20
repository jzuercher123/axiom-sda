# Translates UI wizard & presets into core/agent YAMLs
import os
from pathlib import Path
import yaml

DATA_DIR = Path(os.getenv("AXIOM_DATA_DIR", "./data"))
CONFIG_DIR = DATA_DIR / "config"
PRESETS_DIR = Path("presets/profiles")

def list_presets() -> dict[str, dict]:
    presets = {}
    for file in sorted(PRESETS_DIR.glob("*.yaml")):
        with file.open("r", encoding="utf-8") as f:
            presets[file.stem] = yaml.safe_load(f)
    return presets

def write_node_configs(
    observer_id: str,
    latitude: float,
    longitude: float,
    elevation_m: float,
    profile_key: str,
    spacetrack_user: str = "",
) -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    presets = list_presets()
    profile = presets.get(profile_key, presets["dark_sky"])

    core_config = {
        "site": {
            "observer_id": observer_id,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": elevation_m,
        },
        "sensor": {
            "exposure_ms": profile["detection"]["exposure_ms"],
            "gain": profile["detection"]["gain"],
            "sky_mask_path": "/data/config/sky_mask.png",
        },
    }

    agent_config = {
        "profile": profile_key,
        "detection": profile["detection"],
        "catalog": {
            "source": "spacetrack" if spacetrack_user else "celestrak",
            "spacetrack_user": spacetrack_user,
        },
    }

    (CONFIG_DIR / "core_config.yaml").write_text(
        yaml.safe_dump(core_config, sort_keys=False), encoding="utf-8"
    )
    (CONFIG_DIR / "agent_config.yaml").write_text(
        yaml.safe_dump(agent_config, sort_keys=False), encoding="utf-8"
    )
    return CONFIG_DIR