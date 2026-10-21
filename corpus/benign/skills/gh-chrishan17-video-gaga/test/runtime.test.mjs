// Unit tests for the pure parts of the runtime (no browser needed).
import { test } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';

const src = fs.readFileSync(new URL('../runtime/video-gaga.js', import.meta.url), 'utf8');
const sandbox = { console, URLSearchParams };
sandbox.globalThis = sandbox;
vm.runInNewContext(src, sandbox);
const CV = sandbox.CV;

// Fake 2D context: every character is 1 unit wide (CJK 2) — enough to test breaking rules.
const fakeCtx = { font: '10px x', measureText: (s) => ({ width: Array.from(s).reduce((a, c) => a + (CV.text.isCJK(c) ? 2 : 1), 0) }) };

test('easing endpoints and monotonic bezier', () => {
  for (const k of ['standard', 'enter', 'exit', 'swift', 'gentle', 'outCubic', 'inOutCubic']) {
    assert.equal(CV.ease[k](0), 0, k);
    assert.ok(Math.abs(CV.ease[k](1) - 1) < 1e-6, k);
  }
  const b = CV.ease.bezier(0.2, 0, 0, 1);
  let prev = -1;
  for (let x = 0; x <= 1.0001; x += 0.01) { const y = b(x); assert.ok(y >= prev - 1e-9); prev = y; }
});

test('spring is a pure step response', () => {
  const s = CV.spring(CV.spring.presets.smooth);
  assert.equal(s(0), 0);
  assert.ok(Math.abs(s(3) - 1) < 1e-3);
  assert.equal(s(0.4), s(0.4));
  const v = CV.springTrack(10, [[0, 0], [1, 100], [2, 50]], CV.spring.presets.snappy);
  assert.ok(Math.abs(v - 50) < 1e-3);
});

test('a spring can be given as a damping ratio and a frequency', () => {
  const peak = (s) => { let m = 0; for (let t = 0; t < 3; t += 1 / 240) m = Math.max(m, s(t)); return m; };
  // ratio 1 never overshoots; ratio 0.6 overshoots by exp(-πζ/√(1-ζ²)) ≈ 9.5%
  assert.ok(peak(CV.spring({ ratio: 1, hz: 2 })) <= 1 + 1e-9);
  assert.ok(Math.abs(peak(CV.spring({ ratio: 0.6, hz: 2 })) - (1 + Math.exp((-Math.PI * 0.6) / 0.8))) < 2e-3);
  // Remotion's default (mass 1, damping 10, stiffness 100) is ratio 0.5 at √100/2π Hz
  const a = CV.spring({ stiffness: 100, damping: 10 }), b = CV.spring({ ratio: 0.5, hz: 10 / (2 * Math.PI) });
  for (const t of [0.1, 0.37, 1.2]) assert.ok(Math.abs(a(t) - b(t)) < 1e-9);
});

test('seeded rand is reproducible', () => {
  const a = CV.rand(42), b = CV.rand(42);
  for (let i = 0; i < 10; i++) assert.equal(a(), b());
});

test('CJK wrap obeys kinsoku (no line starts with closing punctuation)', () => {
  const lines = CV.text.wrap(fakeCtx, '画布就是你的摄影棚，每一帧都由代码精确绘制。然后导出成 MP4 视频！', 18);
  assert.ok(lines.length > 1);
  for (const l of lines) assert.ok(!/^[，。、！？）]/.test(l), `bad line start: ${l}`);
  assert.ok(lines.join('').includes('MP4'), 'latin word kept whole');
});

test('zh cues: split at punctuation, strip commas/periods, keep ？', () => {
  const text = '每年多赚 8%，三十年后会怎样？';
  const words = ['每年', '多', '赚', '8%', '三十', '年', '后', '会', '怎样'].map((w, i) => ({ text: w, start: i * 0.3, end: i * 0.3 + 0.25 }));
  const cues = CV.subtitles.build(text, words, { lang: 'zh-CN', minChars: 4 });
  assert.equal(cues.length, 2);
  assert.equal(cues[0].text, '每年多赚 8%');
  assert.equal(cues[1].text, '三十年后会怎样？');
  assert.ok(cues[0].end <= cues[1].start);
});

test('en cues: long sentence splits into balanced chunks, no orphan', () => {
  const text = 'What if your computer could think one step ahead?';
  const ws = text.replace('?', '').split(' ').map((w, i) => ({ text: w, start: i * 0.25, end: i * 0.25 + 0.2 }));
  const cues = CV.subtitles.build(text, ws, { lang: 'en-US', maxChars: 30 });
  assert.equal(cues.length, 2);
  const [a, b] = cues.map((c) => c.text.length);
  assert.ok(Math.abs(a - b) < 12, `unbalanced: ${cues.map((c) => c.text)}`);
  assert.ok(cues[1].text.endsWith('?'));
});

test('zh cues: minChars counts spoken characters, not punctuation', () => {
  const text = '中文、日文、韩文，也能读。';
  const words = ['中文', '日文', '韩文', '也', '能', '读'].map((w, i) => ({ text: w, start: i * 0.4, end: i * 0.4 + 0.3 }));
  const cues = CV.subtitles.build(text, words, { lang: 'zh-CN', minChars: 6 });
  assert.deepEqual(Array.from(cues, (c) => c.text), ['中文 日文 韩文', '也能读']);
});

test('speech end is the last word (+ its decay), not the clip length', () => {
  assert.ok(Math.abs(CV.speech.end({ duration: 2.86, words: [{ text: '读', start: 1.66, end: 1.99 }] }) - 2.24) < 1e-9);
  assert.equal(CV.speech.end({ duration: 1.5, words: [] }), 1.5);
  assert.equal(CV.speech.end({ duration: 1.0, words: [{ text: 'x', start: 0.2, end: 1.3 }] }), 1.0);
});

