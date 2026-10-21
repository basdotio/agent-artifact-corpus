// gaga render tells a reading hold (still while words on screen are read) from
// a dead one: a still frame with no words, or one held far longer than reading takes.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const ROOT = new URL('..', import.meta.url).pathname;
const gaga = path.join(ROOT, 'scripts', 'gaga.mjs');
const hasFfmpeg = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0;
let chromium;
try { ({ chromium } = await import('playwright')); } catch { /* skipped below */ }

// a square that moves, except while it holds: 1–3 s with a line to read,
// 4–6 s with nothing on screen, 7–11 s with one word held far too long
const html = `<!doctype html><html><body><script src="video-gaga.js"></script><script>
const holds = [[1, 3, 'A line with five words'], [4, 6, ''], [7, 11, 'Hi']];
CV.create({
  width: 1920, height: 1080, fps: 30, background: '#fff', lang: 'en',
  scenes: [{
    id: 'holds', duration: 12,
    draw(ctx, s) {
      const h = holds.find(([a, b]) => s.t >= a && s.t < b);
      const moving = holds.reduce((t, [a, b]) => t - Math.max(0, Math.min(s.t, b) - a), s.t);
      ctx.fillStyle = '#000';
      ctx.fillRect(200 + moving * 200, 700, 120, 120);
      if (h && h[2]) { ctx.font = '120px sans-serif'; ctx.fillText(h[2], 200, 400); }
    },
  }],
});
</script></body></html>`;

test('a still frame while words are read is a reading hold, not a dead one', { skip: (!chromium || !hasFfmpeg) && 'playwright or ffmpeg not installed', timeout: 180000 }, async (t) => {
  try { const b = await chromium.launch(); await b.close(); } catch (e) { t.skip(`chromium unavailable: ${e.message.split('\n')[0]}`); return; }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-read-'));
  try {
    fs.writeFileSync(path.join(dir, 'video.html'), html);
    fs.copyFileSync(path.join(ROOT, 'runtime', 'video-gaga.js'), path.join(dir, 'video-gaga.js'));
    const r = spawnSync(process.execPath, [gaga, 'render', dir, '--no-tts', '--no-music', '--subs', 'none', '--scale', '0.25', '--format', 'jpeg'], { encoding: 'utf8' });
    assert.equal(r.status, 0, r.stdout + r.stderr);
    assert.match(r.stdout, /picture: 2 still stretches ≥ 1\.5 s, 1 reading hold,/);
    assert.match(r.stdout, /read: still 1\.00s–2\.97s \(2\.0s, "holds"\) while "A line with five words" is read \(≈ 1\.7s\)/);
    assert.match(r.stdout, /look: nothing moves 4\.00s–6\.00s \(2\.0s, "holds"\): is the hold alive/);
    assert.match(r.stdout, /look: nothing moves 7\.00s–10\.97s \(4\.0s, "holds"\), longer than the ≈ 0\.6s "Hi" takes to read/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
