"""Background music, synthesised to fit the video's scenes.

A style (story.json music.style) sets the instruments, drum pattern and feel;
each scene's mood sets what plays in it:

  tension  a clock ticking faster over a rising drone: problems piling up
  calm     a held chord and a gentle arpeggio: relief, a reveal
  groove   drums, bass, chords and the lead, one chord per scene
  run      the groove without the lead (the scene plays its own notes)
  outro    a warm held chord and a last flourish under the ending
  none     silence

Styles: playful (default), lofi, upbeat, cinematic, chiptune, tropical,
corporate, ambient. Tempo and key come from story.json (music.bpm, music.key);
each style has a suggested tempo, used when bpm is not set.
"""
import numpy as np
from scipy.signal import butter, sosfilt

from sfx import SR, band, bell_tone, clap, glide, highpass, lowpass, marimba, note, pluck_tone, t_axis

STYLE_BPM = {"playful": 100, "lofi": 80, "upbeat": 118, "cinematic": 90, "chiptune": 128, "tropical": 102, "corporate": 110, "ambient": 72}


# ---------------------------------------------------------------- instruments
def epiano(f, d=1.2):
    t = t_axis(d)
    idx = 1.8 * np.exp(-t * 5)
    s = np.sin(2 * np.pi * f * t + idx * np.sin(2 * np.pi * f * t)) * np.exp(-t * 2.2)
    tine = np.sin(2 * np.pi * f * 7.1 * t) * np.exp(-t * 18) * 0.12
    return (s + tine) * (1 - np.exp(-t * 800)) * 0.7


def piano(f, d=1.4):
    t = t_axis(d)
    s = sum((1 / n ** 1.4) * np.sin(2 * np.pi * f * n * (1 + 0.0004 * n * n) * t) * np.exp(-t * (1.6 + n * 0.9)) for n in range(1, 7))
    return s * (1 - np.exp(-t * 1500)) * 0.6


def square(f, d=0.2, duty=0.5):
    t = t_axis(d)
    s = np.where(((f * t) % 1) < duty, 1.0, -1.0)
    return lowpass(s, 6000) * np.exp(-t * 4) * np.clip((d - t) / 0.01, 0, 1) * 0.35


def steel(f, d=0.8):
    t = t_axis(d)
    bend = 1 + 0.01 * np.exp(-t * 30)
    parts = [(1, 1.0, 4), (2.0, 0.45, 6), (3.0, 0.2, 9), (4.2, 0.18, 12)]
    return sum(a * np.sin(glide(f * r * bend * np.ones_like(t))) * np.exp(-t * k) for r, a, k in parts) * (1 - np.exp(-t * 2000)) * 0.55


def strings(freqs, d, attack=0.5, release=0.6, rng=None):
    t = t_axis(d)
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.08, 0.0, 0.08):
            ff = f * 2 ** (det / 12)
            s += 2 * ((ff * t + (rng.random() if rng is not None else 0)) % 1) - 1
    vib = 1 + 0.003 * np.sin(2 * np.pi * 5 * t)
    s = lowpass(s * vib / (len(freqs) * 3), 1600)
    return s * np.minimum(1, t / attack) * np.clip((d - t) / release, 0, 1)


def pad(freqs, d, attack=0.4, release=0.3, rng=None, bright=1400):
    t = t_axis(d)
    s = np.zeros_like(t)
    for f in freqs:
        for det in (-0.12, 0.12):
            s += 2 * ((f * 2 ** (det / 12) * t + (rng.random() if rng is not None else 0)) % 1) - 1
    return lowpass(s / (len(freqs) * 2), bright) * np.minimum(1, t / attack) * np.clip((d - t) / release, 0, 1)


def sub_bass(f, d=0.5):
    t = t_axis(d)
    return (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 2.5) * (1 - np.exp(-t * 300)) * np.clip((d - t) / 0.02, 0, 1)


