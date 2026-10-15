"""
The mix: voice first (if there is one), the score under it, and the UI sounds — each one caused by a cue the
composition declared — then the master.

  node tools/probe.js 0 "window.getCues()" > audio/cues.json      (export cues from the picture)
  python audio/score.py                                            (music: audio/out/music.wav)
  python audio/mix.py                                              ->  audio/out/mix.wav

Targets: -14 LUFS integrated (web/social), true peak <= -1.5 dBTP, voice ~10 dB over the bed, the bed ducked
~7 dB under speech and ~3.5 dB under dense typing. Optional inputs: audio/out/vo.wav (placed voice, from
voice/vo_build.py), audio/assets/<name>.wav for user-supplied real-app sounds (SFX entry with "file").

SFX: map each cue type to a recipe. Add types freely; unknown types are reported, never silently dropped.
"""
import json
import os

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.ndimage import uniform_filter1d
from scipy.signal import resample_poly

from synth import SR, Canvas, n_of, hp, peq, shelf, reverb, db, stereo, tp_limit
import sfx as S

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

# cue type -> (recipe(cue) -> mono array, gain dB, time offset s)  — tune per film; keep UI sounds quiet
SFX = {
    "key": (lambda c: S.wood_key(int(c.get("i", 0)) * 13 + sum(map(ord, c.get("ch", ""))) % 97, heavy=c.get("ch") in ("space", "tab")), -19, 0.0),
    "key_enter": (lambda c: S.wood_key(9000 + int(c.get("i", 0)), heavy=True), -15, 0.0),
    "click": (lambda c: S.mouse_click(0.9), -13, -0.004),
    "tap": (lambda c: S.soft_tap(0.7, int(c["t"] * 10) % 97, 1.0), -18, 0.0),
    "tick": (lambda c: S.felt_tick(0.9, int(c["t"] * 10) % 53), -18, 0.0),
    "relay": (lambda c: S.relay(int(c.get("i", 0))), -22, 0.0),
    "lock": (lambda c: S.lock(int(c.get("i", 0))), -15, 0.0),
    "done": (lambda c: S.lock(int(c.get("i", 0)) + 3), -17, 0.05),
    "tock": (lambda c: S.tock(0.85), -15, 0.0),
    "open": (lambda c: S.drawer(), -16, 0.0),
    "file": (lambda c: S.file_land(), -13, 0.0),
    "paper": (lambda c: S.paper(int(c.get("i", 0))), -13, 0.0),
    "flip": (lambda c: S.card_flip(int(c.get("i", 0))), -19, 0.0),
    "flap": (lambda c: S.flap(), -14, -0.02),
    "denied": (lambda c: S.denied(), -13, 0.0),
    "panel": (lambda c: S.landing(0.9), -15, 0.95),  # panel slide-overs land ~0.95 s after they start
    "window_in": (lambda c: S.settle(0.9), -17, 0.55),
    "glide": (lambda c: S.tonal_glide(c.get("dur", 0.6), c.get("f0", 420.0), c.get("f1", 180.0)), -18, 0.0),
    "impact": (lambda c: S.brake(), -12, 0.0),
    "lockup": (lambda c: S.lockup_mark(), -11, -0.02),
}
SILENT = {"mate_pop", "step_on", "outro_swell", "note"}  # cue types the score (or nothing) carries


def load(path):
    x, sr = sf.read(path, always_2d=True)
    x = x.T.astype(np.float64)
    if sr != SR:
        x = resample_poly(x, SR, sr, axis=1)
    return x if x.shape[0] == 2 else np.vstack([x[0], x[0]])


def compress(x, thr_db=-26.0, ratio=2.4, att=0.008, rel=0.14, knee=6.0):
    m = np.sqrt(uniform_filter1d((0.5 * (x[0] + x[1])) ** 2, size=n_of(0.01)) + 1e-12)
    over = 20 * np.log10(m) - thr_db
    gr = np.where(over <= -knee / 2, 0, np.where(over >= knee / 2, over * (1 - 1 / ratio), (1 - 1 / ratio) * (over + knee / 2) ** 2 / (2 * knee)))
    g = np.empty_like(gr)
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    cur = 0.0
    for i in range(len(gr)):
        v = gr[i]
        cur = a * cur + (1 - a) * v if v > cur else r * cur + (1 - r) * v
        g[i] = cur
    return x * db(-g)


def deess(v, f0=5200.0, thr_db=-30.0, max_cut=7.0):
    hi = hp(v, f0, 0.7)
    lo = v - hi
    e = np.sqrt(uniform_filter1d((0.5 * (hi[0] + hi[1])) ** 2, size=n_of(0.004)) + 1e-12)
    cut = uniform_filter1d(np.clip((20 * np.log10(e) - thr_db) * 0.6, 0, max_cut), size=n_of(0.006))
    return lo + hi * db(-cut)


