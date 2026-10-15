"""
A second pair of eyes: Gemini watches a render (picture + sound) and critiques it like a demanding creative
director. Key from GEMINI_API_KEY. Always include a PROOF question (what text is typed, what is said at 0:20,
what colour is the button) — once, a model "reviewed" a file it never processed, inventing the whole critique.

python review/watch.py renders/preview.mp4 ["proof question"] [--brief "what the film must do"] [--model m]

Know its blind spots: video is sampled at ~1 frame per second (fast slides and growing rows read as "hard cuts"
and "pop-ins" — verify those with tools/strip.py before acting), and quiet UI sounds are under-heard in video
mode (judge the mix with review/listen.py instead). Treat its notes as leads; verify each against frames.
"""
import os
import sys
import time

from google import genai
from google.genai import types

TEMPLATE = """First, to prove you watched and listened, answer: {proof}

Then act as a demanding creative director reviewing this video. {brief}
Your video sampling may be about 1 frame per second, so do not report fast transitions as "hard cuts" or
animations as "pop-ins" unless you are certain. Give a frank, specific critique with timestamps (mm:ss):
1. SYNC: moments where what is said and what is shown disagree.
2. CLARITY: anything a first-time viewer could misunderstand or miss; anything too small or too fast to read.
3. CRAFT: anything cheap, cluttered, awkward, generic or unfinished; and the strongest moments.
4. SOUND: voice, music and effects — balance and fit.
5. The 5 highest-impact fixes, in order. No generic praise."""


def main():
    a = sys.argv[1:]
    path = a[0]
    proof = next((x for x in a[1:] if not x.startswith("--") and a[a.index(x) - 1] not in ("--brief", "--model")), "What words appear on screen in the first five seconds?")
    brief = a[a.index("--brief") + 1] if "--brief" in a else ""
    model = a[a.index("--model") + 1] if "--model" in a else os.environ.get("WATCH_MODEL", "gemini-3.1-pro-preview")
    c = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    f = c.files.upload(file=path)
    while f.state and f.state.name == "PROCESSING":
        time.sleep(3)
        f = c.files.get(name=f.name)
    if f.state and f.state.name == "FAILED":
        sys.exit("upload failed")
    r = c.models.generate_content(model=model, contents=[types.Content(role="user", parts=[
        types.Part.from_uri(file_uri=f.uri, mime_type=f.mime_type), types.Part.from_text(text=TEMPLATE.format(proof=proof, brief=brief))])],
        config=types.GenerateContentConfig(temperature=0.3))
    print(r.text)
    try:
        c.files.delete(name=f.name)
    except Exception:  # noqa: BLE001
        pass


if __name__ == "__main__":
    main()