def saw_bass(f, d=0.28):
    t = t_axis(d)
    saw, sq = 2 * ((f * t) % 1) - 1, np.sign(np.sin(2 * np.pi * f * t))
    return lowpass(0.6 * saw + 0.4 * sq, 700) * np.exp(-t * 7) * (1 - np.exp(-t * 400))


# drums
def kick(kind, rng):
    if kind == "808":
        t = t_axis(0.7)
        return np.sin(glide(42 + 90 * np.exp(-t * 25))) * np.exp(-t * 3.5) * 1.1
    if kind == "soft":
        t = t_axis(0.3)
        return np.sin(glide(55 + 60 * np.exp(-t * 30))) * np.exp(-t * 11) * 0.8
    if kind == "chip":
        t = t_axis(0.12)
        return np.sign(np.sin(glide(160 * np.exp(-t * 25) + 40))) * np.exp(-t * 25) * 0.45
    if kind == "taiko":
        t = t_axis(0.8)
        return (np.sin(glide(70 + 40 * np.exp(-t * 20))) * np.exp(-t * 5) + lowpass(rng.standard_normal(len(t)), 900) * np.exp(-t * 25) * 0.5) * 1.1
    t = t_axis(0.4)
    return np.sin(glide(48 + 110 * np.exp(-t * 32))) * np.exp(-t * 9) + 0.3 * rng.standard_normal(len(t)) * np.exp(-t * 300)


def snare(kind, rng):
    if kind == "clap":
        return clap(rng)
    t = t_axis(0.25)
    if kind == "rim":
        t = t_axis(0.06)
        return (np.sin(2 * np.pi * 1700 * t) + band(rng.standard_normal(len(t)), 2000, 6000)) * np.exp(-t * 90) * 0.6
    if kind == "chip":
        t = t_axis(0.12)
        return rng.uniform(-1, 1, len(t)) * np.exp(-t * 30) * 0.5
    body = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25) * 0.6
    wires = band(rng.standard_normal(len(t)), 1800, 8000) * np.exp(-t * 18)
    s = body + wires
    return lowpass(s, 3500) * 0.9 if kind == "lofi" else s


def hat(kind, rng, open_=False):
    d = 0.2 if open_ else 0.06
    t = t_axis(d)
    if kind == "shaker":
        return band(rng.standard_normal(len(t)), 5000, 11000) * np.sin(np.pi * np.minimum(1, t / d)) ** 2 * 0.8
    if kind == "chip":
        return rng.uniform(-1, 1, len(t)) * np.exp(-t * (30 if open_ else 120)) * 0.3
    return highpass(rng.standard_normal(len(t)), 7000) * np.exp(-t * (18 if open_ else 70))


def crackle(rng, d):
    n = int(SR * d)
    s = np.zeros(n)
    pops = rng.integers(0, n, int(d * 25))
    s[pops] = rng.uniform(-1, 1, len(pops))
    return lowpass(s, 5000) * 0.6 + lowpass(rng.standard_normal(n), 1200) * 0.015


