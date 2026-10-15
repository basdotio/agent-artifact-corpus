"""
The sound engine — everything synthesized from first principles (no samples, no stock).

No samples anywhere: band-limited oscillators (polyBLEP), a zero-delay-feedback
state-variable filter, FM operators, modal (physical) resonators, Karplus-Strong,
and reverbs convolved from impulse responses we synthesize ourselves.
All buffers are float64 at 48 kHz; stereo is shape (2, n).
"""
import numpy as np
from numba import njit

SR = 48000
RNG = np.random.default_rng(20260929)


# ----------------------------------------------------------------- basics
def secs(n):
    return n / SR


def n_of(sec):
    return int(round(sec * SR))


def tvec(dur):
    return np.arange(n_of(dur)) / SR


def db(x):
    return 10 ** (x / 20.0)


def midi(m):
    return 440.0 * 2 ** ((m - 69) / 12.0)


NOTE = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6,
        "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11}


def n2m(name):
    """'F#4' -> midi number."""
    i = 2 if len(name) > 2 and name[1] in "#b" else 1
    return NOTE[name[:i]] + 12 * (int(name[i:]) + 1)


def hz(name):
    return midi(n2m(name))


def pan(mono, p=0.0):
    """Equal-power pan, p in [-1, 1]."""
    a = (p + 1) * np.pi / 4
    return np.stack([mono * np.cos(a), mono * np.sin(a)])


def stereo(x):
    return x if x.ndim == 2 else np.stack([x, x])


def fade(x, fin=0.002, fout=0.005):
    """Click-proof edges."""
    x = x.copy()
    a, b = n_of(fin), n_of(fout)
    n = x.shape[-1]
    if a > 0:
        x[..., :a] *= np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if b > 0 and b < n:
        x[..., n - b:] *= np.cos(np.linspace(0, np.pi / 2, b)) ** 2
    return x


# ----------------------------------------------------------------- envelopes
def env_exp(dur, decay, attack=0.002, curve=1.0):
    """Instant-ish attack, exponential decay (decay = time to -60 dB)."""
    t = tvec(dur)
    a = np.clip(t / max(attack, 1e-5), 0, 1) ** 0.5
    d = np.exp(-6.9078 * (t / decay) ** curve)
    return a * d


def env_adsr(dur, a=0.01, d=0.1, s=0.7, r=0.2, gate=None):
    gate = dur - r if gate is None else gate
    t = tvec(dur)

    def pre(x):
        """The attack/decay/sustain curve (before release), analytically."""
        x = np.asarray(x, dtype=np.float64)
        out = np.full_like(x, s)
        m1 = x < a
        out[m1] = (x[m1] / a) if a > 0 else 1.0
        m2 = (x >= a) & (x < a + d)
        out[m2] = 1 - (1 - s) * ((x[m2] - a) / d)
        return out

    e = pre(t)
    # Release starts from wherever the envelope actually is at the gate.
    lvl_at_gate = float(pre(np.array([gate]))[0])
    m4 = t >= gate
    e[m4] = lvl_at_gate * np.exp(-6.9 * (t[m4] - gate) / max(r, 1e-4))
    return e


def ramp(dur, points):
    """Piecewise-linear curve from [(time, value), ...]."""
    t = tvec(dur)
    ts, vs = zip(*points)
    return np.interp(t, ts, vs)


def glide(dur, f0, f1, tau):
    """Exponential frequency glide f0 -> f1 with time constant tau."""
    t = tvec(dur)
    return f1 + (f0 - f1) * np.exp(-t / tau)


# ----------------------------------------------------------------- oscillators
def phase_of(freq):
    """Freq array (Hz) -> phase in cycles."""
    return np.cumsum(freq) / SR


def sine(freq, dur=None, phase0=0.0):
    if np.isscalar(freq):
        freq = np.full(n_of(dur), float(freq))
    return np.sin(2 * np.pi * (phase_of(freq) + phase0))


@njit(cache=True)
def _polyblep(t, dt):
    if t < dt:
        t /= dt
        return t + t - t * t - 1.0
    elif t > 1.0 - dt:
        t = (t - 1.0) / dt
        return t * t + t + t + 1.0
    return 0.0


