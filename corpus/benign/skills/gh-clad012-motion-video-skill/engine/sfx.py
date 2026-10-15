"""Sound effects, all synthesised (nothing to license).

Every effect is a function returning a mono float array at SR. The registry
SFX maps a name to (function, default gain, description); story.json can
place any of them with a scene's "sounds": [{"at": ..., "kind": "<name>"}].
Parameters an effect understands: pitch (1 = normal), dur (seconds),
from/to (Hz, slide), semis (semitones from the key's C4, marimba/bell/pluck).
"""
import numpy as np
from scipy.signal import butter, lfilter, sosfilt

SR = 44100


def t_axis(d):
    return np.arange(int(SR * d)) / SR


def band(sig, lo, hi, order=2):
    return sosfilt(butter(order, [lo, min(hi, SR / 2 - 100)], btype="band", fs=SR, output="sos"), sig)


def lowpass(sig, f, order=2):
    return sosfilt(butter(order, min(f, SR / 2 - 100), btype="low", fs=SR, output="sos"), sig)


def highpass(sig, f, order=2):
    return sosfilt(butter(order, f, btype="high", fs=SR, output="sos"), sig)


def glide(f):
    return 2 * np.pi * np.cumsum(f) / SR


def noise(rng, d):
    return rng.standard_normal(int(SR * d))


def env_ad(t, attack, decay):
    return (1 - np.exp(-t / max(attack, 1e-4))) * np.exp(-t / max(decay, 1e-4))


def note(semis_from_a4):
    return 440.0 * 2 ** (semis_from_a4 / 12)


def mix_at(out, sig, at):
    i = int(SR * at)
    n = min(len(sig), len(out) - i)
    if n > 0:
        out[i : i + n] += sig[:n]
    return out


# ---------------------------------------------------------------- tones
def marimba(f, d=0.6):
    t = t_axis(d)
    return (np.sin(2 * np.pi * f * t) * np.exp(-t * 6) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 22)
            + 0.1 * np.sin(2 * np.pi * f * 9.2 * t) * np.exp(-t * 40)) * (1 - np.exp(-t * 900))


def bell_tone(f, d=1.2):
    t = t_axis(d)
    parts = [(1, 1.0, 2.2), (2.76, 0.5, 4), (5.4, 0.25, 7), (8.93, 0.12, 10)]
    return sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * k) for r, a, k in parts) * (1 - np.exp(-t * 3000)) * 0.6


def pluck_tone(rng, f, d=0.8, damp=0.996):
    """Karplus-Strong string."""
    n = max(2, int(SR / f))
    burst = np.zeros(int(SR * d))
    burst[:n] = rng.uniform(-1, 1, n)
    a = np.zeros(n + 2)
    a[0], a[n], a[n + 1] = 1, -0.5 * damp, -0.5 * damp
    return lfilter([1], a, burst) * 0.8


# ---------------------------------------------------------------- effects
def pop(rng, pitch=1):
    t = t_axis(0.13)
    return np.sin(glide(380 * pitch + 900 * pitch * np.exp(-t * 60))) * np.exp(-t * 38) + 0.25 * highpass(noise(rng, 0.13), 2000) * np.exp(-t * 400)


def click(rng, pitch=1):
    t = t_axis(0.03)
    return (band(noise(rng, 0.03), 2000 * pitch, 6000) * np.exp(-t * 400) + np.sin(2 * np.pi * 1800 * pitch * t) * np.exp(-t * 300) * 0.5) * 1.2


def tap(rng, pitch=1):
    t = t_axis(0.08)
    return np.sin(glide(700 * pitch * (1 + np.exp(-t * 80)))) * np.exp(-t * 60) + 0.2 * band(noise(rng, 0.08), 800, 3000) * np.exp(-t * 200)


def tick(rng, pitch=1):
    t = t_axis(0.05)
    return np.sin(2 * np.pi * 2300 * pitch * t) * np.exp(-t * 110) * 0.8


def blip(rng, pitch=1):
    t = t_axis(0.14)
    return np.sin(glide(500 * pitch + 900 * pitch * t / 0.14)) * np.exp(-t * 22)


