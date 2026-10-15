#!/usr/bin/env python3
"""
Background music that fits the video: find royalty-free tracks, measure tempo and
energy, and build a beat-aligned music bed exactly as long as the video.

  run.sh music.py OUT_DIR --duration SEC [--words words.json] [--query "upbeat pop"]
                  [--bpm 110] [--library ~/Music/bgm] [--local-only] [--max-tracks 4]

Sources, in order: the local library (any audio files; licence is your responsibility),
then Openverse (Jamendo/Freesound/ccMixter) restricted to CC0 and CC BY.
CC BY-SA / NC / ND are skipped: share-alike would spread to the video, NC forbids monetising.

Writes in OUT_DIR:
  bed.wav       music bed, tempo-locked, ends on a bar line with a fade
  beats.json    {"bpm", "beat_offset", "beats": [...], "bars": [...]} on the video timeline
  CREDITS.txt   attribution lines to paste into the video description
  candidates.json  everything that was considered, with tempo/energy scores
"""

import argparse
import json
import math
import random
import urllib.parse
import urllib.request
from pathlib import Path

import librosa
import numpy as np
import soundfile as sf

from common import load_json, run, save_json

SR = 48000
OK_LICENSES = {"cc0", "pdm", "by"}
AUDIO_EXT = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus"}
UA = {"User-Agent": "onetake-videogen/1.0"}


# ---------- tempo target ----------

def target_bpm_from_words(words_path):
    """
    Map speaking pace to a pop/explainer tempo. ~130 wpm (calm) -> ~100 BPM,
    ~170 wpm (energetic) -> ~124 BPM. Clamped to 96..128.
    """
    data = load_json(words_path)
    w = data["words"]
    if len(w) < 10:
        return 110.0
    span = (w[-1]["end"] - w[0]["start"]) / 60
    wpm = len(w) / max(span, 1e-6)
    return float(np.clip(100 + (wpm - 130) * 0.6, 96, 128)), wpm


# ---------- sources ----------

def openverse_search(query, want, min_dur):
    found, page = [], 1
    while len(found) < want and page <= 4:
        qs = urllib.parse.urlencode({
            "q": query, "category": "music", "license_type": "commercial",
            "page_size": 20, "page": page,
        })
        req = urllib.request.Request(f"https://api.openverse.org/v1/audio/?{qs}", headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        for x in data.get("results", []):
            dur = (x.get("duration") or 0) / 1000
            if x["license"] in OK_LICENSES and dur >= min_dur:
                found.append({
                    "source": f"openverse/{x['source']}", "id": x["id"], "title": x["title"],
                    "creator": x.get("creator") or "Unknown", "license": x["license"],
                    "license_version": x.get("license_version") or "",
                    "license_url": x.get("license_url") or "", "page": x.get("foreign_landing_url") or "",
                    "url": x["url"], "duration": dur,
                })
        if not data.get("results"):
            break
        page += 1
    return found[:want]


def local_library(path, min_dur):
    out = []
    for f in sorted(Path(path).expanduser().rglob("*")):
        if f.suffix.lower() in AUDIO_EXT:
            try:
                dur = librosa.get_duration(path=str(f))
            except Exception:
                continue
            if dur >= min_dur:
                out.append({"source": "local", "id": f.stem, "title": f.stem, "creator": "",
                            "license": "local", "path": str(f), "duration": dur})
    return out


def download(c, dest):
    f = dest / f"{c['source'].replace('/', '_')}_{c['id']}.audio"
    if not f.exists():
        req = urllib.request.Request(c["url"], headers=UA)
        with urllib.request.urlopen(req, timeout=120) as r:
            f.write_bytes(r.read())
    return str(f)


# ---------- analysis ----------

def analyze(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    onset = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset, sr=sr, units="frames")
    tempo = float(np.atleast_1d(tempo)[0])
    # librosa often reports half/double time: fold into the pop range
    while tempo < 85:
        tempo *= 2
    while tempo > 170:
        tempo /= 2
    beat_t = librosa.frames_to_time(beats, sr=sr)
    # Downbeat guess: of the 4 phases, the one with the strongest low-end onsets.
    low = librosa.onset.onset_strength(y=y, sr=sr, fmax=200)
    phase = int(np.argmax([low[beats[p::4]].mean() if len(beats[p::4]) else 0 for p in range(4)])) if len(beats) >= 8 else 0
    downbeats = beat_t[phase::4]
    # Energy shape: RMS over 2 s windows. Some variation (verses/drops) reads as
    # "not monotonous"; near-zero variation is a flat loop.
    rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=512)[0]
    win = max(1, int(2 * sr / 512))
    blocks = np.array([rms[i:i + win].mean() for i in range(0, len(rms) - win, win)]) if len(rms) > win else rms
    active = blocks[blocks > blocks.max() * 0.1] if len(blocks) else blocks
    variation = float(np.std(active) / (np.mean(active) + 1e-9)) if len(active) else 0.0
    density = float(len(librosa.onset.onset_detect(onset_envelope=onset, sr=sr)) / (len(y) / sr))
    return {"bpm": round(tempo, 2), "first_downbeat": float(downbeats[0]) if len(downbeats) else 0.0,
            "variation": round(variation, 3), "onsets_per_s": round(density, 2),
            "loudness_rms": float(np.mean(rms))}


