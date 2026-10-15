"""Resolve local Python workers on supported runtime platforms."""
from pathlib import Path
import os
import platform


def venv_python(root: Path, name: str = ".venv") -> Path:
    return Path(root) / name / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def platform_guidance() -> str:
    if os.name == "nt":
        return "Native Windows full-runtime setup is unverified. Use WSL2 Ubuntu and follow references/setup.md; setup.sh runs inside WSL2. WSL2 is never installed automatically."
    if platform.system() in {"Linux", "Darwin"}:
        return "Run bash setup.sh with Python 3.12+ and Rubber Band CLI installed."
    return "Full runtime supports macOS/Linux (or WSL2 Ubuntu on Windows)."


def mesh_python(root: Path) -> Path:
    worker = venv_python(root, ".venv-face")
    if not worker.is_file():
        raise RuntimeError("Face mesh worker missing. Run bash setup-face-mesh.sh using exact Python 3.12. " + platform_guidance())
    return worker
