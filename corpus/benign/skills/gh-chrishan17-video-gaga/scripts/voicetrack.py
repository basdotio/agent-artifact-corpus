#!/usr/bin/env python3
"""One take: the whole narration recorded or synthesized in one pass, then cut
into one slice per scene, so the picture follows the voice instead of each line
being voiced on its own.

Usage (normally through `gaga voicetrack <project> --audio take.wav`):
    python3 scripts/voicetrack.py <project-dir> --audio <take.wav|mp3> [--cut id:0.44-0.83 …] [--clean]

Reads  <project>/narration.json (the same file Edge TTS reads), plus optional fields:
    "track":    { "audio": "voice/take.wav", "lead": 0.45,
                  "pauses": { "。": 1.0, "？": 0.9, "，": 0.35, ".": 1.0, ",": 0.35 } }
    segment:    "spoken"  what was actually said when it differs from the caption text
                          (numbers read out, a name spelled for the voice)
                "pause"   seconds of silence after this line (default: by its last mark)
                "pauses"  { "phrase inside the line": seconds } pauses after phrases

What it does:
  1. normalizes the take (48 kHz mono, -18 LUFS; --clean adds high-pass, de-noise, de-ess),
  2. transcribes it with word timestamps (mlx-whisper on Apple Silicon, else faster-whisper)
     and aligns the transcript to the script character by character (pinyin for Chinese,
     so a homophone in the transcript still lines up),
  3. lengthens the pauses to the targets, adding silence only inside silences it detected,
     never cutting into speech,
  4. cuts the track in the pause before each line (at most `lead` seconds before it starts),
  5. writes build/voice/<id>.mp3 + .json (caption words with times), build/voice-track.wav,
     and build/narration.js with `track.segments[id] = [start, end]`, which the runtime
     uses to place the scenes so that the slices play back to back as one take.

Transcription errors on homophones or digits are not reading errors; the per-line report
shows how much of each line matched and the differing characters, so you can listen to
the ones that look wrong. --cut deletes a stretch of a slice (a stray syllable, a breath)
given in seconds from the start of that slice.
"""

import argparse
import difflib
import json
import os
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

CJK = r"㐀-鿿豈-﫿"
UNIT = re.compile(rf"[{CJK}]|[A-Za-z]|\d")
MARKS = "。！？：；，、…,.!?:;"
DEFAULT_PAUSES = {"。": 1.0, "！": 1.0, "？": 0.9, "：": 0.5, "；": 0.5, "，": 0.35, "、": 0.2, "…": 0.6,
                  ".": 1.0, "!": 1.0, "?": 0.9, ":": 0.5, ";": 0.5, ",": 0.35}
CLEAN = "highpass=f=70,afftdn=nr=8:nf=-42,deesser=i=0.3"
CN = "零一二三四五六七八九"


def num_cn(n):
    """Chinese reading of 0–9999, the way a voice says it (二十六, 一百零五)."""
    if n < 10: return CN[n]
    out, s, zero = "", str(n), False
    for i, d in enumerate(s):
        d, place = int(d), len(s) - 1 - i
        if d == 0: zero = True; continue
        if zero and out: out += "零"
        zero = False
        out += ("" if (d == 1 and place == 1 and not out) else CN[d]) + ["", "十", "百", "千"][place]
    return out


def units(text, zh):
    """Speakable units of a string: CJK characters, letters, digits (as their Chinese reading in zh)."""
    out = []
    for m in re.finditer(rf"\d+|[{CJK}]|[A-Za-z]", text):
        t = m.group()
        if t.isdigit():
            if zh and len(t) <= 4: out += [(c, m.start(), m.end()) for c in num_cn(int(t))]
            else: out += [(c, m.start(), m.end()) for c in t]
        else: out.append((t.lower(), m.start(), m.end()))
    return out


def key_fn(zh):
    if not zh: return lambda c: c
    try:
        from pypinyin import lazy_pinyin
        return lambda c: lazy_pinyin(c)[0] if re.match(rf"[{CJK}]", c) else c
    except ImportError:
        return lambda c: c