# ---------------------------------------------------------------- styles
# Patterns: 16 steps per 4 beats. K kick, S snare, H hat, O open hat.
STYLES = {
    "playful": dict(kick="punch", snare="clap", hat="hat", K="x...x...x...x...", S="....x.......x...", H="..x...x...x...x.", O="", bass="octaves", lead="marimba", chords=None, swing=0.0, arp="riff"),
    "lofi": dict(kick="soft", snare="lofi", hat="hat", K="x.....x...x.....", S="....x.......x...", H="x.x.x.x.x.x.x.x.", O="", bass="sub", lead="epiano", chords="epiano7", swing=0.12, arp="sparse", crackle=True, darken=3500),
    "upbeat": dict(kick="punch", snare="clap", hat="hat", K="x...x...x...x...", S="....x.......x...", H="x.x.x.x.x.x.x.x.", O="..x...x...x...x.", bass="offbeat", lead="pluck", chords="stabs", swing=0.0, arp="sixteenths", pump=True),
    "cinematic": dict(kick="taiko", snare="rim", hat="shaker", K="x.....x.x.......", S="............x...", H="", O="", bass="sub_long", lead="bell", chords="strings", swing=0.0, arp="sparse"),
    "chiptune": dict(kick="chip", snare="chip", hat="chip", K="x.......x.x.....", S="....x.......x...", H="x.x.x.x.x.x.x.x.", O="", bass="square", lead="square", chords=None, swing=0.0, arp="sixteenths"),
    "tropical": dict(kick="punch", snare="rim", hat="shaker", K="x...x...x...x...", S="...x..x....x..x.", H="xxxxxxxxxxxxxxxx", O="", bass="octaves", lead="steel", chords=None, swing=0.05, arp="riff"),
    "corporate": dict(kick="soft", snare="clap", hat="shaker", K="x...x...x...x...", S="....x.......x...", H="x.x.x.x.x.x.x.x.", O="", bass="octaves", lead="pluck", chords="piano8", swing=0.0, arp="riff"),
    "ambient": dict(kick=None, snare=None, hat=None, K="", S="", H="", O="", bass="sub_long", lead="bell", chords="pad", swing=0.0, arp="sparse"),
}
RIFF = [0, None, 2, 1, None, 2, 3, 2]


def chord_tones(name, key_shift):
    roots = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    root = roots[name[0]] + (1 if name[1:2] == "#" else -1 if name[1:2] == "b" else 0)
    minor = name[1:].lstrip("#b").startswith("m") and not name[1:].lstrip("#b").startswith("maj")
    base = -9 + key_shift + root - (12 if root > 6 else 0)
    tones = [base, base + (3 if minor else 4), base + 7]
    seventh = base + (10 if minor else 11)
    return tones, seventh


