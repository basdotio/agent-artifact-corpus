// video-gaga music — a deterministic, procedurally arranged score.
//
// The composition declares its own score: `music: { bpm, key, mode,
// progression, layers, lead, seed, … }`, designed by the agent for this video
// (there are no preset styles; see "the score spec" below). The runtime
// resolves the timeline (scenes snapped to the beat grid, voice spans, sound
// effects) and hands this module a plan via `__CV.info().score`. We arrange
// the music *from that plan*:
//   • harmony and groove come from the spec; the tempo is the video's grid
//   • each scene's `energy` decides which layers play in its bars
//   • the bed dips under narration and a lead melody fills the gaps
//   • hits get a breath of silence before them, rising scenes get a fill and a crash
//   • the last bar resolves on the tonic and rings out with the final frame
//   • transition whooshes, ticks, risers and hits are placed in time
// Everything is a pure function of (plan, seed): no Math.random, no clock.
//
//   import { renderScore, writeWav } from './music.mjs'
//   const mix = await renderScore(plan); writeWav('music.wav', mix)
//
// The notes are played by real instrument samples (a General MIDI SoundFont,
// rendered offline by scripts/soundfont.mjs): piano, strings, guitars, mallets,
// bass, brass, winds and acoustic or electronic drum kits. When the samples
// aren't available (no network on the first run) it falls back to the small
// built-in synthesizer below and says so: that sounds much cheaper.

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { loadSoundfont, Sampler } from './soundfont.mjs';
import * as Multi from './samples.mjs';

const SR = 48000;
const TAU = Math.PI * 2;
const BLK = 1200; // 25 ms analysis blocks

// ---------------------------------------------------------------------------
// deterministic helpers
// ---------------------------------------------------------------------------
function rng(seed) {
  let a = (typeof seed === 'string' ? [...seed].reduce((h, c) => Math.imul(h ^ c.charCodeAt(0), 16777619), 2166136261) : seed) >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}
const clamp = (v, a = 0, b = 1) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, p) => a + (b - a) * p;
const mtof = (m) => 440 * Math.pow(2, (m - 69) / 12);
const db = (d) => Math.pow(10, d / 20);
const smooth = (p) => p * p * (3 - 2 * p);
const pcOf = (n) => ((n % 12) + 12) % 12;

// ---------------------------------------------------------------------------
// harmony
// ---------------------------------------------------------------------------
const MODES = {
  major: [0, 2, 4, 5, 7, 9, 11],
  minor: [0, 2, 3, 5, 7, 8, 10],
  dorian: [0, 2, 3, 5, 7, 9, 10],
  lydian: [0, 2, 4, 6, 7, 9, 11],
  mixolydian: [0, 2, 4, 5, 7, 9, 10],
  phrygian: [0, 1, 3, 5, 7, 8, 10],
};
const NOTE = { C: 0, 'C#': 1, Db: 1, D: 2, 'D#': 3, Eb: 3, E: 4, F: 5, 'F#': 6, Gb: 6, G: 7, 'G#': 8, Ab: 8, A: 9, 'A#': 10, Bb: 10, B: 11 };

// MIDI note of scale degree d (0-based, may exceed 6 or go negative) above tonic.
function degree(tonic, mode, d) {
  const sc = MODES[mode];
  const o = Math.floor(d / 7), i = ((d % 7) + 7) % 7;
  return tonic + sc[i] + 12 * o;
}
// Chord on scale degree `root` (0-based) as stacked diatonic thirds.
function chordTones(tonic, mode, root, size = 3) {
  const out = [];
  for (let k = 0; k < size; k++) out.push(degree(tonic, mode, root + 2 * k));
  return out;
}
// Voice a chord inside [lo, hi], as close as possible to the previous voicing.
function voiceLead(pcs, lo, hi, prev) {
  const cands = [];
  const classes = pcs.map(pcOf);
  const build = (startOct, inv) => {
    const rot = classes.slice(inv).concat(classes.slice(0, inv));
    const v = [];
    let last = -Infinity;
    for (const pc of rot) {
      let n = startOct * 12 + pc;
      while (n <= last) n += 12;
      v.push(n);
      last = n;
    }
    return v;
  };
  for (let oct = Math.floor(lo / 12) - 1; oct <= Math.ceil(hi / 12); oct++)
    for (let inv = 0; inv < classes.length; inv++) {
      const v = build(oct, inv);
      if (v[0] >= lo && v[v.length - 1] <= hi) cands.push(v);
    }
  if (!cands.length) return build(Math.floor(lo / 12), 0);
  if (!prev) return cands[Math.floor(cands.length / 2)];
  const cost = (v) => v.reduce((a, n, i) => a + Math.abs(n - (prev[Math.min(i, prev.length - 1)] ?? n)), 0);
  return cands.reduce((b, v) => (cost(v) < cost(b) ? v : b));
}

// ---------------------------------------------------------------------------
// the instruments
// ---------------------------------------------------------------------------
// Each name maps to a General MIDI sound (program, bank) in the SoundFont, the
// bus it mixes into, how loud one note sits in the mix (`role`, dB; sustained
// beds sit lower because chords stack), the loudest `vel` a spec may ask for,
// and the built-in synth voice used when the samples are missing.
const PITCHED = {
  // sustained beds
  pad: { program: 89, bus: 'bed', role: -17, cap: 0.12, sus: true, synth: 'pad', cut: 1500 },          // warm synth pad
  sinepad: { program: 49, bus: 'bed', role: -18, cap: 0.12, sus: true, synth: 'sinepad' },               // soft, slow strings
  strings: { program: 49, bus: 'bed', role: -16, cap: 0.12, sus: true, synth: 'pad' },        // string section
  choir: { program: 52, bus: 'bed', role: -18, cap: 0.12, sus: true, synth: 'sinepad' },                 // "aah" choir
  synthpad: { program: 90, bus: 'bed', role: -17, cap: 0.12, sus: true, synth: 'pad', cut: 1500 },       // bright polysynth pad
  // keys and plucked
  keys: { program: 4, bus: 'keys', role: -13, cap: 0.2, synth: 'keys' },                                 // electric piano
  epiano: { program: 4, bus: 'keys', role: -13, cap: 0.2, synth: 'keys' },
  piano: { program: 0, bus: 'keys', role: -12, cap: 0.2, synth: 'keys' },                                // grand piano
  felt: { program: 0, bank: 8, bus: 'keys', role: -12, cap: 0.2, synth: 'keys' },                        // mellow, intimate piano
  pluck: { program: 24, bus: 'keys', role: -13, cap: 0.2, synth: 'pluck' },                             // nylon guitar
  guitar: { program: 24, bus: 'keys', role: -13, cap: 0.2, synth: 'pluck' },                            // nylon guitar
  acoustic: { program: 25, bus: 'keys', role: -13, cap: 0.2, synth: 'pluck' },                          // steel-string guitar
  harp: { program: 46, bus: 'keys', role: -13, cap: 0.2, synth: 'pluck' },
  koto: { program: 107, bus: 'keys', role: -14, cap: 0.2, synth: 'pluck' },                             // zither (guzheng-like)
  pizz: { program: 45, bus: 'keys', role: -13, cap: 0.2, synth: 'pluck' },                              // pizzicato strings
  bell: { program: 9, bus: 'keys', role: -14, cap: 0.2, synth: 'bell', kinds: true },                    // mallets, by `kind`
  // melodic voices
  lead: { program: 80, bus: 'keys', role: -14, cap: 0.12, synth: 'lead', cut: 2600 },                    // square / saw (`saw`)
  flute: { program: 73, bus: 'keys', role: -13, cap: 0.15, synth: 'lead' },
  shakuhachi: { program: 77, bus: 'keys', role: -14, cap: 0.15, synth: 'lead' },                         // breathy bamboo flute
  violin: { program: 40, bus: 'keys', role: -14, cap: 0.15, synth: 'lead' },
  cello: { program: 42, bus: 'keys', role: -13, cap: 0.15, synth: 'lead', ref: 50 },
  horn: { program: 60, bus: 'keys', role: -14, cap: 0.15, synth: 'lead' },                               // french horns
  brass: { program: 61, bus: 'keys', role: -14, cap: 0.15, synth: 'lead' },                              // brass section
  synthbrass: { program: 62, bus: 'keys', role: -14, cap: 0.15, synth: 'lead' },
  timpani: { program: 47, bus: 'keys', role: -11, cap: 0.3, synth: 'bass', ref: 45 },
  // low end
  bass: { program: 33, bus: 'bed', role: -8, cap: 0.35, synth: 'bass', ref: 40, cut: 600 },             // by `kind`
};
const BELLS = { glock: 9, marimba: 12, kalimba: 108, celesta: 8, vibes: 11, musicbox: 10, xylophone: 13, tubular: 14 };
const BASSES = { finger: 33, picked: 34, upright: 32, fretless: 35, synth: 38, synth2: 39 };
// drums: General MIDI kit note, mix level, reverb send
const DRUMS = {
  kick: { note: 36, role: -4, verb: 0 },
  snare: { note: 38, role: -7, verb: 0.14 },
  clap: { note: 39, role: -8, verb: 0.18 },
  snap: { note: 39, role: -12, verb: 0.2 },
  rim: { note: 37, role: -12, verb: 0.12 },
  hat: { note: 42, role: -16, verb: 0.04 },
  openhat: { note: 46, role: -17, verb: 0.06 },
  shaker: { note: 82, role: -18, verb: 0.05 },
  tamb: { note: 54, role: -17, verb: 0.06 },
  ride: { note: 51, role: -17, verb: 0.08 },
  crash: { note: 49, role: -14, verb: 0.1 },
  tom: { note: 45, role: -8, verb: 0.18 },
  conga: { note: 63, role: -10, verb: 0.1 },
};
export const KITS = { standard: 0, room: 8, power: 16, electronic: 24, '808': 25, jazz: 32, brush: 40, orchestra: 48 };
// tom note by pitch (Hz): low floor tom … high tom
const tomNote = (hz) => (hz < 75 ? 41 : hz < 90 ? 43 : hz < 105 ? 45 : hz < 125 ? 47 : hz < 150 ? 48 : 50);
// MIDI velocity for a hit at fraction x of the instrument's loudest
const midiVel = (x) => Math.round(30 + 97 * Math.pow(clamp(x), 0.8));

// ---------------------------------------------------------------------------
// DSP building blocks (mixing, effects, and the fallback synth)
// ---------------------------------------------------------------------------
function blep(t, dt) {
  if (t < dt) { t /= dt; return t + t - t * t - 1; }
  if (t > 1 - dt) { t = (t - 1) / dt; return t * t + t + t + 1; }
  return 0;
}
// TPT state-variable filter (Zavalishin). mode: 'lp' | 'bp' | 'hp'
function svf() {
  let ic1 = 0, ic2 = 0, g = 0, k = 1, a1 = 0, a2 = 0, a3 = 0;
  return {
    set(fc, q = 0.707) {
      g = Math.tan(Math.PI * clamp(fc, 20, SR * 0.45) / SR);
      k = 1 / q;
      a1 = 1 / (1 + g * (g + k)); a2 = g * a1; a3 = g * a2;
    },
    run(v0, mode = 'lp') {
      const v3 = v0 - ic2, v1 = a1 * ic1 + a2 * v3, v2 = ic2 + a2 * ic1 + a3 * v3;
      ic1 = 2 * v1 - ic1; ic2 = 2 * v2 - ic2;
      return mode === 'lp' ? v2 : mode === 'bp' ? v1 : v0 - k * v1 - v2;
    },
  };
}
function onePole(fc) {
  const a = Math.exp(-TAU * fc / SR);
  let z = 0;
  return (x) => (z = x * (1 - a) + z * a);
}
// pinkish noise (Paul Kellet's economy filter): warmer than white for air and whooshes
function pinkNoise(r) {
  let b0 = 0, b1 = 0, b2 = 0;
  return () => {
    const w = r() * 2 - 1;
    b0 = 0.99765 * b0 + w * 0.099046; b1 = 0.963 * b1 + w * 0.2965164; b2 = 0.57 * b2 + w * 1.0526913;
    return (b0 + b1 + b2 + w * 0.1848) * 0.25;
  };
}

// A stereo bus with an optional reverb send.
function bus(n) { return { L: new Float32Array(n), R: new Float32Array(n) }; }

class Mixer {
  constructor(n) {
    this.n = n;
    this.bed = bus(n); this.keys = bus(n); this.drums = bus(n); this.lead = bus(n); this.sfx = bus(n);
    this.verb = new Float32Array(n);  // mono send → stereo reverb
    this.echo = new Float32Array(n);  // mono send → ping-pong delay
    this.susE = new Float64Array(Math.ceil(n / BLK) + 1); // energy of sustained parts per block (sampled engine)
  }
  // add sample v at index i to bus b, equal-power pan (-1..1), sends
  put(b, i, v, pan = 0, verb = 0, echo = 0) {
    if (i < 0 || i >= this.n) return;
    const a = (pan + 1) * Math.PI / 4;
    b.L[i] += v * Math.cos(a) * 1.4142;
    b.R[i] += v * Math.sin(a) * 1.4142;
    if (verb) this.verb[i] += v * verb;
    if (echo) this.echo[i] += v * echo;
  }
}

