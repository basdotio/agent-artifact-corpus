#!/usr/bin/env python3
# copied from shared/lib/cine.py sha256:4c11dbc215774d887fb1eb276b6fe2d9a0165eb9a4c2ba7a713aedc5a7e98043; edit the source
"""cinewright runtime CLI: kb, cards, compile, continuity, qc, takes, voice.

Run it; do not read it. Python 3.9+, standard library only.

  python scripts/cine.py kb index|search WORDS|show SLUG [--section NAME]
  python scripts/cine.py cards new PROJECT --id 1D --scene 1 [--cast a,b]
  python scripts/cine.py cards validate PROJECT
  python scripts/cine.py cards export PROJECT --film-json [--out FILE]
  python scripts/cine.py compile PROJECT --model MODEL [--card ID ...] [--sequence] [--resolution R] [--out DIR]
  python scripts/cine.py continuity diff PROJECT [--with CARD.json] [--json]
  python scripts/cine.py qc sheet CLIP | qc spec CLIP --project P --card ID | qc loud FILE
  python scripts/cine.py qc rubric PROJECT --card ID | qc rubric --read RUBRIC.json
  python scripts/cine.py takes log PROJECT --card ID --model M --verdict V | takes lastframe CLIP --out PNG
  python scripts/cine.py voice measure FILE [--start S --end S] [--text LINE] | voice ref FILE --out WAV
  python scripts/cine.py voice check PROJECT [--character ID --clip FILE [--start S --end S]]

A PROJECT folder holds bibles/style.json, characters.json, locations.json,
scenes.json and cards/*.json (one shot card per file).
"""
import argparse
import datetime
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SIZES = ["EWS", "WS", "FS", "MWS", "MS", "MCU", "CU", "ECU"]
SIZE_WORDS = {
    "EWS": "extreme wide shot", "WS": "wide shot", "FS": "full shot",
    "MWS": "medium wide shot", "MS": "medium shot", "MCU": "medium close-up",
    "CU": "close-up", "ECU": "extreme close-up",
}
ANGLE_WORDS = {
    "eye-level": "eye-level angle", "high": "high angle looking down",
    "low": "low angle looking up", "overhead": "overhead shot looking straight down",
    "ground": "ground-level angle", "dutch": "dutch angle",
}
MOVE_WORDS = {
    "static": "static camera", "pan-left": "slow pan left", "pan-right": "slow pan right",
    "tilt-up": "slow tilt up", "tilt-down": "slow tilt down",
    "dolly-in": "slow dolly in", "dolly-out": "slow dolly out",
    "truck-left": "camera trucks left", "truck-right": "camera trucks right",
    "track": "tracking shot following the subject", "crane-up": "crane up",
    "crane-down": "crane down", "handheld": "handheld camera",
    "zoom-in": "slow zoom in", "zoom-out": "slow zoom out",
}
TRAVEL_WORDS = {
    "left-to-right": "moving from left to right across the frame",
    "right-to-left": "moving from right to left across the frame",
    "toward-camera": "walking toward the camera",
    "away-from-camera": "walking away from the camera",
}
EYELINE_WORDS = {
    "frame-left": "looking toward frame left", "frame-right": "looking toward frame right",
    "up": "looking up", "down": "looking down", "camera": "looking into the lens",
}
POSITION_WORDS = {"frame-left": "on the left of the frame", "center": "in the center of the frame",
                  "frame-right": "on the right of the frame"}
FLIP = {"left-to-right": "right-to-left", "right-to-left": "left-to-right",
        "frame-left": "frame-right", "frame-right": "frame-left"}
POS_INDEX = {"frame-left": 0, "center": 1, "frame-right": 2}
SPEECH_WPS = 2.5  # words a second a generated voice speaks clearly (about 150 a minute)
SPEECH_LEAD_S = 0.5  # breath before the first word
# Many small figures in a wide frame: legs, faces and clones break (field lessons 020, 021)
HARD_SUBJECT = re.compile(r"\b(crowds?|herds?|flocks?|swarms?|army|armies|troops|cavalry|caravans?|stampedes?|hordes?|columns? of|dozens|hundreds)\b", re.I)
SECTIONS = ["Rules", "Numbers", "Vocabulary", "Pitfalls", "Verify", "Notes", "Compile"]


# ---------- context ----------

class Context:
    """Where references, model cards and schemas live. The repo CLI builds its own."""

    def __init__(self, ref_dirs, model_dirs, schema_dir, index_targets=None):
        self.ref_dirs = [Path(d) for d in ref_dirs]
        self.model_dirs = [Path(d) for d in model_dirs]
        self.schema_dir = Path(schema_dir)
        # (skill name, references dir) pairs that `kb index` rewrites
        self.index_targets = index_targets or []


def default_context():
    skill = HERE.parent
    own = skill / "references"
    siblings = sorted(p / "references" for p in skill.parent.glob("*") if p != skill and (p / "references").is_dir())
    schema_dir = HERE / "schemas"
    if not schema_dir.is_dir():
        for up in HERE.parents:
            if (up / "shared" / "schemas").is_dir():
                schema_dir = up / "shared" / "schemas"
                break
    dirs = ([own] if own.is_dir() else []) + siblings
    return Context(dirs, dirs, schema_dir, [(skill.name, own)] if own.is_dir() else [])


# ---------- small parsers ----------

def read_text(path):
    return Path(path).read_text(encoding="utf-8").replace("\r\n", "\n")


def write_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _scalar(s):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        return s[1:-1].replace('\\"', '"')
    return s


def _list(s):
    items = re.findall(r'\s*(?:"((?:[^"\\]|\\.)*)"|\'([^\']*)\'|([^,\[\]]+))', s.strip()[1:-1])
    out = []
    for a, b, c in items:
        v = a.replace('\\"', '"') if a else (b if b else c.strip())
        if v:
            out.append(v)
    return out


