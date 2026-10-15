#!/usr/bin/env node
// done.mjs [--json] — the definition of done. Checks the seven exit criteria against the tracker, git and agents.txt, prints
// the QA CYCLE STATUS block (verdict, criteria table, counts, residuals, later triage) as markdown, and stores the result as
// D.done so the tracker page can render the same banner. Writes nothing else; never runs a gate (criterion 5 trusts the
// sha the last successful merge.sh gated). --json prints the result object instead of markdown.
//
//  1 Fix-now empty        every bucket-now item is verified
//  2 Residuals resolved   no residual is still open
//  3 Converged            the last recorded test pass found 0 new B and 0 new M
//  4 Coverage             every unit in D.units has a pass on each platform in qa.config `platforms` that no later commit
//                         touching the unit's files has invalidated (a unit without `files` goes stale on any commit)
//  5 Main green           D.gate.sha (written by merge.sh after test + lint + build) is main's current sha
//  6 Later triaged        every later item has triage known|next (st.mjs - --triage known|next ID)
//  7 Clean exit           no running agents.txt row, no worktree besides the main checkout, no sandbox left
//
// Verdict: NOT READY (1, 2, 5 or 6 fails: work or a user decision is pending) → ANOTHER CYCLE (3 or 4 fails; becomes
// CYCLE CAP when qa.config `cycle` ≥ `maxCycles`, default 3: stop and ask the user) → CLEANUP (only 7 fails) →
// READY WITH KNOWN ISSUES (all pass, some later items ship as known) → READY.
import { existsSync, readdirSync } from "node:fs";
import { config, withTracker, git, agentRows, openResiduals, SEV, STATUS } from "./lib.mjs";

const cfg = config(), asJson = process.argv.includes("--json");
const g = (...a) => git(cfg.repo, ...a);
const head = g("rev-parse", "--short", cfg.main).out;
const platforms = cfg.platforms ?? [];
const maxCycles = Number(cfg.maxCycles ?? 3);

