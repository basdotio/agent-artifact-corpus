"""
The voice timeline — the narrated film's master clock.

voice/vo_plan.json picks the reading of each line (voice/lines/*.wav, from cast.py lines) and where it starts:
  {"duration": 58.0, "lufs": -18.0, "lines": [{"line": 0, "take": "L0_t2.wav", "start": 0.7, "trim": 0.0}, ...]}
This measures each chosen line's words (on the isolated line), snaps onsets to the waveform, levels the lines to
one loudness, upsamples to 48 kHz, places them, and writes
  comp/data/vo.json         every word's absolute time (scenes key events to words: w(line, "allow"))
  audio/out/vo.wav          the placed dry voice (the mix processes it)
  audio/out/captions.srt    phrase captions for platforms that take sidecar files
Plan the gaps: after a line, leave time for what the picture must still do (a click, a page loading).
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from tts import script_lines  # noqa: E402
from align import words_of, transcribe_words, match, snap_onsets  # noqa: E402

SR = 48000


def lufs(x):
    import pyloudnorm as pyln
    return pyln.Meter(SR).integrated_loudness(x)


def phrases(text, maxlen=42):
    parts = re.split(r"(?<=[,.;:?!—])\s+", text)
    out, cur = [], ""
    for p in parts:
        if cur and len(cur) + 1 + len(p) > maxlen:
            out.append(cur)
            cur = p
        else:
            cur = f"{cur} {p}".strip()
    if cur:
        out.append(cur)
    return out


def srt_time(t):
    h, m, s = int(t // 3600), int(t % 3600 // 60), t % 60
    return f"{h:02d}:{m:02d}:{int(s):02d},{int(round((s - int(s)) * 1000)):03d}"


def main():
    plan = json.load(open(os.path.join(HERE, "vo_plan.json")))
    lines_txt = script_lines()
    total = plan["duration"]
    bus = np.zeros(int(total * SR) + SR)
    out_lines = []
    for L in plan["lines"]:
        li = L["line"]
        src = os.path.join(HERE, "lines", L["take"])
        x, sr = sf.read(src)
        x = x if x.ndim == 1 else x.mean(1)
        ref, wer, mis = match(words_of(lines_txt[li], li), transcribe_words(src))
        ref = snap_onsets(ref, x, sr)
        y = resample_poly(x, SR, sr) if sr != SR else x
        g = plan.get("lufs", -18.0) - lufs(y)
        y = y * 10 ** (g / 20)
        trim = L.get("trim", 0.0)
        y = y[int(trim * SR):]
        start = L["start"]
        i0 = int(round(start * SR))
        bus[i0:i0 + len(y)] += y
        words = [{"w": r["w"], "n": r["n"], "t0": round(start + r["t0"] - trim, 3), "t1": round(start + r["t1"] - trim, 3), "p": round(r.get("p", 0), 2)} for r in ref]
        out_lines.append({"line": li, "text": lines_txt[li], "take": L["take"], "start": start, "end": round(start + len(y) / SR, 3),
                          "speech0": words[0]["t0"], "speech1": words[-1]["t1"], "gain_db": round(g, 2), "wer": round(wer, 3), "words": words})
        print(f"L{li} {L['take']:14s} {start:6.2f} -> {start + len(y) / SR:6.2f}  speech {words[0]['t0']:6.2f}-{words[-1]['t1']:6.2f}  {'' if wer == 0 else f'WER {wer:.2f} {mis}'}")
    for a, b in zip(out_lines, out_lines[1:]):
        if b["speech0"] < a["speech1"] + 0.25:
            print(f"WARNING: L{a['line']} and L{b['line']} nearly overlap")
    os.makedirs(os.path.join(ROOT, "audio", "out"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "comp", "data"), exist_ok=True)
    sf.write(os.path.join(ROOT, "audio", "out", "vo.wav"), bus[: int(total * SR)].astype(np.float32), SR)
    json.dump({"duration": total, "lines": out_lines}, open(os.path.join(ROOT, "comp", "data", "vo.json"), "w"), indent=1)
    # sidecar captions: phrases per line, timed by their words
    from align import norm_tokens
    caps = []
    for L in out_lines:
        k = 0
        for ph in phrases(L["text"]):
            n = len(norm_tokens(ph))
            ws = L["words"][k:k + n]
            if ws:
                caps.append([ws[0]["t0"], ws[-1]["t1"], ph])
            k += n
    for i, c in enumerate(caps):
        nxt = caps[i + 1][0] if i + 1 < len(caps) else c[1] + 0.6
        c[1] = max(c[0] + 0.8, min(c[1] + 0.45, nxt - 0.05))
    with open(os.path.join(ROOT, "audio", "out", "captions.srt"), "w", encoding="utf-8") as f:
        for i, (a, b, ph) in enumerate(caps, 1):
            f.write(f"{i}\n{srt_time(a)} --> {srt_time(b)}\n{ph}\n\n")
    print("ok comp/data/vo.json, audio/out/vo.wav, audio/out/captions.srt")


if __name__ == "__main__":
    main()
