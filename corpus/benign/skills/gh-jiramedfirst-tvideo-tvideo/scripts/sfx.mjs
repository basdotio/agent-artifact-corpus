// sfx.mjs <editor-project-dir>
// Copy the four sound effects the editor uses (click-soft, whoosh-short, chime,
// sparkle) from the user's own Hyperframes media-use install into the project.
// TVideo does not redistribute these files; they ship with Hyperframes
// (`npx hyperframes skills update media-use` installs them).
import { copyFileSync, existsSync, mkdirSync, readdirSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const prj = process.argv[2];
if (!prj) {
  console.error('usage: node sfx.mjs <editor-project-dir>');
  process.exit(1);
}
const tried = [process.env.TV_MEDIA_USE_DIR, join(homedir(), '.claude/skills/media-use'), join(homedir(), '.agents/skills/media-use')]
  .filter(Boolean)
  .map((d) => join(d, 'audio/assets/sfx'));
const src = tried.find(existsSync);
if (!src) {
  console.error(`media-use SFX not found. Tried:\n  ${tried.join('\n  ')}\nRun: npx hyperframes skills update media-use, set TV_MEDIA_USE_DIR, or set "sfx": false in tvideo.config.json`);
  process.exit(1);
}
const dest = join(prj, 'assets/sfx');
mkdirSync(dest, { recursive: true });
for (const n of ['click-soft', 'whoosh-short', 'chime', 'sparkle']) copyFileSync(join(src, `${n}.mp3`), join(dest, `${n}.mp3`));
console.log(readdirSync(dest).join('\n'));