test('phrase lookup prefers exact words over substrings', () => {
  const ws = ['Press', 'Option', 'S', 'to', 'listen'].map((w, i) => ({ text: w, start: i, end: i + 0.8 }));
  assert.equal(CV.speech.find(ws, 'S'), 2, '"S" must not match inside "Press"');
  assert.equal(CV.speech.find(ws, 'Option S'), 1, 'run of words');
  assert.equal(CV.speech.find(ws, 'opt'), 1, 'substring fallback');
  assert.equal(CV.speech.find(ws, 'nothing'), null);
  const zh = [{ text: '这个', start: 0.1, end: 0.44 }, { text: '词', start: 0.44, end: 0.89 }];
  assert.equal(CV.speech.find(zh, '这个词'), 0.1, 'phrase across CJK words');
});

test('zh cues: a long phrase splits at its clause mark when both halves fit', () => {
  const text = '2023 年，全球最繁忙的机场是哪一座？';
  const words = ['2023', '年', '全球', '最', '繁忙', '的', '机场', '是', '哪一座'].map((w, i) => ({ text: w, start: i * 0.3, end: i * 0.3 + 0.25 }));
  const cues = CV.subtitles.build(text, words, { lang: 'zh-CN' });
  assert.deepEqual(Array.from(cues, (c) => c.text), ['2023 年', '全球最繁忙的机场是哪一座？']);
});

test('speech estimate is plausible', () => {
  const zh = CV.subtitles.estimate('画布就是你的摄影棚。', 'zh-CN');
  assert.ok(zh.duration > 1.5 && zh.duration < 4, String(zh.duration));
  const en = CV.subtitles.estimate('Every frame, drawn by code.', 'en-US');
  assert.ok(en.duration > 1 && en.duration < 3.5, String(en.duration));
});

test('countUp / typewriter formatting', () => {
  assert.equal(CV.fx.countUp(1, 0, 12500), '12,500');
  assert.equal(CV.fx.countUp(0.5, 0, 0.9, { decimals: 1 }), '0.5');
  assert.equal(CV.fx.typewriter('上海见', 2 / 3), '上海');
});

// --- beat grid & pacing (CV.create with a stub canvas, no browser) ------------
function stubCreate(config) {
  const ctx = new Proxy({}, { get: () => () => ({}) });
  class Off { constructor(w, h) { this.width = w; this.height = h; } getContext() { return ctx; } }
  const sb = { console, URLSearchParams, OffscreenCanvas: Off };
  sb.globalThis = sb;
  vm.runInNewContext(src, sb);
  return sb.CV.create({ canvas: new Off(1920, 1080), ...config });
}

// a minimal score spec (the agent designs one per video; there are no preset styles)
const SCORE = { key: 'C', mode: 'major', progression: [0, 5, 3, 4], layers: [{ inst: 'pad', pattern: 'X---', vel: 0.06 }] };

test('cuts land on the beat grid and the video ends on a beat', () => {
  const beat = 60 / 100;
  const api = stubCreate({
    music: { ...SCORE, bpm: 100 },
    transition: { type: 'push', duration: 0.6 },
    scenes: [{ id: 'a', duration: 2.3, draw() {} }, { id: 'b', duration: 3.1, draw() {} }, { id: 'c', narration: false, beats: 6, draw() {} }],
  });
  const [a, b, c] = api.scenes;
  for (const s of [b, c]) {
    const mid = s.start + 0.3;
    assert.ok(Math.abs(mid / beat - Math.round(mid / beat)) < 1e-6, `transition midpoint ${mid} not on a beat`);
  }
  assert.ok(Math.abs(c.end - (c.start + 0.3) - 6 * beat) < 1e-6, 'beats: 6 → six beats from the cut');
  assert.ok(Math.abs(api.duration / beat - Math.round(api.duration / beat)) < 1e-6, 'ends on a beat');
  assert.ok(a.end >= 2.3 && Math.abs(a.end - b.start - 0.6) < 1e-6, 'overlap preserved');
});

test('voice starts on an eighth note; sfx resolve phrases, functions and transitions', () => {
  const words = [{ text: 'Hello', start: 0.1, end: 0.4 }, { text: 'world', start: 0.5, end: 0.9 }];
  const api = stubCreate({
    music: { ...SCORE, bpm: 120 },
    narration: { lang: 'en', segments: { a: { text: 'Hello world', duration: 1, words }, b: { text: 'Hello world', duration: 1, words } } },
    scenes: [
      { id: 'a', sfx: [{ at: 'world', type: 'tick' }, { at: (s) => s.onBeat(2), type: 'pop' }], draw() {} },
      { id: 'b', transition: { type: 'whip', duration: 0.4 }, draw() {} },
    ],
  });
  const half = 60 / 120 / 2;
  for (const s of api.scenes) {
    const onset = s.start + s.voiceDelay + 0.1;
    assert.ok(Math.abs(onset / half - Math.round(onset / half)) < 1e-6, `voice onset ${onset} off the grid`);
  }
  const a = api.scenes[0];
  const tick = api.sfx.find((e) => e.type === 'tick'), pop = api.sfx.find((e) => e.type === 'pop');
  assert.ok(Math.abs(tick.t - (a.start + a.voiceDelay + 0.5)) < 1e-6, 'phrase sfx at the word');
  assert.ok(Math.abs(pop.t - 1.0) < 1e-6, 'function sfx at beat 2');
  assert.ok(api.sfx.some((e) => e.type === 'whoosh' && e.transition), 'whip makes a whoosh');
  const info = api.info();
  assert.equal(info.score.key, 'C');
  assert.deepEqual(info.score.progression, [0, 5, 3, 4]);
  assert.equal(info.score.layers.length, 1);
  assert.equal(info.score.voice.length, 2);
});

