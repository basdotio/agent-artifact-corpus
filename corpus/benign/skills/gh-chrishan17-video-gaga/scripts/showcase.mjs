#!/usr/bin/env node
// Build the gallery media in docs/media from rendered presets:
//   <slug>.mp4 (compressed 720p with sound) · <slug>.gif (an excerpt that
//   includes a transition) · <slug>.jpg (poster).
// Render first: `npm run examples`, then `npm run showcase`.

import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const OUT = path.join(ROOT, 'docs', 'media');

// gif: [start s, length s] (chosen to include at least one transition), poster: time s
const SHOWCASE = {
  'launch-keynote': { gif: [3.6, 7], poster: 8.2 },
  'studio-3d': { gif: [7.5, 7], poster: 12.5 },
  // grain overlays change every pixel each frame: fewer frames and colours keep the GIF small
  'clear-explainer': { gif: [15.5, 7], poster: 16.5, fps: 12, colors: 64 },
  blueprint: { gif: [11, 7], poster: 16.5, fps: 12, colors: 96 },
  'data-globe': { gif: [8, 7], poster: 14 },
  editorial: { gif: [3, 7], poster: 8, fps: 12, colors: 48, width: 440 },
  'paper-sketch': { gif: [2.5, 7], poster: 15.5, fps: 12, colors: 96 },
  'swiss-kinetic': { gif: [0, 10], poster: 13.5 },
  'neon-circuit': { gif: [2.5, 8], poster: 16.5 },
  'pop-collage': { gif: [1.5, 8], poster: 5.5 },
  // flat palette colours: few colours, no dither noise; nearest-neighbour keeps the cells square
  'pixel-retro': { gif: [31, 8], poster: 54.3, fps: 15, colors: 16 },
  'ink-wash': { gif: [49.5, 6.5], poster: 75.5, fps: 12, colors: 64 },
  'cinematic-film': { gif: [29.2, 7], poster: 75.6, fps: 12, colors: 48, width: 440 },
};

const ff = (args) => {
  const r = spawnSync('ffmpeg', ['-y', '-loglevel', 'error', ...args], { stdio: 'inherit' });
  if (r.status !== 0) throw new Error(`ffmpeg failed: ${args.join(' ')}`);
};
const only = process.argv.slice(2);
fs.mkdirSync(OUT, { recursive: true });
for (const [slug, o] of Object.entries(SHOWCASE)) {
  if (only.length && !only.includes(slug)) continue;
  const src = path.join(ROOT, 'presets', slug, 'out', `${slug}.mp4`);
  if (!fs.existsSync(src)) { console.log(`- ${slug}: not rendered (run npm run examples)`); continue; }
  const probe = JSON.parse(spawnSync('ffprobe', ['-v', 'error', '-print_format', 'json', '-show_streams', src], { encoding: 'utf8' }).stdout);
  const v = probe.streams.find((s) => s.codec_type === 'video');
  const hasAudio = probe.streams.some((s) => s.codec_type === 'audio');
  const landscape = v.width > v.height;
  const scale = landscape ? 'scale=1280:-2' : 'scale=720:-2';
  const gifW = o.width ?? (landscape ? 480 : v.width === v.height ? 320 : 270);
  ff(['-i', src, '-vf', `${scale}:flags=lanczos`, '-c:v', 'libx264', '-preset', 'slow', '-crf', '27', '-pix_fmt', 'yuv420p', ...(hasAudio ? ['-c:a', 'aac', '-b:a', '96k'] : ['-an']), '-movflags', '+faststart', path.join(OUT, `${slug}.mp4`)]);
  // 15 fps by default so quick transitions survive in the GIF
  ff(['-ss', String(o.gif[0]), '-t', String(o.gif[1]), '-i', src, '-vf', `fps=${o.fps ?? 15},scale=${gifW}:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=${o.colors ?? 128}:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle`, '-loop', '0', path.join(OUT, `${slug}.gif`)]);
  ff(['-ss', String(o.poster), '-i', src, '-frames:v', '1', '-vf', `${landscape ? 'scale=960:-2' : 'scale=540:-2'}:flags=lanczos`, '-q:v', '4', path.join(OUT, `${slug}.jpg`)]);
  const kb = (f) => (fs.statSync(path.join(OUT, f)).size / 1024).toFixed(0);
  console.log(`✔ ${slug}: mp4 ${kb(`${slug}.mp4`)} KB · gif ${kb(`${slug}.gif`)} KB · jpg ${kb(`${slug}.jpg`)} KB`);
}
