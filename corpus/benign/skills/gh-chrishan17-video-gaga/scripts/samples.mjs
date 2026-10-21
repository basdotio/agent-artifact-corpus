// video-gaga samples — multi-sampled instruments for the score.
//
// The General MIDI SoundFont (scripts/soundfont.mjs) plays most parts. The
// instruments a score leans on hardest, the piano and the strings, sound
// better played from real multi-sampled recordings:
//
//   piano     Salamander Grand Piano V3 (Alexander Holm, CC BY 3.0)
//   felt      a close-miked upright, pp and mf (VSCO 2 Community Edition, CC0)
//   strings   violin, viola and cello sections with vibrato (VSCO 2 CE, CC0)
//   violin    a solo violin, p and f (VSCO 2 CE, CC0)
//   cello     the cello section (VSCO 2 CE, CC0)
//   harp      a concert harp (VSCO 2 CE, CC0)
//
// Only the samples a score actually plays are downloaded, once, into
// ~/.cache/video-gaga/samples. When one can't be fetched the part falls back to
// the SoundFont and the score says so. Rendering is a pure function of the
// note list: same notes, same samples, same output.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';

const SR = 48000;
const cacheDir = () => path.join(process.env.VIDEO_GAGA_CACHE || path.join(os.homedir(), '.cache', 'video-gaga'), 'samples');

