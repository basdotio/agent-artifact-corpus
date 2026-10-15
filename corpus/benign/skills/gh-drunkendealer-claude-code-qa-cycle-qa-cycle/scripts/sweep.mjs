#!/usr/bin/env node
// sweep.mjs — read-only: lists TCP listeners in the loop's port ranges (qa.config.json `sweepPorts`, e.g. ["3700-3799","4700-4799"],
// default: every range in `ports` plus +1000 for Vite) with pid and cwd, and marks which belong to a `running` agents.txt row
// (its note/items mention the port or sandbox). Stops nothing: the orchestrator stops leftovers by PID.
import { spawnSync } from "node:child_process";
import { config, agentRows } from "./lib.mjs";
const cfg = config();
const ranges = (cfg.sweepPorts ?? Object.values(cfg.ports ?? {}).flatMap((v) => [...String(v).matchAll(/(\d+)-(\d+)/g)].flatMap((m) => [[+m[1], +m[2]], [+m[1] + 1000, +m[2] + 1000]])).map(([a, b]) => `${a}-${b}`))
  .map((r) => r.split("-").map(Number));
const running = agentRows(cfg).filter((r) => r.state === "running");
const out = spawnSync("lsof", ["-nP", "-iTCP", "-sTCP:LISTEN", "-Fpn"], { encoding: "utf8" }).stdout.split("\n");
let pid, seen = 0;
for (const l of out) {
  if (l.startsWith("p")) pid = l.slice(1);
  else if (l.startsWith("n")) {
    const port = Number(l.match(/:(\d+)$/)?.[1]);
    if (!ranges.some(([a, b]) => port >= a && port <= b)) continue;
    const cwd = spawnSync("lsof", ["-a", "-p", pid, "-d", "cwd", "-Fn"], { encoding: "utf8" }).stdout.split("\n").find((x) => x.startsWith("n"))?.slice(1) ?? "?";
    const owner = running.find((r) => `${r.note} ${r.items}`.includes(String(port)) || (cwd !== "?" && r.note && r.note.split(/\s+/).some((t) => t.length > 3 && cwd.includes(t))));
    console.log(`:${port} pid ${pid} cwd ${cwd} ${owner ? "KEEP (running " + owner.id + ")" : "leftover?"}`);
    seen++;
  }
}
if (!seen) console.log("no listeners in " + ranges.map((r) => r.join("-")).join(", "));