def transcribe(wav, lang, prompt, model):
    """[(unit, start, end)] for the whole take, each word's time spread over its units."""
    words = []
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        try:
            import mlx_whisper
            r = mlx_whisper.transcribe(str(wav), path_or_hf_repo=model or "mlx-community/whisper-large-v3-turbo",
                                       language=lang, word_timestamps=True, condition_on_previous_text=False,
                                       initial_prompt=prompt)
            words = [(w["word"], w["start"], w["end"]) for s in r["segments"] for w in s.get("words", [])]
        except ImportError:
            pass
    if not words:
        from faster_whisper import WhisperModel
        m = WhisperModel(model or "large-v3", device="auto", compute_type="auto")
        segs, _ = m.transcribe(str(wav), language=lang, word_timestamps=True, condition_on_previous_text=False,
                               initial_prompt=prompt)
        words = [(w.word, w.start, w.end) for s in segs for w in (s.words or [])]
    out = []
    zh = lang == "zh"
    for w, a, b in words:
        u = [c for c, _, _ in units(w, zh)]
        if not u: continue
        d = (b - a) / len(u)
        out += [(c, a + i * d, a + (i + 1) * d) for i, c in enumerate(u)]
    return out


def silences(wav, db=-40, d=0.08):
    r = subprocess.run(["ffmpeg", "-i", str(wav), "-af", f"silencedetect=n={db}dB:d={d}", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    st = [float(x) for x in re.findall(r"silence_start: ([-0-9.]+)", r)]
    en = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", r)]
    return list(zip(st, en))


def tokens(text, zh):
    """Caption words (no punctuation): jieba words for Chinese when available, else characters; spaces for Latin."""
    if zh:
        try:
            import jieba
            jieba.setLogLevel(60)
            toks, pos = [], 0
            for t in jieba.cut(text, HMM=False):
                i = text.find(t, pos); pos = i + len(t)
                if units(t, True): toks.append((t, i, pos))
            return toks
        except ImportError:
            pass
    return [(m.group(), m.start(), m.end()) for m in re.finditer(rf"\d+%?|[A-Za-z0-9'’\-/]+|[{CJK}]", text)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--audio")
    ap.add_argument("--cut", action="append", default=[])
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--model")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    spec = json.loads((proj / "narration.json").read_text("utf-8"))
    trk = spec.get("track") or {}
    take = Path(a.audio or trk.get("audio") or "")
    if not take.is_absolute(): take = proj / take
    if not take.is_file(): sys.exit(f"no take: pass --audio or set track.audio in narration.json ({take})")
    lang = (spec.get("lang") or "en")[:2]
    zh = lang == "zh"
    pauses = {**DEFAULT_PAUSES, **(trk.get("pauses") or {})}
    lead = float(trk.get("lead", 0.45))
    segs = spec["segments"]
    build = proj / "build"; vdir = build / "voice"; vdir.mkdir(parents=True, exist_ok=True)

    # 1. normalize
    wav = build / "voice-take.wav"
    af = (CLEAN + "," if a.clean else "") + "loudnorm=I=-18:TP=-2:LRA=9"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(take), "-af", af, "-ar", "48000", "-ac", "1", str(wav)], check=True)

    # 2. script units (what was said), the pause after each, and each line's range
    flat, after, rng = [], {}, []
    for sg in segs:
        said = sg.get("spoken", sg["text"])
        u = units(said, zh); i0 = len(flat); flat += [c for c, _, _ in u]
        ends = [e for _, _, e in u]
        for k, e in enumerate(ends):          # punctuation right after unit k (last unit of a number only)
            if k + 1 < len(u) and u[k + 1][1] < e: continue
            m = re.match(rf"\s*([{re.escape(MARKS)}]+)", said[e:])
            if m: after[i0 + k] = max(pauses.get(ch, 0) for ch in m.group(1))
        for ph, sec in (sg.get("pauses") or {}).items():
            j = said.find(ph)
            if j >= 0:
                last = max((k for k, (_, s0, _) in enumerate(u) if s0 < j + len(ph)), default=None)
                if last is not None: after[i0 + last] = float(sec)
        if u: after[len(flat) - 1] = float(sg.get("pause", max(after.get(len(flat) - 1, 0), 0.8)))
        rng.append((i0, len(flat)))

    glossary = "".join(dict.fromkeys(w for sg in segs for w in re.findall(rf"[{CJK}]{{2,6}}|[A-Za-z]{{3,}}", sg.get("spoken", sg["text"]))))[:200]
    heard = transcribe(wav, lang, glossary, a.model)
    key = key_fn(zh)
    sm = difflib.SequenceMatcher(None, [key(c) for c in flat], [key(c) for c, _, _ in heard], autojunk=False)
    o2a = {}
    for b in sm.get_matching_blocks():
        for k in range(b.size): o2a[b.a + k] = b.b + k
    ratio = len(o2a) / max(1, len(flat))
    print(f"  aligned {len(o2a)}/{len(flat)} units of the script to the take ({ratio:.1%})")
    if ratio < 0.9: print("  ⚠ much of the script is not in the take: a skipped or repeated passage? Listen before using it.")

    # unit times on the take; unmatched units are interpolated between their neighbours
    T = [None] * len(flat)
    for i, j in o2a.items(): T[i] = heard[j][1:]
    for i in range(len(T)):
        if T[i] is None:
            l = next((T[k][1] for k in range(i - 1, -1, -1) if T[k]), 0.0)
            r = next((T[k][0] for k in range(i + 1, len(T)) if T[k]), l + 0.3)
            T[i] = (l, max(l + 0.02, r))

    # 3. lengthen pauses inside detected silences only
    audio, sr = sf.read(wav)
    sil = silences(wav)
    ins = []
    for ci, target in sorted(after.items()):
        if ci + 1 >= len(T) or ci not in o2a or ci + 1 not in o2a: continue
        e, s2 = T[ci][1], T[ci + 1][0]
        cand = [x for x in sil if x[1] > e - 0.15 and x[0] < s2 + 0.15]
        if not cand: continue
        g0, g1 = max(cand, key=lambda x: x[1] - x[0])
        if target > (g1 - g0) + 0.05: ins.append(((g0 + g1) / 2, target - (g1 - g0)))
    shift = lambda t: t + sum(add for p, add in ins if p <= t)
    pieces, last = [], 0
    for p, add in ins:
        n = int(p * sr); pieces += [audio[last:n], np.zeros(int(add * sr))]; last = n
    pieces.append(audio[last:])
    master = np.concatenate(pieces)
    tmp = build / "voice-track.wav"; sf.write(tmp, master, sr)

    # 4. cut in the pause before each line
    msil = silences(tmp)
    def span(i0, i1):
        return shift(T[i0][0]), shift(T[i1 - 1][1])
    cuts = [0.0]
    for k in range(1, len(segs)):
        s, _ = span(*rng[k]); _, e = span(*rng[k - 1])
        g = [x for x in msil if x[0] < s + 0.2 and x[1] > e - 0.2 and x[1] - x[0] > 0.12]
        if g: g0, g1 = max(g, key=lambda x: x[1] - x[0]); s, e = g1, g0
        cuts.append(round(max(e + 0.05, s - min(lead, (s - e) * 0.5)), 3))
    total = len(master) / sr; cuts.append(round(total, 3))
    unit_t = [(shift(a0), shift(b0)) for a0, b0 in T]
    for c in a.cut:                           # delete a stray stretch inside one slice
        sid, r = c.split(":"); r0, r1 = map(float, r.split("-"))
        k = [sg["id"] for sg in segs].index(sid); d0, d1 = cuts[k] + r0, cuts[k] + r1
        master = np.concatenate([master[:int(d0 * sr)], master[int(d1 * sr):]])
        mv = lambda t: t if t <= d0 else max(d0, t - (d1 - d0))
        cuts = [round(mv(x), 3) for x in cuts]; unit_t = [(mv(x), mv(y)) for x, y in unit_t]
        print(f"  cut {sid} {r0:.2f}–{r1:.2f}s")
    total = len(master) / sr; cuts[-1] = round(total, 3)
    sf.write(tmp, master, sr)

    # 5. slices, caption words, narration.js
    out_segs, spans = {}, {}
    for k, sg in enumerate(segs):
        sid, text, said = sg["id"], sg["text"], sg.get("spoken", sg["text"])
        c0, c1 = cuts[k], cuts[k + 1]
        clip = master[int(c0 * sr):int(c1 * sr)]
        cw = vdir / f"{sid}.wav"; sf.write(cw, clip, sr)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(cw), "-b:a", "160k", str(vdir / f"{sid}.mp3")], check=True)
        cw.unlink()
        # caption units → spoken units → time on the take
        i0, i1 = rng[k]
        su = units(said, zh); du = units(text, zh)
        m2 = difflib.SequenceMatcher(None, [key(c) for c, _, _ in du], [key(c) for c, _, _ in su], autojunk=False)
        d2s = {}
        for b in m2.get_matching_blocks():
            for j in range(b.size): d2s[b.a + j] = b.b + j
        dt = [None] * len(du)
        for di, si in d2s.items(): dt[di] = (unit_t[i0 + si][0] - c0, unit_t[i0 + si][1] - c0)
        for di in range(len(dt)):
            if dt[di] is None:
                l = next((dt[j][1] for j in range(di - 1, -1, -1) if dt[j]), 0.0)
                r = next((dt[j][0] for j in range(di + 1, len(dt)) if dt[j]), l + 0.3)
                dt[di] = (l, max(l + 0.05, r))
        # snap the first word to the speech onset (Whisper pulls it into the pause before it)
        csil = silences_arr(clip, sr)
        onset = next((b for a0, b in csil if a0 <= 0.02), 0.0)
        words = []
        for t, s0, e0 in tokens(text, zh):
            idx = [di for di, (_, ds, de) in enumerate(du) if ds >= s0 and de <= e0]
            if not idx: continue
            st, en = dt[idx[0]][0], dt[idx[-1]][1]
            if en <= onset + 0.03: st, en = onset, onset + 0.15
            elif st < onset: st = onset
            words.append({"text": t, "start": round(st, 3), "end": round(en, 3)})
        for j in range(1, len(words)):
            if words[j]["start"] < words[j - 1]["end"]: words[j]["start"] = words[j - 1]["end"]
            words[j]["end"] = max(words[j]["end"], round(words[j]["start"] + 0.04, 3))
        dur = round(c1 - c0, 4)
        meta = {"id": sid, "text": text, "voice": spec.get("voice"), "duration": dur, "words": words, "track": [c0, c1]}
        (vdir / f"{sid}.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
        out_segs[sid] = {"text": text, "duration": dur, "words": words, "file": f"build/voice/{sid}.mp3", "voice": spec.get("voice")}
        spans[sid] = [c0, c1]
        got = sum(1 for i in range(i0, i1) if i in o2a) / max(1, i1 - i0)
        miss = "".join(flat[i] for i in range(i0, i1) if i not in o2a)
        print(f"  [{'ok ' if got >= 0.999 else 'chk'}] {sid:<16} {c0:7.2f}–{c1:7.2f}s  {got:5.1%}" + (f"  not heard: {miss}" if miss else ""))
    narr = {"voice": spec.get("voice"), "lang": spec.get("lang"), "segments": out_segs,
            "track": {"file": "build/voice-track.wav", "duration": round(total, 3), "segments": spans}}
    (build / "narration.json").write_text(json.dumps(narr, ensure_ascii=False, indent=1), "utf-8")
    (build / "narration.js").write_text("// generated by scripts/voicetrack.py — do not edit\nwindow.CV_NARRATION = "
                                        + json.dumps(narr, ensure_ascii=False) + ";\n", "utf-8")
    print(f"  track: {total:.1f}s, {len(ins)} pauses lengthened, {len(segs)} slices → {build / 'narration.js'}")


def silences_arr(clip, sr, db=-40, d=0.08):
    """silencedetect on an in-memory slice."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav") as f:
        sf.write(f.name, clip, sr)
        return silences(f.name, db, d)


if __name__ == "__main__":
    main()
