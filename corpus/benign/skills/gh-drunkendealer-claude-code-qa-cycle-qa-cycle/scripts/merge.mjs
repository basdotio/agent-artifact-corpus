#!/usr/bin/env node
// merge.sh <branch> <IDs...> [--partial] [--force] — land a fixer branch on main, gate it, mark the items.
// Fails closed: main must be on `main` with a clean tracked tree; test, lint and build must all pass (each under
// `gateTimeoutMs`, default 20 min), otherwise main is put back to the pre-merge sha with `git reset --keep`, nothing is
// marked, exit non-zero. If --keep refuses (it never discards local changes) the script stops loudly (exit 2) and leaves
// everything as it is for a human — it never forces. Takes the repo lock, which mkbox.sh also takes.
// --partial: the branch is a PARTIAL fix — it merges and its shas are recorded, but the items are set to `fixing`, not `fixed`.
// Run it in the background (gates take minutes). Load rule: refuses while agents.txt shows a `running` verifier or tester
//   (the gate is a full-suite run); --force overrides.
// Crash recovery: before touching git it writes <tooling>/merge.journal.json (pre-merge sha, branch, ids, pid, start) and deletes
//   it when main is back in a known state (success, or a clean rollback). A journal left by a dead process makes the next run
//   stop and print the exact recovery command — it never runs it. `merge.sh --clear-journal` removes the journal after a human
//   has restored main. The gate runs in its own process group with a watchdog that kills the group if this process is SIGKILLed.
// Commits are ADDED to the item's `commit` (a partial then its revision accumulate), never replaced.
// A pass records the gated sha as D.gate {sha, at}; done.mjs reads it as "main is green" while main still sits on that sha.
import { spawnSync } from "node:child_process";
import { existsSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { join } from "node:path";
import { config, git, die, withTracker, updateItems, repoLock, run, commandExists, canMove, agentRows, isRole, Die } from "./lib.mjs";

const args = process.argv.slice(2);
const partial = args.includes("--partial"), force = args.includes("--force");
const cfg = config(), repo = cfg.repo, main = cfg.main;
const g = (...a) => git(repo, ...a);
const journalPath = join(cfg.tooling, "merge.journal.json");
if (args.includes("--clear-journal")) {
  repoLock(cfg);
  rmSync(journalPath, { force: true });
  console.log("journal cleared (main is whatever you left it at)");
  process.exit(0);
}
const [branch, ...ids] = args.filter((a) => !["--partial", "--force"].includes(a));
if (!branch || !ids.length) die("usage: merge.sh <branch> <IDs...> [--partial] [--force] | merge.sh --clear-journal");

// `gateSummary` (qa.config.json): regex of the output lines worth echoing after a gate passes (e.g. "^ℹ (pass|fail)" for node:test).
const summaryRe = cfg.gateSummary ? new RegExp(cfg.gateSummary) : null;
const gates = Object.entries({ test: cfg.commands?.test, lint: cfg.commands?.lint, build: cfg.commands?.build });
const absent = gates.filter(([, cmd]) => !cmd || !commandExists(cmd, repo)).map(([n, cmd]) => `${n}: ${cmd ? `"${cmd}"` : "not configured"}`);
if (absent.length) die(`refusing: gate command(s) missing, nothing touched:\n- ${absent.join("\n- ")}`);

// Load rule: the gate is a full test + lint + build, so it must not run next to a verifier's or tester's browser suite.
const busy = agentRows(cfg).filter((r) => r.state === "running" && (isRole(r, "verifier") || isRole(r, "tester")));
if (busy.length && !force) die(`refusing: ${busy.map((r) => `${r.id} (${r.role} ${r.items})`).join(", ")} still running in agents.txt — the merge gate would load the machine on top of it.\nWait for it, queue the merge (agents.mjs queue "merge ${branch} ${ids.join(" ")} after <agent>"), or pass --force.`);

repoLock(cfg);
if (existsSync(journalPath)) {
  const j = JSON.parse(readFileSync(journalPath, "utf8"));
  const live = (() => { try { process.kill(j.pid, 0); return true; } catch (e) { return e.code === "EPERM"; } })();
  if (live) die(`refusing: a merge of ${j.branch} (${j.ids.join(" ")}) is running as pid ${j.pid} (started ${j.start})`);
  die(`STOP: a previous merge of ${j.branch} (${j.ids.join(" ")}, pid ${j.pid}, started ${j.start}) died without finishing; main may be half-merged. Nothing was touched.\n` +
    `Pre-merge sha: ${j.pre}\n` +
    `1. Check:   git -C ${repo} status; git -C ${repo} rev-parse HEAD   (if HEAD is ${j.pre} and the tree is clean, main is fine: skip to 3)\n` +
    `2. Restore: git -C ${repo} cherry-pick --abort 2>/dev/null; git -C ${repo} reset --keep ${j.pre}   (--keep refuses rather than discard local changes; then resolve by hand, never force)\n` +
    `3. Then:    node ${join(cfg.tooling, "merge.mjs")} --clear-journal   and re-run the merge. No item was marked by the dead run unless the tracker already says fixed.`, 3);
}
const cur = g("rev-parse", "--abbrev-ref", "HEAD").out;
if (cur !== main) die(`refusing: ${repo} is on "${cur}", not ${main}`);
const dirty = g("status", "--porcelain", "--untracked-files=no").out;
if (dirty) die(`refusing: tracked changes in ${repo}:\n${dirty}`);
if (!g("rev-parse", "--verify", "--quiet", branch + "^{commit}").ok) die(`unknown branch ${branch}`);
const target = partial ? "fixing" : "fixed";
withTracker(cfg, (D) => {
  const by = new Map(D.items.map((i) => [i.id, i]));
  const missing = ids.filter((i) => !by.has(i));
  if (missing.length) die(`unknown item ids: ${missing.join(" ")} (nothing merged)`);
  const stuck = ids.filter((i) => !canMove(by.get(i).status, target));
  if (stuck.length) die(`${stuck.map((i) => `${i} is ${by.get(i).status}`).join(", ")}: cannot move to ${target} (nothing merged); fix the tracker status first`);
  return false;
});

const pre = g("rev-parse", "HEAD").out;
writeFileSync(journalPath, JSON.stringify({ pre, branch, ids, partial, pid: process.pid, start: new Date().toISOString() }, null, 1));
let killGate = null;
const fail = (why, detail) => {
  if (killGate) killGate();
  g("cherry-pick", "--abort"); // no-op unless one is in progress
  const r = g("reset", "--keep", pre);
  if (!r.ok) {
    console.error(`${why}\n${detail ?? ""}\n\nSTOP: \`git reset --keep ${pre.slice(0, 7)}\` refused, so ${repo} is NOT back at the pre-merge sha.\n${r.err}\n` +
      `Nothing was forced and no item was marked. Look at \`git -C ${repo} status\` and \`git log ${pre.slice(0, 7)}..HEAD\`, then restore main by hand.`);
    process.exit(2);
  }
  rmSync(journalPath, { force: true });
  console.error(`${why}\n${detail ?? ""}\nmain reset to ${pre.slice(0, 7)}; items not marked`);
  process.exit(1);
};
for (const sig of ["SIGINT", "SIGTERM"]) process.once(sig, () => fail(`INTERRUPTED (${sig})`));

function patchIds(range) {
  const log = g("log", "-p", "--reverse", "--format=commit %H", range).out;
  const r = spawnSync("git", ["patch-id", "--stable"], { cwd: repo, input: log, encoding: "utf8" });
  return r.stdout.split("\n").filter(Boolean).map((l) => l.split(" "));
}
function equivalentOnMain() {
  const base = g("merge-base", main, branch).out;
  const mine = new Set(patchIds(`${base}..${branch}`).map(([id]) => id));
  return patchIds(`${base}..${main}`).filter(([id]) => mine.has(id)).map(([, sha]) => g("rev-parse", "--short", sha).out);
}

try {
  if (g("merge-base", "--is-ancestor", branch, "HEAD").ok) console.log(`${branch} is already in ${main}`);
  else if (!g("merge", "--ff-only", branch).ok) {
    const base = g("merge-base", main, branch).out;
    const cp = g("cherry-pick", "--empty=drop", `${base}..${branch}`);
    if (!cp.ok) {
      const conflicts = g("status", "--short").out.split("\n").filter((l) => /^(UU|AA|DU|UD|AU|UA)/.test(l)).join("\n");
      fail("CONFLICT", conflicts || cp.err);
    }
  }
  const shas = g("rev-list", "--reverse", "--abbrev-commit", `${pre}..HEAD`).out.split("\n").filter(Boolean);
  console.log(g("log", "--oneline", "-5").out);

  for (const [name, cmd] of gates) {
    const r = await run(cmd, repo, cfg.gateTimeoutMs, { onChild: (k) => (killGate = k), watchdog: true });
    killGate = null;
    const tail = r.out.split("\n").slice(-40).join("\n");
    if (r.timedOut) fail(`${name.toUpperCase()}_TIMEOUT (${cmd}) after ${cfg.gateTimeoutMs / 1000}s`, tail);
    if (r.status !== 0) fail(`${name.toUpperCase()}_FAIL (${cmd})`, tail);
    console.log(`${name.toUpperCase()}_OK`, summaryRe ? r.out.split("\n").filter((l) => summaryRe.test(l)).join(" ") : "");
  }

  // Nothing new landed because the branch was cherry-picked earlier: record the commits on main that carry its patches
  // (the branch's own shas are not on main, and `verified` later demands an ancestor of main).
  const commit = (shas.length ? shas : equivalentOnMain()).join(", ") || g("rev-parse", "--short", branch).out;
  console.log(updateItems(cfg, ids, { status: target, commitAdd: commit }), "| merged", commit, partial ? "| PARTIAL: items kept at fixing" : "");
  withTracker(cfg, (D) => { D.gate = { sha: g("rev-parse", "--short", "HEAD").out, at: new Date().toISOString().slice(0, 16) }; });
  rmSync(journalPath, { force: true });
} catch (e) {
  fail(e instanceof Die ? "FAILED" : "UNEXPECTED ERROR", e instanceof Die ? e.message : e.stack);
}
