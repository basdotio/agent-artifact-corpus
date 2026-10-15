"""Which PDF renderer this machine has. Stdlib only: setup.py runs under the system python3 before the venv exists,
and manual.py needs the same answer when it exports — one place so the two never disagree."""
import os, pathlib, platform, shutil, subprocess

HERE = pathlib.Path(__file__).parent
SOFFICE_DEFAULTS = [
    r"C:\Program Files\LibreOffice\program\soffice.exe",
    r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]


def find_soffice():
    """MSLIDES_SOFFICE, then PATH, then the stock install locations; None when LibreOffice is not here."""
    for p in [os.environ.get("MSLIDES_SOFFICE"), shutil.which("soffice"), *SOFFICE_DEFAULTS]:
        if p and pathlib.Path(p).exists():
            return p
    return None


def has_keynote():
    return platform.system() == "Darwin" and pathlib.Path("/Applications/Keynote.app").exists()


def has_powerpoint():
    """Windows only: the COM class is registered iff PowerPoint is installed (a quick registry probe, no launch)."""
    if platform.system() != "Windows":
        return False
    r = subprocess.run(["powershell", "-NoProfile", "-Command", r"Test-Path 'HKLM:\SOFTWARE\Classes\PowerPoint.Application'"],
                       capture_output=True, text=True)
    return r.stdout.strip() == "True"


def renderer():
    """Human-readable label of the renderer manual.py --pdf would use, or None."""
    if has_keynote():
        return "Keynote"
    if has_powerpoint():
        return "PowerPoint"
    so = find_soffice()
    return f"LibreOffice ({so})" if so else None
