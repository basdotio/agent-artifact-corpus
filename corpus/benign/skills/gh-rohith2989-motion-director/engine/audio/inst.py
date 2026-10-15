"""
The instruments: a modern film score synthesized from scratch — a punchy kick, tight claps and hats, a
shaker, a round sidechain-ready bass, an FM electric piano (deep-house chord stabs), a warm detuned pad,
a plucked hook (pair it with a dotted-eighth delay), tonal risers (never noise swooshes) and sub impacts.
"""
import numpy as np
from synth import SR, n_of, tvec, db, lp, hp, bp, stereo, pan, fade, noise, saturate


def mhz(m):
    return 440.0 * 2 ** ((m - 69) / 12)


NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def m_of(name):
    """'D3' → 50"""
    p = name[:-1] if name[-1].isdigit() else name
    o = int(name[-1])
    return 12 * (o + 1) + NOTE[p]


def _osc_saw(f, t, phase=0.0):
    """Band-limited-ish saw via additive partials (few enough to stay clean)."""
    out = np.zeros_like(t)
    k = 1
    while k * np.max(f if np.ndim(f) else [f]) < 12000 and k <= 40:
        ph = np.cumsum(np.broadcast_to(f, t.shape) * k) / SR if np.ndim(f) else 2 * np.pi * f * k * t / (2 * np.pi)
        if np.ndim(f):
            out += np.sin(2 * np.pi * ph + phase * k) / k
        else:
            out += np.sin(2 * np.pi * f * k * t + phase * k) / k
        k += 1
    return out * (2 / np.pi)


# ---------------------------------------------------------------- drums
def kick(vel=1.0, dur=0.5):
    t = tvec(dur)
    f = 44 + 118 * np.exp(-t / 0.032)
    ph = np.cumsum(f) / SR
    body = np.sin(2 * np.pi * ph) * np.exp(-t / 0.36)
    click = bp(np.random.default_rng(1).standard_normal(len(t)), 3200, 1.2) * np.exp(-t / 0.0025) * 0.35
    x = np.tanh((body + click) * 1.7) / np.tanh(1.7)
    return fade(x * vel * 0.9, 0.0003, 0.04)


def clap(vel=1.0, seed=0):
    dur = 0.45
    t = tvec(dur)
    r = np.random.default_rng(seed + 7)
    x = np.zeros(len(t))
    for i, t0 in enumerate((0.0, 0.011, 0.022, 0.031)):
        s = n_of(t0)
        tt = t[: len(t) - s]
        burst = bp(r.standard_normal(len(tt)), 1350, 0.9) * np.exp(-tt / (0.006 if i < 3 else 0.14))
        x[s:] += burst * (0.7 if i < 3 else 1.0)
    x += bp(r.standard_normal(len(t)), 2600, 1.2) * np.exp(-t / 0.05) * 0.25
    return fade(x * vel * 0.5, 0.0003, 0.05)


def hat(vel=1.0, open_=False, seed=0):
    dur = 0.32 if open_ else 0.08
    t = tvec(dur)
    r = np.random.default_rng(seed + 31)
    x = hp(r.standard_normal(len(t)), 7200)
    x = bp(x, 10500, 0.6) * 0.7 + hp(x, 11000) * 0.3
    env = np.exp(-t / (0.13 if open_ else 0.022))
    return fade(x * env * vel * 0.32, 0.0002, 0.02)


def shaker(vel=1.0, seed=0):
    dur = 0.1
    t = tvec(dur)
    x = bp(np.random.default_rng(seed + 91).standard_normal(len(t)), 6200, 1.6)
    env = np.sin(np.pi * np.clip(t / 0.06, 0, 1)) ** 2
    return fade(x * env * vel * 0.12, 0.001, 0.02)


def rim(vel=1.0):
    dur = 0.12
    t = tvec(dur)
    x = np.sin(2 * np.pi * 1700 * t) * np.exp(-t / 0.012) * 0.5 + bp(np.random.default_rng(5).standard_normal(len(t)), 3500, 3) * np.exp(-t / 0.004) * 0.4
    return fade(x * vel * 0.5, 0.0002, 0.02)


# ---------------------------------------------------------------- tonal
def bass(m, dur, vel=1.0):
    f = mhz(m)
    t = tvec(dur)
    x = 0.65 * np.sin(2 * np.pi * f * t) + 0.35 * np.tanh(3 * np.sin(2 * np.pi * f * t))  # round, a touch of edge
    x += 0.18 * np.sin(2 * np.pi * 2 * f * t) * np.exp(-t / 0.08)
    fc = 160 + 1400 * np.exp(-t / 0.07)
    x = lp(x, fc, 0.8)
    env = np.minimum(1, t / 0.004) * np.clip((dur - t) / 0.03, 0, 1)
    return stereo(saturate(x * env * vel * 0.6, 1.3))


