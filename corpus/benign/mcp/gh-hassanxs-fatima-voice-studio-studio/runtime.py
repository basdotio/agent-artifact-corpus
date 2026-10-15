"""The Microsoft Visual C++ runtime the engines need.

The official llama.cpp and whisper.cpp Windows builds load msvcp140.dll, vcruntime140*.dll and vcomp140.dll from
Windows. Most PCs have them (many programs install Microsoft's redistributable), but a fresh Windows install doesn't,
and then every engine fails to start (exit code 0xC0000135). Installed copies carry those DLLs in runtime/, and
prepare() puts them next to an engine only when Windows lacks them ("app-local" deployment, which Microsoft allows).
Once Windows has its own copies (kept up to date by Windows Update), ours are removed again.
"""
import ctypes
import logging
import os
import shutil
import sys
from pathlib import Path

from . import config

log = logging.getLogger("studio.runtime")

BUNDLED = config.ROOT / "runtime"
VC_REDIST_URL = "https://aka.ms/vs/17/release/vc_redist.x64.exe"
# DLL not found, entry point not found (an old runtime), bad image: the engine never got to run.
LOAD_FAILURES = {0xC0000135, 0xC0000139, 0xC000007B}


def system_dir() -> Path:
    return Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32"


def _ours(local: Path, bundled: Path) -> bool:
    a, b = local.stat(), bundled.stat()
    return a.st_size == b.st_size and int(a.st_mtime) == int(b.st_mtime)  # copy2 keeps the time


def prepare(folder: Path, system: Path | None = None) -> None:
    """Before an engine in `folder` starts: copy in the runtime DLLs Windows is missing, remove ours it now has."""
    if not BUNDLED.is_dir():
        return  # a source copy: the developer's PC has the runtime
    system = system or system_dir()
    for dll in BUNDLED.glob("*.dll"):
        local = folder / dll.name
        try:
            if (system / dll.name).exists():
                if local.exists() and _ours(local, dll):
                    local.unlink()
            elif not local.exists():
                shutil.copy2(dll, local)
                log.info("Windows has no %s: using the app's copy for %s", dll.name, folder.name)
        except OSError as e:  # in use or read-only: leave it, the engine may still start
            log.warning("Couldn't update %s in %s: %s", dll.name, folder, e)


def load_problem(code: int | None) -> str | None:
    """A plain explanation when an engine couldn't even start because of the runtime."""
    if code is None or (code & 0xFFFFFFFF) not in LOAD_FAILURES:
        return None
    return ("The engine couldn't start: a file it needs is missing. Usually that's the Microsoft Visual C++ Runtime: "
            f"install it free from Microsoft ({VC_REDIST_URL}) and try again. If that doesn't help, download the "
            "engine again on the Models page.")


def quiet_loader_errors() -> None:
    """No Windows pop-up per engine run when a DLL is missing; the app shows its own message instead.
    Engines started from this process inherit the setting."""
    if sys.platform == "win32":
        SEM_FAILCRITICALERRORS = 0x0001
        k32 = ctypes.windll.kernel32
        k32.SetErrorMode(k32.SetErrorMode(0) | SEM_FAILCRITICALERRORS)
