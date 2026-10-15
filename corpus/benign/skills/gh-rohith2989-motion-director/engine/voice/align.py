"""
Word timestamps for narration (faster-whisper, local), matched back to the SCRIPT's own words, so the picture
can be keyed to "the moment she says 'Allow'".

python voice/align.py take.wav [out.json]    whole take vs voice/script.txt: per-line spans, WER, misreads

Hard-won rules: never pass the script as Whisper's initial_prompt (it skips stretches it "already knows" and
hallucinates "thanks for watching" at the end) — pass only proper nouns (voice/hints.txt, one line). Whisper
puts a clip's first word at 0.0 and is often 20–80 ms late; word onsets are snapped to the waveform here.
"""
import json
import os
import re
import sys

import numpy as np
import soundfile as sf

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from tts import script_lines  # noqa: E402


def hints():
    p = os.path.join(HERE, "hints.txt")
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None


def norm_tokens(s):
    s = s.lower().replace("—", " ").replace("–", " ").replace("-", " ").replace("@", " at ")
    s = re.sub(r"[^a-z0-9' ]", " ", s)
    return [w for w in s.split() if w]


def words_of(text, line=0):
    out = []
    for raw in text.replace("—", " — ").split():
        if raw == "—":
            continue
        for k, tk in enumerate(norm_tokens(raw)):
            out.append({"line": line, "w": raw if k == 0 else "", "n": tk})
    return out


def align_seq(ref, hyp):
    """Levenshtein alignment → [(i_ref | None, j_hyp | None)], distance."""
    n, m = len(ref), len(hyp)
    d = np.zeros((n + 1, m + 1), dtype=int)
    d[:, 0] = np.arange(n + 1)
    d[0, :] = np.arange(m + 1)
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i, j] = min(d[i - 1, j] + 1, d[i, j - 1] + 1, d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]))
    i, j, path = n, m, []
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i, j] == d[i - 1, j - 1] + (ref[i - 1] != hyp[j - 1]):
            path.append((i - 1, j - 1))
            i, j = i - 1, j - 1
        elif i > 0 and d[i, j] == d[i - 1, j] + 1:
            path.append((i - 1, None))
            i -= 1
        else:
            path.append((None, j - 1))
            j -= 1
    return path[::-1], d[n, m]


_ASR = None


def asr(model="medium.en"):
    global _ASR
    if _ASR is None:
        from faster_whisper import WhisperModel
        _ASR = WhisperModel(model, device="cpu", compute_type="int8")
    return _ASR


def transcribe_words(path):
    segs, _ = asr().transcribe(path, language="en", beam_size=5, word_timestamps=True, condition_on_previous_text=False, initial_prompt=hints())
    hyp = []
    for s in segs:
        for w in s.words:
            for tk in norm_tokens(w.word):
                hyp.append({"n": tk, "t0": w.start, "t1": w.end, "p": w.probability})
    return hyp


def match(ref, hyp):
    """Give each script word whisper's times; report misreads; interpolate the unmatched."""
    path_, dist = align_seq([r["n"] for r in ref], [h["n"] for h in hyp])
    mis = []
    for i, j in path_:
        if i is not None and j is not None:
            ref[i].update(t0=hyp[j]["t0"], t1=hyp[j]["t1"], p=hyp[j]["p"], heard=hyp[j]["n"])
            if ref[i]["n"] != hyp[j]["n"]:
                mis.append(f'{ref[i]["n"]} -> {hyp[j]["n"]} @ {hyp[j]["t0"]:.2f}')
        elif i is not None:
            mis.append(f'{ref[i]["n"]} -> (missing)')
        else:
            mis.append(f'(extra) {hyp[j]["n"]} @ {hyp[j]["t0"]:.2f}')
    for k, r in enumerate(ref):
        if "t0" not in r:
            prev = next((ref[q] for q in range(k - 1, -1, -1) if "t0" in ref[q]), None)
            nxt = next((ref[q] for q in range(k + 1, len(ref)) if "t0" in ref[q]), None)
            r["t0"] = prev["t1"] if prev else (nxt["t0"] if nxt else 0.0)
            r["t1"] = nxt["t0"] if nxt else r["t0"] + 0.25
            r["p"] = 0.0
    return ref, dist / max(1, len(ref)), mis


def snap_onsets(ref, x, sr):
    """First word → first sustained rise; others → nearest rising crossing within 120 ms; then monotonic."""
    hop = int(sr * 0.005)
    n = len(x) // hop
    env = 20 * np.log10(np.sqrt(np.mean(x[: n * hop].reshape(n, hop) ** 2, axis=1) + 1e-12) + 1e-9)
    env = np.convolve(env, np.ones(3) / 3, mode="same")
    floor = np.percentile(env, 8)
    above = env > floor + 0.3 * (env.max() - floor)
    k = 0
    while k < n - 3 and not (above[k] and above[k + 1] and above[k + 2]):
        k += 1
    ref[0]["t0"] = round(max(0.0, k * 0.005 - 0.015), 3)
    for r in ref[1:]:
        i = int(r["t0"] * sr / hop)
        cands = [j for j in range(max(1, i - 24), min(n - 1, i + 24)) if above[j] and not above[j - 1]]
        if cands:
            r["t0"] = round(min(cands, key=lambda j: abs(j - i) + (0 if j <= i else 6)) * 0.005, 3)
    i = 1
    while i < len(ref):  # whisper sometimes stamps two words with one time: spread such runs by length
        if ref[i]["t0"] <= ref[i - 1]["t0"] + 0.04:
            j = i
            while j < len(ref) and ref[j]["t0"] <= ref[i - 1]["t0"] + 0.04:
                j += 1
            a_t = ref[i - 1]["t0"]
            b_t = ref[j]["t0"] if j < len(ref) else max(ref[i - 1]["t1"], a_t + 0.2 * (j - i + 1))
            lens = [len(r["n"]) + 1 for r in ref[i - 1:j]]
            acc = 0
            for q in range(i - 1, j):
                if q >= i:
                    ref[q]["t0"] = round(a_t + (b_t - a_t) * acc / sum(lens), 3)
                acc += lens[q - (i - 1)]
            i = j
        else:
            i += 1
    for a, b in zip(ref, ref[1:]):
        if a["t1"] > b["t0"]:
            a["t1"] = b["t0"]
    return ref


def align_take(path):
    lines = script_lines()
    ref = [w for li, l in enumerate(lines) for w in words_of(l, li)]
    ref, wer, mis = match(ref, transcribe_words(path))
    spans = []
    for li in range(len(lines)):
        ws = [r for r in ref if r["line"] == li]
        spans.append({"line": li, "text": lines[li], "t0": ws[0]["t0"], "t1": ws[-1]["t1"]})
    return {"file": os.path.basename(path), "wer": wer, "misreads": mis, "lines": spans, "words": ref}


if __name__ == "__main__":
    r = align_take(sys.argv[1])
    if len(sys.argv) > 2:
        json.dump(r, open(sys.argv[2], "w"), indent=1)
    print(f'{r["file"]}  WER {r["wer"]:.3f}')
    for m in r["misreads"]:
        print("   misread:", m)
    for L in r["lines"]:
        print(f'   L{L["line"]} {L["t0"]:6.2f} -> {L["t1"]:6.2f}  {L["text"][:70]}')
