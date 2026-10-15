#!/usr/bin/env node
/**
 * Review stills at the moments that matter, on the beat grid.
 *
 *   node scripts/stills.mjs videos/<film> b3.1 b5.1 12.4 [--out review/v3] [--debug]
 *   node scripts/stills.mjs videos/<film> --scenes            (the middle of every scene)
 *   node scripts/stills.mjs videos/<film> --handoffs          (8 frames, 0.1 s apart, around every scene change)
 *
 * Times: b<bar>.<beat>[+fraction] on the grid (b5.3, b5.3+0.5) or plain seconds.
 * --debug renders a copy of the project with window.PF_DEBUG = true: kit/debug.js
 * then prints time, bar.beat, every [data-target] box and the safe zone into the frame.
 * Uses `npx hyperframes snapshot`, which also writes contact-sheet.jpg.
 */
import { execFileSync } from "node:child_process";
import { cpSync, mkdtempSync, readFileSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { basename, join, resolve } from "node:path";
import { loadCues, seconds } from "./cues-lib.mjs";

const args = process.argv.slice(2);
const film = resolve(args[0] || ".");
const has = (n) => args.includes(n);
const val = (n, d) => (has(n) ? args[args.indexOf(n) + 1] : d);
const cues = loadCues(film);
const out = resolve(film, val("--out", "review/latest"));

const parse = (s) => {
  const m = String(s).match(/^b(\d+)(?:[.:](\d+))?(?:\+([\d.]+))?$/);
  if (m) return seconds(cues, [Number(m[1]), Number(m[2] || 1), Number(m[3] || 0)]);
  return Number(s);
};
let times = args.slice(1).filter((a, i, all) => !a.startsWith("--") && !(all[i - 1] || "").match(/^--(out)$/)).map(parse);
if (has("--scenes")) for (const s of cues.scenes || []) times.push((seconds(cues, s.from) + seconds(cues, s.to)) / 2);
if (has("--handoffs")) {
  for (const s of (cues.scenes || []).slice(1)) {
    const at = seconds(cues, s.from);
    for (let k = -4; k < 4; k++) times.push(at + k * 0.1);
  }
}
times = [...new Set(times.filter((t) => Number.isFinite(t) && t >= 0 && t < cues.duration).map((t) => Number(t.toFixed(3))))].sort((a, b) => a - b);
if (!times.length) {
  console.error("no valid times. Example: node scripts/stills.mjs videos/film b3.1 b5.1 12.4 --debug");
  process.exit(1);
}

let project = film;
let cleanup = () => {};
if (has("--debug")) {
  const tmp = mkdtempSync(join(tmpdir(), "pf-debug-"));
  project = join(tmp, basename(film));
  cpSync(film, project, { recursive: true, filter: (p) => !/[\\/](renders|snapshots|review|out|node_modules)([\\/]|$)/.test(p.slice(film.length)) });
  const index = join(project, "index.html");
  writeFileSync(index, readFileSync(index, "utf8").replace(/<head>/i, "<head><script>window.PF_DEBUG = true;</script>"));
  cleanup = () => rmSync(tmp, { recursive: true, force: true });
}
rmSync(out, { recursive: true, force: true });
try {
  execFileSync("npx", ["hyperframes", "snapshot", project, "--at", times.join(","), "--no-end", "-o", out, "--describe", "false"], { stdio: "inherit" });
} finally {
  cleanup();
}
console.log(`\n${times.length} stills in ${out}` + (existsSync(join(out, "contact-sheet.jpg")) ? " (+ contact-sheet.jpg)" : ""));
