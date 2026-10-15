"""
Casting the voice like a director — because an LLM's 1–10 ratings of audio are noise (the same take scored
3 and 9 in two runs), but forced A/B choices heard in BOTH orders and tallied are stable.

python voice/cast.py score voice/audition           Whisper exactness (WER), pace (words/s), pitch range
python voice/cast.py duel voice/audition/*.wav       round-robin, both orders, Bradley-Terry ranking
python voice/cast.py screen champ1.wav,champ2.wav challenger*.wav   challengers vs the current leaders
python voice/cast.py lines voice/takes/*.wav          cut every line from every take, duel the readings of each
                                                      line, write voice/vo_plan.json with the winners
Needs GEMINI_API_KEY (the listener: gemini-3.1-pro-preview by default, LISTEN_MODEL to change).
Workflow: audition 20–50 voices → score → duel the clean top ~12 → screen newcomers → 4–6 full takes of the
winner → lines → vo_build. Prefer the clearer reading when a duel is close ("Need it" must not sound "Needed").
"""
import glob
import itertools
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tts import script_lines  # noqa: E402
from align import norm_tokens, align_seq, transcribe_words, align_take  # noqa: E402

PROMPT_VOICE = (
    "You are a voice director casting the narrator of a short video for a product; many viewers are not technical. "
    "Below are two takes of the same lines by different narrators. Which take sounds more like a real, warm human "
    "narrator — natural rhythm and intonation, no synthetic or robotic moments, relaxed but not slow, friendly "
    "without sounding like an advert? Reply as JSON: {\"winner\": \"A\" or \"B\", \"margin\": 1 | 2 | 3, \"reason\": short}")
PROMPT_LINE = (
    "You are directing a voiceover. Below are two readings, by the same narrator, of this line:\n\n\"{line}\"\n\n"
    "Which reading is better? Judge natural rhythm and intonation, emphasis on the right words, warmth, clarity "
    "(every word unmistakable), not rushed and not dragging, no glitches or mispronunciations. Reply as JSON: "
    "{{\"winner\": \"A\" or \"B\", \"margin\": 1 | 2 | 3, \"reason\": short}}")


def client():
    from google import genai
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def duel(c, prompt, a, b):
    from google.genai import types
    parts = [types.Part.from_text(text=prompt),
             types.Part.from_text(text="A:"), types.Part.from_bytes(data=open(a, "rb").read(), mime_type="audio/wav"),
             types.Part.from_text(text="B:"), types.Part.from_bytes(data=open(b, "rb").read(), mime_type="audio/wav")]
    for _ in range(4):
        try:
            r = c.models.generate_content(model=os.environ.get("LISTEN_MODEL", "gemini-3.1-pro-preview"),
                                          contents=[types.Content(role="user", parts=parts)],
                                          config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2))
            j = json.loads(r.text)
            w = str(j.get("winner", "")).strip().upper()[-1:]
            if w in ("A", "B"):
                return (a if w == "A" else b), int(j.get("margin", 1)), j.get("reason", "")
        except Exception as e:  # noqa: BLE001
            print("retry:", str(e)[:120], file=sys.stderr)
    return None, 0, ""


def bradley_terry(names, wins, iters=200):
    p = {n: 1.0 for n in names}
    for _ in range(iters):
        q = {}
        for i in names:
            w = sum(wins[(i, j)] for j in names if j != i)
            d = sum((wins[(i, j)] + wins[(j, i)]) / (p[i] + p[j]) for j in names if j != i)
            q[i] = w / d if d else p[i]
        s = sum(q.values()) or 1
        p = {n: q[n] * len(names) / s for n in names}
    return p


def round_robin(files, prompt, reps=1):
    c = client()
    jobs = list(itertools.permutations(files, 2)) * reps
    wins = defaultdict(float)
    why = defaultdict(list)
    with ThreadPoolExecutor(8) as ex:
        for (a, b), (w, m, r) in zip(jobs, ex.map(lambda ab: duel(c, prompt, *ab), jobs)):
            if w:
                l = b if w == a else a
                wins[(w, l)] += 0.5 + 0.25 * (m - 1)
                why[w].append(r)
    bt = bradley_terry(files, wins)
    return sorted(files, key=lambda f: -bt[f]), bt, why


