"""
Ears for the mix: Gemini listens to a soundtrack on its own (much more reliable than in video mode) and
critiques balance, fit and edits. Audio is sent inline (32 kHz 16-bit) — an uploaded WAV was once silently
not processed and the "review" was invented, so the prompt demands a transcription first as proof.

python review/listen.py audio/out/mix.wav [--from 58 --to 80] [--ask "is the edit at 0:11 audible?"]
"""
import io
import os
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly
from google import genai
from google.genai import types

PROMPT = """First, to prove you are listening: transcribe the first sentence of any speech word for word (or, if
there is none, describe exactly what you hear in the first three seconds).
Then critique this soundtrack (music bed, sound effects, voice if present) like a senior mix engineer for a
premium product film, with timestamps:
1. Music: audible? level relative to voice? does it fit premium/professional (not childish, not cheesy)?
2. Effects: which can you hear (with times)? any too loud, too quiet, harsh, cheap, cartoonish, distracting?
3. Voice: clarity, masking, pumping, sibilance, level jumps between sentences.
4. Any edit point, click, abrupt jump, empty or cluttered moment.
5. The 3 most important fixes.{extra}"""


def main():
    a = sys.argv[1:]
    x, sr = sf.read(a[0], always_2d=True)
    if "--from" in a:
        x = x[int(float(a[a.index("--from") + 1]) * sr): int(float(a[a.index("--to") + 1]) * sr)]
    y = resample_poly(x, 2, 3, axis=0) if sr == 48000 else x
    buf = io.BytesIO()
    sf.write(buf, y.astype(np.float32), 32000 if sr == 48000 else sr, format="WAV", subtype="PCM_16")
    extra = f"\n6. Specifically: {a[a.index('--ask') + 1]}" if "--ask" in a else ""
    c = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    r = c.models.generate_content(model=os.environ.get("LISTEN_MODEL", "gemini-3.1-pro-preview"), contents=[types.Content(role="user", parts=[
        types.Part.from_bytes(data=buf.getvalue(), mime_type="audio/wav"), types.Part.from_text(text=PROMPT.format(extra=extra))])],
        config=types.GenerateContentConfig(temperature=0.2))
    print(r.text)


if __name__ == "__main__":
    main()