def parse_frontmatter(text):
    """Return (meta, body). Supports key: value, key: [a, b] and '- item' lists."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 3)
    if end < 0:
        if text.rstrip().endswith("\n---"):
            end = text.rstrip().rfind("\n---")
        else:
            return {}, text
    block, body = text[4:end], text[end + 5:]
    meta, key = {}, None
    for line in block.split("\n"):
        if not line.strip():
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            meta[key] = _list(val) if val.startswith("[") else (_scalar(val) if val else [])
        elif line.lstrip().startswith("- ") and key is not None and isinstance(meta.get(key), list):
            meta[key].append(_scalar(line.lstrip()[2:]))
    return meta, body


def split_sections(body):
    out, name = {}, None
    for line in body.split("\n"):
        m = re.match(r"^## (.+?)\s*$", line)
        if m:
            name = m.group(1)
            out[name] = []
        elif name:
            out[name].append(line)
    return {k: "\n".join(v).strip() for k, v in out.items()}


def compile_block(body):
    sec = split_sections(body).get("Compile", "")
    m = re.search(r"```json\n(.*?)\n```", sec, re.S)
    return json.loads(m.group(1)) if m else None


# ---------- mini JSON Schema validator (the subset the schemas use) ----------

_TYPES = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def validate(inst, schema, path="$", root=None):
    root = root if root is not None else schema
    errs = []
    if "$ref" in schema:
        node = root
        for part in schema["$ref"].lstrip("#/").split("/"):
            node = node[part]
        return validate(inst, node, path, root)
    if "enum" in schema and inst not in schema["enum"]:
        return ["%s: %r is not one of %s" % (path, inst, ", ".join(map(str, schema["enum"])))]
    t = schema.get("type")
    if t:
        types = t if isinstance(t, list) else [t]
        if not any(_TYPES[x](inst) for x in types):
            return ["%s: expected %s, got %s" % (path, "/".join(types), type(inst).__name__)]
    if isinstance(inst, str):
        if len(inst) < schema.get("minLength", 0):
            errs.append("%s: shorter than %d characters" % (path, schema["minLength"]))
        if "maxLength" in schema and len(inst) > schema["maxLength"]:
            errs.append("%s: longer than %d characters (%d)" % (path, schema["maxLength"], len(inst)))
        if "pattern" in schema and not re.search(schema["pattern"], inst):
            errs.append("%s: %r does not match %s" % (path, inst, schema["pattern"]))
        if schema.get("format") == "date":
            try:
                datetime.date.fromisoformat(inst)
            except ValueError:
                errs.append("%s: %r is not a YYYY-MM-DD date" % (path, inst))
    if _TYPES["number"](inst):
        if "minimum" in schema and inst < schema["minimum"]:
            errs.append("%s: %s is below %s" % (path, inst, schema["minimum"]))
        if "maximum" in schema and inst > schema["maximum"]:
            errs.append("%s: %s is above %s" % (path, inst, schema["maximum"]))
    if isinstance(inst, list):
        if len(inst) < schema.get("minItems", 0):
            errs.append("%s: needs at least %d items" % (path, schema["minItems"]))
        if schema.get("uniqueItems") and len({json.dumps(v, sort_keys=True) for v in inst}) < len(inst):
            errs.append("%s: items repeat" % path)
        if "items" in schema:
            for i, v in enumerate(inst):
                errs += validate(v, schema["items"], "%s[%d]" % (path, i), root)
    if isinstance(inst, dict):
        for k in schema.get("required", []):
            if k not in inst:
                errs.append("%s: missing required '%s'" % (path, k))
        props = schema.get("properties", {})
        extra = schema.get("additionalProperties", True)
        for k, v in inst.items():
            if k in props:
                errs += validate(v, props[k], "%s.%s" % (path, k), root)
            elif extra is False:
                errs.append("%s: unknown key '%s'" % (path, k))
            elif isinstance(extra, dict):
                errs += validate(v, extra, "%s.%s" % (path, k), root)
            if "propertyNames" in schema:
                errs += validate(k, schema["propertyNames"], "%s key %r" % (path, k), root)
    return errs


def load_schema(ctx, name):
    path = ctx.schema_dir / ("%s.schema.json" % name)
    data = json.loads(read_text(path))
    data.pop("$comment", None)
    return data


# ---------- knowledge base ----------

def entries(ref_dir):
    out = []
    for p in sorted(Path(ref_dir).glob("*.md")):
        if p.name == "INDEX.md":
            continue
        meta, body = parse_frontmatter(read_text(p))
        out.append((p, meta, body))
    return out


def index_text(skill_name, ref_dir):
    lines = ["# %s references" % skill_name, "",
             "Generated by `cine.py kb index`; do not hand-edit. Open one entry with "
             "`python scripts/cine.py kb show <slug> --section <name>` (sections: Rules, Numbers, "
             "Vocabulary, Pitfalls, Verify, Notes).", ""]
    for p, meta, _ in entries(ref_dir):
        lines.append("- `%s`: %s" % (meta.get("slug", p.stem), meta.get("summary", "(no summary)")))
    return "\n".join(lines) + "\n"


def kb_search(ctx, words):
    terms = [w.lower() for w in words]
    hits, seen = [], set()
    for d in ctx.ref_dirs:
        for p, meta, body in entries(d):
            if p.name in seen:  # the same vocab copy ships in several skills
                continue
            seen.add(p.name)
            head = " ".join([meta.get("title", ""), meta.get("summary", ""), " ".join(meta.get("tags", []))]).lower()
            score = sum(3 * head.count(t) + body.lower().count(t) for t in terms)
            if score:
                hits.append((score, meta.get("slug", p.stem), d.parent.name, meta.get("summary", "")))
    hits.sort(key=lambda h: (-h[0], h[1]))
    return hits


def kb_find(ctx, slug):
    for d in ctx.ref_dirs:
        p = d / ("%s.md" % slug)
        if p.is_file():
            return p
    return None


def cmd_kb(ctx, a):
    if a.cmd == "index":
        for name, d in ctx.index_targets:
            write_text(d / "INDEX.md", index_text(name, d))
            print("wrote %s" % (d / "INDEX.md"))
        return 0
    if a.cmd == "search":
        hits = kb_search(ctx, a.words)
        for score, slug, skill, summary in hits[:a.limit]:
            print("%s (%s): %s" % (slug, skill, summary))
        if not hits:
            print("no entry matches; try fewer or broader words")
        return 0 if hits else 1
    if a.cmd == "show":
        p = kb_find(ctx, a.slug)
        if not p:
            print("no entry '%s'; run `kb search`" % a.slug, file=sys.stderr)
            return 1
        meta, body = parse_frontmatter(read_text(p))
        if a.section:
            secs = split_sections(body)
            if a.section not in secs:
                print("no section '%s' in %s; it has: %s" % (a.section, a.slug, ", ".join(secs)), file=sys.stderr)
                return 1
            print("## %s\n\n%s" % (a.section, secs[a.section]))
        else:
            print(body.strip())
        print("\n(last_checked %s; sources: %s)" % (meta.get("last_checked", "?"), "; ".join(meta.get("sources", []))))
        return 0
    return 2


# ---------- projects and cards ----------

class Project:
    def __init__(self, root, overrides=None, style=None):
        self.root = Path(root)
        b = self.root / "bibles"
        # --style FILE: try a look on the whole film without editing bibles/style.json
        self.style = json.loads(read_text(style or b / "style.json"))
        self.characters = json.loads(read_text(b / "characters.json"))
        self.locations = json.loads(read_text(b / "locations.json"))
        self.scenes = json.loads(read_text(b / "scenes.json"))
        pf = b / "props.json"
        self.props_bible = json.loads(read_text(pf)) if pf.is_file() else None
        vf = b / "voices.json"
        self.voices_bible = json.loads(read_text(vf)) if vf.is_file() else None
        self.card_files = sorted((self.root / "cards").glob("*.json"))
        self.cards = [json.loads(read_text(p)) for p in self.card_files]
        for f in overrides or []:
            # --with FILE: the card in FILE replaces the project card with the same id
            new = json.loads(read_text(f))
            self.cards = [c for c in self.cards if c.get("id") != new.get("id")] + [new]
        self.cards.sort(key=lambda c: c.get("order", 0))
        self.chars = bible_entries(self.characters, "characters", "id", "characters.json", "character-bible")
        # how names and invented words are said: respelled inside spoken lines only (library test, 2026-10-07)
        self.pronounce = self.characters.get("pronounce", {})
        self.locs = bible_entries(self.locations, "locations", "id", "locations.json", "location-bible")
        self.scene_map = bible_entries(self.scenes, "scenes", "id", "scenes.json", "scene-axis-bible")
        self.props = bible_entries(self.props_bible or {}, "props", "name", "props.json", "prop-bible")
        self.voices = bible_entries(self.voices_bible or {"voices": []}, "voices", "character", "voices.json", "voice-bible")


def bible_entries(doc, key, idkey, fname, schema):
    """{entry[idkey]: entry} from a bible; a bible in another shape stops with what to fix, not a traceback."""
    items = doc.get(key) if isinstance(doc, dict) else None
    if not isinstance(items, list) or not all(isinstance(x, dict) and idkey in x for x in items):
        raise SystemExit("bibles/%s: want {\"%s\": [{\"%s\": ...}, ...]}; see scripts/schemas/%s.schema.json"
                         % (fname, key, idkey, schema))
    return {x[idkey]: x for x in items}


MM_RANGE = re.compile(r"(\d+)\s*-\s*(\d+)\s*mm")


def lens_range(text):
    """(shortest, longest) focal length named by a lens family string, or None."""
    r = [(int(a), int(b)) for a, b in MM_RANGE.findall(text or "")]
    return (min(a for a, _ in r), max(b for _, b in r)) if r else None


def aspect_value(s):
    w, h = s.split(":")
    return float(w) / float(h)


def frame_words(st):
    """The composition sentence for a frame aspect other than the rendered one, else ''."""
    fa = st.get("frame_aspect")
    if not fa:
        return ""
    frame, render = aspect_value(fa), aspect_value(st["aspect_ratio"])
    if abs(frame - render) < 0.01:
        return ""
    if frame > render:
        return "Composed for a %s widescreen crop, heads and action inside the middle %d%% of the frame height." % (fa, round(100 * render / frame))
    return "Composed for a %s crop, the subject inside the middle %d%% of the frame width." % (fa, round(100 * frame / render))


def wardrobe_for(char, scene_id):
    w = char.get("wardrobe", {})
    return w.get(scene_id, w.get("default", ""))


def validate_project(ctx, p):
    errs = []
    for name, data in [("style-bible", p.style), ("character-bible", p.characters),
                       ("location-bible", p.locations), ("scene-axis-bible", p.scenes)]:
        errs += ["bibles/%s: %s" % (name, e) for e in validate(data, load_schema(ctx, name))]
    if p.props_bible is not None:
        errs += ["bibles/prop-bible: %s" % e for e in validate(p.props_bible, load_schema(ctx, "prop-bible"))]
    if p.voices_bible is not None:
        errs += ["bibles/voice-bible: %s" % e for e in validate(p.voices_bible, load_schema(ctx, "voice-bible"))]
        errs += voice_bible_errors(p)
    card_schema = load_schema(ctx, "shot-card")
    seen_ids, seen_orders = set(), set()
    for path, card in zip(p.card_files, [json.loads(read_text(f)) for f in p.card_files]):
        tag = "cards/%s" % path.name
        errs += ["%s: %s" % (tag, e) for e in validate(card, card_schema)]
        if "TODO" in json.dumps(card):
            errs.append("%s: still holds TODO" % tag)
        cid, order = card.get("id"), card.get("order")
        if cid in seen_ids:
            errs.append("%s: duplicate id %s" % (tag, cid))
        if order in seen_orders:
            errs.append("%s: duplicate order %s" % (tag, order))
        seen_ids.add(cid)
        seen_orders.add(order)
        if card.get("scene") not in p.scene_map:
            errs.append("%s: scene '%s' is not in scenes.json" % (tag, card.get("scene")))
        for m in card.get("cast", []):
            if m.get("id") not in p.chars:
                errs.append("%s: cast '%s' is not in characters.json" % (tag, m.get("id")))
        for d in card.get("dialogue", []):
            if d.get("character") not in p.chars:
                errs.append("%s: speaker '%s' is not in characters.json" % (tag, d.get("character")))
    for s in p.scenes.get("scenes", []):
        if s.get("location") not in p.locs:
            errs.append("bibles/scenes.json: scene %s location '%s' is not in locations.json" % (s.get("id"), s.get("location")))
    return errs


def new_card(p, cid, scene, cast_ids, order=None):
    if scene not in p.scene_map:
        raise SystemExit("scene '%s' is not in scenes.json" % scene)
    cast = []
    for c in cast_ids:
        if c not in p.chars:
            raise SystemExit("character '%s' is not in characters.json" % c)
        ch = p.chars[c]
        cast.append({"id": c, "identity": ch["identity"], "wardrobe": wardrobe_for(ch, scene)})
    return {
        "id": cid, "scene": scene,
        "order": order or (max([c.get("order", 0) for c in p.cards] or [0]) + 1),
        "duration_s": 4,
        "beat": "TODO: what this shot tells the audience",
        "camera": {"size": "MS", "angle": "eye-level", "azimuth_deg": 90, "move": "static", "lens_mm": 35, "side": "A", "framing": "single"},
        "cast": cast,
        "action": "TODO: one action, present tense",
        "time_of_day": p.scene_map[scene]["time_of_day"],
    }


def resolution_size(resolution, aspect):
    short = {"480p": 480, "720p": 720, "1080p": 1080, "1440p": 1440, "4k": 2160, "2160p": 2160}.get(resolution.lower())
    if short is None:
        raise SystemExit("unknown resolution '%s'" % resolution)
    a, b = (float(x) for x in aspect.split(":"))
    long_side = int(round(short * max(a, b) / min(a, b) / 2.0)) * 2
    return (long_side, short) if a >= b else (short, long_side)


def film_json(p, xfade=0.16, prof=None):
    """One shot per card, or with prof one shot per --sequence generation (name = the compile label, so
    `compile --sequence --out <film dir>` writes the <name>.txt prompts the pipeline reads)."""
    st = p.style
    w, h = resolution_size(st["resolution"], st["aspect_ratio"])
    fps = st["fps"]
    if prof:
        w, h = model_size(prof, st["resolution"], st["aspect_ratio"])
    refs = list(st.get("refs", []))
    for ch in p.characters.get("characters", []):
        for r in ch.get("refs", []):
            if r not in refs:
                refs.append(r)
    shots = []
    if prof:
        names = dict(DEFAULT_PARAMS, **prof.get("param_names", {}))
        by_id = {c["id"]: c for c in p.cards}
        for label, _text, params, _warn, info in compile_cards(p, p.cards, prof, sequence=True):
            first = by_id[label.split("+")[0]]
            frames = params.get(names.get("frames") or "", int(round(info["seconds"] * fps)))
            shot = {"name": label, "seed": first.get("seed", first["order"]), "length": frames}
            if params.get(names.get("refs") or ""):
                shot["refs"] = params[names["refs"]]
            shots.append(shot)
        refs = []
    else:
        for c in p.cards:
            shot = {"name": "shot_%s" % c["id"], "seed": c.get("seed", c["order"]), "length": int(round(c["duration_s"] * fps))}
            if c.get("refs"):
                shot["refs"] = c["refs"]
            shots.append(shot)
    name = re.sub(r"[^a-z0-9]+", "_", st["title"].lower()).strip("_")
    out = {"name": name, "target_seconds": st.get("target_seconds", sum(c["duration_s"] for c in p.cards)),
           "width": w, "height": h}
    if refs:
        out["refs"] = refs
    out["seam_audio_xfade"] = xfade
    out["shots"] = shots
    return out


def cmd_cards(ctx, a):
    p = Project(a.project, style=getattr(a, "style", None))
    if a.cmd == "validate":
        errs = validate_project(ctx, p)
        for e in errs:
            print("ERROR %s" % e)
        print("cards validate: %d cards, %d errors" % (len(p.cards), len(errs)))
        return 1 if errs else 0
    if a.cmd == "new":
        card = new_card(p, a.id, a.scene, [c for c in (a.cast or "").split(",") if c], a.order)
        out = p.root / "cards" / ("%s.json" % a.id)
        if out.exists():
            raise SystemExit("%s exists" % out)
        write_text(out, json.dumps(card, indent=2, ensure_ascii=False) + "\n")
        print("wrote %s (fill every TODO, then run cards validate)" % out)
        return 0
    if a.cmd == "list":
        print("| # | Slate | Size | Angle | Az | Move | Lens | Cast | Action | s |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for c in p.cards:
            cam = c.get("camera", {})
            cast = ", ".join(p.chars.get(m["id"], {}).get("name", m["id"]) for m in c.get("cast", [])) or c.get("subject", "")
            print("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %g |" % (
                c.get("order"), c.get("id"), cam.get("size"), cam.get("angle"), cam.get("azimuth_deg", ""), cam.get("move"),
                cam.get("lens_mm", ""), cast, c.get("action", "").replace("|", "/"), c.get("duration_s", 0)))
        scenes = len({c.get("scene") for c in p.cards})
        print("shot list: %d shots, %d scene(s), %gs" % (len(p.cards), scenes, sum(c.get("duration_s", 0) for c in p.cards)))
        return 0
    if a.cmd == "export":
        if not a.film_json:
            raise SystemExit("choose an export format: --film-json")
        prof = None
        if a.sequence:
            if not a.model:
                raise SystemExit("--sequence needs --model (the frame grid and the shot grouping come from the model card)")
            _path, _meta, prof = find_model_card(ctx, a.model)
            if not prof:
                raise SystemExit("no model card for '%s'" % a.model)
        text = json.dumps(film_json(p, a.xfade, prof), indent=2, ensure_ascii=False) + "\n"
        if a.out:
            write_text(a.out, text)
            print("wrote %s" % a.out)
        else:
            sys.stdout.write(text)
        return 0
    return 2


# ---------- continuity diff ----------

def continuity_diff(p):
    """Every card against the bibles and against the previous card in its scene."""
    issues = []

    def add(level, card, code, msg):
        issues.append({"level": level, "card": card.get("id", "?"), "code": code, "message": msg})

    prev_by_scene = {}
    for card in p.cards:
        sc = p.scene_map.get(card.get("scene"))
        if not sc:
            add("error", card, "SCENE", "scene '%s' is not in scenes.json" % card.get("scene"))
            continue
        axis = sc.get("axis", {})
        cam = card.get("camera", {})
        side = cam.get("side", "A")
        flipped = side == "B"
        if flipped and not cam.get("crosses_axis"):
            add("error", card, "AXIS", "camera is on side B of the %s axis (%s): it crosses the line, so every left and right flips. "
                "Move it to side A, or set crosses_axis with a cross_reason (a neutral shot or a move seen on screen)." % (sc["id"], axis.get("line", "")))
        if cam.get("crosses_axis") and not cam.get("cross_reason"):
            add("error", card, "AXIS", "crosses_axis is set without a cross_reason")
        if card.get("time_of_day") and card["time_of_day"] != sc["time_of_day"]:
            add("error", card, "TIME", "time of day %s, scene %s is %s" % (card["time_of_day"], sc["id"], sc["time_of_day"]))
        sun = card.get("light", {}).get("sun")
        if sun and sc.get("sun") and sun != sc["sun"]:
            add("error", card, "SUN", "sun '%s' differs from the scene's '%s'" % (sun, sc["sun"]))
        walls = p.locs.get(sc.get("location"), {}).get("walls", {})
        if cam.get("faces") and cam["faces"] not in walls:
            add("error", card, "WALL", "camera faces '%s' but location %s has no such wall in locations.json walls (%s)" % (
                cam["faces"], sc.get("location"), ", ".join(sorted(walls)) or "none"))
        if cam.get("angle") == "dutch" and not p.style.get("allow_dutch"):
            add("warning", card, "STYLE", "dutch angle but the style bible does not allow it")
        lr = lens_range(p.style.get("lens_family"))
        if lr and cam.get("lens_mm") and not lr[0] <= cam["lens_mm"] <= lr[1]:
            add("warning", card, "LENS", "%gmm is outside the style's lens family (%s, %d-%dmm); change the lens or the family" % (
                cam["lens_mm"], p.style["lens_family"], lr[0], lr[1]))
        moves = p.style.get("allowed_moves")
        if moves and cam.get("move") and cam["move"] not in moves:
            add("warning", card, "MOVE", "%s is not one of the style's moves (%s)" % (cam["move"], ", ".join(moves)))
        positions = axis.get("positions", {})
        travel = axis.get("travel", {})
        allowed_props = set(sc.get("props", [])) | set(p.locs.get(sc.get("location"), {}).get("props", [])) | set(p.props)
        on_screen = []
        for m in card.get("cast", []):
            ch = p.chars.get(m.get("id"))
            if not ch:
                add("error", card, "CAST", "'%s' is not in characters.json" % m.get("id"))
                continue
            allowed_props |= set(ch.get("props", []))
            if m.get("identity") != ch["identity"]:
                add("error", card, "IDENTITY", "%s identity is not the bible's string verbatim; copy it exactly" % ch["name"])
            want = wardrobe_for(ch, sc["id"])
            if "wardrobe" in m and m["wardrobe"] != want:
                add("error", card, "WARDROBE", "%s wears '%s', the bible says '%s' in scene %s" % (ch["name"], m["wardrobe"], want, sc["id"]))
            t = m.get("travel")
            if t in FLIP and travel.get(m["id"]) in FLIP:
                exp = FLIP[travel[m["id"]]] if flipped else travel[m["id"]]
                if t != exp:
                    add("error", card, "DIRECTION", "%s travels %s, screen direction for this scene from side %s is %s" % (ch["name"], t, side, exp))
            tgt, eye = m.get("looks_at"), m.get("eyeline")
            if eye in FLIP and tgt in positions and m["id"] in positions and positions[tgt] != positions[m["id"]]:
                exp = "frame-right" if POS_INDEX[positions[m["id"]]] < POS_INDEX[positions[tgt]] else "frame-left"
                exp = FLIP[exp] if flipped else exp
                if eye != exp:
                    tname = p.chars.get(tgt, {}).get("name", tgt)
                    add("error", card, "EYELINE", "%s looks %s at %s; from side %s the eyeline must be %s" % (ch["name"], eye, tname, side, exp))
            if eye == "camera" and cam.get("framing") != "pov":
                add("warning", card, "EYELINE", "%s looks into the lens outside a POV shot" % ch["name"])
            if m.get("position") in POS_INDEX and m["id"] in positions:
                on_screen.append(m)
            for key in ("holding", "holding_end"):
                if m.get(key) and m[key] not in allowed_props:
                    add("warning", card, "PROP", "%s holds '%s', which no bible lists" % (ch["name"], m[key]))
                elif m.get(key) and p.props and m[key] not in p.props:
                    add("warning", card, "PROP", "%s holds '%s', which has no description in bibles/props.json, so the model invents its look" % (ch["name"], m[key]))
            st_name = m.get("holding_state")
            if st_name and st_name not in [s["name"] for s in p.props.get(m.get("holding"), {}).get("states", [])]:
                add("error", card, "PROP", "%s holds '%s' in state '%s', which props.json does not list" % (ch["name"], m.get("holding"), st_name))
        for x in card.get("props", []):
            if x["name"] not in p.props:
                add("warning", card, "PROP", "features '%s', which has no description in bibles/props.json, so the model invents its look" % x["name"])
            elif x.get("state") and x["state"] not in [s["name"] for s in p.props[x["name"]].get("states", [])]:
                add("error", card, "PROP", "features '%s' in state '%s', which props.json does not list" % (x["name"], x["state"]))
            elif not prop_look(p, x["name"], x.get("state")).get("refs") and not p.props[x["name"]].get("refs"):
                add("warning", card, "PROP", "features '%s' with no prop sheet refs; make one (cinewright-design prop-sheets)" % x["name"])
        for i, a in enumerate(on_screen):
            for b in on_screen[i + 1:]:
                want = POS_INDEX[positions[a["id"]]] - POS_INDEX[positions[b["id"]]]
                got = POS_INDEX[a["position"]] - POS_INDEX[b["position"]]
                if flipped:
                    want = -want
                if want and got and (want > 0) != (got > 0):
                    add("error", card, "POSITION", "%s and %s have swapped sides of the frame" % (a["id"], b["id"]))
        action = card.get("action", "")
        if len(re.findall(r"[.!?](\s|$)", action.strip())) > 1 or re.search(r"\b(then|and then|after that)\b", action):
            add("warning", card, "ONE-ACTION", "the action reads as more than one action; split the card")
        words = sum(len(d.get("line", "").split()) for d in card.get("dialogue", []))
        room = SPEECH_WPS * (card.get("duration_s", 0) - SPEECH_LEAD_S)
        if words > room:
            add("warning", card, "DIALOGUE", "%d words of dialogue in %ss; at %.1f words a second the shot holds %d: cut the line or lengthen the shot" % (
                words, card.get("duration_s"), SPEECH_WPS, int(room)))
        in_shot = [m.get("id") for m in card.get("cast", [])]
        talkers = []
        for d in card.get("dialogue", []):
            who = d.get("character")
            if who not in talkers:
                talkers.append(who)
            if who not in in_shot:
                add("warning", card, "OFFSCREEN", "%s speaks but is not in the shot; video models give a line to a face they can see. Put %s in the shot "
                    "or cut to them for the line; kept off screen, compile writes a voiceover where the model has one, else lay the line in the mix" % (who, who))
            tone = d.get("tone", "").strip()
            if SPEECH_VERBS.match(tone):
                add("warning", card, "TONE", "tone '%s' starts with a verb and is pasted after 'says'; write it as an adverb or phrase ('quietly', 'under his breath')" % tone)
            for name in sorted({w for c in p.chars.values() for w in re.findall(r"[A-Z][\w'-]+", c.get("name", ""))}):
                if len(name) > 2 and re.search(r"(?<!\w)%s(?!\w)" % re.escape(name), d.get("line", "")) and name not in p.pronounce:
                    add("warning", card, "PRONOUNCE", "'%s' is spoken and the voice model guesses how to say a name; add it to characters.json pronounce "
                        "(a respelling, or the name itself when any reading is fine)" % name)
        if len(talkers) > 1:
            add("warning", card, "SPEAKERS", "%d speakers in one shot (%s); lines from two people in one clip come out in the wrong mouth: "
                "one speaker per card, cut to the listener for the answer" % (len(talkers), ", ".join(talkers)))
        hard = HARD_SUBJECT.search("%s %s" % (action, card.get("subject", "")))
        if hard and cam.get("size") in ("EWS", "WS"):
            add("warning", card, "HARD-SUBJECT", "'%s' in a %s: many small figures come out with broken legs and clones; frame 1-5 of them large and side-on, "
                "the mass as background dust (cinewright-movement, entry hard-subjects)" % (hard.group(0), SIZE_WORDS[cam["size"]]))
        prev = prev_by_scene.get(sc["id"])
        if prev:
            pcast = {m["id"]: m for m in prev.get("cast", [])}
            for m in card.get("cast", []):
                pm = pcast.get(m.get("id"))
                if pm and "holding" in m and ("holding" in pm or "holding_end" in pm):
                    before = pm.get("holding_end", pm.get("holding"))
                    if before != m["holding"]:
                        add("error", card, "PROP", "%s ends %s holding %s but starts %s holding %s" % (
                            m["id"], prev["id"], before or "nothing", card["id"], m["holding"] or "nothing"))
            same = sorted(m.get("id") for m in card.get("cast", [])) == sorted(pcast) and (
                card.get("cast") or card.get("subject") == prev.get("subject"))
            pc = prev.get("camera", {})
            if same and cam.get("size") in SIZES and pc.get("size") in SIZES:
                step = abs(SIZES.index(cam["size"]) - SIZES.index(pc["size"]))
                az, paz = cam.get("azimuth_deg"), pc.get("azimuth_deg")
                if step < 2:
                    if az is None or paz is None:
                        add("warning", card, "30-DEGREE", "same subject as %s with %d size step(s); add azimuth_deg to both to check the 30-degree rule" % (prev["id"], step))
                    elif abs(az - paz) < 30:
                        add("error", card, "30-DEGREE", "jump cut from %s: same subject, %d size step(s) and %d degrees; change size by 2+ steps or angle by 30+ degrees" % (
                            prev["id"], step, abs(az - paz)))
        prev_by_scene[sc["id"]] = card
    return issues


def cmd_continuity(ctx, a):
    p = Project(a.project, a.with_card, a.style)
    issues = continuity_diff(p)
    errors = [i for i in issues if i["level"] == "error"]
    if a.json:
        print(json.dumps({"cards": len(p.cards), "issues": issues}, indent=2))
    else:
        for i in issues:
            print("%s %s %s: %s" % (i["level"].upper(), i["card"], i["code"], i["message"]))
        print("continuity diff: %d cards, %d errors, %d warnings" % (len(p.cards), len(errors), len(issues) - len(errors)))
    return 1 if errors else 0


# ---------- compile ----------

def find_model_card(ctx, model):
    for d in ctx.model_dirs:
        for p, meta, body in entries(d):
            if meta.get("model") == model:
                return p, meta, compile_block(body)
    return None, None, None


def _sentence(s):
    s = s.strip()
    return s if not s or s[-1] in ".!?\"'>}" else s + "."


def _cap(s):
    return s[:1].upper() + s[1:]


def _low(s):
    return s[:1].lower() + s[1:]


def _and(names):
    return names[0] if len(names) == 1 else "%s and %s" % (", ".join(names[:-1]), names[-1])


def spoken(p, line):
    """The line as the voice should say it: each word in characters.json `pronounce` swapped for its respelling."""
    if not p.pronounce:
        return line
    pat = r"(?<!\w)(%s)(?!\w)" % "|".join(re.escape(w) for w in sorted(p.pronounce, key=len, reverse=True))
    return re.sub(pat, lambda m: p.pronounce[m.group(1)], line)


# Delivery notes are pasted after "says", so a tone that starts with a speech verb doubles it ("says mutters").
SPEECH_VERBS = re.compile(r"^(says|said|mutters|murmurs|whispers|shouts|yells|screams|cries|calls|snaps|growls|hisses|roars|sighs|laughs|sobs|"
                          r"barks|snarls|asks|replies|answers|tells|bellows|groans|moans|grumbles|stammers)\b", re.I)


# Moves written as a sentence of type + amplitude + speed (Compile "move_style": "sentence").
MOVE_SENTENCES = {
    "static": "The camera stays static", "pan-left": "The camera pans left", "pan-right": "The camera pans right",
    "tilt-up": "The camera tilts up", "tilt-down": "The camera tilts down",
    "dolly-in": "The camera pushes in", "dolly-out": "The camera pulls out",
    "truck-left": "The camera trucks left", "truck-right": "The camera trucks right",
    "track": "The camera tracks the subject", "crane-up": "The camera pedestals up",
    "crane-down": "The camera pedestals down", "handheld": "The camera shakes",
    "zoom-in": "The camera zooms in", "zoom-out": "The camera zooms out",
}
# Generic parameter names; a Compile block's "param_names" renames them, null drops one.
DEFAULT_PARAMS = {"model": "model", "duration": "durationSeconds", "aspect": "aspectRatio", "resolution": "resolution",
                  "seed": "seed", "refs": "referenceImages", "negative": "negativePrompt",
                  "width": "width", "height": "height", "frames": "frames", "fps": "fps"}


def card_props(c):
    """(name, state) for every prop a card holds or features, in order."""
    out = []
    for m in c.get("cast", []):
        for key in ("holding", "holding_end"):
            if m.get(key):
                out.append((m[key], m.get("holding_state") if key == "holding" else None))
    out += [(x["name"], x.get("state")) for x in c.get("props", [])]
    return out


def prop_look(p, name, state=None):
    """The bible entry for a prop, or for one of its states when the card names one."""
    pr = p.props.get(name, {})
    for s in pr.get("states", []):
        if s["name"] == state:
            return s
    return pr


def generation_refs(p, cards, prof):
    """Ordered reference list for one generation (characters, props, sets, card refs) and the tag text
    per character id and per "prop:<name>"."""
    refs, tags = [], {}

    def add(rs):
        for r in rs:
            if r not in refs:
                refs.append(r)
    for c in cards:
        for m in c.get("cast", []):
            add(p.chars[m["id"]].get("refs", []))
        # a prop sheet goes with every shot that shows the prop: without it the model redraws the object
        # each shot (pre-production gaps, 2026-10-09)
        for name, state in card_props(c):
            look = prop_look(p, name, state)
            add(look.get("refs") or p.props.get(name, {}).get("refs", []))
        add(p.locs[p.scene_map[c["scene"]]["location"]].get("refs", []))
        add(c.get("refs", []))
    if prof.get("ref_tag"):
        for cid, ch in p.chars.items():
            mine = [refs.index(r) + 1 for r in ch.get("refs", []) if r in refs]
            if mine:
                tags[cid] = " ".join(prof["ref_tag"].format(n=n, n0=n - 1, name=ch["name"]) for n in mine)
        for name, pr in p.props.items():
            for look in [pr] + pr.get("states", []):
                mine = [refs.index(r) + 1 for r in look.get("refs", []) if r in refs]
                if mine:
                    tags.setdefault("prop:" + name, " ".join(prof["ref_tag"].format(n=n, n0=n - 1, name=name) for n in mine))
    return refs, tags


def prop_words(p, name, state=None, tags=None):
    """A prop as the prop bible's verbatim description (of the state when given), else 'the <name>',
    with the prop sheet's ref tag when the model takes tags."""
    d = prop_look(p, name, state).get("description")
    words = d.rstrip(".") if d else "the %s" % name
    tag = (tags or {}).get("prop:" + name)
    return "%s %s" % (words, tag) if tag else words