def voice_chain(v):
    v = hp(v, 75)
    v = shelf(v, 160, 1.2, "low")
    v = peq(v, 260, -1.0, 1.0)
    v = peq(v, 3600, 1.8, 0.9)
    v = shelf(v, 9000, 2.0, "high")
    v = compress(v)
    v = deess(v)
    return reverb(v, "plate", 0.07)


def duck_env(v, depth_db=7.0, att=0.06, rel=0.45):
    m = np.sqrt(uniform_filter1d((0.5 * (v[0] + v[1])) ** 2, size=n_of(0.03)) + 1e-12)
    on = (20 * np.log10(m) > -46).astype(float)
    g = np.empty_like(on)
    a, r = np.exp(-1 / (att * SR)), np.exp(-1 / (rel * SR))
    cur = 0.0
    for i in range(len(on)):
        cur = a * cur + (1 - a) * on[i] if on[i] > cur else r * cur + (1 - r) * on[i]
        g[i] = cur
    g = np.maximum(g, uniform_filter1d(g, size=n_of(0.5)))
    return db(-depth_db * np.clip(g, 0, 1))


def main():
    cfg = json.load(open(os.path.join(os.path.dirname(HERE), "comp", "config.json")))
    DUR = cfg["duration"]
    n = n_of(DUR)
    cues = json.load(open(os.path.join(HERE, "cues.json")))
    fx = Canvas(DUR + 3)
    unknown, typing = {}, []
    for c in cues:
        k = c["type"]
        if c.get("file"):
            fx.add(c["t"], load(os.path.join(HERE, "assets", c["file"])), c.get("gain", -14))
            continue
        if k in SILENT:
            continue
        if k not in SFX:
            unknown[k] = unknown.get(k, 0) + 1
            continue
        recipe, gain, off = SFX[k]
        fx.add(c["t"] + off, recipe(c), gain + c.get("gain", 0), c.get("pan", 0.0))
        if k == "key":
            typing.append(c["t"])
    if unknown:
        print("NOTE: cue types with no sound (add them to SFX or SILENT):", unknown)
    music = load(os.path.join(OUT, "music.wav"))
    music = np.pad(music, ((0, 0), (0, max(0, n - music.shape[1]))))[:, :n]
    fxb = reverb(fx.buf[:, :n], "room", 0.12)
    meter = pyln.Meter(SR)
    # the bed gives way to dense typing (control-rate envelope, soft edges)
    CR = 200
    marks = np.zeros(int(DUR * CR) + 1)
    for t in typing:
        marks[min(len(marks) - 1, int(t * CR))] += 1
    dens = np.convolve(marks, np.ones(int(0.6 * CR)), mode="same")
    duck = np.convolve(np.clip(dens / 3.0, 0, 1), np.hanning(int(0.25 * CR)) / np.hanning(int(0.25 * CR)).sum(), mode="same")
    music *= np.interp(np.arange(n) / SR, np.arange(len(duck)) / CR, db(-3.5 * duck))
    vo_path = os.path.join(OUT, "vo.wav")
    if os.path.exists(vo_path):
        v = load(vo_path)
        v = np.pad(v, ((0, 0), (0, max(0, n - v.shape[1]))))[:, :n]
        v = voice_chain(v)
        v *= db(-17 - meter.integrated_loudness(v.T))
        music *= db(-21.0 - meter.integrated_loudness(music.T))
        music *= duck_env(v, 7.0)
        mix = v + music + fxb * db(7.5)
    else:
        mix = music * db(-1.0) + fxb
    mix = hp(mix, 22)
    for _ in range(4):
        mix = mix * db(-14.0 - meter.integrated_loudness(mix.T))
        mix = tp_limit(mix, -1.6, 1.5, 90.0)
    fade = cfg.get("audioFadeOut", 1.2)
    e0 = n_of(DUR - fade)
    mix[:, e0:] *= np.cos(np.linspace(0, np.pi / 2, n - e0)) ** 2
    L = meter.integrated_loudness(mix.T)
    tp = 20 * np.log10(np.abs(resample_poly(mix, 4, 1, axis=1)).max() + 1e-12)
    os.makedirs(OUT, exist_ok=True)
    sf.write(os.path.join(OUT, "mix.wav"), mix.T.astype(np.float32), SR, subtype="FLOAT")
    sf.write(os.path.join(OUT, "sfx.wav"), (fxb.T * 0.5).astype(np.float32), SR)
    print(f"mix: {L:.2f} LUFS integrated, true peak {tp:.2f} dBTP, {mix.shape[1] / SR:.2f}s  ({len(cues)} cues)")


if __name__ == "__main__":
    main()