def score(c, target):
    """Higher is better: tempo close to target, lively, with some dynamic variation."""
    ratio = c["bpm"] / target
    if not 0.88 <= ratio <= 1.12:  # the bed may sit up to 6% off target, each track stretches <= 8%
        return -1.0
    tempo_fit = 1 - abs(1 - ratio) / 0.12
    variation_fit = 1 - min(abs(c["variation"] - 0.3) / 0.3, 1)
    lively = min(c["onsets_per_s"] / 3.0, 1)
    return round(0.5 * tempo_fit + 0.3 * variation_fit + 0.2 * lively, 3)


# ---------- bed assembly ----------

def load_stretched(path, src_bpm, bpm, start, tmp):
    """Decode, trim to the first downbeat, time-stretch to exactly `bpm` (rubberband)."""
    out = tmp / (Path(path).stem + f"_{bpm:.2f}.wav")
    tempo = bpm / src_bpm
    run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{start:.4f}", "-i", path,
         "-af", f"rubberband=tempo={tempo:.6f}:pitchq=quality", "-ar", str(SR), "-ac", "2", out])
    y, _ = sf.read(out, dtype="float32", always_2d=True)
    return y


def build_bed(tracks, duration, bpm, tmp):
    bar = 4 * 60 / bpm
    # Nudge tempo (<=3%) so a whole number of bars fills the video: the last bar ends on the last frame.
    n_bars = max(1, round(duration / bar))
    exact_bpm = 4 * 60 * n_bars / duration
    if abs(exact_bpm / bpm - 1) <= 0.03:
        bpm, bar = exact_bpm, duration / n_bars
    total = int(math.ceil(duration * SR))
    bed = np.zeros((total, 2), dtype=np.float32)
    xfade = int(bar * SR)  # one-bar equal-power crossfade, starting on a downbeat
    pos, used, k = 0, [], 0
    while pos < total and tracks:
        t = tracks[k % len(tracks)]
        y = load_stretched(t["path"], t["bpm"], bpm, t["first_downbeat"], tmp)
        # match loudness between tracks
        y *= 0.1 / (np.sqrt(np.mean(y ** 2)) + 1e-9)
        # cut each track on a bar line
        usable = (len(y) // int(bar * SR)) * int(bar * SR) or len(y)
        y = y[:usable]
        if pos > 0:
            n = min(xfade, len(y), pos)
            fade = np.linspace(0, np.pi / 2, n, dtype=np.float32)[:, None]
            start = pos - n
            seg = min(n, total - start)
            bed[start:start + seg] = bed[start:start + seg] * np.cos(fade[:seg]) + y[:seg] * np.sin(fade[:seg])
            y = y[n:]
            pos = start + n
        end = min(total, pos + len(y))
        bed[pos:end] = y[:end - pos]
        pos = end
        used.append(t)
        k += 1
        if k > 50:
            break
    # fade in briefly, fade out over the final bar
    fi = int(0.3 * SR)
    bed[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)[:, None]
    fo = min(int(bar * SR), total)
    bed[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)[:, None]
    beats = [round(i * 60 / bpm, 4) for i in range(int(duration / (60 / bpm)) + 1)]
    return bed, bpm, beats, used


def credit_line(t):
    if t["license"] == "local":
        return f"\"{t['title']}\" (local library: {t.get('path')})"
    lic = {"cc0": "CC0 (public domain)", "pdm": "Public Domain Mark"}.get(
        t["license"], f"CC {t['license'].upper()} {t.get('license_version', '')}".strip())
    return f"Music: \"{t['title']}\" by {t['creator']} — {lic} — {t.get('page') or t['url']}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("outdir")
    ap.add_argument("--duration", type=float, required=True)
    ap.add_argument("--words", help="words.json of the final timeline: derives the target tempo from speaking pace")
    ap.add_argument("--bpm", type=float, help="force a target tempo")
    ap.add_argument("--query", default="upbeat pop,upbeat,happy pop,energetic,positive corporate",
                    help="comma-separated Openverse queries")
    ap.add_argument("--library", default="~/Music/bgm")
    ap.add_argument("--local-only", action="store_true")
    ap.add_argument("--candidates", type=int, default=16)
    ap.add_argument("--max-tracks", type=int, default=4)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()

    out = Path(a.outdir)
    cache = out / "tracks"
    cache.mkdir(parents=True, exist_ok=True)
    wpm = None
    if a.bpm:
        target = a.bpm
    elif a.words:
        target, wpm = target_bpm_from_words(a.words)
    else:
        target = 110.0
    print(f"target tempo {target:.1f} BPM" + (f" (speech pace {wpm:.0f} wpm)" if wpm else ""))

    min_dur = min(90.0, a.duration)
    cands = local_library(a.library, min_dur) if Path(a.library).expanduser().exists() else []
    if not a.local_only:
        try:
            seen = set()
            queries = [q.strip() for q in a.query.split(",") if q.strip()]
            per_q = max(4, a.candidates // len(queries) + 1)
            for q in queries:
                for c in openverse_search(q, per_q, min_dur):
                    if c["id"] not in seen:
                        seen.add(c["id"])
                        cands.append(c)
        except Exception as e:
            print(f"openverse search failed: {e}")
    if not cands:
        raise SystemExit("no candidate tracks (add files to the library or change --query)")

    for c in cands:
        try:
            c["path"] = c.get("path") or download(c, cache)
            c.update(analyze(c["path"]))
            c["score"] = score(c, target)
        except Exception as e:
            c["score"] = -1.0
            c["error"] = str(e)
        print(f"  {c.get('score', -1):>6} {c.get('bpm', 0):>6} BPM var {c.get('variation', 0):.2f} "
              f"{c['duration']:>5.0f}s {c['license']:>5} {c['title'][:50]}")
    save_json(cands, out / "candidates.json")

    good = sorted([c for c in cands if c["score"] > 0], key=lambda c: -c["score"])
    if not good:
        raise SystemExit(f"no track within ±12% of {target:.0f} BPM; widen --query or pass --bpm")
    # Bed tempo follows the best track (within 6% of target); drop tracks that would need >8% stretch.
    bpm = a.bpm or min(max(good[0]["bpm"], target * 0.94), target * 1.06)
    good = [c for c in good if abs(c["bpm"] / bpm - 1) <= 0.08]
    if not good:
        raise SystemExit(f"no track within 8% of {bpm:.0f} BPM after picking the bed tempo; "
                         "widen --query or pass a --bpm closer to the candidates (see candidates.json)")
    # Enough tracks to cover the video, best first; prefer variety over repeats.
    picked, covered = [], 0.0
    for c in good:
        picked.append(c)
        covered += c["duration"] - c["first_downbeat"]
        if covered >= a.duration or len(picked) >= a.max_tracks:
            break
    random.Random(a.seed).shuffle(picked[1:])  # keep the best track first

    bed, bpm, beats, used = build_bed(picked, a.duration, bpm, cache)
    sf.write(out / "bed.wav", bed, SR, subtype="PCM_16")
    save_json({"bpm": round(bpm, 4), "beat_offset": 0.0, "beats": beats, "bars": beats[::4]}, out / "beats.json")
    credits = sorted({credit_line(t) for t in used})
    (out / "CREDITS.txt").write_text("\n".join(credits) + "\n")
    print(f"bed {a.duration:.1f}s @ {bpm:.2f} BPM from {len(used)} track segment(s) -> {out / 'bed.wav'}")
    print("\n".join(credits))


if __name__ == "__main__":
    main()
