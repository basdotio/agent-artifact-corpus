#!/usr/bin/env python3
"""Compose an example score for a short film from the film's timings.

A worked example for the bitwig-track skill. One source of truth: this file
reads the film's scenes and hits (film.json), lays the music out against them,
and writes

  score.json                         the score as data (tracks, notes, cues)
  midi/NN-<part>.mid                 one Standard MIDI File per part
  midi/example-score.mid             every part in one type-1 file, with markers
  bitwig/Example Score.control.js    the Bitwig controller script that builds it
  README.md                          the arrangement map, between its markers
                                     (only if README.md already has them)

The folder layout it expects (copy this file in as score.py):

  <track>/
    score.py                         this file
    film.json                        the input (shape below)
    bitwig/template.control.js       the controller script template
    bitwig/simulate.cjs              the host simulator
    README.md                        optional, with the arrangement markers:
                                     <!-- arrangement:start --> <!-- arrangement:end -->

Outputs go next to score.py unless you pass --out. If there's no bitwig/
folder, the template is also looked for next to this file, so it runs
straight from the skill's reference/ folder too.

film.json:

  {
    "bpm": 100,                      optional, else DEFAULT_TEMPO
    "duration": 60,                  seconds
    "scenes": [                      at least four: opening, turn, middle..., end card
      {"name": "Opening", "start": 0},
      {"name": "The turn", "start": 8},
      {"name": "Build", "start": 14},
      {"name": "Peak", "start": 30},
      {"name": "End card", "start": 50}
    ],
    "marks": [                       optional hits: [seconds, name, kind?]
      [8.0, "freeze", "reverse"],
      [10.5, "lift", "resolve"],
      [52.0, "logo", "land"],
      [20.0, "hit one", "chime"]
    ]
  }

Run it again whenever the edit changes:

  python3 score.py                        # reads ./film.json
  python3 score.py --film path/film.json  # another edit
  python3 score.py --install              # also copy the script into Bitwig

Paths and versions come from flags or environment variables:

  --packages / BITWIG_PACKAGES_DIR   installed-packages folder (presets)
  --scripts  / BITWIG_SCRIPTS_DIR    user Controller Scripts folder (--install)
  --api      / BITWIG_API            Controller API version for loadAPI()
  BITWIG_HOME                        Bitwig install, to detect the API version

The PARTS and FX presets below are examples from Bitwig's Essentials and
Polymerics packages. They are checked for existence on every run; replace
any that are missing with presets you have (find <packages> -name '*.bwpreset').

No third-party modules: the SMF writer is below.
"""

import argparse
import json
import math
import os
import random
import re
import shutil
import struct
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))

# ----------------------------------------------------------------------------
# Settings you might change
# ----------------------------------------------------------------------------

DEFAULT_TEMPO = 100          # used when film.json has no "bpm"
STEP = 0.25                  # every note starts on a 16th (Bitwig's step grid)
PPQ = 960

# How the script shows up in Bitwig (Settings > Controllers > Add controller).
VENDOR = "Bitwig Track"
SCRIPT_NAME = "Example Score"
TITLE = "Example score"
AUTHOR = "bitwig-track skill"
KNOWN_GOOD_API = 25          # Bitwig 6.1

# Preset paths below are relative to the installed-packages folder.
PRESETS = "5.0/Bitwig"
ESS = PRESETS + "/Essentials/Presets"

# Effect (return) tracks, in order; parts send to them by name.
FX = [
    {"name": "Hall", "preset": ESS + "/Reverb/Hall One.bwpreset"},
    {"name": "Echo", "preset": ESS + "/Delay-2/3 16ths.bwpreset"},
]
MASTER = {"device": "Compressor+", "preset": ESS + "/Compressor+/Solid State Glue.bwpreset"}

# The parts. `pitch` pins one-shot instruments to a key; `gm` is only for the
# rough preview and General MIDI players.
PARTS = [
    {"id": "pad",    "name": "Pad",      "preset": PRESETS + "/Polymerics/Velvet Rise Pad.bwpreset",   "ch": 0, "sends": {"Hall": 0.45}},
    {"id": "arp",    "name": "Arp",      "preset": PRESETS + "/Polymerics/Gentle Fold Pluck.bwpreset", "ch": 1, "sends": {"Hall": 0.30, "Echo": 0.35}},
    {"id": "lead",   "name": "Lead",     "preset": PRESETS + "/Polymerics/Pure Sun Pluck.bwpreset",    "ch": 2, "sends": {"Hall": 0.35, "Echo": 0.40}},
    {"id": "bells",  "name": "Bells",    "preset": PRESETS + "/Polymerics/Clear Water Bell.bwpreset",  "ch": 3, "sends": {"Hall": 0.50, "Echo": 0.30}},
    {"id": "bass",   "name": "Sub Bass", "preset": PRESETS + "/Polymerics/Sine Bass.bwpreset",         "ch": 4, "sends": {}},
    {"id": "kick",   "name": "Kick",     "preset": ESS + "/E-Kick/Clean Kick.bwpreset",                "ch": 9, "sends": {"Hall": 0.05}},
    {"id": "clap",   "name": "Clap",     "preset": ESS + "/E-Clap/Classic Clap Wide.bwpreset",         "ch": 9, "sends": {"Hall": 0.25}},
    {"id": "hat",    "name": "Hat",      "preset": ESS + "/E-Hat/Basic Hat 1 Closed.bwpreset",         "ch": 9, "sends": {"Hall": 0.10, "Echo": 0.10}},
    {"id": "ohat",   "name": "Open Hat", "preset": ESS + "/E-Hat/Basic Hat 1 Open.bwpreset",           "ch": 9, "sends": {"Hall": 0.20}},
    {"id": "shaker", "name": "Shaker",   "preset": ESS + "/E-Hat/Shaker 1.bwpreset",                   "ch": 9, "sends": {"Hall": 0.15}},
    {"id": "riser",  "name": "Riser",    "preset": ESS + "/Phase-4/Noise Riser.bwpreset",              "ch": 5, "sends": {"Hall": 0.35}},
    {"id": "impact", "name": "Impact",   "preset": ESS + "/Polysynth/FX Impact.bwpreset",              "ch": 6, "sends": {"Hall": 0.45}},
]
DRUM_KEY = {"kick": 36, "clap": 39, "hat": 42, "ohat": 46, "shaker": 70}
RISER_KEY, IMPACT_KEY = 53, 41     # F3, F2: the tonic, so the one-shots sit in key

