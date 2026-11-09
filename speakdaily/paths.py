"""Where the app keeps its bundled resources and the user's data."""
import os
import sys
from pathlib import Path

APP_NAME = "SpeakDaily"


def resource_dir() -> Path:
    """Folder with bundled assets (works in dev and inside the PyInstaller exe)."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "speakdaily"
    return Path(__file__).resolve().parent


def asset(*parts: str) -> Path:
    return resource_dir().joinpath("assets", *parts)


def _writable(folder: Path) -> bool:
    try:
        folder.mkdir(parents=True, exist_ok=True)
        probe = folder / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def data_dir() -> Path:
    """User data folder.

    Order: SPEAKDAILY_DATA env var, then a 'SpeakDaily_data' folder next to the
    exe (portable), then %APPDATA%/SpeakDaily (or ~/.speakdaily on other OSes).
    """
    env = os.environ.get("SPEAKDAILY_DATA")
    if env:
        folder = Path(env)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    if getattr(sys, "frozen", False):
        portable = Path(sys.executable).resolve().parent / f"{APP_NAME}_data"
    else:
        portable = Path(__file__).resolve().parent.parent / "user_data"
    if _writable(portable):
        return portable

    base = os.environ.get("APPDATA")
    folder = Path(base) / APP_NAME if base else Path.home() / ".speakdaily"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def recordings_dir() -> Path:
    folder = data_dir() / "recordings"
    folder.mkdir(parents=True, exist_ok=True)
    return folder