// --- the fallback synth: each renders one note into a bus ----------------------
const I = {
  // Warm analog pad: 3 detuned band-limited saws → resonant low-pass.
  pad(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const att = o.attack ?? 0.6, rel = o.release ?? 1.2, vel = o.vel ?? 0.12;
    const len = Math.round((dur + rel) * SR);
    const det = [-0.08, 0, 0.09], ph = [0.13, 0.57, 0.81].map((x) => (x + note * 0.07) % 1);
    const flt = svf(), cut0 = (o.cutoff ?? 1400) * 1.2;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      if ((j & 31) === 0) flt.set(cut0 * (1 + 0.1 * Math.sin(TAU * 0.13 * (t0 + t))), 0.7);
      let s = 0;
      for (let v = 0; v < 3; v++) {
        const dt = (f * Math.pow(2, det[v] / 12)) / SR;
        ph[v] += dt; if (ph[v] >= 1) ph[v] -= 1;
        s += 2 * ph[v] - 1 - blep(ph[v], dt);
      }
      const env = (t < att ? smooth(t / att) : 1) * (t > dur ? Math.exp(-(t - dur) / (rel / 3)) : 1);
      m.put(b, n0 + j, flt.run(s / 3) * env * vel, o.pan ?? 0, o.verb ?? 0.25);
    }
  },
  // Soft organ-ish pad from sines. The vibrato is a phase accumulator: a
  // frequency multiplied into `f·t` would drift further every second.
  sinepad(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const att = o.attack ?? 1.2, rel = o.release ?? 2, vel = o.vel ?? 0.1;
    const len = Math.round((dur + rel) * SR);
    const parts = [[1, 1], [2, 0.32], [3, 0.12], [4, 0.06]];
    let ph = 0;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      ph += (f * (1 + 0.0012 * Math.sin(TAU * 4.8 * t + note))) / SR;
      let s = 0;
      for (const [h, a] of parts) s += Math.sin(TAU * h * ph) * a;
      const env = (t < att ? smooth(t / att) : 1) * (t > dur ? Math.exp(-(t - dur) / (rel / 3)) : 1);
      m.put(b, n0 + j, s * 0.6 * env * vel, o.pan ?? 0, o.verb ?? 0.3);
    }
  },
  // FM electric piano (DX-style tine): ratio 1 modulator + bright tine partial.
  keys(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const vel = o.vel ?? 0.16, rel = 0.35, len = Math.round((Math.min(dur, 3.5) + rel) * SR);
    const idx0 = (o.bright ?? 0.6) * 3;
    const tine = f * 14 < SR * 0.4 ? 0.3 : 0; // no tine above Nyquist
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      const idx = idx0 * Math.exp(-t / 0.35) + 0.25;
      const mod = Math.sin(TAU * f * t) * idx;
      let s = Math.sin(TAU * f * t + mod);
      s += tine * Math.sin(TAU * f * 14 * t) * Math.exp(-t / 0.04);
      s += 0.12 * Math.sin(TAU * f * 2 * t + mod * 0.5) * Math.exp(-t / 0.5);
      const env = Math.min(1, t / 0.004) * Math.exp(-t / (o.decay ?? 1.4)) * (t > dur ? Math.exp(-(t - dur) / 0.08) : 1);
      m.put(b, n0 + j, s * env * vel, o.pan ?? 0, o.verb ?? 0.2, o.echo ?? 0);
    }
  },
  // Karplus–Strong plucked string. The loop's averaging filter adds half a
  // sample of delay, so the line is half a sample shorter (in tune up high).
  pluck(m, b, t0, dur, note, o = {}, r) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const N = SR / f - 0.5, size = Math.ceil(N) + 2;
    const buf = new Float32Array(size);
    const bright = o.bright ?? 0.5;
    let lp = 0;
    for (let i = 0; i < size; i++) { const x = r() * 2 - 1; lp = lp + (x - lp) * (0.25 + bright * 0.7); buf[i] = lp; }
    const decay = o.decay != null && o.decay > 0.9 ? o.decay : 0.996, vel = o.vel ?? 0.2;
    const len = Math.round(Math.min(dur + 0.25, o.ring ?? 3) * SR);
    let w = 0, prev = 0;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      const rp = w - N + size * 4;
      const i0 = Math.floor(rp) % size, fr = rp - Math.floor(rp);
      const y = buf[i0] * (1 - fr) + buf[(i0 + 1) % size] * fr;
      const nv = decay * (0.5 * (y + prev));
      prev = y;
      buf[w % size] = nv;
      w++;
      const env = Math.min(1, t / 0.002) * (t > dur ? Math.exp(-(t - dur) / 0.07) : 1);
      m.put(b, n0 + j, y * env * vel * 5, o.pan ?? 0, o.verb ?? 0.2, o.echo ?? 0);
    }
  },
  // Modal percussion: glockenspiel, marimba, kalimba, celesta.
  bell(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const modes = {
      glock: [[1, 1, 1.4], [2.76, 0.32, 0.5], [5.4, 0.12, 0.2], [8.93, 0.05, 0.1]],
      marimba: [[1, 1, 0.55], [3.93, 0.18, 0.09], [9.54, 0.05, 0.03]],
      kalimba: [[1, 1, 0.9], [5.87, 0.16, 0.12], [9.1, 0.04, 0.05]],
      celesta: [[1, 1, 1.0], [2, 0.25, 0.4], [3.01, 0.1, 0.2], [4.2, 0.04, 0.1]],
    }[o.kind] || [[1, 1, 1.4], [2.76, 0.32, 0.5], [5.4, 0.12, 0.2]];
    const vel = o.vel ?? 0.14, len = Math.round(Math.min(4, modes[0][2] * 5) * SR);
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      let s = 0;
      for (const [r, a, d] of modes) if (f * r < SR * 0.45) s += Math.sin(TAU * f * r * t) * a * Math.exp(-t / d);
      m.put(b, n0 + j, s * Math.min(1, t / 0.0015) * vel, o.pan ?? 0, o.verb ?? 0.3, o.echo ?? 0);
    }
  },
  // Bass: sine + saturated 2nd/3rd harmonics, or a filtered saw (synth).
  bass(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const vel = o.vel ?? 0.32, rel = o.release ?? 0.08, len = Math.round((dur + rel) * SR);
    const flt = svf();
    let ph = 0;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      let s;
      if (o.synth) {
        const dt = f / SR;
        ph += dt; if (ph >= 1) ph -= 1;
        if ((j & 15) === 0) flt.set(lerp(o.cutoff ?? 300, (o.cutoff ?? 300) * 6, Math.exp(-t / (o.envDecay ?? 0.12))), 1.4);
        s = flt.run(2 * ph - 1 - blep(ph, dt)) * 0.9;
      } else {
        s = Math.tanh(1.6 * (Math.sin(TAU * f * t) + 0.25 * Math.sin(TAU * 2 * f * t))) * 0.75;
        s += 0.12 * Math.sin(TAU * 3 * f * t) * Math.exp(-t / 0.08);
      }
      const env = Math.min(1, t / 0.006) * Math.exp(-t / (o.decay ?? 2.5)) * (t > dur ? Math.exp(-(t - dur) / (rel / 3)) : 1);
      m.put(b, n0 + j, s * env * vel * 0.55, 0, 0.02);
    }
  },
  // Lead: soft square/saw voice with delayed vibrato.
  lead(m, b, t0, dur, note, o = {}) {
    const f = mtof(note), n0 = Math.round(t0 * SR);
    const vel = o.vel ?? 0.09, rel = 0.25, len = Math.round((dur + rel) * SR);
    const flt = svf();
    flt.set(o.cutoff ?? 2600, 0.9);
    let ph = 0;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      const vib = 1 + 0.003 * Math.sin(TAU * 5.2 * t) * clamp((t - 0.18) / 0.3);
      const dt = (f * vib) / SR;
      ph += dt; if (ph >= 1) ph -= 1;
      const saw = 2 * ph - 1 - blep(ph, dt);
      const sq = (ph < 0.5 ? 1 : -1) + blep(ph, dt) - blep((ph + 0.5) % 1, dt);
      const s = flt.run(lerp(sq, saw, o.saw ?? 0.4));
      const env = Math.min(1, t / 0.02) * (t > dur ? Math.exp(-(t - dur) / 0.08) : 1);
      m.put(b, n0 + j, s * env * vel, o.pan ?? 0, o.verb ?? 0.2, o.echo ?? 0.3);
    }
  },
};

const D = {
  kick(m, t0, o = {}) {
    const n0 = Math.round(t0 * SR), vel = o.vel ?? 0.7, len = Math.round(0.5 * SR);
    const f0 = o.f0 ?? 120, f1 = o.f1 ?? 46;
    let ph = 0;
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      const f = f1 + (f0 - f1) * Math.exp(-t / 0.03);
      ph += f / SR;
      let s = Math.sin(TAU * ph) * Math.exp(-t / (o.decay ?? 0.28));
      s += (j < 120 ? (1 - j / 120) * 0.25 * Math.sin(j * 1.7) : 0);
      m.put(o.bus || m.drums, n0 + j, Math.tanh(s * 1.4) * vel * 0.7, 0, 0);
    }
  },
  // generic noise hit: hat / shaker / snare body / clap
  noise(m, t0, o, r) {
    const n0 = Math.round(t0 * SR), len = Math.round((o.len ?? 0.2) * SR);
    const flt = svf();
    flt.set(o.fc ?? 7000, o.q ?? 0.8);
    for (let j = 0; j < len; j++) {
      const t = j / SR;
      let env = Math.exp(-t / (o.decay ?? 0.04)) * Math.min(1, t / (o.attack ?? 0.0008));
      if (o.clap) {
        const k = Math.floor(t / 0.011);
        env = k < 3 ? Math.exp(-(t - k * 0.011) / 0.004) : Math.exp(-(t - 0.033) / (o.decay ?? 0.11));
      }
      const v = flt.run(r() * 2 - 1, o.mode ?? 'hp') * env * (o.vel ?? 0.1);
      m.put(o.bus || m.drums, n0 + j, v, o.pan ?? 0, o.verb ?? 0.05);
    }
  },
  hat(m, t0, o = {}, r) { D.noise(m, t0, { fc: 7500, decay: o.open ? 0.18 : 0.03, len: o.open ? 0.4 : 0.08, vel: (o.vel ?? 0.07) * 2.4, pan: o.pan ?? 0.25, verb: 0.04 }, r); },
  shaker(m, t0, o = {}, r) { D.noise(m, t0, { fc: 6000, q: 0.9, mode: 'bp', attack: 0.012, decay: 0.04, len: 0.1, vel: (o.vel ?? 0.06) * 2.6, pan: o.pan ?? -0.3, verb: 0.05 }, r); },
  clap(m, t0, o = {}, r) { D.noise(m, t0, { fc: 1300, q: 1.1, mode: 'bp', clap: true, decay: o.decay ?? 0.12, len: 0.35, vel: o.vel ?? 0.28, verb: o.verb ?? 0.22 }, r); },
  snap(m, t0, o = {}, r) { D.noise(m, t0, { fc: 2600, q: 1.6, mode: 'bp', decay: 0.03, len: 0.1, vel: o.vel ?? 0.2, verb: 0.25, pan: 0.2 }, r); },
  snare(m, t0, o = {}, r) {
    D.noise(m, t0, { fc: 2200, q: 0.7, mode: 'bp', decay: o.decay ?? 0.14, len: 0.4, vel: (o.vel ?? 0.3), verb: o.verb ?? 0.25 }, r);
    const n0 = Math.round(t0 * SR), len = Math.round(0.12 * SR);
    for (let j = 0; j < len; j++) { const t = j / SR; m.put(m.drums, n0 + j, Math.sin(TAU * 185 * t) * Math.exp(-t / 0.04) * (o.vel ?? 0.3) * 0.6, 0, 0.1); }
  },
  rim(m, t0, o = {}) {
    const n0 = Math.round(t0 * SR), len = Math.round(0.05 * SR);
    for (let j = 0; j < len; j++) { const t = j / SR; m.put(m.drums, n0 + j, (Math.sin(TAU * 820 * t) * 0.6 + Math.sin(TAU * 1650 * t) * 0.4) * Math.exp(-t / 0.012) * (o.vel ?? 0.12), 0.1, 0.12); }
  },
  tom(m, t0, o = {}) {
    const n0 = Math.round(t0 * SR), len = Math.round(0.9 * SR), f0 = o.f ?? 90, vel = o.vel ?? 0.45;
    let ph = 0;
    for (let j = 0; j < len; j++) { const t = j / SR; ph += (f0 * (1 + 0.5 * Math.exp(-t / 0.05))) / SR; m.put(m.drums, n0 + j, Math.tanh(Math.sin(TAU * ph) * 1.5) * Math.exp(-t / 0.35) * vel, o.pan ?? 0, 0.3); }
  },
  crash(m, t0, o = {}, r) { D.noise(m, t0, { bus: o.bus, fc: 5200, q: 0.5, decay: o.decay ?? 0.9, len: 2.2, vel: o.vel ?? 0.07, attack: 0.002, verb: 0.2, pan: 0.15 }, r); },
};
D.openhat = (m, t0, o, r) => D.hat(m, t0, { ...o, open: true }, r);
D.tamb = (m, t0, o, r) => D.shaker(m, t0, o, r);
D.ride = (m, t0, o = {}, r) => D.noise(m, t0, { fc: 6500, q: 1.2, mode: 'bp', decay: 0.3, len: 0.6, vel: (o.vel ?? 0.06) * 1.6, pan: -0.2, verb: 0.08 }, r);
D.conga = (m, t0, o = {}) => D.tom(m, t0, { ...o, f: 210 });

// ---------------------------------------------------------------------------
// the orchestra: where notes go (the SoundFont sampler, or the fallback synth)
// ---------------------------------------------------------------------------
// The arranger speaks to it in the spec's terms: an instrument name, a time,
// a length, a MIDI note and a `vel` on the spec's scale (0 … the cap).
// The piano, the strings, the harp play from multi-sampled recordings
// (scripts/samples.mjs) unless `multi` is false; a part whose samples can't be
// fetched falls back to the SoundFont and the report says so.
function sampledOrchestra(sf, m, n, kit, { multi = true, log } = {}) {
  const S = new Sampler(sf, SR);
  const tracks = new Map(); // id → { tr, bus, gain, pan, verb, echo, sus, lastCut } (+ bank, notes for a multi-sampled part)
  const patchOf = (inst, o) => {
    const P = PITCHED[inst];
    if (inst === 'bell') return { program: BELLS[o.kind] ?? 9 };
    if (inst === 'bass') return { program: BASSES[o.kind ?? (o.synth ? 'synth' : 'finger')] ?? 33 };
    if (inst === 'lead') return { program: (o.saw ?? 0.4) >= 0.5 ? 81 : 80 };
    return { program: P.program, bank: P.bank ?? 0 };
  };
  const refNote = (inst, o) => PITCHED[inst].ref ?? (inst === 'bell' ? 76 : 64);
  const sendOf = (v, d) => (v == null ? d : Array.isArray(v) ? (v[0] + v[1]) / 2 : v);
  const track = (id, inst, o, busName) => {
    if (tracks.has(id)) return tracks.get(id);
    const P = PITCHED[inst];
    const patch = patchOf(inst, o), cc = {};
    if (o.attack != null) cc[73] = 64 + 16 * Math.log2(Math.max(0.02, o.attack) / 0.25);
    if (o.release != null) cc[72] = 64 + 16 * Math.log2(Math.max(0.05, o.release) / 1.0);
    const bank = multi && !o.kind ? Multi.MULTI[inst] : null;
    if (bank) {
      const t = {
        bank, inst, patch, cc, notes: [], sus: !!P.sus, bus: busName ?? P.bus, ref: refNote(inst, o),
        attack: o.attack ?? (inst === 'sinepad' ? 0.3 : undefined), release: o.release,
        pan: o.pan ?? 0,
        verb: sendOf(o.verb, P.sus ? 0.22 : 0.15),
        echo: sendOf(o.echo, 0),
      };
      tracks.set(id, t);
      return t;
    }
    const tr = S.track(patch, cc);
    const t = {
      tr, sus: !!P.sus, bus: busName ?? P.bus,
      gain: db(P.role) / S.loudness(patch, refNote(inst, o)),
      pan: o.pan ?? 0,
      verb: sendOf(o.verb, P.sus ? 0.22 : inst === 'bass' ? 0.02 : inst === 'bell' ? 0.22 : 0.15),
      echo: sendOf(o.echo, 0),
      lastCut: null,
    };
    tracks.set(id, t);
    return t;
  };
  // brightness (CC 74) from `bright` 0..1 or a `cutoff` in Hz, which may follow the energy
  const brightness = (inst, o) => {
    if (o.bright != null) return 40 + 56 * clamp(o.bright);
    if (o.cutoff != null && PITCHED[inst].cut) return clamp(64 + 14 * Math.log2(o.cutoff / PITCHED[inst].cut), 36, 110);
    return null;
  };
  const drumTrack = (name, busName = 'drums', kitNo = kit) => {
    const id = `drums:${busName}:${kitNo}:${name}`;
    if (tracks.has(id)) return tracks.get(id);
    const d = DRUMS[name], note = d.note;
    const tr = S.track({ kit: kitNo });
    const t = { tr, bus: busName, gain: db(d.role) / S.loudness({ kit: kitNo }, note), pan: name === 'hat' || name === 'openhat' ? 0.2 : name === 'shaker' || name === 'tamb' ? -0.3 : name === 'ride' ? -0.15 : 0, verb: d.verb, echo: 0 };
    tracks.set(id, t);
    return t;
  };
  return {
    kind: 'samples',
    note(id, inst, t0, dur, midi, vel, o = {}, busName) {
      const T = track(id, inst, o, busName), P = PITCHED[inst];
      const cut = brightness(inst, o);
      if (o.decay != null && o.decay > 0 && o.decay < 8 && (inst === 'keys' || inst === 'epiano' || inst === 'piano' || inst === 'felt')) dur = Math.min(dur, o.decay * 2);
      if (T.bank) {
        if (dur > 0 && vel > 0) T.notes.push({ t: t0, dur, midi: Math.round(midi), vel: midiVel(vel / P.cap), bright: cut == null ? undefined : clamp((cut - 40) / 56) });
        return;
      }
      if (cut != null && (T.lastCut == null || Math.abs(cut - T.lastCut) >= 2)) { S.cc(T.tr, Math.max(0, t0 - 0.004), 74, cut); T.lastCut = cut; }
      S.note(T.tr, t0, dur, midi, midiVel(vel / P.cap));
    },
    drum(name, t0, vel, o = {}) {
      const T = drumTrack(name, o.bus ?? 'drums', o.kit ?? kit);
      const note = name === 'tom' ? tomNote(o.pitch ?? 90) : DRUMS[name].note;
      S.note(T.tr, t0, name === 'crash' || name === 'openhat' || name === 'ride' ? 1.5 : 0.25, note, midiVel(vel / (LIMITS.vel[name] ?? 0.5)));
    },
    // one cymbal, reversed, so it swells *into* time t (risers, soft swells)
    reverseCymbal(len) {
      const tr = { patch: { kit: KITS.standard }, cc: {}, notes: [{ t: 0, dur: len, midi: 57, vel: 112 }], ccs: [] };
      const { L, R } = S.render(tr, Math.round((len + 0.5) * SR));
      return { L: L.reverse(), R: R.reverse() };
    },
    // → warnings (a multi-sampled part that fell back to the SoundFont)
    render() {
      const warnings = [];
      for (const T of tracks.values()) {
        if (T.bank) {
          const ready = T.notes.length ? Multi.prepare(T.bank, T.notes, { log }) : { ok: true };
          // as loud over time as the SoundFont instrument it replaces (the
          // roles were balanced on those): compared on three notes around the reference
          const refs = [T.ref - 12, T.ref, T.ref + 12];
          const mine = ready.ok && refs.map((x) => Multi.loudness(T.bank, x, { mean: true }));
          if (ready.ok && mine.every((x) => x)) {
            const ratio = Math.exp(refs.reduce((acc, x, i) => acc + Math.log(S.loudness(T.patch, x, {}, { mean: true }) / mine[i]), 0) / refs.length);
            T.gain = db(PITCHED[T.inst].role) / S.loudness(T.patch, T.ref) * ratio;
            T.out = Multi.renderNotes(T.bank, T.sus ? tieNotes(T.notes) : T.notes, n, { attack: T.attack, release: T.release });
          } else {
            warnings.push(`${T.inst}: its recorded samples could not be loaded, so the SoundFont plays it (${ready.error || 'no reference note'})`);
            T.tr = S.track(T.patch, T.cc);
            for (const nt of T.notes) S.note(T.tr, nt.t, nt.dur, nt.midi, nt.vel);
            T.gain = db(PITCHED[T.inst].role) / S.loudness(T.patch, T.ref);
          }
        }
        const { L, R } = T.out ?? S.render(T.tr, n, { tie: T.sus });
        const b = m[T.bus];
        if (T.sus && T.bus !== 'sfx') { // for the listening checks: how much of the music is held notes
          const g2 = T.gain * T.gain;
          for (let i = 0; i < n; i++) if (L[i] || R[i]) m.susE[(i / BLK) | 0] += (L[i] * L[i] + R[i] * R[i]) * g2;
        }
        const a = (T.pan + 1) * Math.PI / 4, gl = Math.cos(a) * 1.4142 * T.gain, gr = Math.sin(a) * 1.4142 * T.gain;
        const vs = T.verb * T.gain, es = T.echo * T.gain;
        for (let i = 0; i < n; i++) {
          const l = L[i], r = R[i];
          if (l === 0 && r === 0) continue;
          b.L[i] += l * gl; b.R[i] += r * gr;
          if (vs) m.verb[i] += (l + r) * 0.5 * vs;
          if (es) m.echo[i] += (l + r) * 0.5 * es;
        }
      }
      return [...new Set(warnings)];
    },
  };
}