class Music:
    def __init__(self, meta, rng):
        self.meta = meta
        self.rng = rng
        m = meta["music"]
        self.style_name = m.get("style", "playful") if m.get("style") in STYLES else "playful"
        self.style = STYLES[self.style_name]
        self.beat = meta["beat"]
        keys = {"C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3, "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8, "Ab": 8, "A": -3, "A#": -2, "Bb": -2, "B": -1}
        self.shift = keys.get(m.get("key", "C"), 0)
        self.progression = m.get("progression") or ["C", "Am", "F", "G"]
        self.n = int(SR * meta["duration"]) + 1
        self.buf = np.zeros((self.n, 2))

    # -------------------------------------------------------------- placing
    def place(self, sig, at, gain=1.0, pan=0.0):
        i = int(round(at * SR))
        if i >= self.n or len(sig) == 0:
            return
        if i < 0:
            sig, i = sig[-i:], 0
        sig = sig[: self.n - i]
        self.buf[i : i + len(sig), 0] += sig * gain * np.cos((pan + 1) * np.pi / 4)
        self.buf[i : i + len(sig), 1] += sig * gain * np.sin((pan + 1) * np.pi / 4)

    def lead(self, f, d=0.5):
        kind = self.style["lead"]
        if kind == "epiano":
            return epiano(f, max(d, 0.9))
        if kind == "pluck":
            return pluck_tone(self.rng, f, max(d, 0.6))
        if kind == "bell":
            return bell_tone(f, 1.4)
        if kind == "square":
            return square(f, min(d, 0.18), 0.25)
        if kind == "steel":
            return steel(f)
        return marimba(f)

    # -------------------------------------------------------------- moods
    def tension(self, start, length):
        at, gap = start + 0.1, 0.32
        while at < start + length - 0.6:
            t = t_axis(0.03)
            tick = highpass(self.rng.standard_normal(len(t)), 7000) * np.exp(-t * 120)
            self.place(tick, at, 0.35 + 0.4 * (at - start) / length, pan=0.5 * (-1) ** int(at / gap))
            gap = max(0.09, gap * 0.93)
            at += gap
        tones, _ = chord_tones(self.progression[0], self.shift)
        t = t_axis(length)
        f = note(tones[0] - 24) * (1 + 0.06 * t / length)
        saw = lambda ff: 2 * ((np.cumsum(ff) / SR) % 1) - 1  # noqa: E731
        drone = lowpass(saw(f) + 0.5 * saw(f * 1.5), 500)
        drone *= np.minimum(1, t / 0.6) * (0.3 + 0.7 * t / length) * np.clip((length - 0.55 - t) / 0.05, 0, 1)
        self.place(drone, start, 0.35)
        if self.style_name == "cinematic":
            self.place(kick("taiko", self.rng), start + length - 0.6 - self.beat, 0.5)

    def calm(self, start, length, next_mood):
        tones, seventh = chord_tones(self.progression[0], self.shift)
        freqs = [note(tones[0] - 12)] + [note(x) for x in tones] + [note(seventh)]
        if self.style_name == "cinematic":
            self.place(strings(freqs, length + 0.4, 0.8, 0.6, self.rng), start, 0.3)
        else:
            self.place(pad(freqs, length + 0.3, 1.2, 0.4, self.rng), start, 0.22)
        arp, k, at = [0, 4, 7, 12, 16, 12, 7, 4], 0, start + min(1.0, length * 0.3)
        while at < start + length - 0.05:
            self.place(self.lead(note(tones[0] + 12 + arp[k % 8]), 0.5), at, 0.18, pan=0.3 * np.sin(k))
            at += self.beat / (2 if self.style_name not in ("ambient", "cinematic") else 1)
            k += 1
        if next_mood in ("groove", "run") and self.style["snare"]:
            for j, off in enumerate([2 * self.beat, self.beat, self.beat / 2, self.beat / 4]):
                self.place(snare(self.style["snare"], self.rng), start + length - off, 0.2 + 0.1 * j)

    def groove(self, start, length, index, with_lead):
        st = self.style
        tones, seventh = chord_tones(self.progression[index % len(self.progression)], self.shift)
        root = tones[0]
        steps = max(1, round(length / (self.beat / 4)))
        step = self.beat / 4
        drums = [(st["K"], lambda: kick(st["kick"], self.rng), 0.8, 0.0), (st["S"], lambda: snare(st["snare"], self.rng), 0.45, 0.0),
                 (st["H"], lambda: hat(st["hat"], self.rng), 0.18, 0.35), (st["O"], lambda: hat(st["hat"], self.rng, True), 0.14, -0.3)]
        for s in range(steps):
            at = start + s * step + (st["swing"] * step * 2 if s % 2 == 1 else 0)
            for pattern, make, gain, pan in drums:
                if pattern and pattern[s % 16] == "x":
                    self.place(make(), at, gain, pan)
        # bass
        for s in range(0, steps, 2):
            at = start + s * step
            kind = st["bass"]
            if kind == "octaves":
                self.place(saw_bass(note(root - 12 + (12 if (s // 2) % 2 else 0))), at, 0.5)
            elif kind == "offbeat" and (s // 2) % 2 == 1:
                self.place(saw_bass(note(root - 12), 0.25), at, 0.55)
            elif kind == "square":
                self.place(square(note(root - 12 + (12 if (s // 2) % 2 else 0)), 0.12, 0.5), at, 0.6)
            elif kind == "sub" and s % 8 == 0:
                self.place(sub_bass(note(root - 12), self.beat * 1.8), at, 0.6)
            elif kind == "sub_long" and s % 16 == 0:
                self.place(sub_bass(note(root - 12), self.beat * 3.8), at, 0.55)
        # chords
        voicing = [note(x) for x in tones] + [note(seventh)]
        kind = st["chords"]
        if kind == "epiano7":
            for s in range(0, steps, 16):
                for off in (0, 6):
                    if s + off < steps:
                        for f in voicing:
                            self.place(epiano(f, 1.4), start + (s + off) * step, 0.13)
        elif kind == "stabs":
            for s in range(2, steps, 4):
                for f in voicing[:3]:
                    self.place(pluck_tone(self.rng, f * 2, 0.3, 0.99), start + s * step, 0.12)
        elif kind == "strings":
            self.place(strings(voicing, length + 0.2, 0.3, 0.3, self.rng), start, 0.28)
        elif kind == "piano8":
            for s in range(0, steps, 2):
                for f in voicing[:3]:
                    self.place(piano(f, 0.6), start + s * step, 0.1)
        elif kind == "pad":
            self.place(pad(voicing, length + 0.3, 0.8, 0.5, self.rng, 1000), start, 0.2)
        # lead
        if with_lead:
            line = [root + 12, tones[1] + 12, tones[2] + 12, root + 24]
            arp = st["arp"]
            if arp == "riff":
                for e in range(steps // 2):
                    tone = RIFF[(e + index) % 8]
                    if tone is not None:
                        self.place(self.lead(note(line[tone])), start + e * step * 2, 0.2, pan=0.25 * np.cos(e))
            elif arp == "sixteenths":
                seq = [0, 1, 2, 3, 2, 1]
                for s in range(steps):
                    self.place(self.lead(note(line[seq[s % len(seq)]] + (12 if self.style_name == "chiptune" else 0)), 0.15), start + s * step, 0.12, pan=0.3 * np.sin(s))
            else:  # sparse
                for s in range(0, steps, 6):
                    self.place(self.lead(note(line[(s // 6) % 4])), start + s * step, 0.14, pan=0.3 * np.sin(s))

    def outro(self, start):
        tones, seventh = chord_tones(self.progression[0], self.shift)
        freqs = [note(tones[0] - 12)] + [note(x) for x in tones] + [note(tones[0] + 12)]
        hold = start + 0.6
        d = self.meta["duration"] - hold
        if d <= 0.2:
            return
        if self.style_name == "cinematic":
            self.place(strings(freqs, d, 0.05, 1.0, self.rng), hold, 0.3)
        else:
            self.place(pad(freqs, d, 0.05, 1.0, self.rng), hold, 0.22)
        for k, s in enumerate([12, 16, 19, 24]):
            self.place(self.lead(note(tones[0] + 12 + s), 0.6), hold + 1.2 + k * 0.15, 0.1, pan=0.3 * (-1) ** k)

    # -------------------------------------------------------------- render
    def render(self):
        scenes = self.meta["scenes"]
        groove_index = 0
        for i, sc in enumerate(scenes):
            nxt = scenes[i + 1]["mood"] if i + 1 < len(scenes) else None
            mood = sc["mood"]
            if mood == "tension":
                self.tension(sc["start"], sc["len"])
            elif mood == "calm":
                self.calm(sc["start"], sc["len"], nxt)
            elif mood in ("groove", "run"):
                self.groove(sc["start"], sc["len"], groove_index, mood == "groove")
                groove_index += 1
            elif mood == "outro":
                self.outro(sc["start"])
        out = self.buf
        if self.style.get("crackle"):
            c = crackle(self.rng, self.meta["duration"] + 0.1)[: self.n]
            out[: len(c)] += np.stack([c, c], 1) * 0.5
        if self.style.get("darken"):
            sos = butter(2, self.style["darken"], btype="low", fs=SR, output="sos")
            out = np.stack([sosfilt(sos, out[:, 0]), sosfilt(sos, out[:, 1])], 1)
        if self.style.get("pump"):
            t = np.arange(self.n) / SR
            phase = (t % self.beat)
            out = out * (1 - 0.35 * np.exp(-phase / 0.09))[:, None]
        return out


def render_music(meta, rng):
    return Music(meta, rng).render()
