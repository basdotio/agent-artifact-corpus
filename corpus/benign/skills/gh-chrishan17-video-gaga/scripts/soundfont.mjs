// video-gaga soundfont — real instrument samples for the generated score.
//
// The score (scripts/music.mjs) is played by sampled instruments: a General
// MIDI SoundFont rendered offline by spessasynth_core (Apache-2.0, pure JS +
// a WebAssembly Vorbis decoder). Rendering is a pure function of the note
// list, so the score stays deterministic: same spec, same samples.
//
// The SoundFont is MuseScore General (MIT; FluidR3 by Frank Wen, adapted by
// S. Christian Collins). It is 40 MB, so it is not in the repo: the first
// render downloads it once into ~/.cache/video-gaga (pinned by SHA-256).
// VIDEO_GAGA_SOUNDFONT=/path/to/any.sf2|.sf3 uses another General MIDI bank.

import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import crypto from 'node:crypto';
import { spawnSync } from 'node:child_process';

export const SOUNDFONT = {
  name: 'MuseScore_General.sf3',
  url: 'https://ftp.osuosl.org/pub/musescore/soundfont/MuseScore_General/MuseScore_General.sf3',
  sha256: '5b85b6c2c61d10b2b91cddd41efcce7b25cd31c8271d511c73afafbef20b6fa3',
  bytes: 39900972,
  license: 'MIT — MuseScore General by S. Christian Collins, from FluidR3 by Frank Wen',
};

const cacheDir = () => process.env.VIDEO_GAGA_CACHE || path.join(os.homedir(), '.cache', 'video-gaga');

// Where the bank is (or will be): the override, else the cached download.
export function soundfontPath() {
  if (process.env.VIDEO_GAGA_SOUNDFONT) return path.resolve(process.env.VIDEO_GAGA_SOUNDFONT);
  return path.join(cacheDir(), SOUNDFONT.name);
}

function sha256(file) {
  const h = crypto.createHash('sha256');
  const fd = fs.openSync(file, 'r'), buf = Buffer.alloc(1 << 20);
  let n;
  while ((n = fs.readSync(fd, buf, 0, buf.length)) > 0) h.update(buf.subarray(0, n));
  fs.closeSync(fd);
  return h.digest('hex');
}

// → { file } when the bank is ready, else { error }. Downloads it once.
export async function ensureSoundfont({ download = true, log = () => {} } = {}) {
  const file = soundfontPath();
  if (process.env.VIDEO_GAGA_SOUNDFONT) return fs.existsSync(file) ? { file } : { error: `VIDEO_GAGA_SOUNDFONT points to a missing file: ${file}` };
  if (fs.existsSync(file) && fs.statSync(file).size === SOUNDFONT.bytes) return { file };
  if (!download) return { error: `the instrument samples are not downloaded yet (${SOUNDFONT.name}, 40 MB)` };
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const tmp = `${file}.part`;
  log(`▸ downloading the instrument samples once (${SOUNDFONT.name}, 40 MB, ${SOUNDFONT.license})`);
  // curl honours the system proxy settings; fetch is the fallback
  let ok = false, why = '';
  const curl = spawnSync('curl', ['-fsSL', '--retry', '3', '-o', tmp, SOUNDFONT.url], { stdio: ['ignore', 'ignore', 'pipe'], encoding: 'utf8' });
  if (curl.status === 0) ok = true;
  else {
    why = curl.error ? 'curl not found' : (curl.stderr || '').trim();
    try {
      const r = await fetch(SOUNDFONT.url);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      fs.writeFileSync(tmp, Buffer.from(await r.arrayBuffer()));
      ok = true;
    } catch (e) { why += `${why ? '; ' : ''}${e.message}`; }
  }
  if (!ok) { fs.rmSync(tmp, { force: true }); return { error: `could not download ${SOUNDFONT.url} (${why}). Download it yourself to ${file}, or set VIDEO_GAGA_SOUNDFONT to a General MIDI .sf2/.sf3` }; }
  const got = sha256(tmp);
  if (got !== SOUNDFONT.sha256) { fs.rmSync(tmp, { force: true }); return { error: `the downloaded ${SOUNDFONT.name} has the wrong checksum (${got.slice(0, 12)}…)` }; }
  fs.renameSync(tmp, file);
  return { file };
}

let loaded = null; // { file, bank, lib }
// → { bank, lib } or { error }
export async function loadSoundfont(opts = {}) {
  const r = await ensureSoundfont(opts);
  if (r.error) return r;
  if (loaded?.file === r.file) return loaded;
  let lib;
  try { lib = await import('spessasynth_core'); } catch { return { error: `spessasynth_core is not installed (cd ${path.resolve(path.dirname(new URL(import.meta.url).pathname), '..')} && npm install)` }; }
  try {
    lib.SpessaLog.setLogLevel(false, false, false);
    await lib.BasicSoundBank.isSF3DecoderReady;
    const data = fs.readFileSync(r.file);
    const bank = lib.SoundBankLoader.fromArrayBuffer(data.buffer.slice(data.byteOffset, data.byteOffset + data.byteLength));
    loaded = { file: r.file, bank, lib };
    return loaded;
  } catch (e) {
    return { error: `could not read ${r.file}: ${e.message}` };
  }
}

