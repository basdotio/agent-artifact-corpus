"""
Check that this machine can make films. Prints what is missing and how to fix it.

python <skill>/scripts/doctor.py [project-dir]
"""
import importlib
import os
import shutil
import subprocess
import sys


def ok(msg):
    print(f"  ok    {msg}")


def bad(msg, fix):
    print(f"  MISSING {msg}\n          fix: {fix}")


def main():
    proj = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else None
    print("motion-director doctor")
    v = sys.version_info
    (ok if v >= (3, 10) else lambda m: bad(m, "install Python 3.10+"))(f"python {v.major}.{v.minor}")
    node = shutil.which("node")
    if node:
        out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout.strip()
        major = int(out.lstrip("v").split(".")[0]) if out else 0
        (ok if major >= 18 else lambda m: bad(m, "install Node 18+ (https://nodejs.org)"))(f"node {out}")
    else:
        bad("node", "install Node 18+ (https://nodejs.org)")
    (ok if shutil.which("npm") or shutil.which("npm.cmd") else lambda m: bad(m, "comes with Node"))("npm")
    for mod, why in [("numpy", "audio"), ("scipy", "audio"), ("soundfile", "audio"), ("numba", "audio"), ("pyloudnorm", "loudness"),
                     ("PIL", "contact sheets"), ("matplotlib", "audio plots"), ("google.genai", "voice/review (optional)"),
                     ("requests", "voice (optional)"), ("faster_whisper", "voice alignment (optional)")]:
        try:
            importlib.import_module(mod)
            ok(f"python: {mod}")
        except Exception:  # noqa: BLE001
            bad(f"python: {mod} ({why})", "pip install -r <project>/requirements.txt")
    for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ELEVEN_API_KEY"):
        print(f"  {'set ' if os.environ.get(k) else 'unset'} {k}  (only needed for narrated films / AI review)")
    if proj:
        nm = os.path.join(proj, "node_modules")
        if os.path.isdir(nm):
            ok("project node_modules")
            for p in ("puppeteer", "ffmpeg-static", "ffprobe-static", "sharp", "simple-icons", "@fontsource-variable/geist"):
                (ok if os.path.isdir(os.path.join(nm, p)) else lambda m: bad(m, "npm install in the project"))(f"npm: {p}")
            try:
                r = subprocess.run(["node", "-e", "(async () => console.log(await require('puppeteer').executablePath()))()"], cwd=proj, capture_output=True, text=True, timeout=60)
                exe = r.stdout.strip()
                (ok if exe and os.path.exists(exe) else lambda m: bad(m, "npx puppeteer browsers install chrome (or set CHROME_PATH)"))(f"chrome for rendering: {exe or '?'}")
            except Exception as e:  # noqa: BLE001
                bad(f"chrome check failed: {e}", "npx puppeteer browsers install chrome")
        else:
            bad("project node_modules", f"cd {proj} && npm install")
    print("done")


if __name__ == "__main__":
    main()
