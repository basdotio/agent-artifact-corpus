#!/usr/bin/env python3
"""Transcribe video/audio URLs or local files to .txt + .srt, locally.

Human subtitles when the site has them (yt-dlp), otherwise ffmpeg -> whisper.cpp.
Stdlib only; shells out to yt-dlp, ffmpeg, ffprobe, whisper-cli and (for the
one-time model download) curl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

DEFAULT_MODEL = "large-v3-turbo-q5_0"
MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-{name}.bin"

INSTALL_HINTS = {
    "ffmpeg": {"darwin": "brew install ffmpeg", "other": "sudo apt install ffmpeg"},
    "ffprobe": {"darwin": "brew install ffmpeg", "other": "sudo apt install ffmpeg"},
    "whisper-cli": {
        "darwin": "brew install whisper-cpp",
        "other": "brew install whisper-cpp, or build https://github.com/ggml-org/whisper.cpp",
    },
    "yt-dlp": {
        "darwin": "brew install yt-dlp",
        "other": 'pipx install "yt-dlp[default]" (YouTube also needs deno)',
    },
    "curl": {"darwin": "curl ships with macOS", "other": "sudo apt install curl"},
}


class InputError(Exception):
    """A failure confined to one input: reported as FAIL, the batch continues."""


class PreflightError(Exception):
    """A failure that stops the run before any input is processed (exit 2)."""


@dataclass(frozen=True)
class Source:
    raw: str
    kind: Literal["url", "file"]


@dataclass(frozen=True)
class Meta:
    title: str
    channel: str | None
    date: str | None
    duration_s: float | None
    source: str  # canonical URL or absolute path; also the input's identity
    language: str | None
    subtitle_langs: tuple[str, ...]


@dataclass(frozen=True)
class Cue:
    start: str
    end: str
    text: str


@dataclass(frozen=True)
class Provenance:
    kind: Literal["subtitles", "whisper"]
    detail: str  # subtitle language or model name


@dataclass(frozen=True)
class Result:
    input: str
    status: Literal["OK", "SKIP", "FAIL"]
    provenance: Provenance | None = None
    txt_path: Path | None = None
    error: str | None = None


def install_hint(tool: str) -> str:
    platform = "darwin" if sys.platform == "darwin" else "other"
    return INSTALL_HINTS[tool][platform]


_SECRET_PARAM = re.compile(
    r"([?&](?:[\w.-]*(?:token|key|sig|signature|secret|password|passwd|auth|credential)[\w.-]*"
    r"|x-amz-[\w-]+)=)[^&#\s]*",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    """Hide URL credentials (scheme://user:pass@host) and secret-looking query parameters."""
    text = re.sub(r"([a-z][a-z0-9+.-]*://)[^/\s@]+@", r"\1***@", text, flags=re.IGNORECASE)
    return _SECRET_PARAM.sub(r"\1***", text)


def log(message: str) -> None:
    """The one diagnostic sink: stderr, so stdout carries only result lines."""
    print(message, file=sys.stderr)


def progress(index: int, total: int, stage: str, stem: str) -> None:
    log(f"[{index}/{total}] {stage} {stem}")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    tool = cmd[0]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, errors="replace", check=False)
    except OSError as e:
        raise InputError(f"{tool} could not run: {e}") from e
    if proc.returncode != 0:
        lines = proc.stderr.strip().splitlines()
        reason = redact(lines[-1]) if lines else f"exit {proc.returncode}"
        suffix = " (if the site changed, update yt-dlp)" if tool == "yt-dlp" else ""
        raise InputError(f"{tool} failed: {reason}{suffix}")
    return proc


def classify(raw: str) -> Source:
    if raw.startswith(("http://", "https://")):
        return Source(raw, "url")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", raw):
        raise InputError("unsupported scheme (only http and https URLs)")
    try:
        is_file = Path(raw).expanduser().is_file()
    except OSError as e:
        raise InputError(f"cannot access: {e}") from e
    if is_file:
        return Source(raw, "file")
    raise InputError("not found")


def preflight(sources: list[Source], model_arg: str) -> Path:
    needed = ["ffmpeg", "ffprobe", "whisper-cli"]
    if any(s.kind == "url" for s in sources):
        needed.append("yt-dlp")
    missing = [tool for tool in needed if shutil.which(tool) is None]
    if missing:
        lines = [f"  {tool}: {install_hint(tool)}" for tool in missing]
        raise PreflightError("missing dependencies:\n" + "\n".join(lines))
    try:
        return resolve_model(model_arg)
    except OSError as e:
        raise PreflightError(f"model cache error: {e}") from e