def card_parts(p, card, prof, tags=None, speakers=None):
    sc = p.scene_map[card["scene"]]
    loc = p.locs[sc["location"]]
    cam = card["camera"]
    flipped = cam.get("side") == "B"
    tags, speakers = tags or {}, speakers or {}
    sentence_moves = prof.get("move_style") == "sentence"
    parts = {}
    lens = ", %smm lens" % int(cam["lens_mm"]) if cam.get("lens_mm") else ""
    move = "" if sentence_moves else ", " + MOVE_WORDS[cam["move"]]
    parts["camera"] = _sentence("%s, %s%s%s" % (_cap(SIZE_WORDS[cam["size"]]), ANGLE_WORDS[cam["angle"]], lens, move))
    if sentence_moves:
        suffix = "" if cam["move"] == "static" else prof.get("move_suffix", "")
        parts["move"] = _sentence(MOVE_SENTENCES[cam["move"]] + suffix)
    subj = []
    for m in card.get("cast", []):
        ch = p.chars[m["id"]]
        who = ch["name"]
        if m["id"] in tags:
            who = tags[m["id"]] if prof.get("ref_replaces_name") else "%s %s" % (who, tags[m["id"]])
        line = "%s, %s, wearing %s" % (who, ch["identity"].rstrip("."), wardrobe_for(ch, sc["id"]).rstrip("."))
        if m.get("position"):
            line += ", %s" % POSITION_WORDS[m["position"]]
        if m.get("holding"):
            line += ", holding %s" % prop_words(p, m["holding"], m.get("holding_state"), tags)
        subj.append(_sentence(line))
    for x in card.get("props", []):
        subj.append(_sentence(_cap("%s%s" % (prop_words(p, x["name"], x.get("state"), tags), ", " + x["where"] if x.get("where") else ""))))
    if card.get("subject"):
        subj.append(_sentence(_cap(card["subject"])))
    parts["subject"] = " ".join(subj)
    # --sequence: people are introduced once in the header, so each shot restates where they stand and what they hold
    stage = []
    for m in card.get("cast", []):
        bits = [POSITION_WORDS[m["position"]]] if m.get("position") else []
        if m.get("holding"):
            bits.append("holding %s" % prop_words(p, m["holding"], m.get("holding_state"), tags))
        if bits:
            stage.append(_sentence("%s is %s" % (p.chars[m["id"]]["name"], ", ".join(bits))))
    parts["staging"] = " ".join(stage)
    act = [_sentence(card["action"])]
    for m in card.get("cast", []):
        name = p.chars[m["id"]]["name"]
        # only the card's own travel: the scene's travel is what continuity checks against, and stating it
        # on every card put a close-up of a seated man "walking away from the camera" (library test, 2026-10-06)
        t = m.get("travel")
        if t in TRAVEL_WORDS:
            act.append(_sentence("%s is %s" % (name, TRAVEL_WORDS[t])))
        if m.get("eyeline") in EYELINE_WORDS:
            target = m.get("looks_at")
            if target in p.chars:
                target = p.chars[target]["name"]
            elif target and not re.match(r"(the|a|an|his|her|their) ", target, re.I):
                target = "the %s" % target
            target = target or ""
            on = ", at %s" % target if target and m["eyeline"] != "camera" else ""
            act.append(_sentence("%s is %s%s" % (name, EYELINE_WORDS[m["eyeline"]], on)))
    parts["action"] = " ".join(act)
    tod = card.get("time_of_day", sc["time_of_day"]).replace("-", " ")
    where = loc["description"].rstrip(".")
    # the wall the camera faces: a whole-room description names the hero wall, and those words
    # beat "looking north", so a reverse came back as the establishing view (set field test, 2026-10-07)
    if cam.get("faces") in loc.get("walls", {}):
        where = "%s. %s" % (where, _cap(loc["walls"][cam["faces"]].rstrip(".")))
    parts["context"] = _sentence(_cap("%s, %s" % (where, tod)))
    light = card.get("light", {})
    lt = []
    if sc.get("sun"):
        lt.append(sc["sun"])
    if light.get("key_side"):
        lt.append("%s key light from %s" % (light.get("quality", "soft"), light["key_side"].replace("-", " ")))
    if light.get("motivation"):
        lt.append(light["motivation"])
    parts["light"] = _sentence(_cap(", ".join(lt))) if lt else ""
    # --sequence: the scene's sun goes in the shared header, each shot keeps its own key side
    parts["sun"] = _sentence(_cap(sc["sun"])) if sc.get("sun") else ""
    parts["key"] = _sentence(_cap(", ".join(lt[1:] if sc.get("sun") else lt))) if lt[1 if sc.get("sun") else 0:] else ""
    # look, then the style's lighting and frame: said once per generation, identical in every shot
    parts["style"] = " ".join(_sentence(x) for x in (p.style["look"], p.style.get("lighting", ""), frame_words(p.style)) if x)
    lines = []
    if prof["dialogue"]:
        in_shot = [m["id"] for m in card.get("cast", [])]
        for d in card.get("dialogue", []):
            ch = p.chars[d["character"]]
            tone = d.get("tone")
            # a speaker who is not in the shot: models lip-sync a face they can see, so a line written as plain
            # "says" came out of the only visible mouth (library test, 2026-10-07). compile_cards warns either way.
            off = d["character"] not in in_shot
            tpl = prof.get("dialogue_offscreen") if off else prof["dialogue"]
            if not tpl:
                continue
            quiet = [p.chars[i]["name"] for i in in_shot if i != d["character"]]
            lines.append(_sentence(tpl.format(
                name=ch["name"], line=spoken(p, d["line"]), tone=tone or "", tone_clause=(" " + tone) if tone else "",
                tone_paren=(" (%s)" % tone) if tone else "", speaker=speakers.get(d["character"], "S1"),
                voice_clause=(" with a %s voice" % ch["voice"]) if ch.get("voice") else "",
                silent_clause=prof["dialogue_silent"].format(names=_and(quiet)) if quiet and prof.get("dialogue_silent") else "")))
    parts["dialogue"] = " ".join(lines)
    parts["sound"] = _sentence(_cap(prof["audio"].format(sound=card["sound"].rstrip(".")))) if card.get("sound") and prof["audio"] else ""
    parts["audio"] = " ".join(x for x in (parts["dialogue"], parts["sound"]) if x)
    return parts