# Which film moments drive the music. Each cue tries mark names, then mark
# kinds (the optional third field of a mark), then a fallback.
CUES = {
    "freeze": {"names": ["freeze", "the turn"], "kinds": ["reverse"]},
    "rewind": {"names": ["rewind", "the turn"], "kinds": ["reverse"]},
    "lift":   {"names": ["lift", "reveal"],     "kinds": ["resolve"]},
    "logo":   {"names": ["logo", "title"],      "kinds": ["land"]},
}

# How busy each middle scene is: 1 steady, "breath" drops the drums, 2 full,
# "2b" full with another bass line and harmony, 3 peak. Unknown scene names
# fall back to keywords, then to 2 (1 for the first middle scene).
LEVELS = {
    "Intro": 1, "Calm": "breath", "Build": 2, "Variation": "2b", "Peak": 3,
}
LEVEL_KEYWORDS = [("calm", "breath"), ("quiet", "breath"), ("peak", 3), ("climax", 3), ("variation", "2b"), ("build", 2)]

# Film hits the bells answer, by mark name or kind.
ACCENT_NAMES = {"arrival": "pluck", "copies": "copies", "send": "send"}
ACCENT_KINDS = {"blip": "blip", "chime": "chime", "send": "send", "pluck": "pluck", "hit": "hit"}

# ----------------------------------------------------------------------------
# Harmony: F major / D minor. Each chord is (sub-bass root, pad voicing).
# The voicings move by step or not at all from one chord to the next.
# ----------------------------------------------------------------------------

CHORDS = {
    "Dm(add9)":   (38, [57, 62, 64, 65]),        # D2 | A3 D4 E4 F4: curious, a rub on E-F
    "Bbmaj7#11":  (34, [57, 62, 64, 65]),        # same notes over Bb: the ground shifts
    "Fadd9":      (29, [57, 60, 65, 67]),        # F1 | A3 C4 F4 G4: the turn, minor to its major
    "Bbmaj9":     (34, [62, 65, 69, 72]),        # Bb1 | D4 F4 A4 C5
    "F/A":        (33, [60, 65, 69, 72]),        # A1 | C4 F4 A4 C5
    "Dm9":        (38, [60, 64, 65, 69]),        # D2 | C4 E4 F4 A4
    "Csus4":      (36, [60, 65, 67, 72]),        # C2 | C4 F4 G4 C5
    "C":          (36, [60, 64, 67, 72]),        # C2 | C4 E4 G4 C5 (the 4-3)
    "Gm9":        (31, [58, 62, 65, 69]),        # G1 | Bb3 D4 F4 A4
    "C9sus4":     (36, [58, 62, 65, 67]),        # C2 | Bb3 D4 F4 G4
    "Bbmaj13":    (34, [57, 62, 65, 67]),        # Bb1 | A3 D4 F4 G4
    "Fadd9 (end)": (29, [57, 60, 65, 67, 72]),   # F1 | A3 C4 F4 G4 C5
}
LOOP_A = ["Bbmaj9", "F/A", "Dm9", ("Csus4", "C")]   # IV  I6  vi  V(4-3)
LOOP_B = ["Gm9", "Bbmaj9", "Dm9", "C"]              # ii  IV  vi  V, for "2b"
CADENCE = ["Gm9", "C9sus4"]                         # the last two bars before the end card

# The motif: a reach up (A C D) and an answer down (F E D C). It asks in the
# opening, states at the turn, returns in the answer and the build, and
# resolves on the end card.
MOTIF = [(0, 69, 0.75), (0.75, 72, 0.75), (1.5, 74, 2.5), (4, 77, 0.5), (4.5, 76, 0.5), (5, 74, 1), (6, 72, 2)]
MOTIF_REPLY = [(0, 69, 0.75), (0.75, 72, 0.75), (1.5, 74, 2.5), (4, 77, 0.75), (4.75, 79, 0.75), (5.5, 81, 2.5)]
MOTIF_CADENCE = [(0, 69, 0.75), (0.75, 72, 0.75), (1.5, 74, 2.5), (4, 77, 0.75), (4.75, 74, 0.75), (5.5, 72, 1), (6.5, 70, 1.5)]
MOTIF_END = [(0, 69, 0.75), (0.75, 72, 0.75), (1.5, 74, 2), (3.5, 77, 0.5), (4, 76, 0.5), (4.5, 72, 1), (5.5, 77, 3)]


# ----------------------------------------------------------------------------
# Film timings
# ----------------------------------------------------------------------------

class Film:
    def __init__(self, data, tempo_override=None):
        self.data = data
        self.tempo = float(tempo_override or data.get("bpm") or DEFAULT_TEMPO)
        self.spb = 60.0 / self.tempo
        self.duration = float(data.get("duration", 60))
        self.scenes = data["scenes"]
        self.marks = []
        for m in data.get("marks", []):
            t, name = m[0], m[1]
            kind = m[2] if len(m) > 2 else None
            self.marks.append((float(t), name, kind))

    def beat(self, t):
        return t / self.spb

    def mark(self, cue):
        spec = CUES[cue]
        for name in spec["names"]:
            for t, n, _ in self.marks:
                if n == name:
                    return t
        for kind in spec["kinds"]:
            for t, _, k in self.marks:
                if k == kind:
                    return t
        return None


