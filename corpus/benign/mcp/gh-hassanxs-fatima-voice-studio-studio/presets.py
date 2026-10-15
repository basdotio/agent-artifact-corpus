"""Channel presets (data/presets.json): a voice, language, speed, loudness, pauses and output files saved under a
name, so a channel's settings are one click on the Create page (and one word for an agent)."""
import datetime as dt
import json
import re
import threading
import uuid
from pathlib import Path

from . import config

FIELDS = ("voice", "language", "model", "speed", "loudness", "formats", "subtitles", "pause_paragraph",
          "pause_segment", "max_chars", "spell_numbers")


class Presets:
    def __init__(self, path: Path = config.DATA / "presets.json"):
        self.path = path
        self._lock = threading.Lock()
        self.items: list[dict] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(self.items, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)

    def list(self) -> list[dict]:
        return sorted(self.items, key=lambda p: p["name"].lower())

    def get(self, ref: str) -> dict | None:
        if not ref:
            return None
        return next((p for p in self.items if p["id"] == ref or p["name"].lower() == ref.lower()), None)

    def save(self, name: str, settings: dict) -> dict:
        """Create a preset, or update the one with the same name."""
        name = re.sub(r"\s+", " ", name).strip()[:60]
        if not name:
            raise ValueError("Give the preset a name, e.g. your channel's.")
        values = {k: settings[k] for k in FIELDS if k in settings and settings[k] not in (None, "")}
        with self._lock:
            p = self.get(name)
            if p:
                p.update(settings=values, updated=dt.datetime.now().isoformat(timespec="seconds"))
            else:
                p = {"id": uuid.uuid4().hex[:8], "name": name, "settings": values,
                     "created": dt.datetime.now().isoformat(timespec="seconds")}
                self.items.append(p)
            self._save()
        return p

    def delete(self, ref: str) -> None:
        with self._lock:
            p = self.get(ref)
            if not p:
                raise KeyError(ref)
            self.items.remove(p)
            self._save()