test('without music nothing snaps (old compositions keep their timing)', () => {
  const api = stubCreate({ scenes: [{ id: 'a', duration: 2.3, draw() {} }, { id: 'b', duration: 1.7, draw() {} }] });
  assert.equal(api.scenes[1].start, 2.3);
  assert.equal(api.duration, 4);
  assert.equal(api.info().score, null);
});

// --- music synth -----------------------------------------------------------------
// every instrument, note token and pattern feature in one spec
const FULL = {
  bpm: 104, key: 'E', mode: 'dorian', progression: [0, 0, 5, 6], sevenths: true, chordBars: 1, seed: 2,
  layers: [
    { inst: 'pad', notes: 'chord', pattern: 'X---', vel: 0.06, cutoff: [700, 1500] },
    { inst: 'sinepad', notes: 'chord', bars: 2, pattern: 'X-------', vel: 0.05, attack: 1 },
    { inst: 'keys', notes: [0, 1, 2], octave: 1, pattern: '....XXX.', gate: 3, vel: [0.04, 0.08], from: 0.3 },
    { inst: 'pluck', notes: ['root_', 2, 'fifth_', '0^'], pattern: 'XxXx', vel: 0.12, from: 0.2 },
    { inst: 'bell', kind: 'marimba', notes: ['third', 'seventh'], pattern: 'x.x.', vel: 0.08, from: 0.4 },
    { inst: 'bass', synth: true, octave: -1, notes: ['root', 'root^'], pattern: '9898 9898', vel: 0.2, from: 0.3 },
    { inst: 'lead', notes: 'root', octave: 1, pattern: 'X...', vel: 0.05, saw: 0.5, from: 0.6 },
    { inst: 'kick', pattern: 'X...x...X...x...', vel: 0.5, from: 0.5 },
  ],
  lead: { inst: 'bell', kind: 'glock', range: [74, 88], rhythm: 'melodic', vel: 0.1 },
};
const DRUMS = ['snare', 'clap', 'snap', 'rim', 'hat', 'openhat', 'shaker', 'tom'].map((inst) => ({ inst, pattern: '.X.X', vel: 0.08, from: 0.5 }));
const planOf = (spec) => ({ ...spec, duration: 8, sections: [{ start: 0, end: 4, voiced: true, energy: 0.35 }, { start: 4, end: 8, voiced: false, energy: 0.9 }], voice: [{ start: 0.5, end: 3.2 }], sfx: [{ type: 'whoosh', t: 4, dur: 0.6 }, { type: 'hit', t: 6 }] });

test('generated score is deterministic, sized to the video and not clipping', async () => {
  const { renderScore } = await import('../scripts/music.mjs');
  const specs = { full: FULL, drums1: { ...FULL, layers: [FULL.layers[0], ...DRUMS.slice(0, 4)] }, drums2: { ...FULL, layers: [FULL.layers[0], ...DRUMS.slice(4)] }, minimal: { ...SCORE, bpm: 90 }, sfxOnly: { bpm: 100, layers: [] } };
  for (const [name, spec] of Object.entries(specs)) {
    const a = await renderScore(planOf(spec)), b = await renderScore(planOf(spec));
    assert.equal(a.left.length, Math.ceil(8.05 * 48000), name);
    let same = true, peak = 0;
    for (let i = 0; i < a.left.length; i += 97) { if (a.left[i] !== b.left[i] || a.right[i] !== b.right[i]) same = false; peak = Math.max(peak, Math.abs(a.left[i]), Math.abs(a.right[i])); }
    assert.ok(same, `${name} not deterministic`);
    assert.ok(peak > 0.01 && peak <= 1, `${name} peak ${peak}`);
  }
});

test('the score follows the spec: harmony, layers by energy, seed', async () => {
  const { renderScore } = await import('../scripts/music.mjs');
  // 120 BPM (2 s bars), energy 0.35 for 0–8 s and 0.9 for 8–16 s; a kick `from: 0.6`
  // only plays in the second half (the final chord rings from 14 s)
  const pad = { inst: 'pad', notes: 'chord', pattern: 'X---', vel: 0.06 };
  const two = (layers) => renderScore({ ...FULL, bpm: 120, layers, lead: null, duration: 16, sections: [{ start: 0, end: 8, energy: 0.35 }, { start: 8, end: 16, energy: 0.9 }], voice: [], sfx: [] });
  const lift = (x) => {
    let a = 0, b = 0;
    for (let i = 2 * 48000; i < 13.5 * 48000; i += 7) (i < 8 * 48000 ? (a += x.bed.left[i] ** 2) : (b += x.bed.left[i] ** 2));
    return b / a;
  };
  const padOnly = await two([pad]);
  const withKick = await two([pad, { inst: 'kick', pattern: 'X.X.', vel: 0.6, from: 0.6 }]);
  assert.ok(lift(withKick) > lift(padOnly) * 1.3, `the kick enters with the energy (${lift(withKick).toFixed(2)} vs ${lift(padOnly).toFixed(2)})`);
  const unplayed = await two([pad, { inst: 'kick', pattern: 'X.X.', vel: 0.6, from: 0.95 }]);
  assert.ok(Math.abs(lift(unplayed) - lift(padOnly)) < 0.05 * lift(padOnly), 'a layer above every scene\'s energy never plays');
  const a = await renderScore(planOf({ ...FULL, seed: 1 })), b = await renderScore(planOf({ ...FULL, seed: 2 }));
  let diff = 0;
  for (let i = 0; i < a.left.length; i += 97) diff += Math.abs(a.left[i] - b.left[i]);
  assert.ok(diff > 0, 'the seed changes the melody');
  assert.equal(a.report.key, 'E dorian');
  assert.equal(a.report.layers, FULL.layers.length);
});

