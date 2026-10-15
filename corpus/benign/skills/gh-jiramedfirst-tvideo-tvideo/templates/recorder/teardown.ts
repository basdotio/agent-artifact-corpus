import { cpSync, existsSync, readdirSync } from 'node:fs';

/**
 * After a real take, copy each clip's folder out of test-results/ into
 * recordings/<timestamp>/ — Playwright wipes test-results/ at the start of the
 * next run, which would otherwise destroy the take.
 */
export default function globalTeardown() {
  if (process.env.TV_REHEARSE === '1' || !existsSync('test-results')) return;
  const clips = readdirSync('test-results').filter((d) => d.startsWith('clips-'));
  if (!clips.length) return;
  const stamp = new Date().toISOString().replace(/[-:]/g, '').replace('T', '-').slice(0, 15);
  const dest = `recordings/${stamp}`;
  for (const c of clips) cpSync(`test-results/${c}`, `${dest}/${c}`, { recursive: true });
  console.log(`Saved ${clips.length} clip folder(s) to ${dest}/`);
}
