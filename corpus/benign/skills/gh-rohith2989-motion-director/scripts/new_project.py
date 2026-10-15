"""
Scaffold a new film project from the engine template.

python <skill>/scripts/new_project.py <dir> [--format 16:9|9:16|1:1|4:5] [--fps 60] [--duration 30] [--bpm 120]
                                            [--title "Acme launch"] [--keep-demo] [--no-install]

Copies engine/ (composition, tools, audio, voice, review), writes comp/config.json for the format, clears the
demo scenes (unless --keep-demo), writes docs/PLAN.md from the template, runs `npm install` (Chrome for the
renderer, ffmpeg, fonts, icons) and `pip install -r requirements.txt`. Prints the next steps.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENGINE = os.path.join(SKILL, "engine")
FORMATS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "4:5": (1080, 1350)}

EMPTY_SCENE = '''// s01 · {title} — replace with the film's first section (see the skill's references/engine.md).
import {{ scene, cue, bar, W, H }} from "../core/runtime.js";
import {{ h, css, clamp }} from "../core/anim.js";
import {{ expoOut }} from "../core/ease.js";
import {{ Words }} from "../sys/reveal.js";
import {{ livingLight }} from "../sys/light.js";

scene({{
  id: "s01",
  start: 0,
  end: {dur},
  z: 10,
  build(root, s) {{
    s.light = livingLight(root, {{ base: "var(--bg)", colors: ["var(--accent-2)", "#ffffff"], count: 4 }});
    s.titleEl = h("div", {{ class: "abs t-hero", style: {{ left: "0", width: `${{W}}px`, top: `${{H * 0.4}}px`, textAlign: "center" }} }});
    root.appendChild(s.titleEl);
    s.words = new Words(s.titleEl, ["{title}"]).in(0.6, {{ stagger: 0.12, dur: 0.9 }});
  }},
  update(lt, t, s) {{
    s.light.update(t);
    s.words.update(t);
  }},
}});
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--format", default="16:9", choices=FORMATS)
    ap.add_argument("--fps", type=int, default=60)
    ap.add_argument("--duration", type=float, default=30)
    ap.add_argument("--bpm", type=float, default=120)
    ap.add_argument("--title", default="Untitled film")
    ap.add_argument("--keep-demo", action="store_true")
    ap.add_argument("--no-install", action="store_true")
    a = ap.parse_args()
    dst = os.path.abspath(a.dir)
    if os.path.exists(dst) and os.listdir(dst):
        sys.exit(f"{dst} exists and is not empty")
    shutil.copytree(ENGINE, dst, ignore=shutil.ignore_patterns("node_modules", "renders", "out", "__pycache__", "cache", "*.mkv", "*.mp4"), dirs_exist_ok=True)
    w, h = FORMATS[a.format]
    cfg = {"title": a.title, "width": w, "height": h, "fps": a.fps, "duration": a.duration, "bpm": a.bpm, "gridOffset": 0, "shutter": 0.5,
           "finish": {"grain": 0.03, "vignette": 0.06}}
    if a.keep_demo:
        cfg.update(duration=12, bpm=120, title="Lumen — demo film")
    json.dump(cfg, open(os.path.join(dst, "comp", "config.json"), "w"), indent=2)
    if not a.keep_demo:
        sc = os.path.join(dst, "comp", "scenes")
        for f in os.listdir(sc):
            os.remove(os.path.join(sc, f))
        open(os.path.join(sc, "index.js"), "w").write('// The film\'s scenes, in order. ?only=s02 loads a subset while building.\nexport const SCENES = ["s01_open"];\n')
        open(os.path.join(sc, "s01_open.js"), "w", encoding="utf-8").write(EMPTY_SCENE.format(title=a.title.replace('"', "'"), dur=a.duration))
    os.makedirs(os.path.join(dst, "docs"), exist_ok=True)
    shutil.copy(os.path.join(SKILL, "references", "plan-template.md"), os.path.join(dst, "docs", "PLAN.md"))
    open(os.path.join(dst, ".gitignore"), "w").write("node_modules/\nrenders/\nout/\naudio/out/\nvoice/cache/\nvoice/audition/\nvoice/takes/\nvoice/lines/\n__pycache__/\n*.mkv\n")
    print(f"project: {dst}  ({w}x{h} @ {a.fps} fps, {cfg['duration']} s)")
    if not a.no_install:
        npm = "npm.cmd" if os.name == "nt" else "npm"
        print("npm install (Chrome for the renderer, ffmpeg, fonts, icons) ...")
        subprocess.run([npm, "install", "--no-audit", "--no-fund"], cwd=dst, check=True)
        print("pip install -r requirements.txt ...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "-r", "requirements.txt"], cwd=dst, check=False)
    print("""
next:
  1. research the subject, then write docs/PLAN.md (the treatment)            - SKILL.md + references/plan-template.md
  2. set comp/css/theme.css to the subject's real tokens; build scenes        - references/engine.md
  3. stills:  node tools/render.js --stills 1,4,8 --dir renders/stills/a
  4. sound:   node tools/probe.js 0 "window.getCues()" > audio/cues.json && python audio/score.py && python audio/mix.py
  5. preview: npm run preview   then   python tools/sheet.py --video renders/preview.mkv --every 1 renders/sheet.png
  6. final:   npm run render    then   python tools/assemble.py renders/master.mkv --audio audio/out/mix.wav --name Film --cover 3""")


if __name__ == "__main__":
    main()
