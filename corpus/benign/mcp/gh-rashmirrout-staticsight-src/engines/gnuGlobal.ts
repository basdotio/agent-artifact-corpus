// GNU Global adapter: database build/update and `global -x` queries.
import type { Config } from "../config.js";
import { StaticSightError } from "../core/errors.js";
import type { CmdResult } from "../platform/index.js";
import { isAvailable, runEngine, toPosix } from "./base.js";
import { cmpStr } from "./ctags.js";

export const GLOBAL_LINE = /^(\S+)\s+(\d+)\s+(\S+)\s?(.*)$/;
export const INDEX_TIMEOUT_S = 1800;

export interface Hit {
  path: string;
  line: number;
  text: string;
}

export function available(): boolean {
  return isAvailable("gtags") && isAvailable("global");
}

export function parseXOutput(stdout: string): Hit[] {
  const seen = new Map<string, Hit>();
  for (const raw of stdout.split("\n")) {
    const m = GLOBAL_LINE.exec(raw.replace(/\r$/, ""));
    if (!m) continue;
    const hit = { path: toPosix(m[3]), line: parseInt(m[2], 10), text: m[4] };
    seen.set(`${hit.path}\u0000${hit.line}\u0000${hit.text}`, hit);
  }
  return [...seen.values()].sort((a, b) => cmpStr(a.path, b.path) || a.line - b.line);
}

/** `global <flag> -- symbol`; null when the query cannot be answered (caller falls back). */
export async function query(cfg: Config, env: Record<string, string>, flag: string, symbol: string): Promise<Hit[] | null> {
  let res;
  try {
    res = await runEngine("global", [flag, "--", symbol], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS, env });
  } catch (e) {
    if (e instanceof StaticSightError) return null;
    throw e;
  }
  if (res.returncode !== 0 && res.returncode !== 1) return null;
  return parseXOutput(res.stdout);
}

/** Incremental update of an existing in-repo GTAGS database. */
export function updateInPlace(root: string, env: Record<string, string>): Promise<CmdResult> {
  return runEngine("global", ["-u"], { cwd: root, timeout: INDEX_TIMEOUT_S, env });
}

/** (Re)build the database from an explicit file list (fed on stdin). Returns [result, human-readable action]. */
export async function build(root: string, dbPath: string, env: Record<string, string>, files: string[], incremental: boolean): Promise<[CmdResult, string]> {
  const inRepo = dbPath === root;
  const args = incremental || inRepo ? ["-i", "-f", "-"] : ["-f", "-"];
  if (!inRepo) args.push(dbPath);
  const res = await runEngine("gtags", args, { cwd: root, timeout: INDEX_TIMEOUT_S, env, stdinData: files.join("\n") + "\n" });
  return [res, ["gtags", ...args].slice(0, 4).join(" ") + ` (${files.length} files)`];
}
