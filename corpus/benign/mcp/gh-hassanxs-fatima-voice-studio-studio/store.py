"""Batches on disk: one folder per batch with its finished audio, segments/ and batch.json.

A batch holds one or more scripts. Each script is split into segments (text.split) that the engine speaks one
at a time into segments/<script>/<segment>.wav; when all of a script's segments are done they're joined into
<nn>_<title>.wav / .mp3 / .srt in the batch folder.

The folder name IS the batch name, so renaming a batch renames its folder.
"""
import datetime as dt
import json
import os
import random
import re
import shutil
import time
import uuid
from collections import Counter
from pathlib import Path

from . import config, text as textmod
from .trash import to_recycle_bin

INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
STOP_WORDS = {"a", "an", "the", "of", "in", "on", "at", "with", "and", "to", "for", "by", "from", "into",
              "el", "la", "los", "las", "de", "del", "en", "y", "un", "una", "que"}
# Settings a script can have of its own (otherwise the batch's apply)
SCRIPT_OVERRIDES = ("voice", "language", "seed")
SPLIT_KEYS = ("max_chars", "pause_segment", "pause_paragraph")


def clean_name(name: str) -> str:
    """Make a name safe as a Windows folder name: slashes become '-', other invalid characters go."""
    name = INVALID_CHARS.sub("", re.sub(r"[/\\|]", "-", name))
    name = re.sub(r"\s+", " ", name).strip()[:100].rstrip(". ")
    if not name or name.upper() in RESERVED:
        raise ValueError("That name can't be used as a folder name.")
    return name


def slug(text: str, words: int = 4) -> str:
    import unicodedata
    plain = unicodedata.normalize("NFKD", text.lower()).encode("ascii", "ignore").decode()
    kept = [w for w in re.findall(r"[a-z0-9]+", plain) if w not in STOP_WORDS]
    return "-".join(kept[:words]) or "script"


def default_name(first_text: str, now: dt.datetime) -> str:
    return now.strftime("%Y-%m-%d_%H%M_") + slug(first_text)


def settings_for(b: dict, script: dict) -> dict:
    """The batch's settings, plus a single's own output settings, plus the script's own voice/language/seed."""
    return (b["settings"] | (script.get("settings") or {})
            | {k: script[k] for k in SCRIPT_OVERRIDES if script.get(k) not in (None, "")})


def script_of(b: dict, item: dict) -> dict:
    return next(s for s in b["scripts"] if s["n"] == item["script"])


def items_of(b: dict, script: dict) -> list[dict]:
    return [it for it in b["items"] if it["script"] == script["n"]]


def script_status(b: dict, script: dict) -> str:
    """queued | running | finishing | done | failed | cancelled | partial (some segments need attention)."""
    c = Counter(it["status"] for it in items_of(b, script))
    out = script["output"]["status"]
    if c["running"]:
        return "running"
    if c["queued"]:
        return "paused" if b["paused"] else "queued"
    if c["failed"]:
        return "failed"
    if c["cancelled"]:
        return "cancelled"
    if out in ("queued", "running"):
        return "finishing"
    if out == "failed":
        return "failed"
    return "done" if out == "done" else "queued"


def batch_status(b: dict) -> str:
    states = Counter(script_status(b, s) for s in b["scripts"])
    for s in ("running", "finishing", "queued", "paused"):
        if states[s]:
            return s
    if states["failed"]:
        return "failed"
    if states["cancelled"] and not states["done"]:
        return "cancelled"
    return "done"