// ---------------------------------------------------------------------------
// Sampler: one synthesizer per track (a layer, the lead, a family of effects),
// rendered offline with sample-accurate note timing.
// ---------------------------------------------------------------------------
const BLOCK = 512;

export class Sampler {
  constructor(sf, sampleRate) {
    this.sf = sf;
    this.SR = sampleRate;
    this.tracks = [];
  }
  // patch: { program, bank = 0 } for an instrument, { kit } for drums
  // cc: { 74: brightness, 73: attack, 72: release } (64 = as sampled)
  track(patch, cc = {}) {
    const t = { patch, cc, notes: [], ccs: [] };
    this.tracks.push(t);
    return t;
  }
  note(track, t, dur, midi, vel) {
    if (!(dur > 0) || !(vel > 0)) return;
    track.notes.push({ t, dur, midi: Math.round(midi), vel: Math.max(1, Math.min(127, Math.round(vel))) });
  }
  // a controller change at time t (e.g. 74 = brightness, which can follow the energy)
  cc(track, t, num, val) { track.ccs.push({ t, num, val: Math.max(0, Math.min(127, Math.round(val))) }); }
  processor() {
    const { lib, bank } = this.sf;
    const p = new lib.SpessaSynthProcessor(this.SR, { effectsEnabled: false, eventsEnabled: false, maxBufferSize: BLOCK });
    p.soundBankManager.addSoundBank(bank, 'main');
    p.setSystemParameter('autoAllocateVoices', true);
    return p;
  }
  // Render one track to { L, R } (n samples). Sustained notes that repeat the
  // same pitch back to back are tied, so a held pad doesn't re-attack every bar.
  render(track, n, { tie = false } = {}) {
    const p = this.processor();
    const ch = track.patch.kit != null ? 9 : 0;
    if (ch === 9) p.programChange(9, track.patch.kit);
    else { p.controllerChange(0, 0, track.patch.bank ?? 0); p.programChange(0, track.patch.program); }
    for (const [k, v] of Object.entries(track.cc)) p.controllerChange(ch, Number(k), Math.max(0, Math.min(127, Math.round(v))));
    const notes = track.notes.slice().sort((a, b) => a.t - b.t || a.midi - b.midi);
    if (tie) {
      const open = new Map();
      for (const nt of notes) {
        const prev = open.get(nt.midi);
        if (prev && Math.abs(prev.t + prev.dur - nt.t) < 0.03) { prev.dur = nt.t + nt.dur - prev.t; nt.skip = true; continue; }
        open.set(nt.midi, nt);
      }
    }
    const ev = (track.ccs || []).map((c) => ({ i: Math.max(0, Math.round(c.t * this.SR)), k: -1, num: c.num, val: c.val }));
    for (const nt of notes) {
      if (nt.skip) continue;
      const on = Math.max(0, Math.round(nt.t * this.SR)), off = Math.max(on + 1, Math.round((nt.t + nt.dur) * this.SR));
      ev.push({ i: off, k: 0, midi: nt.midi }, { i: on, k: 1, midi: nt.midi, vel: nt.vel });
    }
    // at the same sample: controllers, then note-offs, then note-ons (a repeated note restarts)
    ev.sort((a, b) => a.i - b.i || a.k - b.k);
    const L = new Float32Array(n), R = new Float32Array(n), out = [[L, R]];
    let k = 0, i = 0;
    while (i < n) {
      while (k < ev.length && ev[k].i <= i) {
        const e = ev[k++];
        if (e.k > 0) p.noteOn(ch, e.midi, e.vel); else if (e.k === 0) p.noteOff(ch, e.midi); else p.controllerChange(ch, e.num, e.val);
      }
      const cnt = Math.min(BLOCK, n - i, k < ev.length ? ev[k].i - i : BLOCK);
      p.processSplit(out, L, R, i, cnt);
      i += cnt;
    }
    return { L, R };
  }
  // Loudest 50 ms RMS of one reference note (used to level instruments by role);
  // { mean: true } = its RMS over the whole 1.2 s note
  loudness(patch, midi, cc = {}, { mean = false } = {}) {
    const key = JSON.stringify([patch, midi, cc, mean]);
    this.sf.cal ??= new Map();
    if (this.sf.cal.has(key)) return this.sf.cal.get(key);
    const tr = { patch, cc, notes: [{ t: 0, dur: 1.2, midi, vel: 100 }], ccs: [] };
    const n = Math.round(1.4 * this.SR), { L, R } = this.render(tr, n);
    if (mean) {
      let e = 0;
      const m = Math.round(1.2 * this.SR);
      for (let j = 0; j < m; j++) e += (L[j] * L[j] + R[j] * R[j]) / 2;
      const v = Math.sqrt(e / m) || 1e-6;
      this.sf.cal.set(key, v);
      return v;
    }
    const w = Math.round(0.05 * this.SR);
    let best = 0;
    for (let a = 0; a + w <= n; a += w >> 1) {
      let e = 0;
      for (let j = a; j < a + w; j++) e += (L[j] * L[j] + R[j] * R[j]) / 2;
      best = Math.max(best, Math.sqrt(e / w));
    }
    const v = best || 1e-4;
    this.sf.cal.set(key, v);
    return v;
  }
}
