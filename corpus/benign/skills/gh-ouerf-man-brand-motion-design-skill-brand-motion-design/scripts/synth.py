"""Royalty-free music bed and sound effects, synthesized with numpy.

Music: an exact grid (you set the tempo, so there is nothing to detect), a
bar-by-bar energy curve that follows the story, a clean ring-out.

    uv run --with numpy python3 scripts/synth.py music --out assets/audio/bed.wav \
        [--style trap] [--bpm 140] --bars 12 --key F --mode minor --progression "i VI VII v" \
        --energy 123333332210 [--seed 7] [--tail 0]

    Hip-hop / trap (the default): 808s with glides, half-time clap on 3, hat
    rolls, dark FM bells, at 130 to 150 BPM; energy 0 is a filtered intro.
    --style soft is the calm bed for explainers. Punchy electronic: --style punchy (harder kick, claps, 16th hats, sidechain pump),
    --hits "3 5" (impact on those downbeats), --risers "5" (a riser filling
    the bar before bar 5), --gaps "5" (half a beat of silence before bar 5).

    energy per bar (one digit each): 0 pad only, 1 + pluck arpeggio,
    2 + soft kick and hats, 3 + bass and backbeat. Write the energy from the
    beat sheet: calm under the hook, full under the strongest moment, down
    for the headline, ring out at the end.

It also writes <out>.grid.json: {bpm, firstBeat: 0, beatsPerBar, bars,
duration}. Paste it into cues.js.

Sound effects (short, dry, quiet) and their measured peak times:

    uv run --with numpy python3 scripts/synth.py sfx --out assets/audio/sfx

    writes click.wav tick.wav pop.wav whoosh.wav ping.wav chime.wav thud.wav
    and peaks.json ({name: seconds to the loudest sample}). Place each hit at
    cue - peak so the transient lands on the frame (scripts/place-audio.mjs).

Everything here is generated, so the license is yours (no samples used).
"""

import argparse
import json
import os
import wave

import numpy as np

SR = 48000
NOTE = {"C": 0, "C#": 1, "DB": 1, "D": 2, "D#": 3, "EB": 3, "E": 4, "F": 5, "F#": 6, "GB": 6,
        "G": 7, "G#": 8, "AB": 8, "A": 9, "A#": 10, "BB": 10, "B": 11}
SCALES = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10], "dorian": [0, 2, 3, 5, 7, 9, 10]}
ROMAN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6, "VII": 7}


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def write(path, stereo):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    data = (np.clip(stereo, -1, 1) * 32767).astype(np.int16)
    with wave.open(path, "wb") as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(data.tobytes())


def env(n, attack, release, sustain=1.0):
    a = max(1, int(attack * SR))
    r = max(1, int(release * SR))
    e = np.full(n, sustain, np.float32)
    e[: min(a, n)] = np.linspace(0, sustain, min(a, n))
    if r < n:
        e[-r:] *= np.linspace(1, 0, r) ** 2
    return e


def tone(freq, seconds, harmonics=(1.0,), detune=0.0, phase=0.0):
    t = np.arange(int(seconds * SR)) / SR
    out = np.zeros_like(t)
    for k, amp in enumerate(harmonics, start=1):
        out += amp * np.sin(2 * np.pi * freq * k * (1 + detune) * t + phase * k)
    return out.astype(np.float32)


def add(buf, sig, start, gain=1.0, pan=0.0):
    i = int(round(start * SR))
    if i >= len(buf):
        return
    sig = sig[: len(buf) - i]
    left, right = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
    buf[i:i + len(sig), 0] += sig * gain * left * 1.4142
    buf[i:i + len(sig), 1] += sig * gain * right * 1.4142


def lowpass(x, cutoff):
    # one-pole, vectorised in blocks via cumulative filtering (fine for short signals)
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc
        y[i] = acc
    return y


