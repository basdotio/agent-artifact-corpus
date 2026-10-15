"""Voice lines for a motion-video project: timing and checking.

    python engine/voices.py <project>                  time new or changed voice files
    python engine/voices.py <project> --import         re-time every voice file
    python engine/voices.py <project> --check-lines    transcribe each file, compare with its text
    python engine/voices.py <project> --check <audio>  transcribe a mix (e.g. build/soundtrack.wav)

The engine does not generate speech. Make each scene's line with the
text-to-speech tool you have (an ElevenLabs account connected through
Composio, another TTS, a recording) and save it as voices/<scene id>.mp3
(.wav, .m4a and .ogg work too). This script then finds when each word of the
scene's voice.text is said:

  1. from voices/<scene id>.alignment.json when present (ElevenLabs'
     "with-timestamps" response: {"alignment": {"characters", ...}}),
  2. else with faster-whisper (pip install faster-whisper; the model is
     WHISPER_MODEL: a name like "small" or a local model folder),
  3. else by spreading the words over the speech found in the file.

A scene with a voice but no file gets estimated timings and stays silent, so
the video can be built and checked before any voice exists. Results go to
voices/voices.json, which the renderer and the mixer read.
"""
import difflib
import json
import os
import re
import subprocess
import sys

AUDIO_EXTS = (".mp3", ".wav", ".m4a", ".ogg")
WORD = re.compile(r"\[[^\]]*\]|[\w'’-]+", re.UNICODE)


def spoken_words(text):
    """The words of a line, without audio tags like [excited]."""
    return [m.group() for m in WORD.finditer(text) if not m.group().startswith("[")]


def words_from_alignment(alignment):
    chars = alignment["characters"]
    starts = alignment["character_start_times_seconds"]
    ends = alignment["character_end_times_seconds"]
    text = "".join(chars)
    return [
        {"w": m.group(), "start": round(starts[m.start()], 3), "end": round(ends[m.end() - 1], 3)}
        for m in WORD.finditer(text)
        if not m.group().startswith("[")
    ]


def estimated_words(text):
    """Timings for a line nobody has recorded: about 2.7 words per second."""
    t, out = 0.0, []
    for m in WORD.finditer(text):
        w = m.group()
        if w.startswith("["):
            continue
        d = max(0.18, 0.06 * len(w) + 0.12)
        out.append({"w": w, "start": round(t, 3), "end": round(t + d, 3)})
        t += d + 0.06
        after = text[m.end() : m.end() + 1]
        t += 0.3 if after and after in ".!?…" else 0.15 if after and after in ",;:" else 0
    return out


def ffmpeg_path():
    if os.environ.get("FFMPEG"):
        return os.environ["FFMPEG"]
    from shutil import which
    if which("ffmpeg"):
        return "ffmpeg"
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def speech_span(path):
    """Where speech starts and ends in a file, from ffmpeg's silence detection."""
    err = subprocess.run([ffmpeg_path(), "-hide_banner", "-i", path, "-af", "silencedetect=noise=-38dB:d=0.12", "-f", "null", "-"], capture_output=True, text=True).stderr
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    total = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0.0
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    begin = ends[0] if starts and starts[0] <= 0.02 and ends else 0.0
    finish = starts[-1] if starts and starts[-1] > begin and (not ends or starts[-1] > ends[-1]) else total
    return begin, finish


_model = None


def whisper_words(path, language):
    """Word timings from faster-whisper, or None when it is not installed."""
    global _model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return None
    if _model is None:
        _model = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8")
    segments, _ = _model.transcribe(path, language=language, word_timestamps=True)
    return [{"w": w.word.strip(), "start": w.start, "end": w.end} for seg in segments for w in (seg.words or [])]


