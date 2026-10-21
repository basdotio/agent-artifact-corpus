// Timeline + caption resolution inside CV.create (needs a DOM, so it runs in
// headless Chromium): voiced scenes are sized from the last spoken word (plus
// 0.25 s for its final syllable to decay, never past the clip), and
// scene.captions controls whether cues are burned, exported, or dropped.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
let chromium;
try { ({ chromium } = await import('playwright')); } catch { /* skipped below */ }

test('voice timeline and per-scene captions', { skip: !chromium && 'playwright not installed', timeout: 60000 }, async (t) => {
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) { t.skip(`chromium unavailable: ${e.message.split('\n')[0]}`); return; }
  try {
    const page = await browser.newPage();
    await page.goto('about:blank');
    await page.evaluate(() => { window.__CV_RENDER__ = true; });   // no preview player
    await page.addScriptTag({ path: path.join(ROOT, 'runtime', 'video-gaga.js') });
    const r = await page.evaluate(() => {
      const seg = (text, words, duration) => ({ text, duration, words: words.map(([w, s, e]) => ({ text: w, start: s, end: e })) });
      const narration = {
        lang: 'en-US',
        segments: {
          a: seg('Select a word.', [['Select', 0.1, 0.5], ['a', 0.5, 0.6], ['word', 0.6, 1.0]], 1.9),   // 0.9 s trailing silence
          b: seg('Press Option S.', [['Press', 0.1, 0.4], ['Option', 0.45, 0.9], ['S', 0.95, 1.2]], 2.0),
          c: seg('Hear it.', [['Hear', 0.1, 0.4], ['it', 0.4, 0.6]], 1.5),
        },
      };
      const noop = () => {};
      const api = window.CV.create({
        width: 320, height: 180, narration, tail: 0.5,
        scenes: [
          { id: 'a', voiceDelay: 0.2, draw: noop },
          { id: 'b', voiceDelay: 0.2, captions: 'file', draw(ctx, s) { window.__b = { voiceEnd: s.voiceEnd, whenS: s.when('S') }; } },
          { id: 'c', voiceDelay: 0.2, captions: false, draw: noop },
        ],
      });
      api.drawAt(api.scenes[1].start + 0.5);
      return { scenes: api.info().scenes, cues: api.cues.map((c) => ({ text: c.text, burn: c.burn !== false })), infoCues: api.info().cues.map((c) => c.text), b: window.__b };
    });
    const [a, b, c] = r.scenes;
    assert.ok(Math.abs(a.dur - (0.2 + 1.0 + 0.25 + 0.5)) < 1e-9, `scene a sized from last word: ${a.dur}`);
    assert.ok(Math.abs(b.dur - (0.2 + 1.2 + 0.25 + 0.5)) < 1e-9, `scene b: ${b.dur}`);
    assert.ok(Math.abs(c.dur - (0.2 + 0.6 + 0.25 + 0.5)) < 1e-9, `scene c: ${c.dur}`);
    assert.ok(Math.abs(r.b.voiceEnd - (0.2 + 1.2 + 0.25)) < 1e-9, `voiceEnd = last word + decay: ${r.b.voiceEnd}`);
    assert.ok(Math.abs(r.b.whenS - (0.2 + 0.95)) < 1e-9, `when('S') hits the word S: ${r.b.whenS}`);
    assert.deepEqual(r.cues, [{ text: 'Select a word.', burn: true }, { text: 'Press Option S.', burn: false }]);
    assert.deepEqual(r.infoCues, ['Select a word.', 'Press Option S.'], "'file' cues are exported, false cues are not");
  } finally {
    await browser.close();
  }
});

// One take (narration.track from `gaga voicetrack`): slices of one recording play
// back to back, so each voice starts exactly where its slice starts in the take,
// whatever the transitions, and no cut or voice is moved onto the beat.
test('one take: scenes follow the track', { skip: !chromium && 'playwright not installed', timeout: 60000 }, async (t) => {
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) { t.skip(`chromium unavailable: ${e.message.split('\n')[0]}`); return; }
  try {
    const page = await browser.newPage();
    await page.goto('about:blank');
    await page.evaluate(() => { window.__CV_RENDER__ = true; });
    await page.addScriptTag({ path: path.join(ROOT, 'runtime', 'video-gaga.js') });
    const r = await page.evaluate(() => {
      const seg = (text, words, duration) => ({ text, duration, words: words.map(([w, s, e]) => ({ text: w, start: s, end: e })) });
      const narration = {
        lang: 'en-US',
        segments: {
          a: seg('One.', [['One', 0.3, 0.8]], 2.0),
          b: seg('Two words.', [['Two', 0.35, 0.7], ['words', 0.7, 1.4]], 2.5),
          c: seg('Three.', [['Three', 0.4, 0.9]], 1.5),
        },
        track: { duration: 6.0, segments: { a: [0, 2.0], b: [2.0, 4.5], c: [4.5, 6.0] } },
      };
      const noop = () => {};
      const api = window.CV.create({
        width: 320, height: 180, narration, tail: 0.7,
        music: { bpm: 100, snap: 'beat', layers: [] },
        scenes: [
          { id: 'intro', narration: false, duration: 1.6, draw: noop },
          { id: 'a', voiceDelay: 0.9, transition: { type: 'fade', duration: 0.5 }, draw: noop },
          { id: 'b', transition: { type: 'push', direction: 'up', duration: 0.6 }, draw: noop },
          { id: 'c', draw: noop },
        ],
      });
      return api.info().scenes;
    });
    const v = Object.fromEntries(r.map((s) => [s.id, s]));
    const near = (x, y, msg) => assert.ok(Math.abs(x - y) < 1e-6, `${msg}: ${x} vs ${y}`);
    near(v.b.voiceStart - v.a.voiceStart, 2.0, 'b plays right after slice a');
    near(v.c.voiceStart - v.b.voiceStart, 2.5, 'c plays right after slice b');
    near(v.b.start + 0.3, v.a.voiceStart + 2.0, 'the push into b is centred on the slice boundary');
    assert.ok(v.c.start + v.c.dur >= v.c.voiceStart + 0.9 + 0.25 + 0.7 - 1e-6, 'the last slice still holds its tail');
  } finally {
    await browser.close();
  }
});
