"""
The score: a film score synthesized from scratch and arranged bar by bar against the picture.

python audio/score.py [audio/score_plan.json]  ->  audio/out/music.wav  (+ stems in audio/out/stems/)

The plan (JSON) is the whole arrangement — write it from docs/PLAN.md so sections start on bars:
  bpm, offset (s, the first downbeat), duration (s)
  style: "house" (four-on-the-floor, off-beat bass, ep stabs) | "halftime" (kick 1, clap 3, held chords) |
         "bed" (no drums: pad, soft ep, pulse — for under a voice)
  chords: [{name, bass, ep: [notes], pad: [notes]}]   one per bar, looped
  hook:   [[[beat, note, beats], ...] per chord]         optional melody figure (plucked, delayed)
  sections: [{bars: [b0, b1], parts: {kick, clap, hat, ohat, shaker, bass, ep, pad, hook, drone, pulse: dB or null,
             lpf: [f0, f1]}}]  — parts may be "FULL" or {"FULL": true, ...overrides}
  rises:   [[t0, t1]]  tonal risers into section downbeats (never noise)
  impacts: [t]         sub impacts on downbeats       blooms: [t]  reversed chord blooms arriving at t
  hits:    [{t, chord}] struck chord + impact (titles, kinetic words)
  end:     {t, notes: [...], bass, dots: true}           the last chord ringing out (+ a 3-note figure)
Keys that work for premium product films: D minor/Dorian (Dm9 Bbmaj9 Gm9 A7sus4), F major 7 colours
(Fmaj9 Dm9 Bbmaj9 Csus), A minor 9. Avoid major-key bells and "happy ukulele" anything.
"""
import json
import os
import sys

import numpy as np
import soundfile as sf

from synth import SR, n_of, db, lp, hp, stereo, Canvas, saturate, delay, reverb, chorus, shelf, peq, tvec
from inst import kick, clap, hat, shaker, bass, epiano, pad, pluck, sub_boom, riser, reverse_bloom, m_of

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

FULL = dict(kick=-1.5, clap=-3, hat=-9, ohat=None, shaker=-16, bass=-2.5, ep=-3, pad=-10, hook=-5)
OFF = dict(kick=None, clap=None, hat=None, ohat=None, shaker=None, bass=None, ep=None, pad=None, hook=None)


def parts_of(spec):
    if spec == "FULL":
        return dict(FULL)
    if isinstance(spec, dict) and spec.get("FULL"):
        d = dict(FULL)
        d.update({k: v for k, v in spec.items() if k != "FULL"})
        return d
    d = dict(OFF)
    d.update(spec or {})
    return d


