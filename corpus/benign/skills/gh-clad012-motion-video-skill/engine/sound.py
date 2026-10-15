"""Soundtrack for a motion-video project: music, sound effects and voices.

    python engine/sound.py <project>            build/soundtrack.wav from the project's cues
    python engine/sound.py --gallery <folder>   every effect and every music style, as MP3s

Reads build/meta.json and build/cues.json (exported by the renderer) and the
voice files. Music comes from music.py (story.json music.style) or from your
own file (music.file); effects come from sfx.py, or from your own files placed
with a scene's "sounds": [{"at": ..., "file": "sounds/whatever.wav"}].
The music ducks under every voice line; the mix peaks at -1 dBFS.
"""
import json
import os
import subprocess
import sys

import numpy as np
from scipy.io import wavfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import music as music_lib  # noqa: E402
import sfx as sfx_lib  # noqa: E402

SR = sfx_lib.SR


def ffmpeg_path():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    from shutil import which
    if which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def load_audio(path, channels=1):
    raw = subprocess.run([ffmpeg_path(), "-loglevel", "error", "-i", path, "-f", "f32le", "-ac", str(channels), "-ar", str(SR), "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32).astype(np.float64)
    return a.reshape(-1, channels) if channels > 1 else a


def place(buf, sig, at, gain=1.0, pan=0.0):
    i = int(round(at * SR))
    if i >= len(buf) or len(sig) == 0:
        return
    if i < 0:
        sig, i = sig[-i:], 0
    sig = sig[: len(buf) - i]
    if sig.ndim == 2:
        buf[i : i + len(sig)] += sig * gain
        return
    buf[i : i + len(sig), 0] += sig * gain * np.cos((pan + 1) * np.pi / 4)
    buf[i : i + len(sig), 1] += sig * gain * np.sin((pan + 1) * np.pi / 4)


def finish(mix, fade_s=0.8):
    n_fade = int(SR * min(fade_s, len(mix) / SR / 4))
    if n_fade:
        mix[-n_fade:] *= np.linspace(1, 0, n_fade)[:, None]
    mix = np.tanh(mix * 1.1) / np.tanh(1.1)
    peak = np.max(np.abs(mix))
    return mix * (10 ** (-1 / 20) / peak) if peak > 0 else mix


def write_wav(path, mix):
    wavfile.write(path, SR, (mix * 32767).astype(np.int16))


def build(project):
    build_dir = os.path.join(project, "build")
    meta = json.load(open(os.path.join(build_dir, "meta.json")))
    cues = json.load(open(os.path.join(build_dir, "cues.json")))
    vpath = os.path.join(project, "voices", "voices.json")
    voices = json.load(open(vpath, encoding="utf8")) if os.path.exists(vpath) else {}
    m = meta["music"]
    n = int(SR * meta["duration"]) + 1
    rng = np.random.default_rng(7)
    key = -9 + {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": -3, "A#": -2, "Bb": -2, "B": -1}.get(m.get("key", "C"), 0)

    # Music: your own file, looped and faded, or the synthesised style.
    bed = np.zeros((n, 2))
    if m.get("enabled", True):
        if m.get("file"):
            track = load_audio(os.path.join(project, m["file"]), 2)
            reps = int(np.ceil(n / len(track)))
            bed = np.tile(track, (reps, 1))[:n] * 0.8
            fade = int(SR * 1.5)
            bed[-fade:] *= np.linspace(1, 0, fade)[:, None]
        else:
            bed = music_lib.render_music(meta, rng)

    effects = np.zeros((n, 2))
    voice = np.zeros((n, 2))
    speech = []
    for idx, c in enumerate(cues):
        kind, at, g = c["kind"], c["t"], c.get("gain", 1.0)
        pan = float(np.clip(rng.normal(0, 0.25), -0.6, 0.6))
        if kind == "voice":
            line = voices.get(c["key"], {})
            if line.get("file") and os.path.exists(os.path.join(project, line["file"])):
                v = level_voice(load_audio(os.path.join(project, line["file"])))
                place(voice, v, at, 1.0)
                speech.append((at + line["speechStart"], c["end"], c["key"]))
            continue
        if kind == "file" or c.get("file"):
            place(effects, load_audio(os.path.join(project, c["file"])), at, g, 0)
            continue
        if not m.get("sfx", True) and not c.get("custom"):
            continue
        if kind not in sfx_lib.SFX:
            print(f"! unknown sound kind '{kind}' at {at:.2f}s (see docs/sounds.md)")
            continue
        base = sfx_lib.SFX[kind][1]
        params = {k: c[k] for k in ("pitch", "dur", "from", "to", "semis") if k in c}
        if kind == "whoosh":
            at -= params.get("dur", 0.4) * 0.3
        sig = sfx_lib.render(kind, np.random.default_rng(idx), key=key, **params)
        place(effects, sig, at, base * g, 0 if kind in ("thud", "tada", "slam", "impact", "drop", "crash") else pan)

    # Duck the music to a fifth (-14 dB), and the effects to a third, while anyone speaks.
    tt = np.arange(n) / SR
    duck = np.ones(n)
    for s, e, _ in speech:
        duck = np.minimum(duck, 1 - DUCK * np.minimum(np.clip((tt - (s - 0.12)) / 0.12, 0, 1), np.clip(((e + 0.2) - tt) / 0.2, 0, 1)))
    background = bed * m.get("volume", 0.45) * duck[:, None] + effects * (0.35 + 0.65 * duck)[:, None]
    background = clear_room(background, voice, speech, tt)
    mix = background + voice
    write_wav(os.path.join(build_dir, "soundtrack.wav"), finish(mix))
    style = f"file {m['file']}" if m.get("file") else f"style {m.get('style', 'playful')}"
    print(f"› soundtrack.wav  {meta['duration']:.2f}s  {style}  {len(speech)} voice line(s)  {len(cues)} cues")
    report_levels(build_dir, speech, voice, background)


# Every line is brought to the same speech loudness, so no line sits lower than the others.
SPEECH_RMS = 10 ** (-18 / 20)
DUCK = 0.8
MIN_VOICE_OVER_BACKGROUND_DB = 12.0


TARGET_VOICE_OVER_BACKGROUND_DB = 15.0


def clear_room(background, voice, speech, tt):
    """Lowers the music and effects under any line that doesn't stand TARGET dB above them,
    just enough, with short ramps: the voice is always the loudest thing when someone speaks."""
    gain = np.ones(len(tt))
    for s, e, _ in speech:
        a, b = int(max(0, s) * SR), int(max(s + 0.1, e) * SR)
        vr = float(np.sqrt(np.mean(voice[a:b] ** 2)) + 1e-9)
        br = float(np.sqrt(np.mean(background[a:b] ** 2)) + 1e-9)
        ratio = 20 * np.log10(vr / br)
        if ratio >= TARGET_VOICE_OVER_BACKGROUND_DB:
            continue
        g = max(0.1, 10 ** ((ratio - TARGET_VOICE_OVER_BACKGROUND_DB) / 20))
        ramp = np.clip(np.minimum((tt - (s - 0.25)) / 0.2, ((e + 0.35) - tt) / 0.25), 0, 1)
        gain = np.minimum(gain, 1 - (1 - g) * ramp)
    return background * gain[:, None]


def level_voice(v):
    """Scales a voice file so its speech (not its silences) sits at SPEECH_RMS."""
    frame = int(SR * 0.05)
    usable = len(v) // frame * frame
    if usable == 0:
        return v
    rms = np.sqrt(np.mean(v[:usable].reshape(-1, frame) ** 2, axis=1))
    loud = rms[rms > np.max(rms) * 0.1]
    speech_rms = float(np.sqrt(np.mean(loud ** 2))) if len(loud) else float(np.max(rms))
    return v * (SPEECH_RMS / max(speech_rms, 1e-6))


def report_levels(build_dir, speech, voice, background):
    """How far each line stands above the music and effects under it, in dB."""
    rows, low = [], []
    for s, e, key in speech:
        a, b = int(max(0, s) * SR), int(max(s + 0.1, e) * SR)
        vr = float(np.sqrt(np.mean(voice[a:b] ** 2)) + 1e-9)
        br = float(np.sqrt(np.mean(background[a:b] ** 2)) + 1e-9)
        ratio = 20 * np.log10(vr / br)
        rows.append({"key": key, "start": round(s, 2), "voiceOverBackgroundDb": round(ratio, 1)})
        if ratio < MIN_VOICE_OVER_BACKGROUND_DB:
            low.append((key, ratio))
    json.dump(rows, open(os.path.join(build_dir, "voice-levels.json"), "w"), indent=1)
    if rows:
        print("  voice over music+effects, per line: " + ", ".join(f"{r['key']} {r['voiceOverBackgroundDb']:.0f} dB" for r in rows))
    for key, ratio in low:
        print(f"! {key}: the voice is only {ratio:.1f} dB above the music and effects (needs {MIN_VOICE_OVER_BACKGROUND_DB:.0f}): lower music.volume or remove sounds under this line")


def gallery(folder):
    """Every effect and a short demo of every music style, for choosing by ear."""
    os.makedirs(folder, exist_ok=True)
    ff = ffmpeg_path()

    def mp3(name, mix):
        wav = os.path.join(folder, name + ".wav")
        write_wav(wav, mix)
        subprocess.run([ff, "-loglevel", "error", "-y", "-i", wav, "-b:a", "128k", os.path.join(folder, name + ".mp3")], check=True)
        os.remove(wav)

    for name in sfx_lib.SFX:
        extra = {"slide": {"from": 400, "to": 1200, "dur": 0.5}, "marimba": {"semis": 12}, "pluck": {"semis": 12}}.get(name, {})
        sig = sfx_lib.render(name, np.random.default_rng(1), **extra)
        mix = np.zeros((len(sig) + SR // 4, 2))
        place(mix, sig, 0.05, 1.0)
        mp3(f"sfx-{name}", finish(mix, 0.05))
    for style, bpm in music_lib.STYLE_BPM.items():
        beat = 60 / bpm
        moods = [("tension", 4), ("calm", 4), ("groove", 8), ("run", 4), ("outro", 6)]
        scenes, t = [], 0.0
        for mood, beats in moods:
            scenes.append({"mood": mood, "start": t, "len": beats * beat})
            t += beats * beat
        meta = {"duration": t, "beat": beat, "music": {"style": style, "key": "C", "progression": ["C", "Am", "F", "G"]}, "scenes": scenes}
        mp3(f"music-{style}", finish(music_lib.render_music(meta, np.random.default_rng(3)) * 0.8, 1.0))
        print(f"› music-{style}.mp3  {t:.1f}s")
    print(f"› {len(sfx_lib.SFX)} effects and {len(music_lib.STYLE_BPM)} music styles in {folder}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--gallery":
        gallery(os.path.abspath(sys.argv[2]))
    elif len(sys.argv) >= 2:
        build(os.path.abspath(sys.argv[1]))
    else:
        sys.exit(__doc__)