def map_words(script, heard):
    """The script's exact words, with the times of the words that were heard."""
    a = [w.lower().strip("'’-.,!?") for w in script]
    b = [h["w"].lower().strip("'’-.,!?") for h in heard]
    times = [None] * len(a)
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == "equal":
            for k in range(i2 - i1):
                times[i1 + k] = (heard[j1 + k]["start"], heard[j1 + k]["end"])
        elif tag == "replace":
            t0, t1 = heard[j1]["start"], heard[j2 - 1]["end"]
            step = (t1 - t0) / (i2 - i1)
            for k in range(i2 - i1):
                times[i1 + k] = (t0 + k * step, t0 + (k + 1) * step)
    # Words nobody heard: spread them between their neighbours.
    for i in range(len(times)):
        if times[i] is None:
            prev = next((times[k][1] for k in range(i - 1, -1, -1) if times[k]), 0.0)
            nxt = next((times[k][0] for k in range(i + 1, len(times)) if times[k]), prev + 0.3)
            times[i] = (prev, max(prev + 0.05, (prev + nxt) / 2))
    return [{"w": w, "start": round(t[0], 3), "end": round(t[1], 3)} for w, t in zip(script, times)]


def time_file(audio, align_path, text, language):
    """Word timings for one voice file; returns (words, method)."""
    if os.path.exists(align_path):
        data = json.load(open(align_path, encoding="utf8"))
        return words_from_alignment(data.get("alignment") or data), "alignment"
    heard = whisper_words(audio, language)
    if heard:
        return map_words(spoken_words(text), heard), "faster-whisper"
    begin, finish = speech_span(audio)
    est = estimated_words(text)
    scale = (finish - begin) / max(0.1, est[-1]["end"]) if est else 1
    return [{"w": w["w"], "start": round(begin + w["start"] * scale, 3), "end": round(begin + w["end"] * scale, 3)} for w in est], "estimate"


def scene_lines(story):
    for i, sc in enumerate(story["scenes"]):
        if sc.get("voice"):
            yield sc.get("id") or f"s{i + 1}", sc["voice"]


def find_audio(folder, scene_key):
    return next((os.path.join(folder, scene_key + e) for e in AUDIO_EXTS if os.path.exists(os.path.join(folder, scene_key + e))), None)


def update(project, story, reimport=False):
    lines = list(scene_lines(story))
    if not lines:
        print("no scene has a voice: nothing to time")
        return
    folder = os.path.join(project, "voices")
    os.makedirs(folder, exist_ok=True)
    index_path = os.path.join(folder, "voices.json")
    index = json.load(open(index_path, encoding="utf8")) if os.path.exists(index_path) else {}
    fresh, missing = {}, []
    for scene_key, voice in lines:
        text, who = voice["text"], voice.get("who", "narrator")
        audio = find_audio(folder, scene_key)
        old = index.get(scene_key)
        if audio:
            align_path = os.path.join(folder, f"{scene_key}.alignment.json")
            stamp = [os.path.getmtime(audio), os.path.getmtime(align_path) if os.path.exists(align_path) else 0]
            if old and not reimport and old.get("text") == text and old.get("stamp") == stamp and not old.get("synthetic"):
                fresh[scene_key] = old
                continue
            words, method = time_file(audio, align_path, text, story.get("language"))
            fresh[scene_key] = {"text": text, "who": who, "method": method, "stamp": stamp, "file": f"voices/{os.path.basename(audio)}",
                                "speechStart": words[0]["start"], "speechEnd": words[-1]["end"], "words": words}
            print(f"  {scene_key}: {os.path.basename(audio)} timed by {method}, {words[-1]['end'] - words[0]['start']:.2f}s of speech")
        else:
            words = estimated_words(text)
            fresh[scene_key] = {"text": text, "who": who, "synthetic": True, "speechStart": 0.0, "speechEnd": words[-1]["end"] if words else 0.5, "words": words}
            missing.append(scene_key)
    json.dump(fresh, open(index_path, "w", encoding="utf8"), ensure_ascii=False, indent=1)
    if missing:
        print(f"  no file yet for: {', '.join(missing)} (estimated timings, silent). Save them as voices/<scene id>.mp3")
    print(f"voices.json: {len(fresh)} line(s)")


NUMBERS = {
    "0": ("zéro", "zero"), "1": ("un", "one"), "2": ("deux", "two"), "3": ("trois", "three"), "4": ("quatre", "four"),
    "5": ("cinq", "five"), "6": ("six", "six"), "7": ("sept", "seven"), "8": ("huit", "eight"), "9": ("neuf", "nine"),
    "10": ("dix", "ten"), "12": ("douze", "twelve"), "20": ("vingt", "twenty"), "30": ("trente", "thirty"), "100": ("cent", "hundred"),
}
WORD_FOR = {digit: words for digit, words in NUMBERS.items()}