def bubble(rng, pitch=1):
    t = t_axis(0.18)
    return np.sin(glide((280 + 700 * (1 - np.exp(-t * 45))) * pitch)) * np.exp(-t * 20) * (1 - np.exp(-t * 800))


def ding(rng, pitch=1):
    out = np.zeros(int(SR * 0.5))
    for k, (f, at) in enumerate([(1320 * pitch, 0.0), (1760 * pitch, 0.07)]):
        t = t_axis(0.4)
        s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 12)) * np.exp(-t * 9) * (1 - np.exp(-t * 2000))
        mix_at(out, s * (0.8 if k else 1), at)
    return out


def tritone(rng, pitch=1):
    out = np.zeros(int(SR * 0.7))
    for k, s in enumerate([0, 4, 7]):
        mix_at(out, bell_tone(note(15 + s) * pitch, 0.5) * 0.8, k * 0.1)
    return out


def chime(rng, pitch=1):
    out = np.zeros(int(SR * 1.4))
    for k, s in enumerate([0, 4, 7, 12]):
        mix_at(out, bell_tone(note(3 + s + 12) * pitch, 1.0), k * 0.07)
    return out * 0.7


def bell(rng, pitch=1):
    return bell_tone(note(3) * pitch, 1.6)


def error(rng, pitch=1):
    out = np.zeros(int(SR * 0.45))
    for k, f in enumerate([330, 247]):
        t = t_axis(0.18)
        s = lowpass(np.sign(np.sin(2 * np.pi * f * pitch * t)), 1800) * env_ad(t, 0.005, 0.09) * 0.5
        mix_at(out, s, k * 0.2)
    return out


def coin(rng, pitch=1):
    t1, t2 = t_axis(0.07), t_axis(0.35)
    a = np.sign(np.sin(2 * np.pi * 988 * pitch * t1)) * 0.35
    b = np.sign(np.sin(2 * np.pi * 1319 * pitch * t2)) * np.exp(-t2 * 9) * 0.35
    return lowpass(np.concatenate([a, b]), 7000)


def cash(rng, pitch=1):
    out = np.zeros(int(SR * 1.1))
    t = t_axis(0.05)
    mix_at(out, band(noise(rng, 0.05), 1500, 6000) * np.exp(-t * 90), 0.0)
    mix_at(out, band(noise(rng, 0.05), 1500, 6000) * np.exp(-t * 90), 0.06)
    mix_at(out, bell_tone(2400 * pitch, 0.9) * 0.9 + bell_tone(3200 * pitch, 0.9) * 0.5, 0.12)
    return out


def whoosh(rng, dur=0.4, pitch=1):
    t = t_axis(dur)
    n = noise(rng, dur)
    centers = [300, 550, 900, 1500, 2400, 3800]
    pos = np.sin(np.pi * t / dur) * (len(centers) - 1)
    out = sum(band(n, c * pitch * 0.7, c * pitch * 1.4) * np.clip(1 - np.abs(pos - k), 0, 1) for k, c in enumerate(centers))
    return out * np.sin(np.pi * t / dur) ** 1.5 * 2.2


def swoosh(rng, pitch=1):
    return whoosh(rng, 0.22, pitch * 1.3) * 1.2


def swipe(rng, pitch=1):
    t = t_axis(0.12)
    return band(noise(rng, 0.12), 2500 * pitch, 9000) * np.sin(np.pi * t / 0.12) ** 2 * 1.5


def whip(rng, pitch=1):
    t = t_axis(0.25)
    sweep = band(noise(rng, 0.25), 1200, 8000) * np.exp(-((t - 0.12) ** 2) / 0.002)
    crack = highpass(noise(rng, 0.25), 3000) * np.exp(-np.abs(t - 0.16) * 200)
    return sweep * 1.4 + crack * 1.6


def rise(rng, dur=1.2, pitch=1):
    t = t_axis(dur)
    f = 200 * pitch * (8 ** (t / dur))
    tone = np.sin(glide(f)) * 0.3 + np.sin(glide(f * 1.5)) * 0.15
    n = band(noise(rng, dur), 600, 6000) * (t / dur) ** 2 * 0.8
    return (tone + n) * (t / dur) ** 1.5 * np.clip((dur - t) / 0.03, 0, 1)


