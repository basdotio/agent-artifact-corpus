// Refresh: replay every capture step in order, in one process, into <ws>/shots-new/.
//   MANUAL_CONFIG=<ws>/manual.json node replay.mjs [--only NN-name.js ...]
//
// Steps are <ws>/steps/NN-name.js, run in filename order with the same context the REPL gives them
// ({ P, session, shot, aria, cap, slide }), so a step written interactively replays unchanged.
// Replay assumes the app's test data was just reset: states only exist in order, and a step that expects
// "a record that was sent back" only finds one if every earlier step ran on the same fresh data.
//
// slide() records what each step says. After a FULL, successful replay the step files are the source of the
// wording and the order: manifest.json is upserted from them (steps/tips/task/kicker…) and ordered the way the
// steps produced the slides. Before overwriting, the changed slides are listed and the old file is kept as
// manifest.json.bak. A wording fix made only in manifest.json is therefore reverted — fix the step too, or pass
// --no-sync-manifest to refresh pictures only. A --only run upserts in place and never reorders.
// The first failing step stops the run and is named: that is where the UI changed (renamed button, moved field).
import { readdirSync, readFileSync, mkdirSync, rmSync, writeFileSync } from 'fs';
import path from 'path';
import { syncManifest } from './manifest.mjs';

// Unconditional: an inherited MANUAL_SHOTS=shots would overwrite the accepted baseline before diff_shots.py runs.
process.env.MANUAL_SHOTS = 'shots-new';
const cap = await import('./cap.mjs');
const STEPS = path.join(cap.WS, 'steps');
const args = process.argv.slice(2);
// --only is for debugging one screen on an app that is ALREADY in the right state: each run starts a new process
// with an empty P, so list the setup steps it needs too (e.g. --only 00-lib.js 10-list.js). There is no
// "resume from step N": after a reset, step N only finds its state if every earlier step ran — replay them all.
const only = args.includes('--only') ? args.slice(args.indexOf('--only') + 1).filter((a) => !a.startsWith('--')) : null;

// Only NN-*.js files are replayable steps; anything else in steps/ (or scratch/) is exploration and is skipped.
// Numeric order, not string order: "100-…" must run after "20-…".
let files = readdirSync(STEPS).filter((f) => /^\d+-.+\.js$/.test(f)).sort((a, b) => parseInt(a) - parseInt(b) || a.localeCompare(b));
if (only) files = files.filter((f) => only.includes(f));
if (!files.length) throw new Error(`no steps/NN-*.js to replay in ${STEPS}`);
if (!only) { rmSync(cap.OUT, { recursive: true, force: true }); mkdirSync(cap.OUT, { recursive: true }); }
// A --only run leaves older shots in shots-new; mark the folder so diff_shots.py will not report it as a full
// refresh. The next full replay recreates the folder and drops the marker.
else { mkdirSync(cap.OUT, { recursive: true }); writeFileSync(path.join(cap.OUT, '.partial'), files.join('\n')); }

const P = {};
const aria = async (page, sel = 'main') => page.locator(sel).first().ariaSnapshot();
const produced = [];
const slide = (o) => produced.push(o);
const syncOn = !args.includes('--no-sync-manifest');
const AsyncFunction = (async () => {}).constructor;
let failed = null;
for (const f of files) {
  const t0 = Date.now();
  try {
    await new AsyncFunction('P', 'session', 'shot', 'aria', 'cap', 'slide', readFileSync(path.join(STEPS, f), 'utf8'))(P, cap.session, cap.shot, aria, cap, slide);
    console.log(`ok   ${f} (${((Date.now() - t0) / 1000).toFixed(1)}s)`);
  } catch (e) {
    failed = f;
    console.error(`FAIL ${f}: ${(e.message || e).split('\n')[0]}`);
    console.error('     → the UI changed at this step (or an earlier step left a different state). Fix the step,');
    console.error('       then reset the app\'s test data and replay all steps again.');
    break;
  }
}
await cap.done();
if (syncOn && !failed && produced.length) {  // a failed run saw only some steps: leave the manifest alone
  const MANIFEST = path.join(cap.WS, 'manifest.json');  // same name repl.mjs writes
  const r = syncManifest(MANIFEST, produced, { full: !only });
  for (const c of r.changes) console.log(`manifest ${c.kind === 'new' ? 'new    ' : 'updated'} ${c.shot}: ${c.keys.join(', ')}`);
  if (r.moved.length) console.log(`manifest reordered to step order (${r.moved.length} slide(s) moved)`);
  if (r.orphans.length) console.warn(`manifest: no step produced ${r.orphans.join(', ')} — kept after the replayed slides`);
  console.log(r.wrote ? `manifest.json synced from the steps (previous version: ${path.basename(MANIFEST)}.bak)` : 'manifest.json already matches the steps');
}
console.log(failed ? `stopped at ${failed}` : `replayed ${files.length} steps → ${cap.OUT}`, '— next: diff_shots.py');
process.exit(failed ? 1 : 0);