// a held pad repeats the same pitch bar after bar: tie it so it doesn't re-attack
function tieNotes(notes) {
  const out = [], open = new Map();
  for (const nt of notes.slice().sort((a, b) => a.t - b.t || a.midi - b.midi)) {
    const prev = open.get(nt.midi);
    if (prev && Math.abs(prev.t + prev.dur - nt.t) < 0.03) { prev.dur = nt.t + nt.dur - prev.t; continue; }
    const c = { ...nt };
    open.set(nt.midi, c);
    out.push(c);
  }
  return out;
}

function synthOrchestra(m, R) {
  const fold = { synth: (inst) => PITCHED[inst].synth };
  return {
    kind: 'synth',
    note(id, inst, t0, dur, midi, vel, o = {}, busName) {
      const P = PITCHED[inst], s = fold.synth(inst);
      const b = m[busName ?? P.bus];
      // the synth voices were tuned to their own vel scale: map through the caps
      const v = vel / P.cap * (LIMITS.vel[s] ?? P.cap);
      const args = { ...o, vel: v, pan: o.pan ?? o.spread ?? 0 };
      if (s === 'pluck') I.pluck(m, b, t0, dur, midi, args, R);
      else I[s](m, b, t0, dur, midi, args);
    },
    drum(name, t0, vel, o = {}) {
      const args = { vel, bus: o.bus ? m[o.bus] : undefined };
      if (name === 'tom') D.tom(m, t0, { ...args, f: o.pitch ?? 90 });
      else if (name === 'crash') D.crash(m, t0, { ...args, vel: vel * 0.5 }, R);
      else D[name](m, t0, args, R);
    },
    reverseCymbal: null,
    render() {},
  };
}

// ---------------------------------------------------------------------------
// sound effects
// ---------------------------------------------------------------------------
// Small physical sounds (a tick, a card, a glass) are real recordings in
// assets/sfx (Kenney, CC0): a few takes of each, picked in turn with a little
// change of pitch and level so a repeated sound never sounds copied. They all
// send to the score's one reverb, so they sit in the same room as the music.
const SFX_DIR = fileURLToPath(new URL('../assets/sfx/', import.meta.url));
const takes = new Map(); // type → Float32Array[]
function takesOf(type) {
  if (!takes.has(type)) {
    let list = [];
    try {
      const dir = path.join(SFX_DIR, type);
      list = fs.readdirSync(dir).filter((f) => f.endsWith('.wav')).sort((a, b) => parseInt(a) - parseInt(b))
        .map((f) => Multi.readWav(fs.readFileSync(path.join(dir, f))).ch[0]);
    } catch { /* missing: the caller falls back */ }
    takes.set(type, list);
  }
  return takes.get(type);
}
function recorded(m, type, e, r, { level, verb = 0.06, pan = 0, spread = 0.25, pitch = 0.04, at = 0 }) {
  const list = takesOf(type);
  if (!list.length) return false;
  m.lastTake ??= {};
  let k = Math.floor(r() * list.length);
  if (list.length > 1 && k === m.lastTake[type]) k = (k + 1) % list.length;
  m.lastTake[type] = k;
  const x = list[k], rate = 2 ** ((e.semi ?? 0) / 12) * (1 + (r() * 2 - 1) * (e.semi != null ? pitch / 4 : pitch)), g = level * (e.gain ?? 1) * db((r() * 2 - 1) * 1.5);
  const p = e.pan ?? clamp(pan + (r() * 2 - 1) * spread, -1, 1);
  const n0 = Math.round((e.t + at) * SR), len = Math.floor((x.length - 2) / rate);
  for (let j = 0; j < len; j++) { const q = j * rate, i = q | 0, f = q - i; m.put(m.sfx, n0 + j, (x[i] + (x[i + 1] - x[i]) * f) * g, p, verb); }
  return true;
}
// type → how loud, how much room, where it sits
const RECORDED = {
  tick: { level: 0.36, verb: 0.04, pan: 0.1, spread: 0.1 },        // a small mechanical tick (word-synced text, counters)
  click: { level: 0.28, verb: 0.04, spread: 0.1 },                // a button / mouse click
  type: { level: 0.36, verb: 0.03, spread: 0.2, pitch: 0.06 },    // a key press
  pop: { level: 0.34, verb: 0.08 },                               // a small light object set down: a soft clack
  paper: { level: 0.3, verb: 0.06, pitch: 0.03, at: -0.08 },               // a page turning, a sheet sliding
  card: { level: 0.3, verb: 0.06 },                               // a card laid on a table
  book: { level: 0.34, verb: 0.08 },                              // a book closed or set down
  cloth: { level: 0.32, verb: 0.05, at: -0.1 },                           // fabric moving (a reveal, a curtain)
  wood: { level: 0.32, verb: 0.1 },                               // a knock on wood
  glass: { level: 0.26, verb: 0.12 },                             // a light glass tap
  metal: { level: 0.24, verb: 0.12 },                             // a light metal tap
  thud: { level: 0.4, verb: 0.1, spread: 0.1 },                   // something solid lands
  step: { level: 0.28, verb: 0.06 },                              // a footstep
};
// `o` is the orchestra (sampled cymbals, timpani, celesta… when available).
const FX = {
  // Air moving past: two bands of pinkish noise sweeping up to the transition
  // midpoint and away, travelling across the stereo field.
  whoosh(m, e, r) {
    const dur = Math.max(0.3, Math.min(1.0, (e.dur ?? 0.6) * 1.1)), pre = dur * 0.6;
    const n0 = Math.round((e.t - pre) * SR), len = Math.round(dur * SR), vel = 0.28 * (e.gain ?? 1);
    const lo = svf(), hi = svf(), noise = pinkNoise(r);
    for (let j = 0; j < len; j++) {
      const x = j / len;
      const sweep = Math.sin(Math.PI * Math.min(1, x * 1.05)) ** 1.4;
      if ((j & 31) === 0) { lo.set(lerp(280, 1000, sweep), 0.9); hi.set(lerp(1000, 5200, sweep), 1.1); } // nothing under ~200 Hz: low air reads as rumble
      const env = x < 0.6 ? Math.pow(x / 0.6, 2.4) : Math.exp(-(x - 0.6) / 0.11);
      const w = noise();
      m.put(m.sfx, n0 + j, (lo.run(w, 'bp') * 0.9 + hi.run(w, 'bp') * 0.5) * env * vel, lerp(-0.6, 0.6, smooth(x)), 0.08);
    }
  },
  swish(m, e, r) { FX.whoosh(m, { ...e, dur: Math.min(0.5, (e.dur ?? 0.4) * 0.8), gain: (e.gain ?? 1) * 0.6 }, r); },
  // Impact: a deep kick and a timpani on the tonic, a crash, and a sub tail.
  hit(m, e, r, h, o) {
    const vel = e.gain ?? 1;
    if (o.kind === 'samples') {
      o.drum('kick', e.t, 0.55 * vel, { bus: 'sfx', kit: KITS.power });
      o.drum('crash', e.t, 0.12 * vel, { bus: 'sfx', kit: KITS.standard });
      o.note('sfx:timpani', 'timpani', e.t, 1.5, 40 + ((pcOf(h.tonic) - 4 + 12) % 12), 0.22 * vel, {}, 'sfx');
    } else {
      D.kick(m, e.t, { vel: 0.65 * vel, f0: 140, f1: 38, decay: 0.55, bus: m.sfx });
      D.noise(m, e.t, { bus: m.sfx, fc: 1800, q: 0.5, mode: 'lp', decay: 0.25, len: 1, vel: 0.12 * vel, verb: 0.5 }, r);
    }
    const n0 = Math.round(e.t * SR), len = Math.round(1.4 * SR);
    let ph = 0;
    for (let j = 0; j < len; j++) { const t = j / SR; ph += (44 + 30 * Math.exp(-t / 0.08)) / SR; m.put(m.sfx, n0 + j, Math.sin(TAU * ph) * Math.min(1, t / 0.004) * Math.exp(-t / 0.45) * 0.14 * vel, 0, 0.05); }
  },
  // A deep drop: a big drum (taiko) and a falling sub.
  boom(m, e, r, h, o) {
    const vel = e.gain ?? 1, n0 = Math.round(e.t * SR), len = Math.round(2.2 * SR);
    if (o.kind === 'samples') o.drum('kick', e.t, 0.6 * vel, { bus: 'sfx', kit: KITS.orchestra });
    let ph = 0;
    for (let j = 0; j < len; j++) { const t = j / SR; ph += (32 + 40 * Math.exp(-t / 0.22)) / SR; m.put(m.sfx, n0 + j, Math.tanh(Math.sin(TAU * ph) * 1.6) * Math.exp(-t / 0.7) * 0.3 * vel, 0, 0.2); }
  },
  // Tension that *ends* exactly at e.t (place it on the hit): a reversed
  // cymbal and a band of noise opening up. No sine sweep: that reads as a siren.
  riser(m, e, r, h, o) {
    const dur = e.dur ?? 1.6, n0 = Math.round((e.t - dur) * SR), len = Math.round(dur * SR), vel = 0.14 * (e.gain ?? 1);
    const f = svf(), noise = pinkNoise(r);
    for (let j = 0; j < len; j++) {
      const x = j / len;
      if ((j & 31) === 0) f.set(lerp(300, 6500, x * x), 1.2);
      const env = Math.pow(x, 2.2) * (x > 0.985 ? (1 - x) / 0.015 : 1);
      m.put(m.sfx, n0 + j, f.run(noise(), 'bp') * env * vel, Math.sin(x * 7) * 0.3, 0.3);
    }
    revCymbal(m, o, e.t, dur, 0.5 * (e.gain ?? 1));
  },
  // A soft reverse swell into the moment (ink, dissolve, gentle reveals).
  swell(m, e, r, h, o) {
    const dur = Math.max(0.6, (e.dur ?? 0.8) * 0.9), t = e.t + (e.dur ?? 0.8) * 0.25;
    if (o.kind === 'samples') { revCymbal(m, o, t, dur, 0.3 * (e.gain ?? 1), 2500); return; }
    FX.riser(m, { ...e, dur, t, gain: (e.gain ?? 1) * 0.5 }, r, h, o);
  },
  tick(m, e, r) {
    if (recorded(m, 'tick', e, r, RECORDED.tick)) return;
    const n0 = Math.round(e.t * SR), len = Math.round(0.035 * SR), vel = 0.15 * (e.gain ?? 1), f = e.freq ?? 2200;
    for (let j = 0; j < len; j++) { const t = j / SR; m.put(m.sfx, n0 + j, (Math.sin(TAU * f * t) + 0.35 * Math.sin(TAU * f * 2.01 * t)) * Math.exp(-t / 0.005) * vel, e.pan ?? 0.1, 0.04); }
  },
  click(m, e, r) { if (!recorded(m, 'click', e, r, RECORDED.click)) FX.tick(m, { ...e, gain: (e.gain ?? 1) * 0.7 }, r); },
  pop(m, e, r) { if (!recorded(m, 'pop', e, r, RECORDED.pop)) FX.tick(m, e, r); },
  // Stuttered, bit-crushed bursts (digital/cyber only).
  glitch(m, e, r) {
    const n0 = Math.round((e.t - 0.06) * SR), len = Math.round(0.22 * SR), vel = 0.12 * (e.gain ?? 1);
    let hold = 0, v = 0;
    for (let j = 0; j < len; j++) {
      if (hold-- <= 0) { v = r() * 2 - 1; hold = 6 + Math.floor(r() * 40); }
      const gate = Math.floor(j / (SR * 0.028)) % 2 === 0 ? 1 : 0.15;
      m.put(m.sfx, n0 + j, v * gate * vel * Math.exp(-j / (SR * 0.12)), (r() - 0.5) * 0.8, 0.05);
    }
  },
  // A quick upward celesta arpeggio of the current chord (light, sparkle).
  shimmer(m, e, r, h, o) {
    const tones = h.chordAt(e.t).map((n) => n + 12);
    tones.concat(tones[0] + 12).forEach((n, i) => o.note('sfx:celesta', 'bell', e.t - 0.12 + i * 0.05, 0.8, n, 0.11 * (e.gain ?? 1), { kind: 'celesta', verb: 0.45 }, 'sfx'));
  },
  // Two bell notes, a fifth then the octave (an end card, a notification).
  chime(m, e, r, h, o) {
    const root = pcOf(h.tonic) + 72;
    o.note('sfx:glock', 'bell', e.t, 1.2, root + 7, 0.12 * (e.gain ?? 1), { kind: 'glock', verb: 0.4 }, 'sfx');
    o.note('sfx:glock', 'bell', e.t + 0.16, 1.4, root + 12, 0.12 * (e.gain ?? 1), { kind: 'glock', verb: 0.4 }, 'sfx');
  },
  // the rest are recordings only (see RECORDED)
  ...Object.fromEntries(['type', 'paper', 'card', 'book', 'cloth', 'wood', 'glass', 'metal', 'thud', 'step'].map((k) => [k, (m, e, r) => { recorded(m, k, e, r, RECORDED[k]); }])),
};
// a reversed cymbal (or, without samples, nothing) whose peak lands at t
function revCymbal(m, o, t, dur, gain, lowpass) {
  if (!o.reverseCymbal) return;
  const c = (o.cymbals ??= new Map());
  const key = Math.round(dur * 10);
  if (!c.has(key)) c.set(key, o.reverseCymbal(Math.max(0.6, dur)));
  const { L, R } = c.get(key);
  const len = Math.min(L.length, Math.round(dur * SR)), off = L.length - len, n0 = Math.round(t * SR) - len;
  const f = lowpass ? [onePole(lowpass), onePole(lowpass)] : null;
  let pk = 1e-9;
  for (let j = 0; j < L.length; j++) pk = Math.max(pk, Math.abs(L[j]));
  const g = gain * 0.5 / pk;
  for (let j = 0; j < len; j++) {
    const x = j / len, env = smooth(x) * (x > 0.985 ? (1 - x) / 0.015 : 1);
    let l = L[off + j] * g * env, r = R[off + j] * g * env;
    if (f) { l = f[0](l); r = f[1](r); }
    const i = n0 + j;
    if (i < 0 || i >= m.n) continue;
    m.sfx.L[i] += l; m.sfx.R[i] += r;
    m.verb[i] += (l + r) * 0.1;
  }
}