def impact(rng, pitch=1):
    t = t_axis(1.2)
    boom = np.sin(glide(38 * pitch + 90 * pitch * np.exp(-t * 18))) * np.exp(-t * 3.5)
    hit = lowpass(noise(rng, 1.2), 1800) * np.exp(-t * 14) * 0.8
    return (boom + hit) * 1.1


def drop(rng, pitch=1):
    t = t_axis(1.0)
    return np.sin(glide(30 * pitch + 170 * pitch * np.exp(-t * 4))) * env_ad(t, 0.01, 0.45)


def thud(rng, pitch=1):
    t = t_axis(0.3)
    return np.sin(glide((45 + 70 * np.exp(-t * 25)) * pitch)) * np.exp(-t * 14) + band(noise(rng, 0.3), 600, 2500) * np.exp(-t * 70) * 0.7


def slam(rng, pitch=1):
    t = t_axis(0.35)
    return np.sin(glide((55 + 120 * np.exp(-t * 30)) * pitch)) * np.exp(-t * 12) + 0.6 * band(noise(rng, 0.35), 300, 3000) * np.exp(-t * 45)


def boing(rng, pitch=1):
    t = t_axis(0.55)
    f = 180 * pitch * (0.75 + 0.6 * (1 - np.exp(-t * 14))) * (1 + 0.18 * np.sin(2 * np.pi * 16 * t) * np.exp(-t * 4))
    ph = glide(f)
    return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * np.exp(-t * 5.5) * (1 - np.exp(-t * 600))


def spring(rng, pitch=1):
    t = t_axis(0.4)
    f = 420 * pitch * (1 + 0.35 * np.sin(2 * np.pi * 24 * t) * np.exp(-t * 7))
    return np.sin(glide(f)) * np.exp(-t * 8)


def squeak(rng, pitch=1):
    t = t_axis(0.22)
    f = 1400 * pitch * (1 + 0.3 * np.sin(np.pi * t / 0.22)) * (1 + 0.04 * np.sin(2 * np.pi * 35 * t))
    return np.sin(glide(f)) * np.sin(np.pi * t / 0.22) * 0.7


def slide(rng, pitch=1, dur=0.5, **kw):
    f0, f1 = kw.get("from", 400) * pitch, kw.get("to", 1200) * pitch
    t = t_axis(dur)
    f = f0 * (f1 / f0) ** (t / dur) * (1 + 0.02 * np.sin(2 * np.pi * 7 * t))
    return (np.sin(glide(f)) + band(noise(rng, dur), 1500, 4000) * 0.05) * np.sin(np.pi * np.minimum(1, t / dur)) ** 0.6


def zap(rng, pitch=1):
    t = t_axis(0.3)
    f = 2400 * pitch * np.exp(-t * 12) + 120
    return np.sign(np.sin(glide(f))) * np.exp(-t * 9) * 0.4


def glitch(rng, pitch=1):
    out = np.zeros(int(SR * 0.4))
    for k in range(7):
        d = rng.uniform(0.015, 0.05)
        t = t_axis(d)
        kind = k % 3
        s = np.sign(np.sin(2 * np.pi * rng.uniform(200, 2000) * pitch * t)) if kind == 0 else band(noise(rng, d), 500, 8000) if kind == 1 else np.sin(2 * np.pi * rng.uniform(60, 180) * t)
        mix_at(out, s * 0.5, k * 0.05)
    return out