const VSCO = 'https://raw.githubusercontent.com/sgossner/VSCO-2-CE/440300901dfe9275fd84e0b7763af1f8443ae62e/';
const SALAMANDER = 'https://tonejs.github.io/audio/salamander/';
const PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
// 'F#3', 'Ds1' (s = sharp), 'Bb2' → MIDI (C4 = 60), plus an octave offset for
// libraries that name middle C as C3
function midiOf(name, octaveShift = 0) {
  const m = /^([A-G])(#|s|b)?(-?\d)$/.exec(name);
  if (!m) throw new Error(`bad note name ${name}`);
  return 12 * (Number(m[3]) + 1 + octaveShift) + PC[m[1]] + (m[2] === 'b' ? -1 : m[2] ? 1 : 0);
}
const enc = (p) => p.split('/').map(encodeURIComponent).join('/');
const vsco = (dir, file) => VSCO + enc(`${dir}/${file}`);

function list(names, make) { return names.split(' ').flatMap(make); }

// Each bank: its samples ({ url, midi, layer, group }), how loud a note is
// split between layers, and how it behaves when a note ends.
export const BANKS = {
  piano: {
    credit: 'Piano: "Salamander Grand Piano V3" by Alexander Holm, CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/)',
    kind: 'decay', release: 0.32,
    // one velocity layer: soft notes are darkened instead
    darken: true,
    samples: ['A0', ...[1, 2, 3, 4, 5, 6, 7].flatMap((o) => ['C', 'Ds', 'Fs', 'A'].map((n) => `${n}${o}`)), 'C8']
      .map((n) => ({ url: `${SALAMANDER}${n}.mp3`, midi: midiOf(n), layer: 0 })),
  },
  felt: {
    credit: 'Upright piano: VSCO 2 Community Edition by Versilian Studios, CC0',
    kind: 'decay', release: 0.28, split: 0.62,
    samples: [
      ...list('C1 C2 C3 C4 C5 C6 C7 G1 G2 G3 G4 G5 G6 G7', (n) => ({ url: vsco('Keys/Upright Nr1', `UR1_${n}_pp_RR1.wav`), midi: midiOf(n), layer: 0 })),
      ...list('C2 C3 C4 C5 C6 C7 G1 G2 G3 G4 G5 G6 G7', (n) => ({ url: vsco('Keys/Upright Nr1', `UR1_${n}_mf_RR1.wav`), midi: midiOf(n), layer: 1 })),
    ],
  },
  strings: {
    credit: 'Strings: VSCO 2 Community Edition by Versilian Studios, CC0',
    kind: 'sustain', release: 0.45, split: 0.6,
    // a string section voices each register on the instrument that owns it
    group: (m) => (m < 55 ? 'cello' : m < 67 ? 'viola' : 'violin'),
    samples: [
      ...list('A2 A3 B2 B4 C4 D3 D5 E4 F#3 G2 G4', (n) => [1, 2].map((v) => ({ url: vsco('Strings/Violin Section/susVib', `VlnEns_susVib_${n}_v${v}.wav`), midi: midiOf(n, 1), layer: v - 1, group: 'violin' }))),
      ...list('A3 B2 B4 C2 C4 D2 D3 D5 E2 E4 F3 G2 G4', (n) => [1, 2].map((v) => ({ url: vsco('Strings/Viola Section/susvib', `ViolaEns_susvib_${n}_v${v}_1.wav`), midi: midiOf(n, 1), layer: v - 1, group: 'viola' }))),
      ...list('A2 B1 B3 C1 C3 D2 D4 E1 E3 F2 F4 G1 G3', (n) => [1, 3].map((v, i) => ({ url: vsco('Strings/Cello Section/susvib', `susvib_${n}_v${v}_1.wav`), midi: midiOf(n, 1), layer: i, group: 'cello' }))),
    ],
  },
  violin: {
    credit: 'Solo violin: VSCO 2 Community Edition by Versilian Studios, CC0',
    kind: 'sustain', release: 0.3, split: 0.6,
    samples: list('A3 A4 A5 A6 C4 C5 C6 C7 E4 E5 E6 G3 G4 G5 G6', (n) => ['p', 'f'].map((d, i) => ({ url: vsco('Strings/Solo Violin/Arco Vib', `LLVln_ArcoVib_${n}_${d}.wav`), midi: midiOf(n), layer: i }))),
  },
  cello: {
    credit: 'Cello: VSCO 2 Community Edition by Versilian Studios, CC0',
    kind: 'sustain', release: 0.4, split: 0.6,
    samples: list('A2 B1 B3 C1 C3 D2 D4 E1 E3 F2 F4 G1 G3', (n) => [1, 3].map((v, i) => ({ url: vsco('Strings/Cello Section/susvib', `susvib_${n}_v${v}_1.wav`), midi: midiOf(n, 1), layer: i }))),
  },
  harp: {
    credit: 'Harp: VSCO 2 Community Edition by Versilian Studios, CC0',
    kind: 'ring', release: 1.2,
    samples: ['A2_mf', 'A4_mf', 'A6_mf', 'B1_mf', 'B3_mf', 'B5_mf', 'B6_mf', 'C3_mf', 'C5_mf', 'D2_mf', 'D4_mf', 'D6_mf', 'D7_f', 'E1_f', 'E3_mf', 'E5_mf', 'F2_mf', 'F4_mf', 'F6_mf', 'F7_f', 'G1_mp', 'G3_mf', 'G5_mf']
      .map((s) => ({ url: vsco('Strings/Harp', `KSHarp_${s}.wav`), midi: midiOf(s.split('_')[0]), layer: 0 })),
  },
};
// which score instruments play from which bank (`sinepad` = soft, slow strings)
export const MULTI = { piano: 'piano', felt: 'felt', strings: 'strings', sinepad: 'strings', violin: 'violin', cello: 'cello', harp: 'harp' };

// ---------------------------------------------------------------------------
// loading
// ---------------------------------------------------------------------------
const memo = new Map(); // url → { L, R, sr, start } | { error }

function fileFor(url) {
  const rel = url.replace(/^https?:\/\//, '').replace(/[^A-Za-z0-9._/-]/g, '_');
  return path.join(cacheDir(), rel);
}

function download(url, file) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.part`;
  const r = spawnSync('curl', ['-fsSL', '--retry', '2', '--connect-timeout', '15', '--max-time', '120', '-o', tmp, url], { stdio: ['ignore', 'ignore', 'pipe'], encoding: 'utf8' });
  if (r.status !== 0) { fs.rmSync(tmp, { force: true }); return r.error ? 'curl not found' : (r.stderr || `curl exit ${r.status}`).trim(); }
  fs.renameSync(tmp, file);
  return null;
}

// PCM / float WAV → { ch: Float32Array[], sr }
export function readWav(buf) {
  if (buf.toString('ascii', 0, 4) !== 'RIFF' || buf.toString('ascii', 8, 12) !== 'WAVE') throw new Error('not a WAV file');
  let p = 12, fmt = null, data = null;
  while (p + 8 <= buf.length) {
    const id = buf.toString('ascii', p, p + 4), size = buf.readUInt32LE(p + 4);
    if (id === 'fmt ') {
      let format = buf.readUInt16LE(p + 8);
      if (format === 0xfffe) format = buf.readUInt16LE(p + 32);
      fmt = { format, channels: buf.readUInt16LE(p + 10), sr: buf.readUInt32LE(p + 12), bits: buf.readUInt16LE(p + 22) };
    } else if (id === 'data') data = buf.subarray(p + 8, Math.min(buf.length, p + 8 + size));
    p += 8 + size + (size & 1);
  }
  if (!fmt || !data) throw new Error('WAV without fmt/data');
  const { format, channels, bits } = fmt, bps = bits / 8, frames = Math.floor(data.length / (bps * channels));
  const ch = Array.from({ length: channels }, () => new Float32Array(frames));
  for (let i = 0; i < frames; i++) for (let c = 0; c < channels; c++) {
    const o = (i * channels + c) * bps;
    let v;
    if (format === 3 && bits === 32) v = data.readFloatLE(o);
    else if (bits === 16) v = data.readInt16LE(o) / 32768;
    else if (bits === 24) v = (data.readUInt8(o) | (data.readUInt8(o + 1) << 8) | (data.readInt8(o + 2) << 16)) / 8388608;
    else if (bits === 32) v = data.readInt32LE(o) / 2147483648;
    else if (bits === 8) v = (data.readUInt8(o) - 128) / 128;
    else throw new Error(`unsupported WAV: ${bits}-bit, format ${format}`);
    ch[c][i] = v;
  }
  return { ch, sr: fmt.sr };
}

// anything ffmpeg can read → { ch: [L, R], sr: 48000 }
function readWithFfmpeg(file) {
  const r = spawnSync('ffmpeg', ['-v', 'error', '-i', file, '-ac', '2', '-ar', String(SR), '-f', 'f32le', '-'], { maxBuffer: 1 << 30 });
  if (r.error || r.status !== 0) throw new Error(r.error ? 'ffmpeg not found' : String(r.stderr).trim());
  const f = new Float32Array(r.stdout.buffer, r.stdout.byteOffset, r.stdout.byteLength / 4);
  const n = f.length >> 1, L = new Float32Array(n), R = new Float32Array(n);
  for (let i = 0; i < n; i++) { L[i] = f[2 * i]; R[i] = f[2 * i + 1]; }
  return { ch: [L, R], sr: SR };
}

function load(url, { download: dl = true } = {}) {
  if (memo.has(url)) return memo.get(url);
  const file = fileFor(url);
  let res;
  try {
    if (!fs.existsSync(file)) {
      if (!dl) throw new Error('not downloaded yet');
      const err = download(url, file);
      if (err) throw new Error(err);
    }
    const { ch, sr } = /\.wav$/i.test(file) ? readWav(fs.readFileSync(file)) : readWithFfmpeg(file);
    const L = ch[0], R = ch[1] || ch[0];
    // where the note starts: the first sample within 40 dB of the peak, less 4 ms
    let pk = 0;
    for (let i = 0; i < L.length; i++) pk = Math.max(pk, Math.abs(L[i]), Math.abs(R[i]));
    let start = 0;
    const thr = pk * 0.01;
    while (start < L.length && Math.abs(L[start]) < thr && Math.abs(R[start]) < thr) start++;
    start = Math.max(0, start - Math.round(0.004 * sr));
    // every recording levelled to the same loudness (its loudest 50 ms): the
    // layers differ in timbre, and velocity alone sets how loud a note plays
    const w = Math.round(0.05 * sr);
    let best = 0;
    for (let a = start; a + w <= Math.min(L.length, start + 2 * sr); a += w >> 1) {
      let e = 0;
      for (let j = a; j < a + w; j++) e += (L[j] * L[j] + R[j] * R[j]) / 2;
      best = Math.max(best, e / w);
    }
    res = { L, R, sr, start, norm: 0.25 / Math.max(1e-5, Math.sqrt(best)) };
  } catch (e) {
    res = { error: `${url.split('/').pop()}: ${e.message}` };
  }
  memo.set(url, res);
  return res;
}

// ---------------------------------------------------------------------------
// playing
// ---------------------------------------------------------------------------
// the sample for a note: the right layer (and register group), nearest pitch;
// at equal distance, transpose down rather than up (pitched-up samples thin out)
export function pick(bank, midi, vel01) {
  const layer = bank.split != null && vel01 >= bank.split ? 1 : 0;
  const g = bank.group ? bank.group(midi) : null;
  let pool = bank.samples.filter((s) => s.layer === layer && (!g || s.group === g));
  if (!pool.length) pool = bank.samples.filter((s) => s.layer === layer);
  let best = null, cost = Infinity;
  for (const s of pool) {
    const d = midi - s.midi, c = Math.abs(d) + (d < 0 ? 0.25 : 0);
    if (c < cost) { cost = c; best = s; }
  }
  // a section sample transposed far out of its register sounds wrong: use any group
  if (g && cost > 4) for (const s of bank.samples.filter((x) => x.layer === layer)) {
    const d = midi - s.midi, c = Math.abs(d) + (d < 0 ? 0.25 : 0);
    if (c < cost) { cost = c; best = s; }
  }
  return best;
}

// The samples a list of notes needs, loaded. → { ok } | { error }
export function prepare(bankName, notes, opts = {}) {
  const bank = BANKS[bankName];
  const urls = new Set(notes.map((n) => pick(bank, n.midi, n.vel / 127).url));
  const missing = [...urls].filter((u) => !memo.has(u) && !fs.existsSync(fileFor(u)));
  if (missing.length && opts.log) opts.log(`▸ downloading ${missing.length} ${bankName} sample(s) once (${bank.credit})`);
  for (const u of urls) {
    const s = load(u, opts);
    if (s.error) return { error: s.error };
  }
  return { ok: true };
}

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);

// Render notes ({ t, dur, midi, vel 1–127 }) into stereo buffers of n samples.
// o: { attack, release, bright 0..1 }
export function renderNotes(bankName, notes, n, o = {}) {
  const bank = BANKS[bankName];
  const L = new Float32Array(n), R = new Float32Array(n);
  for (const nt of notes) {
    const v01 = clamp(nt.vel / 127, 0, 1);
    const s = pick(bank, nt.midi, v01), smp = memo.get(s.url);
    if (!smp || smp.error) continue;
    const ratio = Math.pow(2, (nt.midi - s.midi) / 12) * (smp.sr / SR);
    const len = smp.L.length - smp.start;
    // loudness follows velocity like a General MIDI synth (≈ −20 dB from 100 to 30)
    const amp = Math.pow(v01, 2) * 1.6 * smp.norm;
    const rel = o.release ?? bank.release, att = o.attack ?? 0;
    const ring = bank.kind === 'ring'; // a harp string rings on after the note
    const end = ring ? Math.max(nt.dur, 0) + rel : nt.dur + rel;
    const total = Math.min(Math.ceil(end * SR), n - Math.round(nt.t * SR));
    // a sustained note longer than its recording loops its steady middle
    const loopA = Math.floor(len * 0.4), loopB = Math.floor(len * 0.85), loopLen = loopB - loopA, xf = Math.min(Math.floor(0.25 * smp.sr), Math.floor(loopLen / 3));
    const canLoop = bank.kind === 'sustain' && loopLen > smp.sr * 0.5;
    // soft notes (and a darker `bright`) close a gentle low-pass
    const bright = nt.bright ?? o.bright ?? 0.5;
    const fc = (bank.darken ? 1800 + 15000 * v01 * v01 : 16000) * Math.pow(2, (bright - 0.5) * 2.5);
    const a = Math.exp(-2 * Math.PI * Math.min(fc, 20000) / SR);
    let zl = 0, zr = 0;
    const i0 = Math.round(nt.t * SR);
    for (let j = 0; j < total; j++) {
      const t = j / SR;
      let p = j * ratio;
      if (p >= len - 2) {
        if (!canLoop) break;
        p = loopA + ((p - loopA) % loopLen);
      }
      const k = Math.floor(p), fr = p - k;
      let l = interp(smp.L, smp.start + k, fr), r = interp(smp.R, smp.start + k, fr);
      // crossfade into the loop start near the loop end (equal power)
      if (canLoop && j * ratio >= loopA && p > loopB - xf) {
        const x = (p - (loopB - xf)) / xf, q = p - loopLen, kq = Math.floor(q), fq = q - kq;
        const gA = Math.cos(x * Math.PI / 2), gB = Math.sin(x * Math.PI / 2);
        l = l * gA + interp(smp.L, smp.start + kq, fq) * gB;
        r = r * gA + interp(smp.R, smp.start + kq, fq) * gB;
      }
      let env = att > 0 && t < att ? t / att : 1;
      if (!ring && t > nt.dur) env *= Math.exp(-(t - nt.dur) / (rel / 4));
      if (ring && t > nt.dur + rel * 0.5) env *= Math.exp(-(t - nt.dur - rel * 0.5) / (rel / 4));
      if (j > total - 64) env *= (total - j) / 64; // no click at the end
      zl = l + (zl - l) * a; zr = r + (zr - r) * a;
      const i = i0 + j;
      if (i < 0) continue;
      L[i] += zl * env * amp; R[i] += zr * env * amp;
    }
  }
  return { L, R };
}

// 4-point Hermite interpolation
function interp(x, k, f) {
  const xm = x[k - 1] ?? x[k] ?? 0, x0 = x[k] ?? 0, x1 = x[k + 1] ?? x0, x2 = x[k + 2] ?? x1;
  const c1 = 0.5 * (x1 - xm), c2 = xm - 2.5 * x0 + 2 * x1 - 0.5 * x2, c3 = 0.5 * (x2 - xm) + 1.5 * (x0 - x1);
  return ((c3 * f + c2) * f + c1) * f + x0;
}

// Loudest 50 ms RMS of one reference note at velocity 100 (to level a bank
// against the rest of the score, like Sampler.loudness).
// { mean: true } = the RMS over the whole note instead (how loud it sits over time).
export function loudness(bankName, midi, { mean = false } = {}) {
  const notes = [{ t: 0, dur: 1.2, midi, vel: 100 }];
  const p = prepare(bankName, notes);
  if (p.error) return null;
  const n = Math.round(1.6 * SR), { L, R } = renderNotes(bankName, notes, n);
  if (mean) return meanRms(L, R, Math.round(1.2 * SR));
  const w = Math.round(0.05 * SR);
  let best = 0;
  for (let s = 0; s + w <= n; s += w >> 1) {
    let e = 0;
    for (let j = s; j < s + w; j++) e += (L[j] * L[j] + R[j] * R[j]) / 2;
    best = Math.max(best, Math.sqrt(e / w));
  }
  return best || 1e-4;
}

export function meanRms(L, R, n) {
  let e = 0;
  for (let j = 0; j < n; j++) e += (L[j] * L[j] + R[j] * R[j]) / 2;
  return Math.sqrt(e / n) || 1e-6;
}

// which samples are cached (for `gaga doctor`)
export function cacheReport() {
  const out = {};
  for (const [name, bank] of Object.entries(BANKS)) out[name] = { cached: bank.samples.filter((s) => fs.existsSync(fileFor(s.url))).length, total: bank.samples.length };
  return out;
}