def cache_dir() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "transcribe" / "models"


def resolve_model(arg: str) -> Path:
    if "/" in arg or arg.endswith(".bin"):
        path = Path(arg).expanduser()
        if not path.is_file():
            raise PreflightError(f"model file not found: {path}")
        return path
    path = cache_dir() / f"ggml-{arg}.bin"
    if not path.is_file():
        download_model(arg, path)
    return path


def download_model(name: str, dest: Path) -> None:
    if shutil.which("curl") is None:
        hint = install_hint("curl")
        raise PreflightError(f"model {name} is not cached and curl is missing: {hint}")
    url = MODEL_URL.format(name=name)
    part = dest.with_name(dest.name + ".part")
    log(f"downloading model {name} (one-time) to {dest}")
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["curl", "-fL", "--retry", "3", "-#", "-o", str(part), url]
        code = subprocess.run(cmd, check=False).returncode
        if code != 0:
            raise PreflightError(f"model download failed (curl exit {code}): {url}")
        os.replace(part, dest)
    finally:
        remove_quietly(part)


def remove_quietly(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass


def as_duration(value: object) -> float | None:
    try:
        seconds = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def as_text(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


# Every yt-dlp call: ignore the user's config (it can add outputs or post-processing),
# never expand playlists, keep stderr to real errors.
YT_DLP = ("yt-dlp", "--ignore-config", "--no-playlist", "--no-warnings")


def probe_url(url: str) -> Meta:
    proc = run([*YT_DLP, "-J", "--flat-playlist", url])
    try:
        info = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise InputError("yt-dlp returned unreadable metadata") from e
    if not isinstance(info, dict):
        raise InputError("yt-dlp returned unexpected metadata")
    if info.get("_type") == "playlist":
        raise InputError("playlist URLs are not supported; pass video URLs")
    subs = info.get("subtitles")
    langs = tuple(sorted(k for k in subs if k != "live_chat")) if isinstance(subs, dict) else ()
    upload = as_text(info.get("upload_date"))
    date = f"{upload[:4]}-{upload[4:6]}-{upload[6:8]}" if upload and len(upload) == 8 else None
    return Meta(
        title=as_text(info.get("title")) or as_text(info.get("id")) or "untitled",
        channel=as_text(info.get("channel")) or as_text(info.get("uploader")),
        date=date,
        duration_s=as_duration(info.get("duration")),
        source=as_text(info.get("webpage_url")) or url,
        language=as_text(info.get("language")),
        subtitle_langs=langs,
    )


def probe_file(path: Path) -> Meta:
    proc = run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json",
                str(path)])
    try:
        fmt = json.loads(proc.stdout).get("format")
    except (json.JSONDecodeError, AttributeError):
        fmt = None
    return Meta(
        title=path.stem,
        channel=None,
        date=None,
        duration_s=as_duration(fmt.get("duration")) if isinstance(fmt, dict) else None,
        source=str(path),
        language=None,
        subtitle_langs=(),
    )


def stem_for(meta: Meta) -> str:
    """Readable slug of the title plus a hash of the input's identity.

    Site-supplied ids are neither unique across sites nor filename-safe, so the
    canonical URL / absolute path is hashed instead.
    """
    ascii_title = unicodedata.normalize("NFKD", meta.title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:60].rstrip("-")
    digest = hashlib.sha1(meta.source.encode()).hexdigest()[:8]
    return f"{slug}-{digest}" if slug else digest


def pick_subtitle_lang(meta: Meta, lang_arg: str) -> str | None:
    target = meta.language if lang_arg == "auto" else lang_arg
    if target is None:
        return meta.subtitle_langs[0] if len(meta.subtitle_langs) == 1 else None
    if target in meta.subtitle_langs:
        return target
    base = target.split("-")[0]
    matches = [k for k in meta.subtitle_langs if k.split("-")[0] == base]
    return matches[0] if matches else None


def only_artifact(tmp: Path, pattern: str, producer: str) -> Path:
    found = sorted(tmp.glob(pattern))
    if len(found) != 1:
        raise InputError(f"{producer} produced {len(found)} files matching {pattern}, expected 1")
    return found[0]


def fetch_subtitles(url: str, lang: str, tmp: Path) -> str:
    run([*YT_DLP, "--skip-download", "--write-subs", "--sub-langs", lang,
         "--convert-subs", "srt", "-o", str(tmp / "sub"), url])
    return only_artifact(tmp, "sub*.srt", "yt-dlp").read_text(encoding="utf-8", errors="replace")