withTracker(cfg, (D) => {
  const items = D.items, now = items.filter((i) => i.bucket === "now"), later = items.filter((i) => i.bucket === "later");
  const passes = D.passes ?? [], units = D.units ?? {};
  const C = [];
  const crit = (n, name, ok, evidence) => C.push({ n, name, ok, evidence });

  const notDone = now.filter((i) => i.status !== "verified");
  crit(1, "Fix-now empty", !notDone.length, notDone.length
    ? `${notDone.length} not verified: ${notDone.map((i) => `${i.id} ${i.status}`).join(", ")}`
    : `${now.length}/${now.length} verified`);

  const open = items.flatMap((i) => openResiduals(i).map((r) => `${i.id}#${r.n}`));
  const accepted = items.flatMap((i) => (i.residuals ?? []).filter((r) => r.state === "accepted")).length;
  crit(2, "Residuals resolved", !open.length, open.length ? `${open.length} open: ${open.join(", ")}` : `${accepted} accepted, none open`);

  const last = passes.at(-1);
  crit(3, "Last cycle converged", !!last && last.found.B === 0 && last.found.M === 0, last
    ? `pass ${passes.length} (cycle ${last.cycle} @ ${last.sha}) found ${last.found.B} B / ${last.found.M} M / ${last.found.m} m`
    : "no test pass recorded (st.mjs pass)");

  // A pass still counts for a unit while no commit after it touches the unit's files.
  const fresh = (p, files) => g("merge-base", "--is-ancestor", p.sha, cfg.main).ok
    && !g("rev-list", "--count", `${p.sha}..${cfg.main}`, ...(files?.length ? ["--", ...files] : [])).out.match(/^[1-9]/);
  const ids = Object.keys(units), stale = [];
  for (const u of ids) {
    const have = new Set(passes.filter((p) => p.units.includes(u) && fresh(p, units[u].files)).flatMap((p) => p.platforms.length ? p.platforms : ["*"]));
    const miss = platforms.length ? platforms.filter((pl) => !have.has(pl) && !have.has("*")) : have.size ? [] : ["any"];
    if (miss.length) stale.push(platforms.length ? `${u} (${miss.join("+")})` : u);
  }
  crit(4, "Coverage", ids.length > 0 && !stale.length, !ids.length
    ? "no unit map in the tracker (D.units)"
    : stale.length ? `${stale.length}/${ids.length} units untested since their files changed: ${stale.slice(0, 12).join(", ")}${stale.length > 12 ? " …" : ""}`
      : `${ids.length}/${ids.length} units covered${platforms.length ? ` on ${platforms.join(" + ")}` : ""}`);

  crit(5, "Main green", D.gate?.sha === head, D.gate
    ? D.gate.sha === head ? `${head}: test, lint, build OK (${D.gate.at})` : `gated ${D.gate.sha}, main is now ${head}: run the gates`
    : "no gate recorded (merge.sh records one)");

  const untriaged = later.filter((i) => !i.triage);
  const known = later.filter((i) => i.triage === "known");
  crit(6, "Later triaged", !untriaged.length, untriaged.length
    ? `${untriaged.length} untriaged: ${untriaged.map((i) => i.id).join(", ")}`
    : later.length ? `${known.length} known issue(s), ${later.length - known.length} next release` : "later bucket empty");

  const running = agentRows(cfg).filter((r) => r.state === "running").map((r) => `${r.role} ${r.id.slice(0, 8)}`);
  const trees = g("worktree", "list", "--porcelain").out.split("\n").filter((l) => l.startsWith("worktree ")).length - 1;
  const boxes = existsSync(cfg.sandboxRoot) ? readdirSync(cfg.sandboxRoot).filter((f) => !f.startsWith(".")).length : 0;
  const left = [running.length && `${running.length} running agent(s): ${running.join(", ")}`, trees > 0 && `${trees} worktree(s)`, boxes && `${boxes} sandbox(es)`].filter(Boolean);
  crit(7, "Clean exit", !left.length, left.length ? left.join("; ") : "no agents, worktrees or sandboxes left");

  const fail = new Set(C.filter((c) => !c.ok).map((c) => c.n));
  const cycle = cfg.cycle ?? last?.cycle ?? "?";
  const verdict = [1, 2, 5, 6].some((n) => fail.has(n)) ? "NOT READY"
    : fail.has(3) || fail.has(4) ? Number(cycle) >= maxCycles ? "CYCLE CAP" : "ANOTHER CYCLE"
      : fail.has(7) ? "CLEANUP"
        : known.length ? "READY WITH KNOWN ISSUES" : "READY";
  const why = verdict === "CYCLE CAP" ? `cycle ${cycle} of ${maxCycles}: stop and ask the user whether to run another`
    : fail.size ? `failing: ${[...fail].map((n) => C[n - 1].name.toLowerCase()).join(", ")}` : "all criteria met";

  const counts = Object.fromEntries(SEV.map((s) => [s, Object.fromEntries(STATUS.map((st) => [st, items.filter((i) => i.sev === s && i.status === st).length]))]));
  D.done = { verdict, why, cycle: String(cycle), sha: head, at: new Date().toISOString().slice(0, 16), criteria: C };

  if (asJson) return console.log(JSON.stringify({ ...D.done, counts }, null, 1));
  const bar = "━".repeat(56);
  const out = [
    "```", bar, `  QA CYCLE STATUS · ${cfg.project ?? "project"} · Cycle ${cycle} · ${D.done.at.slice(0, 10)}`, `  Verdict: ${verdict}  (${why})`, bar, "```", "",
    "| # | Criterion | | Evidence |", "|---|---|---|---|",
    ...C.map((c) => `| ${c.n} | ${c.name} | ${c.ok ? "✅" : "❌"} | ${c.evidence.replace(/\|/g, "\\|")} |`), "",
    "| Severity | " + STATUS.join(" | ") + " |", "|---|" + STATUS.map(() => "---:").join("|") + "|",
    ...SEV.map((s) => `| ${s} | ${STATUS.map((st) => counts[s][st] || "·").join(" | ")} |`),
  ];
  const openRes = items.flatMap((i) => openResiduals(i).map((r) => `- [ ] ${i.id}#${r.n} — ${r.text}`));
  if (openRes.length) out.push("", "**Open residuals (the user decides)**", ...openRes);
  if (later.length) out.push("", "**Later**", ...later.map((i) => `- ${i.id} ${i.sev} ${i.triage ?? "UNTRIAGED"} — ${i.title}`));
  console.log(out.join("\n"));
});
