"""Voiceover from audio.json "voice" (ElevenLabs eleven_v4), placed by word timings measured with speech-to-text.

Line fields: id, at (when speech begins, or when `anchor` begins), text (v4 audio tags like [warmly] allowed),
endBy (must finish by), speed (default 0.95), anchor (a word to land exactly on `at`), split [word, at] (one take,
two placements: the part before `word` starts at `at`; keeps one performance instead of separate fragments).
"chorus" items: {"id", "text", "at", "voice"} short lines by other voices (for example names in a roll); space them
at least one clip's speech length apart or they blur into a murmur.

    uv run --with requests python3 scripts/gen_vo.py main [alt] [chorus] [--only id,id]

Library voices work by id without adding them to the account, so no voice slot is used.
"""
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from timeline import ROOT, resolve  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "audio.json")))["voice"]
KEY = os.environ["ELEVENLABS_API_KEY"]


def tts(voice_id, text, speed, path):
    body = {"text": text, "model_id": CFG.get("model", "eleven_v4"),
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.8, "style": 0.3, "use_speaker_boost": True, "speed": speed}}
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_192",
                      headers={"xi-api-key": KEY, "content-type": "application/json"}, json=body, timeout=300)
    r.raise_for_status()
    open(path, "wb").write(r.content)


def stt_words(path):
    """Word timings measured on the generated audio: the TTS alignment is off by 0.1–0.3 s."""
    with open(path, "rb") as f:
        r = requests.post("https://api.elevenlabs.io/v1/speech-to-text", headers={"xi-api-key": KEY},
                          data={"model_id": "scribe_v1", "timestamps_granularity": "word"},
                          files={"file": (os.path.basename(path), f, "audio/mpeg")}, timeout=300)
    r.raise_for_status()
    return [{"text": w["text"], "start": w["start"], "end": w["end"]} for w in r.json().get("words", []) if w.get("type") == "word"]


def clean(w):
    return w.lower().strip(".,…!?:;\"'")


def gen(name, only):
    vid = CFG["voices"][name]
    out = os.path.join(ROOT, "assets", "audio", "vo", name)
    os.makedirs(out, exist_ok=True)
    meta_path = os.path.join(out, "lines.json")
    old = {m["id"]: m for m in json.load(open(meta_path))} if os.path.exists(meta_path) else {}
    meta = []
    for ln in CFG["lines"]:
        lid, text = ln["id"], ln["text"]
        at, end_by = resolve(ln["at"]), resolve(ln["endBy"])
        mp3 = os.path.join(out, f"{lid}.mp3")
        if only is None or lid in only or lid not in old or not os.path.exists(mp3):
            tts(vid, text, ln.get("speed", 0.95), mp3)
            words = stt_words(mp3)
        else:
            words = old[lid]["words"]
        onset, end = words[0]["start"], words[-1]["end"]
        anchor = ln.get("anchor")
        a_start = next((w["start"] for w in words if anchor and clean(w["text"]) == anchor), onset)
        place = at - (a_start if anchor else onset)
        parts = [{"from": 0.0, "to": None, "place": round(place, 3)}]
        speech = [place + onset, place + end]
        if ln.get("split"):
            word, head_at = ln["split"][0], resolve(ln["split"][1])
            i = next(k for k, w in enumerate(words) if clean(w["text"]) == word)
            cut = (words[i - 1]["end"] + words[i]["start"]) / 2
            parts = [{"from": 0.0, "to": round(cut, 3), "place": round(head_at - onset, 3)}, {"from": round(cut, 3), "to": None, "place": round(place, 3)}]
            speech = [head_at, place + end]
        fits = speech[1] <= end_by
        meta.append({"id": lid, "text": text, "words": words, "onset": onset, "end": end, "parts": parts,
                     "speech": [round(speech[0], 3), round(speech[1], 3)], "endBy": end_by, "fits": fits})
        print(f"{name:6s} {lid:10s} speech {speech[0]:6.2f}–{speech[1]:6.2f} by {end_by:6.2f} {'ok' if fits else 'LONG → shorten, speed up, or start earlier'}")
    json.dump(meta, open(meta_path, "w"), indent=1)


def gen_chorus():
    out = os.path.join(ROOT, "assets", "audio", "vo", "chorus")
    os.makedirs(out, exist_ok=True)
    meta = []
    for c in CFG.get("chorus", []):
        mp3 = os.path.join(out, f"{c['id']}.mp3")
        tts(c["voice"], c["text"], c.get("speed", 0.95), mp3)
        words = stt_words(mp3)
        onset = words[0]["start"] if words else 0.0
        meta.append({"id": c["id"], "place": round(resolve(c["at"]) + 0.03 - onset, 3), "words": words,
                     "speech": words[-1]["end"] - onset if words else 0})
        print(f"chorus {c['id']:10s} heard {[w['text'] for w in words]}")
    json.dump(meta, open(os.path.join(out, "lines.json"), "w"), indent=1)


if __name__ == "__main__":
    args = sys.argv[1:]
    only = None
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))
        args = args[: args.index("--only")]
    for a in args or ["main"]:
        gen_chorus() if a == "chorus" else gen(a, only)
