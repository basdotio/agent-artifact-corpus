// manifest.json helpers shared by repl.mjs (exploration) and replay.mjs (refresh). Plain fs, no Playwright, so
// tests/test_manifest.mjs can import it anywhere.
import { readFileSync, writeFileSync, existsSync, copyFileSync } from 'fs';

export const readManifest = (file) => (existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : []);
const save = (file, a) => writeFileSync(file, JSON.stringify(a, null, 2));

/** Upsert one entry by its `shot` name (what slide() does in the REPL). Returns the entry count. */
export function upsertSlide(file, o) {
  const a = readManifest(file);
  const i = a.findIndex((x) => x.shot === o.shot);
  if (i >= 0) a[i] = o; else a.push(o);
  save(file, a);
  return a.length;
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

/**
 * What a replay changes in the manifest. `produced` = the slide() calls of the replay, in call order.
 *  full:  the manifest follows the step files — entries in the order the steps produced them, their fields
 *         replaced by what slide() said; entries no step produced (hand-added) keep their order after them.
 *  !full: a --only run — upsert in place, never reorder (the run did not see every step).
 * Returns { merged, changes: [{shot, kind: 'new'|'changed', keys}], moved: [shot…], orphans: [shot…] }.
 */
export function planSync(old, produced, { full = true } = {}) {
  const last = new Map(produced.map((o) => [o.shot, o]));  // a step may call slide() twice: the last call wins
  const order = [...new Set(produced.map((o) => o.shot))];
  const oldBy = new Map(old.map((o) => [o.shot, o]));
  const changes = [];
  for (const shot of order) {
    const n = last.get(shot), o = oldBy.get(shot);
    if (!o) changes.push({ shot, kind: 'new', keys: Object.keys(n) });
    else {
      const keys = [...new Set([...Object.keys(o), ...Object.keys(n)])].filter((k) => !same(o[k], n[k]));
      if (keys.length) changes.push({ shot, kind: 'changed', keys });
    }
  }
  let merged;
  const orphans = old.filter((o) => !last.has(o.shot)).map((o) => o.shot);
  if (full) {
    merged = [...order.map((s) => last.get(s)), ...old.filter((o) => !last.has(o.shot))];
  } else {
    merged = old.map((o) => last.get(o.shot) ?? o);
    for (const s of order) if (!oldBy.has(s)) merged.push(last.get(s));
  }
  const moved = full ? merged.map((o) => o.shot).filter((s, i) => oldBy.has(s) && old.map((o) => o.shot).indexOf(s) !== i) : [];
  return { merged, changes, moved, orphans: full ? orphans : [] };
}

/** Apply planSync to the file. The previous file is kept as <file>.bak when anything changes. */
export function syncManifest(file, produced, opts = {}) {
  const old = readManifest(file);
  const plan = planSync(old, produced, opts);
  const changed = !same(old, plan.merged);
  if (changed) {
    if (existsSync(file)) copyFileSync(file, file + '.bak');
    save(file, plan.merged);
  }
  return { ...plan, wrote: changed };
}