// ---------------------------------------------------------------------------
// the score spec — designed by the agent for each video, validated here
// ---------------------------------------------------------------------------
// There are no built-in music styles. Each composition declares its own score,
// designed from the brief (docs/music-spec.md §2), or writes it whole in a
// score module (music.script, docs/music-and-sound.md §2: written scores below):
//
//   music: {
//     bpm: 104, key: 'A', mode: 'major', seed: 7, kit: 'room',
//     progression: [0, 4, 5, 3], sevenths: false, chordBars: 1,
//     layers: [
//       { inst: 'piano', notes: 'chord', pattern: 'X..x..X.', vel: 0.12 },
//       { inst: 'strings', notes: 'chord', pattern: 'X---', vel: 0.07, from: 0.4 },
//       { inst: 'bass', kind: 'finger', notes: ['root', 'fifth'], octave: -1, pattern: 'X..x..X.', vel: 0.28, from: 0.3 },
//       { inst: 'kick', pattern: 'X...X...', vel: 0.5, from: 0.45 },
//       { inst: 'clap', pattern: '..X...X.', vel: 0.2, from: 0.45 },
//     ],
//     lead: { inst: 'bell', kind: 'glock', range: [74, 88], rhythm: 'melodic', vel: 0.1 },
//   }
//
// A pattern covers `bars` bars (default 1) in equal steps: X = hit, x = soft
// hit (0.6), 1–9 = hit at n/9, '-' = hold the previous note one more step,
// '.' = rest; spaces are ignored. A layer plays in bars whose energy is in
// [from, to). Any numeric sound option may be [low, high], set by the energy.
// validateScore() enforces LIMITS; renderScore() refuses a spec with errors.

export const LIMITS = {
  bpm: [60, 150],
  beatsPerBar: [2, 7],
  progressionLength: [1, 8],
  degree: [0, 6],
  chordBars: [1, 2, 4],
  layers: 8,
  patternBars: [1, 2, 4],
  stepsPerBar: 32,
  octave: [-2, 2],
  noteRange: [28, 100], // MIDI, after octave shifts (E1 … E7)
  gate: [0.05, 8],
  swing: [0, 0.5],
  lineBars: 16, // a written line repeats after at most this many bars
  // loudest allowed hit per instrument (the mix is normalised afterwards; these
  // keep one layer from swamping the others)
  vel: {
    ...Object.fromEntries(Object.entries(PITCHED).map(([k, v]) => [k, v.cap])),
    kick: 0.7, snare: 0.35, clap: 0.3, snap: 0.25, rim: 0.2, hat: 0.12, openhat: 0.1, shaker: 0.12, tamb: 0.12, ride: 0.12, crash: 0.15, tom: 0.5, conga: 0.3,
  },
  drumHitsPerBar: 40, // all drum layers together, at full energy
  lead: { vel: 0.15, range: [55, 96], insts: ['keys', 'epiano', 'piano', 'felt', 'bell', 'pluck', 'guitar', 'acoustic', 'harp', 'koto', 'pizz', 'lead', 'flute', 'shakuhachi', 'violin', 'cello', 'horn', 'brass', 'synthbrass'] },
};
export const INSTRUMENTS = {
  pitched: Object.keys(PITCHED),
  drums: Object.keys(DRUMS),
};
export const MODE_NAMES = Object.keys(MODES);
export const BELL_KINDS = Object.keys(BELLS);
export const BASS_KINDS = Object.keys(BASSES);
const SUSTAINED = new Set(Object.keys(PITCHED).filter((k) => PITCHED[k].sus));

// sound options and their allowed ranges (numbers may also be [low, high] by energy)
const OPT_RANGES = {
  cutoff: [80, 8000], attack: [0, 4], release: [0, 6], bright: [0, 1], decay: [0, 8],
  echo: [0, 0.6], verb: [0, 1], strum: [0, 0.1], envDecay: [0.01, 1], saw: [0, 1], pitch: [40, 400],
};
const SAMPLED_OPTS = ['bright', 'attack', 'release', 'echo', 'verb'];
const OPTS_FOR = {
  pad: ['cutoff', 'attack', 'release', 'verb'], sinepad: ['attack', 'release', 'verb'],
  strings: ['attack', 'release', 'bright', 'verb'], choir: ['attack', 'release', 'verb'], synthpad: ['cutoff', 'attack', 'release', 'verb'],
  keys: ['bright', 'decay', 'echo', 'verb', 'release', 'strum'], epiano: ['bright', 'decay', 'echo', 'verb', 'release', 'strum'],
  piano: ['bright', 'decay', 'echo', 'verb', 'release', 'strum'], felt: ['bright', 'decay', 'echo', 'verb', 'release', 'strum'],
  pluck: ['bright', 'decay', 'echo', 'verb', 'strum'], guitar: [...SAMPLED_OPTS, 'strum'], acoustic: [...SAMPLED_OPTS, 'strum'],
  harp: [...SAMPLED_OPTS, 'strum'], koto: [...SAMPLED_OPTS, 'strum'], pizz: [...SAMPLED_OPTS, 'strum'],
  bell: ['kind', 'echo', 'verb'], bass: ['kind', 'synth', 'cutoff', 'envDecay', 'decay', 'release'], lead: ['saw', 'cutoff', 'echo', 'verb'],
  timpani: SAMPLED_OPTS, flute: SAMPLED_OPTS, shakuhachi: SAMPLED_OPTS, violin: SAMPLED_OPTS, cello: SAMPLED_OPTS, horn: SAMPLED_OPTS, brass: SAMPLED_OPTS, synthbrass: SAMPLED_OPTS,
  tom: ['pitch'],
};
const LAYER_KEYS = ['inst', 'pattern', 'line', 'notes', 'octave', 'vel', 'from', 'to', 'bars', 'gate', 'pan', 'name', 'swing'];
const SPEC_KEYS = ['bpm', 'key', 'mode', 'seed', 'progression', 'sevenths', 'chordBars', 'layers', 'lead', 'fills', 'beatsPerBar', 'parts', 'kit', 'swing', 'script'];
// what a part (a chapter of a long score, chosen per scene with `part`) may change
const PART_KEYS = ['key', 'mode', 'progression', 'chordBars', 'sevenths', 'seed', 'lead', 'lines'];
const NOTE_TOKEN = /^(root|third|fifth|seventh|[0-7])([_^]*)$/;

// pattern → { len, events: [{ i, v, len }] }
function parsePattern(p) {
  const s = String(p).replace(/\s+/g, '');
  const events = [];
  for (let i = 0; i < s.length; i++) {
    const c = s[i];
    if (c === '.') continue;
    if (c === '-') { if (!events.length) return { error: `starts with a hold '-'` }; events[events.length - 1].len++; continue; }
    const v = c === 'X' ? 1 : c === 'x' ? 0.6 : /[1-9]/.test(c) ? +c / 9 : null;
    if (v == null) return { error: `has '${c}' (use X x 1-9 - .)` };
    events.push({ i, v, len: 1 });
  }
  return { len: s.length, events };
}

