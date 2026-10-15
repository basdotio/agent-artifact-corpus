// Shared helpers for the qa-cycle tooling. Config: qa.config.json next to the scripts as invoked, in the cwd, or $QA_CONFIG (see configPath).
import { readFileSync, writeFileSync, renameSync, mkdirSync, rmSync, statSync, utimesSync, existsSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { spawn, spawnSync } from "node:child_process";

export const here = dirname(fileURLToPath(import.meta.url));

// Which qa.config.json: $QA_CONFIG, else the one next to the script as INVOKED (a tooling folder holding symlinks to these
// scripts: import.meta.url is the real path, process.argv[1] is not), else the cwd's, else the one beside the real script.
export function configPath() {
  if (process.env.QA_CONFIG) return resolve(process.env.QA_CONFIG);
  const invoked = process.argv[1] ? dirname(resolve(process.argv[1])) : here;
  return [join(invoked, "qa.config.json"), resolve("qa.config.json"), join(here, "qa.config.json")].find(existsSync) ?? join(here, "qa.config.json");
}

export function config() {
  const p = configPath();
  const c = JSON.parse(readFileSync(p, "utf8"));
  c.tooling ??= dirname(p);
  c.scratch = process.env.QA_SCRATCH ?? c.scratch;
  c.main ??= "main";
  c.tracker ??= join(c.tooling, "tracker.html");
  c.agents ??= join(c.tooling, "agents.txt");
  c.sandboxDir ??= "sbx";
  c.sandboxRoot = resolve(c.scratch ?? "", c.sandboxDir);
  c.gateTimeoutMs ??= 20 * 60_000;
  return c;
}

// die() throws so a caller that has already touched git (merge.mjs) can roll back; uncaught, it prints the message and exits.
export class Die extends Error { constructor(msg, code = 1) { super(msg); this.code = code; } }
export const die = (msg, code = 1) => { throw new Die(msg, code); };
process.on("uncaughtException", (e) => {
  console.error(e instanceof Die ? e.message : e);
  process.exit(e instanceof Die ? e.code : 1);
});

export function git(cwd, ...args) {
  const r = spawnSync("git", args, { cwd, encoding: "utf8" });
  return { ok: r.status === 0, out: (r.stdout ?? "").trim(), err: (r.stderr ?? "").trim() };
}

export const STATUS = ["open", "fixing", "fixed", "verified", "failed", "deferred"];
export const SEV = ["B", "M", "m"];
export const BUCKET = ["now", "later"];
// How a later item leaves the cycle: shipped as a known issue, or moved to the next release.
export const TRIAGE = ["known", "next"];

const sleep = (ms) => Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
const alive = (pid) => { try { process.kill(pid, 0); return true; } catch (e) { return e.code === "EPERM"; } };

// Directory lock. A lock is a directory holding `pid` and `token` files; it is created fully formed (written under a
// temp name, then renamed into place) so a reader never sees a half-made one, and rename onto an existing non-empty
// directory fails, which is the mutual exclusion. A lock is stale when its owner pid is dead or its mtime is older than
// staleMs (a crashed or SIGKILLed holder never ran its cleanup; a live holder renews the mtime with `heartbeatMs`).
// Taking over a stale lock is serialized by a short-lived `<lock>.takeover` mutex, and under it the lock is re-read: it is
// moved aside (atomic rename to a unique name, never rm) only if it is still the very directory seen as stale, so a
// racer that lost can never remove the winner's fresh lock. release() deletes the lock only while its token is ours.
// Released on exit, SIGINT and SIGTERM. Returns the release function.
const uniq = () => `${process.pid}.${Date.now()}.${randomBytes(4).toString("hex")}`;
const readTrim = (p) => { try { return readFileSync(p, "utf8").trim(); } catch { return ""; } };
const identity = (lock) => { // pid, token and inode: changes whenever the directory is replaced
  const st = statSync(lock, { throwIfNoEntry: false });
  return st ? `${readTrim(join(lock, "pid"))}:${readTrim(join(lock, "token"))}:${st.ino}` : null;
};
const staleness = (lock, staleMs) => {
  const st = statSync(lock, { throwIfNoEntry: false });
  if (!st) return null;
  const age = Date.now() - st.mtimeMs, raw = readTrim(join(lock, "pid")), pid = Number(raw);
  // A pid-less dir is only a legacy lock mid-creation: give it 5s before calling it dead.
  const dead = raw && Number.isFinite(pid) ? !alive(pid) : age > 5000;
  return { pid, age, stale: dead || age > staleMs, why: dead ? `owner pid ${raw || "?"} is gone` : `older than ${Math.round(staleMs / 60000)} min` };
};

function takeOver(lock, seen, label, staleMs) {
  const mutex = lock + ".takeover";
  for (let tries = 0; ; tries++) {
    try { mkdirSync(mutex); break; } catch (e) {
      if (e.code !== "EEXIST") throw e;
      const st = statSync(mutex, { throwIfNoEntry: false });
      if (st && Date.now() - st.mtimeMs > 10_000) try { renameSync(mutex, `${mutex}.dead.${uniq()}`); } catch {}
      if (tries > 400) return false;
      sleep(25);
    }
  }
  try {
    if (identity(lock) !== seen) return false; // replaced since we looked: not ours to remove
    const s = staleness(lock, staleMs);
    if (!s?.stale) return false;
    console.error(`${label}: taking over a stale lock (${s.why})`);
    const aside = `${lock}.stale.${uniq()}`;
    try { renameSync(lock, aside); } catch { return false; }
    rmSync(aside, { recursive: true, force: true });
    return true;
  } finally { rmSync(mutex, { recursive: true, force: true }); }
}

// Every lock this process holds, released by ONE exit/SIGINT/SIGTERM handler set (a listener per lock tripped MaxListeners, and
// the first lock's signal handler exited before the others were released). A signal exits unless the script has its own handler
// (merge.mjs rolls main back first); the exit handler then releases whatever is still held.
const held = new Set();
let armed = false;
function armSignals() {
  if (armed) return; armed = true;
  process.on("exit", () => { for (const r of [...held]) r(); });
  for (const sig of ["SIGINT", "SIGTERM"]) process.on(sig, () => { if (process.listenerCount(sig) <= 1) process.exit(128 + (sig === "SIGINT" ? 2 : 15)); });
}

export function lockDir(lock, { staleMs, waitMs, label = lock, heartbeatMs = 0 }) {
  const until = Date.now() + waitMs, token = uniq();
  for (;;) {
    const tmp = `${lock}.new.${token}`;
    mkdirSync(tmp);
    writeFileSync(join(tmp, "pid"), String(process.pid));
    writeFileSync(join(tmp, "token"), token);
    try { renameSync(tmp, lock); break; } catch (e) {
      rmSync(tmp, { recursive: true, force: true });
      if (!["ENOTEMPTY", "EEXIST", "EISDIR"].includes(e.code)) throw e;
    }
    const seen = identity(lock);
    if (!seen) continue; // released between our rename and now
    const s = staleness(lock, staleMs);
    if (s?.stale && takeOver(lock, seen, label, staleMs)) continue;
    if (Date.now() > until) throw new Die(`${label} is held by pid ${s?.pid} (${Math.round((s?.age ?? 0) / 1000)}s old); gave up after ${Math.round(waitMs / 1000)}s`);
    sleep(50 + Math.random() * 50);
  }
  if (readTrim(join(lock, "token")) !== token) throw new Die(`${label}: lost the lock right after taking it`);
  let released = false, beat;
  const mine = () => readTrim(join(lock, "token")) === token;
  if (heartbeatMs) { beat = setInterval(() => { if (mine()) { const t = new Date(); try { utimesSync(lock, t, t); } catch {} } }, heartbeatMs); beat.unref(); }
  const release = () => {
    if (released) return; released = true;
    held.delete(release);
    clearInterval(beat);
    if (!mine()) return; // taken over while we were stuck: it is not ours to delete
    const aside = `${lock}.rel.${uniq()}`;
    try { renameSync(lock, aside); rmSync(aside, { recursive: true, force: true }); } catch {}
  };
  held.add(release);
  armSignals();
  return release;
}

// One writer of main at a time: merge.sh and mkbox.sh both take it (a sandbox must never be cut from a main that a failed merge is about to reset).
// A merge holds it through up to three gate commands, so the stale limit is 3 × gateTimeoutMs plus slack, and the holder renews the mtime every 30s.
export const repoLock = (cfg) => lockDir(join(cfg.tooling, "repo.lock"), { staleMs: 3 * cfg.gateTimeoutMs + 10 * 60_000, waitMs: 30 * 60_000, label: "repo lock", heartbeatMs: 30_000 });

// Run a shell command in its own process group so a timeout (or a signal) kills the whole tree, not just the shell.
// A SIGKILLed parent can't kill the group itself, so a detached watchdog polls: when its parent is gone (reparented or dead)
// it SIGKILLs the group. Limit: a descendant that detached into a group of its own (a browser a test launched with setsid)
// is outside this group and is not reached.
const WATCHDOG = `const [parent, group] = process.argv.slice(1).map(Number), ppid = process.ppid;
const alive = (p) => { try { process.kill(p, 0); return true; } catch (e) { return e.code === "EPERM"; } };
setInterval(() => {
  if (process.ppid !== ppid || !alive(parent)) { try { process.kill(-group, "SIGKILL"); } catch {} process.exit(0); }
  try { process.kill(-group, 0); } catch { process.exit(0); }
}, 1000);`;
export function run(cmd, cwd, timeoutMs, { onChild, watchdog = false } = {}) {
  return new Promise((done) => {
    const c = spawn(cmd, { cwd, shell: true, detached: true, stdio: ["ignore", "pipe", "pipe"] });
    let out = "", timedOut = false;
    const kill = (sig = "SIGKILL") => { try { process.kill(-c.pid, sig); } catch {} };
    const dog = watchdog && c.pid ? spawn(process.execPath, ["-e", WATCHDOG, String(process.pid), String(c.pid)], { detached: true, stdio: "ignore" }) : null;
    dog?.unref();
    onChild?.(kill);
    const t = setTimeout(() => { timedOut = true; kill(); }, timeoutMs);
    for (const s of [c.stdout, c.stderr]) s.on("data", (d) => { out = (out + d).slice(-(1 << 22)); });
    c.on("close", (status) => { clearTimeout(t); dog?.kill(); done({ status: timedOut ? null : status, timedOut, out }); });
    c.on("error", (e) => { clearTimeout(t); dog?.kill(); done({ status: null, timedOut, out: String(e) }); });
  });
}

// True when `cmd`'s program (after any VAR=x prefixes) is a shell builtin/function/executable in cwd's PATH.
export function commandExists(cmd, cwd) {
  const prog = cmd.trim().split(/\s+/).find((t) => !/^\w+=/.test(t));
  if (!prog) return false;
  return spawnSync("sh", ["-c", 'command -v "$1" >/dev/null 2>&1', "sh", prog], { cwd }).status === 0;
}

// agents.txt is rewritten whole, so every read-modify-write of it runs under this lock (tmp names are per-process, never shared).
export function withAgents(cfg, fn) {
  const release = lockDir(cfg.agents + ".lock", { staleMs: 60_000, waitMs: 30_000, label: "agents lock" });
  try { return fn(); } finally { release(); }
}

// Read-modify-write under a mkdir lock so two scripts never clobber each other's edit of the page.
export function withTracker(cfg, fn) {
  const release = lockDir(cfg.tracker + ".lock", { staleMs: 60_000, waitMs: 30_000, label: "tracker lock" });
  try {
    let html = readFileSync(cfg.tracker, "utf8");
    const m = html.match(/const D=(\{.*\});\n/);
    if (!m) die("tracker.html has no `const D={...};` line");
    const D = JSON.parse(m[1]);
    const result = fn(D);
    if (result === false) return;
    html = html.replace(m[0], () => "const D=" + JSON.stringify(D).replace(/</g, "\\u003c") + ";\n");
    html = stripCounts(html, D);
    const tmp = cfg.tracker + ".tmp";
    writeFileSync(tmp, html);
    renameSync(tmp, cfg.tracker);
  } finally { release(); }
}

// The header strip is static HTML; recompute it from D so it never drifts.
function stripCounts(html, D) {
  const now = D.items.filter((i) => i.bucket === "now");
  const n = (f) => D.items.filter(f).length;
  const vals = {
    Blockers: n((i) => i.sev === "B"),
    Major: n((i) => i.sev === "M"),
    "Minor groups": n((i) => i.sev === "m"),
    "Fix now": now.length,
    Later: n((i) => i.bucket === "later"),
    Verified: `${now.filter((i) => i.status === "verified").length}/${now.length}`,
  };
  for (const [label, v] of Object.entries(vals))
    html = html.replace(new RegExp(`<b([^>]*)>[^<]*</b><span>${label}</span>`), (_, attrs) => `<b${attrs}>${v}</b><span>${label}</span>`);
  return html;
}

export const knownWs = (D) => new Set([...Object.keys(D.workstreams ?? {}), ...D.items.map((i) => i.ws)]);

export function summary(D) {
  const now = D.items.filter((i) => i.bucket === "now");
  const c = {};
  for (const i of now) c[i.status] = (c[i.status] ?? 0) + 1;
  return `${JSON.stringify(c)} later: ${D.items.filter((i) => i.bucket === "later").length}`;
}

// Allowed status moves. Anything else (open → verified, deferred → verified, …) needs --force.
export const NEXT = {
  open: ["fixing", "fixed", "deferred"],
  fixing: ["open", "fixed", "failed", "deferred"],
  fixed: ["open", "fixing", "verified", "failed", "deferred"],
  verified: ["open", "fixing", "failed", "deferred"],
  failed: ["open", "fixing", "fixed", "deferred"],
  deferred: ["open", "fixing", "fixed"],
};
export const canMove = (from, to) => from === to || NEXT[from]?.includes(to);

// Rows of agents.txt as {id, role, model, items, state, started, ended, note}. Legacy rows may say `fix`/`verify` for the role.
export function agentRows(cfg) {
  if (!existsSync(cfg.agents)) return [];
  return readFileSync(cfg.agents, "utf8").split("\n").filter((l) => l.trim() && !l.startsWith("#")).map((l) => {
    const [id, role, model, items, state, started, ended, ...note] = l.split("|").map((x) => x.trim());
    return { id, role, model, items: items ?? "", state, started, ended, note: note.join(" | ") };
  });
}
export const itemIds = (field) => String(field ?? "").split(/[,+\s/]+/).filter(Boolean);
const LEGACY_ROLE = { fixer: "fix", verifier: "verify", tester: "test", planner: "plan" };
export const isRole = (r, role) => r.role === role || r.role === LEGACY_ROLE[role];

// Every sha in a `commit` field must resolve and be an ancestor of main — a verified item points at code that is really there.
export const shasOf = (commit) => String(commit ?? "").split(/[\s,;+|]+/).filter(Boolean);
export function badShas(cfg, commit) {
  return shasOf(commit).filter((sha) => !git(cfg.repo, "rev-parse", "--verify", "--quiet", sha + "^{commit}").ok || !git(cfg.repo, "merge-base", "--is-ancestor", sha, cfg.main).ok);
}
const full = (cfg, sha) => git(cfg.repo, "rev-parse", "--verify", "--quiet", sha + "^{commit}").out || sha;
// Stored shas are always `rev-parse --short` of the resolved commit, so `HEAD~1` or a branch name is never kept literally (an unresolvable value under --force stays as given).
const shortShas = (cfg, v) => shasOf(v).map((s) => git(cfg.repo, "rev-parse", "--short", s + "^{commit}").out || s).join(", ");
// old ∪ add by full sha, keeping the spelling already stored.
function unionShas(cfg, old, add) {
  const have = new Set(shasOf(old).map((s) => full(cfg, s))), out = shasOf(old);
  for (const s of shasOf(add)) if (!have.has(full(cfg, s))) { have.add(full(cfg, s)); out.push(s); }
  return out.join(", ");
}

export const openResiduals = (it) => (it.residuals ?? []).map((r, i) => ({ ...r, n: i + 1 })).filter((r) => r.state === "open");

// patch: {status, verify ("+x" appends), note ("+x" appends), commit, commitAdd, bucket, triage, ws, by, residual[], resolveResidual {n, as}, force}
// A `commit` on an item that already has shas only ADDS to them (the merge recorded those); replacing needs --force. Every sha given must be on main, whatever the status.
// `verified` also needs `by` (an agents.txt verifier that is not a fixer of the item) and no unresolved residual.
export function updateItems(cfg, ids, patch) {
  let msg;
  withTracker(cfg, (D) => {
    const by = new Map(D.items.map((i) => [i.id, i]));
    const missing = ids.filter((id) => !by.has(id));
    if (missing.length) die(`unknown item ids: ${missing.join(" ")} (nothing written)`);
    const errs = [];
    if (patch.status && patch.status !== "-" && !STATUS.includes(patch.status)) errs.push(`status "${patch.status}" not in ${STATUS.join("|")}`);
    if (patch.bucket && !BUCKET.includes(patch.bucket)) errs.push(`bucket "${patch.bucket}" not in ${BUCKET.join("|")}`);
    if (patch.ws && !patch.force && !knownWs(D).has(patch.ws)) errs.push(`workstream "${patch.ws}" is new (known: ${[...knownWs(D)].join(" ")}); --force to create it`);
    const rows = agentRows(cfg);
    if (patch.by !== undefined && !patch.force) {
      const row = rows.find((r) => r.id === patch.by);
      if (!row) errs.push(`--by ${patch.by}: no such agent in agents.txt`);
      else if (!isRole(row, "verifier")) errs.push(`--by ${patch.by}: role is "${row.role}", not verifier`);
    }
    const join = (old, v) => (v.startsWith("+") ? (old ? old + " | " : "") + v.slice(1) : v);
    for (const id of ids) {
      const it = by.get(id);
      const to = patch.status && patch.status !== "-" ? patch.status : it.status;
      if (patch.status && patch.status !== "-") {
        if (!patch.force && !canMove(it.status, patch.status)) errs.push(`${id}: ${it.status} → ${patch.status} is not a normal move (allowed from ${it.status}: ${NEXT[it.status]?.join("|")}); --force to override`);
        it.status = patch.status;
      }
      if (patch.bucket) it.bucket = patch.bucket;
      if (patch.ws) it.ws = patch.ws;
      if (patch.triage) {
        if (!TRIAGE.includes(patch.triage)) errs.push(`triage "${patch.triage}" not in ${TRIAGE.join("|")}`);
        else if (it.bucket !== "later") errs.push(`${id}: --triage sorts the later bucket; ${id} is in ${it.bucket}`);
        else it.triage = patch.triage;
      }
      for (const [k, v] of [["--commit", patch.commit], ["commitAdd", patch.commitAdd]]) {
        const bad = patch.force || v === undefined ? [] : badShas(cfg, v);
        if (bad.length) errs.push(`${id}: ${k} ${bad.join(", ")} does not resolve or is not an ancestor of ${cfg.main}; merge it first, fix the sha, or --force`);
      }
      if (patch.commitAdd !== undefined) it.commit = unionShas(cfg, it.commit, shortShas(cfg, patch.commitAdd));
      if (patch.commit !== undefined) it.commit = it.commit && !patch.force ? unionShas(cfg, it.commit, shortShas(cfg, patch.commit)) : shortShas(cfg, patch.commit);
      if (patch.verify !== undefined) it.verify = join(it.verify, patch.verify);
      if (patch.note !== undefined) it.note = join(it.note, patch.note);
      for (const text of patch.residual ?? []) (it.residuals ??= []).push({ text, state: "open", at: new Date().toISOString().slice(0, 10) });
      if (patch.resolveResidual) {
        const { n, as } = patch.resolveResidual, r = it.residuals?.[n - 1];
        if (!r) errs.push(`${id}: no residual #${n} (it has ${it.residuals?.length ?? 0})`);
        else if (!["accept", "fix"].includes(as)) errs.push(`resolve as accept|fix, not "${as}"`);
        else { r.state = as === "accept" ? "accepted" : "fix"; r.resolvedAt = new Date().toISOString().slice(0, 10); }
      }
      if (patch.status === "verified" && !patch.force) {
        if (!it.commit || !it.verify)
          errs.push(`${id}: verified needs a commit and verify evidence (missing: ${[!it.commit && "commit", !it.verify && "verify"].filter(Boolean).join(", ")}); pass --commit/--verify or --force`);
        else {
          const bad = badShas(cfg, it.commit);
          if (bad.length) errs.push(`${id}: commit ${bad.join(", ")} does not resolve or is not an ancestor of ${cfg.main}; merge it first, fix --commit, or --force`);
        }
        const fixers = rows.filter((r) => isRole(r, "fixer") && itemIds(r.items).includes(id)).map((r) => r.id);
        if (patch.by === undefined) errs.push(`${id}: verified needs --by <verifier agentId> (an agents.txt verifier that is not a fixer of ${id}); or --force`);
        else if (!itemIds(rows.find((r) => r.id === patch.by)?.items).includes(id) && !patch.force) errs.push(`${id}: --by ${patch.by} does not list ${id} among its items in agents.txt; \`agents.mjs add\` it with ${id} first`);
        else if (fixers.includes(patch.by)) errs.push(`${id}: --by ${patch.by} is a fixer of ${id}; a fresh verifier must verify it`);
        else it.by = patch.by;
        const open = openResiduals(it);
        if (open.length) errs.push(`${id}: ${open.length} unresolved residual(s) (${open.map((r) => "#" + r.n).join(", ")}); the user decides accept|fix at the gate, then \`st.mjs - --resolve-residual <n> accept|fix ${id}\`. The item stays fixed until then`);
      } else if (patch.by !== undefined && !errs.length) it.by = patch.by;
    }
    if (errs.length) die(errs.join("\n") + "\n(nothing written)");
    msg = `${ids.length} updated; ${summary(D)}`;
  });
  return msg;
}
