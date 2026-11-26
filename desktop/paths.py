import os
import pathlib
import sys


def get_app_data_dir() -> pathlib.Path:
    if os.name == "nt":
        base = pathlib.Path(
            os.environ.get("LOCALAPPDATA", pathlib.Path.home() / "AppData" / "Local")
        )
    else:
        base = pathlib.Path(
            os.environ.get("XDG_DATA_HOME", pathlib.Path.home() / ".local" / "share")
        )
    data_dir = base / "Axiom"
    (data_dir / "config").mkdir(parents=True, exist_ok=True)
    (data_dir / "logs").mkdir(parents=True, exist_ok=True)
    (data_dir / "events").mkdir(parents=True, exist_ok=True)
    return data_dir


def get_sda_root() -> pathlib.Path:
    """Returns the inner axiom-sda directory (containing backend/, frontend/, presets/)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        bundled_sda = pathlib.Path(sys._MEIPASS) / "axiom-sda"
        return bundled_sda if bundled_sda.exists() else pathlib.Path(sys._MEIPASS)
    return pathlib.Path(__file__).resolve().parents[1]


def get_workspace_root() -> pathlib.Path:
    """Resolves the parent folder containing axiom_kernel, axiom_agents, and axiom-sda."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return pathlib.Path(sys._MEIPASS)
    # desktop/paths.py -> desktop -> inner axiom-sda -> outer axiom-sda -> Desktop
    return pathlib.Path(__file__).resolve().parents[3]