@njit(cache=True)
def _saw(freq, phase0):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / 48000.0
        out[i] = 2.0 * ph - 1.0 - _polyblep(ph, dt)
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


@njit(cache=True)
def _square(freq, phase0, pw):
    n = freq.shape[0]
    out = np.empty(n)
    ph = phase0
    for i in range(n):
        dt = freq[i] / 48000.0
        v = 1.0 if ph < pw else -1.0
        v += _polyblep(ph, dt)
        p2 = ph + (1.0 - pw)
        if p2 >= 1.0:
            p2 -= 1.0
        v -= _polyblep(p2, dt)
        out[i] = v
        ph += dt
        if ph >= 1.0:
            ph -= 1.0
    return out


def saw(freq, dur=None, phase0=None):
    if np.isscalar(freq):
        freq = np.full(n_of(dur), float(freq))
    return _saw(np.asarray(freq, dtype=np.float64), RNG.random() if phase0 is None else phase0)


def square(freq, dur=None, pw=0.5, phase0=None):
    if np.isscalar(freq):
        freq = np.full(n_of(dur), float(freq))
    return _square(np.asarray(freq, dtype=np.float64), RNG.random() if phase0 is None else phase0, pw)


def tri(freq, dur=None):
    # integrate a band-limited square (leaky) for a soft triangle
    sq = square(freq, dur)
    f = np.full(sq.shape, float(freq)) if np.isscalar(freq) else freq
    y = np.cumsum(sq * 4 * f / SR)
    y -= _onepole_hp(y, 5.0)
    return y / max(1e-9, np.max(np.abs(y)))


def supersaw(freq, dur, voices=7, detune_cents=14.0, spread=0.8):
    """Detuned saw stack, stereo."""
    n = n_of(dur)
    L = np.zeros(n)
    R = np.zeros(n)
    for v in range(voices):
        c = (v / (voices - 1) - 0.5) * 2 * detune_cents if voices > 1 else 0
        f = freq * 2 ** (c / 1200)
        s = saw(f, dur)
        p = (v / (voices - 1) - 0.5) * 2 * spread if voices > 1 else 0
        a = (p + 1) * np.pi / 4
        L += s * np.cos(a)
        R += s * np.sin(a)
    return np.stack([L, R]) / np.sqrt(voices)


def noise(dur, color="white"):
    n = n_of(dur)
    w = RNG.standard_normal(n)
    if color == "white":
        return w
    if color == "pink":
        # Paul Kellet's refined pink filter
        b = np.zeros(7)
        out = _pink(w)
        return out / np.std(out)
    raise ValueError(color)


@njit(cache=True)
def _pink(w):
    n = w.shape[0]
    out = np.empty(n)
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    for i in range(n):
        x = w[i]
        b0 = 0.99886 * b0 + x * 0.0555179
        b1 = 0.99332 * b1 + x * 0.0750759
        b2 = 0.96900 * b2 + x * 0.1538520
        b3 = 0.86650 * b3 + x * 0.3104856
        b4 = 0.55000 * b4 + x * 0.5329522
        b5 = -0.7616 * b5 - x * 0.0168980
        out[i] = b0 + b1 + b2 + b3 + b4 + b5 + b6 + x * 0.5362
        b6 = x * 0.115926
    return out


# ----------------------------------------------------------------- filters
@njit(cache=True)
def _svf(x, fc, q, mode):
    """Zavalishin TPT state-variable filter with per-sample cutoff. mode 0 LP, 1 BP, 2 HP."""
    n = x.shape[0]
    y = np.empty(n)
    ic1 = 0.0
    ic2 = 0.0
    k = 1.0 / q
    for i in range(n):
        f = fc[i]
        if f > 23000.0:
            f = 23000.0
        if f < 10.0:
            f = 10.0
        g = np.tan(np.pi * f / 48000.0)
        a1 = 1.0 / (1.0 + g * (g + k))
        a2 = g * a1
        a3 = g * a2
        v3 = x[i] - ic2
        v1 = a1 * ic1 + a2 * v3
        v2 = ic2 + a2 * ic1 + a3 * v3
        ic1 = 2.0 * v1 - ic1
        ic2 = 2.0 * v2 - ic2
        if mode == 0:
            y[i] = v2
        elif mode == 1:
            y[i] = v1
        else:
            y[i] = x[i] - k * v1 - v2
    return y


