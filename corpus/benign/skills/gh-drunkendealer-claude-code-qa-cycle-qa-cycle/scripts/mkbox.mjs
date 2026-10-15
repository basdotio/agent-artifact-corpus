#!/usr/bin/env node
// mkbox.sh <ID> <port> [--force] — verifier sandbox built from the commit `main` points at (git archive of the resolved sha), not from the working tree.
// <scratch>/<sandboxDir>/<ID>: tracked files only, node_modules symlinked, test-only .env, built in place, SANDBOX_SHA written last.
// Takes the repo lock first, then checks the sandbox is free and resolves and archives main (so it never cuts a sandbox from a main a failing merge is about to reset).
// Refuses to rebuild a sandbox ANY process has its cwd in (a server, a browser, a shell, a test run) unless --force.
// qa.config.json: `sandboxLinks` (paths symlinked from the repo checkout, default ["node_modules"]), `sandboxEnvFile` (default ".env"), `sandboxEnv` lines.
import { cpSync, existsSync, mkdirSync, realpathSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { spawnSync } from "node:child_process";
import { config, git, die, repoLock } from "./lib.mjs";

const force = process.argv.includes("--force");
const [id, port] = process.argv.slice(2).filter((a) => a !== "--force");
if (!id || !/^\d+$/.test(port ?? "")) die("usage: mkbox.sh <ID> <port> [--force]");
if (!/^[\w.-]+$/.test(id) || id.startsWith(".")) die(`bad id ${id}`);
const cfg = config();
if (!cfg.scratch) die("no scratch root: set `scratch` in qa.config.json or $QA_SCRATCH");
const root = cfg.sandboxRoot;
const dir = join(root, id);
if (!dir.startsWith(root + sep)) die("sandbox path escapes scratch root");

// Every process on the machine whose cwd is inside the sandbox (lsof -d cwd), not only listeners: rebuilding under a shell or
// a browser breaks the run in progress just the same.
function inUse() {
  if (!existsSync(dir)) return [];
  const real = realpathSync(dir), hits = [];
  let pid;
  for (const l of spawnSync("lsof", ["-a", "-d", "cwd", "-Fpn"], { encoding: "utf8", maxBuffer: 1 << 26 }).stdout.split("\n")) {
    if (l.startsWith("p")) pid = l.slice(1);
    else if (l.startsWith("n") && pid !== String(process.pid) && [dir, real].some((r) => l.slice(1) === r || l.slice(1).startsWith(r + sep))) hits.push(`pid ${pid} (cwd ${l.slice(1)})`);
  }
  return hits;
}

const release = repoLock(cfg);
const busy = inUse();
if (busy.length && !force) die(`refusing to rebuild ${dir}: in use by ${busy.join(", ")}.\nStop them by PID (or let their verifier finish), or pass --force.`);
const sha = git(cfg.repo, "rev-parse", cfg.main + "^{commit}");
if (!sha.ok) die(`cannot resolve ${cfg.main}: ${sha.err}`);

rmSync(dir, { recursive: true, force: true });
mkdirSync(dir, { recursive: true });
const ex = spawnSync(`git -C "${cfg.repo}" archive ${sha.out} | tar -x -C "${dir}"`, { shell: true, encoding: "utf8" });
if (ex.status !== 0) die("git archive failed: " + ex.stderr);
release();
// Gitignored caches the app needs at run time (config.sandboxCopy), so the sandbox doesn't refetch them.
for (const rel of cfg.sandboxCopy ?? []) {
  const from = join(cfg.repo, rel);
  if (!existsSync(from)) continue;
  mkdirSync(dirname(join(dir, rel)), { recursive: true });
  cpSync(from, join(dir, rel), { recursive: true });
}
for (const rel of cfg.sandboxLinks ?? ["node_modules"]) { mkdirSync(dirname(join(dir, rel)), { recursive: true }); symlinkSync(join(cfg.repo, rel), join(dir, rel)); }
const env = (cfg.sandboxEnv ?? ["PORT={port}", "PUBLIC_URL=http://localhost:{port}"]).map((l) => l.replaceAll("{port}", port)).join("\n") + "\n";
writeFileSync(join(dir, cfg.sandboxEnvFile ?? ".env"), env);
const b = spawnSync(cfg.commands.build, { cwd: dir, shell: true, encoding: "utf8", maxBuffer: 1 << 28 });
if (b.status !== 0) die(`build failed in ${dir} (no SANDBOX_SHA written):\n` + ((b.stdout ?? "") + (b.stderr ?? "")).split("\n").slice(-30).join("\n"));
writeFileSync(join(dir, "SANDBOX_SHA"), sha.out + "\n");
console.log(`${dir} @ ${sha.out.slice(0, 7)}`);