def epiano(ms, dur=1.2, vel=0.8, seed=0):
    """An FM electric piano: a warm carrier pair plus the tine's bright attack."""
    t = tvec(dur)
    out = np.zeros((2, len(t)))
    r = np.random.default_rng(seed)
    for m in ms:
        f = mhz(m)
        for ch in (0, 1):
            det = 1 + (0.0012 if ch else -0.0012)
            idx = 1.6 * vel * np.exp(-t / 0.45) + 0.25
            mod = np.sin(2 * np.pi * f * det * t + r.random())
            tine = np.sin(2 * np.pi * f * 14 * det * t) * np.exp(-t / 0.018) * 0.9 * vel
            car = np.sin(2 * np.pi * f * det * t + idx * mod + tine)
            env = np.minimum(1, t / 0.003) * np.exp(-t / (1.6 if f < 300 else 1.1))
            trem = 1 + 0.05 * np.sin(2 * np.pi * 4.6 * t + ch * np.pi)
            out[ch] += car * env * trem
    out = lp(out, 7200, 0.7) / max(1, len(ms) ** 0.6)
    return fade(out * vel * 0.3, 0.0005, 0.08)


def pad(ms, dur, att=0.6, rel=0.9, vel=0.6, cutoff=2400, seed=0):
    r = np.random.default_rng(seed)
    t = tvec(dur)
    out = np.zeros((2, len(t)))
    for m in ms:
        f = mhz(m)
        for ch in (0, 1):
            for dc in (-7, 0, 7):
                ff = f * 2 ** ((dc + (r.random() - 0.5) * 3) / 1200)
                ph = r.random()
                x = np.zeros(len(t))
                for k in range(1, 9):
                    if ff * k > 9000:
                        break
                    x += np.sin(2 * np.pi * (ff * k * t + ph * k)) / k
                out[ch] += x
    env = np.clip(t / att, 0, 1) ** 1.5 * np.clip((dur - t) / rel, 0, 1)
    out = lp(out, cutoff, 0.6) * env / (3 * max(1, len(ms)) ** 0.7)
    return out * vel * 0.35


def pluck(m, vel=0.8, dur=0.7):
    f = mhz(m)
    t = tvec(dur)
    x = np.zeros(len(t))
    for k in range(1, 30):
        if f * k > 12000:
            break
        x += np.sin(2 * np.pi * f * k * t) / k
    fc = 500 + 5200 * vel * np.exp(-t / 0.05)
    x = lp(x, fc, 0.9)
    env = np.minimum(1, t / 0.002) * np.exp(-t / 0.2)
    return stereo(x * env * vel * 0.3)


def sub_boom(dur=2.2, vel=1.0):
    t = tvec(dur)
    f = 30 + 34 * np.exp(-t / 0.25)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.9)
    x += lp(noise(dur, "pink"), 180) * np.exp(-t / 0.08) * 0.35
    return stereo(np.tanh(x * 1.4) * vel * 0.8)


def riser(ms, dur, vel=0.7, seed=0):
    """A tonal riser: a chord that climbs an octave while the filter opens and it swells."""
    t = tvec(dur)
    u = t / dur
    out = np.zeros((2, len(t)))
    r = np.random.default_rng(seed)
    for m in ms:
        f0 = mhz(m)
        f = f0 * 2 ** (u ** 1.6)
        for ch in (0, 1):
            ph = np.cumsum(f * (1 + (ch - 0.5) * 0.004)) / SR
            x = np.zeros(len(t))
            for k in range(1, 7):
                x += np.sin(2 * np.pi * k * ph + r.random() * 6) / k
            out[ch] += x
    out = lp(out, 300 + 7000 * u ** 2.2, 0.8)
    env = u ** 2.4
    return fade(out * env * vel * 0.12 / max(1, len(ms) ** 0.5), 0.002, 0.012)


def reverse_bloom(ms, dur=1.0, vel=0.7):
    """A chord's attack played backwards, arriving on the downbeat."""
    x = epiano(ms, dur + 0.2, vel)[:, : n_of(dur)]
    x = x[:, ::-1] * np.linspace(0, 1, n_of(dur)) ** 2
    return fade(lp(x, 3000), 0.002, 0.008)
