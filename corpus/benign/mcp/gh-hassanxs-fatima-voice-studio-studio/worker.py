"""Two queues.

The GPU queue speaks one segment at a time: API requests first, then Singles, then batches in their order.
The finishing queue turns a script whose segments are all done into its final files (joined, levelled, WAV /
MP3 / SRT). It runs on the CPU at the same time, so the GPU never waits for it.
"""
import asyncio
import collections
import datetime as dt
import logging
import random
import time
import uuid
from pathlib import Path

import numpy as np

from . import audio, config, subtitles, text as textmod
from .engine import Cancelled, Engine, EngineError
from .speech_text import Dictionary, speakable
from .store import Store, items_of, script_of, settings_for
from .voices import Voices

log = logging.getLogger("studio.worker")

RETRY_SEED = 7919  # added to a segment's seed when it's re-rolled automatically


def _now() -> str:
    return dt.datetime.now().isoformat(timespec="seconds")


def length_problem(text: str, seconds: float) -> str | None:
    """A segment far longer or shorter than its text needs usually means the model rambled, repeated or skipped."""
    expected = textmod.estimate_seconds(text)
    if seconds > expected * 2.2 + 4:
        return "longer than the text needs (it may repeat or ramble)"
    if expected > 3 and seconds < expected * 0.35:
        return "shorter than the text needs (it may skip words)"
    return None


