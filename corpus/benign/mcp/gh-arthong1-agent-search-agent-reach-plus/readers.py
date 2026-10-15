"""Public URL, RSS and YouTube caption adapters."""
from __future__ import annotations

import html
import json
import re
import shutil
from urllib.parse import parse_qs, urlsplit

import feedparser

from .transport import ReachError, fetch_bytes, run_cli, validate_limit, validate_url


async def fetch_url(url: str) -> dict:
    await validate_url(url)
    raw = await fetch_bytes("https://r.jina.ai/" + url)
    text = raw.decode("utf-8", errors="replace")
    from agent_reach.channels.web import _is_antibot_page
    if _is_antibot_page(raw):
        raise ReachError("challenge_required", "source returned an anti-bot challenge; use a site-specific reader")
    if not text.strip():
        raise ReachError("empty_response", "reader returned no content")
    return {"backend": "Jina Reader", "source_url": url, "data": {"markdown": text}}


async def rss_read(url: str, limit: int = 10) -> dict:
    validate_limit(limit)
    feed = feedparser.parse(await fetch_bytes(url))
    if not feed.entries and feed.bozo:
        raise ReachError("invalid_feed", "source is not a readable RSS/Atom feed")
    entries = [{"title": e.get("title", ""), "url": e.get("link", ""), "published": e.get("published", e.get("updated", "")), "summary": e.get("summary", "")} for e in feed.entries[:limit]]
    return {"backend": "feedparser", "source_url": url, "data": {"title": feed.feed.get("title", ""), "entries": entries}}


def parse_vtt(text: str) -> dict:
    segments = []
    words: list[str] = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n")):
        lines = block.splitlines()
        index = next((i for i, line in enumerate(lines) if " --> " in line), None)
        if index is None:
            continue
        times = lines[index].split(" --> ")
        content = html.unescape(re.sub(r"<[^>]+>", "", " ".join(lines[index + 1:]))).strip()
        if not content:
            continue
        segments.append({"start": times[0], "end": times[1].split()[0], "text": content})
        tokens = content.split()
        overlap = 0
        for n in range(min(len(words), len(tokens)), 0, -1):
            if words[-n:] == tokens[:n]:
                overlap = n
                break
        words.extend(tokens[overlap:])
    return {"text": " ".join(words), "segments": segments}


async def youtube_subtitles(url: str, languages: list[str] | None = None) -> dict:
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname not in ("youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be") or p.username or p.password or p.port not in (None, 443):
        raise ReachError("invalid_url", "use a specific public https YouTube video URL")
    if p.hostname == "youtu.be":
        video_id = p.path.strip("/")
    elif p.path == "/watch":
        ids = parse_qs(p.query, keep_blank_values=True).get("v", [])
        video_id = ids[0] if len(ids) == 1 else ""
    else:
        match = re.fullmatch(r"/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})/?", p.path)
        video_id = match[1] if match else ""
    if not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ReachError("invalid_url", "provide exactly one YouTube video ID; channels/playlists/redirects are not accepted")
    url = "https://www.youtube.com/watch?v=" + video_id
    languages = languages or ["ko", "en", "ja", "zh-Hans"]
    if not 1 <= len(languages) <= 10 or any(not re.fullmatch(r"[a-zA-Z0-9-]{2,20}", lang) for lang in languages):
        raise ReachError("invalid_input", "provide up to 10 language codes, e.g. ko,en")
    node = shutil.which("node.exe") or shutil.which("node")
    js = ["--js-runtimes", "node:" + node] if node else []
    output = await run_cli("yt-dlp", ["--ignore-config", "--no-playlist", "--skip-download", "--dump-single-json", "--no-warnings", "--socket-timeout", "10", "--retries", "0", "--extractor-retries", "0", "--extractor-args", "youtube:skip=dash,hls", *js, "--", url], timeout=45)
    info = json.loads(output)
    for automatic, group in ((False, info.get("subtitles", {})), (True, info.get("automatic_captions", {}))):
        for lang in languages:
            actual = next((key for key in group if key == lang), None)
            if actual is None:
                actual = next((key for key in group if key.startswith(lang + "-")), None)
            tracks = group.get(actual, [])
            track = next((t for t in tracks if t.get("ext") == "vtt"), None)
            if track:
                caption = parse_vtt((await fetch_bytes(track["url"])).decode("utf-8", errors="replace"))
                if not caption["segments"]:
                    raise ReachError("invalid_subtitles", "caption track contained no VTT cues")
                return {"backend": "yt-dlp", "source_url": url, "data": {"title": info.get("title"), "video_id": info.get("id"), "language": actual, "automatic": automatic, **caption}}
    raise ReachError("no_subtitles", "requested languages have no usable subtitles; audio transcription requires separate explicit configuration")
