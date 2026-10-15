"""Shared helpers for the onetake-videogen scripts."""

import json
import os
import subprocess
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
ONETAKE = Path(os.environ.get("ONETAKE_HOME", Path.home() / "OneTake"))
FONTS_DIR = SKILL_DIR / "assets" / "fonts"
REMOTION_DIR = SKILL_DIR / "remotion"

TARGET_W, TARGET_H, TARGET_FPS = 1280, 720, 60


def load_json(path):
    return json.loads(Path(path).read_text())


def save_json(obj, path):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1))


def probe(path):
    """Return duration, video size/fps and whether audio exists."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=duration:stream=codec_type,width,height,avg_frame_rate",
         "-of", "json", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout
    d = json.loads(out)
    info = {"duration": float(d["format"]["duration"]), "has_audio": False, "has_video": False}
    for s in d.get("streams", []):
        if s["codec_type"] == "video" and not info["has_video"]:
            num, den = (s.get("avg_frame_rate") or "0/1").split("/")
            info.update(has_video=True, width=s["width"], height=s["height"],
                        fps=float(num) / float(den) if float(den) else 0)
        elif s["codec_type"] == "audio":
            info["has_audio"] = True
    return info


def run(cmd, **kw):
    """Run a command, raising with the stderr tail on failure."""
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed ({r.returncode}):\n{r.stderr[-3000:]}")
    return r


def fmt_ts(sec):
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:04.1f}"