class Worker:
    def __init__(self, store: Store, engine: Engine, voices: Voices, cfg: dict, dictionary: Dictionary | None = None):
        self.store, self.engine, self.voices, self.cfg = store, engine, voices, cfg
        self.dictionary = dictionary
        self.current: tuple[dict, dict] | None = None  # (batch, item) being spoken
        self.finishing: tuple[dict, dict] | None = None  # (batch, script) being finished
        self.finish_progress: int | None = None  # Whisper's progress on it, 0-100
        self.api_busy = False
        self._api_jobs: collections.deque = collections.deque()
        self._wake = asyncio.Event()
        self._wake_finisher = asyncio.Event()

    def notify(self) -> None:
        self._wake.set()
        self._wake_finisher.set()

    # ---- GPU queue ---------------------------------------------------------------

    async def submit(self, job) -> object:
        """Run `await job()` on the GPU ahead of batch work (API requests, voice previews)."""
        fut = asyncio.get_running_loop().create_future()
        self._api_jobs.append((job, fut))
        self._wake.set()
        return await fut

    def next_item(self) -> tuple[dict, dict] | None:
        batches = [b for b in sorted(self.store.batches.values(), key=lambda b: b["order"]) if not b["paused"]]
        batches.sort(key=lambda b: b.get("kind") != "singles")  # Singles jump the queue
        for b in batches:
            for it in b["items"]:
                if it["status"] == "queued":
                    return b, it
        return None

    async def run(self) -> None:
        asyncio.create_task(self._finisher())
        while True:
            self._wake.clear()
            if self._api_jobs:
                job, fut = self._api_jobs.popleft()
                if fut.cancelled():
                    continue
                self.api_busy = True
                try:
                    result = await job()
                    if not fut.cancelled():
                        fut.set_result(result)
                except Exception as e:
                    if not fut.cancelled():
                        fut.set_exception(e)
                finally:
                    self.api_busy = False
            elif nxt := self.next_item():
                await self._run_item(*nxt)
            else:
                await self._wake.wait()

    def spoken_text(self, text: str, s: dict) -> str:
        """What the engine reads: the pronunciation dictionary applied and numbers spelled out (the script stays as
        written). [Tags] go to models that act on them untouched, and are left out for the others."""
        lang = s.get("language") or self.cfg["default_language"]
        numbers = s.get("spell_numbers", self.cfg.get("spell_numbers", True))
        if not config.MODELS.get(s.get("model") or self.cfg["default_model"], {}).get("tags"):
            return speakable(textmod.strip_tags(text), lang, self.dictionary, numbers=numbers)
        pieces = textmod.TAG.split(text)  # the words between the tags
        tags = textmod.TAG.findall(text)
        out = [speakable(p, lang, self.dictionary, numbers=numbers) if p.strip() else p for p in pieces]
        return "".join(p + (tags[i] if i < len(tags) else "") for i, p in enumerate(out))

    def voice_clip(self, ref: str | None) -> Path | None:
        if not ref:
            return None
        clip = self.voices.clip(ref)
        if not clip:
            raise EngineError(f"The voice “{ref}” isn't in the voice library any more. Pick another voice and retry.")
        return clip

    async def _run_item(self, b: dict, it: dict) -> None:
        script = script_of(b, it)
        s = settings_for(b, script)
        it.update(status="running", error=None, started=_now(), check=None)
        self.current = (b, it)
        self.store.save(b)
        started = time.monotonic()
        out = self.store.folder(b) / it["file"]
        try:
            voice = self.voice_clip(s.get("voice"))
            spoken = self.spoken_text(it["text"], s)
            if spoken != it["text"]:
                it["spoken"] = spoken  # shown under the part: "Read as …"
            else:
                it.pop("spoken", None)
            speak = lambda seed: self.engine.speak(s["model"], spoken, language=s["language"], voice=voice,
                                                   seed=seed, out=out)
            try:
                await speak(it["seed"])
            except EngineError as e:
                if "isn't" in str(e) or "No engine" in str(e):
                    raise
                log.warning("Retrying %s/%s after: %s", b["name"], it["id"], e)  # a crash or a passing GPU hiccup
                await speak(it["seed"])
            seconds = audio.duration(out)
            if problem := length_problem(spoken, seconds):
                log.info("Segment %s/%s came out %.1fs (%s); re-rolling once", b["name"], it["id"], seconds, problem)
                it["seed"] += RETRY_SEED
                await speak(it["seed"])
                seconds = audio.duration(out)
                problem = length_problem(spoken, seconds)
                it["check"] = f"This part came out {problem}. Listen to it and regenerate if needed." if problem else None
            it.update(status="done", audio_s=round(seconds, 2))
            if all(x["status"] == "done" for x in items_of(b, script)):
                script["output"].update(status="queued", error=None)
                self._wake_finisher.set()
        except Cancelled:
            it["status"] = "cancelled"
        except Exception as e:
            log.exception("Failed %s/%s", b["name"], it["id"])
            it.update(status="failed", error=str(e) or e.__class__.__name__)
        finally:
            it.update(duration=round(time.monotonic() - started, 2), finished=_now())
            self.current = None
            if b["id"] in self.store.batches:
                try:
                    self.store.save(b)
                except OSError:  # never let a save stop the queue; the next save writes it all
                    log.exception("Couldn't save %s", b["name"])

    # ---- finishing ---------------------------------------------------------------

    def _next_to_finish(self) -> tuple[dict, dict] | None:
        for b in sorted(self.store.batches.values(), key=lambda b: (b.get("kind") != "singles", b["order"])):
            for s in b["scripts"]:
                if s["output"]["status"] == "queued" and all(it["status"] == "done" for it in items_of(b, s)):
                    return b, s
        return None

    async def _finisher(self) -> None:
        while True:
            self._wake_finisher.clear()
            nxt = self._next_to_finish()
            if not nxt:
                await self._wake_finisher.wait()
                continue
            b, script = nxt
            script["output"].update(status="running", error=None)
            self.finishing, self.finish_progress = (b, script), None
            self.store.save(b)
            try:
                result = await asyncio.to_thread(self._finish, b, script)
                if b["id"] not in self.store.batches:
                    continue
                if any(it["status"] != "done" for it in items_of(b, script)):
                    script["output"]["status"] = "pending"  # a segment was regenerated meanwhile; finish again later
                else:
                    script["output"].update(status="done", **result["output"])
                    for it in items_of(b, script):
                        it["check"] = result["checks"].get(it["id"], it.get("check"))
            except Exception as e:
                log.exception("Finishing %s/%s failed", b["name"], script["stem"])
                script["output"].update(status="failed", error=str(e) or e.__class__.__name__)
            finally:
                self.finishing = self.finish_progress = None
                if b["id"] in self.store.batches:
                    self.store.save(b)

    def _finish(self, b: dict, script: dict) -> dict:
        """Join the segments, level the loudness and write the files. Runs in a thread."""
        s = settings_for(b, script)
        folder = self.store.folder(b)
        items = items_of(b, script)
        speed = max(config.SPEED_RANGE[0], min(config.SPEED_RANGE[1], float(s.get("speed") or 1.0)))
        parts = []
        for it in items:
            a, sr = audio.load(folder / it["file"])
            parts.append((audio.time_stretch(a, sr, speed), it["pause_after"]))  # the parts keep their natural pace
        track, spans = audio.stitch(parts, sr)
        track, before = audio.normalize(track, sr, float(s.get("loudness", -16.0)))
        formats = s.get("formats") or ["wav", "mp3"]
        files = {}
        stem = script["stem"]
        wav_path = folder / f"{stem}.wav"
        tmp_wav = None
        if "wav" in formats:
            audio.save_wav(wav_path, track, sr)
            files["wav"] = wav_path.name
        else:
            wav_path.unlink(missing_ok=True)
        if "mp3" in formats:
            audio.save_mp3(folder / f"{stem}.mp3", track, sr, int(s.get("mp3_bitrate", 128)))
            files["mp3"] = f"{stem}.mp3"
        else:
            (folder / f"{stem}.mp3").unlink(missing_ok=True)
        duration = len(track) / sr
        checks, match = {}, None
        if s.get("subtitles", True):
            srt = None
            if subtitles.whisper_available(self.cfg):
                src = wav_path if "wav" in formats else (tmp_wav := config.DATA / "tmp" / f"{uuid.uuid4().hex[:8]}.wav")
                if tmp_wav:
                    tmp_wav.parent.mkdir(parents=True, exist_ok=True)
                    audio.save_wav(tmp_wav, track, sr)
                try:
                    heard = subtitles.whisper_words(subtitles.run_whisper(
                        self.cfg, src, s.get("language"), on_progress=lambda p: setattr(self, "finish_progress", p)))
                    srt = subtitles.from_whisper(script["text"], heard, duration)
                    match = round(subtitles.match_rate(script["text"], heard), 3)
                    checks = self._segment_checks(items, spans, heard)
                except subtitles.WhisperError as e:
                    log.warning("Whisper failed for %s: %s; timing subtitles from segments", stem, e)
                finally:
                    if tmp_wav:
                        tmp_wav.unlink(missing_ok=True)
            if srt is None:
                srt = subtitles.from_segments([(it["text"], a, e) for it, (a, e) in zip(items, spans)], duration)
            (folder / f"{stem}.srt").write_text(srt, encoding="utf-8")
            files["srt"] = f"{stem}.srt"
        else:
            (folder / f"{stem}.srt").unlink(missing_ok=True)
        return {"output": {"files": files, "seconds": round(duration, 2), "lufs_before": round(before, 1),
                           "match": match, "finished": _now(),
                           "spans": [[round(a, 2), round(e, 2)] for a, e in spans]},
                "checks": checks}

    @staticmethod
    def _segment_checks(items: list[dict], spans: list[tuple[float, float]], heard) -> dict:
        """Segments where Whisper heard well under the words of the text: likely a skipped or garbled part."""
        checks = {}
        for it, (start, end) in zip(items, spans):
            words = [w for w in heard if w[1] >= start - 0.3 and w[2] <= end + 0.3]
            # Whisper may write what it hears as digits ("1913") or as words ("ce jota ene ge"): take the better match.
            rate = max(subtitles.match_rate(it["text"], words), subtitles.match_rate(it.get("spoken") or it["text"], words))
            n = len(textmod.PAUSE_TAG.sub(" ", it["text"]).split())
            if n >= 4 and rate < 0.7:
                checks[it["id"]] = (f"Whisper only recognised {rate:.0%} of the words here: part of it may be skipped "
                                    "or unclear. Listen to it and regenerate if needed.")
            elif it.get("check") and "came out" in (it.get("check") or ""):
                checks[it["id"]] = it["check"]
            else:
                checks[it["id"]] = None
        return checks

    # ---- API / previews --------------------------------------------------------------

    async def speech(self, text: str, *, voice: str | None, language: str, model: str, seed: int | None = None,
                     loudness: float | None = -16.0, speed: float = 1.0, spell_numbers: bool | None = None) -> tuple[np.ndarray, int]:
        """Speak any length of text right now (ahead of batches) and return the audio. For the API and previews."""
        split = {k: self.cfg[k] for k in ("max_chars", "pause_segment", "pause_paragraph")}
        split["max_chars"] = config.part_chars(model, split["max_chars"])
        parts = textmod.split(text, **split)
        numbers = self.cfg.get("spell_numbers", True) if spell_numbers is None else spell_numbers
        for p in parts:
            p["text"] = self.spoken_text(p["text"], {"language": language, "spell_numbers": numbers, "model": model})
        speed = max(config.SPEED_RANGE[0], min(config.SPEED_RANGE[1], float(speed or 1.0)))
        if not parts:
            raise ValueError("There's no text to speak.")
        seed = random.randint(0, 2**31 - 10**6) if seed is None else int(seed)

        async def job():
            clip = self.voice_clip(voice)
            tmp = config.DATA / "tmp"
            tmp.mkdir(parents=True, exist_ok=True)
            loaded, files = [], []
            try:
                for k, p in enumerate(parts):
                    f = tmp / f"api-{uuid.uuid4().hex[:10]}.wav"
                    files.append(f)
                    await self.engine.speak(model, p["text"], language=language, voice=clip, seed=seed + k, out=f)
                    a, sr = audio.load(f)
                    loaded.append((audio.time_stretch(a, sr, speed), p["pause_after"]))
            finally:
                for f in files:
                    f.unlink(missing_ok=True)
            track, _ = audio.stitch(loaded, sr)
            if loudness is not None:
                track, _ = await asyncio.to_thread(audio.normalize, track, sr, float(loudness))
            return track, sr

        return await self.submit(job)

    # ---- batch controls ----------------------------------------------------------------

    def cancel(self, b: dict) -> None:
        for it in b["items"]:
            if it["status"] == "queued":
                it["status"] = "cancelled"
        if self.current and self.current[0] is b:
            self.engine.cancel_current()
        self.store.save(b)

    def retry(self, b: dict, item_id: str | None = None) -> None:
        for it in b["items"]:
            if it["status"] in ("failed", "cancelled") and item_id in (None, it["id"]):
                it.update(status="queued", error=None)
        for s in b["scripts"]:
            if s["output"]["status"] == "failed":
                s["output"].update(status="queued" if all(it["status"] == "done" for it in items_of(b, s)) else "pending",
                                   error=None)
        b["paused"] = False
        self.store.save(b)
        self.notify()

    def regenerate(self, b: dict, it: dict, new_seed: bool) -> None:
        """Speak one segment again; the script's files are rebuilt when it's done."""
        if self.current and self.current[1] is it:
            raise ValueError("That segment is being spoken right now.")
        if new_seed:
            it["seed"] = random.randint(0, 2**31 - 10**6)
        it.update(status="queued", error=None, check=None)
        script_of(b, it)["output"]["status"] = "pending"
        b["paused"] = False
        self.store.save(b)
        self.notify()

    def refinish(self, b: dict, script: dict) -> None:
        """Rebuild a script's files (e.g. after changing loudness or formats) without speaking it again."""
        if all(it["status"] == "done" for it in items_of(b, script)):
            script["output"].update(status="queued", error=None)
            self.store.save(b)
            self.notify()

    def is_busy_with(self, b: dict, it: dict | None = None) -> bool:
        return bool(self.current) and self.current[0] is b and (it is None or self.current[1] is it)