test('score specs are validated against the limits', async () => {
  const { validateScore, renderScore, LIMITS } = await import('../scripts/music.mjs');
  assert.deepEqual(validateScore({ ...FULL, layers: [...FULL.layers] }).errors, []);
  const errs = (spec) => validateScore(spec).errors.join('\n');
  assert.match(errs({ ...FULL, style: 'explainer' }), /no preset styles/);
  assert.match(errs({ ...FULL, bpm: 200 }), /music\.bpm/);
  assert.match(errs({ ...FULL, key: 'H' }), /music\.key/);
  assert.match(errs({ ...FULL, mode: 'blues' }), /music\.mode/);
  assert.match(errs({ ...FULL, progression: [0, 9] }), /progression\[1\]/);
  assert.match(errs({ ...FULL, progression: [] }), /progression/);
  assert.match(errs({ ...FULL, layers: Array(LIMITS.layers + 1).fill(FULL.layers[0]) }), /at most/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kazoo', pattern: 'X' }] }), /inst must be/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kick', pattern: 'X..?', vel: 0.5 }] }), /pattern has '\?'/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kick', pattern: '-X..', vel: 0.5 }] }), /starts with a hold/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kick', pattern: 'X'.repeat(33), vel: 0.5 }] }), /steps per bar/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kick', pattern: 'X...', vel: 0.9 }] }), /vel must be in \(0, 0\.7\]/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'kick', pattern: 'X...', vel: 0.5, notes: 'root' }] }), /drum and has no notes/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'pad', pattern: 'X---', vel: 0.05, notes: ['ninth'] }] }), /not a note/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'pad', pattern: 'X---', vel: 0.05, bright: 0.5 }] }), /not an option for pad/);
  assert.match(errs({ ...FULL, layers: [{ inst: 'pad', pattern: 'X---', vel: 0.05, cutoff: [100, 99999] }] }), /cutoff/);
  assert.match(errs({ ...FULL, layers: Array(3).fill({ inst: 'hat', pattern: 'X'.repeat(16), vel: 0.05 }) }), /drum hits per bar/);
  assert.match(errs({ ...FULL, lead: { inst: 'pad', range: [60, 80], rhythm: 'sparse', vel: 0.1 } }), /lead\.inst/);
  assert.match(errs({ ...FULL, lead: { inst: 'keys', range: [60, 64], rhythm: 'sparse', vel: 0.1 } }), /lead\.range/);
  assert.match(errs({ ...FULL, tempo: 100 }), /music\.tempo is not a score option/);
  // musical advice is a warning, not an error
  const w = validateScore({ ...FULL, layers: [{ inst: 'kick', pattern: 'X...', vel: 0.5 }, { inst: 'bass', pattern: 'X---', vel: 0.2 }] });
  assert.deepEqual(w.errors, []);
  assert.ok(w.warnings.some((x) => /no harmony/.test(x)));
  // a drone with a low tom heartbeat is the classic horror bed: warn
  const eerie = validateScore({ ...FULL, layers: [{ inst: 'sinepad', pattern: 'X---', vel: 0.05 }, { inst: 'tom', pitch: 62, pattern: 'X..x....', vel: 0.3, from: 0.5 }] });
  assert.ok(eerie.warnings.some((x) => /heartbeat/.test(x)), eerie.warnings.join('; '));
  assert.ok(validateScore({ ...FULL, layers: [{ inst: 'strings', pattern: 'X---', vel: 0.05 }, { inst: 'bass', pattern: 'X---', vel: 0.2 }] }).warnings.some((x) => /drone/.test(x)));
  await assert.rejects(() => renderScore(planOf({ ...FULL, bpm: 10 })), /music\.bpm/);
});

test('music.style is rejected: the score is designed per video', () => {
  assert.throws(() => stubCreate({ music: { style: 'explainer', bpm: 100 }, scenes: [{ id: 'a', duration: 2, draw() {} }] }), /no preset music styles/);
  assert.throws(() => stubCreate({ music: { ...SCORE }, scenes: [{ id: 'a', duration: 2, draw() {} }] }), /music\.bpm is required/);
  assert.throws(() => stubCreate({ scenes: [] }), /no scenes yet/);
});

test('music options reach the score plan', () => {
  const api = stubCreate({ music: { ...SCORE, bpm: 80, duck: -15, gap: 5, volume: 1.2, seed: 9, chordBars: 2, fills: false }, scenes: [{ id: 'a', duration: 3, draw() {} }] });
  const sc = api.info().score;
  assert.equal(sc.duck, -15);
  assert.equal(sc.gap, 5);
  assert.equal(sc.volume, 1.2);
  assert.equal(sc.seed, 9);
  assert.equal(sc.chordBars, 2);
  assert.equal(sc.fills, false);
  assert.equal(sc.mode, 'major');
});

test('scene timing ends at the last spoken word, not the clip end', () => {
  const words = [{ text: 'One', start: 0.1, end: 0.6 }, { text: 'two', start: 1.4, end: 2.2 }];
  assert.ok(Math.abs(CV.speech.end({ duration: 3.0, words }) - 2.45) < 1e-9, 'last word + 0.25 s');
  assert.equal(CV.speech.end({ duration: 2.3, words }), 2.3, 'never longer than the clip');
  assert.equal(CV.speech.end({ duration: 3.0, words, estimated: true }), 3.0, 'estimates keep their length');
  const api = stubCreate({ narration: { lang: 'en', segments: { a: { text: 'One two', duration: 3.0, words } } }, scenes: [{ id: 'a', voiceDelay: 0.5, tail: 0.5, draw() {} }] });
  assert.ok(Math.abs(api.scenes[0].dur - (0.5 + 2.45 + 0.5)) < 1e-9);
});

