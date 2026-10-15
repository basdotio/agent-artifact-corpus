#!/usr/bin/env python3
"""
Cut a recording from its transcript: drop deleted words, fillers and long pauses,
optionally burn pop captions, and scale to 720p (the short side, so portrait stays portrait).
One frame-accurate NVENC pass.

  run.sh cut.py VIDEO WORDS_JSON OUT.mp4 [--cuts cuts.json] [--max-gap 0.6] [--pad 0.12]
                [--keep-fillers] [--captions] [--height 720] [--quality high]

cuts.json: {"delete": [[first_i, last_i], ...]}  (inclusive word-index ranges, from transcript.txt)

Also writes OUT.words.json (kept words re-timed to the output) and OUT.segments.json.
"""

import argparse
import time
from pathlib import Path

from app.services.ffmpeg_service import FFmpegService
from captions import ass_filter, write_ass
from common import FONTS_DIR, TARGET_H, load_json, probe, save_json


def build_segments(words, deleted, duration, max_gap, pad, keep_fillers):
    kept = [w for w in words if w["i"] not in deleted and (keep_fillers or not w["filler"])]
    segs = []
    for w in kept:
        s, e = max(0.0, w["start"] - pad), min(duration, w["end"] + pad)
        if segs and s - segs[-1][1] <= max_gap:
            segs[-1][1] = max(segs[-1][1], e)
        else:
            if segs and s < segs[-1][1]:
                s = segs[-1][1]
            segs.append([s, e])
    return [(round(a, 3), round(b, 3)) for a, b in segs if b - a > 0.04], kept


def retime(kept, segs):
    """Map kept words onto the output timeline."""
    out, k, offset = [], 0, 0.0
    for a, b in segs:
        while k < len(kept) and kept[k]["start"] < b:
            w = kept[k]
            if w["end"] > a:
                out.append({**w, "start": round(max(w["start"], a) - a + offset, 3),
                            "end": round(min(w["end"], b) - a + offset, 3)})
            k += 1
        offset += b - a
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("words")
    ap.add_argument("out")
    ap.add_argument("--cuts")
    ap.add_argument("--max-gap", type=float, default=0.6, help="pauses longer than this are shortened")
    ap.add_argument("--pad", type=float, default=0.12, help="seconds kept around each word")
    ap.add_argument("--keep-fillers", action="store_true")
    ap.add_argument("--captions", action="store_true")
    ap.add_argument("--height", type=int, default=TARGET_H, help="downscale when the short side is larger (0 = keep)")
    ap.add_argument("--quality", default="high", choices=["high", "medium", "low"])
    a = ap.parse_args()

    data = load_json(a.words)
    words = data["words"]
    deleted = set()
    if a.cuts:
        for first, last in load_json(a.cuts).get("delete", []):
            deleted.update(range(first, last + 1))

    info = probe(a.video)
    segs, kept = build_segments(words, deleted, info["duration"], a.max_gap, a.pad, a.keep_fillers)
    out_words = retime(kept, segs)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    filters = []
    # --height is the short side: portrait footage keeps its shape (1080x1920 -> 720x1280).
    width, height = info.get("width", 0), info.get("height", 0)
    if a.height and min(width, height) > a.height:
        k = a.height / min(width, height)
        width, height = (round(width * k / 2) * 2, a.height) if width >= height else (a.height, round(height * k / 2) * 2)
        filters.append(f"scale={width}:{height}:flags=lanczos")
    if a.captions:
        ass = out.with_suffix(".ass")
        write_ass(out_words, ass, width=width, height=height)
        filters.append(ass_filter(ass, FONTS_DIR))

    t0 = time.time()
    FFmpegService().clip_segments(a.video, segs, out, a.quality, ",".join(filters) or None)
    kept_dur = sum(b - x for x, b in segs)
    save_json({"source": str(Path(a.video).resolve()), "segments": segs}, out.with_suffix(".segments.json"))
    save_json({"duration": kept_dur, "words": out_words}, out.with_suffix(".words.json"))
    print(f"{len(segs)} segments, {info['duration']:.1f}s -> {kept_dur:.1f}s "
          f"(removed {info['duration'] - kept_dur:.1f}s), render {time.time() - t0:.1f}s -> {out}")


if __name__ == "__main__":
    main()
