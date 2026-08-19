import sys
from pathlib import Path


def base_dir() -> Path:
    """App root, whether running from source or from the bundled .exe."""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def resource(relative: str) -> Path:
    return base_dir() / relative
