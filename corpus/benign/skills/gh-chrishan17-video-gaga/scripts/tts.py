#!/usr/bin/env python3
"""Synthesize narration with Microsoft Edge TTS (rany2/edge-tts) and emit
word-level timings that drive the video-gaga timeline.

Usage:
    uv run --no-project --with edge-tts python scripts/tts.py <project-dir>
    # or, with edge-tts installed:  python3 scripts/tts.py <project-dir>

Reads  <project>/narration.json:
    {
      "voice": "zh-CN-YunxiNeural", "rate": "+0%", "pitch": "+0Hz", "volume": "+0%",
      "lang": "zh-CN",
      "segments": [ {"id": "hook", "text": "..."}, {"id": "s2", "text": "...", "voice": "..."} ]
    }

Writes <project>/build/voice/<id>.mp3 and <id>.json, plus
       <project>/build/narration.json and build/narration.js
       (window.CV_NARRATION = {...}) which the runtime picks up.

Durations come from the byte count of the CBR stream (48 kbit/s mono MP3),
which is exact; word offsets come from WordBoundary events (100-ns ticks).
Results are cached by a hash of (text, voice, rate, pitch, volume).
"""

import asyncio
import hashlib
import json
import os
import ssl
import sys
from pathlib import Path

# edge-tts pins certifi's CA bundle and ignores SSL_CERT_FILE, which breaks
# behind TLS-intercepting proxies (corporate networks, cloud sandboxes).
# Honor SSL_CERT_FILE when it is set; must run before edge_tts is imported.
_ca_file = os.environ.get("SSL_CERT_FILE")
if _ca_file and os.path.isfile(_ca_file):
    try:
        import certifi

        certifi.where = lambda: _ca_file
    except ImportError:
        pass

try:
    import edge_tts
except ImportError:  # pragma: no cover
    sys.exit(
        "edge-tts is not installed. Run with `uv run --no-project --with edge-tts python scripts/tts.py <dir>` "
        "or `pip install edge-tts`."
    )

MP3_BPS = 48_000  # audio-24khz-48kbitrate-mono-mp3
TICKS = 10_000_000

# edge-tts trusts only certifi's bundle, so behind a TLS-inspecting proxy
# (corporate networks, sandboxes) every request fails certificate checks.
# Honour the standard CA variables the way curl and requests do.
_ca = os.environ.get("SSL_CERT_FILE") or os.environ.get("REQUESTS_CA_BUNDLE")
if _ca and os.path.isfile(_ca) and hasattr(edge_tts, "communicate") and hasattr(edge_tts.communicate, "_SSL_CTX"):
    edge_tts.communicate._SSL_CTX = ssl.create_default_context(cafile=_ca)


async def synth(seg, defaults, out_dir: Path):
    voice = seg.get("voice", defaults.get("voice", "en-US-AndrewNeural"))
    rate = seg.get("rate", defaults.get("rate", "+0%"))
    pitch = seg.get("pitch", defaults.get("pitch", "+0Hz"))
    volume = seg.get("volume", defaults.get("volume", "+0%"))
    text = seg["text"].strip()
    key = hashlib.sha1(json.dumps([text, voice, rate, pitch, volume]).encode()).hexdigest()[:16]
    mp3 = out_dir / f"{seg['id']}.mp3"
    meta_path = out_dir / f"{seg['id']}.json"
    if mp3.exists() and meta_path.exists():
        meta = json.loads(meta_path.read_text("utf-8"))
        if meta.get("key") == key:
            return meta, True

    last_err = None
    for attempt in range(4):
        try:
            comm = edge_tts.Communicate(
                text, voice, rate=rate, pitch=pitch, volume=volume, boundary="WordBoundary"
            )
            audio = bytearray()
            words = []
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    audio.extend(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    start = chunk["offset"] / TICKS
                    words.append(
                        {
                            "text": chunk["text"],
                            "start": round(start, 4),
                            "end": round(start + chunk["duration"] / TICKS, 4),
                        }
                    )
            if not audio:
                raise RuntimeError("no audio received")
            mp3.write_bytes(bytes(audio))
            duration = len(audio) * 8 / MP3_BPS
            meta = {
                "id": seg["id"],
                "key": key,
                "text": text,
                "voice": voice,
                "rate": rate,
                "pitch": pitch,
                "duration": round(duration, 4),
                "words": words,
            }
            meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
            return meta, False
        except Exception as e:  # network hiccups, 403 clock-skew, etc.
            last_err = e
            await asyncio.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"TTS failed for segment {seg['id']!r}: {last_err}")


async def main(project: Path):
    spec_path = project / "narration.json"
    if not spec_path.exists():
        sys.exit(f"no narration.json in {project}")
    spec = json.loads(spec_path.read_text("utf-8"))
    out_dir = project / "build" / "voice"
    out_dir.mkdir(parents=True, exist_ok=True)

    segments = {}
    total = 0.0
    # Sequential on purpose: the service rate-limits bursts of connections.
    for seg in spec["segments"]:
        meta, cached = await synth(seg, spec, out_dir)
        total += meta["duration"]
        segments[seg["id"]] = {
            "text": meta["text"],
            "duration": meta["duration"],
            "words": meta["words"],
            "file": f"build/voice/{seg['id']}.mp3",
            "voice": meta["voice"],
        }
        tag = "cached" if cached else "synth "
        print(f"  [{tag}] {seg['id']:<14} {meta['duration']:6.2f}s  {len(meta['words']):3d} words  {meta['voice']}")

    narration = {
        "voice": spec.get("voice"),
        "lang": spec.get("lang") or (spec.get("voice", "en-US")[:5]),
        "segments": segments,
    }
    build = project / "build"
    (build / "narration.json").write_text(json.dumps(narration, ensure_ascii=False, indent=1), "utf-8")
    (build / "narration.js").write_text(
        "// generated by scripts/tts.py — do not edit\nwindow.CV_NARRATION = "
        + json.dumps(narration, ensure_ascii=False)
        + ";\n",
        "utf-8",
    )
    print(f"  narration: {len(segments)} segments, {total:.2f}s of speech → {build / 'narration.js'}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    asyncio.run(main(Path(sys.argv[1]).resolve()))
