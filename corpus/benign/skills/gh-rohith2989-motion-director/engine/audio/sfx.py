"""
The sound-effects library. Every sound has a cause on screen and is synthesized here — tactile, dry, quiet.
House rules: no bells or "tinks" on UI events, no cartoon bloops/boings, no filtered-noise whooshes (use a
tonal glide, a low settle or nothing), nothing cute. Real app notification sounds (Slack, Teams, iMessage…)
only if the user supplies the file — never bundle them.

Each recipe returns a mono float array at 48 kHz (place with Canvas.add(t, x, gain_db, pan)).
"""
import numpy as np
from synth import *  # noqa: F401,F403  (SR, n_of, tvec, lp, hp, bp, noise, glide, phase_of, fade, ...)


def _at(buf, x, t):
    i = n_of(t)
    j = min(buf.shape[-1], i + x.shape[-1])
    if j > i:
        buf[..., i:j] += x[..., : j - i]
    return buf


def _resonate(exc, modes):
    out = np.zeros_like(exc)
    for f, q, g in modes:
        out += bp(exc, f, q) * g
    return out


# ------------------------------------------------------------ keys and pointer
def wood_key(k=0, heavy=False):
    """One keystroke on a mechanical board in a solid-wood case: the deep 'thock' of the switch
    bottoming out, the case answering, then the lighter upstroke."""
    rng = np.random.default_rng(700 + k)
    dur = 0.2
    t = tvec(dur)
    p = 1 + (rng.random() - 0.5) * 0.12
    burst = rng.standard_normal(len(t)) * np.exp(-t / 0.0009)
    body = [(185 * p, 5, 1.6), (430 * p, 7, 1.1), (760 * p, 9, 0.7), (1320 * p, 10, 0.4), (2450 * p, 8, 0.22), (4100 * p, 6, 0.1)]
    if heavy:
        body = [(f * 0.78, q, g * (1.25 if f < 600 else 0.8)) for f, q, g in body]
    press = lp(_resonate(burst, body), 5200)
    rel_t = 0.055 + rng.random() * 0.04
    burst2 = rng.standard_normal(len(t)) * np.exp(-t / 0.0006)
    rel = _resonate(burst2, [(610 * p, 9, 0.35), (1500 * p, 10, 0.3), (3300 * p, 8, 0.18)])
    out = press.copy()
    i = n_of(rel_t)
    out[i:] += rel[: len(out) - i]
    if heavy:  # the stabiliser wire of a big key
        j = n_of(0.012)
        out[j:] += _resonate(rng.standard_normal(len(t)) * np.exp(-t / 0.002), [(1900, 14, 0.12)])[: len(out) - j]
    return fade(out * (0.8 + 0.35 * rng.random()), 0.0002, 0.02)


def soft_tap(vel=1.0, seed=0, bright=1.0):
    """A haptic tap: a small dry click with a little low body."""
    rng = np.random.default_rng(seed)
    dur = 0.09
    t = tvec(dur)
    p = 1 + (rng.random() - 0.5) * 0.2
    x = bp(noise(dur), 2600 * p * bright, 1.3) * np.exp(-t / 0.0018) * 0.7
    x += np.sin(2 * np.pi * 175 * p * t) * np.exp(-t / 0.014) * 0.55
    return fade(x * vel, 0.0002, 0.01)


def mouse_click(vel=1.0):
    """A trackpad/mouse click: the press and, 70 ms later, the release."""
    dur = 0.12
    t = tvec(dur)
    a = bp(noise(dur), 3400, 1.5) * np.exp(-t / 0.0014) + bp(noise(dur), 1100, 1.2) * np.exp(-t / 0.004) * 0.4
    y = a.copy()
    j = n_of(0.07)
    y[j:] += a[: len(y) - j] * 0.5
    return fade(y * 0.7 * vel, 0.0001, 0.01)


# ------------------------------------------------------------ confirmations and objects
def lock(i=0):
    """A confirmation that locks in (connected, approved, step done): a precise mechanical detent — a tiny latch tick, then
    a short low 'clunk' of a well-made mechanism seating. Felt as much as heard."""
    rng = np.random.default_rng(40 + i)
    dur = 0.32
    t = tvec(dur)
    p = 1 + (rng.random() - 0.5) * 0.08
    latch = bp(rng.standard_normal(len(t)), 3300 * p, 2.2) * np.exp(-t / 0.0011) * 0.55
    seat = np.zeros(len(t))
    j = n_of(0.013)
    exc = rng.standard_normal(len(t)) * np.exp(-t / 0.0016)
    body = _resonate(exc, [(150 * p, 4, 1.4), (345 * p, 6, 0.9), (620 * p, 8, 0.45), (1180 * p, 9, 0.2)])
    seat[j:] = body[: len(t) - j]
    thump = np.sin(2 * np.pi * phase_of(glide(dur, 78, 52, 0.02))) * np.exp(-t / 0.05) * 0.5
    return fade(latch + lp(seat, 3000) + thump, 0.0002, 0.03)


