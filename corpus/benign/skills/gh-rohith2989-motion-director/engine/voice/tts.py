"""
Text-to-speech for narrated films, provider-agnostic, cached (re-runs never re-bill). Keys come ONLY from
environment variables — never write a key into a file, a commit or a log.

  GEMINI_API_KEY   Gemini TTS. gemini-3.8-flash-tts (+ a 300-voice library) takes delivery direction in
                   speech_metadata.style and reads ANY text aloud verbatim — never put direction in the text.
                   gemini-2.5-pro-preview-tts / gemini-3.1-flash-tts-preview take "Say warmly: …" style prompts.
  OPENAI_API_KEY   gpt-4o-mini-tts (instruction-following delivery via `instructions`).
  ELEVEN_API_KEY   ElevenLabs (eleven_v3 is the most expressive; voice ids from their library).

The script is voice/script.txt (one line of narration per line). Delivery is voice/style.txt (one paragraph).

python voice/tts.py voices [query]                       list the Gemini voice library (needs GEMINI_API_KEY)
python voice/tts.py audition <voices,...> [provider/model]   two opening lines per voice -> voice/audition/
python voice/tts.py takes <voice> <n> [provider/model]   n full takes of the script     -> voice/takes/
providers: gemini/gemini-3.8-flash-tts (default) · gemini/gemini-2.5-pro-preview-tts · openai/gpt-4o-mini-tts · eleven/eleven_v3
"""
import base64
import hashlib
import io
import json
import os
import sys
import wave
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)


def script_lines():
    p = os.path.join(HERE, "script.txt")
    if not os.path.exists(p):
        sys.exit("write voice/script.txt first: one line of narration per line (see references/voice.md)")
    return [l.strip() for l in open(p, encoding="utf-8") if l.strip()]


def style_text():
    p = os.path.join(HERE, "style.txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    return ("warm, friendly and relaxed, like a helpful colleague walking someone through it; clear and unhurried, "
            "gently smiling, natural small pauses between sentences; not salesy, not an announcer")


def key(name):
    v = os.environ.get(name)
    if not v:
        sys.exit(f"{name} is not set (export it in the shell; never write it into a file)")
    return v


def write_wav(path, pcm, rate=24000):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)


def _gemini38(text, voice, style, model):
    import requests
    content = {"type": "text", "text": text, "annotations": [{"type": "speech_metadata", "style": style}]}
    body = {"model": model, "input": [{"type": "user_input", "content": [content]}], "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": voice}]}}
    r = requests.post("https://generativelanguage.googleapis.com/v1beta/interactions",
                      headers={"x-goog-api-key": key("GEMINI_API_KEY"), "Content-Type": "application/json"}, json=body, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    audio = [c for s in r.json().get("steps", []) if s.get("type") == "model_output" for c in s.get("content", []) if c.get("type") == "audio"]
    if not audio:
        raise RuntimeError("no audio in response")
    a = audio[-1]
    data = base64.b64decode(a["data"])
    mime = a.get("mime_type") or a.get("mimeType") or ""
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    return data, rate


def _gemini_inline(text, voice, style, model):
    from google import genai
    from google.genai import types
    c = genai.Client(api_key=key("GEMINI_API_KEY"))
    resp = c.models.generate_content(
        model=model, contents=f"{style}\n\nRead only this script:\n{text}",
        config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice)))))
    part = resp.candidates[0].content.parts[0]
    data = part.inline_data.data
    data = base64.b64decode(data) if isinstance(data, str) else data
    mime = part.inline_data.mime_type or ""
    rate = int(mime.split("rate=")[1].split(";")[0]) if "rate=" in mime else 24000
    return data, rate


