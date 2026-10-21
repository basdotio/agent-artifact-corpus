"""Generate score candidates from audio.json "musicGen" (ElevenLabs timed chunks), plus an optional Lyria take.

Section lengths are in bars at timeline.json bpm, so section changes fall on bar lines. Generate 2–3 seeds, then
measure them with scripts/analyze_music.py and pick by dynamics (quiet intro, lift, peak, drop) and grid fit.

    uv run --with requests python3 scripts/gen_music.py            # every seed in musicGen.seeds
    uv run --with requests python3 scripts/gen_music.py lyria      # Gemini Lyria 3.5 take (GEMINI_API_KEY)

Notes: music_v2/v2.5 take `chunks`; music_v1 takes `sections`; `force_instrumental` only works with a plain prompt.
"""
import base64
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from timeline import BEAT, ROOT  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "audio.json")))["musicGen"]
OUT = os.path.join(ROOT, "assets", "audio", "music")
os.makedirs(OUT, exist_ok=True)
BAR = 4 * BEAT


def eleven(seed):
    chunks = [{"text": text, "duration_ms": int(round(bars * BAR * 1000)), "positive_styles": CFG["globalStyles"] + styles,
               "negative_styles": CFG["negative"]} for _, bars, text, styles in CFG["sections"]]
    body = {"model_id": CFG.get("model", "music_v2_5"), "composition_plan": {"chunks": chunks}, "seed": seed}
    r = requests.post("https://api.elevenlabs.io/v1/music?output_format=mp3_44100_192",
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"}, json=body, timeout=900)
    if r.status_code != 200:
        print("eleven", seed, r.status_code, r.text[:400])
        return
    path = os.path.join(OUT, f"eleven_{body['model_id']}_s{seed}.mp3")
    open(path, "wb").write(r.content)
    print("wrote", path)


def lyria():
    t, lines = 0.0, []
    for name, bars, _, styles in CFG["sections"]:
        a, b = t, t + bars * BAR
        lines.append(f"[{int(a // 60)}:{a % 60:05.2f} - {int(b // 60)}:{b % 60:05.2f}] {name}: {', '.join(styles)}")
        t = b
    prompt = (f"Instrumental film score, exactly {round(60 / BEAT)} BPM in 4/4, steady tempo, {t:.0f} seconds. "
              f"{', '.join(CFG['globalStyles'])}. No vocals. Structure:\n" + "\n".join(lines))
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/interactions",
                      headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "content-type": "application/json"},
                      json={"model": "lyria-3.5", "input": prompt, "response_format": {"type": "audio"}}, timeout=900)
    if r.status_code != 200:
        print("lyria", r.status_code, r.text[:400])
        return
    n = 0
    for step in r.json().get("steps", []):
        for c in step.get("content", []):
            if c.get("data"):
                path = os.path.join(OUT, f"lyria_{n}.{'wav' if 'wav' in (c.get('mime_type') or '') else 'mp3'}")
                open(path, "wb").write(base64.b64decode(c["data"]))
                print("wrote", path)
                n += 1


if __name__ == "__main__":
    if sys.argv[1:] == ["lyria"]:
        lyria()
    else:
        for s in CFG["seeds"]:
            eleven(s)
