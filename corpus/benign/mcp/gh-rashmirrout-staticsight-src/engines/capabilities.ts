// Engine discovery + capability checks (used by get_index_status, `doctor`, and the ctags adapter).
import { homedir } from "node:os";
import { StaticSightError, ToolFailed, ToolMissing } from "../core/errors.js";
import { current } from "../platform/index.js";
import { findEngine } from "./base.js";

export const ENGINES: Array<[string, string]> = [
  ["ctags", "required"],
  ["rg", "required"],
  ["git", "required"],
  ["cppcheck", "recommended"],
  ["global", "optional"],
  ["gtags", "optional"],
];
export const PURPOSE: Record<string, string> = {
  ctags: "scopes, signatures, skeletons (Universal Ctags with JSON)",
  rg: "fast text search: struct risks, includes, mutations, fallbacks",
  git: "diffs, base refs, changed-line markers",
  cppcheck: "run_file_static_audit",
  global: "precise callers/definitions (ripgrep fallback without it)",
  gtags: "builds the GNU Global index",
};
export const EXUBERANT_HINT =
  "This is not Universal Ctags with JSON support (Exuberant Ctags and some minimal builds lack it). " +
  "Install Universal Ctags; on Windows note that `scoop install ctags` is Exuberant - use " +
  "`scoop bucket add extras; scoop install universal-ctags` or `winget install UniversalCtags.Ctags`.";

export interface EngineStatus {
  name: string;
  level: string;
  path: string;
  version: string;
  ok: boolean;
  problem: string;
  hint: string;
}

export const cache = new Map<string, EngineStatus>();

async function output(tool: string, exe: string, args: string[]): Promise<string> {
  try {
    const res = await current().run(exe, args, { cwd: homedir(), timeout: 10, displayName: tool });
    return res.stdout + "\n" + res.stderr;
  } catch (e) {
    if (e instanceof StaticSightError) return "";
    throw e;
  }
}

export async function probe(tool: string, level = ""): Promise<EngineStatus> {
  const lvl = level || (Object.fromEntries(ENGINES)[tool] ?? "optional");
  const exe = findEngine(tool);
  if (exe === null) return { name: tool, level: lvl, path: "", version: "", ok: false, problem: "not found on PATH", hint: current().installHint(tool) ?? "" };
  const key = `${tool}\u0000${exe}`;
  const cached = cache.get(key);
  if (cached) return cached;
  const version = (await output(tool, exe, ["--version"])).split("\n").map((l) => l.trim()).find(Boolean) ?? "";
  const st: EngineStatus = { name: tool, level: lvl, path: exe, version, ok: true, problem: "", hint: "" };
  if (tool === "ctags") {
    const features = await output(tool, exe, ["--list-features"]);
    if (version.toLowerCase().includes("exuberant") || !features.toLowerCase().includes("json")) {
      st.ok = false;
      st.problem = `\`${version || "ctags"}\` has no JSON output`;
      st.hint = EXUBERANT_HINT;
    }
  }
  cache.set(key, st);
  return st;
}

export async function probeAll(): Promise<EngineStatus[]> {
  const out: EngineStatus[] = [];
  for (const [t, lvl] of ENGINES) out.push(await probe(t, lvl));
  return out;
}

/** Fail fast with a precise message when ctags is missing or cannot emit JSON. */
export async function ensureCtags(): Promise<void> {
  const st = await probe("ctags");
  if (!st.path) throw new ToolMissing("ctags", st.hint || undefined);
  if (!st.ok) throw new ToolFailed(st.problem, st.hint);
}

export function clearCache(): void {
  cache.clear();
}