def fetch_audio(url: str, tmp: Path) -> Path:
    # Named source.*, never audio.*: a WAV download would collide with the conversion target.
    run([*YT_DLP, "-f", "bestaudio/best", "-o", str(tmp / "source.%(ext)s"), url])
    return only_artifact(tmp, "source.*", "yt-dlp")


def to_wav(src: Path, tmp: Path) -> Path:
    wav = tmp / "audio.wav"
    run(["ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(src),
         "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", str(wav)])
    if not wav.is_file() or wav.stat().st_size == 0:
        raise InputError("ffmpeg produced no audio")
    return wav


def transcribe_wav(wav: Path, model: Path, lang: str, tmp: Path) -> str:
    run(["whisper-cli", "-m", str(model), "-f", str(wav), "-l", lang, "-osrt",
         "-of", str(tmp / "w"), "-np"])
    # whisper-cli can exit 0 without writing anything (e.g. unreadable audio).
    srt = tmp / "w.srt"
    if not srt.is_file():
        raise InputError("whisper-cli produced no transcript")
    return srt.read_text(encoding="utf-8", errors="replace")


_TIMESTAMP = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})$")
_ARROW = re.compile(r"^\s*(\S+)\s*-->\s*(\S+)(?:\s.*)?$")


def _seconds(stamp: str) -> float | None:
    match = _TIMESTAMP.match(stamp)
    if match is None:
        return None
    hours, minutes, secs, millis = match.groups()
    if int(minutes) > 59 or int(secs) > 59:
        return None
    return int(hours) * 3600 + int(minutes) * 60 + int(secs) + int(millis.ljust(3, "0")) / 1000


def _timing(line: str) -> Cue | None:
    """The line as an empty-bodied Cue if it is a valid timing line, else None."""
    arrow = _ARROW.match(line)
    if arrow is None:
        return None
    start, end = _seconds(arrow.group(1)), _seconds(arrow.group(2))
    if start is None or end is None or end < start:
        return None
    return Cue(arrow.group(1), arrow.group(2), "")


def parse_srt(text: str) -> list[Cue]:
    """Parse SRT by position, not by blank lines or arrows alone.

    ffmpeg-converted subtitles can hold blank lines inside a cue, and dialogue can contain
    "-->" or be a bare number. So only a fully valid timing line opens a cue; a number is
    an index only at the start of a block with a valid timing line right after it; every
    other line is cue text. Text before the first cue means the input is not SRT.
    """
    lines = text.lstrip("﻿").replace("\r\n", "\n").split("\n")
    cues: list[Cue] = []
    current: Cue | None = None
    body: list[str] = []
    block_start = True
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            block_start = True
            continue
        is_index = (block_start and stripped.isdigit()
                    and i + 1 < len(lines) and _timing(lines[i + 1]) is not None)
        block_start = False
        if is_index:
            continue
        timing = _timing(line)
        if timing is not None:
            _append_cue(cues, current, body)
            current, body = timing, []
        elif current is None:
            kind = "bad timing line" if "-->" in stripped else "text before the first timing line"
            raise InputError(f"malformed subtitles: {kind} {stripped[:40]!r}")
        else:
            body.append(line)
    _append_cue(cues, current, body)
    return cues


# Formatting tags that SRT (and ffmpeg's SRT/VTT conversions) carry; other angle-bracket
# text, e.g. "x < 5 and y > 3", is dialogue.
_FORMAT_TAG = re.compile(r"</?(?:i|b|u|s|font|c|v|lang|ruby|rt)(?:[\s.][^<>]*)?>", re.IGNORECASE)


def _append_cue(cues: list[Cue], timing: Cue | None, body: list[str]) -> None:
    if timing is None:
        return
    text = " ".join(_FORMAT_TAG.sub("", " ".join(body)).split())
    if text:
        cues.append(Cue(timing.start, timing.end, text))


def cue_lines(cues: list[Cue]) -> list[str]:
    lines: list[str] = []
    for cue in cues:
        if not lines or lines[-1] != cue.text:
            lines.append(cue.text)
    return lines