def cmd_score(d):
    files = sorted(glob.glob(os.path.join(d, "*.wav")))
    ref = " ".join(script_lines()[:2])
    rows = []
    for f in files:
        x, sr = sf.read(f)
        x = x if x.ndim == 1 else x.mean(1)
        hyp = transcribe_words(f)
        _, dist = align_seq(norm_tokens(ref), [h["n"] for h in hyp])
        idx = np.nonzero(np.abs(x) > 0.02)[0]
        span = (idx[-1] - idx[0]) / sr if len(idx) else len(x) / sr
        rng = 0.0
        try:
            import librosa
            f0, _, _ = librosa.pyin(x.astype(np.float32), fmin=65, fmax=400, sr=sr, frame_length=1024)
            f0 = f0[~np.isnan(f0)]
            rng = float(np.std(12 * np.log2(f0 / np.median(f0)))) if len(f0) > 10 else 0.0
        except Exception:  # noqa: BLE001 — pitch range is optional
            pass
        rows.append((os.path.basename(f), dist / max(1, len(norm_tokens(ref))), len(norm_tokens(ref)) / span, rng))
    for n, wer, wps, rng in sorted(rows, key=lambda r: r[1]):
        flag = "  MISREAD — exclude" if wer > 0.05 else ""
        print(f"{n:48s} WER {wer:.2f}  pace {wps:.2f} w/s  range {rng:.2f} st{flag}")


def cmd_duel(files):
    rank, bt, why = round_robin(files, PROMPT_VOICE)
    for f in rank:
        print(f"{os.path.basename(f):48s} {bt[f]:6.2f}   {(why[f][0] if why[f] else '')[:100]}")


def cmd_screen(champs, files):
    c = client()
    jobs = [(f, ch) for f in files for ch in champs] + [(ch, f) for f in files for ch in champs]
    res = defaultdict(list)
    with ThreadPoolExecutor(8) as ex:
        for (a, b), (w, m, r) in zip(jobs, ex.map(lambda ab: duel(c, PROMPT_VOICE, *ab), jobs)):
            f = a if a in files else b
            if w:
                res[f].append(1 if w == f else 0)
    for f in sorted(files, key=lambda f: -np.mean(res[f] or [0])):
        print(f"{os.path.basename(f):48s} won {sum(res[f])}/{len(res[f])}")


def cmd_lines(takes):
    lines = script_lines()
    out_dir = os.path.join(HERE, "lines")
    os.makedirs(out_dir, exist_ok=True)
    cands = defaultdict(list)
    for ti, tk in enumerate(takes):
        a = align_take(tk)
        x, sr = sf.read(tk)
        x = x if x.ndim == 1 else x.mean(1)
        spans = a["lines"]
        for k, L in enumerate(spans):
            ws = [w for w in a["words"] if w["line"] == L["line"]]
            clean = all(w.get("heard", w["n"]) == w["n"] and w.get("p", 1) > 0 for w in ws)
            # cut in the middle of the silences around the line (a fixed pre-roll catches the previous line's tail)
            prev_end = spans[k - 1]["t1"] if k else 0.0
            next_start = spans[k + 1]["t0"] if k + 1 < len(spans) else len(x) / sr
            t0 = max(0.0, max(L["t0"] - 0.25, (prev_end + L["t0"]) / 2))
            t1 = min(len(x) / sr, min(L["t1"] + 0.35, (L["t1"] + next_start) / 2))
            seg = x[int(t0 * sr): int(t1 * sr)].copy()
            k = int(0.01 * sr)
            seg[:k] *= np.linspace(0, 1, k)
            seg[-k:] *= np.linspace(1, 0, k)
            p = os.path.join(out_dir, f"L{L['line']}_t{ti}{'' if clean else '_x'}.wav")
            sf.write(p, seg, sr)
            if clean:
                cands[L["line"]].append(p)
    plan = {"duration": None, "lufs": -18.0, "lines": []}
    for li, line in enumerate(lines):
        files = cands.get(li, [])
        if not files:
            print(f"L{li}: no clean reading — re-take this line")
            continue
        best = files[0]
        if len(files) > 1:
            rank, bt, why = round_robin(files, PROMPT_LINE.format(line=line))
            best = rank[0]
            print(f"L{li}: {', '.join(f'{os.path.basename(f)} {bt[f]:.2f}' for f in rank)}")
        plan["lines"].append({"line": li, "take": os.path.basename(best), "start": None})
    json.dump(plan, open(os.path.join(HERE, "vo_plan.json"), "w"), indent=1)
    print("wrote voice/vo_plan.json — now set each line's start (and the duration) from docs/PLAN.md, then vo_build.py")


if __name__ == "__main__":
    c = sys.argv[1]
    if c == "score":
        cmd_score(sys.argv[2])
    elif c == "duel":
        cmd_duel(sys.argv[2:])
    elif c == "screen":
        cmd_screen(sys.argv[2].split(","), sys.argv[3:])
    elif c == "lines":
        cmd_lines(sys.argv[2:])
