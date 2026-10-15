#!/usr/bin/env node
// stale.mjs <plan.md> [--rev N] [--allow-partial] — the fixer's stale-plan check, so nobody does the sha arithmetic by hand.
// Reads the plan's BASE line (`BASE main <sha> [+ assumes <ITEM> merged]`, or `BASE <branch> <sha>` for a revision stacked on an unmerged fix branch — then that branch stands in for main below; the LAST REVISION block is the plan in force and must have its own BASE,
// or --rev N for the block under `REVISION N`, 0 = the original; the line continues over indented or `+` lines). Then:
//   1. BASE sha must be an ancestor of main;
//   2. every assumed item (all ids after `assumes`, split on and / , / +; an `assumes` that yields none is an error) must be fixed|verified and carry commit shas in the tracker, each an ancestor of main, and not be `fixing` (a partial
//      merge) unless --allow-partial — otherwise exit 2: `PLAN GAP — stale: assumed <ITEM> not merged`;
//   3. prints the diff stat from the parent of the earliest assumed sha (or from BASE) to main, limited to the files the plan's
//      APPROACH names, and — per assumed item — what landed on top of its latest sha.
// Exit 0: assumptions hold (read the stat; if functions the plan touches moved, PLAN GAP — stale). Exit 2: an assumption fails or can't be read (no BASE line in the last block, unparsable assumes, a tracker id on the BASE line the parser didn't read as an assumption).
import { readFileSync } from "node:fs";
import { config, git, withTracker, shasOf, die } from "./lib.mjs";

const argv = process.argv.slice(2);
const revIdx = argv.indexOf("--rev"), rev = revIdx >= 0 ? Number(argv[revIdx + 1]) : null;
const allowPartial = argv.includes("--allow-partial");
const planPath = argv.find((a, i) => !a.startsWith("--") && i !== (revIdx < 0 ? -1 : revIdx + 1));
if (!planPath) die("usage: stale.mjs <plan.md> [--rev N] [--allow-partial]");
const cfg = config(), g = (...a) => git(cfg.repo, ...a);

