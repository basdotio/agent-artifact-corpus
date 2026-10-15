"""SRT subtitles for a finished script, and transcripts (whisper.cpp).

The cue text always comes from the script itself (so names and spelling are yours); Whisper only supplies the
timing. Script words are matched to the words Whisper heard, and words it heard differently ("42" for
"forty-two") get times interpolated from their neighbours. Without a Whisper model, cues are timed from the
known segment boundaries, spreading each segment's time over its text.
"""
import contextlib
import difflib
import json
import logging
import os
import re
import subprocess
import sys
import threading
import unicodedata
import uuid
from pathlib import Path

from . import config, runtime, text as textmod

log = logging.getLogger("studio.subtitles")

MAX_LINE = 42      # characters per subtitle line (Chinese, Japanese and Korean characters count double)
MAX_CUE_CHARS = 84  # two lines
# Chinese and Japanese have no spaces: each character is a "word" for matching and timing (punctuation stays with it).
_CJK = "\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
_TOKEN = re.compile(rf"[{_CJK}][^\w\s]*|[^\s{_CJK}]+")
MAX_CUE_SECONDS = 7.0
MIN_CUE_SECONDS = 0.8


class WhisperError(Exception):
    pass


def _tokens(text: str) -> list[str]:
    """The words of a text: split at spaces, and every Chinese or Japanese character on its own."""
    return _TOKEN.findall(text)


def _join(words: list[str]) -> str:
    out = ""
    for w in words:
        out = textmod.glue(out, w)
    return out


def _norm(word: str) -> str:
    w = unicodedata.normalize("NFKC", word.lower()).replace("’", "'")
    return re.sub(r"[^\w']", "", w)


PROGRESS = re.compile(r"progress\s*=\s*(\d+)%")  # whisper-cli -pp
VK_DEVICE = re.compile(r"ggml_vulkan: (\d+) = .*?\| uma: (\d)")  # each Vulkan device; uma 1 = built into the processor
VK_USING = re.compile(r"using Vulkan(\d+) backend")
ON_CARD = re.compile(r"using (CUDA|Vulkan)\d+ backend")  # whisper-cli found the graphics card
# Windows priority: Whisper never makes the rest of the PC wait (elsewhere creationflags must be 0)
BELOW_NORMAL = 0x00004000 if sys.platform == "win32" else 0


def whisper_builds(cfg: dict) -> list[dict]:
    """The whisper-cli builds to try, best first: the graphics card one for the voice engine in use (when it's
    downloaded), then the CPU one, which is also the fallback if the graphics card run fails."""
    builds = []
    engine = config.whisper_gpu_engine(cfg)
    if engine and (config.whisper_gpu_dir(engine) / config.WHISPER_EXE).exists():
        builds.append({"exe": config.whisper_gpu_dir(engine) / config.WHISPER_EXE, "gpu": True, "engine": engine})
    cpu = config.whisper_dir() / config.WHISPER_EXE
    if cpu.exists():
        builds.append({"exe": cpu, "gpu": False, "engine": None})
    return builds


def whisper_available(cfg: dict) -> bool:
    return bool(config.subtitles_model(cfg)) and bool(whisper_builds(cfg))