def felt_tick(vel=1.0, seed=0):
    """A soft, dry felt tick — a pencil set down, not a chime. Highlights, list items, small marks."""
    rng = np.random.default_rng(90 + seed)
    dur = 0.08
    t = tvec(dur)
    x = lp(bp(rng.standard_normal(len(t)), 1700, 1.1), 3200) * np.exp(-t / 0.003) * 0.6
    x += np.sin(2 * np.pi * 240 * t) * np.exp(-t / 0.012) * 0.25
    return fade(x * vel, 0.0002, 0.01)


def relay(k=0, n=17):
    """A tiny relay click, each a little different (fast sequences: counters, a list filling)."""
    rng = np.random.default_rng(300 + k)
    dur = 0.06
    t = tvec(dur)
    f = 2100 + 1500 * rng.random()
    x = bp(rng.standard_normal(len(t)), f, 3.0) * np.exp(-t / 0.0012)
    x += np.sin(2 * np.pi * (380 + 120 * rng.random()) * t) * np.exp(-t / 0.006) * 0.3
    return fade(x, 0.0001, 0.008)


def tock(vel=1.0):
    """A single low wooden tock: a message landing, a ✓ settling."""
    dur = 0.3
    t = tvec(dur)
    exc = noise(dur) * np.exp(-t / 0.0012)
    x = _resonate(exc, [(265, 7, 1.2), (590, 9, 0.5), (1210, 10, 0.18)])
    return fade(lp(x, 3000) * vel, 0.0002, 0.03)


def drawer():
    """Something opening (a panel, sources, a menu): a small drawer on good runners — two soft detents and a low body."""
    out = np.zeros(n_of(0.35))
    _at(out, soft_tap(0.55, 11, 0.8), 0.0)
    _at(out, soft_tap(0.4, 12, 0.7), 0.16)
    t = tvec(0.35)
    out += np.sin(2 * np.pi * 120 * t) * np.exp(-t / 0.05) * 0.12
    return fade(out, 0.0002, 0.03)


def file_land():
    """A file arriving (PDF, sheet, image): paper set down on felt — a soft low thump, a few grains."""
    rng = np.random.default_rng(17)
    dur = 0.5
    t = tvec(dur)
    x = np.sin(2 * np.pi * phase_of(glide(dur, 118, 64, 0.03))) * np.exp(-t / 0.08) * 0.8
    x += lp(noise(dur, "pink"), 700) * np.exp(-t / 0.012) * 0.3
    for _ in range(9):
        tk = rng.uniform(0.004, 0.05)
        g = n_of(0.003)
        i = n_of(tk)
        x[i: i + g] += hp(rng.standard_normal(g), 3000) * np.hanning(g) * rng.uniform(0.05, 0.14)
    return fade(x, 0.0003, 0.05)


def paper(seed=0, vel=1.0):
    """A page set down: a soft contact thump with a few fibre grains (short, textured, not a swoosh)."""
    rng = np.random.default_rng(600 + seed)
    dur = 0.3
    t = tvec(dur)
    x = np.sin(2 * np.pi * phase_of(glide(dur, 140, 80, 0.02))) * np.exp(-t / 0.035) * 0.45
    for _ in range(12):
        tk = rng.uniform(0.0, 0.06)
        g = n_of(0.004)
        i = n_of(tk)
        x[i: i + g] += hp(rng.standard_normal(g), 2500) * np.hanning(g) * rng.uniform(0.04, 0.11)
    return fade(lp(x, 6000) * vel, 0.0003, 0.04)


def card_flip(seed=0, vel=1.0):
    """A card turning over: a soft, short flick of a stiff card — a bright edge, a little body."""
    rng = np.random.default_rng(800 + seed)
    dur = 0.09
    t = tvec(dur)
    p = 1 + (rng.random() - 0.5) * 0.18
    x = bp(rng.standard_normal(len(t)), 3200 * p, 1.4) * np.exp(-t / 0.0035) * 0.55
    x += bp(rng.standard_normal(len(t)), 950 * p, 1.1) * np.exp(-t / 0.009) * 0.35
    x += np.sin(2 * np.pi * 165 * p * t) * np.exp(-t / 0.016) * 0.3
    return fade(x * vel, 0.0002, 0.02)


def flap():
    """A split-flap leaf turning (a word changing in place): a tick, the leaf landing, a small low body."""
    dur = 0.2
    out = np.zeros(n_of(dur))
    t = tvec(dur)
    for k, (t0, f, g) in enumerate(((0.0, 4300, 0.5), (0.034, 1250, 0.7))):
        i = n_of(t0)
        e = bp(np.random.default_rng(900 + k).standard_normal(len(t) - i), f, 1.6) * np.exp(-t[: len(t) - i] / 0.004) * g
        out[i:] += e
    out += np.sin(2 * np.pi * 140 * t) * np.exp(-t / 0.03) * 0.25
    return fade(out, 0.0002, 0.03)


def denied():
    """A refusal (blocked, denied): two dull low knocks, close together."""
    out = np.zeros(n_of(0.4))
    for k, t0 in enumerate((0.0, 0.11)):
        s = tock(0.9 - 0.2 * k)
        i = n_of(t0)
        out[i: i + len(s)] += s[: len(out) - i]
    return lp(out, 1600)