def _fc(fc, n):
    return np.full(n, float(fc)) if np.isscalar(fc) else np.asarray(fc, dtype=np.float64)


def lp(x, fc, q=0.707):
    if x.ndim == 2:
        return np.stack([lp(x[0], fc, q), lp(x[1], fc, q)])
    return _svf(x, _fc(fc, len(x)), q, 0)


def bp(x, fc, q=1.0):
    if x.ndim == 2:
        return np.stack([bp(x[0], fc, q), bp(x[1], fc, q)])
    return _svf(x, _fc(fc, len(x)), q, 1)


def hp(x, fc, q=0.707):
    if x.ndim == 2:
        return np.stack([hp(x[0], fc, q), hp(x[1], fc, q)])
    return _svf(x, _fc(fc, len(x)), q, 2)


@njit(cache=True)
def _onepole_hp(x, fc):
    a = np.exp(-2 * np.pi * fc / 48000.0)
    y = np.empty_like(x)
    xm = 0.0
    ym = 0.0
    for i in range(x.shape[0]):
        ym = a * (ym + x[i] - xm)
        xm = x[i]
        y[i] = ym
    return y


def dc_block(x, fc=18.0):
    if x.ndim == 2:
        return np.stack([_onepole_hp(x[0], fc), _onepole_hp(x[1], fc)])
    return _onepole_hp(x, fc)


def peq(x, f0, gain_db, q=1.0):
    """RBJ peaking EQ (static)."""
    from scipy.signal import lfilter
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / (2 * q)
    b = np.array([1 + al * A, -2 * np.cos(w), 1 - al * A])
    a = np.array([1 + al / A, -2 * np.cos(w), 1 - al / A])
    return lfilter(b / a[0], a / a[0], x, axis=-1)