def start_whisper(cfg: dict, build: dict, model_path: Path, wav: Path, language: str | None, stem: Path,
                  extra: list[str] = ()) -> subprocess.Popen:
    """Start whisper-cli writing <stem>.json, with progress lines on stderr. Low priority; on the processor it
    leaves half the threads to everything else."""
    exe, engine = build["exe"], build["engine"]
    threads = 4 if build["gpu"] else max(2, min(12, (os.cpu_count() or 4) // 2))
    args = [str(exe), "-m", str(model_path), "-f", str(Path(wav).resolve()), "-l", language or "auto",
            "-t", str(threads), "-ojf", "-of", str(stem), "-pp", *extra]
    env = None
    if engine in ("cuda", "cuda12"):  # cuBLAS and cudart come from the voice engine's folder
        env = os.environ | {"PATH": str(config.engine_dir(cfg, engine)) + os.pathsep + os.environ.get("PATH", "")}
    elif engine == "vulkan" and cfg.get("whisper_vk_device") is not None:
        args += ["-dev", str(cfg["whisper_vk_device"])]
    runtime.prepare(exe.parent)
    return subprocess.Popen(args, cwd=exe.parent, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0) | BELOW_NORMAL)


def read_whisper(proc: subprocess.Popen, on_progress=None) -> tuple[int, list[str], int | None]:
    """Wait for whisper-cli, passing its progress (0-100) on. Returns the exit code, the last lines it printed, and
    a better Vulkan device when it started on a chip built into the processor while a dedicated card is there (it's
    stopped then, to run again on the card: laptops list the built-in chip first, and it's slower than the CPU)."""
    tail, uma, better = [], {}, None
    proc.on_card = False
    for raw in proc.stderr:
        line = raw.decode("utf-8", "replace")
        if ON_CARD.search(line):
            proc.on_card = True
        if (m := PROGRESS.search(line)) and on_progress:
            on_progress(int(m[1]))
        elif m := VK_DEVICE.search(line):
            uma[int(m[1])] = m[2] == "1"
        elif (m := VK_USING.search(line)) and uma.get(int(m[1])) and not all(uma.values()):
            better = min(d for d, built_in in uma.items() if not built_in)
            proc.kill()
        tail = (tail + [line.strip()])[-5:]
    return proc.wait(), tail, better


def run_whisper(cfg: dict, wav: Path, language: str | None, model: str | None = None, on_progress=None) -> dict:
    """Run whisper-cli (on the graphics card when it can); returns its full JSON (segments with token timings)."""
    model = model or config.subtitles_model(cfg)
    builds = whisper_builds(cfg)
    if not model or not builds:
        raise WhisperError("No subtitles model installed. Download Whisper on the Models page.")
    tmp = config.DATA / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    stem = tmp / f"w{uuid.uuid4().hex[:10]}"
    model_path = Path(cfg["models_dir"]).resolve() / config.MODELS[model]["files"][0]
    try:  # the limit grows with the audio (large models on the CPU run near real time); a stuck run can't block the queue
        import soundfile as sf
        seconds = sf.info(str(wav)).duration
    except Exception:
        seconds = 600
    error = None
    for build in builds:
        code, tail, timed_out = run_build(cfg, build, model_path, wav, language, stem, 120 + seconds * 2, on_progress)
        out = stem.with_suffix(".json")
        if not code and out.exists():
            try:
                return json.loads(out.read_text(encoding="utf-8", errors="replace"))
            finally:
                out.unlink(missing_ok=True)
        out.unlink(missing_ok=True)
        error = ("Whisper took far longer than this audio needs and was stopped." if timed_out
                 else runtime.load_problem(code) or "Whisper failed: " + (tail[-1] if tail else f"code {code}"))
        if build["gpu"]:
            log.warning("Whisper on the graphics card failed (%s); trying the processor", error)
            if on_progress:
                on_progress(0)
    raise WhisperError(error)


# Set by the app: a context manager for Whisper's turn on the graphics card (S2 Pro makes room on small cards).
GPU_TURN = contextlib.nullcontext


def run_build(cfg: dict, build: dict, model_path: Path, wav: Path, language: str | None, stem: Path,
              limit: float, on_progress=None, extra: list[str] = (), on_start=None) -> tuple[int, list[str], bool]:
    """One whisper-cli run with a time limit; moves to the dedicated card (and remembers it) when Vulkan picked a
    built-in chip. on_start gets the process (so it can be stopped). Returns the exit code, the last lines it
    printed, and whether it ran out of time."""
    with GPU_TURN() if build["gpu"] else contextlib.nullcontext():
        return _run_build(cfg, build, model_path, wav, language, stem, limit, on_progress, extra, on_start)


def _run_build(cfg, build, model_path, wav, language, stem, limit, on_progress, extra, on_start):
    for _ in range(2):
        proc = start_whisper(cfg, build, model_path, wav, language, stem, extra)
        if on_start:
            on_start(proc)
        timer = threading.Timer(limit, proc.kill)
        timer.start()
        try:
            code, tail, better = read_whisper(proc, on_progress)
        finally:
            timed_out = not timer.is_alive()
            timer.cancel()
        if better is None:
            if build["gpu"] and not code and not proc.on_card:  # e.g. the voice engine's CUDA files are missing
                log.warning("Whisper's graphics card build ran on the processor: it couldn't use the card")
            return code, tail, timed_out
        log.info("Whisper started on the built-in graphics; using Vulkan device %s (the graphics card) from now on", better)
        cfg["whisper_vk_device"] = better
        config.save(cfg)
    return code, tail, timed_out


def whisper_words(result: dict) -> list[tuple[str, float, float]]:
    """Words with start/end seconds, built from Whisper's tokens (a token starting with a space starts a word)."""
    words: list[list] = []
    for seg in result.get("transcription", []):
        for tok in seg.get("tokens", []):
            t = tok.get("text", "")
            if t.startswith("[_") or not t.strip():
                continue
            start, end = tok["offsets"]["from"] / 1000, tok["offsets"]["to"] / 1000
            if re.search(f"[{_CJK}]", t):  # one word per character, the token's time shared out between them
                pieces = _tokens(t)
                for k, piece in enumerate(pieces):
                    s, e = start + (end - start) * k / len(pieces), start + (end - start) * (k + 1) / len(pieces)
                    if words and not _norm(piece):  # punctuation
                        words[-1][0] += piece
                        words[-1][2] = e
                    else:
                        words.append([piece, s, e])
                continue
            if t.startswith(" ") or not words:
                words.append([t.strip(), start, end])
            else:
                words[-1][0] += t
                words[-1][2] = end
    return [(w, s, e) for w, s, e in words if _norm(w)]


def transcript(result: dict) -> str:
    return " ".join(seg.get("text", "").strip() for seg in result.get("transcription", [])).strip()


# ---- cues ------------------------------------------------------------------------

def _script_units(script: str) -> list[list[str]]:
    """The script as subtitle-sized pieces of words: sentences, split further when too long."""
    units = []
    clean = textmod.PAUSE_TAG.sub(" ", textmod.strip_tags(textmod.clean(script)))  # subtitles show what's said
    for paragraph in clean.split("\n\n"):
        for sentence in textmod.sentences(paragraph):
            words = _tokens(sentence)
            if textmod.width(sentence) <= MAX_CUE_CHARS:
                units.append(words)
                continue
            # Split long sentences at commas where possible, then what is still too long into even pieces.
            clauses, cur = [], []
            for w in words:
                cur.append(w)
                if re.search(r"[,;:、，；：]$", w) and textmod.width(_join(cur)) > MAX_CUE_CHARS * 0.45:
                    clauses.append(cur)
                    cur = []
            for clause in clauses + [cur]:
                units += _even(clause)
    return [u for u in units if u]


def _even(words: list[str]) -> list[list[str]]:
    """Words too long for one subtitle, cut between words into even pieces (not a full one and a stub)."""
    size = textmod.width(_join(words))
    if size <= MAX_CUE_CHARS:
        return [words]
    limit = min(MAX_CUE_CHARS, size / -(-size // MAX_CUE_CHARS) * 1.1)
    out, cur = [], []
    for w in words:
        if cur and textmod.width(_join(cur + [w])) > limit:
            out.append(cur)
            cur = []
        cur.append(w)
    return out + [cur]


def _word_times(script_words: list[str], heard: list[tuple[str, float, float]]) -> list[tuple[float, float]]:
    """Time for every script word: matched to Whisper's words, gaps interpolated."""
    a = [_norm(w) for w in script_words]
    b = [_norm(w) for w, _, _ in heard]
    times: list[tuple[float, float] | None] = [None] * len(a)
    for block in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(block.size):
            _, s, e = heard[block.b + k]
            times[block.a + k] = (s, e)
    # Interpolate unmatched runs between known neighbours, in proportion to their characters.
    i = 0
    total_end = heard[-1][2] if heard else 0.0
    while i < len(a):
        if times[i] is not None:
            i += 1
            continue
        j = i
        while j < len(a) and times[j] is None:
            j += 1
        t0 = times[i - 1][1] if i > 0 else 0.0
        t1 = times[j][0] if j < len(a) else total_end
        if t1 < t0:
            t1 = t0
        chars = [max(1, len(script_words[k])) for k in range(i, j)]
        span, acc = t1 - t0, 0
        for k, c in zip(range(i, j), chars):
            s = t0 + span * acc / sum(chars)
            acc += c
            times[k] = (s, t0 + span * acc / sum(chars))
        i = j
    return [t for t in times]  # type: ignore[misc]


def _wrap(words: list[str]) -> str:
    text = _join(words)
    if textmod.width(text) <= MAX_LINE:
        return text
    # Two balanced lines, broken between words.
    best, best_score = text, 1e9
    for k in range(1, len(words)):
        l1, l2 = _join(words[:k]), _join(words[k:])
        w1, w2 = textmod.width(l1), textmod.width(l2)
        if w1 <= MAX_LINE + 6 and w2 <= MAX_LINE + 6:
            score = abs(w1 - w2) - (8 if re.search(r"[,;:、，；：]$", l1) else 0)  # after a comma reads best
            if score < best_score:
                best, best_score = f"{l1}\n{l2}", score
    return best


def build_cues(units: list[list[str]], times: list[tuple[float, float]], track_end: float) -> list[tuple[float, float, str]]:
    cues, k = [], 0
    for words in units:
        span = times[k:k + len(words)]
        k += len(words)
        start, end = span[0][0], span[-1][1]
        # Too long on screen: split the unit in two at the middle word.
        if end - start > MAX_CUE_SECONDS and len(words) > 3:
            mid = len(words) // 2
            cues.append([start, span[mid - 1][1], words[:mid]])
            cues.append([span[mid][0], end, words[mid:]])
        else:
            cues.append([start, end, words])
    for i, c in enumerate(cues):  # minimum display time, never overlapping the next cue
        nxt = cues[i + 1][0] if i + 1 < len(cues) else track_end
        if c[1] - c[0] < MIN_CUE_SECONDS:
            c[1] = min(c[0] + MIN_CUE_SECONDS, max(nxt - 0.05, c[1]))
        c[1] = min(c[1], nxt - 0.02) if i + 1 < len(cues) else min(c[1] + 0.2, track_end)
    return [(max(0.0, s), max(s, e), _wrap(w)) for s, e, w in cues]


def _ts(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[tuple[float, float, str]]) -> str:
    return "".join(f"{i}\n{_ts(s)} --> {_ts(e)}\n{t}\n\n" for i, (s, e, t) in enumerate(cues, 1))


def from_whisper(script: str, heard: list[tuple[str, float, float]], track_end: float) -> str:
    units = _script_units(script)
    words = [w for u in units for w in u]
    if not words:
        return ""
    if not heard:
        raise WhisperError("Whisper heard no speech in the audio.")
    return to_srt(build_cues(units, _word_times(words, heard), track_end))


def from_segments(segments: list[tuple[str, float, float]], track_end: float) -> str:
    """No Whisper: time each segment's words by spreading the segment's (start, end) over its characters."""
    units_all, times_all = [], []
    for text, start, end in segments:
        units = _script_units(text)
        words = [w for u in units for w in u]
        chars = [len(w) + 1 for w in words]
        total, acc = sum(chars) or 1, 0
        for c in chars:
            s = start + (end - start) * acc / total
            acc += c
            times_all.append((s, start + (end - start) * acc / total))
        units_all += units
    return to_srt(build_cues(units_all, times_all, track_end)) if units_all else ""


def match_rate(script: str, heard: list[tuple[str, float, float]]) -> float:
    """Share of script words Whisper heard the same way: a quick check that the audio says the script."""
    a = [_norm(w) for w in _tokens(textmod.PAUSE_TAG.sub(" ", textmod.strip_tags(script))) if _norm(w)]
    b = [_norm(w) for w, _, _ in heard]
    if not a:
        return 1.0
    matched = sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    return matched / len(a)
