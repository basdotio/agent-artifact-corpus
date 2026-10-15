#!/usr/bin/env python3
"""
Generate or edit an image with agy (the Antigravity CLI) and save it to OUT.

  run.sh image.py "PROMPT" OUT.jpg [--aspect 16:9] [--ref IMG ...] [--timeout 300]

agy's built-in image-generator subagent calls Gemini's image model through the signed-in Antigravity
account, so no API key is needed. --aspect is one of 1:1 2:3 3:2 3:4 4:3 9:16 16:9. --ref passes up to
3 images to edit, combine or use as references. agy writes a JPEG (16:9 is 1376x768) into its own
conversation folder; this copies the newest one to OUT, converting when OUT has another extension.
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from PIL import Image

BRAIN = Path.home() / ".gemini" / "antigravity-cli" / "brain"
ASPECTS = ["1:1", "2:3", "3:2", "3:4", "4:3", "9:16", "16:9"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("out")
    ap.add_argument("--aspect", default="16:9", choices=ASPECTS)
    ap.add_argument("--ref", action="append", default=[], help="image to edit or use as a reference (max 3)")
    ap.add_argument("--timeout", type=int, default=300, help="seconds to wait for agy")
    a = ap.parse_args()
    if len(a.ref) > 3:
        ap.error("at most 3 --ref images")

    out = Path(a.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    refs = [str(Path(r).resolve()) for r in a.ref]
    # Without this, agy may open an installed image skill instead, which print mode denies.
    ask = ("Use your built-in image-generator subagent, not a skill. "
           f"Generate one image with aspect ratio {a.aspect} from the prompt below. "
           + (f"Pass these as ImagePaths: {', '.join(refs)}. " if refs else "")
           + "Do not copy or move the file. Reply with only the absolute path of the saved file.\n"
           f"Prompt: {a.prompt}")
    r = subprocess.run(
        ["agy", "-p", ask, "--disable-slash-commands", "--output-format", "json",
         "--print-timeout", f"{a.timeout}s"],
        capture_output=True, text=True, cwd=out.parent, timeout=a.timeout + 30,
    )
    try:
        res = json.loads(r.stdout[r.stdout.index("{"):])
    except ValueError:
        raise SystemExit(f"agy failed ({r.returncode}):\n{(r.stdout + r.stderr)[-2000:]}")

    made = [p for p in (BRAIN / res["conversation_id"]).glob("*")
            if p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")]
    if not made:
        raise SystemExit(f"agy made no image: {res.get('response', '').strip()}")
    src = max(made, key=lambda p: p.stat().st_mtime)
    if src.suffix.lower() == out.suffix.lower():
        shutil.copyfile(src, out)
    else:
        Image.open(src).convert("RGB").save(out)
    w, h = Image.open(out).size
    print(f"{out}  {w}x{h}")


if __name__ == "__main__":
    main()
