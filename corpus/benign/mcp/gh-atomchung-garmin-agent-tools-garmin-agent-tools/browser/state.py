"""Private browser state is independent of source and API authorization."""
import os
import stat
from pathlib import Path


def private_location(value):
    root = Path(value).expanduser()
    if not root.is_absolute() or root.is_symlink() or ".." in root.parts:
        raise ValueError("unsafe_browser_state")
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists() and root.resolve().is_relative_to(parent):
            raise ValueError("browser_state_must_be_outside_checkout")
    return root


def state_root():
    value = os.environ.get("GARMIN_AGENT_BROWSER_HOME")
    return private_location(value if value else Path.home() / ".local/share/garmin-agent-tools-browser")


def ensure_state_root():
    root = state_root()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(mode=0o700, exist_ok=True)
    info = root.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("unsafe_browser_state")
    return root