def snap_duration(seconds, allowed):
    up = [d for d in sorted(allowed) if d >= seconds]
    return up[0] if up else max(allowed)


def plan_length(total, prof):
    """Rendered length in seconds and frame count (None unless the model has a frame grid)."""
    fr = prof.get("frames")
    if not fr:
        return snap_duration(total, prof["durations_s"]), None
    lo, hi = min(prof["durations_s"]), max(prof["durations_s"])
    fps, step, off = fr["fps"], fr["step"], fr["offset"]
    want = min(max(total, lo), hi) * fps
    frames = int(max(0, math.ceil((want - off) / float(step)))) * step + off
    while frames / float(fps) > hi + 1e-9 and frames - step >= off:
        frames -= step
    return round(frames / float(fps), 3), frames


def model_size(prof, resolution, aspect):
    sizes = prof.get("sizes", {}).get(resolution)
    if sizes is not None:
        if aspect not in sizes:
            raise SystemExit("%s has no %s size at %s (%s)" % (prof["model_id"], aspect, resolution, ", ".join(sizes)))
        w, h = (int(x) for x in sizes[aspect].split("x"))
        return w, h
    w, h = resolution_size(resolution, aspect)
    m = prof.get("size_multiple", 1)
    return w // m * m, h // m * m


def _stamp(tpl, n, start, end):
    mins, secs = divmod(start, 60)
    return tpl.format(n=n, start="%02d:%02d" % divmod(int(round(start)), 60), end="%02d:%02d" % divmod(int(round(end)), 60),
                      start_s="%g" % round(start, 3), end_s="%g" % round(end, 3), start_ms="%02d:%06.3f" % (mins, secs))


def compile_cards(p, cards, prof, sequence=False, resolution=None, join=False):
    """Return a list of (label, prompt, params, warnings, info); info holds seconds and est_usd."""
    out = []
    st = p.style
    res = resolution or st["resolution"]
    problems = []
    if st["aspect_ratio"] not in prof["aspect_ratios"]:
        problems.append("aspect %s not offered (%s)" % (st["aspect_ratio"], ", ".join(prof["aspect_ratios"])))
    if res not in prof["resolutions"]:
        problems.append("resolution %s not offered (%s); pick one with --resolution or change the style bible" % (res, ", ".join(prof["resolutions"])))
    if problems:
        raise SystemExit("style bible does not fit %s: %s" % (prof["model_id"], "; ".join(problems)))
    names = dict(DEFAULT_PARAMS, **prof.get("param_names", {}))
    groups = [[c] for c in cards]
    if sequence:
        groups, cur = [], []
        limit = max(prof["durations_s"])
        for c in cards:
            new_scene = c["scene"] != cur[-1]["scene"] if cur else False
            if cur and ((new_scene and not join) or sum(x["duration_s"] for x in cur) + c["duration_s"] > limit):
                groups.append(cur)
                cur = []
            cur.append(c)
        if cur:
            groups.append(cur)
    for g in groups:
        warnings = []
        refs, tags = generation_refs(p, g, prof)
        speakers = {}
        for c in g:
            for d in c.get("dialogue", []):
                speakers.setdefault(d["character"], "S%d" % (len(speakers) + 1))
        sound = []
        if len(g) == 1:
            parts = card_parts(p, g[0], prof, tags, speakers)
            main = " ".join(parts[k] for k in prof["order"] if parts.get(k))
            if parts["sound"]:
                sound.append(parts["sound"])
            total = g[0]["duration_s"]
            shots = [total]
        elif "timestamp" not in prof:
            raise SystemExit("%s has no multi-shot syntax; compile without --sequence" % prof["model_id"])
        else:
            first = card_parts(p, g[0], prof, tags, speakers)
            people = []
            for c in g:
                for m in c.get("cast", []):
                    ch = p.chars[m["id"]]
                    who = ch["name"]
                    if m["id"] in tags:
                        who = tags[m["id"]] if prof.get("ref_replaces_name") else "%s %s" % (who, tags[m["id"]])
                    line = _sentence("%s, %s, wearing %s" % (who, ch["identity"].rstrip("."), wardrobe_for(ch, c["scene"]).rstrip(".")))
                    if line not in people:
                        people.append(line)
            pool = dict(first, people=" ".join(people))
            head = " ".join(pool[k] for k in prof.get("sequence_head", ["people", "context", "sun", "style"]) if pool.get(k))
            blocks, t = [], 0.0
            for i, c in enumerate(g):
                parts = card_parts(p, c, prof, tags, speakers)
                if parts["sound"]:
                    sound.append(parts["sound"])
                start, end = t, t + c["duration_s"]
                tpl = prof["timestamp"] if i == 0 else prof.get("timestamp_next", prof["timestamp"])
                stamp = _stamp(tpl, i + 1, start, end)
                body = " ".join(parts[k] for k in prof.get("sequence_block", ["camera", "staging", "action", "key", "audio"]) if parts.get(k))
                prev_loc = p.scene_map[g[i - 1]["scene"]]["location"] if i else None
                if i and p.scene_map[c["scene"]]["location"] != prev_loc:
                    # the head only describes the first card's place: say the new place where the sequence moves
                    body = " ".join(x for x in (parts.get("context"), parts.get("sun"), body) if x)
                if stamp and stamp.rstrip()[-1:] not in ".:]),":
                    body = _low(body)
                blocks.append(("%s %s" % (stamp, body)).strip())
                t = end
            if prof.get("sequence_join", "\n") == "\n":
                main = head + "\n" + "\n".join(blocks)
            else:
                main = " ".join([head] + blocks)
            total = t
            shots = [c["duration_s"] for c in g]
        if prof.get("prefix"):
            main = prof["prefix"] + " " + main
        if prof.get("single_shot") and len(g) == 1:
            main = prof["single_shot"] + " " + main
        if prof.get("negative_prompt") == "inline" and prof.get("negative_terms"):
            main = main + " " + prof["negative_terms"]
        music = []
        for c in g:
            if c.get("music") and _cap(_sentence(c["music"])) not in music:
                music.append(_cap(_sentence(c["music"])))
        if music and "{music}" not in prof.get("layout", "") and prof["audio"]:
            if prof.get("layout"):
                sound.append("Music: " + " ".join(music))  # no separate music slot: say it with the sound
            else:
                main = main + " Music: " + " ".join(music)
        elif music and not prof["audio"]:
            warnings.append("%s makes no sound: the music goes in the mix" % prof["model_id"])
        if prof.get("layout"):
            text = prof["layout"].format(main=main, sound=" ".join(sound) or prof.get("empty", "N/A"),
                                         music=" ".join(music) or prof.get("empty", "N/A"))
        else:
            text = main
        dur, frames = plan_length(total, prof)
        forced = prof.get("resolution_duration_s", {}).get(res)
        if refs and prof.get("reference_duration_s"):
            forced = prof["reference_duration_s"]
        if forced:
            dur = forced
        if total > max(prof["durations_s"]):
            warnings.append("planned %ss, %s renders at most %ss: split the card or cut it shorter" % (total, prof["model_id"], max(prof["durations_s"])))
        elif abs(dur - total) > 0.1:
            warnings.append("planned %ss, rendered at %ss: trim in the edit" % (total, dur))
        if refs and len(refs) > prof.get("max_reference_images", 0):
            warnings.append("%d reference images, %s takes %d" % (len(refs), prof["model_id"], prof.get("max_reference_images", 0)))
        if not prof["dialogue"] and any(c.get("dialogue") for c in g):
            warnings.append("%s makes no speech: record the dialogue and lay it in the mix" % prof["model_id"])
        elif prof["dialogue"]:
            for c in g:
                for d in c.get("dialogue", []):
                    if d["character"] in [m["id"] for m in c.get("cast", [])]:
                        continue
                    who = p.chars[d["character"]]["name"]
                    if prof.get("dialogue_offscreen"):
                        warnings.append("%s: %s speaks off screen, compiled as an off-screen voiceover; in QC check that no visible mouth says it, "
                                        "else lay the line in the mix" % (c["id"], who))
                    else:
                        warnings.append("%s: %s speaks off screen and %s has no voiceover syntax, so the line is left out of the prompt "
                                        "(the model would give it to a visible face): record it and lay it in the mix" % (c["id"], who, prof["model_id"]))
        if not prof["audio"] and any(c.get("sound") for c in g):
            warnings.append("%s makes no sound: the sound goes in the mix" % prof["model_id"])
        words = len(text.split())
        if words > prof["max_words"]:
            warnings.append("%d words, over the %d-word guide: shorten action or context, never the identity string" % (words, prof["max_words"]))
        if prof.get("max_chars") and len(text) > prof["max_chars"]:
            warnings.append("%d characters, the API limit is %d: shorten action or context, never the identity string" % (len(text), prof["max_chars"]))
        for c in g:
            for m in c.get("cast", []):
                if p.chars[m["id"]]["identity"] not in text:
                    raise SystemExit("compiler bug: identity of %s not verbatim in %s" % (m["id"], c["id"]))
                if m.get("holding") in p.props and prop_words(p, m["holding"], m.get("holding_state")) not in text:
                    raise SystemExit("compiler bug: prop '%s' not verbatim in %s" % (m["holding"], c["id"]))
            for x in c.get("props", []):
                # [1:]: a featured prop opens its sentence, so its first letter is capitalised
                if x["name"] in p.props and prop_words(p, x["name"], x.get("state"))[1:] not in text:
                    raise SystemExit("compiler bug: prop '%s' not verbatim in %s" % (x["name"], c["id"]))
        for key, want in (("lighting", st.get("lighting", "").rstrip(".")), ("frame_aspect", frame_words(st).rstrip("."))):
            if want and want not in text:
                raise SystemExit("compiler bug: style %s not verbatim in %s" % (key, "+".join(c["id"] for c in g)))
        params = {}

        def put(key, val):
            if names.get(key):
                params[names[key]] = val
        put("model", prof["model_id"])
        if frames is None:
            put("duration", prof["duration_format"].format(d=dur) if prof.get("duration_format") else dur)
        put("aspect", prof.get("aspect_values", {}).get(st["aspect_ratio"], st["aspect_ratio"]))
        put("resolution", res)
        if frames is not None or prof.get("sizes") or prof.get("size_multiple"):
            w, h = model_size(prof, res, st["aspect_ratio"])
            put("width", w)
            put("height", h)
        if frames is not None:
            put("frames", frames)
            put("fps", prof["frames"]["fps"])
        if len(g) > 1 and prof.get("shot_lengths"):
            params[prof["shot_lengths"]] = shots
        seeds = [c["seed"] for c in g if "seed" in c]
        if seeds and prof.get("seed"):
            put("seed", seeds[0])
        if refs:
            put("refs", refs)
        if prof.get("negative_prompt") == "field" and prof.get("negative_terms"):
            put("negative", prof["negative_terms"])
        rate = prof.get("usd_per_s", {}).get(res)
        info = {"seconds": dur, "est_usd": round(rate * dur, 2) if rate is not None else None}
        label = "+".join(c["id"] for c in g)
        out.append((label, text, params, warnings, info))
    return out