// A written line: notes the composer chose, in beats.
//   'E5:1 D5:.5 C5:1.5 | G4:2 r:2 | [A3 C4 E4]:4@0.8'
// A note is a name with its octave (C4 = middle C; # or b), r is a rest,
// [ … ] a chord; :beats sets the length (it carries over to the next notes
// until changed; 1/3 for triplets), @0.5–1.3 scales the velocity (accents),
// and | checks that a bar is full.
// → { events: [{ b, len, midis, acc }], beats } | { error }
const LINE_TOKEN = /^(r|[A-G](?:#|b)?-?\d|\[[^\]]*\])(?::(\d*\.?\d+(?:\/\d+)?))?(?:@(\d*\.?\d+))?$/;
function noteNumber(name) {
  const m = /^([A-G])(#|b)?(-?\d)$/.exec(name);
  return m ? 12 * (Number(m[3]) + 1) + NOTE[m[1]] + (m[2] === '#' ? 1 : m[2] === 'b' ? -1 : 0) : null;
}
function parseLine(str, beatsPerBar = 4) {
  if (typeof str !== 'string' || !str.trim()) return { error: 'is empty' };
  const toks = str.match(/\[[^\]]*\][^\s|]*|\||[^\s|]+/g) || [];
  const events = [];
  let b = 0, len = 1, lastBar = 0, checks = 0;
  for (const tok of toks) {
    if (tok === '|') {
      checks++;
      const k = (b - lastBar) / beatsPerBar;
      if (Math.abs(k - Math.round(k)) > 1e-6 || k < 0.5) return { error: `the bar before '|' number ${checks} has ${+(b - lastBar).toFixed(3)} beats (a bar holds ${beatsPerBar})` };
      lastBar = b;
      continue;
    }
    const m = LINE_TOKEN.exec(tok);
    if (!m) return { error: `can't read '${tok}' (write notes like E5:1, rests r:2, chords [C4 E4 G4]:2, accents @1.2)` };
    if (m[2] != null) {
      const [x, y] = m[2].split('/').map(Number);
      len = y ? x / y : x;
      if (!(len > 0) || len > 16) return { error: `'${tok}': a length must be more than 0 and at most 16 beats` };
    }
    const acc = m[3] != null ? Number(m[3]) : 1;
    if (!(acc >= 0.3 && acc <= 1.3)) return { error: `'${tok}': @ (velocity scale) must be 0.3–1.3` };
    if (m[1] !== 'r') {
      const names = m[1].startsWith('[') ? m[1].slice(1, -1).trim().split(/[\s,]+/) : [m[1]];
      const midis = names.map(noteNumber);
      if (!names.length || midis.some((x) => x == null)) return { error: `'${tok}': write chord notes with octaves, e.g. [C4 E4 G4]` };
      events.push({ b, len, midis, acc });
    }
    b += len;
  }
  if (!events.length) return { error: 'has no notes' };
  const bars = b / beatsPerBar;
  if (Math.abs(bars - Math.round(bars)) > 1e-6) return { error: `lasts ${+b.toFixed(3)} beats, not a whole number of ${beatsPerBar}-beat bars (pad the end with a rest)` };
  if (Math.round(bars) > LIMITS.lineBars) return { error: `is ${Math.round(bars)} bars long (at most ${LIMITS.lineBars}; it repeats)` };
  return { events, beats: b, bars: Math.round(bars) };
}

const isRange = (v) => Array.isArray(v) && v.length === 2 && v.every((x) => typeof x === 'number' && Number.isFinite(x));
const atEnergy = (v, e) => (Array.isArray(v) ? lerp(v[0], v[1], e) : v);

// → { errors: string[], warnings: string[] }
export function validateScore(spec) {
  const errors = [], warnings = [];
  const err = (m) => errors.push(m), warn = (m) => warnings.push(m);
  if (!spec || typeof spec !== 'object') return { errors: ['music must be an object'], warnings };
  if ('style' in spec) err(`music.style ('${spec.style}') is not supported: there are no preset styles. Write the score for this video (bpm, key, mode, script: 'score.mjs'), see docs/music-and-sound.md`);
  for (const k of Object.keys(spec)) if (!SPEC_KEYS.includes(k) && !['volume', 'duck', 'gap', 'intro', 'ending', 'offset', 'snap', 'voiceOnBeat', 'sfx', 'file', 'style', 'duration', 'fps', 'sections', 'voice'].includes(k)) err(`music.${k} is not a score option`);
  const inRange = (name, v, [a, b]) => { if (typeof v !== 'number' || !Number.isFinite(v) || v < a || v > b) err(`${name} must be a number in ${a}…${b} (got ${JSON.stringify(v)})`); };
  inRange('music.bpm', spec.bpm, LIMITS.bpm);
  if (spec.beatsPerBar != null) inRange('music.beatsPerBar', spec.beatsPerBar, LIMITS.beatsPerBar);
  if (spec.kit != null && !(spec.kit in KITS)) err(`music.kit must be one of ${Object.keys(KITS).join(', ')} (got ${JSON.stringify(spec.kit)})`);
  if (spec.swing != null) inRange('music.swing', spec.swing, LIMITS.swing);
  // layers: [] and no lead = sound effects only (on the beat grid): no harmony needed
  const sfxOnly = Array.isArray(spec.layers) && !spec.layers.length && spec.lead == null;
  const harmony = (at, h, partial) => {
    if (sfxOnly || (partial && h.key == null)) { /* nothing to check */ } else if (!(h.key in NOTE)) err(`${at}.key must be one of ${Object.keys(NOTE).join(' ')} (got ${JSON.stringify(h.key)})`);
    if (!sfxOnly && !(partial && h.mode == null) && !MODE_NAMES.includes(h.mode)) err(`${at}.mode must be one of ${MODE_NAMES.join(', ')} (got ${JSON.stringify(h.mode)})`);
    const prog = h.progression;
    if (sfxOnly || (partial && prog == null)) { /* no chords */ } else if (!Array.isArray(prog) || prog.length < LIMITS.progressionLength[0] || prog.length > LIMITS.progressionLength[1]) err(`${at}.progression must list ${LIMITS.progressionLength.join('–')} scale degrees`);
    else prog.forEach((d, i) => { if (!Number.isInteger(d) || d < LIMITS.degree[0] || d > LIMITS.degree[1]) err(`${at}.progression[${i}] must be a scale degree 0–6 (0 = tonic)`); });
    if (h.chordBars != null && !LIMITS.chordBars.includes(h.chordBars)) err(`${at}.chordBars must be ${LIMITS.chordBars.join(', ')}`);
    if (h.sevenths != null && typeof h.sevenths !== 'boolean') err(`${at}.sevenths must be true or false`);
  };
  // music.script: the composition's own score module writes every note (§ written scores)
  const scripted = spec.script != null;
  if (scripted && (typeof spec.script !== 'string' || !/\.m?js$/.test(spec.script))) err(`music.script must name the score module next to video.html, e.g. 'score.mjs' (got ${JSON.stringify(spec.script)})`);
  if (scripted && ((spec.layers || []).length || spec.lead != null)) err('music.script writes the whole score: remove music.layers and music.lead (or remove music.script)');
  if (scripted && !(spec.key in NOTE)) err(`music.key must be one of ${Object.keys(NOTE).join(' ')} (got ${JSON.stringify(spec.key)}): the sound effects and the checks read it`);
  harmony('music', spec, scripted);

  const kindOk = (at, inst, kind) => {
    if (kind == null) return;
    if (inst === 'bell' && !BELL_KINDS.includes(kind)) err(`${at}.kind must be one of ${BELL_KINDS.join(', ')}`);
    if (inst === 'bass' && !BASS_KINDS.includes(kind)) err(`${at}.kind must be one of ${BASS_KINDS.join(', ')}`);
  };
  // a written line: readable, in range, in the key (a few chromatic notes are fine)
  const scaleOf = (h) => (h.key in NOTE && MODES[h.mode] ? new Set(MODES[h.mode].map((x) => (x + NOTE[h.key]) % 12)) : null);
  const checkLine = (at, line, octave, [lo, hi], h = spec) => {
    const r = parseLine(line, spec.beatsPerBar || 4);
    if (r.error) return err(`${at}.line ${r.error}`);
    const all = r.events.flatMap((e) => e.midis.map((x) => x + 12 * (octave ?? 0)));
    const out = all.filter((x) => x < lo || x > hi);
    if (out.length) err(`${at}.line: notes must be within MIDI ${lo}…${hi} (${out.length} outside, e.g. ${out[0]})`);
    const sc = scaleOf(h);
    if (sc) {
      const off = all.filter((x) => !sc.has(pcOf(x))).length;
      if (off / all.length > 0.25) warn(`${at}.line: ${off} of ${all.length} notes are outside ${h.key} ${h.mode}; check it was written in this key`);
    }
  };
  const layers = spec.layers ?? (scripted ? [] : undefined);
  if (!Array.isArray(layers)) err('music.layers must be an array ([] = sound effects only)');
  else {
    if (layers.length > LIMITS.layers) err(`music.layers: at most ${LIMITS.layers} layers (got ${layers.length}); fewer, clearer parts leave room for the voice`);
    let drumHits = 0;
    layers.forEach((L, li) => {
      const at = `music.layers[${li}]${L?.name ? ` (${L.name})` : ''}`;
      if (!L || typeof L !== 'object') return err(`${at} must be an object`);
      const pitched = INSTRUMENTS.pitched.includes(L.inst), drum = INSTRUMENTS.drums.includes(L.inst);
      if (!pitched && !drum) return err(`${at}.inst must be one of ${[...INSTRUMENTS.pitched, ...INSTRUMENTS.drums].join(', ')} (got ${JSON.stringify(L.inst)})`);
      const allowed = [...LAYER_KEYS, ...(OPTS_FOR[L.inst] || [])];
      for (const k of Object.keys(L)) if (!allowed.includes(k)) err(`${at}.${k} is not an option for ${L.inst} (allowed: ${allowed.join(', ')})`);
      const bars = L.bars ?? 1;
      if (!LIMITS.patternBars.includes(bars)) err(`${at}.bars must be ${LIMITS.patternBars.join(', ')}`);
      if (L.line != null) {
        if (!pitched) err(`${at}.line: ${L.inst} is a drum; write its rhythm as a pattern`);
        if (L.pattern != null || L.notes != null || L.bars != null) err(`${at}: a layer plays either a written \`line\` or a \`pattern\` with \`notes\`, not both`);
        checkLine(at, L.line, L.octave, LIMITS.noteRange);
      } else if (typeof L.pattern !== 'string') err(`${at}.pattern is required (e.g. 'X---' or 'X.x.X.x.'), or write the notes as a \`line\``);
      else {
        const p = parsePattern(L.pattern);
        if (p.error) err(`${at}.pattern ${p.error}`);
        else if (p.len % bars) err(`${at}.pattern has ${p.len} steps, which doesn't divide into ${bars} bar(s)`);
        else if (p.len / bars > LIMITS.stepsPerBar) err(`${at}.pattern: at most ${LIMITS.stepsPerBar} steps per bar`);
        else if (!p.events.length) err(`${at}.pattern has no hits`);
        else if (drum) drumHits += p.events.length / bars;
      }
      const cap = LIMITS.vel[L.inst];
      if (cap != null) {
        const vs = isRange(L.vel) ? L.vel : [L.vel];
        if (vs.some((v) => typeof v !== 'number' || !(v > 0) || v > cap)) err(`${at}.vel must be in (0, ${cap}] for ${L.inst} (got ${JSON.stringify(L.vel)})`);
      }
      for (const k of ['from', 'to']) if (L[k] != null) inRange(`${at}.${k}`, L[k], [0, 1.01]);
      if (L.from != null && L.to != null && L.to <= L.from) err(`${at}: to must be above from`);
      if (L.gate != null) inRange(`${at}.gate`, L.gate, LIMITS.gate);
      if (L.swing != null) inRange(`${at}.swing`, L.swing, LIMITS.swing);
      if (L.pan != null && L.pan !== 'spread') inRange(`${at}.pan`, L.pan, [-1, 1]);
      if (L.octave != null && (!Number.isInteger(L.octave) || L.octave < LIMITS.octave[0] || L.octave > LIMITS.octave[1])) err(`${at}.octave must be an integer ${LIMITS.octave.join('…')}`);
      if (drum && L.notes != null) err(`${at}.notes: ${L.inst} is a drum and has no notes`);
      if (pitched && L.notes != null) {
        const ns = Array.isArray(L.notes) ? L.notes : [L.notes];
        if (!ns.length) err(`${at}.notes is empty`);
        ns.forEach((t) => { if (!(t === 'chord' && !Array.isArray(L.notes)) && !NOTE_TOKEN.test(String(t))) err(`${at}.notes: '${t}' is not a note (use 'chord', root, third, fifth, seventh or a chord-tone index 0–7, with ^ / _ for an octave up / down)`); });
      }
      kindOk(at, L.inst, L.kind);
      if (L.synth != null && typeof L.synth !== 'boolean') err(`${at}.synth must be true or false`);
      for (const k of Object.keys(OPT_RANGES)) if (L[k] != null) {
        const vs = isRange(L[k]) ? L[k] : [L[k]];
        vs.forEach((v) => inRange(`${at}.${k}`, v, OPT_RANGES[k]));
      }
    });
    if (drumHits > LIMITS.drumHitsPerBar) err(`music.layers: ${Math.round(drumHits)} drum hits per bar at full energy (max ${LIMITS.drumHitsPerBar}); thin the patterns`);
    const ok = layers.filter((L) => L && INSTRUMENTS.pitched.includes(L.inst));
    if (layers.length && !ok.some((L) => (L.from ?? 0) <= 0.3 && L.inst !== 'bass')) warn('no harmony plays at low energy (a pad, piano, keys or guitar layer with from ≤ 0.3): quiet scenes will sound empty');
    if (layers.length > 1 && layers.every((L) => (L?.from ?? 0) === 0 && L?.to == null)) warn('every layer plays at every energy: give layers a `from` so the score builds and breathes with the story');
    if (layers.length && layers.every((L) => SUSTAINED.has(L?.inst) || L?.inst === 'bass')) warn('only sustained layers (pads, strings, choir) and bass: nothing articulates the beat, so the score will drone. Add a piano, guitar, mallet or drum pulse');
    const toms = layers.filter((L) => L?.inst === 'tom');
    if (toms.length && toms.every((L) => (L.pitch ?? 90) < 80) && !layers.some((L) => ['kick', 'snare', 'clap', 'hat', 'shaker'].includes(L?.inst))) warn('a low tom as the only pulse reads as a horror-film heartbeat: use a kick/clap groove, or keep the tom for one dramatic moment');
  }
  const checkLead = (at, lead, h = spec) => {
    if (typeof lead !== 'object') return err(`${at} must be an object or null`);
    if (!LIMITS.lead.insts.includes(lead.inst)) err(`${at}.inst must be one of ${LIMITS.lead.insts.join(', ')}`);
    if (lead.line != null) checkLine(at, lead.line, 0, LIMITS.noteRange, h);
    else {
      if (!(lead.rhythm in RHYTHMS)) err(`${at}.rhythm must be one of ${Object.keys(RHYTHMS).join(', ')} (or write the melody as a \`line\`)`);
      if (!isRange(lead.range) || lead.range[0] < LIMITS.lead.range[0] || lead.range[1] > LIMITS.lead.range[1] || lead.range[1] - lead.range[0] < 7) err(`${at}.range must be [low, high] MIDI within ${LIMITS.lead.range.join('…')}, at least 7 semitones wide`);
    }
    if (typeof lead.vel !== 'number' || !(lead.vel > 0) || lead.vel > LIMITS.lead.vel) err(`${at}.vel must be in (0, ${LIMITS.lead.vel}]`);
    const allowed = ['inst', 'range', 'rhythm', 'line', 'vel', ...(OPTS_FOR[lead.inst] || []), 'bright', 'decay'];
    for (const k of Object.keys(lead)) if (!allowed.includes(k)) err(`${at}.${k} is not an option for ${lead.inst}`);
    kindOk(at, lead.inst, lead.kind);
    for (const k of Object.keys(OPT_RANGES)) if (lead[k] != null) inRange(`${at}.${k}`, lead[k], OPT_RANGES[k]);
  };
  if (spec.lead != null) checkLead('music.lead', spec.lead);
  // parts: chapters of a long score. Each may change the harmony and the
  // melody; the layers (the instruments) stay, so the video keeps one sound.
  if (spec.parts != null) {
    if (typeof spec.parts !== 'object' || Array.isArray(spec.parts)) err('music.parts must be an object: { name: { progression, key, mode, chordBars, sevenths, seed, lead } }');
    else for (const [name, part] of Object.entries(spec.parts)) {
      const at = `music.parts.${name}`;
      if (!part || typeof part !== 'object') { err(`${at} must be an object`); continue; }
      for (const k of Object.keys(part)) if (!PART_KEYS.includes(k)) err(`${at}.${k} is not a part option (a part may change ${PART_KEYS.join(', ')}; layers stay the same for the whole video)`);
      harmony(at, part, true);
      if (part.seed != null && !Number.isFinite(part.seed)) err(`${at}.seed must be a number`);
      const h = { key: part.key ?? spec.key, mode: part.mode ?? spec.mode };
      const newHarmony = ['key', 'mode', 'progression'].some((k) => part[k] != null);
      if (part.lead != null) {
        if (!spec.lead) err(`${at}.lead: there is no music.lead to vary (add one, or leave the part's lead out)`);
        else checkLead(`${at}.lead`, { ...spec.lead, ...part.lead }, h);
      }
      if (newHarmony && spec.lead?.line != null && part.lead?.line == null) warn(`${at} changes the harmony but plays music.lead.line, written for the main chords: give it its own lead.line`);
      if (part.lines != null) {
        if (typeof part.lines !== 'object' || Array.isArray(part.lines)) err(`${at}.lines must be { layerName: line }`);
        else for (const [ln, line] of Object.entries(part.lines)) {
          const L = (Array.isArray(layers) ? layers : []).find((x) => x?.name === ln);
          if (!L || L.line == null) err(`${at}.lines.${ln}: no layer named '${ln}' plays a written line`);
          else checkLine(`${at}.lines.${ln}`, line, L.octave, LIMITS.noteRange, h);
        }
      }
      if (newHarmony && Array.isArray(layers)) for (const L of layers) if (L?.line != null && part.lines?.[L.name] == null) warn(`${at} changes the harmony but layer ${L.name ? `'${L.name}'` : L.inst} keeps its written line: give it one in ${at}.lines${L.name ? '' : ' (name the layer first)'}`);
    }
  }
  for (const sec of spec.sections || []) if (sec.part != null && !spec.parts?.[sec.part]) err(`scene "${sec.id}": part '${sec.part}' is not in music.parts (${Object.keys(spec.parts || {}).join(', ') || 'none defined'})`);
  return { errors, warnings };
}

// One layer, one bar: schedule its notes.
function playLayer(a, li, L, P, c, e, bi, b0) {
  const bars = L.bars ?? 1, spb = P.len / bars, step = a.barLen / spb;
  const pos = bi % bars, lo = pos * spb, hi = lo + spb;
  const gate = L.gate ?? (SUSTAINED.has(L.inst) ? 1 : 0.9);
  const base = atEnergy(L.vel, e);
  const opts = {};
  for (const k of OPTS_FOR[L.inst] || []) if (L[k] != null && k !== 'pitch') opts[k] = atEnergy(L[k], e);
  if (typeof L.pan === 'number') opts.pan = L.pan;
  const notes = L.notes == null ? (L.inst === 'bass' ? ['root'] : ['chord']) : Array.isArray(L.notes) ? L.notes : [L.notes];
  const shift = 12 * (L.octave ?? 0);
  const fold = (n) => { while (n < LIMITS.noteRange[0]) n += 12; while (n > LIMITS.noteRange[1]) n -= 12; return n; };
  const pitch = (tok) => {
    const [, name, oct] = String(tok).match(NOTE_TOKEN);
    const v = c.voicing;
    let n = name === 'root' ? c.root : name === 'third' ? c.tones[1] : name === 'fifth' ? c.tones[2]
      : name === 'seventh' ? c.seventh : v[+name % v.length] + 12 * Math.floor(+name / v.length);
    for (const ch of oct) n += ch === '^' ? 12 : -12;
    return fold(n + shift);
  };
  // swing delays every other step when the grid is eighths or sixteenths
  const perBeat = spb / a.beatsPerBar, swing = L.swing ?? a.swing ?? 0;
  const swung = swing && (perBeat === 2 || perBeat === 4);
  const id = `L${li}`;
  P.events.forEach((ev, k) => {
    if (ev.i < lo || ev.i >= hi) return;
    let lt = (ev.i - lo) * step;
    if (swung && (ev.i - lo) % 2 === 1) lt += swing * step;
    const d = ev.len * step * gate, vel = base * ev.v;
    if (INSTRUMENTS.drums.includes(L.inst)) return a.drum(id, L.inst, b0 + lt, vel, { pitch: L.pitch });
    const tok = notes[k % notes.length];
    if (tok === 'chord') return a.chord(id, L.inst, b0 + lt, d, c.voicing.map((n) => fold(n + shift)), vel, opts);
    a.note(id, L.inst, b0 + lt, d, pitch(tok), vel, opts);
  });
}

// One bar of a written line (bar k of the line counted from its part's start):
// the notes that start in it, phrased like a player would: the line's high
// points a little stronger, the downbeats leaning, sustained notes legato.
function playLine(a, id, inst, line, k, b0, { vel, octave = 0, opts = {}, sus = false, gate, phrase = false }) {
  const bpb = a.barLen / a.beat, lb = ((k % line.bars) + line.bars) % line.bars;
  let lo = Infinity, hi = -Infinity;
  for (const ev of line.events) for (const x of ev.midis) { lo = Math.min(lo, x); hi = Math.max(hi, x); }
  for (const ev of line.events) {
    if (Math.floor(ev.b / bpb + 1e-9) !== lb) continue;
    const t = b0 + (ev.b - lb * bpb) * a.beat;
    const top = Math.max(...ev.midis);
    const shape = phrase && hi > lo ? 0.9 + 0.2 * (top - lo) / (hi - lo) : 1;
    const down = Math.abs(ev.b % bpb) < 1e-6 ? 1.06 : Math.abs(ev.b % 1) > 1e-6 ? 0.92 : 1;
    const d = ev.len * a.beat * (gate ?? (sus ? 1 : 0.95));
    ev.midis.forEach((x, i) => a.note(id, inst, t + i * (ev.midis.length > 1 && !sus ? 0.008 : 0), d, x + 12 * octave, vel * ev.acc * shape * down * (i ? 0.92 : 1), opts));
  }
}

// Melody rhythms in beats: [start, length] over two bars (8 beats).
const RHYTHMS = {
  sparse: [[[0, 2], [2.5, 1.5], [4, 3]], [[0.5, 1.5], [2, 2], [5, 2.5]], [[0, 1], [1, 1], [2, 3], [6, 1.5]]],
  melodic: [[[0, 1], [1, 0.5], [1.5, 1.5], [3, 1], [4, 1], [5, 0.5], [5.5, 2]], [[0, 1.5], [1.5, 0.5], [2, 2], [4.5, 0.5], [5, 1], [6, 2]], [[0.5, 0.5], [1, 1], [2, 1], [3, 1], [4, 3]]],
  rhythmic: [[[0, 0.5], [0.75, 0.5], [1.5, 0.5], [2.5, 1], [4, 0.5], [4.75, 0.5], [5.5, 1.5]], [[0, 0.75], [0.75, 0.75], [1.5, 1], [3, 0.5], [3.5, 0.5], [4, 2]]],
};

// A motif: a rhythm and a contour (scale steps above the phrase floor) that
// rises to a peak and settles, so the line has a shape a listener can follow.
function composeMotif(rh, rr) {
  const n = rh.length, peak = clamp(Math.round(n * (0.35 + rr() * 0.3)), 1, Math.max(1, n - 2));
  const top = 3 + Math.floor(rr() * 3), start = Math.floor(rr() * 3);
  return rh.map(([b, len], i) => {
    let d = i <= peak ? start + (top - start) * (i / peak) : top - (top - 1) * ((i - peak) / Math.max(1, n - 1 - peak));
    if (i && i !== peak && i !== n - 1 && rr() < 0.3) d += rr() < 0.5 ? -1 : 1;
    return { b, len, d: Math.round(d) };
  });
}

// ---------------------------------------------------------------------------
// arrangement
// ---------------------------------------------------------------------------
// opts: { voiceDb, targetDb, engine: 'samples' | 'synth', log, trace: [] }
export async function renderScore(plan, opts = {}) {
  const { errors, warnings } = validateScore(plan);
  if (errors.length) throw new Error(`music: the score spec has ${errors.length} problem(s):\n  ${errors.join('\n  ')}`);
  const layers = plan.layers.map((L) => ({ L, P: L.line != null ? null : parsePattern(L.pattern) }));
  const scripted = typeof plan.script === 'string'; // the composition's own score script writes every note (§ written scores)
  const silent = !layers.length && !plan.lead && !scripted; // sound effects only
  if (silent || scripted) plan = { ...plan, key: plan.key || 'C', mode: plan.mode || 'major', progression: plan.progression || [0] }; // harmony for tonal sfx
  const bpm = plan.bpm;
  const beat = 60 / bpm, beatsPerBar = plan.beatsPerBar || 4, barLen = beat * beatsPerBar;
  const offset = plan.offset || 0;
  const duration = plan.duration;
  const n = Math.ceil((duration + 0.05) * SR);
  const m = new Mixer(n);
  const R = rng(`${plan.seed ?? 1}:${plan.key}:${plan.mode}`);
  const human = rng(`${plan.seed ?? 1}:human`);
  const tonic = 48 + NOTE[plan.key];
  const mode = plan.mode;
  const prog = plan.progression, chordBars = plan.chordBars ?? 1, sevenths = !!plan.sevenths;
  const voice = (plan.voice || []).map((v) => [v.start - 0.12, v.end + 0.2]);
  const voicedAt = (t) => voice.some(([a, b]) => t >= a && t < b);
  const sections = plan.sections || [{ start: 0, end: duration, energy: 0.5 }];

  // who plays the notes: the sampled instruments, or the fallback synth
  let orch = null, engineNote = null;
  if (opts.engine !== 'synth') {
    const sf = await loadSoundfont({ log: opts.log });
    if (sf.error) engineNote = `played by the built-in synth, which sounds much cheaper: ${sf.error}`;
    else orch = sampledOrchestra(sf, m, n, KITS[plan.kit ?? 'standard'], { multi: opts.multi !== false && process.env.VIDEO_GAGA_MULTISAMPLE !== '0', log: opts.log });
  }
  orch ??= synthOrchestra(m, R);
  // where the music articulates (note and drum starts), for the listening checks
  const onsets = [];
  {
    const { note, drum } = orch;
    orch.note = (id, inst, t, d, midi, vel, o, b) => { if (b !== 'sfx' && !SUSTAINED.has(inst)) onsets.push(t); note(id, inst, t, d, midi, vel, o, b); };
    orch.drum = (name, t, vel, o = {}) => { if (o.bus !== 'sfx') onsets.push(t); drum(name, t, vel, o); };
  }
  if (opts.trace) { // every note and hit, for tests and debugging
    const { note, drum } = orch;
    orch.note = (id, inst, t, d, midi, vel, o, b) => { opts.trace.push({ id, inst, t, d, midi, vel }); note(id, inst, t, d, midi, vel, o, b); };
    orch.drum = (name, t, vel, o) => { opts.trace.push({ id: 'drum', inst: name, t, vel }); drum(name, t, vel, o); };
  }

  // energy per section: explicit, else an arc (a confident open, a fuller
  // middle, a settled ending); music-only sections lift a little
  const energyOf = (sec, i) => {
    if (sec.energy != null) return clamp(sec.energy);
    const last = i === sections.length - 1;
    const base = i === 0 ? 0.45 : last ? 0.55 : 0.65;
    return clamp(base + (sec.voiced ? 0 : 0.12));
  };
  const secAt = (t) => { let k = 0; sections.forEach((s, i) => { if (t >= s.start - 1e-6) k = i; }); return k; };

  // timeline of bars (bar 0 starts at the grid offset; a pickup before it is silent)
  const nBars = Math.ceil((duration - offset) / barLen) + 1;
  // the final resolution: last downbeat that leaves ≥ 1 s to ring
  const ring = Math.max(1.0, beat * 2);
  let endBar = Math.floor((duration - ring - offset) / barLen + 1e-6);
  if (plan.ending === 'none' || silent) endBar = nBars + 1;
  const endT = offset + endBar * barLen;

  // accents: big hits get a half-beat breath before them
  const hits = (plan.sfx || []).filter((e) => e.type === 'hit' || e.type === 'boom').map((e) => e.t);
  const breathAt = (t) => hits.some((h) => t >= h - beat * 0.5 && t < h - 0.01);

  // parts: a scene's `part` changes the harmony (and the melody) from the bar it
  // starts in; each part's progression starts on its own first chord
  const partHarmony = (name) => {
    const P = name != null ? plan.parts[name] : {};
    const key = P.key ?? plan.key, md = P.mode ?? plan.mode;
    return { tonic: 48 + NOTE[key], mode: md, prog: P.progression ?? prog, chordBars: P.chordBars ?? chordBars, sevenths: P.sevenths ?? sevenths };
  };
  const partAt = (t) => sections[secAt(t)]?.part ?? null;

  // chords per bar, voice-led
  const chords = [];
  let prevV = null, curPart, partBar = 0;
  for (let b = 0; b < nBars; b++) {
    const pn = plan.parts ? partAt(offset + b * barLen + barLen * 0.25) : null;
    if (b === 0 || pn !== curPart) { curPart = pn; partBar = b; }
    const H = partHarmony(pn);
    const deg = H.prog[Math.floor((b - partBar) / H.chordBars) % H.prog.length];
    const pcs = chordTones(H.tonic, H.mode, deg, H.sevenths ? 4 : 3);
    const voicing = voiceLead(pcs, 57, 76, prevV);
    prevV = voicing;
    chords.push({ deg, root: degree(H.tonic, H.mode, deg), seventh: degree(H.tonic, H.mode, deg + 6), voicing, tones: pcs, tonic: H.tonic, mode: H.mode, part: pn, partBar });
  }
  const chordAtT = (t) => chords[clamp(Math.floor((t - offset) / barLen), 0, chords.length - 1)];
  const harmony = { tonic, chordAt: (t) => chordAtT(t).voicing };

  // what the arrangement plays through: gating, humanising, chords
  const ok = (t) => t >= 0 && t < endT - 0.02 && !breathAt(t);
  const feel = (t, tight) => t + (human() - 0.5) * (tight ? 0.006 : 0.014); // a player's timing
  const touch = (v) => v * (0.94 + human() * 0.12);                          // and touch
  const arr = {
    beat, barLen, beatsPerBar, swing: plan.swing ?? 0,
    note(id, inst, t, d, midi, vel, o = {}) { if (ok(t)) orch.note(id, inst, Math.max(0, feel(t)), d, midi, touch(vel), o); },
    chord(id, inst, t, d, ns, vel, o = {}) {
      if (!ok(t)) return;
      const t0 = Math.max(0, feel(t));
      const strum = o.strum ?? (['guitar', 'pluck', 'acoustic', 'harp', 'koto'].includes(inst) ? 0.014 : SUSTAINED.has(inst) ? 0 : 0.006);
      ns.forEach((nn, i) => orch.note(id, inst, t0 + i * strum, d, nn, touch(vel) * (i ? 0.92 : 1), { ...o, spread: ns.length > 1 ? lerp(-0.3, 0.3, i / (ns.length - 1)) : 0 }));
    },
    drum(id, name, t, vel, o = {}) { if (ok(t)) orch.drum(name, Math.max(0, feel(t, true)), touch(vel), o); },
  };

  const lineCache = new Map();
  const lineOf = (str) => { if (!lineCache.has(str)) lineCache.set(str, parseLine(str, beatsPerBar)); return lineCache.get(str); };
  const optsAt = (L, e) => { const o = {}; for (const k of OPTS_FOR[L.inst] || []) if (L[k] != null && k !== 'pitch') o[k] = atEnergy(L[k], e); if (typeof L.pan === 'number') o.pan = L.pan; return o; };

  // --- bars -------------------------------------------------------------------
  const report = { bpm, key: `${plan.key} ${mode}`, progression: prog.join('-'), layers: layers.length, lead: plan.lead?.inst ?? null, engine: orch.kind, bars: [], warnings };
  if (engineNote) warnings.push(engineNote);
  // where each part takes over: "name@bar"
  if (plan.parts) report.parts = chords.filter((c, b) => b < endBar && (b === 0 || c.part !== chords[b - 1].part)).map((c) => `${c.part ?? 'main'}@${chords.indexOf(c) + 1}`);
  // one loop for minutes on end is the most audible problem of a long score
  const loops = Math.min(nBars, endBar) / (prog.length * chordBars);
  if (!plan.parts && !silent && duration > 75 && loops > 8) warnings.push(`${Math.round(duration)} s on one ${prog.length}-chord loop (it repeats ${Math.round(loops)} times): give the chapters their own harmony with music.parts and a \`part\` on each chapter's first scene (docs/music-spec.md §2.5)`);
  const plays = (L, e) => e >= (L.from ?? 0) && e < (L.to ?? 1.01);
  const drumsAt = (e) => layers.some(({ L }) => INSTRUMENTS.drums.includes(L.inst) && plays(L, e));
  for (let b = 0; b < (silent ? 0 : Math.min(nBars, endBar)); b++) {
    const b0 = offset + b * barLen;
    if (b0 >= duration) break;
    const si = secAt(b0 + barLen * 0.25);
    let e = energyOf(sections[si], si);
    if (b === 0 && plan.intro !== 'full') e = Math.min(e, 0.3); // let the first bar breathe in
    layers.forEach(({ L, P }, li) => {
      if (!plays(L, e)) return;
      if (P) return playLayer(arr, li, L, P, chords[b], e, b, b0);
      // a written line, from the start of its part (a part may rewrite it)
      const c = chords[b], line = lineOf(c.part != null ? plan.parts[c.part].lines?.[L.name] ?? L.line : L.line);
      playLine(arr, `L${li}`, L.inst, line, b - c.partBar, b0, { vel: atEnergy(L.vel, e), octave: L.octave, opts: optsAt(L, e), sus: SUSTAINED.has(L.inst), gate: L.gate });
    });
    report.bars.push(Math.round(e * 100) / 100);
    // section changes: a fill into the downbeat and a crash on it, when the
    // energy rises and the score has drums there
    const next = sections[si + 1];
    if (next && e >= 0.5 && plan.fills !== false) {
      const nb = Math.round((next.start - offset) / beat); // beat index of the change (transitions are snapped)
      const ct = offset + nb * beat;
      if (ct > b0 && ct <= b0 + barLen + 1e-6) {
        const ne = energyOf(next, si + 1);
        if (ne >= e - 0.05 && ct < endT - 0.05 && (drumsAt(e) || drumsAt(ne))) {
          arr.drum('fills', 'crash', ct, 0.08 + ne * 0.05);
          const toms = e >= 0.65 ? [50, 48, 47, 45] : null;
          for (let k = 0; k < 4; k++) {
            const t = ct - beat + k * beat / 4;
            if (toms) arr.drum('fills', 'tom', t, 0.22 + k * 0.04, { pitch: [160, 140, 115, 95][k] });
            else arr.drum('fills', 'snare', t, 0.08 + k * 0.035);
          }
        }
      }
    }
  }

  // --- melody in the gaps ---------------------------------------------------------
  const Lm = plan.lead ? { ...plan.lead, opts: Object.fromEntries(Object.entries(plan.lead).filter(([k]) => !['inst', 'range', 'rhythm', 'vel', 'line'].includes(k))) } : null;
  let prevNote = null;
  const written = (Lp) => Lp.line != null;
  const leadOf = (name) => {
    const P = name != null ? plan.parts[name] : null;
    return P?.lead ? { ...Lm, ...P.lead, opts: { ...Lm.opts, ...Object.fromEntries(Object.entries(P.lead).filter(([k]) => !['inst', 'range', 'rhythm', 'vel', 'line'].includes(k))) } } : Lm;
  };
  if (Lm && !silent && [null, ...Object.keys(plan.parts || {})].some((k) => written(leadOf(k)))) {
    // the composer wrote the melody: play it as written, bar by bar from the
    // start of each part, only where nobody is speaking
    for (let b = 0; b < Math.min(nBars, endBar); b++) {
      const c = chords[b], L = leadOf(c.part);
      if (!written(L)) continue;
      const b0 = offset + b * barLen;
      playLine({
        beat, barLen,
        note(id, inst, t, d, midi, vel, o) {
          if (t >= endT - 0.05) return;
          const si = secAt(t);
          if (energyOf(sections[si], si) < 0.3 || voicedAt(t) || voicedAt(t + Math.min(d, 0.6)) || breathAt(t)) return;
          prevNote = midi;
          orch.note(id, inst, Math.max(0, feel(t)), Math.min(d, endT - t), midi, vel * (0.96 + human() * 0.08), o, 'lead');
        },
      }, `lead:${L.inst}:${L.opts.kind ?? ''}`, L.inst, lineOf(L.line), b - c.partBar, b0, { vel: L.vel, opts: { ...(L.opts || {}), pan: 0.12 }, phrase: true });
    }
  } else if (Lm && !silent) {
    // each part gets its own motifs (its own seed and lead options)
    const compose = (Lp, rr) => {
      const set = RHYTHMS[Lp.rhythm];
      const a = Math.floor(rr() * set.length), b = (a + 1 + Math.floor(rr() * (set.length - 1))) % set.length;
      return [composeMotif(set[a], rr), composeMotif(set[b], rr)];
    };
    const leads = new Map([[null, { L: Lm, motifs: compose(Lm, plan.parts ? rng(`${plan.seed ?? 1}:main`) : R) }]]);
    const leadFor = (name) => {
      if (!leads.has(name)) {
        const P = plan.parts[name];
        const Lp = P.lead ? { ...Lm, ...P.lead, opts: { ...Lm.opts, ...Object.fromEntries(Object.entries(P.lead).filter(([k]) => !['inst', 'range', 'rhythm', 'vel'].includes(k))) } } : Lm;
        leads.set(name, { L: Lp, motifs: compose(Lp, rng(`${P.seed ?? plan.seed ?? 1}:${name}`)) });
      }
      return leads.get(name);
    };
    const phrases = Math.ceil(nBars / 2);
    let phPart, ph0 = 0;
    for (let phAbs = 0; phAbs < phrases; phAbs++) {
      const t0 = offset + phAbs * 2 * barLen;
      const pn = chords[clamp(phAbs * 2, 0, chords.length - 1)].part;
      if (phAbs === 0 || pn !== phPart) { phPart = pn; ph0 = phAbs; }
      const ph = phAbs - ph0;
      const { L, motifs } = leadFor(pn);
      // an eight-bar period: A, A (answered), B (contrast), A (home)
      const motif = motifs[ph % 4 === 2 ? 1 : 0];
      motif.forEach((nt, i) => {
        const t = t0 + nt.b * beat;
        if (t >= endT - 0.05 || t < barLen * 0.5) return;
        const si = secAt(t);
        if (energyOf(sections[si], si) < 0.3) return;
        // play only where nobody is talking (with a little air on both sides)
        if (voicedAt(t) || voicedAt(t + Math.min(nt.len * beat, 0.6)) || breathAt(t)) return;
        const c = chordAtT(t);
        const last = i === motif.length - 1;
        // the line lives on the key's scale (so the hook repeats over the
        // changes), floored at the lowest tonic inside the range
        let floor = c.tonic; while (floor < L.range[0]) floor += 12; while (floor - 12 >= L.range[0]) floor -= 12;
        // the answer (2nd phrase) is a sequence: the same shape two steps higher
        let d = nt.d + (ph % 4 === 1 ? (i < motif.length - 1 ? 2 : 1) : 0);
        const at = (dd) => degree(floor, c.mode, dd);
        const pcs = c.tones.map(pcOf);
        const strong = Number.isInteger(nt.b) && (nt.b % 2 === 0 || nt.len >= 1.5);
        let note = at(d);
        if (strong || last || nt.len >= 1) {
          // a chord tone on strong beats, long notes and phrase ends
          for (const step of [0, -1, 1, -2, 2]) if (pcs.includes(pcOf(at(d + step)))) { note = at(d + step); break; }
        }
        if (last && ph % 4 === 3) note = degree(floor, c.mode, 0) + 12 * Math.round((note - degree(floor, c.mode, 0)) / 12); // home at the period's end
        while (note < L.range[0]) note += 12;
        while (note > L.range[1]) note -= 12;
        if (prevNote != null && Math.abs(note - prevNote) > 9) note += note > prevNote ? -12 : 12;
        while (note < L.range[0]) note += 12;
        while (note > L.range[1]) note -= 12;
        prevNote = note;
        const len = Math.min(nt.len * beat * 0.95, endT - t);
        const v = L.vel * (strong ? 1 : 0.85) * (0.94 + human() * 0.12);
        orch.note(`lead:${L.inst}:${L.opts.kind ?? ''}`, L.inst, feel(t), len, note, v, { ...(L.opts || {}), pan: 0.12 }, 'lead');
      });
    }
  }

  // --- ending: the home chord rings out with the last frame, on the score's own instruments ---
  if (endT < duration && !silent) {
    const H = partHarmony(plan.parts ? partAt(endT) : null);
    const v = voiceLead(chordTones(H.tonic, H.mode, 0, H.sevenths ? 4 : 3), 57, 76, prevV);
    const ringFor = duration - endT;
    const lastE = energyOf(sections[sections.length - 1], sections.length - 1);
    let tonal = layers.map(({ L }, li) => ({ L, li })).filter(({ L }) => INSTRUMENTS.pitched.includes(L.inst) && plays(L, lastE));
    if (!tonal.length) tonal = layers.map(({ L }, li) => ({ L, li })).filter(({ L }) => INSTRUMENTS.pitched.includes(L.inst)).slice(0, 1);
    for (const { L, li } of tonal) {
      const shift = 12 * (L.octave ?? 0), vel = atEnergy(L.vel, lastE) * 0.9;
      const o = {};
      for (const k of OPTS_FOR[L.inst] || []) if (L[k] != null && k !== 'pitch') o[k] = atEnergy(L[k], lastE);
      if (L.inst === 'bass') orch.note(`L${li}`, 'bass', endT, ringFor, H.tonic - 12 + (shift < 0 ? -12 : 0), vel, o);
      else v.forEach((nn, i) => orch.note(`L${li}`, L.inst, endT + i * (SUSTAINED.has(L.inst) ? 0 : 0.012), ringFor, nn + shift, vel, o));
    }
    if (drumsAt(lastE)) { orch.drum('kick', endT, 0.4); orch.drum('crash', endT, 0.1); }
  }

  // --- a written score: the composition's score script places every note and sound ---
  const placedFx = [];
  const musicGain = scripted ? new Float32Array(Math.ceil(n / 64) + 2).fill(1) : null; // holes and dips (music only)
  if (scripted) {
    const mod = await import(`${pathToFileURL(plan.script).href}?t=${fs.statSync(plan.script).mtimeMs}`);
    const write = mod.default ?? mod.score;
    if (typeof write !== 'function') throw new Error(`music.script: ${path.basename(plan.script)} must export default function (S) { … } (docs/music-and-sound.md §2)`);
    await write(scoreApi({ plan, orch, m, R, human, harmony, chordAtT, beat, barLen, beatsPerBar, offset, duration, sections, voicedAt, placedFx, musicGain, n }));
    report.script = path.basename(plan.script);
    report.placedSfx = [...(plan.sfx || []), ...placedFx].sort((a, b) => a.t - b.t).map((e) => `${e.type}@${e.t.toFixed(2)}`);
  }

  // --- sound effects ------------------------------------------------------------------
  for (const e of plan.sfx || []) {
    const fn = FX[e.type];
    if (!fn) { report.unknownSfx = (report.unknownSfx || []).concat(e.type); continue; }
    if (e.t < -1 || e.t > duration + 1) continue;
    fn(m, e, R, harmony, orch);
  }

  // the sampled tracks render now, into the buses and the effect sends
  for (const w of orch.render() || []) warnings.push(w);

  // --- effects, ducking, master ----------------------------------------------------
  // ping-pong delay (dotted eighth), fed by the echo send
  {
    const dl = Math.round(beat * 0.75 * SR), fb = 0.32;
    const bl = new Float32Array(dl), br = new Float32Array(dl);
    const lp = onePole(3200), lp2 = onePole(3200);
    for (let i = 0; i < n; i++) {
      const k = i % dl;
      const yl = bl[k], yr = br[k];
      bl[k] = lp(m.echo[i] + yr * fb);
      br[k] = lp2(yl * fb);
      m.lead.L[i] += yl * 0.5; m.lead.R[i] += yr * 0.5;
      m.verb[i] += (yl + yr) * 0.12;
    }
  }
  // reverb: a medium, darkish room-to-hall (a long bright tail reads as eerie)
  const verb = freeverb(m.verb, n, { room: 0.74, damp: 0.5, predelay: 0.02 });

  // duck envelopes from the voice spans (smooth: 120 ms in, 450 ms out)
  const ctl = 64, nc = Math.ceil(n / ctl);
  const act = new Float32Array(nc);
  {
    let y = 0;
    for (let c = 0; c < nc; c++) {
      const target = voicedAt((c * ctl) / SR) ? 1 : 0;
      const tau = target > y ? 0.12 : 0.45;
      y += (target - y) * (1 - Math.exp(-ctl / SR / tau));
      act[c] = y;
    }
  }
  // how far each layer dips while someone speaks (plan.duck = bed depth in dB)
  const duck = plan.duck ?? -10; // dB
  const depth = { bed: db(duck), keys: db(duck - 2), drums: db(duck + 3), lead: db(duck - 12), sfx: db(-2), verb: db(duck - 2) };
  // two mixes: the full score, and the bed without sound effects (the renderer
  // measures the music/voice balance on the bed, so word-synced ticks don't count)
  const out = { L: new Float32Array(n), R: new Float32Array(n) };
  const bedOut = { L: new Float32Array(n), R: new Float32Array(n) };
  for (let i = 0; i < n; i++) {
    const a = act[(i / ctl) | 0];
    const g = (d) => 1 - a * (1 - d);
    let l = m.bed.L[i] * g(depth.bed) + m.keys.L[i] * g(depth.keys) + m.drums.L[i] * g(depth.drums) + m.lead.L[i] * g(depth.lead) + verb.L[i] * g(depth.verb);
    let r = m.bed.R[i] * g(depth.bed) + m.keys.R[i] * g(depth.keys) + m.drums.R[i] * g(depth.drums) + m.lead.R[i] * g(depth.lead) + verb.R[i] * g(depth.verb);
    if (musicGain) { const q = i / 64, k = q | 0, w = musicGain[k] + (musicGain[k + 1] - musicGain[k]) * (q - k); l *= w; r *= w; }
    bedOut.L[i] = l; bedOut.R[i] = r;
    out.L[i] = l + m.sfx.L[i] * g(depth.sfx);
    out.R[i] = r + m.sfx.R[i] * g(depth.sfx);
  }
  // how loud each part of the mix is (dB, relative to the whole), so a score can be balanced without ears
  {
    const e = (b) => { let a = 0; for (let i = 0; i < n; i += 4) a += b.L[i] * b.L[i] + b.R[i] * b.R[i]; return a; };
    const parts = { bed: e(m.bed), keys: e(m.keys), drums: e(m.drums), lead: e(m.lead), reverb: e(verb) }, all = e(out) || 1e-12;
    report.mixDb = Object.fromEntries(Object.entries(parts).filter(([, v]) => v > 0).map(([k, v]) => [k, +(10 * Math.log10(v / all)).toFixed(1)]));
  }
  // glue: a gentle bus compressor, keyed from the music bed, applied to both mixes
  glue(bedOut, bedOut, out);
  const endN = Math.min(n, Math.round(duration * SR));
  const finish = (o) => {
    // keep the low end tidy under a voice, take out a little boxiness, then fades
    hp(o.L, 32); hp(o.R, 32);
    peakEq(o.L, 300, db(-1.5), 0.8); peakEq(o.R, 300, db(-1.5), 0.8);
    const fadeIn = Math.round(0.03 * SR), fadeOut = Math.round(0.35 * SR);
    for (let i = 0; i < fadeIn && i < n; i++) { o.L[i] *= i / fadeIn; o.R[i] *= i / fadeIn; }
    for (let i = Math.max(0, endN - fadeOut); i < n; i++) { const k = clamp((endN - i) / fadeOut); o.L[i] *= k * k; o.R[i] *= k * k; }
  };
  finish(out); finish(bedOut);

  // listening checks: what a listener would hear as ghostly, a buried melody,
  // a flat score, or effects that vanish or poke out (report.listen + warnings)
  if (!silent) measure({ m, verb, bedOut, onsets, beat, barLen, offset, endT: scripted ? duration : endT, sfx: [...(plan.sfx || []), ...placedFx], energies: sections.map(energyOf), voicedAt, engine: orch.kind, report, warnings });

  // loudness: the bed's music-only passages land `gap` dB under the voice
  // (opts.voiceDb = the measured speech RMS; Edge voices sit near -25 dBFS).
  // Without narration the score *is* the soundtrack and plays at full level.
  // `volume` is applied after this, so it really changes the level.
  const stats = level(bedOut, act, ctl);
  const gap = plan.gap ?? 6; // vs gated speech RMS ≈ 3–4 dB under the voice as `gaga check` measures it
  const targetRms = db(opts.targetDb ?? (voice.length ? (opts.voiceDb ?? -25.5) - gap : -18));
  const norm = (stats.rms > 1e-6 ? targetRms / stats.rms : 1) * (plan.volume ?? 1);
  for (const o of [out, bedOut]) {
    for (let i = 0; i < n; i++) { o.L[i] *= norm; o.R[i] *= norm; }
    limit(o, db(-1));
  }
  let peak = 0;
  for (let i = 0; i < n; i++) peak = Math.max(peak, Math.abs(out.L[i]), Math.abs(out.R[i]));
  report.peakDb = +(20 * Math.log10(peak || 1e-9)).toFixed(1);
  report.endChordAt = endT < duration ? +endT.toFixed(3) : null;
  report.voiceDuckDb = duck;
  report.gapDb = voice.length ? -gap : null;
  return { left: out.L, right: out.R, bed: { left: bedOut.L, right: bedOut.R }, sampleRate: SR, duration, report };
}

// ---------------------------------------------------------------------------
// written scores: music.script
// ---------------------------------------------------------------------------
// A composition can name a score script (music.script: 'score.mjs') instead of
// layers. It exports default function (S) and writes every note and every sound
// effect itself, at the picture's own times: the scenes, the words as they are
// spoken and the events the scenes declare (their sfx and transitions). The
// renderer still plays it on the sampled instruments, in one room, ducks it
// under the voice, levels it and runs the listening checks.
function scoreApi({ plan, orch, m, R, human, harmony, chordAtT, beat, barLen, beatsPerBar, offset, duration, sections, voicedAt, placedFx, musicGain, n }) {
  const norm = (x) => String(x).replace(/[\s\p{P}]/gu, '').toLowerCase();
  const sceneOf = (id) => { const s = sections.find((x) => x.id === id); if (!s) throw new Error(`score script: no scene '${id}' (scenes: ${sections.map((x) => x.id).join(', ')})`); return s; };
  // where a phrase starts (or ends) in a scene's narration, in film seconds
  const phrase = (id, text, end) => {
    const w = sceneOf(id).words || [], want = norm(text);
    for (let i = 0; i < w.length; i++) {
      let acc = '';
      for (let j = i; j < w.length; j++) {
        acc += norm(w[j].text);
        if (acc === want || (acc.startsWith(want) && j === i)) return end ? w[j].end : w[i].t;
        if (!want.startsWith(acc)) break;
      }
    }
    for (let i = 0; i < w.length; i++) if (norm(w[i].text).includes(want)) return end ? w[i].end : w[i].t;
    throw new Error(`score script: '${text}' is not spoken in scene '${id}'`);
  };
  const midiOf = (x) => {
    if (typeof x === 'number') return x;
    const v = noteNumber(String(x));
    if (v == null) throw new Error(`score script: can't read the note '${x}' (write C4, F#5, Bb3 or a MIDI number)`);
    return v;
  };
  const capOf = (inst) => PITCHED[inst]?.cap ?? 0.2;
  const feel = (t, o) => (o.tight ? t : t + (human() - 0.5) * 0.012);
  const touch = (v, o) => (o.tight ? v : v * (0.94 + human() * 0.12));
  const idOf = (inst, o) => o.id ?? `${inst}:${o.kind ?? ''}:${o.bus ?? ''}`;
  const soundOpts = (o) => { const x = { ...o }; for (const k of ['id', 'bus', 'tight', 'strum', 'gate']) delete x[k]; return x; };
  const inFilm = (t) => t >= 0 && t < duration;
  const ramp = (t0, t1, target, mode) => { // shape the music gain (64-sample steps)
    const a = Math.max(0, Math.round((t0 * SR) / 64)), b = Math.min(musicGain.length - 1, Math.round((t1 * SR) / 64));
    for (let k = a; k <= b; k++) { const w = typeof target === 'function' ? target((k * 64) / SR) : target; musicGain[k] = mode === 'min' ? Math.min(musicGain[k], w) : w; }
  };
  const S = {
    bpm: plan.bpm, beat, bar: barLen, beatsPerBar, offset, duration,
    key: plan.key, mode: plan.mode,
    scenes: sections.map((s) => ({ ...s })),
    events: (plan.sfx || []).map((e) => ({ ...e })),
    voice: (plan.voice || []).map((v) => ({ ...v })),
    scene: (id) => ({ ...sceneOf(id) }),
    when: (id, text) => phrase(id, text, false),
    whenEnd: (id, text) => phrase(id, text, true),
    event: (scene, type, i = 0) => {
      const list = (plan.sfx || []).filter((e) => e.scene === scene && (type == null || e.type === type));
      if (!list[i]) throw new Error(`score script: scene '${scene}' has no event${type ? ` '${type}'` : ''} #${i}`);
      return list[i].t;
    },
    speaking: (t) => voicedAt(t),
    // the beat grid: the nearest / next point on it (div in beats: 1, 0.5, 0.25, 4 …)
    grid: (t, div = 1) => offset + Math.round((t - offset) / (beat * div)) * beat * div,
    next: (t, div = 1) => offset + Math.ceil((t - offset) / (beat * div) - 1e-6) * beat * div,
    beats: (k) => k * beat,
    // bar n, beat b (both from 0) in film seconds, and the bar a time falls in
    at: (bar, b = 0) => offset + (bar * beatsPerBar + b) * beat,
    barAt: (t) => (t - offset) / barLen,
    midi: midiOf,
    chordAt: (t) => harmony.chordAt(t).slice(),
    random: () => R(),
    note(t, inst, pitch, dur, vel, o = {}) {
      if (!PITCHED[inst]) throw new Error(`score script: '${inst}' is not an instrument (${Object.keys(PITCHED).join(', ')})`);
      if (!inFilm(t)) return;
      orch.note(idOf(inst, o), inst, Math.max(0, feel(t, o)), Math.min(dur, duration - t), midiOf(pitch), Math.min(capOf(inst), touch(vel, o)), soundOpts(o), o.bus);
    },
    chord(t, inst, pitches, dur, vel, o = {}) {
      const strum = o.strum ?? (['guitar', 'pluck', 'acoustic', 'harp', 'koto'].includes(inst) ? 0.014 : SUSTAINED.has(inst) ? 0 : 0.006);
      pitches.forEach((p, i) => S.note(t + i * strum, inst, p, dur, vel * (i ? 0.92 : 1), { ...o, tight: true }));
    },
    // a line in the notation of §2.3 ('C5:.5 F5 A5 | …'), from time t
    line(t, inst, str, vel, o = {}) {
      const L = parseLine(str, beatsPerBar);
      if (L.error) throw new Error(`score script: line ${L.error}: ${str}`);
      let lo = Infinity, hi = -Infinity;
      for (const ev of L.events) for (const x of ev.midis) { lo = Math.min(lo, x); hi = Math.max(hi, x); }
      for (const ev of L.events) {
        const top = Math.max(...ev.midis), shape = hi > lo ? 0.9 + 0.2 * (top - lo) / (hi - lo) : 1;
        const down = Math.abs(ev.b % beatsPerBar) < 1e-6 ? 1.06 : Math.abs(ev.b % 1) > 1e-6 ? 0.92 : 1;
        const d = ev.len * beat * (o.gate ?? (SUSTAINED.has(inst) ? 1 : 0.95));
        ev.midis.forEach((x, i) => S.note(t + ev.b * beat + i * (ev.midis.length > 1 ? 0.008 : 0), inst, x + 12 * (o.octave ?? 0), d, vel * ev.acc * shape * down * (i ? 0.92 : 1), o));
      }
      return L.beats * beat; // how long it lasts
    },
    drum(name, t, vel, o = {}) {
      if (!DRUMS[name]) throw new Error(`score script: '${name}' is not a drum (${Object.keys(DRUMS).join(', ')})`);
      if (!inFilm(t)) return;
      orch.drum(name, Math.max(0, o.tight === false ? feel(t, {}) : t), Math.min(LIMITS.vel[name] ?? 0.5, vel), { ...o, ...(o.kit != null ? { kit: KITS[o.kit] ?? o.kit } : {}) });
    },
    // a sound effect from the kit (§4), optionally tuned: semi = semitones up or down
    fx(type, t, o = {}) {
      const fn = FX[type];
      if (!fn) throw new Error(`score script: '${type}' is not a sound effect (${Object.keys(FX).join(', ')})`);
      if (t < -1 || t > duration + 1) return;
      const e = { type, t, ...o };
      fn(m, e, R, harmony, orch);
      placedFx.push(e);
    },
    // silence the music (not the effects) from t0 to t1: a dead stop. `fade`
    // is the way in; the music comes back at once (on the hit that ends it)
    hole(t0, t1, fade = 0.01) { const back = 0.008; ramp(t0, t1, 0); ramp(t0 - fade, t0, (t) => clamp((t0 - t) / fade), 'min'); ramp(t1, t1 + back, (t) => clamp((t - t1) / back), 'min'); },
    // dip the music under a sound that matters: db down, held, then back
    dip(t, dB = -4, { attack = 0.04, hold = 0.15, release = 0.3 } = {}) {
      const g = db(dB);
      ramp(t - attack, t, (x) => 1 - (1 - g) * clamp((x - (t - attack)) / attack), 'min');
      ramp(t, t + hold, g, 'min');
      ramp(t + hold, t + hold + release, (x) => g + (1 - g) * clamp((x - t - hold) / release), 'min');
    },
  };
  return S;
}

// ---------------------------------------------------------------------------
// listening checks
// ---------------------------------------------------------------------------
// Numbers for what can't be heard from here, each tied to what a listener
// notices. Warnings, never errors: a quiet, held passage can be right.
//   ghost   4-bar windows with few note starts (< 1 per beat), mostly held notes
//           (> 60% of the energy) and a reverb tail within 12 dB of the dry
//           sound: the combination people describe as eerie or "阴间"
//   melody  the lead vs everything else in 500 Hz–4 kHz while it plays (≥ 3 dB)
//   range   loudness range (LU, 3 s windows) of the music before ducking: a score
//           whose energy plan rises and falls should not measure flat (≥ 3 LU)
//   sfx     each effect's loudest 25 ms vs the music around it, in the band it
//           lives in (2–8 kHz; 60 Hz–2 kHz for hits): about +3 to +10 dB reads
//           clearly, under −6 dB is lost, over +18 dB jumps out (accents aside)
function measure({ m, verb, bedOut, onsets, beat, barLen, offset, endT, sfx, energies, voicedAt, engine, report, warnings }) {
  const n = m.bed.L.length, nb = Math.ceil(n / BLK);
  const blockE = (bufs, from = 0, to = n) => {
    const e = new Float64Array(nb);
    for (const b of bufs) for (let i = from; i < to; i++) e[(i / BLK) | 0] += b.L[i] * b.L[i] + b.R[i] * b.R[i];
    return e;
  };
  const dry = [m.bed, m.keys, m.drums, m.lead];
  const dryE = blockE(dry), verbE = blockE([verb]);
  const sum = (a, i0, i1) => { let s = 0; for (let i = Math.max(0, i0); i < Math.min(a.length, i1); i++) s += a[i]; return s; };
  const listen = {};

  // ghost windows (needs the per-part energies of the sampled engine)
  if (engine === 'samples') {
    const ons = onsets.slice().sort((a, b) => a - b).filter((t, i, a) => !i || t - a[i - 1] > 0.03);
    let peak = 0;
    for (const v of dryE) peak = Math.max(peak, v);
    const ghost = [];
    const w = 4 * barLen;
    for (let t0 = offset, bar = 1; t0 + 2 * barLen <= endT + 1e-6; t0 += w, bar += 4) {
      const t1 = Math.min(t0 + w, endT), i0 = Math.floor(t0 * SR / BLK), i1 = Math.floor(t1 * SR / BLK);
      const d = sum(dryE, i0, i1);
      if (d < peak * (i1 - i0) * 1e-4) continue; // (near) silence is not a ghost
      const perBeat = ons.filter((t) => t >= t0 && t < t1).length / ((t1 - t0) / beat);
      const held = sum(m.susE, i0, i1) / d;
      const tail = 10 * Math.log10(sum(verbE, i0, i1) / d + 1e-12);
      if (perBeat < 1 && held > 0.6 && tail > -12) ghost.push({ bars: `${bar}–${bar + Math.round((t1 - t0) / barLen) - 1}`, perBeat: +perBeat.toFixed(2), held: Math.round(held * 100), tailDb: +tail.toFixed(1) });
    }
    listen.ghost = ghost;
    for (const g of ghost) warnings.push(`bars ${g.bars} may sound ghostly: ${g.perBeat} note starts per beat, ${g.held}% held notes, reverb tail ${g.tailDb} dB under the dry sound. Give it a part that articulates (piano, pluck, a pulse) or less reverb`);
  }

  // band-limited mono copy of some buses
  const band = (bufs, lo, hi) => {
    const x = new Float32Array(n);
    for (const b of bufs) for (let i = 0; i < n; i++) x[i] += (b.L[i] + b.R[i]) * 0.5;
    const f1 = svf(), f2 = svf();
    f1.set(lo, 0.707); f2.set(hi, 0.707);
    for (let i = 0; i < n; i++) x[i] = f2.run(f1.run(x[i], 'hp'), 'lp');
    return x;
  };
  const eOf = (x) => { const e = new Float64Array(nb); for (let i = 0; i < n; i++) e[(i / BLK) | 0] += x[i] * x[i]; return e; };

  // melody vs the rest, 500 Hz – 4 kHz, where the lead plays
  {
    const leadE = eOf(band([m.lead], 500, 4000)), restE = eOf(band([m.bed, m.keys, m.drums], 500, 4000));
    let top = 0;
    for (const v of leadE) top = Math.max(top, v);
    const margins = [];
    for (let i = 0; i < nb; i++) if (top > 0 && leadE[i] > top * 0.03) margins.push(10 * Math.log10(leadE[i] / (restE[i] + 1e-12)));
    if (margins.length > 20) {
      margins.sort((a, b) => a - b);
      listen.melodyDb = +margins[Math.floor(margins.length / 2)].toFixed(1);
      if (listen.melodyDb < 3) warnings.push(`the melody sits ${listen.melodyDb} dB against the other parts in 500 Hz–4 kHz while it plays (aim for ≥ 3 dB): it will be hard to follow. Thin or lower the keys/pads in its register, or move the lead above them`);
    }
  }

  // loudness range of the music itself (before the voice ducks it)
  {
    const x = new Float32Array(n);
    for (const b of [...dry, verb]) for (let i = 0; i < n; i++) x[i] += (b.L[i] * b.L[i] + b.R[i] * b.R[i]) * 0.5;
    const end = Math.min(n, Math.round(endT * SR)), win = 3 * SR, hop = SR;
    const st = [];
    for (let a = 0; a + win <= end; a += hop) { let e = 0; for (let i = a; i < a + win; i++) e += x[i]; st.push(10 * Math.log10(e / win + 1e-12)); }
    const mean = 10 * Math.log10(st.reduce((acc, v) => acc + 10 ** (v / 10), 0) / Math.max(1, st.length) + 1e-12);
    const gated = st.filter((v) => v > mean - 20).sort((a, b) => a - b);
    if (gated.length >= 5) {
      listen.rangeLU = +(gated[Math.min(gated.length - 1, Math.floor(gated.length * 0.95))] - gated[Math.floor(gated.length * 0.1)]).toFixed(1);
      const span = Math.max(...energies) - Math.min(...energies);
      if (span >= 0.3 && listen.rangeLU < 3) warnings.push(`the score's energy plan rises and falls (${Math.min(...energies).toFixed(2)}–${Math.max(...energies).toFixed(2)}) but the music measures nearly flat (${listen.rangeLU} LU loudness range): let the quiet scenes drop parts and the peaks add them`);
    }
  }

  // each effect against the music under it (after ducking), in its own band
  if (sfx.length) {
    const lowTypes = new Set(['hit', 'boom', 'riser', 'swell', 'thud']);
    const music = { hi: eOf(band([bedOut], 2000, 8000)), lo: eOf(band([bedOut], 60, 2000)) };
    const fx = { hi: eOf(band([m.sfx], 2000, 8000)), lo: eOf(band([m.sfx], 60, 2000)) };
    const lifts = [];
    for (const e of sfx) {
      const k = lowTypes.has(e.type) ? 'lo' : 'hi';
      const i0 = Math.max(0, Math.floor((e.t - 0.5) * SR / BLK)), i1 = Math.min(nb, Math.ceil((e.t + 0.4) * SR / BLK));
      let best = -1, at = i0;
      for (let i = i0; i < i1; i++) if (fx[k][i] > best) { best = fx[k][i]; at = i; }
      if (!(best > 0)) continue;
      // its loudest 25 ms against the music's average over ~150 ms around it
      const a = Math.max(0, at - 2), b = Math.min(nb, at + 4);
      const lift = 10 * Math.log10(best / (sum(music[k], a, b) / (b - a) + 1e-12));
      lifts.push({ type: e.type, t: +e.t.toFixed(2), db: +Math.max(-60, Math.min(60, lift)).toFixed(1), voiced: voicedAt(e.t) });
    }
    if (lifts.length) {
      const sorted = lifts.map((x) => x.db).sort((a, b) => a - b);
      listen.sfxDb = { median: sorted[Math.floor(sorted.length / 2)], min: sorted[0], max: sorted[sorted.length - 1] };
      if (process.env.VIDEO_GAGA_LISTEN_ALL) listen.sfxAll = lifts;
      // accents (hits, booms, chimes, swells) are meant to stand out, often over a breath in the music
      const accent = new Set(['hit', 'boom', 'riser', 'swell', 'shimmer', 'chime']);
      const buried = lifts.filter((x) => x.db < -6), loud = lifts.filter((x) => x.db > 18 && !accent.has(x.type));
      if (buried.length) warnings.push(`${buried.length} sound effect(s) sit under the music in their band and will barely be heard: ${buried.slice(0, 6).map((x) => `${x.type}@${x.t} (${x.db} dB)`).join(', ')}. Raise their gain or drop them`);
      if (loud.length) warnings.push(`${loud.length} sound effect(s) stand far above the music (> 18 dB in their band): ${loud.slice(0, 6).map((x) => `${x.type}@${x.t} (+${x.db} dB)`).join(', ')}. They will jump out; lower their gain`);
    }
  }
  report.listen = listen;
}

function level(out, act, ctl) {
  // RMS over the samples where nobody talks (what the music sounds like "alone")
  let s = 0, c = 0, sAll = 0;
  for (let i = 0; i < out.L.length; i++) {
    const v = (out.L[i] * out.L[i] + out.R[i] * out.R[i]) / 2;
    sAll += v;
    if (act[(i / ctl) | 0] < 0.05) { s += v; c++; }
  }
  const rms = c > out.L.length * 0.08 ? Math.sqrt(s / c) : Math.sqrt(sAll / out.L.length) * 1.6;
  return { rms };
}

// A slow RMS compressor (2:1 above the bed's own loud passages): it evens out
// layer entrances and fills so the score sits like a produced track.
function glue(key, ...outs) {
  const n = key.L.length, w = Math.round(0.03 * SR);
  let e = 0, cnt = 0;
  for (let i = 0; i < n; i++) { const v = (key.L[i] ** 2 + key.R[i] ** 2) / 2; if (v > 1e-10) { e += v; cnt++; } }
  if (!cnt) return;
  const thr = Math.sqrt(e / cnt) * db(2), ratio = 2;
  const att = Math.exp(-1 / (0.02 * SR)), rel = Math.exp(-1 / (0.25 * SR));
  let ms = 0, g = 1;
  const gains = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    const v = (key.L[i] ** 2 + key.R[i] ** 2) / 2;
    ms += (v - ms) / w;
    const lvl = Math.sqrt(Math.max(ms, 0));
    const target = lvl > thr ? Math.pow(lvl / thr, 1 / ratio - 1) : 1;
    g = target < g ? target + (g - target) * att : target + (g - target) * rel;
    gains[i] = g;
  }
  for (const o of outs) for (let i = 0; i < n; i++) { o.L[i] *= gains[i]; o.R[i] *= gains[i]; }
}

// Look-ahead peak limiter: the gain is already down when a peak arrives (no
// clipping, no distortion), and recovers over ~100 ms.
function limit(o, ceil) {
  const n = o.L.length, look = Math.round(0.002 * SR), rel = Math.exp(-1 / (0.1 * SR));
  const need = new Float32Array(n);
  for (let i = 0; i < n; i++) { const a = Math.max(Math.abs(o.L[i]), Math.abs(o.R[i])); need[i] = a > ceil ? ceil / a : 1; }
  // the lowest gain needed anywhere in the next `look` samples (a running minimum)
  const env = new Float32Array(n), dq = [];
  for (let i = n - 1; i >= 0; i--) {
    while (dq.length && need[dq[dq.length - 1]] >= need[i]) dq.pop();
    dq.push(i);
    while (dq[0] > i + look) dq.shift();
    env[i] = need[dq[0]];
  }
  // ramp into it over the look-ahead, release slowly
  let g = 1;
  const att = 1 / look;
  for (let i = 0; i < n; i++) {
    const t = env[i];
    g = t < g ? Math.max(t, g - att) : t + (g - t) * rel;
    o.L[i] *= g; o.R[i] *= g;
  }
}

// RBJ peaking EQ (gain g as a linear factor)
function peakEq(buf, fc, g, q) {
  const A = Math.sqrt(g), w = TAU * fc / SR, al = Math.sin(w) / (2 * q), cw = Math.cos(w);
  const a0 = 1 + al / A, b0 = (1 + al * A) / a0, b1 = (-2 * cw) / a0, b2 = (1 - al * A) / a0, a1 = (-2 * cw) / a0, a2 = (1 - al / A) / a0;
  let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
  for (let i = 0; i < buf.length; i++) {
    const x = buf[i], y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2;
    x2 = x1; x1 = x; y2 = y1; y1 = y; buf[i] = y;
  }
}

function hp(buf, fc) {
  const a = Math.exp(-TAU * fc / SR);
  let x1 = 0, y1 = 0;
  for (let i = 0; i < buf.length; i++) { const x = buf[i]; const y = a * (y1 + x - x1); x1 = x; y1 = y; buf[i] = y; }
}

function freeverb(input, n, { room = 0.8, damp = 0.5, wet = 1, predelay = 0 } = {}) {
  const k = SR / 44100;
  const combT = [1116, 1188, 1277, 1356, 1422, 1491, 1557, 1617], apT = [556, 441, 341, 225], spread = 23;
  const fb = room * 0.28 + 0.7, d = damp * 0.4;
  const make = (off) => ({
    combs: combT.map((c) => ({ buf: new Float32Array(Math.round((c + off) * k)), i: 0, f: 0 })),
    aps: apT.map((c) => ({ buf: new Float32Array(Math.round((c + off) * k)), i: 0 })),
  });
  const chans = [make(0), make(spread)];
  const out = { L: new Float32Array(n), R: new Float32Array(n) };
  // input: pre-delay, then band-limit (no rumble or fizz in the tail)
  const pd = Math.round(predelay * SR), lp = onePole(6000);
  let hx = 0, hy = 0;
  const ha = Math.exp(-TAU * 220 / SR);
  for (let i = 0; i < n; i++) {
    let x = lp(i >= pd ? input[i - pd] : 0) * 0.015;
    const y = ha * (hy + x - hx); hx = x; hy = y; x = y;
    for (let ch = 0; ch < 2; ch++) {
      const c = chans[ch];
      let s = 0;
      for (const cb of c.combs) {
        const o = cb.buf[cb.i];
        cb.f = o * (1 - d) + cb.f * d;
        cb.buf[cb.i] = x + cb.f * fb;
        if (++cb.i >= cb.buf.length) cb.i = 0;
        s += o;
      }
      for (const ap of c.aps) {
        const b = ap.buf[ap.i];
        ap.buf[ap.i] = s + b * 0.5;
        s = b - s;
        if (++ap.i >= ap.buf.length) ap.i = 0;
      }
      (ch ? out.R : out.L)[i] = s * wet * 2.1;
    }
  }
  return out;
}

// ---------------------------------------------------------------------------
// WAV (32-bit float, stereo)
// ---------------------------------------------------------------------------
export function writeWav(file, { left, right, sampleRate = SR }) {
  const n = left.length, bytes = n * 2 * 4;
  const buf = Buffer.alloc(44 + bytes);
  buf.write('RIFF', 0); buf.writeUInt32LE(36 + bytes, 4); buf.write('WAVE', 8);
  buf.write('fmt ', 12); buf.writeUInt32LE(16, 16); buf.writeUInt16LE(3, 20); buf.writeUInt16LE(2, 22);
  buf.writeUInt32LE(sampleRate, 24); buf.writeUInt32LE(sampleRate * 8, 28); buf.writeUInt16LE(8, 32); buf.writeUInt16LE(32, 34);
  buf.write('data', 36); buf.writeUInt32LE(bytes, 40);
  let o = 44;
  for (let i = 0; i < n; i++) { buf.writeFloatLE(left[i], o); buf.writeFloatLE(right[i], o + 4); o += 8; }
  fs.writeFileSync(file, buf);
}

export const sfxTypes = Object.keys(FX);
export const _internals = { I, D, FX, Mixer, rng, SR, PITCHED, DRUMS, parseLine };