def build(plan):
    BPM = plan["bpm"]
    BEAT = 60 / BPM
    BAR = 4 * BEAT
    OFFS = plan.get("offset", 0.0)
    DUR = plan["duration"] + 2.0
    style = plan.get("style", "house")
    M = m_of
    chords = [{"bass": M(c["bass"]), "ep": [M(n) for n in c["ep"]], "pad": [M(n) for n in c["pad"]], "name": c.get("name", "")} for c in plan["chords"]]
    hook = [[(b, M(n), ln) for b, n, ln in fig] for fig in plan.get("hook", [])]
    sections = [(s["bars"][0], s["bars"][1], parts_of(s["parts"])) for s in plan["sections"]]
    bar_t = lambda b: OFFS + b * BAR

    def parts_at(b):
        for b0, b1, d in sections:
            if b0 <= b < b1:
                return d
        return None

    drums, bassC, keys, pads, hooks, fx = (Canvas(DUR) for _ in range(6))
    kicks = []
    rng = np.random.default_rng(3)
    K = kick(1.0)
    nbars = int(np.ceil((plan["duration"] - OFFS) / BAR)) + 1
    for b in range(nbars):
        P = parts_at(b)
        if P is None:
            continue
        t0 = bar_t(b)
        ch = chords[b % len(chords)]
        for q in range(4):
            tb = t0 + q * BEAT
            on_kick = q in (0, 2) if style == "house" else q == 0
            if P.get("kick") is not None and (style == "house" or on_kick):
                drums.add(tb, K, P["kick"])
                kicks.append(tb)
            clap_q = (1, 3) if style == "house" else (2,)
            if P.get("clap") is not None and q in clap_q:
                drums.add(tb + 0.004, clap(1.0, seed=b * 4 + q), P["clap"], 0.0)
            if P.get("hat") is not None:
                drums.add(tb + BEAT / 2, hat(0.9 + 0.1 * rng.random(), seed=b * 8 + q), P["hat"], 0.35)
                drums.add(tb + BEAT / 4, hat(0.45, seed=b * 8 + q + 100), P["hat"] - 7, -0.45)
                drums.add(tb + 3 * BEAT / 4, hat(0.4, seed=b * 8 + q + 200), P["hat"] - 8, 0.5)
            if P.get("ohat") is not None:
                drums.add(tb + BEAT / 2, hat(1.0, open_=True, seed=b * 8 + q + 300), P["ohat"], 0.3)
            if P.get("shaker") is not None:
                for s16 in range(4):
                    drums.add(tb + s16 * BEAT / 4, shaker(0.6 + 0.4 * (s16 % 2), seed=b * 16 + q * 4 + s16), P["shaker"], -0.55 if s16 % 2 else 0.45)
        if P.get("bass") is not None:
            pat = ((0, 0), (1, 0), (2, 12), (3, 0)) if style == "house" else ((0, 0), (2.5, 0))
            for q, oct_ in pat:
                off = BEAT / 2 if style == "house" else 0
                bassC.add(t0 + q * BEAT + off, bass(ch["bass"] + oct_, BEAT * (0.42 if style == "house" else 1.4), 0.95), P["bass"])
        if P.get("ep") is not None:
            keys.add(t0, epiano(ch["ep"], 1.6, 0.55, seed=b), P["ep"] - 5)
            stabs = (0, 1, 2, 3) if style == "house" else ((1.5, 2.5) if style == "bed" else (1.5, 3.5))
            for q in stabs:
                keys.add(t0 + q * BEAT + (BEAT / 2 if style == "house" else 0), epiano(ch["ep"], 0.32 if style == "house" else 0.9, 0.8 if style == "house" else 0.45, seed=b * 4 + int(q * 2)), P["ep"])
        if P.get("pulse") is not None:  # an eighth-note muted pulse on the chord's root (beds)
            for e in range(8):
                keys.add(t0 + e * BEAT / 2, pluck(ch["bass"] + 24, 0.45, 0.22), P["pulse"] - (3 if e % 2 else 0))
        if P.get("drone") is not None:
            tt = tvec(BAR + 0.3)
            f = 440.0 * 2 ** ((ch["bass"] - 69) / 12)
            dr = (np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3 * f * tt))
            dr *= np.clip(tt / 0.25, 0, 1) * np.clip((BAR + 0.3 - tt) / 0.3, 0, 1)
            bassC.add(t0, stereo(dr * 0.35), P["drone"])
        if P.get("pad") is not None:
            pads.add(t0 - 0.05, pad(ch["pad"], BAR + 0.5, att=0.35, rel=0.5, vel=0.6, cutoff=2600, seed=b), P["pad"])
        if P.get("hook") is not None and hook:
            for bt, m, ln in hook[b % len(hook)]:
                hooks.add(t0 + bt * BEAT, pluck(m, 0.85, ln * BEAT + 0.35), P["hook"])

    def sweep(canvas, b0, b1, f0, f1):
        i0, i1 = n_of(bar_t(b0)), n_of(bar_t(b1))
        seg = canvas.buf[:, i0:i1]
        if seg.shape[1]:
            canvas.buf[:, i0:i1] = lp(seg, np.geomspace(f0, f1, seg.shape[1]), 0.9)

    for b0, b1, d in sections:
        if d.get("lpf"):
            for c in (drums, bassC, keys, pads):
                sweep(c, b0, b1, *d["lpf"])

    c0 = chords[0]
    for h in plan.get("hits", []):
        ch = chords[h.get("chord", 0) % len(chords)]
        fx.add(h["t"], epiano(ch["ep"] + [ch["ep"][-1] + 12], 1.9, 0.95, seed=int(h["t"] * 10)), -1)
        fx.add(h["t"], sub_boom(1.8, 0.8), -3)
        fx.add(h["t"], stereo(K), -1)
        fx.add(h["t"] - 0.6, riser([ch["bass"] + 24, ch["bass"] + 31], 0.6, 0.6, seed=int(h["t"])), -6)
    for a, b in plan.get("rises", []):
        fx.add(a, riser([c0["bass"] + 12, c0["bass"] + 19, c0["bass"] + 26], b - a, 0.8, seed=int(a * 10)), -2)
    for t in plan.get("impacts", []):
        fx.add(t, sub_boom(2.0, 0.85), -4)
    for t in plan.get("blooms", []):
        fx.add(t - 1.0, reverse_bloom(c0["ep"], 1.0, 0.7), -6)
    e = plan.get("end")
    if e:
        notes = [M(n) for n in e["notes"]]
        fx.add(e["t"], epiano(notes, 6.0, 0.8, seed=777), -1)
        fx.add(e["t"], pad([M(e.get("bass", "D2"))] + notes, 7.5, att=0.05, rel=4.0, vel=0.7, cutoff=3000, seed=9), -6)
        fx.add(e["t"], sub_boom(3.0, 0.9), -3)
        if e.get("dots", True):
            top = sorted(notes)[-3:]
            for k, m in enumerate(top):
                fx.add(e["t"] + 2.2 + k * 0.22, pluck(m + 12 if m < 69 else m, 0.7, 1.6), -9)

    # sidechain: bass, keys, pads, hook breathe with the kick
    env = np.ones(n_of(DUR))
    tt = np.arange(len(env)) / SR
    for tk in kicks:
        i = n_of(tk)
        j = min(len(env), i + n_of(0.32))
        u = tt[i:j] - tk
        env[i:j] = np.minimum(env[i:j], 1 - 0.72 * np.exp(-u / 0.085) * np.clip(u / 0.004, 0, 1) ** 0.5)
    for c, depth in ((bassC, 1.0), (keys, 0.6), (pads, 0.8), (hooks, 0.35)):
        c.buf *= 1 - depth * (1 - env)
    hooks.buf = delay(hooks.buf, BEAT * 0.75, fb=0.32, damp=0.45, mix=0.28)
    keys.buf = chorus(keys.buf, depth_ms=2.2, base_ms=8.0, rate=0.3, mix=0.45)
    pads.buf = chorus(pads.buf, depth_ms=3.5, base_ms=11.0, rate=0.22, mix=0.6)
    keys.buf = reverb(keys.buf, "hall", 0.18)
    pads.buf = reverb(pads.buf, "hall", 0.32)
    hooks.buf = reverb(hooks.buf, "hall", 0.18)
    fx.buf = reverb(fx.buf, "hall", 0.14)

    os.makedirs(os.path.join(OUT, "stems"), exist_ok=True)
    stems = {"drums": drums, "bass": bassC, "keys": keys, "pads": pads, "hook": hooks, "fx": fx}
    mixb = np.zeros((2, n_of(DUR)))
    GAIN = {"drums": -1.0, "bass": -5, "keys": 1.5, "pads": 0, "hook": 1.0, "fx": -1}
    for k, c in stems.items():
        x = hp(c.buf, 28)
        sf.write(os.path.join(OUT, "stems", f"{k}.wav"), (x.T * 0.5).astype(np.float32), SR)
        mixb += x * db(GAIN[k])
    mixb = shelf(mixb, 110, -4.0, "low")
    mixb = peq(mixb, 320, -1.5, 0.9)
    mixb = peq(mixb, 1800, 1.5, 0.8)
    mixb = shelf(mixb, 6500, -1.0, "high")
    mixb = saturate(mixb * 0.8, 1.2)
    mixb = mixb / (np.abs(mixb).max() + 1e-9) * 0.89
    mixb = mixb[:, : n_of(plan["duration"])]
    sf.write(os.path.join(OUT, "music.wav"), mixb.T.astype(np.float32), SR)
    print(f"music {mixb.shape[1] / SR:.2f}s  bpm {BPM}  style {style}  bars {nbars}")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "score_plan.json")
    build(json.load(open(path)))
