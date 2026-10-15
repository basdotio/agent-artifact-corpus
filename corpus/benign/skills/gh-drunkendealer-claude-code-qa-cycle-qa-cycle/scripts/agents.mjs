#!/usr/bin/env node
// agents.mjs add <agentId> <role> <model> <items> [--note t]   (role planner|fixer|verifier|tester|mapper|reviewer|other, model opus|sonnet|haiku|fable|?) upsert a row as running (resume = add again)
//            set <agentId> running|done|failed|stopped [--note t|+append]
//            queue "<text>"                                     rewrites the single `# QUEUE:` line ("" clears it)
//            ls [state]
//            restart [--note t]                                 marks every `running` row `stopped` (note default "session restart"): subagents never survive a session restart, so this is the resume step
//            stale [hours]                                      lists `running` rows older than N hours (default 6); no process check (ps can't see subagents): after a session restart use `restart`
// `add` of a fixer row also sets its items that are open|failed to `fixing` (tracker lock). `set` never touches item status. An existing row's role can't change (use a new id).
// Every write is a read-modify-write under agents.txt.lock.
// File: `id | role | model | items | state | started | ended | note`, `#` lines are comments.
import { readFileSync, writeFileSync, existsSync, renameSync } from "node:fs";
import { config, die, withAgents, withTracker, itemIds, isRole } from "./lib.mjs";

const STATES = ["running", "done", "failed", "stopped"];
const ROLES = ["planner", "fixer", "verifier", "tester", "mapper", "reviewer", "other"];
const MODELS = ["opus", "sonnet", "haiku", "fable", "?"];
const HEAD = "# id | role | model | items | state | started | ended | note";
const cfg = config();
// `|` separates the columns and a newline ends the row: a value holding either would corrupt every later parse, so it is refused, not rewritten.
const clean = (s, what = "field") => {
  const v = String(s ?? "");
  if (/[|\r\n]/.test(v)) die(`${what} contains "|" or a newline, which agents.txt can't hold (nothing written): ${JSON.stringify(v.slice(0, 60))}`);
  return v.trim();
};
const now = () => new Date().toLocaleString("sv").slice(0, 16);
let lines;
const load = () => {
  lines = existsSync(cfg.agents) ? readFileSync(cfg.agents, "utf8").split("\n").filter((l, i, a) => l || i < a.length - 1) : [];
  if (!lines.some((l) => l === HEAD)) lines.unshift(HEAD);
};
const rowIdx = (id) => lines.findIndex((l) => !l.startsWith("#") && l.split("|")[0].trim() === id);
const parse = (l) => l.split("|").map((s) => s.trim());
const save = () => { const t = `${cfg.agents}.tmp.${process.pid}`; writeFileSync(t, lines.join("\n") + "\n"); renameSync(t, cfg.agents); };
const mutate = (fn) => withAgents(cfg, () => { load(); return fn(); });

const [cmd, ...a] = process.argv.slice(2);
const flag = (name) => { const i = a.indexOf(name); if (i < 0) return undefined; const [, v] = a.splice(i, 2); return v; };
if (cmd === "add") {
  const note = flag("--note");
  const [id, role, model, items] = a;
  if (!id || !role || !model || !items) die("usage: add <agentId> <role> <model> <items> [--note t]");
  for (const [n, v] of Object.entries({ agentId: id, role, model, items })) clean(v, n);
  if (!ROLES.includes(role)) die(`role "${role}" not in ${ROLES.join("|")}`);
  if (!MODELS.includes(model)) die(`model "${model}" not in ${MODELS.join("|")}`);
  const resumed = mutate(() => {
    const i = rowIdx(id), old = i >= 0 ? parse(lines[i]) : [];
    if (i >= 0 && !isRole({ role: old[1] }, role) && !isRole({ role }, old[1])) die(`${id} is already a ${old[1]} row; a role can't change — register a new agent id as ${role}`);
    const row = [id, role, model, items, "running", i >= 0 && old[5] ? old[5] : now(), "", clean(note ?? old[7], "note")].join(" | ");
    i >= 0 ? (lines[i] = row) : lines.push(row);
    save();
    return i >= 0;
  });
  console.log(resumed ? "resumed" : "added", id);
  if (role === "fixer") withTracker(cfg, (D) => {
    const moved = [];
    for (const n of itemIds(items)) {
      const it = D.items.find((x) => x.id === n);
      if (!it) console.error(`warning: ${n} is not in the tracker`);
      else if (["open", "failed"].includes(it.status)) { it.status = "fixing"; moved.push(n); }
    }
    if (!moved.length) return false;
    console.log("fixing:", moved.join(" "));
  });
} else if (cmd === "set") {
  const note = flag("--note");
  const [id, state] = a;
  clean(id, "agentId");
  if (!STATES.includes(state)) die(`state must be ${STATES.join("|")}`);
  mutate(() => {
    const i = rowIdx(id);
    if (i < 0) die(`no agent ${id}`);
    const r = parse(lines[i]);
    r[4] = state; r[6] = state === "running" ? "" : now();
    if (note !== undefined) r[7] = note.startsWith("+") ? [r[7], clean(note.slice(1), "note")].filter(Boolean).join("; ") : clean(note, "note");
    lines[i] = r.join(" | "); save();
  });
  console.log(id, state);
} else if (cmd === "queue") {
  const text = a[0] ?? "";
  if (/[\r\n]/.test(text)) die("queue text can't hold a newline (nothing written)");
  mutate(() => {
    const i = lines.findIndex((l) => l.startsWith("# QUEUE:"));
    if (i >= 0) text ? (lines[i] = "# QUEUE: " + text) : lines.splice(i, 1);
    else if (text) lines.push("# QUEUE: " + text);
    save();
  });
} else if (cmd === "restart") {
  const note = clean(flag("--note") ?? "session restart", "note");
  const stopped = mutate(() => {
    const ids = [];
    lines = lines.map((l) => {
      if (l.startsWith("#")) return l;
      const r = parse(l);
      if (r[4] !== "running") return l;
      r[4] = "stopped"; r[6] = now(); r[7] = [r[7], note].filter(Boolean).join("; ");
      ids.push(r[0]);
      return r.join(" | ");
    });
    if (ids.length) save();
    return ids;
  });
  console.log(stopped.length ? `stopped ${stopped.length}: ${stopped.join(" ")}` : "no running rows");
} else if (cmd === "stale") {
  load();
  const hours = Number(a[0] ?? 6);
  for (const l of lines) {
    if (l.startsWith("#")) continue;
    const r = parse(l);
    if (r[4] !== "running") continue;
    const age = (Date.now() - Date.parse(String(r[5]).replace(" ", "T"))) / 3.6e6;
    if (Number.isFinite(age) && age < hours) continue;
    console.log(`${l}  # ${Number.isFinite(age) ? Math.round(age) + "h old" : "no start time"}`);
  }
  console.error("after a session restart use `agents.mjs restart`: subagents never survive it, and no process check can see them");
} else if (cmd === "ls") {
  load();
  for (const l of lines) if (!l.startsWith("#") && (!a[0] || parse(l)[4] === a[0])) console.log(l);
} else die("usage: agents.mjs add|set|queue|restart|ls|stale …");
