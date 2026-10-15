from __future__ import annotations

import os
import secrets
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = Path(os.environ.get("MUSTANG_DATA_DIR", Path.home() / "AppData/Local/MustangToneAgent"))
DATA.mkdir(parents=True, exist_ok=True)
for folder in ("audio", "screens", "checkpoints", "models"):
    (DATA / folder).mkdir(exist_ok=True)


def token() -> str:
    path = DATA / "access.token"
    if not path.exists():
        path.write_text(secrets.token_urlsafe(32), encoding="utf-8")
    return path.read_text(encoding="utf-8").strip()


def adb_path() -> str:
    explicit = os.environ.get("MUSTANG_ADB")
    if explicit:
        return explicit
    found = shutil.which("adb")
    if found:
        return found
    base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    candidates = list(base.glob("Microsoft/WinGet/Packages/Google.PlatformTools_*/platform-tools/adb.exe"))
    candidates += list(base.glob("Android/Sdk/platform-tools/adb.exe"))
    if not candidates:
        raise RuntimeError("ADB not found. Install Google Platform Tools or set MUSTANG_ADB.")
    return str(candidates[0])
