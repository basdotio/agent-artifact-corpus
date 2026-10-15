#!/usr/bin/env node
// node st.mjs <status|-> [--verify text|+append] [--item-note text|+append]
//   [--commit sha] [--bucket now|later] [--triage known|next] [--ws W] [--by agentId] [--residual text] [--resolve-residual n accept|fix] [--force] ID ...
// status: open|fixing|fixed|verified|failed|deferred, or - to leave it.
// `verified` needs: a commit + verify evidence, every sha in commit an ancestor of main, `--by <agentId>` (an agents.txt
//   verifier that is not a fixer of the item), no unresolved residual, and a prior `fixed` (else --force).
//   On a verified item `--commit` only ADDS shas to the ones the merge recorded; replacing them needs --force.
// --residual "text" records a residual the user has to judge (repeatable); --resolve-residual <n> accept|fix records the
//   user's answer (1-based; run by the orchestrator after the gate). An item with an unresolved residual cannot be verified.
// `show ID...` prints id | status | commit [| by X] [| residuals: n open / m] and changes nothing.
// `legacy` marks every verified item with no commit (verified before shas were recorded) `legacy: true` instead of backfilling a sha
//   nobody can vouch for; it backs the page up first to tracker.html.pre-legacy.<time> and runs under the tracker lock. Idempotent.
// --triage known|next sorts a later item: ship it as a known issue, or move it to the next release (done.mjs criterion 6).
// `pass <cycle> <units|all> <B/M/m> [--platforms a,b] [--sha s]` records one test pass: which units ran, on which platforms,
//   against which sha of main (default: main now), and how many new findings of each severity it produced. `all` expands to
//   the units in D.units at that moment. done.mjs reads the passes for criteria 3 (converged) and 4 (coverage).
// --verify is the verifier-evidence field, --item-note the item's own note. (--note no longer exists: it silently meant --verify.)
import { copyFileSync } from "node:fs";
import { config, updateItems, withTracker, git, badShas, die } from "./lib.mjs";
const [status, ...rest] = process.argv.slice(2);
if (!status) die("usage: st.mjs <status|-> [--verify t] [--item-note t] [--commit sha] [--bucket b] [--triage known|next] [--ws W] [--by agentId] [--residual t] [--resolve-residual n accept|fix] [--force] ID...");
if (status === "show") { // read-only: st.mjs show ID... → id | status | commit (the stale check reads the commit shas)
  const want = rest;
  withTracker(config(), (D) => {
    for (const id of want) {
      const i = D.items.find((x) => x.id === id);
      const res = i?.residuals?.length ? ` | residuals: ${i.residuals.filter((r) => r.state === "open").length} open / ${i.residuals.length}` : "";
      console.log(i ? `${i.id} | ${i.status} | ${i.commit || "-"}${i.by ? " | by " + i.by : ""}${res}` : `${id} | unknown`);
    }
    return false;
  });
  process.exit(0);
}
if (status === "legacy") {
  const cfg = config();
  withTracker(cfg, (D) => {
    const todo = D.items.filter((i) => i.status === "verified" && !i.commit && !i.legacy);
    if (!todo.length) return console.log("nothing to mark") ?? false;
    copyFileSync(cfg.tracker, `${cfg.tracker}.pre-legacy.${new Date().toISOString().replace(/\D/g, "").slice(0, 14)}`);
    for (const i of todo) i.legacy = true;
    console.log(`marked ${todo.length} legacy: ${todo.map((i) => i.id).join(" ")}`);
  });
  process.exit(0);
}
if (status === "pass") {
  const [cycle, units, found, ...more] = rest, o = {};
  for (let i = 0; i < more.length; i++) {
    if (!["--platforms", "--sha"].includes(more[i]) || more[i + 1] === undefined) die(`pass: unknown or empty flag ${more[i]}`);
    o[more[i].slice(2)] = more[++i];
  }
  const n = String(found ?? "").split("/").map(Number);
  if (!cycle || !units || n.length !== 3 || n.some((x) => !Number.isInteger(x) || x < 0))
    die("usage: st.mjs pass <cycle> <U1,U2|all> <B/M/m new findings, e.g. 0/1/3> [--platforms android,ios] [--sha s]");
  const cfg = config(), sha = o.sha ?? cfg.main;
  if (badShas(cfg, sha).length) die(`pass: ${sha} does not resolve or is not an ancestor of ${cfg.main}`);
  withTracker(cfg, (D) => {
    const known = Object.keys(D.units ?? {});
    const list = units === "all" ? known : units.split(",").filter(Boolean);
    if (!list.length) die("pass: no units (D.units is empty; record the unit plan in the tracker first)");
    const unknown = known.length ? list.filter((u) => !known.includes(u)) : [];
    if (unknown.length) die(`pass: units not in D.units: ${unknown.join(" ")} (nothing written)`);
    const p = { cycle: String(cycle), sha: git(cfg.repo, "rev-parse", "--short", sha).out, at: new Date().toISOString().slice(0, 16),
      units: list, platforms: o.platforms ? o.platforms.split(",") : [], found: { B: n[0], M: n[1], m: n[2] } };
    (D.passes ??= []).push(p);
    console.log(`pass ${D.passes.length}: cycle ${p.cycle} @ ${p.sha}, ${list.length} unit(s), found ${found}`);
  });
  process.exit(0);
}
const patch = { status }, ids = [];
const opts = { "--verify": "verify", "--item-note": "note", "--commit": "commit", "--bucket": "bucket", "--triage": "triage", "--ws": "ws", "--by": "by" };
for (let i = 0; i < rest.length; i++) {
  const a = rest[i];
  if (a === "--note") die("--note is gone (it used to write the verifier-evidence field): use --verify for evidence or --item-note for the item's own note");
  if (a === "--force") patch.force = true;
  else if (a === "--residual") { if (rest[i + 1] === undefined) die("--residual needs text"); (patch.residual ??= []).push(rest[++i]); }
  else if (a === "--resolve-residual") {
    const n = Number(rest[++i]), as = rest[++i];
    if (!Number.isInteger(n) || n < 1 || !["accept", "fix"].includes(as)) die("--resolve-residual needs <n> accept|fix");
    patch.resolveResidual = { n, as };
  }
  else if (opts[a]) { if (rest[i + 1] === undefined) die(`${a} needs a value`); patch[opts[a]] = rest[++i]; }
  else if (a.startsWith("--")) die(`unknown flag ${a}`);
  else ids.push(a);
}
if (!ids.length) die("no item ids given");
if ((patch.residual || patch.resolveResidual) && ids.length > 1) die("--residual / --resolve-residual take exactly one item id");
console.log(updateItems(config(), ids, patch));