test('music parts: a scene part holds until the next one, and a new part starts on a bar', () => {
  const bar = (60 / 100) * 4;
  const api = stubCreate({
    music: { ...SCORE, bpm: 100, parts: { low: { mode: 'minor', progression: [0, 5] }, lift: { progression: [5, 3, 0, 4] } } },
    transition: { type: 'push', duration: 0.6 },
    scenes: [
      { id: 'a', duration: 2.3, draw() {} },
      { id: 'b', part: 'low', duration: 3.1, draw() {} },
      { id: 'c', duration: 1.7, draw() {} },
      { id: 'd', part: 'lift', duration: 2.2, draw() {} },
    ],
  });
  const [, b, c, d] = api.scenes;
  for (const s of [b, d]) {
    const mid = s.start + 0.3;
    assert.ok(Math.abs(mid / bar - Math.round(mid / bar)) < 1e-6, `chapter cut ${mid} not on a bar line`);
  }
  const beat = 60 / 100, cm = c.start + 0.3;
  assert.ok(Math.abs(cm / beat - Math.round(cm / beat)) < 1e-6 && Math.abs(cm / bar - Math.round(cm / bar)) > 1e-6, 'other cuts stay on the beat');
  const sc = api.info().score;
  assert.deepEqual(sc.sections.map((s) => s.part ?? null), [null, 'low', 'low', 'lift']);
  assert.equal(sc.parts.low.mode, 'minor');
  assert.throws(() => stubCreate({ music: { ...SCORE, bpm: 100, parts: {} }, scenes: [{ id: 'a', part: 'nope', duration: 2, draw() {} }] }), /part 'nope' is not defined/);
});

test('music parts change the harmony from their bar, and are validated', async () => {
  const { renderScore, validateScore } = await import('../scripts/music.mjs');
  const bar = (60 / 120) * 4;
  const plan = (parts, secParts) => ({ ...FULL, bpm: 120, lead: { inst: 'bell', range: [72, 86], rhythm: 'melodic', vel: 0.1 }, ...(parts ? { parts } : {}), duration: 8 * bar,
    sections: [{ start: 0, end: 4 * bar, energy: 0.5, part: secParts[0] }, { start: 4 * bar, end: 8 * bar, energy: 0.5, part: secParts[1] }], voice: [], sfx: [] });
  const parts = { b: { key: 'A', mode: 'minor', progression: [5], seed: 3, lead: { rhythm: 'sparse' } } };
  const same = await renderScore(plan(parts, [undefined, undefined])), moved = await renderScore(plan(parts, [undefined, 'b']));
  assert.deepEqual(moved.report.parts, ['main@1', 'b@5']);
  // the mix is levelled as a whole, so compare after matching the gain
  const misfit = (a0, a1) => {
    let ab = 0, bb = 0, d = 0, n = 0;
    for (let i = a0; i < a1; i += 13) { ab += same.left[i] * moved.left[i]; bb += moved.left[i] ** 2; }
    const k = ab / bb;
    for (let i = a0; i < a1; i += 13) { d += Math.abs(same.left[i] - k * moved.left[i]); n += Math.abs(same.left[i]); }
    return d / n;
  };
  assert.ok(misfit(0, 3.5 * bar * 48000) < 0.01, 'bars before the part are unchanged');
  assert.ok(misfit(5 * bar * 48000, 7 * bar * 48000) > 0.3, 'the part changes what plays');
  const errs = (p, secParts = [undefined, 'b']) => validateScore(plan(p, secParts)).errors.join('\n');
  assert.equal(errs(parts), '');
  assert.match(errs({ b: { layers: [] } }), /parts\.b\.layers is not a part option/);
  assert.match(errs({ b: { progression: [9] } }), /parts\.b\.progression\[0\]/);
  assert.match(errs({ b: { lead: { rhythm: 'waltz' } } }), /parts\.b\.lead\.rhythm/);
  assert.match(errs({ c: {} }), /part 'b' is not in music\.parts/);
  // one loop for minutes on end gets a warning
  const long = await renderScore({ ...SCORE, bpm: 120, duration: 90, sections: [{ start: 0, end: 90, energy: 0.5 }], voice: [], sfx: [] });
  assert.ok(long.report.warnings.some((w) => /music\.parts/.test(w)));
});

test('a held synth note stays in tune (the sinepad vibrato bug)', async () => {
  const { _internals } = await import('../scripts/music.mjs');
  const { I, Mixer, SR } = _internals;
  const m = new Mixer(SR * 7);
  I.sinepad(m, m.bed, 0, 6, 62, { vel: 0.1, attack: 0.05 }); // D4 ≈ 293.7 Hz for 6 s
  const x = m.bed.L;
  for (const t of [0.5, 3, 5.5]) {
    const a = Math.round(t * SR), zc = [];
    for (let i = a + 1; i < a + SR / 4; i++) if (x[i - 1] < 0 && x[i] >= 0) zc.push(i - x[i] / (x[i] - x[i - 1]));
    const f = (SR * (zc.length - 1)) / (zc.at(-1) - zc[0]);
    assert.ok(Math.abs(1200 * Math.log2(f / 293.66)) < 15, `pitch at ${t}s is ${f.toFixed(1)} Hz`);
  }
});

test('the melody puts chord tones on its strong beats', async () => {
  const { renderScore } = await import('../scripts/music.mjs');
  const trace = [];
  const bar = (60 / 96) * 4;
  await renderScore({ bpm: 96, key: 'Eb', mode: 'major', progression: [0, 4, 5, 3], seed: 4,
    layers: [{ inst: 'piano', notes: 'chord', pattern: 'X---', vel: 0.1 }], lead: { inst: 'bell', range: [72, 88], rhythm: 'melodic', vel: 0.1 },
    duration: 16 * bar, sections: [{ start: 0, end: 16 * bar, energy: 0.6 }], voice: [], sfx: [] }, { engine: 'synth', trace });
  const chordAt = (t) => { const k = Math.floor((t + 0.02) / bar); return trace.filter((x) => x.id === 'L0' && Math.abs(x.t - k * bar) < 0.03).map((x) => x.midi % 12); };
  const lead = trace.filter((x) => x.id.startsWith('lead'));
  assert.ok(lead.length > 20, `${lead.length} melody notes`);
  let strong = 0, inChord = 0;
  for (const x of lead) {
    const beat = (x.t + 0.01) / (60 / 96), pos = beat % 4;
    if (Math.abs(pos - Math.round(pos)) > 0.03 || Math.round(pos) % 2) continue;
    strong++;
    if (chordAt(x.t + 0.01).includes(x.midi % 12)) inChord++;
  }
  assert.ok(strong > 5 && inChord === strong, `${inChord}/${strong} strong-beat notes are chord tones`);
});