# ------------------------------------------------------------ arrivals, impacts, transitions
def landing(vel=1.0):
    """A panel settling into place: a soft, low, felt landing (no air, no whoosh)."""
    dur = 0.35
    t = tvec(dur)
    x = np.sin(2 * np.pi * phase_of(glide(dur, 96, 58, 0.03))) * np.exp(-t / 0.07) * 0.7
    x += lp(noise(dur, "pink"), 500) * np.exp(-t / 0.01) * 0.18
    return fade(x * vel, 0.0005, 0.05)


def settle(vel=1.0):
    """A window arriving: a low, soft settle of air and a felt body — felt more than heard."""
    dur = 0.45
    t = tvec(dur)
    x = np.sin(2 * np.pi * phase_of(glide(dur, 96, 62, 0.06))) * (1 - np.exp(-t / 0.01)) * np.exp(-t / 0.11) * 0.7
    x += lp(noise(dur, "pink"), 500) * np.exp(-t / 0.03) * 0.15
    return fade(x * vel, 0.002, 0.08)


def brake():
    """A hard stop: a low wooden stop and a sub that lands like a hand on a table. Once or twice a film."""
    rng = np.random.default_rng(7)
    dur = 1.6
    t = tvec(dur)
    sub_ = np.sin(2 * np.pi * phase_of(glide(dur, 62, 38, 0.06))) * np.exp(-t / 0.42)
    exc = rng.standard_normal(len(t)) * np.exp(-t / 0.002)
    wood_ = lp(_resonate(exc, [(110, 3, 1.6), (240, 5, 1.0), (455, 7, 0.5), (830, 8, 0.22)]), 2500)
    return fade(sub_ * 0.9 + wood_ * 0.7, 0.0003, 0.2)


def pre_bloom(dur=0.55):
    """A reversed low bloom that leans into the brake: the tail of the hit, played backwards."""
    tail = brake()[: n_of(dur)]
    tail = lp(tail, 900)
    r = tail[::-1] * np.linspace(0, 1, len(tail)) ** 2
    return fade(r * 0.6, 0.02, 0.002)


def tonal_glide(dur=0.6, f0=420.0, f1=180.0, vel=1.0):
    """The transition sound that replaces a whoosh: a pure, soft pitch glide with an airless envelope."""
    t = tvec(dur)
    env = np.sin(np.pi * np.clip(t / dur, 0, 1)) ** 2
    x = np.sin(2 * np.pi * phase_of(glide(dur, f0, f1, dur * 0.4))) * env * 0.4
    x += np.sin(2 * np.pi * phase_of(glide(dur, f0 * 2.01, f1 * 2.01, dur * 0.4))) * env * 0.08
    return fade(x * vel, 0.003, 0.02)


# ------------------------------------------------------------ sign-offs
def sonic_logo():
    """A sign-off for a logo: a tap (the key that sends), a lower wooden knock answering it, a reversed bloom
    into the last chord, and a sub under the mark. (Chord in E-flat — transpose to the score's key.)"""
    dur = 3.2
    out = np.zeros(n_of(dur))
    _at(out, wood_key(4242, heavy=True) * 0.9, 0.0)
    t = tvec(0.6)
    exc = noise(0.6) * np.exp(-t / 0.0014)
    kn = lp(_resonate(exc, [(196, 6, 1.3), (430, 8, 0.7), (905, 9, 0.3)]), 2600)
    _at(out, fade(kn, 0.0002, 0.05) * 0.9, 0.17)
    # the bloom: an E-flat chord's attack, reversed, arriving on 0.34
    tb = tvec(0.34)
    bloom = np.zeros(len(tb))
    for f in (hz("Eb3"), hz("Bb3"), hz("G4")):
        bloom += np.sin(2 * np.pi * f * tb)
    bloom = fade(lp(bloom, 1200) * (tb / 0.34) ** 3 * 0.18, 0.001, 0.006)
    _at(out, bloom, 0.0)
    ts = tvec(2.8)
    sub_ = np.sin(2 * np.pi * hz("Eb1") * ts) * np.minimum(1, ts / 0.08) * np.exp(-ts / 1.1) * 0.55
    _at(out, sub_, 0.34)
    return fade(out, 0.0002, 0.3)


def lockup_mark():
    """A logo lockup: the key that sends, then a lower wooden knock answering it, and a sub (F1 here; match the key)."""
    dur = 2.6
    out = np.zeros(n_of(dur))
    _at(out, wood_key(4242, heavy=True) * 0.85, 0.0)
    t = tvec(0.6)
    exc = noise(0.6) * np.exp(-t / 0.0014)
    kn = lp(_resonate(exc, [(175, 6, 1.3), (392, 8, 0.7), (870, 9, 0.3)]), 2600)
    _at(out, fade(kn, 0.0002, 0.05) * 0.85, 0.16)
    ts = tvec(2.2)
    sub_ = np.sin(2 * np.pi * 43.65 * ts) * np.minimum(1, ts / 0.06) * np.exp(-ts / 0.9) * 0.45  # F1
    _at(out, sub_, 0.16)
    return fade(out, 0.0002, 0.3)