def norm_words(s):
    out = []
    for w in spoken_words(s.replace("'", "' ").replace("’", "’ ")):
        w = w.lower().strip("'’-")
        if w in WORD_FOR:
            w = WORD_FOR[w][0]
        for fr, en in NUMBERS.values():
            if w == en:
                w = fr
        if w:
            out.append(w)
    return out


def similarity(a, b):
    """Letter-level likeness of what was written and what was heard, ignoring spaces,
    hyphens and punctuation, so "demande-lui" and "demande lui" match."""
    la = "".join(norm_words(a)).replace("-", "").replace("'", "").replace("’", "")
    lb = "".join(norm_words(b)).replace("-", "").replace("'", "").replace("’", "")
    return difflib.SequenceMatcher(None, la, lb, autojunk=False).ratio()


def need_whisper():
    sys.exit("Checking needs faster-whisper: pip install faster-whisper")


def check_lines(project, story):
    index = json.load(open(os.path.join(project, "voices", "voices.json"), encoding="utf8"))
    bad = 0
    for scene_key, line in index.items():
        if line.get("synthetic"):
            print(f"  NONE  {scene_key}: no voice file yet")
            continue
        words = whisper_words(os.path.join(project, line["file"]), story.get("language"))
        if words is None:
            need_whisper()
        heard = " ".join(w["w"] for w in words)
        score = similarity(line["text"], heard)
        bad += score < 0.85
        print(f"  {'OK   ' if score >= 0.85 else 'CHECK'} {scene_key}  {score:.2f}\n        wrote: {line['text']}\n        heard: {heard}")
    print(f"{bad} line(s) to check" if bad else "all lines match")


def check_mix(project, story, audio):
    """Transcribes each voice line where it sits in the final mix, one window at a time:
    a whole-mix transcription silently drops segments, a window per line does not."""
    build = os.path.join(project, "build")
    cues = json.load(open(os.path.join(build, "cues.json")))
    index_path = os.path.join(project, "voices", "voices.json")
    if not any(c["kind"] == "voice" for c in cues) or not os.path.exists(index_path):
        print("no voice lines in this video: nothing to check")
        return
    index = json.load(open(index_path, encoding="utf8"))
    levels_path = os.path.join(build, "voice-levels.json")
    levels = {r["key"]: r["voiceOverBackgroundDb"] for r in json.load(open(levels_path))} if os.path.exists(levels_path) else {}
    bad = 0
    for c in (c for c in cues if c["kind"] == "voice"):
        line = index.get(c["key"], {})
        start = c["t"] + line.get("speechStart", 0) - 0.5
        clip = os.path.join(build, f"check-{c['key']}.wav")
        subprocess.run([ffmpeg_path(), "-loglevel", "error", "-y", "-ss", f"{max(0, start):.2f}", "-to", f"{c['end'] + 0.35:.2f}", "-i", audio, "-ac", "1", "-ar", "16000", clip], check=True)
        words = whisper_words(clip, story.get("language"))
        if words is None:
            need_whisper()
        heard = " ".join(w["w"] for w in words)
        score = similarity(line.get("text", ""), heard)
        level = levels.get(c["key"])
        ok = score >= 0.85 and (level is None or level >= 12)
        bad += not ok
        lv = f"{level:4.0f} dB" if level is not None else "   ? dB"
        print(f"  {'OK   ' if ok else 'CHECK'} {c['key']:12} words {score:.2f}  voice over music {lv}  {c['t'] + line.get('speechStart', 0):6.2f}s")
        if not ok:
            print(f"        wrote: {line.get('text')}\n        heard: {heard}")
        os.remove(clip)
    print(f"{bad} line(s) to check" if bad else "every line is heard, and stands above the music")


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    project = os.path.abspath(sys.argv[1])
    story = json.load(open(os.path.join(project, "story.json"), encoding="utf8"))
    opts = sys.argv[2:]
    if "--check-lines" in opts:
        check_lines(project, story)
    elif "--check" in opts:
        check_mix(project, story, opts[opts.index("--check") + 1])
    else:
        update(project, story, "--import" in opts)


if __name__ == "__main__":
    main()