def q(x, grid=STEP):
    return round(x / grid) * grid


def level_for(name, index, count):
    if name in LEVELS:
        return LEVELS[name]
    low = name.lower()
    for word, level in LEVEL_KEYWORDS:
        if word in low:
            return level
    return 1 if index == 0 else 2


# ----------------------------------------------------------------------------
# The plan: where every section sits, in beats
# ----------------------------------------------------------------------------

def plan(film):
    scenes = film.scenes
    if len(scenes) < 4:
        sys.exit("need at least four scenes (problem, turn, middle, end card)")
    b = film.beat
    turn_start = b(scenes[1]["start"])
    grid = q(b(scenes[2]["start"]), 1)                 # the groove's bar 1
    end_card = b(scenes[-1]["start"])
    total = math.ceil(b(film.duration) / 4) * 4

    freeze = film.mark("freeze")
    freeze = q(b(freeze)) if freeze is not None else q(turn_start)
    rewind = film.mark("rewind")
    rewind = max(freeze, q(b(rewind))) if rewind is not None else freeze
    lift = film.mark("lift")
    lift = q(b(lift)) if lift is not None else q(turn_start + 2.5)
    lift = min(max(lift, rewind + 1), grid - 2)

    bars = max(3, round((end_card - grid) / 4))
    end = grid + 4 * bars                                # end card, on a bar line
    logo = film.mark("logo")
    logo = q(b(logo)) if logo is not None else end + 2
    logo = min(max(logo, end + 1), total - 2)     # the end motif truncates rather than move the hit

    # Middle scenes: density changes snap to the nearest half bar of the groove,
    # rounding up, so the music turns just after the cut rather than before it.
    middle = scenes[2:-1]
    regions = []
    for i, s in enumerate(middle):
        start = grid if i == 0 else grid + 2 * math.floor((b(s["start"]) - grid) / 2 + 0.5)
        regions.append({"scene": s["name"], "level": level_for(s["name"], i, len(middle)), "start": start})
    for i, r in enumerate(regions):
        r["end"] = regions[i + 1]["start"] if i + 1 < len(regions) else end
    regions = [r for r in regions if r["end"] > r["start"]]

    return {
        "tempo": film.tempo, "spb": film.spb, "total": total,
        "freeze": freeze, "rewind": rewind, "lift": lift, "grid": grid,
        "bars": bars, "end": end, "logo": logo, "regions": regions,
    }


def region_at(p, t):
    for r in p["regions"]:
        if r["start"] <= t < r["end"]:
            return r
    return None


def level_at(p, t):
    r = region_at(p, t)
    return r["level"] if r else None


