"""Transcribe generated speech and compare it with the script, to catch stutters, repeats and spoken tags.

    export ELEVENLABS_API_KEY=...
    uv run --with requests python3 scripts/qa_speech.py assets/audio/vo/main
"""
import glob
import json
import os
import re
import sys

import requests

KEY = os.environ["ELEVENLABS_API_KEY"]


def norm(s):
    return re.sub(r"[^a-z' ]", " ", re.sub(r"\[[^\]]+\]", " ", s.lower())).split()


def transcribe(path):
    with open(path, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": KEY},
                          data={"model_id": "scribe_v1", "tag_audio_events": "true", "timestamps_granularity": "word"},
                          files={"file": (os.path.basename(path), f, "audio/mpeg")}, timeout=300)
    r.raise_for_status()
    return r.json()


def expected_texts(folder):
    lines = os.path.join(folder, "lines.json")
    if os.path.exists(lines):
        return {m["id"]: m["text"] for m in json.load(open(lines))}
    out = {}
    for j in glob.glob(os.path.join(folder, "*.json")):
        out[os.path.basename(j)[:-5]] = json.load(open(j))["text"]
    return out


for folder in sys.argv[1:]:
    exp = expected_texts(folder)
    for lid, text in exp.items():
        path = os.path.join(folder, f"{lid}.mp3")
        if not os.path.exists(path):
            continue
        d = transcribe(path)
        words = [w for w in d.get("words", []) if w.get("type") == "word"]
        events = [w["text"] for w in d.get("words", []) if w.get("type") == "audio_event"]
        got = norm(" ".join(w["text"] for w in words))
        want = norm(text)
        ok = got == want
        first = words[0]["start"] if words else None
        last = words[-1]["end"] if words else None
        print(f"{'OK ' if ok else 'BAD'} {os.path.basename(folder)}/{lid:9s} want={' '.join(want)!r} got={' '.join(got)!r} speech {first}-{last} events={events}")