def typing(rng, dur=0.8, pitch=1):
    out = np.zeros(int(SR * dur) + SR // 10)
    at = 0.0
    while at < dur:
        t = t_axis(0.03)
        mix_at(out, band(noise(rng, 0.03), 1800 * pitch, 7000) * np.exp(-t * 300) * rng.uniform(0.5, 1), at)
        at += rng.uniform(0.05, 0.12)
    return out * 1.3


def shutter(rng, pitch=1):
    out = np.zeros(int(SR * 0.25))
    for at in (0.0, 0.07):
        t = t_axis(0.05)
        mix_at(out, band(noise(rng, 0.05), 1500 * pitch, 8000) * np.exp(-t * 120) + np.sin(2 * np.pi * 900 * t) * np.exp(-t * 150) * 0.4, at)
    return out


def scratch(rng, pitch=1):
    t = t_axis(0.45)
    speed = np.sin(2 * np.pi * 3.3 * t)
    f = 300 * pitch + 900 * pitch * np.abs(speed)
    tone = np.sin(glide(f)) * 0.4
    grit = band(noise(rng, 0.45), 400, 3000) * np.abs(speed) * 0.6
    return (tone + grit) * np.sin(np.pi * t / 0.45)


def heartbeat(rng, pitch=1):
    out = np.zeros(int(SR * 0.8))
    for at, g in ((0.0, 1.0), (0.22, 0.7)):
        t = t_axis(0.25)
        mix_at(out, np.sin(glide((50 + 40 * np.exp(-t * 30)) * pitch)) * np.exp(-t * 16) * g, at)
    return out * 1.3


def clock(rng, pitch=1):
    out = np.zeros(int(SR * 1.0))
    for k, f in enumerate([2100, 1600]):
        t = t_axis(0.04)
        mix_at(out, (np.sin(2 * np.pi * f * pitch * t) + band(noise(rng, 0.04), 2000, 7000) * 0.5) * np.exp(-t * 180), k * 0.5)
    return out


def drumroll(rng, dur=1.0, pitch=1):
    out = np.zeros(int(SR * dur) + SR // 5)
    at, k = 0.0, 0
    while at < dur:
        t = t_axis(0.08)
        hit = (band(noise(rng, 0.08), 1500, 6000) + np.sin(2 * np.pi * 190 * pitch * t) * 0.6) * np.exp(-t * 60)
        mix_at(out, hit * (0.4 + 0.6 * at / dur), at)
        at += 0.075 - 0.045 * at / dur
        k += 1
    return out


def crash(rng, pitch=1):
    t = t_axis(2.0)
    return highpass(noise(rng, 2.0), 4000 * pitch) * np.exp(-t * 2.2) * 0.7 + band(noise(rng, 2.0), 3000, 9000) * np.exp(-t * 6) * 0.4


def sparkle(rng, pitch=1):
    out = np.zeros(int(SR * 0.7))
    for k in range(7):
        t = t_axis(0.35)
        mix_at(out, np.sin(2 * np.pi * rng.uniform(2200, 5200) * pitch * t) * np.exp(-t * 14) * 0.35, k * 0.035)
    return out


def magic(rng, pitch=1):
    out = np.zeros(int(SR * 1.6))
    scale = [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24]
    for k, s in enumerate(scale):
        mix_at(out, pluck_tone(rng, note(3 + s) * pitch, 0.9, 0.997) * 0.5, k * 0.045)
    return mix_at(out, sparkle(rng, pitch) * 0.6, 0.4)


def breath(rng, pitch=1):
    t = t_axis(1.4)
    return band(noise(rng, 1.4), 400 * pitch, 2400 * pitch) * np.sin(np.pi * t / 1.4) ** 2 * 0.6


def water(rng, pitch=1):
    t = t_axis(0.2)
    return np.sin(glide(700 * pitch + 900 * pitch * (1 - np.exp(-t * 40)))) * env_ad(t, 0.002, 0.04)


def tada(rng, pitch=1, key=-9):
    out = np.zeros(int(SR * 1.3))
    for s in [0, 4, 7, 12, 16]:
        m = marimba(note(key + 12 + s) * pitch, 1.2) * 0.4
        out[: len(m)] += m
        t = t_axis(1.1)
        out[: len(t)] += lowpass(2 * ((note(key + s) * pitch * t) % 1) - 1, 2200) * np.exp(-t * 3) * (1 - np.exp(-t * 60)) * 0.22
    t = t_axis(1.3)
    return out + highpass(noise(rng, 1.3), 5000) * np.exp(-t * 3.2) * 0.35


def clap(rng, pitch=1):
    t = t_axis(0.25)
    env = sum(np.where(t >= o, np.exp(-(t - o) * 90), 0) for o in (0.0, 0.011, 0.022)) + 0.5 * np.exp(-t * 18)
    return band(noise(rng, 0.25), 900 * pitch, 3200 * pitch) * env * 1.6


# name: (function, default gain, description, extra parameters it takes)
SFX = {
    "pop": (pop, 0.40, "Bubbly pop: things appearing", "pitch"),
    "click": (click, 0.35, "UI click", "pitch"),
    "tap": (tap, 0.35, "Soft tap, a finger on glass", "pitch"),
    "tick": (tick, 0.35, "Tiny tick, letters landing", "pitch"),
    "blip": (blip, 0.35, "Rising blip, a badge or an idea", "pitch"),
    "bubble": (bubble, 0.40, "Speech-bubble bloop", "pitch"),
    "ding": (ding, 0.30, "Phone notification, two tones", "pitch"),
    "tritone": (tritone, 0.35, "Three-note message tone", "pitch"),
    "chime": (chime, 0.40, "Success chime, rising bells", "pitch"),
    "bell": (bell, 0.35, "Single bell strike", "pitch"),
    "error": (error, 0.35, "Soft error buzz", "pitch"),
    "coin": (coin, 0.30, "Game coin", "pitch"),
    "cash": (cash, 0.45, "Cha-ching cash register", "pitch"),
    "whoosh": (whoosh, 0.30, "Air sweep, a transition (dur)", "dur pitch"),
    "swoosh": (swoosh, 0.35, "Short fast whoosh", "pitch"),
    "swipe": (swipe, 0.30, "Very short swipe", "pitch"),
    "whip": (whip, 0.40, "Whip crack, a snappy cut", "pitch"),
    "rise": (rise, 0.35, "Riser before a reveal (dur; place it to end on the hit)", "dur pitch"),
    "impact": (impact, 0.60, "Deep boom hit", "pitch"),
    "drop": (drop, 0.55, "Bass drop", "pitch"),
    "thud": (thud, 0.60, "Card landing", "pitch"),
    "slam": (slam, 0.55, "Sticker slam", "pitch"),
    "boing": (boing, 0.45, "Cartoon spring boing", "pitch"),
    "spring": (spring, 0.40, "Quick twang", "pitch"),
    "squeak": (squeak, 0.35, "Rubber squeak", "pitch"),
    "slide": (slide, 0.20, "Slide whistle (from, to in Hz; dur)", "from to dur"),
    "zap": (zap, 0.30, "Laser zap", "pitch"),
    "glitch": (glitch, 0.40, "Digital glitch stutter", "pitch"),
    "typing": (typing, 0.35, "Keyboard typing burst (dur)", "dur pitch"),
    "shutter": (shutter, 0.45, "Camera shutter", "pitch"),
    "scratch": (scratch, 0.40, "Record scratch, a comic stop", "pitch"),
    "heartbeat": (heartbeat, 0.55, "Heartbeat, suspense", "pitch"),
    "clock": (clock, 0.40, "Tick-tock", "pitch"),
    "drumroll": (drumroll, 0.40, "Snare roll building up (dur)", "dur pitch"),
    "crash": (crash, 0.35, "Cymbal crash", "pitch"),
    "sparkle": (sparkle, 0.45, "Twinkles, confetti", "pitch"),
    "magic": (magic, 0.45, "Harp glissando with sparkles", "pitch"),
    "breath": (breath, 0.35, "Soft exhale, calm", "pitch"),
    "water": (water, 0.40, "Water drop", "pitch"),
    "tada": (tada, 0.70, "Fanfare chord: the big finish", "pitch"),
    "clap": (clap, 0.40, "Hand clap", "pitch"),
    "marimba": (lambda rng, semis=0, key=-9, pitch=1: marimba(note(key + semis) * pitch, 0.5), 0.30, "Marimba note (semis from the key's middle C)", "semis"),
    "pluck": (lambda rng, semis=0, key=-9, pitch=1: pluck_tone(rng, note(key + semis) * pitch, 0.8), 0.35, "Plucked string note (semis)", "semis"),
}


def render(name, rng, key=-9, **params):
    """One effect by name, with only the parameters it understands."""
    fn, _, _, accepts = SFX[name]
    allowed = set(accepts.split()) | {"pitch"}
    kw = {k: v for k, v in params.items() if k in allowed and v is not None}
    if name in ("marimba", "pluck", "tada"):
        kw["key"] = key
    return np.asarray(fn(rng, **kw), dtype=np.float64)
