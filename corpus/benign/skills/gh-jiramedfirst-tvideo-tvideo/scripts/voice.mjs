// voice.mjs — OPTIONAL narration. Run inside an editor project:
//
//   node <skill>/scripts/voice.mjs --voice <heygenVoiceId> --lang th
//
// Reads `narration` on plan.json's intro, steps[] and outro, generates one file
// per line with HeyGen TTS (via the Hyperframes media-use skill) and writes
// voices.json {id: {path, duration}} that build.mjs uses to pace each step.
// A line is regenerated only when its text or voice changed (hash next to the
// file) — TTS quota is small on free plans, so never re-bill unchanged lines.
import { execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { homedir } from 'node:os';
import { join } from 'node:path';

const arg = (name, def) => {
  const i = process.argv.indexOf(`--${name}`);
  return i > -1 ? process.argv[i + 1] : def;
};
const VOICE = arg('voice');
const LANG = arg('lang', 'en');
if (!VOICE) throw new Error('--voice <id> is required (list voices: see references/narration.md).');
const tried = [process.env.TV_MEDIA_USE_DIR, join(homedir(), '.claude/skills/media-use'), join(homedir(), '.agents/skills/media-use')]
  .filter(Boolean)
  .map((d) => join(d, 'audio/scripts/heygen-tts.mjs'));
const TTS = tried.find(existsSync);
if (!TTS) throw new Error(`heygen-tts.mjs not found. Tried:\n  ${tried.join('\n  ')}\nRun: npx hyperframes skills update media-use, or set TV_MEDIA_USE_DIR.`);

const plan = JSON.parse(readFileSync('plan.json', 'utf8'));
const lines = [
  plan.intro && { id: 'intro', text: plan.intro.narration },
  ...plan.steps.map((s) => ({ id: s.id, text: s.narration })),
  plan.outro && { id: 'outro', text: plan.outro.narration },
].filter((l) => l && l.text);
mkdirSync('assets/voice', { recursive: true });

const out = {};
for (const { id, text } of lines) {
  const path = `assets/voice/${id}.mp3`;
  const hashFile = `${path}.sha`;
  const hash = createHash('sha1').update(`${VOICE}|${LANG}|${text}`).digest('hex');
  if (!existsSync(path) || !existsSync(hashFile) || readFileSync(hashFile, 'utf8') !== hash) {
    const args = [TTS, text, '--voice', VOICE, '-o', path];
    if (LANG !== 'en') args.push('--lang', LANG);
    execFileSync('node', args, { stdio: 'inherit' });
    writeFileSync(hashFile, hash);
  }
  const duration = Number(execFileSync('ffprobe', ['-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', path], { encoding: 'utf8' }).trim());
  out[id] = { path, duration };
}
writeFileSync('voices.json', JSON.stringify(out, null, 2));
console.log(Object.entries(out).map(([k, v]) => `${k}:${v.duration.toFixed(1)}s`).join(' '));
