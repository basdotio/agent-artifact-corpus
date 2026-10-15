#!/usr/bin/env node
// reap.sh <ID|branch|agentId|worktree-dir> — remove a finished item's worktree and delete its branches.
//   Refuses anything not fully merged into main, locked, dirty, or in use (a process cwd inside it).
// reap.sh --all-merged [--yes] [--skip name,name]  — the same for EVERY worktree/branch whose commits are all on main by
//   patch-id (`git cherry main <branch>` shows no `+`). Dry run unless --yes: prints SAFE / SKIP <reason> per entry.
//   Skips: locked or in-use worktrees, tracked changes, untracked non-ignored files, anything belonging to a `running`
//   row in agents.txt (its agent-<id> worktree, worktree-agent-<id> branch, and the lowercased branch of each of its items),
//   --skip names, and a bare branch sitting exactly on main (a fixer may be about to use it). Gitignored leftovers
//   (uploads/, web/dist, the `sandboxLinks` symlinks, node_modules by default) go with the worktree.
// Safety rails (both modes):
//   - worktree paths are compared to the main checkout by realpath, so a symlinked spelling of the checkout is never reaped;
//   - a branch/worktree with no commit of its own beyond main (a fresh agent worktree: nothing ever committed on it) is SKIP
//     unless --include-empty;
//   - anything touched in the last 30 minutes (branch tip commit, git admin files, modified or untracked files, the dir) is SKIP;
//     it is reaped only with --include-recent (and --yes in --all-merged mode).
import { existsSync, lstatSync, readdirSync, readFileSync, rmSync, realpathSync, statSync } from "node:fs";
import { join, basename } from "node:path";
import { spawnSync } from "node:child_process";
import { config, git, die } from "./lib.mjs";

const argv = process.argv.slice(2);
const all = argv.includes("--all-merged"), yes = argv.includes("--yes");
const includeEmpty = argv.includes("--include-empty"), includeRecent = argv.includes("--include-recent");
const RECENT_MS = 30 * 60_000;
const skipIdx = argv.indexOf("--skip");
const extraSkip = skipIdx >= 0 ? (argv[skipIdx + 1] ?? "").split(",").filter(Boolean) : [];
const arg = argv.find((a, i) => !a.startsWith("--") && i !== (skipIdx < 0 ? -1 : skipIdx + 1));
if (!all && !arg) die("usage: reap.sh <ID|branch|agentId|worktree-dir> | --all-merged [--yes] [--skip a,b]  (+ --include-empty, --include-recent)");
if (!all && (yes || skipIdx >= 0)) die("--yes and --skip only go with --all-merged");
const cfg = config(), repo = cfg.repo, main = cfg.main;
const g = (...a) => git(repo, ...a);
const rp = (p) => { try { return realpathSync(p); } catch { return p; } };
const linkNames = cfg.sandboxLinks ?? ["node_modules"];

const wts = g("worktree", "list", "--porcelain").out.split("\n\n").map((b) => {
  const w = { locked: false, prunable: false };
  for (const l of b.split("\n")) {
    if (l.startsWith("worktree ")) w.path = l.slice(9);
    else if (l.startsWith("branch ")) w.branch = l.slice(7).replace("refs/heads/", "");
    else if (l.startsWith("HEAD ")) w.head = l.slice(5);
    else if (l.startsWith("locked")) w.locked = true;
    else if (l.startsWith("prunable")) w.prunable = true;
  }
  return w;
}).filter((w) => w.path && rp(w.path) !== rp(repo));

let cwds; // every process cwd on the machine, read once
const processCwds = () => {
  if (cwds) return cwds;
  cwds = [];
  let pid;
  for (const l of spawnSync("lsof", ["-a", "-d", "cwd", "-Fpn"], { encoding: "utf8", maxBuffer: 1 << 26 }).stdout.split("\n")) {
    if (l.startsWith("p")) pid = l.slice(1);
    else if (l.startsWith("n")) cwds.push({ pid, cwd: l.slice(1) });
  }
  return cwds;
};

const mergedProblems = (b) => {
  if (g("merge-base", "--is-ancestor", b, main).ok) return [];
  const unmerged = g("cherry", main, b).out.split("\n").filter((l) => l.startsWith("+"));
  return unmerged.length ? [`${b}: ${unmerged.length} commit(s) not in ${main} (cherry-picks count as merged)`] : [];
};

