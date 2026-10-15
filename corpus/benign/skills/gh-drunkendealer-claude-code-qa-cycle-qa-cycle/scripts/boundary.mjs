#!/usr/bin/env node
// boundary.mjs — run at every cycle boundary and after any wave that merged items the area rules name.
// Lists the item ids mentioned in the project's `.claude/rules/*.md` (qa.config `rules`: dirs/files, default <repo>/.claude/rules)
// and in the handoff memory file(s) (qa.config `handoffMemory`: array of paths), with each one's tracker status, and flags the
// ones that are merged (fixed), verified or unknown to the tracker: those lines are where a rule or handoff may now be stale
// and needs a refresh. Read-only; exit 0.
// Item ids are the tracker's own prefixes followed by digits (N168 when the tracker holds N-ids).
import { readFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { config, withTracker } from "./lib.mjs";

const cfg = config();
const files = [];
const add = (p) => {
  p = resolve(cfg.repo, p.replace(/^~(?=\/)/, process.env.HOME));
  if (!existsSync(p)) return console.error(`not found: ${p}`);
  if (statSync(p).isDirectory()) for (const f of readdirSync(p).filter((f) => f.endsWith(".md")).sort()) files.push(join(p, f));
  else files.push(p);
};
for (const p of cfg.rules ?? [join(".claude", "rules")]) add(p);
for (const p of cfg.handoffMemory ?? []) add(p);

let items;
withTracker(cfg, (D) => { items = new Map(D.items.map((i) => [i.id, i])); return false; });
const prefixes = [...new Set([...items.keys()].map((id) => id.match(/^[A-Za-z]+/)?.[0]).filter(Boolean))];
if (!prefixes.length) { console.log("tracker has no items"); process.exit(0); }
const re = new RegExp(`\\b(?:${prefixes.join("|")})\\d+\\b`, "g");

let flagged = 0;
for (const f of files) {
  const ids = [...new Set(readFileSync(f, "utf8").match(re) ?? [])];
  if (!ids.length) continue;
  console.log(f);
  for (const id of ids) {
    const it = items.get(id);
    const flag = !it ? "unknown" : ["fixed", "verified"].includes(it.status) ? it.status === "fixed" ? "merged" : "verified" : "";
    if (flag) flagged++;
    console.log(`  ${flag ? "FLAG" : "    "} ${id} | ${it ? it.status : "unknown"} | ${it?.commit || "-"}${flag ? ` | ${flag}: check the rule/handoff still says the right thing` : ""}`);
  }
}
console.log(`${files.length} file(s) scanned, ${flagged} flagged`);
