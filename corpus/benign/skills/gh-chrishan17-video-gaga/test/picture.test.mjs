// gaga check scans the encoded picture: still stretches, one-frame glitches,
// flashing and blank frames. Each check is made to fire on a generated clip.
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const gaga = new URL('../scripts/gaga.mjs', import.meta.url).pathname;
const hasFfmpeg = spawnSync('ffmpeg', ['-version'], { stdio: 'ignore' }).status === 0;

function clip(name, input, vf) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'gaga-picture-'));
  const file = path.join(dir, `${name}.mp4`);
  const r = spawnSync('ffmpeg', ['-v', 'error', '-f', 'lavfi', '-i', input, ...(vf ? ['-vf', vf] : []), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', file]);
  assert.equal(r.status, 0, String(r.stderr));
  return file;
}
const check = (file) => spawnSync(process.execPath, [gaga, 'check', file], { encoding: 'utf8' });

test('a frozen stretch and a one-frame glitch are pointed at, not failed', { skip: !hasFfmpeg && 'ffmpeg not installed' }, () => {
  // 3 s of moving test pattern; frame 15 is white; frame 45 is held for 2 s
  const file = clip('glitch', 'testsrc2=s=320x180:r=30:d=3', "drawbox=x=0:y=0:w=iw:h=ih:color=white:t=fill:enable='eq(n,15)',loop=loop=60:size=1:start=45");
  const r = check(file);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(r.stdout, /1 still stretch ≥ 1\.5 s, 1 one-frame glitch, no flashing/);
  assert.match(r.stdout, /look: nothing moves 1\.[45]\ds–3\.[45]\ds \(2\.0s\)/);
  assert.match(r.stdout, /look: frame at 0\.50s differs from both neighbours/);
});

test('flashing more than three times a second fails the check', { skip: !hasFfmpeg && 'ffmpeg not installed' }, () => {
  const file = clip('flash', 'color=c=black:s=320x180:r=30:d=2', "geq=lum='255*mod(floor(T*8),2)':cb=128:cr=128");
  const r = check(file);
  assert.equal(r.status, 2, r.stdout + r.stderr);
  assert.match(r.stdout, /⚠ flashing: \d+ flashes within one second/);
});

test('a blank opening is pointed at; a closing hold is not a still stretch', { skip: !hasFfmpeg && 'ffmpeg not installed' }, () => {
  // 0.5 s of flat grey, then a moving pattern that freezes for its last 2 s
  const file = clip('blank', 'testsrc2=s=320x180:r=30:d=2', "drawbox=x=0:y=0:w=iw:h=ih:color=gray:t=fill:enable='lt(t,0.5)',tpad=stop_mode=clone:stop_duration=2");
  const r = check(file);
  assert.equal(r.status, 0, r.stdout + r.stderr);
  assert.match(r.stdout, /look: blank 0\.00s–0\.50s/);
  assert.doesNotMatch(r.stdout, /nothing moves/);
});