def cmd_compile(ctx, a):
    p = Project(a.project, style=a.style)
    path, meta, prof = find_model_card(ctx, a.model)
    if not prof:
        print("no model card for '%s'. Install cinewright-genvideo, or check `kb search %s`." % (a.model, a.model), file=sys.stderr)
        return 1
    if meta.get("status") in ("deprecated", "shut-down"):
        print("warning: %s is %s" % (meta.get("title"), meta.get("status")), file=sys.stderr)
    cards = [c for c in p.cards if not a.card or c["id"] in a.card]
    if not cards:
        print("no matching cards", file=sys.stderr)
        return 1
    results = compile_cards(p, cards, prof, a.sequence, a.resolution, getattr(a, "join", False))
    cost = 0.0
    for label, text, params, warnings, info in results:
        if a.out:
            out = Path(a.out)
            write_text(out / ("%s.txt" % label), text + "\n")
            write_text(out / ("%s.params.json" % label), json.dumps(params, indent=2, ensure_ascii=False) + "\n")
        price = "" if info["est_usd"] is None else "  est. $%.2f" % info["est_usd"]
        cost += info["est_usd"] or 0
        print("== %s  %s  %ss %s %s  %d words%s" % (label, prof["model_id"], info["seconds"], p.style["aspect_ratio"], a.resolution or p.style["resolution"], len(text.split()), price))
        if not a.out:
            print(text)
            print("params: %s" % json.dumps(params, ensure_ascii=False))
        for w in warnings:
            print("  warning: %s" % w)
    if a.out:
        print("wrote %d prompts to %s (model card %s, last_checked %s)" % (len(results), a.out, path.name, meta.get("last_checked")))
    if cost:
        print("est. $%.2f for one take of each (list price on %s; a render needs the user's go)" % (cost, meta.get("last_checked")))
    return 0


# ---------- qc: rendered takes against their cards ----------

# Rubric checks: (check, what to look at, question). The failure-code entries map codes to checks.
RUBRIC = [
    ("identity", "sheet", "Does {name} match the identity string in every frame: {identity}?"),
    ("wardrobe", "sheet", "Is {name} wearing exactly: {wardrobe}? No added marks or badges?"),
    ("props", "sheet", "{name} holds the {holding} at the start{holding_end}; same size and shape throughout?"),
    ("position", "first and last frame", "Is {name} {position_words}?"),
    ("direction", "sheet", "Does {name} keep {travel_words} for the whole take?"),
    ("eyeline", "sheet", "Is {name} {eyeline_words}?"),
    ("light", "sheet", "Light as planned ({light}), with no change of side or time of day?"),
    ("style", "sheet", "Does the look match: {look}?"),
    ("camera", "sheet", "Is it a {size}, {angle}, with {move} and no other move?"),
    ("action", "sheet", "Does the action happen and finish at normal speed, already moving at frame 1: {action}"),
    ("opening", "first frame", "Does the first frame match the start state: {start_state}"),
    ("end-state", "last frame", "Does the last frame match the end state: {end_state} Write what it shows."),
    ("anatomy", "sheet", "Are hands, limbs and faces whole in every frame?"),
    ("physics", "sheet", "Do objects keep their shape, contact and weight (nothing merges, slides or passes through)?"),
    ("text", "sheet", "Is the frame free of subtitles, captions, watermarks and garbled writing?"),
    ("audio", "listen", "Is the sound as planned ({audio}), spoken by the right person in sync?"),
    ("seam", "the previous take's last frame and this sheet", "Does the cut from {prev} read as one continuous scene, not a restart?"),
    ("spec", "qc spec", "Run `qc spec`: fps, size, aspect and length as planned?"),
    ("loudness", "qc loud", "At the mix: run `qc loud`; loudness on target?"),
]
CHECKS = [r[0] for r in RUBRIC]
TAX_ROW = re.compile(r"^\|\s*`([a-z-]+)`\s*\|(.+)\|\s*$")
VERDICTS = ("pass", "fail", "na")


def taxonomy(ctx):
    """Failure codes from every entry tagged `failures`: code -> symptom, cause, fix, rung, check."""
    codes, seen = {}, set()
    for d in ctx.ref_dirs:
        for p, meta, body in entries(d):
            if "failures" not in meta.get("tags", []) or meta.get("slug") in seen:
                continue
            seen.add(meta.get("slug"))
            for line in body.split("\n"):
                m = TAX_ROW.match(line.strip())
                if not m:
                    continue
                cells = [c.strip() for c in m.group(2).split("|")]
                if len(cells) == 5 and cells[3].isdigit():
                    codes[m.group(1)] = {"symptom": cells[0], "cause": cells[1], "fix": cells[2],
                                         "rung": int(cells[3]), "check": cells[4], "entry": meta.get("slug")}
    return codes


def need_tool(name):
    exe = shutil.which(name)
    if not exe:
        raise SystemExit("%s not found on PATH. qc and takes lastframe need it; see SETUP.md in cinewright-qc." % name)
    return exe


def run_tool(args):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("%s failed (%d): %s" % (Path(args[0]).name, r.returncode, r.stderr.strip()[-600:]))
    return r


def probe(clip):
    r = run_tool([need_tool("ffprobe"), "-v", "error", "-show_entries",
                  "stream=codec_type,width,height,r_frame_rate:format=duration", "-of", "json", str(clip)])
    j = json.loads(r.stdout)
    info = {"duration": float(j.get("format", {}).get("duration") or 0), "audio": False}
    for s in j.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            num, _, den = s.get("r_frame_rate", "0/1").partition("/")
            info.update(width=s["width"], height=s["height"], fps=float(num) / float(den or 1))
        elif s.get("codec_type") == "audio":
            info["audio"] = True
    if "width" not in info:
        raise SystemExit("%s has no video stream" % clip)
    return info


def contact_sheet(clip, out, fps=None, cols=4, width=320):
    info = probe(clip)
    fps = fps or (2 if info["duration"] <= 10 else 1)
    n = max(1, int(math.ceil(info["duration"] * fps)))
    rows = int(math.ceil(n / float(cols)))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    run_tool([need_tool("ffmpeg"), "-v", "error", "-y", "-i", str(clip), "-vf",
              "fps=%s,scale=%d:-2,tile=%dx%d:padding=4:margin=4" % (fps, width, cols, rows),
              "-frames:v", "1", "-update", "1", str(out)])
    return n, fps, info


def last_frame(clip, out):
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    run_tool([need_tool("ffmpeg"), "-v", "error", "-y", "-sseof", "-0.5", "-i", str(clip),
              "-update", "1", "-q:v", "2", str(out)])
    if not out.is_file():
        raise SystemExit("no frame written to %s" % out)
    return out


# Delivery loudness targets: integrated LUFS, tolerance in LU, max true peak dBTP, note.
# Sources and dates: shared vocab loudness-targets (cinewright-sound).
LOUD_PRESETS = {
    "web": (-18.0, 2.0, -2.0, "web video (EBU R128 s2 distribution range -20 to -16 LUFS; -2 dBTP before a lossy encoder)"),
    "ebu-r128": (-23.0, 0.2, -1.0, "EBU R128 v4 broadcast: on target within the meter's 0.2 LU; +/-1 LU only where the target is not practical (live)"),
    "atsc-a85": (-24.0, 2.0, -2.0, "ATSC A/85 US broadcast; it measures dialogue (the anchor) and this meter the whole programme, so the result is approximate"),
    "netflix": (-27.0, 2.0, -2.0, "Netflix measures dialogue-gated (BS.1770-1) and this meter the whole programme, so the result is approximate"),
    "music-streaming": (-14.0, 1.0, -1.0, "Spotify's normalisation level; its advice is -2 dBTP when louder than -14"),
}


def loud_target(a):
    """--preset fills target, tolerance and true peak; explicit flags win. No preset means web."""
    base = LOUD_PRESETS[a.preset or "web"][:3]
    pick = [a.target, a.tolerance, a.true_peak]
    return tuple(base[i] if pick[i] is None else pick[i] for i in range(3))