def format_duration(seconds: float) -> str:
    total = round(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s" if hours else f"{minutes}m{secs:02d}s"


def format_provenance(prov: Provenance | None) -> str:
    return f"{prov.kind}:{prov.detail}" if prov else "-"


def render_txt(meta: Meta, prov: Provenance, lines: list[str]) -> str:
    header = [f"title: {meta.title}"]
    if meta.channel:
        header.append(f"channel: {meta.channel}")
    if meta.date:
        header.append(f"date: {meta.date}")
    if meta.duration_s is not None:
        header.append(f"duration: {format_duration(meta.duration_s)}")
    header += [f"source: {redact(meta.source)}", f"transcript: {format_provenance(prov)}", "---"]
    return "\n".join(header + lines) + "\n"


def format_result(result: Result) -> str:
    """One line, three tab-separated fields; tabs and newlines inside a field become spaces."""
    detail = str(result.txt_path) if result.txt_path else (result.error or "")
    fields = [result.status, format_provenance(result.provenance), redact(detail)]
    return "\t".join(re.sub(r"[\t\r\n]+", " ", field) for field in fields)


def publish(out: Path, stem: str, srt: str, txt: str) -> None:
    """Replace <stem>.srt/.txt so that a present .txt always means a complete, matching pair.

    Both files are staged first; the old .txt (the completion marker) is removed before
    the .srt is replaced, and the new .txt lands last. Assumes a single writer per <out>.
    """
    srt_tmp, txt_tmp = out / f".{stem}.srt.tmp", out / f".{stem}.txt.tmp"
    try:
        srt_tmp.write_text(srt, encoding="utf-8")
        txt_tmp.write_text(txt, encoding="utf-8")
        (out / f"{stem}.txt").unlink(missing_ok=True)
        os.replace(srt_tmp, out / f"{stem}.srt")
        os.replace(txt_tmp, out / f"{stem}.txt")
    finally:
        remove_quietly(srt_tmp)
        remove_quietly(txt_tmp)


@dataclass(frozen=True)
class Options:
    out: Path
    lang: str
    force: bool
    model: Path


def process(source: Source, opts: Options, index: int, total: int) -> Result:
    try:
        return _process(source, opts, index, total)
    except OSError as e:
        raise InputError(f"filesystem error: {e}") from e


def _process(source: Source, opts: Options, index: int, total: int) -> Result:
    is_url = source.kind == "url"
    meta = probe_url(source.raw) if is_url else probe_file(Path(source.raw).expanduser().resolve())
    stem = stem_for(meta)
    txt_path = opts.out / f"{stem}.txt"
    if txt_path.exists() and not opts.force:
        return Result(source.raw, "SKIP", txt_path=txt_path)
    with tempfile.TemporaryDirectory(prefix="transcribe-") as tmp_name:
        tmp = Path(tmp_name)
        lang = pick_subtitle_lang(meta, opts.lang) if is_url else None
        if lang:
            progress(index, total, f"subtitles:{lang}", stem)
            srt, prov = fetch_subtitles(source.raw, lang, tmp), Provenance("subtitles", lang)
        else:
            if is_url:
                progress(index, total, "download", stem)
            media = fetch_audio(source.raw, tmp) if is_url else Path(meta.source)
            progress(index, total, "whisper", stem)
            srt = transcribe_wav(to_wav(media, tmp), opts.model, opts.lang, tmp)
            prov = Provenance("whisper", opts.model.stem.replace("ggml-", "", 1))
    lines = cue_lines(parse_srt(srt))
    if not lines:
        raise InputError("empty transcript (no speech detected)")
    publish(opts.out, stem, srt, render_txt(meta, prov, lines))
    return Result(source.raw, "OK", provenance=prov, txt_path=txt_path)


def classify_or_fail(raw: str) -> Source | Result:
    try:
        return classify(raw)
    except InputError as e:
        return Result(raw, "FAIL", error=str(e))


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("inputs", nargs="+", metavar="INPUT", help="URL or local media file")
    parser.add_argument("-o", "--out", type=Path, default=Path("transcripts"),
                        help="output directory (default: ./transcripts)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"whisper.cpp model name or path to a .bin (default: {DEFAULT_MODEL})")
    parser.add_argument("--lang", default="auto", help="spoken language code, or auto (default)")
    parser.add_argument("--force", action="store_true", help="re-transcribe even if outputs exist")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    items = [classify_or_fail(raw) for raw in args.inputs]
    try:
        args.out.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        log(f"transcribe: cannot create output directory: {e}")
        return 2
    try:
        model = preflight([i for i in items if isinstance(i, Source)], args.model)
    except PreflightError as e:
        log(f"transcribe: {e}")
        return 2
    opts = Options(out=args.out, lang=args.lang, force=args.force, model=model)
    results = []
    for n, item in enumerate(items, 1):
        if isinstance(item, Result):
            results.append(item)
            continue
        try:
            results.append(process(item, opts, n, len(items)))
        except InputError as e:
            results.append(Result(item.raw, "FAIL", error=str(e)))
    for result in results:
        print(format_result(result))
    return 1 if any(r.status == "FAIL" for r in results) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