def shelf(x, f0, gain_db, kind="high", s=0.9):
    from scipy.signal import lfilter
    A = 10 ** (gain_db / 40)
    w = 2 * np.pi * f0 / SR
    al = np.sin(w) / 2 * np.sqrt((A + 1 / A) * (1 / s - 1) + 2)
    c = np.cos(w)
    if kind == "high":
        b = [A * ((A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
             A * ((A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
             (A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al]
    else:
        b = [A * ((A + 1) - (A - 1) * c + 2 * np.sqrt(A) * al), 2 * A * ((A - 1) - (A + 1) * c),
             A * ((A + 1) - (A - 1) * c - 2 * np.sqrt(A) * al)]
        a = [(A + 1) + (A - 1) * c + 2 * np.sqrt(A) * al, -2 * ((A - 1) + (A + 1) * c),
             (A + 1) + (A - 1) * c - 2 * np.sqrt(A) * al]
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return lfilter(b, a, x, axis=-1)


# ----------------------------------------------------------------- physical-ish voices
def modal(freqs, decays, amps, dur, attack=0.0008, phases=None):
    """Bank of exponentially decaying sinusoids — mallets, glass, wood, metal."""
    t = tvec(dur)
    out = np.zeros_like(t)
    for i, (f, d, a) in enumerate(zip(freqs, decays, amps)):
        if f >= SR / 2 * 0.92:
            continue
        ph = 0 if phases is None else phases[i]
        out += a * np.sin(2 * np.pi * f * t + ph) * np.exp(-6.9078 * t / d)
    att = np.clip(t / attack, 0, 1) ** 0.5 if attack > 0 else 1
    return out * att


def fm(fc, ratio, index, dur, fb=0.0):
    """2-op FM; fc/index may be arrays (index in radians)."""
    n = n_of(dur)
    fcv = _fc(fc, n)
    idx = _fc(index, n)
    pm = phase_of(fcv * ratio)
    mod = np.sin(2 * np.pi * pm)
    pc = phase_of(fcv)
    return np.sin(2 * np.pi * pc + idx * mod)


@njit(cache=True)
def _ks(n, period, decay, bright, seed_noise):
    buf = seed_noise.copy()
    L = buf.shape[0]
    out = np.empty(n)
    idx = 0
    last = 0.0
    for i in range(n):
        v = buf[idx]
        out[i] = v
        nxt = buf[(idx + 1) % L]
        avg = bright * v + (1 - bright) * 0.5 * (v + nxt)
        buf[idx] = avg * decay
        idx = (idx + 1) % L
    return out


def pluck(freq, dur, decay=0.996, bright=0.35):
    """Karplus-Strong string."""
    period = SR / freq
    L = int(round(period))
    seed = lp(RNG.uniform(-1, 1, L), 6000)
    return _ks(n_of(dur), period, decay, bright, seed)


# ----------------------------------------------------------------- time effects
@njit(cache=True)
def _fbdelay(x, d, fb, damp):
    n = x.shape[0]
    y = np.zeros(n)
    buf = np.zeros(d + 1)
    w = 0
    lpst = 0.0
    for i in range(n):
        r = (w - d) % (d + 1)
        dl = buf[r]
        lpst = lpst + damp * (dl - lpst)
        buf[w] = x[i] + lpst * fb
        y[i] = dl
        w = (w + 1) % (d + 1)
    return y


def delay(x, time_s, fb=0.35, damp=0.35, mix=0.3, pingpong=True):
    x = stereo(x)
    d = n_of(time_s)
    if pingpong:
        mono = 0.5 * (x[0] + x[1])
        a = _fbdelay(mono, d, fb, damp)
        b = _fbdelay(np.concatenate([np.zeros(d), a])[: len(a)], d, fb, damp)
        wet = np.stack([a, b]) * 0.8
    else:
        wet = np.stack([_fbdelay(x[0], d, fb, damp), _fbdelay(x[1], d, fb, damp)])
    return x + mix * wet


def make_ir(length=2.8, predelay=0.018, lowcut=180.0, hicut=9000.0, rt_low=2.6, rt_high=1.1, er=True, seed=7):
    """A lush stereo impulse response, synthesized: band-wise exponential decays
    over decorrelated noise, with early reflections. Returns (2, n)."""
    rng = np.random.default_rng(seed)
    n = n_of(length)
    t = np.arange(n) / SR
    chans = []
    for c in range(2):
        w = rng.standard_normal(n)
        lo = lp(w, 700.0)
        mid = bp(w, 2400.0, 0.7)
        hi = hp(w, 5000.0)
        rtm = 0.5 * (rt_low + rt_high)
        tail = (lo * np.exp(-6.9 * t / rt_low) + mid * np.exp(-6.9 * t / rtm) + hi * np.exp(-6.9 * t / rt_high))
        tail *= np.clip(t / 0.06, 0, 1) ** 1.5  # soft build
        if er:
            for k in range(14):
                tk = predelay + rng.uniform(0.003, 0.075)
                i = n_of(tk)
                if i < n:
                    tail[i] += rng.choice([-1, 1]) * rng.uniform(0.3, 1.0) * np.exp(-tk * 18)
        pd = n_of(predelay)
        tail = np.concatenate([np.zeros(pd), tail])[:n]
        chans.append(tail)
    ir = np.stack(chans)
    ir = hp(ir, lowcut)
    ir = lp(ir, hicut)
    return ir / np.sqrt(np.sum(ir ** 2) / 2)


_IR_CACHE = {}


def reverb(x, ir_name="hall", mix=0.25):
    from scipy.signal import fftconvolve
    if ir_name not in _IR_CACHE:
        presets = {
            "hall": dict(length=3.2, rt_low=2.8, rt_high=1.3, predelay=0.024),
            "room": dict(length=1.2, rt_low=0.8, rt_high=0.45, predelay=0.008),
            "plate": dict(length=2.2, rt_low=1.6, rt_high=1.4, predelay=0.004, lowcut=300, hicut=11000),
            "air": dict(length=5.0, rt_low=4.2, rt_high=2.2, predelay=0.04, lowcut=250),
        }
        _IR_CACHE[ir_name] = make_ir(**presets[ir_name])
    ir = _IR_CACHE[ir_name]
    x = stereo(x)
    wet = np.stack([fftconvolve(x[0], ir[0])[: x.shape[1]], fftconvolve(x[1], ir[1])[: x.shape[1]]])
    return x * (1 - mix) + wet * mix


def wet_only(x, ir_name="hall", pad=3.0):
    """Return just the reverb tail (x padded so tails are kept)."""
    from scipy.signal import fftconvolve
    x = stereo(x)
    x = np.concatenate([x, np.zeros((2, n_of(pad)))], axis=1)
    reverb(np.zeros((2, 10)), ir_name, 0)  # warm cache
    ir = _IR_CACHE[ir_name]
    return np.stack([fftconvolve(x[0], ir[0])[: x.shape[1]], fftconvolve(x[1], ir[1])[: x.shape[1]]])


@njit(cache=True)
def _chorus_ch(x, base, depth, rate, phase):
    n = x.shape[0]
    y = np.empty(n)
    for i in range(n):
        d = base + depth * (0.5 + 0.5 * np.sin(2 * np.pi * rate * i / 48000.0 + phase))
        j = i - d
        j0 = int(np.floor(j))
        fr = j - j0
        a = x[j0] if 0 <= j0 < n else 0.0
        b = x[j0 + 1] if 0 <= j0 + 1 < n else 0.0
        y[i] = a + (b - a) * fr
    return y


def chorus(x, depth_ms=3.0, base_ms=9.0, rate=0.35, mix=0.5):
    x = stereo(x)
    L = _chorus_ch(x[0], base_ms * 48, depth_ms * 48, rate, 0.0)
    R = _chorus_ch(x[1], base_ms * 48, depth_ms * 48, rate * 1.07, 1.7)
    return x * (1 - mix) + np.stack([L, R]) * mix


def saturate(x, drive=1.5):
    return np.tanh(x * drive) / np.tanh(drive)


# ----------------------------------------------------------------- mixing canvas
class Canvas:
    """A stereo timeline. add() places a sound at a time with gain and pan."""

    def __init__(self, dur):
        self.buf = np.zeros((2, n_of(dur)))

    def add(self, t, x, gain_db=0.0, p=None):
        x = stereo(x) if p is None else pan(x if x.ndim == 1 else 0.5 * (x[0] + x[1]), p)
        i = n_of(t)
        if i < 0:
            x = x[:, -i:]
            i = 0
        j = min(self.buf.shape[1], i + x.shape[1])
        if j > i:
            self.buf[:, i:j] += x[:, : j - i] * db(gain_db)
        return self

    def mix_in(self, other, gain_db=0.0):
        self.buf += other.buf * db(gain_db)
        return self


def tp_limit(x, ceiling_db=-1.3, lookahead_ms=1.5, release_ms=90.0, iters=3):
    """Lookahead true-peak limiter: gain from the 4x-oversampled peak envelope, a smoothed
    lookahead attack and an exponential release. x: (2, n)."""
    from scipy.signal import resample_poly
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    y = x.copy()
    ceil = 10 ** (ceiling_db / 20)
    L = max(1, int(lookahead_ms * 1e-3 * SR))
    a_rel = np.exp(-1.0 / (release_ms * 1e-3 * SR))
    for _ in range(iters):
        up = resample_poly(y, 4, 1, axis=1)
        pk = np.abs(up).max(axis=0)
        n = y.shape[1]
        pk = pk[: n * 4].reshape(n, 4).max(axis=1)
        req = np.minimum(1.0, ceil / np.maximum(pk, 1e-12))
        if req.min() >= 0.9999:
            break
        look = minimum_filter1d(req, size=2 * L + 1, origin=0, mode="nearest")
        look = np.minimum(look, np.concatenate([req[L:], np.full(L, 1.0)]))
        sm = uniform_filter1d(look, size=L, mode="nearest")
        g = np.minimum(sm, look)
        g = _release(g, a_rel)
        y = y * g
    return y


@njit(cache=True)
def _release(g, a):
    out = np.empty_like(g)
    cur = 1.0
    for i in range(g.shape[0]):
        v = g[i]
        if v < cur:
            cur = v
        else:
            cur = a * cur + (1 - a) * v
        out[i] = cur
    return out