def loudness(path):
    r = subprocess.run([need_tool("ffmpeg"), "-nostats", "-hide_banner", "-i", str(path), "-filter_complex",
                        "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = r.stderr[r.stderr.rfind("Summary:"):] if "Summary:" in r.stderr else ""
    i = re.search(r"I:[\s]+(-?[\d.]+|-inf) LUFS", tail)
    if r.returncode != 0 or not i:
        raise SystemExit("ffmpeg could not measure loudness of %s (no audio stream?): %s" % (path, r.stderr.strip()[-300:]))
    tp = re.search(r"True peak:[\s]+Peak:[\s]+(-?[\d.]+|-inf) dBFS", tail)
    lra = re.search(r"LRA:[\s]+(-?[\d.]+) LU", tail)

    def num(m):
        return float("-inf") if m.group(1) == "-inf" else float(m.group(1))
    return {"integrated_lufs": num(i), "true_peak_dbtp": num(tp) if tp else None, "lra_lu": num(lra) if lra else None}


def card_by_id(p, cid):
    for c in p.cards:
        if c["id"] == cid:
            return c
    raise SystemExit("no card %s in %s" % (cid, p.root))


def spec_check(info, p, card, params=None):
    """Return a list of (status, text); status is PASS, FAIL or INFO."""
    st, out, params = p.style, [], params or {}
    want, dur = card["duration_s"], info["duration"]
    if dur + 0.05 < want:
        out.append(("FAIL", "length %.2fs, card needs %ss" % (dur, want)))
    elif dur > want + 0.5:
        out.append(("INFO", "length %.2fs, card %ss: trim %.2fs in the edit" % (dur, want, dur - want)))
    else:
        out.append(("PASS", "length %.2fs for a %ss card" % (dur, want)))
    fps = params.get("fps", st["fps"])
    out.append(("PASS" if abs(info["fps"] - fps) < 0.01 else "FAIL", "fps %.3g, planned %s" % (info["fps"], fps)))
    a, b = (float(x) for x in st["aspect_ratio"].split(":"))
    got = info["width"] / float(info["height"])
    ok = abs(got - a / b) / (a / b) <= 0.02
    out.append(("PASS" if ok else "FAIL", "aspect %dx%d (%.3f), planned %s" % (info["width"], info["height"], got, st["aspect_ratio"])))
    if "width" in params and "height" in params:
        same = (info["width"], info["height"]) == (params["width"], params["height"])
        out.append(("PASS" if same else "FAIL", "size %dx%d, settings %dx%d" % (info["width"], info["height"], params["width"], params["height"])))
    if (card.get("dialogue") or card.get("sound")) and not info["audio"]:
        out.append(("FAIL", "no audio stream, but the card has dialogue or sound (add it in the mix if the model makes none)"))
    return out


def rubric_items(p, card):
    sc = p.scene_map[card["scene"]]
    cam, light = card["camera"], card.get("light", {})
    prev = [c for c in p.cards if c["scene"] == card["scene"] and c["order"] < card["order"]]
    lt = [sc["sun"]] if sc.get("sun") else []
    if light.get("key_side"):
        lt.append("%s key from %s" % (light.get("quality", "soft"), light["key_side"].replace("-", " ")))
    in_shot = [m["id"] for m in card.get("cast", [])]
    audio = ["%s%s says: %s" % (p.chars[d["character"]]["name"], "" if d["character"] in in_shot else " (off screen, no visible mouth)", d["line"])
             for d in card.get("dialogue", [])]
    if card.get("sound"):
        audio.append(card["sound"])
    base = {"look": p.style["look"], "light": "; ".join(lt) or "as the scene bible", "size": SIZE_WORDS[cam["size"]],
            "angle": ANGLE_WORDS[cam["angle"]], "move": MOVE_WORDS[cam["move"]], "action": _sentence(card["action"]),
            "start_state": _sentence(card.get("start_state", "")), "end_state": _sentence(card.get("end_state", "")),
            "audio": "; ".join(audio), "prev": prev[-1]["id"] if prev else ""}
    items = []
    for check, look, ask in RUBRIC:
        rows = []
        if "{name}" in ask:
            for m in card.get("cast", []):
                ch = p.chars[m["id"]]
                travel = m.get("travel") or sc.get("axis", {}).get("travel", {}).get(m["id"])
                v = dict(base, name=ch["name"], identity=ch["identity"], wardrobe=wardrobe_for(ch, sc["id"]),
                         holding=("%s (%s)" % (m["holding"], prop_words(p, m["holding"])) if m.get("holding") in p.props else m.get("holding") or ""),
                         holding_end=(" and the %s at the end" % m["holding_end"]) if m.get("holding_end") else "",
                         position_words=POSITION_WORDS.get(m.get("position"), ""),
                         travel_words=TRAVEL_WORDS.get(travel, ""), eyeline_words=EYELINE_WORDS.get(m.get("eyeline"), ""))
                need = {"props": "holding", "position": "position_words", "direction": "travel_words", "eyeline": "eyeline_words"}.get(check)
                if not need or v[need]:
                    rows.append(("%s:%s" % (check, m["id"]), ask.format(**v)))
        else:
            need = {"opening": "start_state", "end-state": "end_state", "audio": "audio", "seam": "prev"}.get(check)
            if not need or base[need]:
                rows.append((check, ask.format(**base)))
        for rid, text in rows:
            items.append({"id": rid, "check": check, "look": look, "ask": text, "verdict": None, "code": None, "note": ""})
    return items


def repair_plan(rub, codes):
    """Fails in a filled rubric -> ([(rung, item id, code, fix)] cheapest first, errors)."""
    plan, errs = [], []
    for it in rub["items"]:
        v = it.get("verdict")
        if v not in VERDICTS:
            errs.append("%s: verdict must be one of %s (got %r)" % (it["id"], ", ".join(VERDICTS), v))
            continue
        if v != "fail":
            continue
        cands = [c for c, x in codes.items() if x["check"] == it["check"]]
        code = it.get("code")
        if code and codes.get(code, {}).get("check") != it["check"]:
            errs.append("%s: code %s does not belong to check %s; use one of %s" % (it["id"], code, it["check"], ", ".join(cands)))
            continue
        if not code:
            if len(cands) != 1:
                errs.append("%s: pick a code: %s" % (it["id"], ", ".join(cands)))
                continue
            code = cands[0]
        plan.append((codes[code]["rung"], it["id"], code, codes[code]["fix"]))
    plan.sort()
    return plan, errs


# Machine measures of a take (qc measure). They find technical faults a reviewer misses at contact-sheet
# resolution; they never judge acting, look or story (that is the rubric). Thresholds were set on 2026-10-07
# against reviewed takes of three local multi-shot films (keepers and rejects).
MEASURE_CUT_SCENE = 0.30     # ffmpeg scene score that counts as a cut
MEASURE_CUT_EARLY_S = 1.0    # H3 cuts 0.1-0.8 s before the stamped time (24 reviewed takes), so allow early
MEASURE_CUT_LATE_S = 0.6     # ... and less late
MEASURE_CUT_NEAR_S = 2.0     # a cut this close but outside the window is the planned cut, early or late (a long line
                             # holds the shot: 1.2 s late on a 16-word line in 6 s, 2026-10-07)
MEASURE_FREEZE = 0.35        # mean luma difference (0-255, 160 px wide) below which the picture is frozen
MEASURE_FREEZE_S = 1.5       # a frozen run longer than this inside one shot fails
MEASURE_SILENCE_DB = -60.0   # 100 ms window RMS below this is silence (room tone sits above it)
MEASURE_DEAD_AIR_S = 2.0     # a silent run longer than this fails
MEASURE_CLIP = 0.999         # sample magnitude that counts as clipped
MEASURE_SPEECH_S = 0.6       # seconds of speech-band activity a shot with a planned line must have
MEASURE_SEAM_JUMP_DB = 6.0   # level change across a seam (1 s each side) that fails
MEASURE_WEIGHTS = {"cut-missing": 10, "cut-extra": 4, "cut-off": 12, "frozen": 10, "dead-air": 10, "clipping": 10,
                   "speech-missing": 15, "seam-jump": 8}


def scene_cuts(clip, thresh=MEASURE_CUT_SCENE):
    r = subprocess.run([need_tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(clip), "-an", "-vf",
                        "select='gt(scene,%s)',showinfo" % thresh, "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg could not scan %s for cuts: %s" % (clip, r.stderr.strip()[-300:]))
    return [round(float(t), 3) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]


def frame_motion(clip):
    """[(t, mean luma difference to the previous frame)] at 160 px wide."""
    r = subprocess.run([need_tool("ffmpeg"), "-hide_banner", "-nostats", "-i", str(clip), "-an", "-vf",
                        "scale=160:-2,format=gray,tblend=all_mode=difference,signalstats,"
                        "metadata=print:key=lavfi.signalstats.YAVG:file=-", "-f", "null", "-"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        raise SystemExit("ffmpeg could not measure motion in %s: %s" % (clip, r.stderr.strip()[-300:]))
    out, t = [], None
    for line in r.stdout.splitlines():
        m = re.search(r"pts_time:([\d.]+)", line)
        if m:
            t = float(m.group(1))
            continue
        m = re.search(r"YAVG=([\d.]+)", line)
        if m and t is not None:
            out.append((t, float(m.group(1))))
    return out


def pcm(clip, rate=8000, af=None):
    args = [need_tool("ffmpeg"), "-v", "error", "-i", str(clip), "-vn", "-ac", "1", "-ar", str(rate)]
    if af:
        args += ["-af", af]
    r = subprocess.run(args + ["-f", "s16le", "-"], capture_output=True)
    if r.returncode != 0:
        return []
    import array
    a = array.array("h")
    a.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return [x / 32768.0 for x in a]


def window_db(x, rate=8000, win=0.1):
    n = int(rate * win)
    out = []
    for i in range(0, len(x) - n + 1, n):
        e = sum(v * v for v in x[i:i + n]) / n
        out.append(10 * math.log10(e) if e > 1e-12 else -120.0)
    return out


def longest_run(flags, step):
    best = cur = 0
    for f in flags:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return round(best * step, 2)


def measure_plan(p, label):
    """[(card id, start s, end s, has a visible speaker's line)] for a generation label such as 1A+1B+1C."""
    plan, t = [], 0.0
    for cid in label.split("+"):
        c = card_by_id(p, cid)
        cast = [m["id"] for m in c.get("cast", [])]
        speaks = any(d["character"] in cast for d in c.get("dialogue", []))
        plan.append((cid, t, t + c["duration_s"], speaks))
        t += c["duration_s"]
    return plan


def measure_stills(p, label):
    return {c["id"]: c.get("sound", "") for c in (card_by_id(p, cid) for cid in label.split("+")) if c["camera"].get("move") == "static"}


def measure_take(clip, plan=None, seams=None, stills=None):
    """stills: {card id: its sound text} for cards whose camera is static; a still picture or silence there warns, not fails."""
    info = probe(clip)
    dur = info["duration"]
    planned_cuts = bool(plan)  # without a plan, cuts are listed, never counted as unplanned
    if not plan:
        plan = [("whole", 0.0, dur, False)]
    plan = [(cid, s, min(e, dur), sp) for cid, s, e, sp in plan]  # prompts stamp absolute times, so no scaling
    cuts = scene_cuts(clip)
    motion = frame_motion(clip)
    checks, shots = [], []
    planned = [s for _, s, _, _ in plan[1:]]
    used = set()
    for t in planned:
        near = [c for c in cuts if t - MEASURE_CUT_EARLY_S <= c <= t + MEASURE_CUT_LATE_S and c not in used]
        off = sorted((c for c in cuts if abs(c - t) <= MEASURE_CUT_NEAR_S and c not in used), key=lambda c: abs(c - t))
        if near:
            used.add(near[0])
            checks.append(("PASS", "cut-planned", "planned cut at %.2fs found at %.2fs" % (t, near[0])))
        elif off:
            used.add(off[0])
            checks.append(("WARN", "cut-off", "planned cut at %.2fs came %.2fs %s (a long line holds a shot; check the timing reads)"
                           % (t, abs(off[0] - t), "late" if off[0] > t else "early")))
        else:
            checks.append(("FAIL", "cut-missing", "planned cut at %.2fs not found: the shot held or cut elsewhere" % t))
    for c in cuts:
        if planned_cuts and c not in used and not any(t - MEASURE_CUT_EARLY_S <= c <= t + MEASURE_CUT_LATE_S for t in planned):
            checks.append(("FAIL", "cut-extra", "unplanned cut at %.2fs (a jump, a flash or a new shot the plan did not ask for)" % c))
    quiet = bool(stills) and any("silen" in (s or "") for s in stills.values())
    x = pcm(clip) if info["audio"] else []
    sp = pcm(clip, af="highpass=f=300,lowpass=f=3400") if x else []
    full, band = window_db(x), window_db(sp)
    if x:
        peak = max(abs(v) for v in x)
        clipped = sum(1 for v in x if abs(v) >= MEASURE_CLIP)
        checks.append(("FAIL" if clipped > 10 else "PASS", "clipping" if clipped > 10 else "audio-peak",
                       "peak %.1f dBFS, %d clipped samples" % (20 * math.log10(peak) if peak > 0 else -120, clipped)))
        dead = longest_run([d < MEASURE_SILENCE_DB for d in full], 0.1)
        bad = "WARN" if quiet else "FAIL"
        checks.append((bad if dead > MEASURE_DEAD_AIR_S else "PASS", "dead-air" if dead > MEASURE_DEAD_AIR_S else "audio-silence",
                       "longest silence %.1fs%s" % (dead, " (a card asks for silence)" if quiet and dead > MEASURE_DEAD_AIR_S else "")))
    elif plan and any(s for *_, s in plan):
        checks.append(("FAIL", "speech-missing", "no audio stream"))
    for cid, s, e, speaks in plan:
        fr = [m for t, m in motion if s + 0.25 <= t < e - 0.25]  # skip the frames either side of a cut
        frozen = longest_run([m < MEASURE_FREEZE for m in fr], 1 / max(info["fps"], 1))
        row = {"card": cid, "start": round(s, 2), "end": round(e, 2),
               "motion": round(sum(fr) / len(fr), 2) if fr else 0.0, "frozen_s": frozen}
        if band:
            ws = band[int(s * 10):int(e * 10)]
            med = sorted(ws)[len(ws) // 2] if ws else MEASURE_SILENCE_DB
            row["speech_s"] = round(sum(1 for d in ws if d >= max(MEASURE_SILENCE_DB + 20, med + 6)) * 0.1, 1)  # above the shot's own floor
            row["level_db"] = round(sum(full[int(s * 10):int(e * 10)]) / max(1, len(ws)), 1)
        shots.append(row)
        if frozen > MEASURE_FREEZE_S:
            st = "WARN" if stills and cid in stills else "FAIL"
            checks.append((st, "frozen", "%s: picture frozen for %.1fs%s" % (cid, frozen, " (static camera: check it is meant)" if st == "WARN" else "")))
        if speaks and band:
            ok = row["speech_s"] >= MEASURE_SPEECH_S
            checks.append(("PASS" if ok else "FAIL", "speech" if ok else "speech-missing",
                           "%s: %.1fs of speech-band sound where a line is planned" % (cid, row["speech_s"])))
    for t in seams or []:
        a, b = full[max(0, int((t - 1.05) * 10)):int((t - 0.05) * 10)], full[int((t + 0.05) * 10):int((t + 1.05) * 10)]
        if a and b:
            ja, jb = 10 * math.log10(sum(10 ** (d / 10) for d in a) / len(a)), 10 * math.log10(sum(10 ** (d / 10) for d in b) / len(b))
            bad = abs(ja - jb) > MEASURE_SEAM_JUMP_DB
            checks.append(("WARN" if bad else "PASS", "seam-jump" if bad else "seam-level",  # often scripted (a roar cut to silence)
                           "seam at %.2fs: level %.1f dB before, %.1f dB after" % (t, ja, jb)))
    score = 100
    for st, code, _ in checks:
        if st == "FAIL":
            score -= MEASURE_WEIGHTS.get(code, 5)
        elif st == "WARN":
            score -= MEASURE_WEIGHTS.get(code, 5) // 3
    res = {"clip": str(clip), "duration": round(dur, 3), "cuts": cuts, "shots": shots,
           "checks": [{"status": s, "code": c, "text": t} for s, c, t in checks], "score": max(0, score)}
    if x:
        try:
            res["loudness"] = loudness(clip)
        except SystemExit:
            pass
    return res


def measure_lines(m):
    out = ["%s: %.2fs, cuts at %s" % (m["clip"], m["duration"], ", ".join("%.2f" % c for c in m["cuts"]) or "none")]
    for r in m["shots"]:
        out.append("  %-6s %5.2f-%5.2fs  motion %5.2f  frozen %.1fs%s" % (
            r["card"], r["start"], r["end"], r["motion"], r["frozen_s"],
            ("  speech %.1fs  level %.1f dB" % (r["speech_s"], r["level_db"])) if "speech_s" in r else ""))
    for c in m["checks"]:
        out.append("%-4s %-15s %s" % (c["status"], c["code"], c["text"]))
    if m.get("loudness"):
        out.append("loudness %.1f LUFS, true peak %s dBTP" % (m["loudness"]["integrated_lufs"], m["loudness"]["true_peak_dbtp"]))
    out.append("qc measure: score %d/100 (machine checks only; judge the picture with qc rubric)" % m["score"])
    return out


def cmd_qc(ctx, a):
    if a.cmd == "sheet":
        out = a.out or str(Path(a.clip).with_suffix("")) + ".sheet.png"
        n, fps, info = contact_sheet(a.clip, out, a.fps, a.cols, a.width)
        print("wrote %s: %d frames at %s fps from %.2fs, %dx%d" % (out, n, fps, info["duration"], info["width"], info["height"]))
        print("Read it once, whole, then fill the rubric (qc rubric).")
        return 0
    if a.cmd == "spec":
        info = probe(a.clip)
        p = Project(a.project)
        group = [card_by_id(p, cid) for cid in a.card.split("+")]
        card = dict(group[0], duration_s=sum(c["duration_s"] for c in group),
                    dialogue=[d for c in group for d in c.get("dialogue", [])], sound=" ".join(c.get("sound", "") for c in group).strip())
        rows = spec_check(info, p, card, json.loads(read_text(a.params)) if a.params else None)
        fails = sum(1 for s, _ in rows if s == "FAIL")
        if a.json:
            print(json.dumps({"clip": str(a.clip), "probe": info, "checks": [{"status": s, "text": t} for s, t in rows]}, indent=2))
        else:
            for s, t in rows:
                print("%-4s %s" % (s, t))
            print("qc spec: %d checks, %d failed%s" % (len(rows), fails, " (code spec-mismatch)" if fails else ""))
        return 1 if fails else 0
    if a.cmd == "loud":
        m = loudness(a.file)
        target, tol, peak = loud_target(a)
        if a.preset:
            print("preset %s: %s" % (a.preset, LOUD_PRESETS[a.preset][3]))
        ok_i = abs(m["integrated_lufs"] - target) <= tol
        ok_tp = m["true_peak_dbtp"] is not None and m["true_peak_dbtp"] <= peak
        print("integrated %.1f LUFS (target %.1f +/- %.1f): %s" % (m["integrated_lufs"], target, tol, "PASS" if ok_i else "FAIL"))
        print("true peak %s dBTP (max %.1f): %s" % (m["true_peak_dbtp"], peak, "PASS" if ok_tp else "FAIL"))
        if m["lra_lu"] is not None:
            print("loudness range %.1f LU" % m["lra_lu"])
        print("qc loud: %s" % ("PASS" if ok_i and ok_tp else "FAIL (code loudness-off): normalise in the mix"))
        return 0 if ok_i and ok_tp else 1
    if a.cmd == "measure":
        plan = stills = None
        if a.card:
            if not a.project:
                print("qc measure --card needs --project", file=sys.stderr)
                return 2
            pr = Project(a.project)
            plan, stills = measure_plan(pr, a.card), measure_stills(pr, a.card)
        seams = [float(t) for t in a.seams.split(",")] if a.seams else []
        if a.every:
            info = probe(a.clip)
            seams = [a.every * k for k in range(1, int(info["duration"] / a.every + 0.999)) if a.every * k < info["duration"] - 0.5]
        m = measure_take(a.clip, plan, seams, stills)
        if a.out:
            write_text(a.out, json.dumps(m, indent=2) + "\n")
        print(json.dumps(m, indent=2) if a.json else "\n".join(measure_lines(m)))
        return 1 if any(c["status"] == "FAIL" for c in m["checks"]) else 0
    if a.cmd == "rubric":
        codes = taxonomy(ctx)
        if not codes:
            print("no failure-code entries (tag failures) found; install cinewright-qc", file=sys.stderr)
            return 1
        if a.read:
            rub = json.loads(read_text(a.read))
            plan, errs = repair_plan(rub, codes)
            for e in errs:
                print("error: %s" % e)
            if errs:
                return 1
            if not plan:
                print("qc rubric %s: PASS (%d items)" % (rub.get("card"), len(rub["items"])))
                return 0
            for rung, rid, code, fix in plan:
                print("rung %d  %-18s %-18s %s" % (rung, rid, code, fix))
            rung, rid, code, fix = plan[0]
            verdict = "keep-fix-in-edit" if all(r[0] >= 7 for r in plan) else "fail"
            print("qc rubric %s: %s, %d failed. Next take changes one thing: %s (%s). Then: takes log ... --verdict %s --fix %s"
                  % (rub.get("card"), verdict.upper(), len(plan), fix, code, verdict, code))
            return 1
        if not a.project or not a.card:
            print("qc rubric needs PROJECT --card ID, or --read RUBRIC.json", file=sys.stderr)
            return 2
        p = Project(a.project)
        card = card_by_id(p, a.card)
        items = rubric_items(p, card)
        for it in items:
            it["codes"] = [c for c, x in codes.items() if x["check"] == it["check"]]
        rub = {"card": card["id"], "clip": a.clip or "", "sheet": a.sheet or "",
               "how": "Set each verdict to pass, fail or na. On a fail set code (one of codes) and a note. Then run: qc rubric --read THIS_FILE",
               "items": items}
        out = a.out or str(p.root / "qc" / ("%s.rubric.json" % card["id"]))
        write_text(out, json.dumps(rub, indent=2, ensure_ascii=False) + "\n")
        print("wrote %s: %d items for card %s" % (out, len(items), card["id"]))
        return 0
    return 2


def cmd_takes(ctx, a):
    if a.cmd == "lastframe":
        out = last_frame(a.clip, a.out)
        print("wrote %s" % out)
        if a.take:
            rec = json.loads(read_text(a.take))
            if a.observed:
                rec["observed_end_state"] = a.observed
                write_text(a.take, json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
                print("observed_end_state written to %s" % a.take)
            try:
                card = card_by_id(Project(Path(a.take).resolve().parent.parent), rec["card"])
                print("planned end state: %s" % card.get("end_state", "(none)"))
            except (OSError, SystemExit, KeyError):
                pass
        if not a.observed:
            print('Look at the frame, then record what it shows: takes lastframe CLIP --out PNG --take TAKE.json --observed "...". The next card copies it into start_state.')
        return 0
    if a.cmd == "log":
        p = Project(a.project)
        card = card_by_id(p, a.card)
        tdir = p.root / "takes"
        nums = [int(m.group(1)) for f in tdir.glob("%s-*.json" % card["id"]) for m in [re.match(r".*-(\d+)\.json$", f.name)] if m]
        n = 1 + max(nums or [0])
        rec = {"card": card["id"], "take": n, "model": a.model, "date": datetime.date.today().isoformat(), "verdict": a.verdict}
        cdir = p.root / "compiled" / a.model
        comp = [f for f in sorted(cdir.glob("*.txt")) if card["id"] in f.stem.split("+")] if cdir.is_dir() else []
        if comp:
            rec["prompt_sha256"] = hashlib.sha256(read_text(comp[0]).encode("utf-8")).hexdigest()
            pf = comp[0].with_name(comp[0].stem + ".params.json")
            if pf.is_file():
                rec["params"] = json.loads(read_text(pf))
                rec["model_id"] = str(rec["params"].get("model", ""))
        rec["seed"] = a.seed if a.seed is not None else rec.get("params", {}).get("seed", card.get("seed"))
        for k, v in (("file", a.file), ("fix_code", a.fix), ("change_from_previous", a.change),
                     ("observed_end_state", a.observed), ("notes", a.notes)):
            if v:
                rec[k] = v
        if a.fix:
            codes = taxonomy(ctx)
            if codes and a.fix not in codes:
                raise SystemExit("unknown fix code %s; run kb show failures-picture or failures-motion" % a.fix)
        errs = validate(rec, load_schema(ctx, "take"))
        if errs:
            raise SystemExit("take record invalid: %s" % "; ".join(errs))
        out = tdir / ("%s-%d.json" % (card["id"], n))
        write_text(out, json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
        takes = [json.loads(read_text(f)) for f in sorted(tdir.glob("%s-*.json" % card["id"]))]
        fails = sum(1 for t in takes if t["verdict"] == "fail")
        print("wrote %s; card %s: %d takes, %d failed" % (out, card["id"], len(takes), fails))
        if fails >= 3 and a.verdict == "fail":
            print("three strikes: stop rerolling and re-plan card %s (rung 6)" % card["id"])
        return 0
    return 2


# ---------- argument parsing ----------

# ---------- voice ----------

VOICE_RATE = 8000  # pitch is tracked at 8 kHz: enough for 60-400 Hz, fast in pure Python
F0_LO, F0_HI = 60.0, 400.0
REF_SECONDS = (3.0, 30.0)  # most cloning engines want a clip in this range (cinewright-voice, entry reference-clips)


def voice_pcm(path, start=None, end=None):
    """Mono float samples at VOICE_RATE from any audio or video file (ffmpeg decodes it)."""
    args = [need_tool("ffmpeg"), "-v", "error"]
    if start is not None:
        args += ["-ss", "%.3f" % start]
    if end is not None:
        args += ["-to", "%.3f" % end]
    args += ["-i", str(path), "-vn", "-ac", "1", "-ar", str(VOICE_RATE), "-af", "highpass=f=60", "-f", "s16le", "-"]
    r = subprocess.run(args, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("ffmpeg could not read audio from %s: %s" % (path, r.stderr.decode("utf-8", "replace").strip()[-300:]))
    import array
    a = array.array("h")
    a.frombytes(r.stdout[:len(r.stdout) // 2 * 2])
    if sys.byteorder == "big":
        a.byteswap()
    return [x / 32768.0 for x in a]


def f0_track(x, frame=0.04, hop=0.02, thresh=0.3, gate_db=35.0):
    """YIN pitch per frame (0.0 = unvoiced or silent), seconds above the energy gate, and first-to-last speech span.

    thresh 0.3: steadier than 0.2 on low creaky voices and on lines with music under them (tested 2026-10-07)."""
    from operator import mul
    n, h = int(frame * VOICE_RATE), int(hop * VOICE_RATE)
    tmin, tmax = int(VOICE_RATE / F0_HI), int(VOICE_RATE / F0_LO)
    starts = range(0, max(0, len(x) - n - tmax), h)
    energy = [sum(map(mul, x[i:i + n], x[i:i + n])) / n for i in starts]
    if not energy or max(energy) <= 0:
        return [], 0.0, 0.0
    gate = max(energy) * 10 ** (-gate_db / 10)
    loud = [k for k, e in enumerate(energy) if e >= gate]
    span = (loud[-1] - loud[0]) * hop + frame
    out, active = [], 0
    for i, e in zip(starts, energy):
        if e < gate:
            out.append(0.0)
            continue
        active += 1
        w = x[i:i + n]
        r0 = sum(map(mul, w, w))
        cmnd, cum = [1.0] * (tmax + 2), 0.0
        for tau in range(1, tmax + 2):
            seg = x[i + tau:i + tau + n]
            d = r0 + sum(map(mul, seg, seg)) - 2 * sum(map(mul, w, seg))
            cum += d
            cmnd[tau] = d * tau / cum if cum else 1.0
        tau = tmin
        while tau < tmax and cmnd[tau] >= thresh:
            tau += 1
        if tau >= tmax:
            out.append(0.0)
            continue
        while tau + 1 < tmax and cmnd[tau + 1] < cmnd[tau]:
            tau += 1
        a, b, c = cmnd[tau - 1], cmnd[tau], cmnd[tau + 1]
        den = a - 2 * b + c
        out.append(VOICE_RATE / (tau + (0.5 * (a - c) / den if den else 0.0)))
    return out, active * hop, span


def voice_measure(path, start=None, end=None, text=None):
    x = voice_pcm(path, start, end)
    track, active, span = f0_track(x)
    v = sorted(f for f in track if f)
    m = {"file": str(path), "seconds": round(len(x) / float(VOICE_RATE), 2), "speech_span_s": round(span, 2),
         "active_s": round(active, 2), "voiced_s": round(len(v) * 0.02, 2)}
    if start is not None or end is not None:
        m["span"] = [start, end]
    if v:
        q = lambda k: v[min(len(v) - 1, int(k * len(v)))]
        m.update(f0_median_hz=round(v[len(v) // 2], 1), f0_p10_hz=round(q(0.1), 1), f0_p90_hz=round(q(0.9), 1),
                 range_st=round(12 * math.log2(q(0.9) / q(0.1)), 1))
    if text:
        words = len(re.findall(r"[\w']+", text))
        m["words"] = words
        if span:
            m["wpm"] = round(words * 60.0 / span)
    warn = []
    if not v:
        warn.append("no voiced speech found")
    else:
        if m["voiced_s"] < 0.3 * max(active, 0.01):
            warn.append("little of the sound is voiced: music, effects or noise under the voice; cut to the line or isolate the voice first")
        if m["range_st"] > 18:
            warn.append("pitch range over 18 semitones: another source is mixed in, or the tracker jumped an octave")
        if m["voiced_s"] < 1.0:
            warn.append("under 1 s of voiced speech: the numbers are rough")
    m["warnings"] = warn
    return m


def voice_lines(m):
    out = ["%s%s: %.2fs, speech from first to last word %.2fs (%.2fs above the gate), voiced %.2fs" % (
        m["file"], (" [%s-%s]" % tuple(m["span"])) if "span" in m else "", m["seconds"], m["speech_span_s"], m["active_s"], m["voiced_s"])]
    if "f0_median_hz" in m:
        out.append("  pitch median %.0f Hz (p10 %.0f, p90 %.0f), range %.1f semitones"
                   % (m["f0_median_hz"], m["f0_p10_hz"], m["f0_p90_hz"], m["range_st"]))
    if "wpm" in m:
        out.append("  pace %d words a minute, pauses included (%d words)" % (m["wpm"], m["words"]))
    out += ["  WARNING: %s" % w for w in m["warnings"]]
    return out


def voice_bible_errors(p):
    errs = []
    for cid, v in p.voices.items():
        if cid not in p.chars:
            errs.append("bibles/voices.json: character '%s' is not in characters.json" % cid)
        elif not p.chars[cid].get("voice"):
            errs.append("bibles/voices.json: %s has no short `voice` string in characters.json; prompts copy that string" % cid)
        for r in v.get("refs", []):
            f = p.root / r.get("file", "")
            if not f.is_file():
                errs.append("bibles/voices.json: %s reference %s is missing" % (cid, r.get("file")))
        if v.get("refs") and not any(r.get("emotion") == "neutral" for r in v["refs"]):
            errs.append("bibles/voices.json: %s has no neutral reference; record or cut one first" % cid)
    return errs


def voice_baseline(p, cid):
    """Pitch median across the character's reference clips (the neutral ones when there are any)."""
    v = p.voices.get(cid)
    if not v:
        raise SystemExit("%s has no entry in bibles/voices.json" % cid)
    refs = [r for r in v.get("refs", []) if r.get("emotion") == "neutral"] or v.get("refs", [])
    if not refs:
        raise SystemExit("%s has no reference clips in bibles/voices.json" % cid)
    ms = [voice_measure(p.root / r["file"], r.get("start_s"), r.get("end_s"), r.get("text")) for r in refs]
    meds = sorted(m["f0_median_hz"] for m in ms if "f0_median_hz" in m)
    if not meds:
        raise SystemExit("no voiced speech in %s's references" % cid)
    wpms = sorted(m["wpm"] for m in ms if "wpm" in m)
    return {"f0_median_hz": meds[len(meds) // 2], "wpm": wpms[len(wpms) // 2] if wpms else None,
            "tolerance_st": v.get("tolerance_st", 2.0), "refs": ms}


def cmd_voice(ctx, a):
    if a.cmd == "measure":
        m = voice_measure(a.file, a.start, a.end, a.text)
        print(json.dumps(m, indent=2) if a.json else "\n".join(voice_lines(m)))
        return 1 if "f0_median_hz" not in m else 0
    if a.cmd == "ref":
        out = Path(a.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        args = [need_tool("ffmpeg"), "-v", "error", "-y"]
        if a.start is not None:
            args += ["-ss", "%.3f" % a.start]
        if a.end is not None:
            args += ["-to", "%.3f" % a.end]
        # dry mono clip: rumble cut, edges trimmed of silence, levelled for a cloning engine
        flt = ("highpass=f=70,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.15,"
               "areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.25,areverse,"
               "loudnorm=I=-20:TP=-3:LRA=11")
        run_tool(args + ["-i", str(a.file), "-vn", "-ac", "1", "-af", flt, "-ar", str(a.rate), "-c:a", "pcm_s16le", str(out)])
        m = voice_measure(out, text=a.text)
        print("wrote %s (mono, %d Hz, 16-bit)" % (out, a.rate))
        print("\n".join(voice_lines(m)))
        lo, hi = REF_SECONDS
        if not lo <= m["seconds"] <= hi:
            print("  WARNING: %.1fs; most engines want %d-%d s (ElevenLabs instant clones 60-120 s)" % (m["seconds"], lo, hi))
        if not a.text:
            print("  Next: write the exact words of this clip into the ref's `text` (many engines need the transcript).")
        return 0 if "f0_median_hz" in m and not m["warnings"] else 1
    p = Project(a.project)
    errs = validate_project(ctx, p) if p.voices_bible is not None else ["bibles/voices.json is missing; write it first (cinewright-voice)"]
    speakers = sorted({d["character"] for c in p.cards for d in c.get("dialogue", [])})
    for cid in speakers:
        if p.voices_bible is not None and cid not in p.voices:
            errs.append("%s speaks in the cards but has no voice in bibles/voices.json" % cid)
    if not a.clip:
        for e in errs:
            print("ERROR " + e)
        for cid, v in sorted(p.voices.items()):
            print("%s: %d reference(s), emotions %s, engine %s" % (cid, len(v.get("refs", [])),
                  ", ".join(sorted({r["emotion"] for r in v.get("refs", [])})) or "none", v.get("engine", {}).get("name", "not set")))
        print("voice check: %d error(s)" % len(errs))
        return 1 if errs else 0
    if not a.character:
        raise SystemExit("--clip needs --character")
    base = voice_baseline(p, a.character)
    m = voice_measure(a.clip, a.start, a.end, a.text)
    print("\n".join(voice_lines(m)))
    print("  reference: median %.0f Hz over %d clip(s)%s" % (base["f0_median_hz"], len(base["refs"]),
          (", pace %d wpm" % base["wpm"]) if base["wpm"] else ""))
    if "f0_median_hz" not in m:
        print("voice check: UNMEASURED (no voiced speech)")
        return 1
    st = 12 * math.log2(m["f0_median_hz"] / base["f0_median_hz"])
    fails = []
    if abs(st) > base["tolerance_st"]:
        fails.append("pitch %+.1f semitones from the reference (limit %.1f)%s" % (
            st, base["tolerance_st"], ": a different voice, likely the wrong gender or age" if abs(st) >= 5 else ""))
    if base["wpm"] and m.get("wpm") and abs(m["wpm"] - base["wpm"]) > 0.25 * base["wpm"]:
        fails.append("pace %d wpm against %d (more than 25%% off)" % (m["wpm"], base["wpm"]))
    for f in fails:
        print("  DRIFT " + f)
    verdict = "DRIFT" if fails else ("UNSURE" if m["warnings"] else "PASS")
    print("voice check %s: %s (pitch %+.1f semitones). Pitch and pace only: listen, or run a speaker-embedding check, before calling it the same voice."
          % (a.character, verdict, st))
    return 0 if verdict == "PASS" else 1


def build_parser(prog="cine.py"):
    ap = argparse.ArgumentParser(prog=prog, description="cinewright: plan, check and compile shots.")
    g = ap.add_subparsers(dest="group", required=True)

    kb = g.add_parser("kb", help="knowledge base").add_subparsers(dest="cmd", required=True)
    kb.add_parser("index", help="rewrite references/INDEX.md")
    s = kb.add_parser("search", help="find entries by words")
    s.add_argument("words", nargs="+")
    s.add_argument("--limit", type=int, default=8)
    s = kb.add_parser("show", help="print one entry or one section")
    s.add_argument("slug")
    s.add_argument("--section")

    cards = g.add_parser("cards", help="shot cards").add_subparsers(dest="cmd", required=True)
    s = cards.add_parser("new", help="write a skeleton card filled from the bibles")
    s.add_argument("project")
    s.add_argument("--id", required=True)
    s.add_argument("--scene", required=True)
    s.add_argument("--cast", help="comma-separated character ids")
    s.add_argument("--order", type=int)
    s = cards.add_parser("validate", help="check bibles and cards against the schemas")
    s.add_argument("project")
    s.add_argument("--style", metavar="FILE", help="check this style bible in place of bibles/style.json")
    s = cards.add_parser("list", help="print the shot list in cut order")
    s.add_argument("project")
    s = cards.add_parser("export", help="export the shot list")
    s.add_argument("project")
    s.add_argument("--film-json", action="store_true", help="film.json shape for a local long-render pipeline")
    s.add_argument("--xfade", type=float, default=0.16, help="seam_audio_xfade seconds")
    s.add_argument("--sequence", action="store_true", help="one shot per compile --sequence generation (needs --model)")
    s.add_argument("--model", help="model card for --sequence")
    s.add_argument("--out")

    s = g.add_parser("compile", help="card plus bibles to one model's prompt")
    s.add_argument("project")
    s.add_argument("--model", required=True)
    s.add_argument("--card", action="append", help="card id; repeat; default all")
    s.add_argument("--sequence", action="store_true", help="join consecutive cards of a scene into one timestamped generation")
    s.add_argument("--join", action="store_true", help="with --sequence: keep cards of different scenes in one generation (an establishing exterior before the interior); the new place is described where it changes")
    s.add_argument("--resolution", help="override the style bible's resolution, e.g. a cheap draft size")
    s.add_argument("--style", metavar="FILE", help="compile with this style bible in place of bibles/style.json")
    s.add_argument("--out")

    c = g.add_parser("continuity", help="script supervisor checks").add_subparsers(dest="cmd", required=True)
    s = c.add_parser("diff", help="check every card against the bibles and the previous card")
    s.add_argument("project")
    s.add_argument("--json", action="store_true")
    s.add_argument("--with", dest="with_card", action="append", metavar="FILE", help="check this card in place of the project card with the same id")
    s.add_argument("--style", metavar="FILE", help="check against this style bible in place of bibles/style.json")

    q = g.add_parser("qc", help="check rendered takes (needs ffmpeg)").add_subparsers(dest="cmd", required=True)
    s = q.add_parser("sheet", help="contact sheet of a clip at 1-2 fps")
    s.add_argument("clip")
    s.add_argument("--out")
    s.add_argument("--fps", type=float)
    s.add_argument("--cols", type=int, default=4)
    s.add_argument("--width", type=int, default=320)
    s = q.add_parser("spec", help="fps, size, aspect, length and audio against the card")
    s.add_argument("clip")
    s.add_argument("--project", required=True)
    s.add_argument("--card", required=True, help="card id, or a generation label such as 1B+1C")
    s.add_argument("--params", help="the compiled settings file used for this take")
    s.add_argument("--json", action="store_true")
    s = q.add_parser("loud", help="integrated loudness and true peak (EBU R128 meter)")
    s.add_argument("file")
    s.add_argument("--preset", choices=sorted(LOUD_PRESETS), help="delivery target (default web: -18 +/- 2 LUFS, -2 dBTP); the flags below override it")
    s.add_argument("--target", type=float, help="integrated LUFS")
    s.add_argument("--tolerance", type=float, help="LU either side")
    s.add_argument("--true-peak", type=float, help="maximum dBTP")
    s = q.add_parser("measure", help="machine checks of a take: planned cuts, frozen picture, dead air, clipping, speech where lines are planned, seam jumps")
    s.add_argument("clip")
    s.add_argument("--project")
    s.add_argument("--card", help="card id, or a generation label such as 1A+1B+1C (plans the cuts and the lines)")
    s.add_argument("--seams", help="comma list of seam times in a cut film, in seconds")
    s.add_argument("--every", type=float, help="seams every N seconds (a film cut from equal generations)")
    s.add_argument("--out", help="also write the result as JSON here")
    s.add_argument("--json", action="store_true")
    s = q.add_parser("rubric", help="write a take's checklist, or read its verdicts back as fixes")
    s.add_argument("project", nargs="?")
    s.add_argument("--card")
    s.add_argument("--clip")
    s.add_argument("--sheet")
    s.add_argument("--out")
    s.add_argument("--read", metavar="RUBRIC.json", help="read a filled rubric and print the repair plan")

    t = g.add_parser("takes", help="take records").add_subparsers(dest="cmd", required=True)
    s = t.add_parser("log", help="write takes/<card>-<n>.json")
    s.add_argument("project")
    s.add_argument("--card", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--verdict", required=True, choices=["pending", "pass", "fail", "keep-fix-in-edit"])
    s.add_argument("--file")
    s.add_argument("--seed", type=int)
    s.add_argument("--fix", help="failure code")
    s.add_argument("--change", help="the one thing changed from the previous take")
    s.add_argument("--observed", help="what the last frame shows")
    s.add_argument("--notes")
    s = t.add_parser("lastframe", help="extract the last frame for the next card's start")
    s.add_argument("clip")
    s.add_argument("--out", required=True)
    s.add_argument("--take", help="take record to update")
    s.add_argument("--observed", help="what the frame shows; written to the take record")
    v = g.add_parser("voice", help="character voices: measure, reference clips, drift checks (needs ffmpeg)").add_subparsers(dest="cmd", required=True)
    s = v.add_parser("measure", help="pitch, range, pace and speech time of a clip or a span of it")
    s.add_argument("file")
    s.add_argument("--start", type=float)
    s.add_argument("--end", type=float)
    s.add_argument("--text", help="the words said, for pace")
    s.add_argument("--json", action="store_true")
    s = v.add_parser("ref", help="cut a clean mono reference clip for a cloning engine")
    s.add_argument("file")
    s.add_argument("--out", required=True)
    s.add_argument("--start", type=float)
    s.add_argument("--end", type=float)
    s.add_argument("--rate", type=int, default=24000, help="sample rate the engine wants (default 24000)")
    s.add_argument("--text", help="the words said in the clip")
    s = v.add_parser("check", help="check bibles/voices.json, or one line against a character's references")
    s.add_argument("project")
    s.add_argument("--character")
    s.add_argument("--clip")
    s.add_argument("--start", type=float)
    s.add_argument("--end", type=float)
    s.add_argument("--text", help="the words said, for pace")
    return ap


HANDLERS = {"kb": cmd_kb, "cards": cmd_cards, "compile": cmd_compile, "continuity": cmd_continuity, "qc": cmd_qc, "takes": cmd_takes,
            "voice": cmd_voice}


def main(argv=None, ctx=None):
    a = build_parser().parse_args(argv)
    return HANDLERS[a.group](ctx or default_context(), a)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