def chords_for(key, mode, progression):
    root = NOTE[key.upper()]
    scale = SCALES[mode]
    out = []
    for token in progression.split():
        degree = ROMAN[token.strip("°+").upper()] - 1
        notes = [scale[(degree + s) % 7] + 12 * ((degree + s) // 7) for s in (0, 2, 4)]
        out.append([root + n for n in notes])
    return out


def fm_bell(freq, seconds, index=2.2, ratio=3.5, decay=5.0):
    """A small FM bell: bright attack, dark tail (the trap 'bell' melody)."""
    t = np.arange(int(seconds * SR)) / SR
    mod = index * np.exp(-t * decay * 1.5) * np.sin(2 * np.pi * freq * ratio * t)
    return (np.sin(2 * np.pi * freq * t + mod) * np.exp(-t * decay)).astype(np.float32)


def eight08(freq, seconds, glide_to=None, glide_at=None):
    """An 808: a sine with a punchy start, long tail, optional pitch glide, a little drive."""
    n = int(seconds * SR)
    t = np.arange(n) / SR
    f = np.full(n, freq, np.float64)
    if glide_to is not None and glide_at is not None and glide_at < seconds:
        k = t >= glide_at
        u = np.clip((t[k] - glide_at) / 0.09, 0, 1)
        f[k] = freq * (glide_to / freq) ** u
    f = f * (1 + 1.6 * np.exp(-t * 60))  # the click of the pitch drop
    phase = 2 * np.pi * np.cumsum(f) / SR
    y = np.tanh(1.8 * np.sin(phase)) * np.exp(-t * 1.6)
    y[: int(0.003 * SR)] *= np.linspace(0, 1, int(0.003 * SR))
    return y.astype(np.float32)


def trap_layers(args, buf, drums, energy, chords, beat, bar, rng, kicks):
    """Hip-hop / trap: half-time clap on 3, 808s with glides, hat rolls, a dark bell melody."""
    s16 = beat / 4
    noise = rng.standard_normal(int(0.4 * SR)).astype(np.float32)
    hat = np.diff(noise[: int(0.04 * SR)], prepend=0) * env(int(0.04 * SR), 0.0005, 0.035)
    ohat = np.diff(noise[: int(0.28 * SR)], prepend=0) * env(int(0.28 * SR), 0.001, 0.26)
    tt = np.arange(int(0.25 * SR)) / SR
    clap = np.zeros(int(0.25 * SR), np.float32)
    for d in (0, 0.008, 0.017, 0.028):
        i = int(d * SR)
        clap[i:] += (np.diff(noise[: len(clap) - i], prepend=0) * np.exp(-tt[: len(clap) - i] * 28)).astype(np.float32)
    clap += (np.sin(2 * np.pi * 210 * tt) * np.exp(-tt * 30) * 0.5).astype(np.float32)
    tk = np.arange(int(0.18 * SR)) / SR
    kick = (np.tanh(2.5 * np.sin(2 * np.pi * (50 * tk + 110 * (1 - np.exp(-tk * 40)) / 40)) * np.exp(-tk * 16))).astype(np.float32)
    pattern808 = [(0, 6), (6, 4), (10, 6)]  # (sixteenth, length in sixteenths)
    melody = [0, None, 2, None, 1, None, 4, 3, 0, None, 2, None, 4, None, 3, 2]  # scale steps per sixteenth pair
    for index in range(args.bars):
        level = energy[index]
        start = index * bar
        chord = chords[index % len(chords)]
        nxt = chords[(index + 1) % len(chords)]
        root = chord[0] % 12
        # bell melody on eighths from the chord and its neighbours (dark, sparse at low energy)
        if True:
            tones = sorted(set([n % 12 for n in chord] + [(chord[0] + 10) % 12]))
            for k, step in enumerate(melody[: args.beats * 2 if level < 3 else args.beats * 4]):
                if step is None:
                    continue
                if level == 0 and k % 4:
                    continue
                pitch = 72 + tones[step % len(tones)] + (12 if step >= len(tones) else 0)
                at = start + k * beat / 2
                if at >= start + bar:
                    break
                b_ = fm_bell(hz(pitch), 0.9)
                if level == 0:
                    b_ = lowpass(b_, 900)
                add(buf, b_, at, 0.2 if level <= 1 else 0.16, 0.3 if k % 2 else -0.3)
        if level >= 2:
            # 808 + kick on the pattern, the last note glides into the next bar's root
            for j, (pos, length) in enumerate(pattern808):
                at = start + pos * s16
                f0 = hz(40 + (root + 8) % 12)  # 808 between E2 and D#3: audible on phone speakers
                glide = hz(40 + (nxt[0] % 12 + 8) % 12) if j == len(pattern808) - 1 and nxt[0] % 12 != root else None
                add(buf, eight08(f0, length * s16 + 0.05, glide, length * s16 - 0.12), at, 0.42)
                add(drums, kick, at, 0.5)
                kicks.append(at)
            # half-time clap on beat 3
            add(drums, clap, start + 2 * beat, 0.42)
            if level >= 3:
                add(drums, clap, start + 2 * beat + s16 * 3, 0.1)  # a ghost
            # hats: eighths, sixteenths at full energy, a roll into the next bar
            steps = 16 if level >= 3 else 8
            for k in range(steps):
                pos = k * (16 // steps)
                if level >= 3 and pos >= 12 and index % 2 == 1:
                    continue  # leave room for the roll
                add(drums, hat, start + pos * s16, 0.16 if pos % 4 == 0 else 0.11, 0.25)
            if level >= 3 and index % 2 == 1:
                for k in range(9):  # a 32nd-note-triplet roll across the last beat
                    add(drums, hat, start + 3 * beat + k * beat / 9, 0.07 + 0.01 * k, 0.25)
            add(drums, ohat, start + 3 * beat + beat / 2, 0.08, -0.2)
        elif level == 1:
            for k in range(8):
                add(drums, hat, start + k * beat / 2, 0.08, 0.25)


def music(args):
    rng = np.random.default_rng(args.seed)
    beat = 60.0 / args.bpm
    bar = beat * args.beats
    energy = [int(c) for c in args.energy.ljust(args.bars, args.energy[-1])[: args.bars]]
    duration = args.bars * bar
    total = duration + args.tail
    buf = np.zeros((int(total * SR) + SR, 2), np.float32)  # tonal: pads, plucks, bass
    drums = np.zeros_like(buf)
    punchy = args.style in ("punchy", "trap")
    chords = chords_for(args.key, args.mode, args.progression)
    kicks = []  # kick times, for the sidechain pump
    hits = [float(x) for x in args.hits.replace(",", " ").split()] if args.hits else []
    risers = [float(x) for x in args.risers.replace(",", " ").split()] if args.risers else []
    gaps = [float(x) for x in args.gaps.replace(",", " ").split()] if args.gaps else []
    at_bar = lambda b: (b - 1) * bar  # bar numbers are 1-based on the film grid

    t = np.arange(int(0.35 * SR)) / SR
    kick = (np.sin(2 * np.pi * (45 * t + (110 - 45) * (1 - np.exp(-t * 28)) / 28)) * np.exp(-t * 9)).astype(np.float32)
    if punchy:  # a harder kick: higher sweep, a click on top, a little drive
        kick = np.tanh(2.2 * np.sin(2 * np.pi * (48 * t + (160 - 48) * (1 - np.exp(-t * 35)) / 35)) * np.exp(-t * 7.5)).astype(np.float32)
        click = rng.standard_normal(int(0.004 * SR)).astype(np.float32) * np.linspace(1, 0, int(0.004 * SR))
        kick[: len(click)] += click * 0.6
    noise = rng.standard_normal(int(0.12 * SR)).astype(np.float32)
    hat = np.diff(noise, prepend=0)[: int(0.05 * SR)] * env(int(0.05 * SR), 0.001, 0.045) * 0.5
    snare = (np.diff(noise, prepend=0) * 0.5 + tone(185, 0.12, (1, 0.3))) * env(int(0.12 * SR), 0.001, 0.11)

    if args.style == "trap":
        trap_layers(args, buf, drums, energy, chords, beat, bar, rng, kicks)
    else:
        for index in range(args.bars):
            level = energy[index]
            start = index * bar
            chord = chords[index % len(chords)]
            # pad: soft additive voices, slightly detuned, whole bar, always on
            pad_len = bar + (args.tail if index == args.bars - 1 else 0.25)
            for j, n in enumerate(chord):
                for det, pan in ((-0.0025, -0.5), (0.0025, 0.5)):
                    voice = tone(hz(n + 48 - 12 * (n > 11)), pad_len, (1, 0.35, 0.12, 0.05), det, j)
                    add(buf, voice * env(len(voice), 0.35, 0.6), start, 0.055, pan)
            if level >= 1:  # pluck arpeggio on eighths (sixteenths at full energy)
                step = beat / (4 if level >= 3 else 2)
                pattern = [0, 1, 2, 1, 2, 0, 2, 1]
                for k in range(int(round(bar / step))):
                    n = chord[pattern[k % len(pattern)]] + 72 - 12 * (chord[0] > 5)
                    p = tone(hz(n), 0.4, (1, 0.25, 0.08)) * env(int(0.4 * SR), 0.002, 0.38) * np.exp(-np.arange(int(0.4 * SR)) / SR * 7)
                    add(buf, p, start + k * step, 0.07 if level < 3 else 0.055, 0.35 if k % 2 else -0.35)
            if level >= 2:
                for k in range(args.beats):
                    add(drums, kick, start + k * beat, (0.62 if punchy else 0.5) if level >= 3 else 0.32)
                    kicks.append(start + k * beat)
                if punchy and level >= 3:  # sixteenth hats, accented on the offbeat
                    for k in range(args.beats * 4):
                        add(drums, hat, start + k * beat / 4, 0.13 if k % 2 else 0.06, 0.25 if k % 4 == 2 else -0.15)
                else:
                    for k in range(args.beats):  # hats on the "and" of every beat
                        add(drums, hat, start + k * beat + beat / 2, 0.12, 0.2)
            if level >= 3:
                for k in (1, 3):
                    if k < args.beats:
                        add(drums, snare, start + k * beat, 0.24 if punchy else 0.16)
                        if punchy:  # clap layer: three quick noise bursts
                            for j, dly in enumerate((0, 0.009, 0.019)):
                                add(drums, np.diff(noise, prepend=0)[: int(0.09 * SR)] * env(int(0.09 * SR), 0.001, 0.085), start + k * beat + dly, 0.07, (-0.3, 0.3, 0)[j])
                root = chord[0] + 36 - 12 * (chord[0] > 7)
                for k in range(args.beats * 2):
                    bass = tone(hz(root), beat / 2 * 0.95, (1, 0.5, 0.25, 0.12)) * env(int(beat / 2 * 0.95 * SR), 0.004, 0.08)
                    add(buf, bass, start + k * beat / 2, 0.26 if punchy else 0.22)

    # impacts (a sub drop plus a noise crash) on the downbeat of each listed bar
    for b in hits:
        t0 = at_bar(b)
        n = int(1.4 * SR)
        tt = np.arange(n) / SR
        sub = np.sin(2 * np.pi * (38 * tt + 60 * (1 - np.exp(-tt * 6)) / 6)) * np.exp(-tt * 2.2)
        crash = lowpass(rng.standard_normal(n).astype(np.float32), 6000) * np.exp(-tt * 3.5)
        add(drums, (sub * 0.9 + crash * 0.35).astype(np.float32), t0, 0.55)
    # risers: filtered noise and a pitch sweep across the bar before the listed bar
    for b in risers:
        t1 = at_bar(b)
        t0 = t1 - bar
        n = int(bar * SR)
        tt = np.arange(n) / SR
        u = tt / bar
        sweep = np.sin(2 * np.pi * np.cumsum(200 + 1400 * u ** 2) / SR) * 0.25
        hiss = np.diff(rng.standard_normal(n).astype(np.float32), prepend=0) * 0.3
        add(drums, ((sweep + hiss) * u ** 2.2).astype(np.float32), t0, 0.35)
    # gaps: silence the last half beat before the listed bar (the breath before a drop)
    for b in gaps:
        t1 = at_bar(b)
        i0, i1 = int((t1 - beat / 2) * SR), int(t1 * SR)
        ramp = np.linspace(1, 0, max(1, int(0.01 * SR)))[:, None]
        for target in (buf, drums):
            target[i0:i0 + len(ramp)] *= ramp
            target[i0 + len(ramp):i1] = 0

    # sidechain pump: the tonal parts duck under every kick (punchy style)
    if args.style == "punchy" and kicks:  # (trap keeps its 808s whole)
        tt = np.arange(len(buf)) / SR
        gain = np.ones(len(buf), np.float32)
        for k in kicks:
            i = int(k * SR)
            j = min(len(buf), i + int(beat * SR))
            gain[i:j] = np.minimum(gain[i:j], 1 - 0.6 * np.exp(-(tt[i:j] - k) / 0.09))
        buf *= gain[:, None]
    buf += drums

    # a simple room: a few decaying taps
    wet = np.zeros_like(buf)
    for delay, g in ((0.031, 0.35), (0.047, 0.3), (0.071, 0.24), (0.113, 0.18), (0.173, 0.12)):
        d = int(delay * SR)
        wet[d:] += buf[:-d] * g
    wet[:, [0, 1]] = wet[:, [1, 0]] * 0.9 + wet * 0.1
    mix = buf + wet * 0.35
    mix = mix[: int(total * SR)]
    mix = np.tanh(mix * 1.4) / np.tanh(1.4)
    rms = np.sqrt(np.mean(mix ** 2)) + 1e-9
    mix *= min(10 ** (-16 / 20) / rms, 0.84 / (np.abs(mix).max() + 1e-9))  # about -1.5 dBFS: room for the true peak after AAC
    fade = max(int(min(args.tail, 1.2) * SR), int(0.01 * SR))  # at least 10 ms, so --tail 0 ends clean on the downbeat
    mix[-fade:] *= np.linspace(1, 0, fade)[:, None] ** 2
    write(args.out, mix)
    grid = {"bpm": args.bpm, "firstBeat": 0, "pickupBeats": 0, "beatsPerBar": args.beats, "bars": args.bars,
            "duration": round(duration, 4), "fileDuration": round(total, 4), "energy": args.energy,
            "key": f"{args.key} {args.mode}", "progression": args.progression, "style": args.style,
            "hits": args.hits, "risers": args.risers, "gaps": args.gaps}
    with open(os.path.splitext(args.out)[0] + ".grid.json", "w") as f:
        json.dump(grid, f, indent=2)
    print(f"{args.out}: {total:.2f}s ({args.bars} bars at {args.bpm} BPM + {args.tail}s tail), grid -> {os.path.splitext(args.out)[0]}.grid.json")


def sfx(args):
    rng = np.random.default_rng(3)
    out = {}

    def save(name, sig, gain=0.7):
        sig = sig / (np.abs(sig).max() + 1e-9) * gain
        path = os.path.join(args.out, name + ".wav")
        write(path, np.stack([sig, sig], axis=1))
        out[name] = round(int(np.argmax(np.abs(sig))) / SR, 4)

    n = lambda s: int(s * SR)
    t = lambda s: np.arange(n(s)) / SR
    noise = lambda s: rng.standard_normal(n(s)).astype(np.float32)

    save("click", (np.diff(noise(0.03), prepend=0) * 0.4 + np.sin(2 * np.pi * 2400 * t(0.03))) * np.exp(-t(0.03) * 260), 0.5)
    save("tick", np.sin(2 * np.pi * 1800 * t(0.05)) * np.exp(-t(0.05) * 120), 0.35)
    save("pop", np.sin(2 * np.pi * (900 * t(0.09) - 2500 * t(0.09) ** 2)) * np.exp(-t(0.09) * 45), 0.5)
    w = lowpass(noise(0.6), 1800) * np.sin(np.pi * np.clip(t(0.6) / 0.6, 0, 1)) ** 2
    save("whoosh", w, 0.45)
    save("ping", (np.sin(2 * np.pi * 1318.5 * t(0.9)) + 0.3 * np.sin(2 * np.pi * 2637 * t(0.9))) * np.exp(-t(0.9) * 6) * env(n(0.9), 0.002, 0.2), 0.4)
    c = sum(np.sin(2 * np.pi * f * t(1.4)) * np.exp(-t(1.4) * d) for f, d in ((880, 3.5), (1108.7, 4), (1318.5, 4.5), (1760, 6)))
    save("chime", c * env(n(1.4), 0.004, 0.4), 0.4)
    save("thud", np.sin(2 * np.pi * (40 * t(0.4) + 70 * (1 - np.exp(-t(0.4) * 20)) / 20)) * np.exp(-t(0.4) * 8), 0.6)
    with open(os.path.join(args.out, "peaks.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(f"{len(out)} effects in {args.out}, peaks.json: {out}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("music")
    m.add_argument("--out", required=True)
    m.add_argument("--bpm", type=float, default=140)
    m.add_argument("--bars", type=int, default=10)
    m.add_argument("--beats", type=int, default=4)
    m.add_argument("--key", default="D")
    m.add_argument("--mode", default="minor", choices=sorted(SCALES))
    m.add_argument("--progression", default="i VI III VII")
    m.add_argument("--energy", default="1223332211")
    m.add_argument("--tail", type=float, default=1.5)
    m.add_argument("--seed", type=int, default=7)
    m.add_argument("--style", default="trap", choices=["soft", "punchy", "trap"], help="punchy: harder kick, claps, 16th hats, sidechain pump; trap: hip-hop, 808s with glides, half-time clap, hat rolls, dark bells (use 130 to 150 BPM)")
    m.add_argument("--hits", default="", help="bars (1-based) that open with an impact, e.g. '3 5'")
    m.add_argument("--risers", default="", help="bars that a riser leads INTO (it fills the bar before)")
    m.add_argument("--gaps", default="", help="bars preceded by a half-beat of silence")
    s = sub.add_parser("sfx")
    s.add_argument("--out", required=True)
    args = p.parse_args()
    music(args) if args.cmd == "music" else sfx(args)


if __name__ == "__main__":
    main()
