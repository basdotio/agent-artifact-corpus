"""The voice library: named voices, each a short reference clip the engine copies.

voices/<id>/original.<ext>  the file as it was added (kept, so the clip can be prepared again differently)
voices/<id>/clip.wav        the prepared clip the engine uses: trimmed, optionally cleaned, levelled
voices/<id>/voice.json      name, language, notes, how it was prepared, and a quality report
"""
import datetime as dt
import json
import re
import shutil
from pathlib import Path

import numpy as np

from . import audio, config
from .trash import to_recycle_bin

MAX_SECONDS = 20.0   # longer clips are cut (at a pause) to this
IDEAL = (6.0, 15.0)  # what the quality report calls a good length


def _slug(name: str) -> str:
    import unicodedata
    plain = unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode()  # Lucía -> lucia
    s = re.sub(r"[^a-z0-9]+", "-", plain).strip("-")
    return s[:40] or "voice"


class Voices:
    def __init__(self, root: Path = config.VOICES):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _meta_path(self, vid: str) -> Path:
        return self.root / vid / "voice.json"

    def list(self) -> list[dict]:
        out = []
        for folder in sorted(self.root.iterdir()) if self.root.exists() else []:
            meta = folder / "voice.json"
            if folder.is_dir() and meta.exists() and (folder / "clip.wav").exists():
                try:
                    v = json.loads(meta.read_text(encoding="utf-8"))
                except ValueError:
                    continue
                if "cut_end" not in (v.get("report") or {"cut_end": None}):  # prepared before that check existed
                    self._recheck(v, folder)
                out.append(v)
        return sorted(out, key=lambda v: v["name"].lower())

    def get(self, ref: str) -> dict | None:
        """By id or by name (case-insensitive), so agents can say "narrator"."""
        if not ref:
            return None
        if (self.root / ref / "voice.json").exists() and "/" not in ref and "\\" not in ref and ".." not in ref:
            return json.loads(self._meta_path(ref).read_text(encoding="utf-8"))
        return next((v for v in self.list() if v["name"].lower() == ref.lower()), None)

    def clip(self, ref: str) -> Path | None:
        v = self.get(ref)
        return self.root / v["id"] / "clip.wav" if v else None

    def _recheck(self, v: dict, folder: Path) -> None:
        """Run the clip report again on a voice prepared by an older version (once), so its card warns about a clip
        cut off mid-word."""
        try:
            report = audio.clip_report(*audio.load(folder / "clip.wav"))
        except Exception:
            return
        v["report"], v["advice"] = report, advice(report)
        try:
            self._save(v)
        except OSError:
            pass

    def _save(self, v: dict) -> None:
        p = self._meta_path(v["id"])
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(v, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(p)

    def _unique_id(self, name: str) -> str:
        base, i = _slug(name), 2
        vid = base
        while (self.root / vid).exists():
            vid, i = f"{base}-{i}", i + 1
        return vid

    def add(self, *, name: str, filename: str, data: bytes | None = None, decoded: tuple | None = None,
            language: str = "", notes: str = "", denoise: bool = False, source: str = "clip",
            start: float | None = None, end: float | None = None, extra: dict | None = None) -> dict:
        """From file bytes (`data`), or from audio already decoded/separated (`decoded` = (samples, sr), kept as
        original.flac). A long recording with no range given uses its best 12 seconds of speech."""
        from .media import best_window
        name = name.strip()
        if not name:
            raise ValueError("Give the voice a name.")
        if self.get(name):
            raise ValueError(f"There's already a voice called “{name}”.")
        raw, sr = decoded if decoded is not None else audio.load(data)  # validates it's audio before anything is written
        if len(raw) < sr * 1.0:
            raise ValueError("That clip is shorter than a second. Use 5–15 seconds of clear speech.")
        if start is None and end is None and len(raw) > 25 * sr:
            start, end = best_window(raw, sr, 12.0)
        vid = self._unique_id(name)
        folder = self.root / vid
        folder.mkdir(parents=True)
        if decoded is not None:
            original = "original.flac"
            import soundfile as sf
            sf.write(str(folder / original), np.clip(raw, -1, 1), sr, format="FLAC")
        else:
            original = "original" + (Path(filename).suffix.lower() or ".wav")[:6]
            (folder / original).write_bytes(data)
        v = {"id": vid, "name": name, "language": language, "notes": notes.strip(), "source": source,
             "created": dt.datetime.now().isoformat(timespec="seconds"), "original": original,
             "from_file": Path(filename).name, **(extra or {})}
        try:
            self._prepare(v, raw, sr, denoise=denoise, start=start, end=end)
        except Exception:
            shutil.rmtree(folder, ignore_errors=True)
            raise
        return v

    def reprepare(self, ref: str, *, denoise: bool, start: float | None = None, end: float | None = None) -> dict:
        """Prepare the clip again from the original (e.g. with noise reduction turned on, or another part of it)."""
        v = self.get(ref)
        if not v:
            raise KeyError(ref)
        raw, sr = audio.load(self.root / v["id"] / v["original"])
        v.pop("transcript", None)  # another part of the recording says other words: heard again when S2 Pro needs it
        self._prepare(v, raw, sr, denoise=denoise, start=start, end=end)
        return v

    def _prepare(self, v: dict, raw: np.ndarray, sr: int, *, denoise: bool, start: float | None, end: float | None) -> None:
        a = raw
        if start is not None or end is not None:
            a = a[int((start or 0) * sr): int(end * sr) if end else None]
        a = audio.trim_silence(a, sr, threshold_db=-40, pad_ms=80)
        if len(a) > MAX_SECONDS * sr:
            a = a[:_cut_point(a, sr)]
        if denoise:
            a = audio.denoise(a, sr)
            a = audio.trim_silence(a, sr, threshold_db=-40, pad_ms=80)
        a = audio.fade(audio.peak_normalize(a, -1.0), sr, ms=15)
        audio.save_wav(self.root / v["id"] / "clip.wav", a, sr)
        report = audio.clip_report(a, sr)
        v.update(seconds=report["seconds"], denoised=denoise, trimmed_from=round(len(raw) / sr, 1),
                 report=report, advice=advice(report), range=[start, end] if (start or end) else None)
        self._save(v)

    def update(self, ref: str, **fields) -> dict:
        v = self.get(ref)
        if not v:
            raise KeyError(ref)
        if fields.get("name") is not None:
            name = (fields["name"] or "").strip()
            if not name:
                raise ValueError("Give the voice a name.")
            other = self.get(name)
            if other and other["id"] != v["id"]:
                raise ValueError(f"There's already a voice called “{name}”.")
            v["name"] = name
        for k in ("language", "notes"):
            if k in fields and fields[k] is not None:
                v[k] = fields[k].strip()
        if fields.get("transcript") is not None:  # what the clip says (S2 Pro copies a voice from clip + words)
            words = " ".join(fields["transcript"].split())
            if words:
                v["transcript"] = words
            else:
                v.pop("transcript", None)  # empty: Whisper hears it again the next time S2 Pro needs it
        self._save(v)
        return v

    def delete(self, ref: str) -> None:
        v = self.get(ref)
        if not v:
            raise KeyError(ref)
        to_recycle_bin(self.root / v["id"])


def _cut_point(a: np.ndarray, sr: int) -> int:
    """Where to end a long clip: a real pause between 12 s and MAX_SECONDS, so no word is cut (see
    media.pause_near), else the quietest moment there."""
    from .media import frame_db, pause_near
    db = frame_db(a, sr, 0.01)
    if len(db) < 2:
        return int(MAX_SECONDS * sr)
    k = pause_near(db, min(1600, len(db) - 1), reach_s=4.0)  # around 16 s, so between 12 and 20 s
    return int(min(max(int((k + 0.5) * 0.01 * sr), 12 * sr), MAX_SECONDS * sr))


def advice(report: dict) -> list[str]:
    tips = []
    s = report["seconds"]
    if s < 3:
        tips.append("Very short: the voice may not come through. 6–15 seconds of speech works best.")
    elif s < IDEAL[0]:
        tips.append("A bit short. 6–15 seconds of speech usually copies the voice more closely.")
    if report["snr_db"] < 20:
        tips.append("There's noticeable background noise. Try “Reduce background noise”, or use a cleaner recording.")
    if report.get("cut_end"):
        tips.append("The clip ends in the middle of a word. Some voice models then say the rest of that word before "
                    "your script. Use Edit to pick a range that ends at a pause.")
    if report["clipped"]:
        tips.append("The recording is distorted (too loud when it was made). A cleaner clip will sound better.")
    return tips
