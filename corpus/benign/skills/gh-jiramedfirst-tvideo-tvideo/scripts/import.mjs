// import.mjs <recording-dir> <editor-project-dir>
// Bring one Playwright recording into an editor project:
//   video.webm   -> assets/footage.mp4 (H.264, EVERY frame a keyframe, so the
//                   preview can seek between the many step windows without stutter)
//   timeline.json, clicks.json -> project root, re-timed to the footage (below)
// Stale hold stills are cleared (they belong to the previous take).
//
// Re-timing: the recorder's times count from the test body's t0, the video from
// page creation, and the gap is fixture setup time. The recorder paints a
// magenta flash before the first step and saves when (sync.json); this finds the
// flash in the footage and shifts every time by the difference. No flash found
// (older recorder, rehearsal take) → times are used as recorded, with a warning.
import { execFileSync, spawnSync } from 'node:child_process';
import { existsSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

const [REC, PRJ] = process.argv.slice(2);
if (!REC || !PRJ) {
  console.error('usage: node import.mjs <recording-dir containing video.webm> <editor-project-dir>');
  process.exit(1);
}
const need = (f, hint) => {
  if (!existsSync(join(REC, f))) {
    console.error(`no ${f} in ${REC}${hint}`);
    process.exit(1);
  }
};
need('video.webm', '');
need('timeline.json', ' — did the clip call tl.save()?');
const read = (f, fallback) => (existsSync(join(REC, f)) ? JSON.parse(readFileSync(join(REC, f), 'utf8')) : fallback);

mkdirSync(join(PRJ, 'assets'), { recursive: true });
const footage = join(PRJ, 'assets/footage.mp4');
execFileSync('ffmpeg', ['-v', 'error', '-y', '-i', join(REC, 'video.webm'), '-c:v', 'libx264', '-g', '1', '-crf', '18', '-pix_fmt', 'yuv420p', '-an', footage]);

const sync = read('sync.json', null);
let offsetMs = 0;
if (!sync) console.warn('! no sync.json (older recorder, or a rehearsal take) — using recorded times as-is');
else {
  const flashAt = findFlash(footage);
  if (flashAt === null) console.warn('! sync flash not found in the footage — using recorded times as-is');
  else offsetMs = Math.round(flashAt * 1000 - sync.syncMs);
}
const shift = (ms) => Math.max(0, ms + offsetMs);
const timeline = read('timeline.json').map((s) => ({ ...s, startMs: shift(s.startMs), endMs: shift(s.endMs) }));
// clicks.json: v1 recorders wrote bare ms numbers, v1.1 writes {ms, box, gone}.
const clicks = read('clicks.json', []).map((c) => (typeof c === 'number' ? { ms: shift(c) } : { ...c, ms: shift(c.ms) }));
writeFileSync(join(PRJ, 'timeline.json'), JSON.stringify(timeline, null, 2));
writeFileSync(join(PRJ, 'clicks.json'), JSON.stringify(clicks));
rmSync(join(PRJ, 'assets/holds'), { recursive: true, force: true });

const dur = execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', footage], { encoding: 'utf8' }).trim();
console.log(`imported ${dur} s of footage, ${timeline.length} steps${sync ? `, sync offset ${offsetMs} ms` : ''}`);

/**
 * Seconds into `video` of the first frame that is (almost) all magenta, or null.
 * Decodes only the first 60 s (the flash precedes the first step, after any
 * fixture/setup work) at 16x10: the flash fills the viewport, so a thumbnail is
 * enough and this stays around a second.
 */
function findFlash(video) {
  const W = 16, H = 10, FRAME = W * H * 3;
  const p = spawnSync('ffmpeg', ['-v', 'info', '-t', '60', '-i', video, '-vf', `scale=${W}:${H},showinfo`, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], { maxBuffer: 64 << 20 });
  const times = [...p.stderr.toString().matchAll(/pts_time:([\d.]+)/g)].map((m) => Number(m[1]));
  const raw = p.stdout;
  for (let i = 0; i < times.length && (i + 1) * FRAME <= raw.length; i++) {
    let hits = 0;
    for (let px = i * FRAME; px < (i + 1) * FRAME; px += 3) {
      if (raw[px] > 200 && raw[px + 1] < 70 && raw[px + 2] > 200) hits++;
    }
    if (hits >= W * H * 0.9) return times[i];
  }
  return null;
}
