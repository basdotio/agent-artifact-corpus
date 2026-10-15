#!/usr/bin/env node
// node add.mjs ID sev "title" "where" "note" [later] [--now] [--ws W] [--unit N] [--force]
// sev: B|M|m. ws defaults to config.defaultWs, else the last item's workstream.
// Bucket follows severity: B and M go to `now`, m goes to `later` (status deferred) — a new minor waits for the user's gate.
// --now puts an m in `now` (only after the user said so); the 6th argument "later" parks any severity.
import { config, withTracker, summary, knownWs, SEV, die } from "./lib.mjs";
const pos = [], o = {};
const a = process.argv.slice(2);
for (let i = 0; i < a.length; i++) {
  if (a[i] === "--force") o.force = true;
  else if (a[i] === "--now") o.now = true;
  else if (a[i] === "--ws" || a[i] === "--unit") o[a[i].slice(2)] = a[++i];
  else if (a[i].startsWith("--")) die(`unknown flag ${a[i]}`);
  else pos.push(a[i]);
}
const [id, sev, title, where, note = "", later] = pos;
if (!id || !title || !where) die('usage: add.mjs ID sev "title" "where" "note" [later] [--ws W]');
if (!SEV.includes(sev)) die(`severity "${sev}" not in ${SEV.join("|")}`);
if (later !== undefined && later !== "later") die(`6th argument must be "later" or absent, got "${later}"`);
if (o.now && later) die("--now and \"later\" contradict each other");
const isLater = !!later || (sev === "m" && !o.now);
const cfg = config();
withTracker(cfg, (D) => {
  if (D.items.some((i) => i.id === id)) { console.log("exists", id); return false; }
  const ws = o.ws ?? cfg.defaultWs ?? D.items.at(-1)?.ws;
  if (!o.force && !knownWs(D).has(ws)) die(`workstream "${ws}" is new (known: ${[...knownWs(D)].join(" ")}); --force to create it`);
  D.items.push({ id, sev, bucket: isLater ? "later" : "now", ws, unit: Number(o.unit ?? 0), title, where, note, status: isLater ? "deferred" : "open", commit: "", verify: "" });
  console.log("added", id, isLater ? "(later)" : "(now)", "ws", ws, "|", summary(D));
});
