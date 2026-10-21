"""Generate sound effects from audio.json "sfxGen" (ElevenLabs sound generation). Levels do not matter here:
the mix matches every cue to its own loudness target.

    uv run --with requests python3 scripts/gen_sfx.py [name ...]
"""
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(__file__))
from timeline import ROOT  # noqa: E402

CFG = json.load(open(os.path.join(ROOT, "audio.json")))["sfxGen"]
OUT = os.path.join(ROOT, "assets", "audio", "sfx")
os.makedirs(OUT, exist_ok=True)
for name in sys.argv[1:] or CFG:
    text, dur = CFG[name]
    r = requests.post("https://api.elevenlabs.io/v1/sound-generation?output_format=mp3_44100_192",
                      headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"], "content-type": "application/json"},
                      json={"text": text, "duration_seconds": dur, "prompt_influence": 0.6, "model_id": "eleven_text_to_sound_v2"}, timeout=300)
    if r.status_code != 200:
        print(name, r.status_code, r.text[:300])
        continue
    open(os.path.join(OUT, f"{name}.mp3"), "wb").write(r.content)
    print("wrote", name)