// Fresh = nothing was ever committed on the branch and it holds nothing beyond main (an agent worktree just made from main).
const isFresh = (ref) => {
  if (g("rev-list", "--count", `${main}..${ref}`).out !== "0") return false;
  const log = g("reflog", "show", "--format=%gs", `refs/heads/${ref}`);
  return !log.ok || !log.out.split("\n").some((l) => /^commit/.test(l));
};
const freshReason = `no commits of its own beyond ${main} (a fresh agent worktree?): --include-empty to reap it`;
const newest = (...t) => Math.max(...t.filter(Number.isFinite));
const recentReason = (ms) => (Date.now() - ms < RECENT_MS ? `touched ${Math.round((Date.now() - ms) / 60000)} min ago (< 30): --include-recent${all ? " with --yes" : ""} to reap it` : null);
const mtime = (p) => statSync(p, { throwIfNoEntry: false })?.mtimeMs ?? NaN;
const tipTime = (ref) => Number(g("log", "-1", "--format=%ct", ref).out) * 1000;
function worktreeTouched(wt) {
  const gd = git(wt.path, "rev-parse", "--absolute-git-dir").out;
  const files = git(wt.path, "ls-files", "-m", "-o", "--exclude-standard").out.split("\n").filter(Boolean).slice(0, 2000).map((f) => mtime(join(wt.path, f)));
  return newest(mtime(wt.path), mtime(join(gd, "HEAD")), mtime(join(gd, "index")), mtime(join(gd, "logs/HEAD")), tipTime(wt.head ?? "HEAD"), ...files);
}

// Everything that makes removing this worktree unsafe; also fills wt.links (scratch symlinks pointing at it).
function worktreeProblems(wt) {
  const problems = [];
  if (wt.locked) problems.push("worktree is locked");
  if (!wt.prunable && existsSync(wt.path)) {
    const dirty = git(wt.path, "--no-optional-locks", "status", "--porcelain").out.split("\n").filter((l) => l && !linkNames.some((x) => l.endsWith(" " + x) || l.endsWith(" " + x + "/")));
    const tracked = dirty.filter((l) => !l.startsWith("??")), untracked = dirty.filter((l) => l.startsWith("??"));
    if (tracked.length) problems.push(`worktree has uncommitted changes:\n${tracked.join("\n")}`);
    if (untracked.length) problems.push(`worktree has untracked files:\n${untracked.join("\n")}`);
    const real = realpathSync(wt.path), links = [];
    if (cfg.scratch && existsSync(cfg.scratch)) for (const e of readdirSync(cfg.scratch)) {
      const p = join(cfg.scratch, e);
      try { if (lstatSync(p).isSymbolicLink() && realpathSync(p) === real) links.push(p); } catch {}
    }
    const users = processCwds().filter(({ cwd }) => [wt.path, real, ...links].some((r) => cwd === r || cwd.startsWith(r + "/")));
    if (users.length) problems.push(`in use: pid ${[...new Set(users.map((u) => u.pid))].join(", ")} ${users.length > 1 ? "have" : "has"} cwd inside (e.g. ${users[0].cwd})`);
    wt.links = links;
  }
  return problems;
}

function removeWorktree(wt) {
  if (!wt.prunable && existsSync(wt.path)) {
    for (const x of linkNames) { const nm = join(wt.path, x); try { if (lstatSync(nm).isSymbolicLink()) rmSync(nm); } catch {} }
    const r = g("worktree", "remove", wt.path);
    if (!r.ok) return `worktree remove failed (nothing deleted): ${r.err}`;
    for (const l of wt.links ?? []) rmSync(l);
  } else g("worktree", "prune");
  console.log("removed worktree", wt.path);
}

const deleteBranches = (list) => {
  for (const b of list) {
    const r = g("branch", "-D", b);
    console.log(r.ok ? `deleted branch ${b}` : `could not delete ${b}: ${r.err}`);
  }
};

const branchesOf = (wt) => [wt.branch, "worktree-" + basename(wt.path)].filter((b, i, a) => b && a.indexOf(b) === i && g("rev-parse", "--verify", "--quiet", `refs/heads/${b}`).ok);

