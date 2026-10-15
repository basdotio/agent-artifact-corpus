#!/usr/bin/env python3
"""
Transcribe a video/audio file with word timestamps (faster-whisper on GPU).

  run.sh transcribe.py MEDIA OUTDIR [--lang id] [--model large-v3-turbo]

Writes:
  OUTDIR/words.json      {"duration", "language", "words": [{i, text, start, end, prob, filler}]}
  OUTDIR/transcript.txt  numbered lines for deciding cuts: "#<first>-<last> [mm:ss] text"
                         pauses >= 1s are shown as "(... 2.3s ...)"
"""

import argparse
import time
from pathlib import Path

from asr_demo import FasterWhisperASR, FillerDetector
from common import fmt_ts, save_json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("media")
    ap.add_argument("outdir")
    ap.add_argument("--lang", default="id", help="language code, or 'auto'")
    ap.add_argument("--model", default="large-v3-turbo")
    a = ap.parse_args()

    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    asr = FasterWhisperASR(model_size=a.model, device="auto")
    words, duration = asr.transcribe(a.media, language=None if a.lang == "auto" else a.lang)
    FillerDetector().detect(words)
    # Whisper splits reduplication ("berjam-jam") into "berjam" + "-jam": glue them back.
    merged = []
    for w in words:
        if merged and w.word.startswith("-"):
            merged[-1].word += w.word
            merged[-1].end = w.end
        else:
            merged.append(w)
    words = merged

    items = [
        {"i": i, "text": w.word, "start": round(w.start, 3), "end": round(w.end, 3),
         "prob": round(w.confidence, 3), "filler": w.type == "filler"}
        for i, w in enumerate(words)
    ]
    save_json({"duration": duration, "language": a.lang, "words": items}, out / "words.json")

    # Human/Claude-readable transcript: one line per sentence-ish chunk, with word indices.
    lines, cur = [], []
    for k, w in enumerate(items):
        cur.append(w)
        nxt = items[k + 1] if k + 1 < len(items) else None
        gap = (nxt["start"] - w["end"]) if nxt else 0
        if w["text"].endswith((".", "?", "!")) or gap >= 1.0 or len(cur) >= 25 or not nxt:
            text = " ".join(("[" + x["text"] + "]") if x["filler"] else x["text"] for x in cur)
            lines.append(f"#{cur[0]['i']}-{cur[-1]['i']} [{fmt_ts(cur[0]['start'])}] {text}")
            if gap >= 1.0:
                lines.append(f"    (... {gap:.1f}s ...)")
            cur = []
    (out / "transcript.txt").write_text("\n".join(lines) + "\n")
    print(f"{len(items)} words, {duration:.1f}s audio, {time.time() - t0:.1f}s elapsed")
    print(f"-> {out / 'words.json'}\n-> {out / 'transcript.txt'}")


if __name__ == "__main__":
    main()