class Store:
    def __init__(self, root: str):
        self.set_root(root)

    def set_root(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.batches: dict[str, dict] = {}
        for folder in self.root.iterdir():
            meta = folder / "batch.json"
            if not (folder.is_dir() and meta.exists()):
                continue
            try:
                b = json.loads(meta.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            b["name"] = folder.name
            for it in b["items"]:
                if it["status"] == "running":  # app closed mid-segment: do it again
                    it["status"] = "queued"
            for s in b["scripts"]:
                if s["output"]["status"] == "running":
                    s["output"]["status"] = "queued"
            self.batches[b["id"]] = b

    def folder(self, b: dict) -> Path:
        return self.root / b["name"]

    def save(self, b: dict) -> None:
        meta = self.folder(b) / "batch.json"
        tmp = meta.with_suffix(".tmp")
        tmp.write_text(json.dumps(b, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(meta)

    def _unique(self, name: str) -> str:
        candidate, i = name, 2
        while (self.root / candidate).exists():
            candidate, i = f"{name}-{i}", i + 1
        return candidate

    # ---- scripts and segments ------------------------------------------------

    def _make_script(self, b: dict, n: int, s: dict, digits: int) -> dict:
        title = (s.get("title") or "").strip() or textmod.title_of(s["text"])
        script = {"n": n, "title": title, "text": s["text"], "stem": f"{n:0{digits}d}_{slug(title, 6)}",
                  "created": dt.datetime.now().isoformat(timespec="seconds"),
                  **{k: s[k] for k in SCRIPT_OVERRIDES if s.get(k) not in (None, "")},
                  "output": {"status": "pending", "error": None, "files": {}}}
        return script

    def _make_items(self, b: dict, script: dict, reuse: dict | None = None) -> list[dict]:
        """Split a script into queued segments. `reuse`: {(text, voice, language): old item} whose audio can be kept."""
        s = settings_for(b, script)
        split = {k: b["settings"][k] for k in SPLIT_KEYS}
        split["max_chars"] = config.part_chars(s.get("model"), split["max_chars"])  # S2 Pro: shorter parts
        parts = textmod.split(script["text"], **split)
        if not parts:
            raise ValueError(f"Script {script['n']} has no text to speak.")
        # Each script gets its own seed range; a script with a seed of its own starts exactly there.
        base = int(s["seed"]) + (0 if script.get("seed") not in (None, "") else (script["n"] - 1) * 1000)
        items = []
        for k, p in enumerate(parts, 1):
            it = {"id": f"{script['n']}.{k}", "script": script["n"], "k": k, "text": p["text"],
                  "pause_after": p["pause_after"], "paragraph": p["paragraph"], "seed": base + k,
                  "file": f"segments/{script['n']:03d}/{k:03d}.wav", "status": "queued", "error": None,
                  "duration": None, "audio_s": None, "started": None, "finished": None, "check": None}
            old = (reuse or {}).get((p["text"], s.get("voice"), s.get("language")))
            if old:
                it.update(status="done", seed=old["seed"], audio_s=old["audio_s"], duration=old["duration"],
                          finished=old["finished"], reused_from=old["file"])
            items.append(it)
        return items

    def create(self, *, name: str | None, scripts: list[dict], settings: dict, kind: str | None = None) -> dict:
        """scripts: [{"text", optional "title", "voice", "language", "seed"}]"""
        scripts = [s for s in scripts if (s.get("text") or "").strip()]
        if not scripts:
            raise ValueError("Add at least one script.")
        now = dt.datetime.now()
        first = scripts[0]
        name = self._unique(clean_name(name) if name and name.strip()
                            else default_name((first.get("title") or "").strip() or first["text"], now))
        settings = dict(settings)
        if settings.get("seed") in (None, ""):
            settings["seed"], settings["seed_random"] = random.randint(0, 2**31 - 10**6), True
        b = {"id": uuid.uuid4().hex[:12], "name": name, "created": now.isoformat(timespec="seconds"),
             "order": time.time(), "paused": False, "kind": kind, "settings": settings, "scripts": [], "items": []}
        digits = max(2, len(str(len(scripts))))
        for n, s in enumerate(scripts, 1):
            script = self._make_script(b, n, s, digits)
            b["scripts"].append(script)
            b["items"] += self._make_items(b, script)
        (self.root / name / "segments").mkdir(parents=True)
        self.batches[b["id"]] = b
        self.save(b)
        return b

    def singles_today(self) -> dict | None:
        today = dt.date.today().isoformat()
        return next((b for b in self.batches.values() if b.get("kind") == "singles" and b.get("day") == today
                     and self.folder(b).exists()), None)

    def add_single(self, *, text: str, settings: dict) -> tuple[dict, dict]:
        """One quick generation, added as a script to today's Singles batch (created if needed)."""
        now = dt.datetime.now()
        b = self.singles_today()
        if b is None:
            name = self._unique(now.strftime("%Y-%m-%d_Singles"))
            (self.root / name / "segments").mkdir(parents=True)
            b = {"id": uuid.uuid4().hex[:12], "name": name, "created": now.isoformat(timespec="seconds"),
                 "order": time.time(), "paused": False, "kind": "singles", "day": now.date().isoformat(),
                 "settings": {k: v for k, v in settings.items() if k not in SCRIPT_OVERRIDES} | {"seed": 0},
                 "scripts": [], "items": []}
            self.batches[b["id"]] = b
        n = max((s["n"] for s in b["scripts"]), default=0) + 1
        seed = settings.get("seed")
        if seed in (None, ""):
            seed = random.randint(0, 2**31 - 10**6)
        script = self._make_script(b, n, {"text": text, "voice": settings.get("voice"),
                                          "language": settings.get("language"), "seed": int(seed)}, 3)
        # Singles keep each one's own output settings (they can differ from one single to the next).
        script["settings"] = {k: settings[k] for k in ("model", "loudness", "formats", "mp3_bitrate", "subtitles", "speed", "spell_numbers") if k in settings}
        b["scripts"].append(script)
        b["items"] += self._make_items(b, script)
        b["paused"] = False
        self.save(b)
        return b, script

    def edit_script(self, b: dict, script: dict, *, text: str | None = None, title: str | None = None,
                    voice: str | None = None, language: str | None = None) -> None:
        """Change a script's text (or voice/language). Segments whose text didn't change keep their audio."""
        if title is not None and title.strip():
            script["title"] = title.strip()
        for k, v in (("voice", voice), ("language", language)):
            if v is not None:
                script[k] = v
        if text is not None:
            script["text"] = text
        old = items_of(b, script)
        reuse = {}
        before = settings_for(b, script)
        for it in old:
            if it["status"] == "done" and (self.folder(b) / it["file"]).exists():
                reuse[(it["text"], before.get("voice"), before.get("language"))] = it
        new = self._make_items(b, script, reuse)
        # Move kept audio into its new place (two passes via temporary names, so positions can swap).
        folder = self.folder(b)
        staged = {}
        for it in new:
            src = it.pop("reused_from", None)
            if src:
                tmp = folder / f"{src}.keep-{uuid.uuid4().hex[:6]}"
                shutil.copy2(folder / src, tmp)
                staged[it["file"]] = tmp
        for it in old:
            (folder / it["file"]).unlink(missing_ok=True)
        for dest, tmp in staged.items():
            (folder / dest).parent.mkdir(parents=True, exist_ok=True)
            os.replace(tmp, folder / dest)
        b["items"] = [it for it in b["items"] if it["script"] != script["n"]] + new
        b["items"].sort(key=lambda it: (it["script"], it["k"]))
        script["output"] = {"status": "pending", "error": None, "files": script["output"].get("files", {})}
        b["paused"] = False
        self.save(b)

    def edit_segment(self, b: dict, it: dict, text: str) -> None:
        text = textmod.clean(text)
        if not text:
            raise ValueError("A segment needs some text. Delete it from the script instead.")
        it.update(text=text, status="queued", error=None, check=None)
        script_of(b, it)["output"]["status"] = "pending"
        b["paused"] = False
        self.save(b)

    def rename(self, b: dict, new_name: str) -> None:
        new_name = clean_name(new_name)
        if new_name == b["name"]:
            return
        target = new_name if new_name.lower() == b["name"].lower() else self._unique(new_name)
        try:
            os.rename(self.folder(b), self.root / target)
        except OSError as e:
            raise ValueError("Windows wouldn't rename the folder. Close any Explorer window, player or editor "
                             "that has a file from it open, then try again.") from e
        b["name"] = target
        self.save(b)

    def rerun(self, b: dict) -> dict:
        """A new batch with the same scripts and settings (same seed, so it comes out the same)."""
        scripts = [{"text": s["text"], "title": s["title"], **{k: s[k] for k in SCRIPT_OVERRIDES if s.get(k) not in (None, "")}}
                   for s in b["scripts"]]
        settings = dict(b["settings"])
        if b.get("kind") == "singles":
            settings.pop("seed", None)
            for s, src in zip(scripts, b["scripts"]):
                s.update(src.get("settings") or {})
        return self.create(name=None, scripts=scripts, settings=settings)

    def delete(self, b: dict) -> None:
        folder = self.folder(b)
        if folder.exists():
            to_recycle_bin(folder)
        self.batches.pop(b["id"], None)

    def delete_script(self, b: dict, script: dict) -> None:
        """A script's finished files go to the Recycle Bin; its segments are removed."""
        folder = self.folder(b)
        for rel in script["output"].get("files", {}).values():
            if (folder / rel).exists():
                to_recycle_bin(folder / rel)
        shutil.rmtree(folder / "segments" / f"{script['n']:03d}", ignore_errors=True)
        b["items"] = [it for it in b["items"] if it["script"] != script["n"]]
        b["scripts"].remove(script)
        self.save(b)

    def file_path(self, b: dict, rel: str) -> Path | None:
        folder = self.folder(b).resolve()
        path = (folder / rel).resolve()
        if folder not in path.parents or not path.is_file():
            return None
        return path