if (all) {
  const running = existsSync(cfg.agents) ? readFileSync(cfg.agents, "utf8").split("\n").filter((l) => l && !l.startsWith("#")).map((l) => l.split("|").map((s) => s.trim())).filter((r) => r[4] === "running") : [];
  const busyNames = new Set(extraSkip);
  for (const [id, , , items, , , , note] of running) {
    busyNames.add("agent-" + id); busyNames.add("worktree-agent-" + id); busyNames.add(id);
    for (const it of (items ?? "").split(/[,+\s]+/).filter(Boolean)) busyNames.add(it.toLowerCase());
    for (const t of (note ?? "").split(/[\s,;:]+/).filter(Boolean)) busyNames.add(t);
  }
  const mainTip = g("rev-parse", main).out;
  const entries = [], onWorktree = new Set();
  for (const wt of wts) {
    const bs = branchesOf(wt);
    bs.forEach((b) => onWorktree.add(b));
    const reasons = [];
    const hit = [basename(wt.path), ...bs].find((n) => busyNames.has(n));
    if (hit) reasons.push(`belongs to a running agent or --skip (${hit})`);
    if (!bs.length) reasons.push(...mergedProblems(wt.head ?? "HEAD").map((p) => p.replace(/^[^:]*:/, "detached HEAD:")));
    for (const b of bs) reasons.push(...mergedProblems(b));
    reasons.push(...worktreeProblems(wt));
    if (!includeEmpty && bs.length && bs.every(isFresh)) reasons.push(freshReason);
    const rec = !(includeRecent && yes) && existsSync(wt.path) && !wt.prunable ? recentReason(worktreeTouched(wt)) : null;
    if (rec) reasons.push(rec);
    entries.push({ kind: "worktree", name: wt.branch ?? basename(wt.path), path: wt.path, wt, branches: bs, reasons });
  }
  const bare = g("for-each-ref", "--format=%(refname:short) %(objectname)", "refs/heads").out.split("\n").filter(Boolean).map((l) => l.split(" ")).filter(([b]) => b !== main && !onWorktree.has(b));
  for (const [b, tip] of bare) {
    const reasons = [];
    if (busyNames.has(b)) reasons.push(`belongs to a running agent or --skip (${b})`);
    if (tip === mainTip) reasons.push(`sits exactly on ${main} (no commits of its own; may be a fresh branch about to be used)`);
    reasons.push(...mergedProblems(b));
    if (tip !== mainTip && !includeEmpty && isFresh(b)) reasons.push(freshReason);
    const rec = includeRecent && yes ? null : recentReason(tipTime(b));
    if (rec) reasons.push(rec);
    entries.push({ kind: "branch", name: b, branches: [b], reasons });
  }
  const safe = entries.filter((e) => !e.reasons.length), skipped = entries.filter((e) => e.reasons.length);
  const indent = (r) => "      - " + r.split("\n").join("\n        ");
  for (const e of entries) console.log(`${e.reasons.length ? "SKIP" : "SAFE"} ${e.kind} ${e.name}${e.path ? " " + e.path : ""}${e.reasons.map((r) => "\n" + indent(r)).join("")}`);
  console.log(`\n${safe.length} safe, ${skipped.length} skipped of ${entries.length} (${wts.length} worktrees besides main, ${bare.length} bare branches)`);
  if (!yes) { console.log("dry run — pass --yes to reap the SAFE entries"); process.exit(0); }
  let done = 0, failed = 0;
  for (const e of safe) {
    if (e.wt) { const err = removeWorktree(e.wt); if (err) { console.log(`${e.name}: ${err}`); failed++; continue; } }
    deleteBranches(e.branches);
    done++;
  }
  console.log(`\nreaped ${done}, failed ${failed}, skipped ${skipped.length}`);
  process.exit(failed ? 1 : 0);
}

const names = new Set([arg, arg.toLowerCase(), "agent-" + arg, "worktree-agent-" + arg]);
const hits = wts.filter((w) => names.has(w.branch) || names.has(basename(w.path)));
if (hits.length > 1) die(`ambiguous: ${hits.map((w) => w.path).join(", ")}`);
const wt = hits[0];

const branches = new Set();
if (wt?.branch) { branches.add(wt.branch); branches.add("worktree-" + basename(wt.path)); }
else for (const n of names) branches.add(n);
const existing = [...branches].filter((b) => g("rev-parse", "--verify", "--quiet", `refs/heads/${b}`).ok);
if (!wt && !existing.length) die(`nothing matches "${arg}"`);
if (existing.includes(main)) die(`refusing: ${main}`);

const problems = existing.flatMap(mergedProblems);
if (wt) problems.push(...worktreeProblems(wt));
if (!includeEmpty && existing.length && existing.every(isFresh)) problems.push(freshReason);
const rec = includeRecent ? null : wt && existsSync(wt.path) && !wt.prunable ? recentReason(worktreeTouched(wt)) : existing.length ? recentReason(Math.max(...existing.map(tipTime))) : null;
if (rec) problems.push(rec);
if (problems.length) die(`refusing to reap "${arg}":\n- ` + problems.join("\n- "));

if (wt) { const err = removeWorktree(wt); if (err) die(err); }
deleteBranches(existing);
