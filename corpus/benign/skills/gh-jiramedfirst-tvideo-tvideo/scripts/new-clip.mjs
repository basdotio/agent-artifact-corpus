// new-clip.mjs <clip-dir> <recording-dir>
// Set up (or refresh) one editor project from one recording, in one command:
//   1. `hyperframes init` if <clip-dir> isn't a Hyperframes project yet;
//   2. copy the editor template over it (build.mjs regenerates index.html, so
//      overwriting init's starter files is intended). plan.json and
//      tvideo.config.json are created from the examples only when missing —
//      re-running on an edited project keeps them;
//   3. import the recording (import.mjs) and the stock SFX (sfx.mjs).
// Re-recording a clip = run this again with the new recording-dir, then build.
import { execFileSync } from 'node:child_process';
import { cpSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const [CLIP, REC] = process.argv.slice(2).map((p) => p && resolve(p));
if (!CLIP || !REC) {
  console.error('usage: node new-clip.mjs <clip-dir> <recording-dir containing video.webm>');
  process.exit(1);
}
const SKILL = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// shell on Windows only: npx is npx.cmd there, which execFile can't start directly.
const run = (cmd, args, cwd) => execFileSync(cmd, args, { cwd, stdio: 'inherit', shell: process.platform === 'win32' });

if (!existsSync(join(CLIP, 'hyperframes.json'))) {
  run('npx', ['hyperframes', 'init', CLIP, '--non-interactive', '--example=blank']);
}
cpSync(join(SKILL, 'templates/editor'), CLIP, { recursive: true });
for (const f of ['tvideo.config', 'plan']) {
  if (!existsSync(join(CLIP, `${f}.json`))) cpSync(join(CLIP, `${f}.example.json`), join(CLIP, `${f}.json`));
}
run('node', [join(SKILL, 'scripts/import.mjs'), REC, CLIP]);
try {
  run('node', [join(SKILL, 'scripts/sfx.mjs'), CLIP]);
} catch {
  // Optional: build.mjs leaves clicks silent when assets/sfx is empty.
  console.warn('! no click/whoosh sounds copied (see the error above) — the video will build without them');
}
console.log(`\n${CLIP} ready — edit plan.json (one step per tl.step) and tvideo.config.json, then: node build.mjs`);