test('sampled instruments: deterministic, in time, and every instrument sounds', async (t) => {
  const { loadSoundfont } = await import('../scripts/soundfont.mjs');
  const sf = await loadSoundfont({ download: false });
  if (sf.error) return t.skip(`no instrument samples here (${sf.error})`);
  const { renderScore, INSTRUMENTS } = await import('../scripts/music.mjs');
  const spec = { bpm: 120, key: 'G', mode: 'major', progression: [0, 4], kit: 'room',
    layers: [{ inst: 'piano', notes: 'chord', pattern: 'X...', vel: 0.15 }, { inst: 'kick', pattern: 'X...', vel: 0.6 }],
    duration: 4, sections: [{ start: 0, end: 4, energy: 0.8 }], voice: [], sfx: [{ type: 'riser', t: 2, dur: 1 }, { type: 'hit', t: 2 }] };
  const a = await renderScore(spec), b = await renderScore(spec);
  assert.equal(a.report.engine, 'samples');
  let same = true;
  for (let i = 0; i < a.left.length; i += 31) if (a.left[i] !== b.left[i]) same = false;
  assert.ok(same, 'sampled render is deterministic');
  // the first kick lands on the downbeat of bar 1 (bar 0 is held back to 0.3 energy)
  const onset = (x, from) => { for (let i = Math.round(from * 48000); i < x.length; i++) if (Math.abs(x[i]) > 0.05) return i / 48000; return null; };
  assert.ok(Math.abs(onset(a.bed.left, 1.9) - 2) < 0.02, `kick onset ${onset(a.bed.left, 1.9)}`);
  // every pitched instrument and drum produces sound
  for (const inst of [...INSTRUMENTS.pitched, ...INSTRUMENTS.drums]) {
    const drum = INSTRUMENTS.drums.includes(inst);
    const L = { inst, pattern: 'X...', vel: 0.1, ...(drum ? {} : { notes: inst === 'bass' ? 'root' : 'chord' }) };
    const r = await renderScore({ bpm: 120, key: 'C', mode: 'major', progression: [0], layers: [L], intro: 'full', ending: 'none', duration: 2, sections: [{ start: 0, end: 2, energy: 0.8 }], voice: [], sfx: [] }, { targetDb: -30 });
    let e = 0;
    for (let i = 0; i < r.left.length; i += 7) e += r.left[i] ** 2;
    assert.ok(e > 1e-4, `${inst} is silent`);
  }
});

test('motion-blur subframes never reach across a hard cut', () => {
  const drawn = [];
  const scene = (id) => ({ id, duration: 1, narration: false, draw: (c, s) => drawn.push([id, s.t]) });
  const api = stubCreate({ fps: 30, transition: 'cut', scenes: [scene('a'), scene('b')] });
  const at = (f, sub) => { drawn.length = 0; api.drawFrame(f, sub); return drawn[0][0]; };
  assert.equal(at(29, 0.4), 'a', 'the last frame before the cut stays in its scene');
  assert.equal(at(30, -0.4), 'b', 'the first frame after the cut stays in its scene');
  assert.equal(at(15, 0.4), 'a');
  api.drawFrame(0, -0.4);
  assert.ok(drawn.at(-1)[1] >= 0, 'never before the start');
});

test('color.mix keeps endpoints and mixes in OKLab (no muddy midpoint)', () => {
  const rgb = (s) => s.match(/[\d.]+/g).map(Number);
  assert.deepEqual(rgb(CV.color.mix('#E4572E', '#1A2746', 0)).slice(0, 3), [0xE4, 0x57, 0x2E]);
  assert.deepEqual(rgb(CV.color.mix('#E4572E', '#1A2746', 1)).slice(0, 3), [0x1A, 0x27, 0x46]);
  const [r, g] = rgb(CV.color.mix('#ff0000', '#00ff00', 0.5));
  assert.ok(r + g > 300, `red→green midpoint should stay bright, got ${r},${g}`);
  assert.equal(rgb(CV.color.mix('rgba(0,0,0,0)', '#fff', 0.5))[3], 0.5, 'alpha is linear');
});

test('cameraAt: keyed, zoom even in log space, fields hold', () => {
  const keys = [[0, { zoom: 1, x: 10 }], [2, { zoom: 4 }, CV.ease.linear]];
  assert.equal(CV.draw.cameraAt(0, keys).zoom, 1);
  assert.ok(Math.abs(CV.draw.cameraAt(1, keys).zoom - 2) < 1e-9, 'halfway from 1× to 4× is 2×');
  assert.equal(CV.draw.cameraAt(1, keys).x, 10, 'x holds when a key leaves it out');
  assert.equal(CV.draw.cameraAt(5, keys).zoom, 4);
  assert.equal(CV.draw.cameraAt(1, keys).focusX, undefined);
});

