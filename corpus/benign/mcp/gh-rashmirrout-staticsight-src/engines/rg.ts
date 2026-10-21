// ripgrep runner: always uses --json and parses the event stream natively.
import { CPP_GLOBS, type Config } from "../config.js";
import { ToolFailed } from "../core/errors.js";
import { runEngine, toPosix } from "./base.js";
import { cmpStr } from "./ctags.js";

export interface RgLine {
  path: string;
  line: number;
  text: string;
  isMatch: boolean;
}

export class RgResult {
  files = new Map<string, RgLine[]>();
  truncated = false;

  sortedPaths(): string[] {
    return [...this.files.keys()].sort(cmpStr);
  }

  matches(): RgLine[] {
    const out: RgLine[] = [];
    for (const p of this.sortedPaths()) for (const ln of this.files.get(p)!) if (ln.isMatch) out.push(ln);
    return out;
  }
}

function globArgs(cfg: Config, globs: string[]): string[] {
  const args: string[] = [];
  for (const g of globs) args.push("-g", g);
  for (const ex of cfg.excludes) args.push("-g", "!" + ex);
  return args;
}

export interface RgOptions {
  word?: boolean;
  fixed?: boolean;
  ignoreCase?: boolean;
  context?: number;
  globs?: string[];
  paths?: string[];
  maxCount?: number;
}

export async function rgSearch(cfg: Config, pattern: string | string[], opts: RgOptions = {}): Promise<RgResult> {
  const argv = ["--json", "--no-config", "--no-messages", "--path-separator", "/"];
  if (opts.word) argv.push("-w");
  if (opts.fixed) argv.push("-F");
  if (opts.ignoreCase) argv.push("-i");
  if (opts.context) argv.push("-C", String(opts.context));
  if (opts.maxCount) argv.push("-m", String(opts.maxCount));
  argv.push(...globArgs(cfg, opts.globs ?? CPP_GLOBS));
  for (const p of typeof pattern === "string" ? [pattern] : pattern) argv.push("-e", p);
  argv.push("--");
  argv.push(...(opts.paths && opts.paths.length ? opts.paths : ["."]));
  const res = await runEngine("rg", argv, { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  if (res.returncode === 2 && !res.stdout.trim()) {
    throw new ToolFailed(`\`rg\` failed: ${res.stderr.trim().slice(0, 300)}`, "Check the pattern / path arguments.");
  }
  const out = new RgResult();
  out.truncated = res.truncated;
  for (const raw of res.stdout.split("\n")) {
    if (!raw.startsWith("{")) continue;
    let ev: { type?: string; data?: Record<string, any> };
    try {
      ev = JSON.parse(raw);
    } catch {
      continue;
    }
    if (ev.type !== "match" && ev.type !== "context") continue;
    const data = ev.data ?? {};
    const rawPath: string = data.path?.text ?? "";
    if (!rawPath) continue;
    const path = toPosix(rawPath);
    let text: string = data.lines?.text ?? "";
    text = text.replace(/\n$/, "").replace(/\r$/, "");
    const num = data.line_number;
    if (!Number.isInteger(num)) continue;
    if (!out.files.has(path)) out.files.set(path, []);
    out.files.get(path)!.push({ path, line: num, text, isMatch: ev.type === "match" });
  }
  for (const arr of out.files.values()) arr.sort((a, b) => a.line - b.line);
  return out;
}

export async function rgFiles(cfg: Config, globs: string[] = CPP_GLOBS): Promise<string[]> {
  const argv = ["--files", "--no-config", "--no-messages", "--path-separator", "/", ...globArgs(cfg, globs)];
  const res = await runEngine("rg", argv, { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  return res.stdout
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => toPosix(l.replace(/\r$/, "")))
    .sort(cmpStr);
}
