// git helpers: base-ref resolution and a `git diff -U0` hunk parser.
import { join } from "node:path";
import type { Config } from "../config.js";
import { InvalidArgument, StaticSightError } from "../core/errors.js";
import { readLines } from "../core/paths.js";
import { runEngine } from "./base.js";
import { cmpStr } from "./ctags.js";

export const DEFAULT_BASE_CANDIDATES = ["origin/main", "origin/master", "main", "master"];
const HUNK = /^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@/;

export class NotAGitRepo extends StaticSightError {
  constructor(message: string, hint?: string) {
    super(message, hint);
    this.title = "Not a git repository";
  }
}

export class FileDiff {
  addedLines = new Set<number>();
  removedAt = new Map<number, number>();
  additions = 0;
  deletions = 0;
  binary = false;
  constructor(public path: string, public oldPath: string, public status: string) {}

  get touchedLines(): Set<number> {
    return new Set([...this.addedLines, ...this.removedAt.keys()]);
  }
}

export interface DiffInfo {
  baseSha: string;
  baseLabel: string;
  files: FileDiff[];
}

export function diffGet(info: DiffInfo, path: string): FileDiff | null {
  return info.files.find((f) => f.path === path) ?? null;
}

async function git(cfg: Config, args: string[], check = true): Promise<string> {
  const res = await runEngine("git", ["-c", "core.quotepath=off", ...args], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  if (check && res.returncode !== 0) {
    const err = res.stderr.trim();
    if (err.toLowerCase().includes("not a git repository")) {
      throw new NotAGitRepo(`\`${cfg.workspaceRoot}\` is not inside a git repository.`, "Set WORKSPACE_ROOT to the root of a git checkout.");
    }
    throw new StaticSightError(`\`git ${args.slice(0, 2).join(" ")}\` failed: ${err.slice(0, 300)}`);
  }
  return res.stdout;
}

async function rev(cfg: Config, ref: string): Promise<string | null> {
  const res = await runEngine("git", ["rev-parse", "--verify", "--quiet", `${ref}^{commit}`], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  const sha = res.stdout.trim();
  return res.returncode === 0 && sha ? sha : null;
}

async function mergeBase(cfg: Config, ref: string): Promise<string | null> {
  const res = await runEngine("git", ["merge-base", "HEAD", ref], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  const sha = res.stdout.trim();
  return res.returncode === 0 && sha ? sha : null;
}

/** Current HEAD commit, or '' when git is unavailable or the repo has no commits. */
export async function headSha(cfg: Config): Promise<string> {
  try {
    return (await rev(cfg, "HEAD")) ?? "";
  } catch (e) {
    if (e instanceof StaticSightError) return "";
    throw e;
  }
}

export async function resolveBase(cfg: Config, baseRef = ""): Promise<[string, string]> {
  await git(cfg, ["rev-parse", "--git-dir"]);
  const ref = (baseRef || cfg.baseRef).trim();
  if (ref) {
    if (ref.startsWith("-")) throw new InvalidArgument(`\`${ref}\` is not a valid git ref.`);
    const sha = await rev(cfg, ref);
    if (!sha) throw new InvalidArgument(`git ref \`${ref}\` does not exist.`, "Use a branch, tag or commit, e.g. `origin/main`.");
    const mb = await mergeBase(cfg, ref);
    if (mb && mb !== sha) return [mb, `merge-base with \`${ref}\` (${mb.slice(0, 10)})`];
    return [sha, `\`${ref}\` (${sha.slice(0, 10)})`];
  }
  for (const cand of DEFAULT_BASE_CANDIDATES) {
    if (await rev(cfg, cand)) {
      const mb = await mergeBase(cfg, cand);
      if (mb) return [mb, `merge-base with \`${cand}\` (${mb.slice(0, 10)})`];
    }
  }
  const head = await rev(cfg, "HEAD");
  if (!head) throw new StaticSightError("The repository has no commits yet.", "Commit something or pass base_ref.");
  return [head, `\`HEAD\` (${head.slice(0, 10)}), no origin/main or origin/master found`];
}

function unquote(p: string): string {
  p = p.replace(/\t+$/, "");
  if (p.length >= 2 && p[0] === '"' && p[p.length - 1] === '"') {
    p = p.slice(1, -1).replace(/\\(["\\tn])/g, (_, c) => ({ t: "\t", n: "\n" } as Record<string, string>)[c] ?? c);
  }
  return p;
}

export function parseDiff(text: string): FileDiff[] {
  const files: FileDiff[] = [];
  let cur: FileDiff | null = null;
  let inHunk = false;
  for (const line of text.split("\n")) {
    if (line.startsWith("diff --git ")) {
      const m = /^diff --git (?:"?a\/)(.+?)"? (?:"?b\/)(.+?)"?$/.exec(line);
      const [a, b] = m ? [m[1], m[2]] : ["", ""];
      cur = new FileDiff(b, a, "modified");
      files.push(cur);
      inHunk = false;
      continue;
    }
    if (cur === null) continue;
    if (!inHunk) {
      if (line.startsWith("new file mode")) cur.status = "added";
      else if (line.startsWith("deleted file mode")) cur.status = "deleted";
      else if (line.startsWith("rename from ")) {
        cur.oldPath = unquote(line.slice("rename from ".length));
        cur.status = "renamed";
      } else if (line.startsWith("rename to ")) {
        cur.path = unquote(line.slice("rename to ".length));
        cur.status = "renamed";
      } else if (line.startsWith("Binary files ")) cur.binary = true;
      else if (line.startsWith("--- ")) {
        const p = unquote(line.slice(4));
        if (p !== "/dev/null" && p.startsWith("a/")) cur.oldPath = p.slice(2);
      } else if (line.startsWith("+++ ")) {
        const p = unquote(line.slice(4));
        if (p === "/dev/null") {
          cur.status = "deleted";
          cur.path = cur.oldPath;
        } else if (p.startsWith("b/")) cur.path = p.slice(2);
      }
    }
    const m = HUNK.exec(line);
    if (m) {
      inHunk = true;
      const oldCount = m[2] !== undefined ? parseInt(m[2], 10) : 1;
      const newStart = parseInt(m[3], 10);
      const newCount = m[4] !== undefined ? parseInt(m[4], 10) : 1;
      if (newCount > 0) for (let k = newStart; k < newStart + newCount; k++) cur.addedLines.add(k);
      if (oldCount > 0) {
        const anchor = newCount > 0 ? newStart : Math.max(newStart, 1);
        cur.removedAt.set(anchor, (cur.removedAt.get(anchor) ?? 0) + oldCount);
      }
      continue;
    }
    if (inHunk) {
      if (line.startsWith("+")) cur.additions++;
      else if (line.startsWith("-")) cur.deletions++;
    }
  }
  return files;
}

export async function collectDiff(cfg: Config, baseRef = "", includeUntracked = true, path?: string): Promise<DiffInfo> {
  const [sha, label] = await resolveBase(cfg, baseRef);
  const args = ["diff", "-U0", "--no-color", "--no-ext-diff", "--no-textconv", "-M", sha, "--"];
  if (path) args.push(path);
  const files = parseDiff(await git(cfg, args));
  if (includeUntracked) {
    const lsArgs = ["ls-files", "--others", "--exclude-standard", "-z", "--"];
    if (path) lsArgs.push(path);
    const out = await git(cfg, lsArgs);
    for (const rel of out.split("\0").filter(Boolean).sort(cmpStr)) {
      const fd = new FileDiff(rel, rel, "untracked");
      let n = 0;
      try {
        n = readLines(join(cfg.workspaceRoot, rel)).length;
      } catch {
        n = 0;
      }
      for (let k = 1; k <= n; k++) fd.addedLines.add(k);
      fd.additions = n;
      files.push(fd);
    }
  }
  files.sort((a, b) => cmpStr(a.path, b.path));
  return { baseSha: sha, baseLabel: label, files };
}

export async function showBlob(cfg: Config, sha: string, path: string): Promise<string | null> {
  const res = await runEngine("git", ["show", `${sha}:${path}`], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
  return res.returncode === 0 ? res.stdout : null;
}

export async function changedLines(cfg: Config, relPath: string, baseRef = ""): Promise<Set<number>> {
  try {
    const info = await collectDiff(cfg, baseRef, true, relPath);
    const fd = diffGet(info, relPath);
    return fd ? fd.touchedLines : new Set();
  } catch (e) {
    if (e instanceof StaticSightError) return new Set();
    throw e;
  }
}