test('written lines: parsed in beats, bar-checked, validated against range and key', async () => {
  const { _internals, validateScore } = await import('../scripts/music.mjs');
  const { parseLine } = _internals;
  const a = parseLine('E5:1 D5 C5:.5 r:1.5 | [A3 C4 E4]:2 G4:1@1.2 G4:1/2 r:1/2');
  assert.equal(a.bars, 2);
  assert.deepEqual(a.events.map((e) => e.b), [0, 1, 2, 4, 6, 7]);
  assert.deepEqual(a.events[3].midis, [57, 60, 64]);
  assert.equal(a.events[1].len, 1); // a length carries over until changed
  assert.equal(a.events[4].acc, 1.2);
  assert.match(parseLine('E5:1 D5 | G4:4').error, /has 2 beats/);
  assert.match(parseLine('E5:3').error, /whole number/);
  assert.match(parseLine('H5:1').error, /can't read/);
  assert.equal(parseLine('C4:4', 3).error?.includes('whole number'), true);
  const base = { bpm: 90, key: 'C', mode: 'major', progression: [0, 3, 4, 0], layers: [{ inst: 'piano', notes: 'chord', pattern: 'X...', vel: 0.1 }] };
  assert.deepEqual(validateScore({ ...base, lead: { inst: 'violin', vel: 0.1, line: 'E5:2 G5:2 | C6:4' } }).errors, []);
  assert.ok(validateScore({ ...base, lead: { inst: 'violin', vel: 0.1, line: 'E8:4' } }).errors.some((e) => /within MIDI/.test(e)));
  assert.ok(validateScore({ ...base, lead: { inst: 'violin', vel: 0.1, line: 'C#5 D#5 F#5 G#5' } }).warnings.some((w) => /outside C major/.test(w)));
  assert.ok(validateScore({ ...base, layers: [{ inst: 'cello', line: 'C3:4', pattern: 'X...', vel: 0.1 }] }).errors.some((e) => /either a written/.test(e)));
  assert.ok(validateScore({ ...base, layers: [{ inst: 'kick', line: 'C3:4', vel: 0.1 }] }).errors.some((e) => /is a drum/.test(e)));
  // a part that changes the harmony needs its own written lines
  const parted = { ...base, layers: [...base.layers, { name: 'cello', inst: 'cello', line: 'C3:4', vel: 0.1 }], lead: { inst: 'violin', vel: 0.1, line: 'E5:4' }, parts: { b: { key: 'A', mode: 'minor' } } };
  const v = validateScore(parted);
  assert.ok(v.warnings.some((w) => /plays music.lead.line/.test(w)) && v.warnings.some((w) => /keeps its written line/.test(w)));
  const fixed = validateScore({ ...parted, parts: { b: { key: 'A', mode: 'minor', lead: { line: 'A5:4' }, lines: { cello: 'A2:4' } } } });
  assert.deepEqual([fixed.errors, fixed.warnings.filter((w) => /line/.test(w))], [[], []]);
  assert.ok(validateScore({ ...parted, parts: { b: { lines: { nope: 'A2:4' } } } }).errors.some((e) => /no layer named 'nope'/.test(e)));
});

test('written lines play as written: the lead in the gaps, a layer looping, a part rewriting it', async () => {
  const { renderScore } = await import('../scripts/music.mjs');
  const bar = 2; // 120 BPM, 4/4
  const trace = [];
  await renderScore({ bpm: 120, key: 'C', mode: 'major', progression: [0, 5], intro: 'full',
    layers: [{ name: 'cello', inst: 'cello', line: 'C3:2 G2:2 | A2:4', vel: 0.1 }],
    lead: { inst: 'flute', vel: 0.1, line: 'E5:1 D5:1 C5:2 | r:4' },
    duration: 9 * bar, sections: [{ start: 0, end: 9 * bar, energy: 0.6 }], voice: [{ start: 2 * bar, end: 3 * bar }], sfx: [] }, { engine: 'synth', trace });
  const cello = trace.filter((x) => x.inst === 'cello' && x.t < 4 * bar);
  assert.deepEqual(cello.map((x) => x.midi), [48, 43, 45, 48, 43, 45]);
  assert.ok(cello.every((x, i) => Math.abs(x.t - [0, 1, 2, 4, 5, 6][i]) < 0.02), cello.map((x) => x.t).join(' '));
  const lead = trace.filter((x) => x.id.startsWith('lead'));
  // bars 0, 2, 4, 6 hold the notes; bar 2 is spoken over, so it is skipped
  assert.deepEqual([...new Set(lead.map((x) => Math.floor((x.t + 0.05) / bar)))], [0, 4, 6]);
  assert.deepEqual(lead.slice(0, 3).map((x) => x.midi), [76, 74, 72]);
  // a part rewrites the layer's line from the bar it starts on
  const t2 = [];
  await renderScore({ bpm: 120, key: 'C', mode: 'major', progression: [0, 5], intro: 'full',
    layers: [{ name: 'cello', inst: 'cello', line: 'C3:2 G2:2 | A2:4', vel: 0.1 }], parts: { b: { key: 'A', mode: 'minor', lines: { cello: 'E2:4' } } },
    duration: 9 * bar, sections: [{ start: 0, end: 3 * bar, energy: 0.6 }, { start: 3 * bar, end: 9 * bar, energy: 0.6, part: 'b' }], voice: [], sfx: [] }, { engine: 'synth', trace: t2 });
  const c2 = t2.filter((x) => x.inst === 'cello' && x.t < 5 * bar).map((x) => x.midi);
  assert.deepEqual(c2, [48, 43, 45, 48, 43, 40, 40]);
});

test('recorded sound effects: every type sounds, repeats vary, renders stay deterministic', async () => {
  const { renderScore, sfxTypes } = await import('../scripts/music.mjs');
  for (const t of ['tick', 'click', 'type', 'pop', 'paper', 'card', 'book', 'cloth', 'wood', 'glass', 'metal', 'thud', 'step']) assert.ok(sfxTypes.includes(t), t);
  const plan = { bpm: 100, layers: [], duration: 8, sections: [{ start: 0, end: 8, energy: 0.5 }], voice: [],
    sfx: sfxTypes.map((type, i) => ({ type, t: 0.3 + i * 0.25 })) };
  const a = await renderScore(plan, { engine: 'synth' }), b = await renderScore(plan, { engine: 'synth' });
  let same = true;
  for (let i = 0; i < a.left.length; i += 13) if (a.left[i] !== b.left[i]) same = false;
  assert.ok(same, 'deterministic');
  for (const [i, type] of sfxTypes.entries()) {
    if (['riser', 'swell', 'shimmer', 'chime', 'hit', 'boom', 'whoosh', 'swish'].includes(type)) continue; // overlap their neighbours
    let e = 0;
    for (let k = Math.round((0.3 + i * 0.25 - 0.1) * 48000); k < Math.round((0.3 + i * 0.25 + 0.12) * 48000); k++) e += a.left[k] ** 2;
    assert.ok(e > 1e-5, `${type} is silent`);
  }
  // three ticks in a row are three different takes
  const ticks = await renderScore({ ...plan, sfx: [0.5, 1.5, 2.5].map((t) => ({ type: 'tick', t })) }, { engine: 'synth' });
  const shape = (t) => Array.from({ length: 200 }, (_, k) => ticks.left[Math.round(t * 48000) - 400 + k * 4]);
  const s = [0.5, 1.5, 2.5].map(shape), diff = (x, y) => x.reduce((acc, v, k) => acc + Math.abs(v - y[k]), 0);
  assert.ok(diff(s[0], s[1]) > 1e-3 && diff(s[1], s[2]) > 1e-3);
});

test('listening checks: a held, washed-out passage is flagged; a pulse is not', async () => {
  const { renderScore } = await import('../scripts/music.mjs');
  const { loadSoundfont } = await import('../scripts/soundfont.mjs');
  if ((await loadSoundfont({ download: false })).error) return; // the ghost check needs the sampled engine
  const base = { bpm: 66, key: 'D', mode: 'minor', progression: [0, 5, 3, 4], duration: 16, sections: [{ start: 0, end: 16, energy: 0.6 }], voice: [], sfx: [{ type: 'tick', t: 5 }] };
  const ghost = await renderScore({ ...base, layers: [{ inst: 'choir', notes: 'chord', pattern: 'X---', vel: 0.1, verb: 0.9 }, { inst: 'synthpad', notes: 'chord', pattern: 'X---', vel: 0.1, verb: 0.9 }] }, { multi: false });
  assert.ok(ghost.report.listen.ghost.length >= 1, JSON.stringify(ghost.report.listen));
  assert.ok(ghost.report.warnings.some((w) => /ghostly/.test(w)));
  const alive = await renderScore({ ...base, layers: [{ inst: 'piano', notes: [0, 1, 2, 1], pattern: 'x.x.x.x.', vel: 0.12 }, { inst: 'kick', pattern: 'X...X...', vel: 0.4 }, { inst: 'hat', pattern: 'x.x.x.x.', vel: 0.06 }] }, { multi: false });
  assert.deepEqual(alive.report.listen.ghost, []);
  assert.ok(alive.report.listen.sfxDb.median > 0, 'a tick over a light groove is heard');
  assert.ok(typeof alive.report.listen.rangeLU === 'number');
});

test('a written score (music.script) plays its own notes on the timeline, with the scenes\' sounds', async () => {
  const { renderScore, validateScore } = await import('../scripts/music.mjs');
  const os = await import('node:os');
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-score-'));
  const file = path.join(dir, 'score.mjs');
  fs.writeFileSync(file, `export default function score(S) {
    // a chord on every bar, a line from the spoken word, silence from 4 to 6 s
    for (let bar = 0; bar < 4; bar++) S.chord(S.at(bar), 'piano', ['C3', 'E3', 'G3'], S.bar * 0.9, 0.15);
    S.line(S.when('a', 'world'), 'bell', 'C5:1 E5 G5 C6', 0.12, { kind: 'glock' });
    S.hole(4, 6);
    S.fx('tick', S.at(3, 2));
    if (Math.abs(S.event('b', 'whoosh') - 4) > 1e-9 || Math.abs(S.barAt(S.at(2, 2)) - 2.5) > 1e-9) throw new Error('timeline');
  }`);
  const plan = (script) => ({
    bpm: 120, key: 'C', mode: 'major', script, layers: [], duration: 8,
    sections: [{ id: 'a', start: 0, end: 4, energy: 0.4, voiced: true, words: [{ text: 'hello', t: 0.5, end: 0.9 }, { text: 'world', t: 1, end: 1.4 }] }, { id: 'b', start: 4, end: 8, energy: 0.6, voiced: false }],
    voice: [{ start: 0.5, end: 1.4 }], sfx: [{ type: 'whoosh', t: 4, dur: 0.6, scene: 'b' }],
  });
  const x = await renderScore(plan(file));
  const rms = (buf, a, b) => { let e = 0; for (let i = Math.round(a * 48000); i < b * 48000; i++) e += buf[i] ** 2; return Math.sqrt(e / ((b - a) * 48000)); };
  assert.ok(rms(x.bed.left, 2, 3.5) > 1e-3, 'the notes play');
  assert.ok(rms(x.bed.left, 4.3, 5.8) < 1e-5, 'a hole silences the music');
  assert.ok(rms(x.left, 3.6, 4.4) > rms(x.bed.left, 3.6, 4.4), 'the scene\'s whoosh still plays');
  assert.equal(x.report.script, 'score.mjs');
  assert.deepEqual(x.report.placedSfx, ['whoosh@4.00', 'tick@7.00']);
  fs.writeFileSync(path.join(dir, 'bad.mjs'), `export default (S) => S.when('a', 'nobody said this');`);
  await assert.rejects(() => renderScore(plan(path.join(dir, 'bad.mjs'))), /not spoken in scene 'a'/);
  assert.match(validateScore({ bpm: 120, key: 'C', script: 'score.mjs', layers: [{ inst: 'kick', pattern: 'X...', vel: 0.3 }] }).errors.join(' '), /writes the whole score/);
  assert.deepEqual(validateScore({ bpm: 120, key: 'C', script: 'score.mjs' }).errors, []);
});
