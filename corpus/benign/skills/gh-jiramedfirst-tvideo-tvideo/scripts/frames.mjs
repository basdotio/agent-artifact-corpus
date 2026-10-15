// frames.mjs <video> <outdir> <t1> [t2 ...]
// Grab full-resolution frames at the given seconds plus a 4-column contact sheet.
// Read the full frames to measure zoom/ring/mask coordinates — they are in the
// recording's own pixel space (e.g. 1280x800), which is what plan.json expects.
import { execFileSync } from 'node:child_process';
import { copyFileSync, mkdirSync, rmSync } from 'node:fs';
import { join } from 'node:path';

const [video, out, ...times] = process.argv.slice(2);
if (!video || !out || !times.length) {
  console.error('usage: node frames.mjs <video> <outdir> <t1> [t2 ...]');
  process.exit(1);
}
// The sheet is tiled from a numbered sequence of THIS run's frames only (a fresh
// .sheet/ dir): a glob over <outdir> would pick up an earlier run's frames, and
// ffmpeg's glob input doesn't exist on Windows builds.
const seq = join(out, '.sheet');
rmSync(seq, { recursive: true, force: true });
mkdirSync(seq, { recursive: true });
const ff = (...a) => execFileSync('ffmpeg', ['-v', 'error', '-y', ...a], { stdio: 'inherit' });
times.forEach((t, i) => {
  const png = join(out, `${String(i + 1).padStart(2, '0')}-t${t}.png`);
  ff('-ss', t, '-i', video, '-frames:v', '1', png);
  copyFileSync(png, join(seq, `${String(i + 1).padStart(2, '0')}.png`));
});
const rows = Math.ceil(times.length / 4); // the tile grid must hold every frame or ffmpeg drops the rest
ff('-framerate', '1', '-i', join(seq, '%02d.png'), '-vf', `scale=640:-1,tile=4x${rows}`, '-frames:v', '1', join(out, 'sheet.png'));
rmSync(seq, { recursive: true, force: true });
console.log(join(out, 'sheet.png'));
