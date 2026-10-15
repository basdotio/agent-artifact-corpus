"""Windows shortcuts: Start menu entry, project launcher and the optional Startup-folder entry; the app icon."""
import os
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from . import APP_NAME, config

ICON = config.DATA / "icon.ico"
STARTUP_LINK = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup" / f"{APP_NAME}.lnk"
START_MENU_LINK = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs" / f"{APP_NAME}.lnk"
PROJECT_LINK = config.ROOT / f"{APP_NAME}.lnk"
LAUNCHER = config.ROOT / "FatimaVoiceStudio.exe"  # installed copies start through this

BRAND = "#3f4ae0"   # indigo: tells it apart from Fatima Image Studio's red in the tray
MARK = "#fcfaf5"
BARS = [0.30, 0.62, 0.95, 0.70, 0.42, 0.78, 0.36]  # the waveform mark, heights as a share of the square


def pythonw() -> str:
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return str(candidate if candidate.exists() else exe)


def launch_command(app_args: str) -> tuple[str, str]:
    """What a shortcut runs: the launcher when installed, else pythonw -m studio."""
    if config.INSTALLED and LAUNCHER.exists():
        return str(LAUNCHER), app_args
    return pythonw(), f"-m studio {app_args}"


def python_console() -> str:
    """python.exe (not pythonw): stdio MCP needs a console-mode interpreter."""
    bundled = config.ROOT / "python" / "python.exe"
    if config.INSTALLED and bundled.exists():
        return str(bundled)
    exe = Path(sys.executable)
    candidate = exe.with_name("python.exe")
    return str(candidate if candidate.exists() else exe)


def icon_image(size: int = 256) -> Image.Image:
    """The studio mark: cream waveform bars on an indigo rounded square (same drawing as web/icons/mark.svg)."""
    scale = 4  # draw large, then shrink: smooth edges at tray sizes
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=BRAND)
    n = len(BARS)
    inner = s * 0.64
    gap = inner / (n * 2 - 1)
    x0 = (s - inner) / 2
    for i, h in enumerate(BARS):
        x = x0 + i * 2 * gap
        bh = s * 0.62 * h
        y = (s - bh) / 2
        d.rounded_rectangle([x, y, x + gap, y + bh], radius=gap / 2, fill=MARK)
    return img.resize((size, size), Image.LANCZOS)


def ensure_icon() -> Path:
    if not ICON.exists():
        ICON.parent.mkdir(parents=True, exist_ok=True)
        icon_image().save(ICON, sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    return ICON


def make_shortcut(link: Path, app_args: str) -> None:
    target, args = launch_command(app_args)
    link.parent.mkdir(parents=True, exist_ok=True)
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
          "$s.TargetPath=$env:TARGET;$s.Arguments=$env:ARGS;$s.WorkingDirectory=$env:WD;"
          "$s.IconLocation=$env:ICO;$s.Description='Voiceovers and voice cloning on this PC';$s.Save()")
    env = os.environ | {"LNK": str(link), "TARGET": target, "ARGS": args, "WD": str(config.ROOT),
                        "ICO": target if target == str(LAUNCHER) else str(ensure_icon())}
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps], env=env, check=True,
                   capture_output=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))


def install_launchers() -> None:
    """Start menu entry and a launcher in the project folder; both open the tray app."""
    for link in (START_MENU_LINK, PROJECT_LINK):
        make_shortcut(link, "--tray")


def enabled() -> bool:
    return STARTUP_LINK.exists()


def set_enabled(on: bool) -> None:
    if on:
        make_shortcut(STARTUP_LINK, "--tray --no-browser")
    else:
        STARTUP_LINK.unlink(missing_ok=True)
