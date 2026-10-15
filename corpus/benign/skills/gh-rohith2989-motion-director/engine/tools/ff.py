"""Find ffmpeg / ffprobe: $FFMPEG_PATH / $FFPROBE_PATH, then PATH, then the project's npm static builds."""
import os
import platform
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXE = ".exe" if os.name == "nt" else ""


def ffmpeg():
    p = os.environ.get("FFMPEG_PATH") or shutil.which("ffmpeg")
    if p:
        return p
    p = os.path.join(ROOT, "node_modules", "ffmpeg-static", "ffmpeg" + EXE)
    if os.path.exists(p):
        return p
    raise SystemExit("ffmpeg not found: npm install in the project, or set FFMPEG_PATH")


def ffprobe():
    p = os.environ.get("FFPROBE_PATH") or shutil.which("ffprobe")
    if p:
        return p
    plat = {"Windows": "win32", "Darwin": "darwin", "Linux": "linux"}[platform.system()]
    arch = {"AMD64": "x64", "x86_64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(platform.machine(), "x64")
    p = os.path.join(ROOT, "node_modules", "ffprobe-static", "bin", plat, arch, "ffprobe" + EXE)
    if os.path.exists(p):
        return p
    raise SystemExit("ffprobe not found: npm install in the project, or set FFPROBE_PATH")