def _openai(text, voice, style, model):
    import requests
    r = requests.post("https://api.openai.com/v1/audio/speech", headers={"Authorization": f"Bearer {key('OPENAI_API_KEY')}"},
                      json={"model": model, "voice": voice, "input": text, "instructions": style, "response_format": "pcm"}, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.content, 24000  # pcm = 24 kHz 16-bit mono


def _eleven(text, voice, style, model):
    import requests
    r = requests.post(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_24000",
                      headers={"xi-api-key": key("ELEVEN_API_KEY"), "Content-Type": "application/json"},
                      json={"text": text, "model_id": model}, timeout=600)
    if r.status_code != 200:
        raise RuntimeError(f"{r.status_code} {r.text[:300]}")
    return r.content, 24000


def synth(text, voice, provider_model="gemini/gemini-3.8-flash-tts", style=None, out=None, nonce=""):
    """Speak `text`; returns the wav path. Cached by everything that changes the audio (+ a nonce for takes)."""
    style = style or style_text()
    provider, model = provider_model.split("/", 1)
    tag = hashlib.sha1(json.dumps([provider, model, voice, style, text, nonce]).encode()).hexdigest()[:12]
    cached = os.path.join(CACHE, f"{provider}_{voice}_{tag}.wav")
    if not os.path.exists(cached):
        if provider == "gemini":
            data, rate = (_gemini38 if "3.8" in model else _gemini_inline)(text, voice, style, model)
        elif provider == "openai":
            data, rate = _openai(text, voice, style, model)
        elif provider == "eleven":
            data, rate = _eleven(text, voice, style, model)
        else:
            raise SystemExit(f"unknown provider {provider}")
        if data[:4] == b"RIFF":
            open(cached, "wb").write(data)
        else:
            write_wav(cached, data, rate)
    if out:
        os.makedirs(os.path.dirname(out), exist_ok=True)
        open(out, "wb").write(open(cached, "rb").read())
        return out
    return cached


def list_voices(query=None):
    import requests
    H = {"x-goog-api-key": key("GEMINI_API_KEY")}
    vs, tok = [], None
    for _ in range(40):
        p = [("language_code", "en-US"), ("language_code", "en-GB"), ("page_size", "50")]
        if tok:
            p += [("page_token", tok)]
        j = requests.get("https://generativelanguage.googleapis.com/v1beta/voices", headers=H, params=p, timeout=60).json()
        vs += j.get("voices", [])
        tok = j.get("next_page_token") or j.get("nextPageToken")
        if not tok:
            break
    json.dump(vs, open(os.path.join(HERE, "voices.json"), "w"), indent=1)
    for v in vs:
        line = f'{v["id"]:22s} {v.get("gender", "")[:1]} {v.get("pitch", ""):6s} {v.get("accent", "")[:18]:18s} {v.get("persona", "")[:34]:34s} {v.get("description", "")[:120]}'
        if not query or query.lower() in line.lower():
            print(line)
    print(f"{len(vs)} voices (voice/voices.json)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    pm = "gemini/gemini-3.8-flash-tts"
    if cmd == "voices":
        list_voices(sys.argv[2] if len(sys.argv) > 2 else None)
    elif cmd == "audition":
        voices = sys.argv[2].split(",")
        pm = sys.argv[3] if len(sys.argv) > 3 else pm
        text = " ".join(script_lines()[:2])
        d = os.path.join(HERE, "audition")

        def one(v):
            try:
                return "ok " + os.path.basename(synth(text, v, pm, out=os.path.join(d, f"{v}__{pm.replace('/', '_')}.wav")))
            except Exception as e:  # noqa: BLE001
                return f"FAIL {v}: {str(e)[:200]}"

        with ThreadPoolExecutor(6) as ex:
            for line in ex.map(one, voices):
                print(line)
    elif cmd == "takes":
        v, n = sys.argv[2], int(sys.argv[3])
        pm = sys.argv[4] if len(sys.argv) > 4 else pm
        text = " ".join(script_lines())
        d = os.path.join(HERE, "takes")
        with ThreadPoolExecutor(4) as ex:
            for p in ex.map(lambda i: synth(text, v, pm, out=os.path.join(d, f"{v}_{i}.wav"), nonce=str(i)), range(n)):
                print("ok", p)