def chord_at(p, t):
    """The chord sounding at beat t (the name)."""
    if t < p["freeze"]:
        return "Dm(add9)" if t < problem_split(p) else "Bbmaj7#11"
    if t < p["grid"]:
        return "Fadd9"
    if t >= p["logo"]:
        return "Fadd9 (end)"
    if t >= p["end"]:
        return "Bbmaj13"
    bar = int((t - p["grid"]) // 4)
    if bar >= p["bars"] - 2:
        return CADENCE[bar - (p["bars"] - 2)]
    downbeat = p["grid"] + 4 * bar
    loop = LOOP_B if level_at(p, downbeat) == "2b" else LOOP_A
    c = loop[bar % 4]
    if isinstance(c, tuple):
        return c[0] if (t - downbeat) < 2 else c[1]
    return c


def problem_split(p):
    """Where the opening's bass moves from D to Bb (only if there's room)."""
    return 8 if p["freeze"] >= 10 else p["freeze"]


def bar_chords(p):
    """(start, length, chord) for every chord change from the groove to the end card."""
    out = []
    t = p["grid"]
    while t < p["end"]:
        c = chord_at(p, t)
        if out and out[-1][2] == c:
            out[-1][1] += 2
        else:
            out.append([t, 2, c])
        t += 2
    return out


# ----------------------------------------------------------------------------
# Composition
# ----------------------------------------------------------------------------

class Score:
    def __init__(self, p):
        self.p = p
        self.notes = {part["id"]: [] for part in PARTS}
        self.rng = random.Random(20260925)

    def add(self, part, start, pitch, vel, dur):
        start = q(start)
        if dur <= 0 or start < 0 or start >= self.p["total"]:
            return
        vel = int(max(1, min(127, round(vel))))
        self.notes[part].append([start, int(pitch), vel, round(dur, 4)])

    def jitter(self, vel, amount=6):
        return vel + self.rng.randint(-amount, amount)

    # --- the opening: sparse, curious ---------------------------------------
    def problem(self):
        p = self.p
        f = p["freeze"]
        split = problem_split(p)
        # Pad: the cluster, then the same notes over a new bass
        for t0, t1 in ((0, split), (split, f)):
            if t1 - t0 >= 1:
                name = chord_at(p, t0)
                for n in CHORDS[name][1]:
                    self.add("pad", t0, n, 58 if t0 == 0 else 64, t1 - t0)
        # Sub: a slow pulse on D, then Bb
        for t, d in ((0, 1.5), (4, 1.5)):
            if t < split:
                self.add("bass", t, 38, 88, min(d, split - t))
        if f > split:
            self.add("bass", split, 34, 92, f - split)
        # Arp: a tick-tock clock, quiet, from beat 2
        t, i = 2.0, 0
        while t < f:
            self.add("arp", t, [69, 76][i % 2], self.jitter(44 if i % 2 == 0 else 34, 3), 0.2)
            t += 0.5
            i += 1
        # Shaker: 16ths from the second bar, barely there
        t = 4.0
        while t < f:
            accent = (t % 1) == 0.5
            self.add("shaker", t, DRUM_KEY["shaker"], self.jitter(34 if accent else 22, 4), 0.1)
            t += 0.25
        # Lead: the motif's first half, a question left hanging
        start = q(max(3, f - 5.5), 1)
        for dt, n, d in MOTIF[:3]:
            if start + dt < f:
                self.add("lead", start + dt, n, 68, min(d, f - start - dt))

    # --- the turn: silence, a rewind swell, the lift -------------------------
    def turn(self):
        p = self.p
        swell = max(1.0, p["lift"] - p["rewind"])
        self.add("riser", p["lift"] - swell, RISER_KEY, 96, swell)
        self.add("impact", p["lift"], IMPACT_KEY, 104, 4)
        self.add("kick", p["lift"], DRUM_KEY["kick"], 100, 0.5)
        self.add("ohat", p["lift"], DRUM_KEY["ohat"], 60, 1)
        span = p["grid"] - p["lift"]
        for n in CHORDS["Fadd9"][1]:
            self.add("pad", p["lift"], n, 84, span)
        self.add("bass", p["lift"], CHORDS["Fadd9"][0], 100, span)
        self.add("bells", p["lift"], 77, 72, 2)
        self.add("bells", p["lift"], 84, 58, 2)
        # The motif, stated in full, landing on the groove's first downbeat
        g = p["grid"]
        lift_motif = [(-5, 69, 0.75), (-4.25, 72, 0.75), (-3.5, 74, 1.5), (-2, 77, 0.5), (-1.5, 76, 0.5), (-1, 74, 0.5), (-0.5, 72, 2.5)]
        for dt, n, d in lift_motif:
            if g + dt > p["lift"]:
                self.add("lead", g + dt, n, 82, d)
        # Hats swell into the groove
        t, k = g - 2, 0
        while t < g:
            self.add("hat", t, DRUM_KEY["hat"], 22 + k * 6, 0.1)
            t += 0.25
            k += 1

    # --- the groove: the middle scenes ---------------------------------------
    def groove(self):
        p = self.p
        g, e = p["grid"], p["end"]
        # Pad: whole chords, re-struck only on a change; the peak adds air on top
        for start, length, name in bar_chords(p):
            level = level_at(p, start)
            vel = {1: 74, "breath": 82, 2: 78, "2b": 76, 3: 88}.get(level, 78)
            voicing = CHORDS[name][1]
            for n in voicing:
                self.add("pad", start, n, vel, length)
            if level == 3:
                self.add("pad", start, voicing[-1] + 12, vel - 22, length)

        # Bars, beat by beat: bass, arp, drums
        bar = 0
        t0 = g
        while t0 < e:
            self.groove_bar(bar, t0)
            bar += 1
            t0 += 4

        self.fills()
        self.lead_middle()

    def groove_bar(self, bar, t0):
        p = self.p
        last_bar = bar == p["bars"] - 1
        for half in (0, 2):
            level = level_at(p, t0 + half)
            if level is None:
                continue
            h0 = t0 + half
            name = chord_at(p, h0)
            root = CHORDS[name][0]
            nxt = CHORDS[chord_at(p, t0 + 4)][0]
            voicing = CHORDS[name][1]
            pool = [n + 12 for n in voicing] + [voicing[0] + 24]

            # Sub bass: (offset, length, velocity, "r" root / "n" next root)
            bass = {
                1:        [(0, 1.5, 100, "r"), (1.5, 0.5, 72, "r")],
                "breath": [(0, 2, 90, "r")],
                2:        [(0, 0.75, 104, "r"), (1, 0.5, 80, "r"), (1.5, 0.5, 90, "r")],
                "2b":     [(0, 0.75, 104, "r"), (0.75, 0.75, 84, "r"), (1.5, 0.5, 94, "r")],
                3:        [(0, 0.75, 106, "r"), (1, 0.5, 82, "r"), (1.5, 0.5, 92, "r" if half == 0 else "n")],
            }[level]
            if level == "breath" and half == 2:
                bass = []
            if level == "breath" and half == 0:
                bass = [(0, 4, 90, "r")]
            for dt, d, v, which in bass:
                self.add("bass", h0 + dt, root if which == "r" else nxt, v, d)

            # Arp: 8ths when steady or breathing, 16ths when full
            if level in (1, "breath"):
                order = [0, 1, 2, 3] if half == 0 else [1, 2, 3, 2]
                for k, idx in enumerate(order):
                    v = (66 if k == 0 else 52) - (14 if level == "breath" else 0)
                    self.add("arp", h0 + k * 0.5, pool[idx], self.jitter(v, 3), 0.35)
            else:
                if level == "2b":
                    order = [0, None, 2, 1, None, 3, 2, None]
                elif level == 3 and bar % 2:
                    order = [0, 2, 4, 2, 1, 3, 4, 3]
                else:
                    order = [0, 1, 2, 3, 1, 2, 3, 4]
                for k, idx in enumerate(order):
                    if idx is None:
                        continue
                    accent = [1.0, 0.62, 0.8, 0.62][k % 4]
                    base = 74 if level == 3 else 68
                    self.add("arp", h0 + k * 0.25, pool[idx], self.jitter(base * accent, 3), 0.22)

            # Drums
            if level == "breath":
                for k in range(4):
                    self.add("hat", h0 + k * 0.5, DRUM_KEY["hat"], self.jitter(38 if k % 2 else 28, 3), 0.1)
                continue
            if level == 1:
                self.add("kick", h0, DRUM_KEY["kick"], 96, 0.5)
                if half == 2:
                    self.add("clap", h0, DRUM_KEY["clap"], 62, 0.5)
                for k in (0.5, 1.5):
                    self.add("hat", h0 + k, DRUM_KEY["hat"], self.jitter(58, 4), 0.1)
                for k in (0, 1):
                    self.add("hat", h0 + k, DRUM_KEY["hat"], self.jitter(34, 3), 0.1)
            else:
                for k in (0, 1):
                    self.add("kick", h0 + k, DRUM_KEY["kick"], 104 if k == 0 else 88, 0.5)
                self.add("clap", h0 + 1, DRUM_KEY["clap"], 84 if level == 3 else 72, 0.5)
                for k in range(8):
                    if level == 3 and k == 6:
                        continue                        # the open hat takes the "and"
                    v = [46, 28, 60, 30][k % 4] * (1.12 if level == 3 else 1.0)
                    self.add("hat", h0 + k * 0.25, DRUM_KEY["hat"], self.jitter(v, 4), 0.1)
                if level == 3:
                    self.add("ohat", h0 + 1.5, DRUM_KEY["ohat"], 56, 0.5)
                    if bar % 2 and half == 2:
                        self.add("clap", h0 + 1.75, DRUM_KEY["clap"], 34, 0.25)   # ghost
                if level == "2b" and half == 2 and bar % 2:
                    self.add("kick", h0 + 1.75, DRUM_KEY["kick"], 62, 0.25)       # a push
            # Shaker: under everything that grooves
            for k in range(8):
                self.add("shaker", h0 + k * 0.25, DRUM_KEY["shaker"], self.jitter([30, 22, 38, 22][k % 4], 4), 0.1)

            # Variation: every fourth bar drops the kick on the last beat
            if half == 2 and bar % 4 == 3 and not last_bar and level in (2, "2b", 3):
                self.notes["kick"] = [n for n in self.notes["kick"] if n[0] != h0 + 1]
                self.add("kick", h0 + 1.5, DRUM_KEY["kick"], 70, 0.25)

    def fills(self):
        """A fill leads into every change of level; a riser into the biggest ones."""
        p = self.p
        regions = p["regions"]
        rank = {"breath": 0, 1: 1, "2b": 2, 2: 2, 3: 3}
        targets = [(r["start"], r["level"]) for r in regions[1:]] + [(p["end"], "end")]
        prev = regions[0]["level"] if regions else 1
        for at, level in targets:
            if level == "breath":
                # Drop: the drums stop a beat early; a soft swell carries over
                self.clear(["kick", "clap", "ohat"], at - 1, at)
                self.add("riser", at - 2, RISER_KEY, 58, 2)
            else:
                length = 2 if level in (3, "end") else 1
                self.clear(["clap", "hat", "ohat", "kick"], at - length, at)
                steps = int(length / 0.25)
                for k in range(steps):
                    v = 36 + (86 - 36) * k / max(1, steps - 1)
                    self.add("clap", at - length + k * 0.25, DRUM_KEY["clap"], v, 0.2)
                self.add("kick", at - length, DRUM_KEY["kick"], 90, 0.5)
                if level != "end" and rank[level] > rank.get(prev, 1):
                    self.add("riser", at - 4, RISER_KEY, 70, 4)
                if level != "end":
                    self.add("ohat", at, DRUM_KEY["ohat"], 64, 1)
            prev = level

    def clear(self, parts, a, b):
        for part in parts:
            self.notes[part] = [n for n in self.notes[part] if not (a <= n[0] < b)]

    def lead_middle(self):
        p = self.p
        g, e = p["grid"], p["end"]
        busy = []

        def place(start, phrase, vel, limit):
            placed = False
            for dt, n, d in phrase:
                if start + dt < limit:
                    self.add("lead", start + dt, n, vel, min(d, limit - start - dt))
                    placed = True
            if placed:
                busy.append((start, min(limit, start + max(dt + d for dt, _, d in phrase))))

        cadence = e - 8
        # Breath: the question again, softer
        for r in p["regions"]:
            if r["level"] == "breath":
                place(q(r["start"] + 1, 1), MOTIF[:3], 64, r["end"])
        # The first peak: motif, then its reply
        peaks = [r for r in p["regions"] if r["level"] == 3 and r["start"] < cadence]
        if peaks:
            r = peaks[0]
            start = g + 4 * math.ceil((r["start"] - g) / 4)
            if start + 8 <= cadence:
                place(start, MOTIF, 86, cadence)
                if start + 16 <= cadence:
                    place(start + 8, MOTIF_REPLY, 84, cadence)
        # The build: the motif over the cadence, falling onto the end card
        place(cadence, MOTIF_CADENCE, 90, e)
        self.add("lead", e, 69, 76, p["logo"] - e)
        # "2b": long tones on the chord's top voices where the lead is free
        for r in p["regions"]:
            if r["level"] != "2b":
                continue
            t = r["start"]
            while t + 2 <= min(r["end"], cadence):
                if not any(t < b and t + 2 > a for a, b in busy):
                    voicing = CHORDS[chord_at(p, t)][1]
                    top = voicing[-1] if int((t - g) / 2) % 2 == 0 else voicing[-2]
                    self.add("lead", t, top, 62, 2)
                t += 2

    # --- the end card: breath, then home -------------------------------------
    def ending(self):
        p = self.p
        e, logo, total = p["end"], p["logo"], p["total"]
        for n in CHORDS["Bbmaj13"][1]:
            self.add("pad", e, n, 80, logo - e)
        # One long rise from the build to the logo
        self.add("riser", e - 4, RISER_KEY, 86, logo - (e - 4))
        self.add("bass", e, CHORDS["Bbmaj13"][0], 92, logo - e)
        # Home: F with a 9th, the sub, a last kick and impact, bells
        ring = total - logo - 1
        for n in CHORDS["Fadd9 (end)"][1]:
            self.add("pad", logo, n, 86, ring)
        self.add("bass", logo, 29, 104, ring - 1)
        self.add("kick", logo, DRUM_KEY["kick"], 108, 0.5)
        self.add("impact", logo, IMPACT_KEY, 112, 6)
        self.add("ohat", logo, DRUM_KEY["ohat"], 66, 2)
        for n, v in ((77, 74), (84, 62), (89, 50)):
            self.add("bells", logo, n, v, 4)
        # The arp unwinds: up the chord in 8ths, fading
        pool = [n + 12 for n in CHORDS["Fadd9 (end)"][1]]
        for k in range(10):
            self.add("arp", logo + 0.5 + k * 0.5, pool[k % len(pool)], 60 - k * 4, 0.4)
        # The motif, resolved
        start = logo + 1
        for dt, n, d in MOTIF_END:
            if start + dt < total:
                self.add("lead", start + dt, n, 84, min(d, total - start - dt))

    # --- bells on the film's hits ---------------------------------------------
    def accents(self, film):
        p = self.p
        last = -9.0
        climb = 0
        for t, name, kind in sorted(film.marks):
            acc = ACCENT_NAMES.get(name)
            if acc is None:
                acc = ACCENT_KINDS.get(kind)
            if acc is None:
                continue
            at = q(film.beat(t))
            if at - last < 0.5 or at >= p["total"]:
                continue
            if p["freeze"] <= at < p["lift"]:
                continue                                  # the rewind stays clean
            voicing = CHORDS[chord_at(p, at)][1]
            top = sorted(set(n % 12 for n in voicing))
            bell = [n for n in range(79, 96) if n % 12 in top]
            if acc == "hit":
                self.add("impact", at, IMPACT_KEY - 12, 62, 3)
            elif acc == "copies":
                for k, n in enumerate(sorted(bell, reverse=True)[:3]):
                    self.add("bells", at + k * 0.25, n, 56 - k * 8, 0.75)
            elif acc == "send":
                for n in bell[:3]:
                    self.add("bells", at, n, 64, 2)
            elif acc in ("blip", "chime"):
                self.add("bells", at, bell[climb % len(bell)], 50 if acc == "blip" else 44, 0.75)
                climb += 1
            else:  # pluck
                self.add("bells", at, bell[len(bell) // 2], 50, 1)
            last = at

    # --- tidy -----------------------------------------------------------------
    def finish(self, film):
        p = self.p
        f, r = p["freeze"], p["rewind"]
        for part, notes in self.notes.items():
            out = []
            # Nothing plays through the freeze but the rewind swell
            for n in notes:
                if part != "riser" and n[0] < f < n[0] + n[3]:
                    n[3] = round(f - n[0], 4)
                if part != "riser" and f <= n[0] < p["lift"]:
                    continue
                n[3] = min(n[3], p["total"] - n[0])
                out.append(n)
            # One note per key at a time: a new strike ends the last one
            out.sort(key=lambda n: (n[0], n[1], -n[2]))
            dedup = []
            seen = set()
            for n in out:
                key = (n[0], n[1])
                if key in seen:
                    continue
                seen.add(key)
                dedup.append(n)
            by_key = {}
            for n in dedup:
                prev = by_key.get(n[1])
                if prev is not None and prev[0] + prev[3] > n[0]:
                    prev[3] = round(n[0] - prev[0], 4)
                by_key[n[1]] = n
            self.notes[part] = [n for n in dedup if n[3] > 0.01]
            for n in self.notes[part]:
                assert abs(n[0] / STEP - round(n[0] / STEP)) < 1e-9, (part, n)


def compose(film, p):
    s = Score(p)
    s.problem()
    s.turn()
    s.groove()
    s.ending()
    s.accents(film)
    s.finish(film)
    return s


# ----------------------------------------------------------------------------
# Standard MIDI Files
# ----------------------------------------------------------------------------

def vlq(n):
    out = [n & 0x7F]
    n >>= 7
    while n:
        out.insert(0, (n & 0x7F) | 0x80)
        n >>= 7
    return bytes(out)


def meta(kind, data):
    return bytes([0xFF, kind]) + vlq(len(data)) + data


def track_chunk(events):
    """events: (tick, order, bytes); order sorts note-offs before note-ons."""
    events.sort(key=lambda e: (e[0], e[1]))
    body = b""
    now = 0
    for tick, _, data in events:
        body += vlq(tick - now) + data
        now = tick
    body += vlq(0) + meta(0x2F, b"")
    return b"MTrk" + struct.pack(">I", len(body)) + body


def conductor_events(p, cues, title):
    us = round(60_000_000 / p["tempo"])
    ev = [
        (0, 0, meta(0x03, title.encode())),
        (0, 0, meta(0x51, us.to_bytes(3, "big"))),
        (0, 0, meta(0x58, bytes([4, 2, 24, 8]))),
        (0, 0, meta(0x59, bytes([0xFF, 0]))),          # 1 flat: F major / D minor
    ]
    for c in cues:
        ev.append((round(c["beat"] * PPQ), 1, meta(0x06, c["name"].encode())))
    return ev


def part_events(part, notes):
    ch = part["ch"]
    ev = [(0, 0, meta(0x03, part["name"].encode()))]
    for start, pitch, vel, dur in notes:
        on = round(start * PPQ)
        off = max(on + 1, round((start + dur) * PPQ))
        ev.append((on, 2, bytes([0x90 | ch, pitch, vel])))
        ev.append((off, 1, bytes([0x80 | ch, pitch, 0])))
    return ev


def smf(tracks, fmt):
    header = b"MThd" + struct.pack(">IHHH", 6, fmt, len(tracks), PPQ)
    return header + b"".join(track_chunk(t) for t in tracks)


def write_midi(score, p, cues, outdir):
    os.makedirs(outdir, exist_ok=True)
    for f in os.listdir(outdir):
        if f.endswith(".mid"):
            os.remove(os.path.join(outdir, f))
    written = []
    for i, part in enumerate(PARTS, 1):
        ev = conductor_events(p, cues, part["name"]) + part_events(part, score.notes[part["id"]])
        name = f"{i:02d}-{slug(part['name'])}.mid"
        with open(os.path.join(outdir, name), "wb") as fh:
            fh.write(smf([ev], 0))
        written.append(name)
    combined = slug(SCRIPT_NAME) + ".mid"
    tracks = [conductor_events(p, cues, TITLE)]
    tracks += [part_events(part, score.notes[part["id"]]) for part in PARTS]
    with open(os.path.join(outdir, combined), "wb") as fh:
        fh.write(smf(tracks, 1))
    written.append(combined)
    return written


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ----------------------------------------------------------------------------
# Outputs
# ----------------------------------------------------------------------------

def secs(p, beat):
    return beat * p["spb"]


def barpos(beat):
    """Bitwig's bar.beat.16th, 1-based; "~" when the time falls between 16ths."""
    bar = int(beat // 4) + 1
    rem = beat - (bar - 1) * 4
    sixteenth = (rem - int(rem)) / STEP
    exact = abs(sixteenth - round(sixteenth)) < 1e-6
    return f"{'' if exact else '~'}{bar}.{int(rem) + 1}.{int(round(sixteenth) if exact else sixteenth) + 1}"


def arrangement_rows(film, p):
    rows = []
    rows.append(("Opening, the problem", 0, p["freeze"], "Pad cluster Dm(add9) then the same notes over Bb, sub pulse, tick-tock arp, shaker, motif's first half left hanging; bells on the hits"))
    rows.append(("Freeze and rewind", p["freeze"], p["lift"], "Everything stops on the freeze; a noise swell rewinds into the lift"))
    rows.append(("The lift", p["lift"], p["grid"], "Impact, kick, Fadd9 opens (D minor turns to its major), the motif in full, hats swell"))
    desc = {1: "Groove: kick on 1 and 3, clap on 3, offbeat hats, 8th arp, sub on the root",
            "breath": "Breath: drums drop, 8th arp, long sub, the motif's question again",
            2: "Full: four on the floor, clap on 2 and 4, 16th hats and arp, driving sub",
            "2b": "Full, other colour: ii-IV-vi-V, syncopated sub, gapped arp, lead long tones",
            3: "Peak: open hats, ghost claps, pad air on top, sub anticipates each change"}
    first_peak = True
    for r in p["regions"]:
        what = desc[r["level"]]
        if r["level"] == 3 and first_peak and r["start"] < p["end"] - 8:
            what += ", the motif and its reply"
            first_peak = False
        rows.append((f"{r['scene']} (level {r['level']})", r["start"], r["end"], what))
    rows.append(("Build (inside the last scene)", p["end"] - 8, p["end"], "Cadence Gm9 to C9sus4, the motif falls onto the end card, clap roll and riser"))
    rows.append(("End card", p["end"], p["logo"], "Drums out, Bbmaj13 breathes, the riser keeps rising"))
    rows.append(("Logo lands, resolve", p["logo"], p["total"], "Fadd9 with impact, last kick, bells, the arp unwinds, the motif resolves up to F; tail"))
    return rows


def readme_block(film, p, cues, source):
    lines = []
    lines.append(f"Generated from `{source}` at {p['tempo']:g} BPM, 4/4, {p['total'] // 4} bars ({secs(p, p['total']):.1f} s). "
                 "Positions are Bitwig's bar.beat.16th (1.1.1 = 0 s; ~ means between 16ths).")
    lines.append("")
    lines.append("| Section | Bars | Film time | What plays |")
    lines.append("| --- | --- | --- | --- |")
    for name, a, b, what in arrangement_rows(film, p):
        lines.append(f"| {name} | {barpos(a)} to {barpos(b)} | {secs(p, a):.2f} to {secs(p, b):.2f} s | {what} |")
    lines.append("")
    lines.append("Cue markers (scene starts, exact film times):")
    lines.append("")
    lines.append("| Marker | Position | Film time |")
    lines.append("| --- | --- | --- |")
    for c in cues:
        lines.append(f"| {c['name']} | {barpos(c['beat'])} | {c['seconds']:.2f} s |")
    lines.append("")
    lines.append("Chords from the groove on, bar by bar:")
    lines.append("")
    lines.append(" | ".join(f"{barpos(a)} {c}" for a, _, c in bar_chords(p)) + f" | {barpos(p['end'])} Bbmaj13 | {barpos(p['logo'])} Fadd9")
    return "\n".join(lines)


def update_readme(block, outdir):
    path = os.path.join(outdir, "README.md")
    if not os.path.exists(path):
        return False
    text = open(path).read()
    start, end = "<!-- arrangement:start -->", "<!-- arrangement:end -->"
    if start not in text:
        return False
    head, rest = text.split(start, 1)
    _, tail = rest.split(end, 1)
    open(path, "w").write(head + start + "\n" + block + "\n" + end + tail)
    return True


# ----------------------------------------------------------------------------
# Where Bitwig lives on this computer
# ----------------------------------------------------------------------------

def default_bitwig_home():
    if sys.platform == "darwin":
        return "/Applications/Bitwig Studio.app"
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Bitwig Studio")
    return "/opt/bitwig-studio"


def default_scripts_dir():
    if sys.platform == "darwin" or sys.platform.startswith("win"):
        return os.path.expanduser("~/Documents/Bitwig Studio/Controller Scripts")
    return os.path.expanduser("~/Bitwig Studio/Controller Scripts")


def default_packages_dir():
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/Bitwig/Bitwig Studio/installed-packages")
    if sys.platform.startswith("win"):
        return os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~/AppData/Local")), "Bitwig Studio", "installed-packages")
    return os.path.expanduser("~/.BitwigStudio/installed-packages")


def detect_api(bitwig_home):
    """The highest "API version N" the installed Javadoc mentions, or None."""
    docs = None
    for sub in ("resources/doc/control-surface/api", "Contents/Resources/doc/control-surface/api"):
        if os.path.isdir(os.path.join(bitwig_home, sub)):
            docs = os.path.join(bitwig_home, sub)
            break
    if docs is None:
        for root, dirs, _ in os.walk(bitwig_home):
            if os.path.basename(root) == "control-surface" and "api" in dirs:
                docs = os.path.join(root, "api")
                break
    if docs is None:
        return None
    best = None
    for root, _, files in os.walk(docs):
        for f in files:
            if not f.endswith(".html"):
                continue
            try:
                text = open(os.path.join(root, f), encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in re.finditer(r"API version (\d+)", text):
                best = max(best or 0, int(m.group(1)))
    return best


def resolve_api(flag):
    if flag:
        return flag, "--api"
    if os.environ.get("BITWIG_API"):
        return int(os.environ["BITWIG_API"]), "BITWIG_API"
    home = os.environ.get("BITWIG_HOME") or default_bitwig_home()
    found = detect_api(home) if os.path.isdir(home) else None
    if found:
        return found, "the Javadoc in " + home
    print(f"warning: couldn't find Bitwig's Javadoc under {home}; using API {KNOWN_GOOD_API} "
          "(set BITWIG_HOME or BITWIG_API)", file=sys.stderr)
    return KNOWN_GOOD_API, "the known-good default"


def find_template(base):
    for path in (os.path.join(base, "bitwig", "template.control.js"), os.path.join(base, "template.control.js")):
        if os.path.exists(path):
            return path
    sys.exit("template.control.js not found in " + base + "/bitwig or " + base)


def bitwig_script(data, template_path, api):
    template = open(template_path).read()
    payload = json.dumps(data, separators=(",", ":"))
    out = template.replace("/*@SCORE@*/null", payload).replace("loadAPI(/*@API@*/25)", f"loadAPI({api})")
    for token, value in (("VENDOR", VENDOR), ("NAME", SCRIPT_NAME), ("AUTHOR", AUTHOR),
                         ("UUID", str(uuid.uuid5(uuid.NAMESPACE_URL, f"bitwig-track:{VENDOR}/{SCRIPT_NAME}")))):
        out = out.replace(f'"@{token}@"', json.dumps(value))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--film", default=os.path.join(HERE, "film.json"), help="the film's timings (default ./film.json)")
    ap.add_argument("--out", default=HERE, help="where to write the outputs (default: next to this file)")
    ap.add_argument("--template", help="template.control.js (default: bitwig/ next to this file, or next to it)")
    ap.add_argument("--tempo", type=float, help="override the film's bpm")
    ap.add_argument("--api", type=int, help="Controller API version (default: BITWIG_API, else detected from BITWIG_HOME)")
    ap.add_argument("--packages", default=os.environ.get("BITWIG_PACKAGES_DIR") or default_packages_dir(),
                    help="Bitwig's installed-packages folder (default: BITWIG_PACKAGES_DIR or the platform default)")
    ap.add_argument("--scripts", default=os.environ.get("BITWIG_SCRIPTS_DIR") or default_scripts_dir(),
                    help="user Controller Scripts folder for --install (default: BITWIG_SCRIPTS_DIR or the platform default)")
    ap.add_argument("--install", action="store_true", help="copy the script into <scripts>/<VENDOR>/")
    args = ap.parse_args()

    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    packages = os.path.expanduser(args.packages)
    for x in PARTS + FX + [MASTER]:
        if not os.path.isabs(x["preset"]):
            x["preset"] = os.path.join(packages, x["preset"])
    api, api_from = resolve_api(args.api)

    film = Film(json.load(open(args.film)), args.tempo)
    p = plan(film)
    score = compose(film, p)

    cues = [{"name": s["name"], "seconds": float(s["start"]), "beat": round(film.beat(float(s["start"])), 4)} for s in film.scenes]
    source = os.path.relpath(os.path.abspath(args.film), out)

    data = {
        "title": TITLE,
        "source": source,
        "tempo": p["tempo"],
        "stepSize": STEP,
        "lengthBeats": p["total"],
        "sections": {k: p[k] for k in ("freeze", "rewind", "lift", "grid", "end", "logo")},
        "regions": p["regions"],
        "cues": cues,
        "fx": FX,
        "master": MASTER,
        "tracks": [dict(part, notes=score.notes[part["id"]]) for part in PARTS],
    }

    missing = [x["preset"] for x in PARTS + FX + [MASTER] if not os.path.exists(x["preset"])]
    if missing:
        print("warning: presets not found:\n  " + "\n  ".join(missing), file=sys.stderr)

    with open(os.path.join(out, "score.json"), "w") as fh:
        json.dump(data, fh, indent=1)
    written = write_midi(score, p, cues, os.path.join(out, "midi"))
    script = bitwig_script(data, args.template or find_template(HERE), api)
    os.makedirs(os.path.join(out, "bitwig"), exist_ok=True)
    script_path = os.path.join(out, "bitwig", SCRIPT_NAME + ".control.js")
    with open(script_path, "w") as fh:
        fh.write(script)
    readme = update_readme(readme_block(film, p, cues, source), out)

    if args.install:
        dest = os.path.join(os.path.expanduser(args.scripts), VENDOR)
        os.makedirs(dest, exist_ok=True)
        shutil.copy(script_path, dest)
        print(f"installed {dest}/{os.path.basename(script_path)}")

    count = sum(len(score.notes[x["id"]]) for x in PARTS)
    print(f"{source}: {p['tempo']:g} bpm, {p['total']} beats, {len(PARTS)} parts, {count} notes")
    print(f"freeze {barpos(p['freeze'])}  lift {barpos(p['lift'])}  groove {barpos(p['grid'])}  end card {barpos(p['end'])}  logo {barpos(p['logo'])}")
    for r in p["regions"]:
        print(f"  {r['scene']:<20} level {str(r['level']):<6} {barpos(r['start'])} to {barpos(r['end'])}")
    print(f"wrote score.json, {len(written)} MIDI files, {os.path.basename(script_path)} (API {api}, from {api_from})" + (", README arrangement" if readme else ""))


if __name__ == "__main__":
    main()