// Split into blocks at `REVISION n` headings; block 0 is the original plan.
const text = readFileSync(planPath, "utf8");
const blocks = [{ n: 0, text: "" }];
for (const line of text.split("\n")) {
  const m = line.match(/^(?:#+\s*)?REVISION\s+(\d+)\b/i);
  if (m) blocks.push({ n: Number(m[1]), text: "" });
  blocks.at(-1).text += line + "\n";
}
// No --rev: the LAST block is the plan in force. A revision that dropped its BASE line fails closed instead of falling back to an older block's.
const block = rev === null ? blocks.at(-1) : blocks.find((b) => b.n === rev);
const fail = (msg) => { console.error(`PLAN GAP — stale: ${msg}`); process.exit(2); }; // fail closed: a plan whose assumptions can't be read is not "holding"
if (!block) fail(`${planPath} has no ${rev === null ? "BASE line" : "REVISION " + rev}; a plan states what it was written against (\`BASE main <sha> [+ assumes <ITEM> merged]\`)`);
// The BASE line plus its continuation lines (indented, or starting with `+`) — an assumption wrapped onto the next line is still on the BASE line.
const blockLines = block.text.split("\n"), baseAt = blockLines.findIndex((l) => /^BASE\b/.test(l));
let baseLine = null;
if (baseAt >= 0) {
  let end = baseAt + 1;
  while (end < blockLines.length && /^(?:\s+\S|\+)/.test(blockLines[end])) end++;
  baseLine = blockLines.slice(baseAt, end).map((l) => l.trim()).join(" ");
}
if (!baseLine) fail(`${planPath}: REVISION ${block.n} has no BASE line`);
const baseSha = baseLine.match(/\b([0-9a-f]{7,40})\b/)?.[1];
if (!baseSha) fail(`${planPath}: BASE line has no sha: ${baseLine}`);
// Everything after "assumes" up to "merged" or a "(" comment: item ids separated by "and", commas or "+", each optionally `@sha`.
const assumed = [];
if (/\bassumes\b/i.test(baseLine)) {
  for (const m of baseLine.matchAll(/\bassumes\s+([^()]*?)(?=\bmerged\b|\(|$)/gi))
    for (const tok of m[1].split(/\s*(?:,|\+|\band\b)\s*/i).map((t) => t.trim()).filter(Boolean)) {
      const id = tok.match(/^([A-Za-z]+\d[\w-]*)(?:@[0-9a-f]+)?$/)?.[1];
      if (!id) fail(`BASE line assumes "${tok}", which is not an item id: ${baseLine}`);
      if (!assumed.includes(id)) assumed.push(id);
    }
  if (!assumed.length) fail(`BASE line says "assumes" but no item id parsed: ${baseLine}`);
}

// Every tracker id on the BASE line must be an assumed item or carry wording we know means "not an assumption" (`independent of N168`, a `<sha> N172:` annotation of a sha).
// Anything else (`assuming N179`, `requires N179`, `+ N179 merged first`) is a dependency the parser didn't read: fail closed and name it.
const known = new Set(assumed.map((x) => x.toLowerCase()));
const baseRef = baseLine.match(/^BASE\s+([\w./-]+)\s+[0-9a-f]{7,40}\b/)?.[1];
const benign = (id, at) => id === baseRef /* the branch a revision stacks on (`BASE n179 <sha>`), however often the line names it */ || /\bindependent of\s+(?:N\d+\s*(?:,|\band\b|\+)\s*)*$/i.test(baseLine.slice(0, at)) || /\b[0-9a-f]{7,40}\s+$/.test(baseLine.slice(0, at));
const unread = [...baseLine.matchAll(/\bN\d+\b/gi)].filter((m) => !known.has(m[0].toLowerCase()) && !benign(m[0], m.index)).map((m) => m[0]);
if (unread.length) fail(`BASE line mentions ${[...new Set(unread)].join(", ")} in wording the parser doesn't read as an assumption (use \`assumes <ITEM> merged\`): ${baseLine}`);

// Files named in APPROACH (up to the next plan section).
const approach = block.text.match(/^(?:#+\s*)?APPROACH\b[\s\S]*?(?=^(?:#+\s*)?(?:CASES|TESTS|RISKS|ROOT CAUSE|INVARIANT|PRODUCT Q|REVISION)\b|^#{1,3}\s|(?![\s\S]))/m)?.[0] ?? "";
const files = [...new Set([...approach.matchAll(/[\w@.~-]+(?:\/[\w@.~-]+)+\.[A-Za-z]\w*/g)].map((m) => m[0]).filter((f) => !/^https?:/.test(f)))];

// `BASE n179 9e12c3a`: a revision written on top of a fix branch that hasn't merged yet. Checking its sha against main failed every
// such plan, so the fixer did the arithmetic by hand — exactly what this script exists to stop. Check against that branch instead.
// A reaped branch whose BASE sha is on main has merged: main stands in for it.
const refGone = (r) => !g("rev-parse", "--verify", "--quiet", r + "^{commit}").ok;
const ref = !baseRef || (refGone(baseRef) && g("merge-base", "--is-ancestor", baseSha, cfg.main).ok) ? cfg.main : baseRef;
if (refGone(ref)) fail(`BASE names ${ref}, which is not a branch or commit in ${cfg.repo}`);
if (!g("rev-parse", "--verify", "--quiet", baseSha + "^{commit}").ok) fail(`BASE ${baseSha} does not exist in ${cfg.repo}`);
if (!g("merge-base", "--is-ancestor", baseSha, ref).ok) fail(`BASE ${baseSha} is not an ancestor of ${ref}`);

const items = {};
if (assumed.length) withTracker(cfg, (D) => { for (const id of assumed) items[id] = D.items.find((i) => i.id.toLowerCase() === id.toLowerCase()); return false; });
const shas = [];
for (const id of assumed) {
  const it = items[id];
  if (!it) fail(`assumed ${id} is not in the tracker`);
  const own = shasOf(it.commit);
  if (it.status === "fixing" && allowPartial) { /* the plan assumes the partial merge */ }
  else if (!["fixed", "verified"].includes(it.status)) fail(`assumed ${id} is ${it.status}, not merged (needs fixed or verified${it.status === "fixing" ? "; pass --allow-partial if the plan assumes the partial merge" : ""})`);
  if (!own.length) fail(`assumed ${id} not merged: no commit recorded in the tracker (status ${it.status})`);
  const bad = own.filter((s) => !g("merge-base", "--is-ancestor", s, ref).ok);
  if (bad.length) fail(`assumed ${id} not merged: ${bad.join(", ")} is not an ancestor of ${ref}`);
  shas.push(...own);
}

// Earliest / latest by ancestry (commits made in the same second sort arbitrarily by date); date order only when they are unrelated.
const anc = (a, b) => a === b || g("merge-base", "--is-ancestor", a, b).ok;
const edge = (list, first) => list.find((s) => list.every((o) => (first ? anc(s, o) : anc(o, s)))) ?? g("rev-list", "--no-walk=sorted", ...(first ? ["--reverse"] : []), ...list).out.split("\n")[0];
const earliest = shas.length ? edge(shas, true) : null;
let from = baseSha;
if (earliest) {
  if (!g("rev-parse", "--verify", "--quiet", earliest + "^").ok) fail(`${earliest} has no parent to diff from`);
  from = earliest + "^";
}
const spec = files.length ? ["--", ...files] : [];
const short = (r) => g("rev-parse", "--short", r).out;
console.log(`plan ${planPath} (${block.n ? "REVISION " + block.n : "original"}): BASE ${short(baseSha)}${assumed.length ? ` + assumes ${assumed.join(", ")} merged` : ""}; ${ref} is ${short(ref)}${ref === cfg.main ? "" : ` (a branch, not ${cfg.main}: it must merge before this plan's commits)`}`);
console.log(`files named by APPROACH (${files.length}): ${files.join(" ") || "none found — diffing everything"}`);
console.log(`\ndiff ${short(from)}..${ref}${earliest ? ` (parent of the earliest assumed commit ${short(earliest)}; the assumed items' own commits are expected here)` : ` (BASE to ${ref})`}:`);
console.log(g("diff", "--stat", from, ref, ...spec).out || "  no change in those files");
for (const id of assumed) {
  const latest = edge(shasOf(items[id].commit), false);
  console.log(`\nlanded on top of ${id} (${short(latest)}..${ref}):\n` + (g("diff", "--stat", latest, ref, ...spec).out || "  nothing"));
}
console.log("\nassumptions hold. If a function the plan changes or relies on moved in a way its BASE didn't assume, stop with PLAN GAP — stale: <what> — <commit>.");
