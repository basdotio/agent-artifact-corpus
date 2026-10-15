#!/usr/bin/env python3
"""Generate and edit images via an OpenAI-compatible relay.

Text-to-image:  POST {BASE}/images/generations
Image edit:     POST {BASE}/images/edits   (multipart, when --ref is given)

Config resolution order (first wins): environment variable, then the .env file
next to this script. Keys: IMAGE_API_KEY, IMAGE_API_BASE, IMAGE_MODEL.
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("ERROR: python 'requests' not installed. Run: pip install requests")

SCRIPT_DIR = Path(__file__).resolve().parent


def load_env_file():
    env = {}
    envfile = SCRIPT_DIR / ".env"
    if envfile.exists():
        for line in envfile.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env


_ENV_FILE = load_env_file()


def cfg(key, default=None):
    return os.environ.get(key) or _ENV_FILE.get(key) or default


API_BASE = cfg("IMAGE_API_BASE", "").rstrip("/")
API_KEY = cfg("IMAGE_API_KEY")
DEFAULT_MODEL = cfg("IMAGE_MODEL", "gpt-image-2.5")

DEFAULT_OUT_DIR = cfg("IMAGE_OUT_DIR", "generated-images")

TEMPLATES_FILE = SCRIPT_DIR / "templates.json"


def load_templates():
    if not TEMPLATES_FILE.exists():
        return {}
    try:
        return json.loads(TEMPLATES_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit("ERROR: bad templates.json: %s" % e)


TEMPLATES = load_templates()

PRESETS_FILE = SCRIPT_DIR / "presets.json"


def load_presets():
    if not PRESETS_FILE.exists():
        return {}
    try:
        return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        sys.exit("ERROR: bad presets.json: %s" % e)


PRESETS = load_presets()


def compose_prompt(tpl, preset, subject, text=None):
    parts = []
    if tpl.get("prompt_prefix"):
        parts.append(tpl["prompt_prefix"])
    if preset.get("prompt_prefix"):
        parts.append(preset["prompt_prefix"])
    parts.append(subject)
    if preset.get("prompt_suffix"):
        parts.append(preset["prompt_suffix"])
    if text:
        items = [t.strip() for t in re.split(r"[|，,;；\n]+", text) if t.strip()]
        parts.append("Chinese text to display (render these characters exactly, do not translate or misspell): %s" % "；".join(items))
    if tpl.get("prompt_suffix"):
        parts.append(tpl["prompt_suffix"])
    return "\n\n".join(parts)


def _pick(*vals):
    for v in vals:
        if v:
            return v
    return None


def slugify(text, n=40):
    s = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff]+", "-", text).strip("-").lower()
    if not s:
        s = "image"
    return s[:n]


def download_image(item, out_path):
    """item is a data entry from the API: either {url} or {b64_json}."""
    if item.get("url"):
        r = requests.get(item["url"], timeout=300)
        r.raise_for_status()
        out_path.write_bytes(r.content)
    elif item.get("b64_json"):
        out_path.write_bytes(base64.b64decode(item["b64_json"]))
    else:
        raise RuntimeError("response item has neither url nor b64_json: %s" % item)


def resolve_outputs(args, count):
    """Return a list of target file paths."""
    out = args.out
    if out:
        p = Path(out)
        as_dir = out.endswith(("/", os.sep)) or (p.exists() and p.is_dir()) or count > 1
    else:
        as_dir = True
        p = Path(DEFAULT_OUT_DIR)

    stem = "%s-%s" % (time.strftime("%Y%m%d-%H%M%S"),
                      slugify(getattr(args, "stem_hint", None) or args.prompt))
    if as_dir:
        p.mkdir(parents=True, exist_ok=True)
        if count == 1:
            return [p / (stem + ".png")]
        return [p / ("%s-%d.png" % (stem, i + 1)) for i in range(count)]
    return [p]


def call_edit(args, headers):
    data = {"model": args.model, "prompt": args.prompt, "n": str(args.n)}
    if args.size:
        data["size"] = args.size
    if args.quality:
        data["quality"] = args.quality
    if args.background:
        data["background"] = args.background

    files = []
    field = "image" if len(args.ref) == 1 else "image[]"
    for ref in args.ref:
        fp = Path(ref)
        if not fp.exists():
            sys.exit("ERROR: reference image not found: %s" % ref)
        mime = mimetypes.guess_type(fp.name)[0] or "image/png"
        files.append((field, (fp.name, fp.read_bytes(), mime)))
    if args.mask:
        mp = Path(args.mask)
        if not mp.exists():
            sys.exit("ERROR: mask not found: %s" % args.mask)
        files.append(("mask", (mp.name, mp.read_bytes(), "image/png")))

    return requests.post(API_BASE + "/images/edits", headers=headers, data=data, files=files, timeout=600)


def call_generation(args, headers):
    payload = {"model": args.model, "prompt": args.prompt, "n": args.n}
    if args.size:
        payload["size"] = args.size
    if args.quality:
        payload["quality"] = args.quality
    if args.background:
        payload["background"] = args.background
    return requests.post(API_BASE + "/images/generations", headers=headers, json=payload, timeout=600)


def main():
    ap = argparse.ArgumentParser(description="Generate or edit images via an OpenAI-compatible API.")
    ap.add_argument("prompt", nargs="?", help="image description / edit instruction / product subject")
    ap.add_argument("--model", default=None, help="model id (default: %s)" % DEFAULT_MODEL)
    ap.add_argument("--size", default=None, help="e.g. 1024x1024, 1536x1024, 1024x1536, auto")
    ap.add_argument("--n", type=int, default=1, help="number of images (default 1)")
    ap.add_argument("--quality", default=None, help="low | medium | high | auto")
    ap.add_argument("--background", default=None, help="transparent | opaque | auto")
    ap.add_argument("--template", default=None, help="apply a PDD template (see --list-templates)")
    ap.add_argument("--preset", default=None, help="apply a style preset (see --list-presets)")
    ap.add_argument("--text", default=None, help="Chinese text to render (for template/卖点/海报)")
    ap.add_argument("--list-templates", action="store_true", help="show available templates and exit")
    ap.add_argument("--list-presets", action="store_true", help="show available style presets and exit")
    ap.add_argument("--ref", action="append", default=[], metavar="FILE",
                    help="reference image; switches to edit mode. repeatable")
    ap.add_argument("--mask", default=None, help="optional mask PNG (edit mode)")
    ap.add_argument("--out", default=None, help="output file, or directory (ending in /)")
    ap.add_argument("--json", action="store_true", help="print machine-readable JSON result")
    args = ap.parse_args()

    if args.list_templates:
        if not TEMPLATES:
            print("(no templates found at %s)" % TEMPLATES_FILE)
        for key, t in TEMPLATES.items():
            flags = " [需 --text]" if t.get("requires_text") else ""
            print("%-16s %s — %s%s" % (key, t.get("name", ""), t.get("desc", ""), flags))
        return
    if args.list_presets:
        if not PRESETS:
            print("(no presets found at %s)" % PRESETS_FILE)
        for key, p in PRESETS.items():
            print("%-12s %s — %s" % (key, p.get("name", ""), p.get("desc", "")))
        return
    if not args.prompt:
        ap.error("prompt is required (or use --list-templates / --list-presets)")

    subject = args.prompt
    if args.template and args.template not in TEMPLATES:
        sys.exit("ERROR: unknown template '%s'. Available: %s"
                 % (args.template, ", ".join(TEMPLATES) or "(none)"))
    if args.preset and args.preset not in PRESETS:
        sys.exit("ERROR: unknown preset '%s'. Available: %s"
                 % (args.preset, ", ".join(PRESETS) or "(none)"))
    tpl = TEMPLATES.get(args.template, {}) if args.template else {}
    preset = PRESETS.get(args.preset, {}) if args.preset else {}

    if tpl or preset or args.text:
        args.prompt = compose_prompt(tpl, preset, subject, args.text)
        args.stem_hint = "-".join(x for x in (args.template, args.preset, subject) if x)

    # defaults: explicit CLI flag > template > preset > built-in
    args.model = _pick(args.model, tpl.get("model"), preset.get("model"), DEFAULT_MODEL)
    args.size = _pick(args.size, tpl.get("size"), preset.get("size"))
    args.quality = _pick(args.quality, tpl.get("quality"), preset.get("quality"))
    args.background = _pick(args.background, tpl.get("background"), preset.get("background"))

    if not API_KEY:
        sys.exit("ERROR: IMAGE_API_KEY not set. Put it in %s/.env" % SCRIPT_DIR)
    if not API_BASE:
        sys.exit("ERROR: IMAGE_API_BASE not set. Put it in %s/.env "
                 "(e.g. https://your-relay.example/v1)" % SCRIPT_DIR)
    if args.n < 1:
        sys.exit("ERROR: --n must be >= 1")

    headers = {"Authorization": "Bearer " + API_KEY}
    is_edit = len(args.ref) > 0

    try:
        resp = call_edit(args, headers) if is_edit else call_generation(args, headers)
    except requests.RequestException as e:
        sys.exit("ERROR: request failed: %s" % e)

    if resp.status_code != 200:
        sys.exit("ERROR http %s: %s" % (resp.status_code, resp.text[:2000]))

    try:
        j = resp.json()
    except ValueError:
        sys.exit("ERROR: non-JSON response: %s" % resp.text[:1000])

    if j.get("error"):
        sys.exit("ERROR: %s" % json.dumps(j["error"], ensure_ascii=False))
    items = j.get("data") or []
    if not items:
        sys.exit("ERROR: empty data in response: %s" % resp.text[:1000])

    targets = resolve_outputs(args, len(items))
    saved = []
    for item, path in zip(items, targets):
        path.parent.mkdir(parents=True, exist_ok=True)
        download_image(item, path)
        saved.append(str(path.resolve()))

    usage = j.get("usage", {})
    result = {
        "mode": "edit" if is_edit else "generate",
        "template": args.template,
        "model": args.model,
        "saved": saved,
        "revised_prompt": items[0].get("revised_prompt"),
        "usage": {k: usage.get(k) for k in ("total_tokens", "input_tokens", "output_tokens") if k in usage},
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for p in saved:
            print(p)
        if result.get("revised_prompt"):
            print("# revised_prompt: %s" % result["revised_prompt"], file=sys.stderr)


if __name__ == "__main__":
    main()
