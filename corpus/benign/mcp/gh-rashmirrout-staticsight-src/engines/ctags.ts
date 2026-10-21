// Universal Ctags JSON runner with an mtime-keyed cache, plus scope lookup helpers.
import { statSync } from "node:fs";
import { dirname, join } from "node:path";
import type { Config } from "../config.js";
import { StaticSightError, ToolFailed } from "../core/errors.js";
import { runEngine, toPosix } from "./base.js";
import { ensureCtags } from "./capabilities.js";

export const BLOCK_KINDS = new Set(["function", "class", "struct", "union", "enum", "namespace", "macro"]);
export const FUNCTION_KINDS = new Set(["function"]);
export const TYPE_KINDS = new Set(["class", "struct", "union", "enum"]);
export const DEFINITION_KINDS = new Set(["function", "class", "struct", "union", "enum", "macro", "typedef", "namespace", "variable", "member"]);
const KIND_PRIORITY: Record<string, number> = { function: 0, struct: 1, class: 1, union: 1, enum: 2, macro: 3, namespace: 4 };

/** Language auto-detection (any language Universal Ctags knows); used by the semantic chunker. */
export const CTAGS_GENERIC_ARGS = ["--output-format=json", "--fields=+neKSZ", "--sort=no", "-f", "-"];
export const CTAGS_ARGS = ["--output-format=json", "--fields=+neKSZ", "--kinds-C++=+p", "--sort=no", "--language-force=C++", "-f", "-"];

export class Tag {
  constructor(
    public name: string,
    public kind: string,
    public line: number,
    public end: number,
    public path: string,
    public scope = "",
    public scopeKind = "",
    public signature = "",
    public typeref = "",
    public pattern = "",
  ) {}

  get qualified(): string {
    if (!this.scope || this.name.includes("::")) return this.name;
    return `${this.scope}::${this.name}`;
  }

  get shortName(): string {
    const parts = this.name.split("::");
    return parts[parts.length - 1];
  }

  get returnType(): string {
    return this.typeref.startsWith("typename:") ? this.typeref.slice("typename:".length) : this.typeref;
  }

  get displaySignature(): string {
    const rt = this.returnType;
    const sig = ["function", "prototype", "macro"].includes(this.kind) ? this.signature : "";
    const base = `${this.qualified}${sig}`;
    return rt ? `${rt} ${base}`.trim() : base;
  }

  get key(): string {
    return `${this.path}\u0000${this.line}\u0000${this.kind}\u0000${this.qualified}`;
  }

  withPath(path: string): Tag {
    return new Tag(this.name, this.kind, this.line, this.end, path, this.scope, this.scopeKind, this.signature, this.typeref, this.pattern);
  }
}

const cache = new Map<string, { mtime: number; size: number; tags: Tag[] }>();

/** ctags names anonymous namespaces/structs with a per-run hash; normalise so runs are comparable. */
function anon(text: string): string {
  return text.replace(/__anon[0-9a-f]+/g, "(anonymous)");
}

function parse(stdout: string): Map<string, Tag[]> {
  const byPath = new Map<string, Tag[]>();
  for (let raw of stdout.split("\n")) {
    raw = raw.trim();
    if (!raw.startsWith("{")) continue;
    let d: Record<string, unknown>;
    try {
      d = JSON.parse(raw);
    } catch {
      continue;
    }
    if (d._type !== "tag" || !Number.isInteger(d.line)) continue;
    const path = toPosix(String(d.path ?? ""));
    const line = d.line as number;
    const end = Number.isInteger(d.end) ? (d.end as number) : line;
    const tag = new Tag(
      anon(String(d.name ?? "")),
      String(d.kind ?? ""),
      line,
      Math.max(end, line),
      path,
      anon(String(d.scope ?? "")),
      String(d.scopeKind ?? ""),
      String(d.signature ?? ""),
      String(d.typeref ?? ""),
      String(d.pattern ?? ""),
    );
    if (!byPath.has(path)) byPath.set(path, []);
    byPath.get(path)!.push(tag);
  }
  return byPath;
}

function arg(rel: string): string {
  return rel.startsWith("-") ? "./" + rel : rel;
}

/** generic=false parses every file as C++ (review tools); generic=true lets ctags detect each file's language. */
export async function ctagsForFiles(cfg: Config, relPaths: string[], generic = false): Promise<Map<string, Tag[]>> {
  const args = generic ? CTAGS_GENERIC_ARGS : CTAGS_ARGS;
  const mode = generic ? "g:" : "c:";
  const result = new Map<string, Tag[]>();
  const todo: string[] = [];
  const stats = new Map<string, [number, number]>();
  for (const rel of new Set(relPaths)) {
    let st;
    try {
      st = statSync(join(cfg.workspaceRoot, rel), { bigint: true });
    } catch {
      result.set(rel, []);
      continue;
    }
    const mt = Number(st.mtimeNs);
    const sz = Number(st.size);
    stats.set(rel, [mt, sz]);
    const cached = cache.get(mode + join(cfg.workspaceRoot, rel));
    if (cached && cached.mtime === mt && cached.size === sz) result.set(rel, cached.tags);
    else todo.push(rel);
  }
  if (todo.length) await ensureCtags();
  for (let i = 0; i < todo.length; i += 200) {
    const batch = todo.slice(i, i + 200);
    const res = await runEngine("ctags", [...args, ...batch.map(arg)], { cwd: cfg.workspaceRoot, timeout: cfg.timeoutS });
    if (res.returncode !== 0 && !res.stdout.trim()) {
      if (res.stderr.toLowerCase().includes("json")) {
        throw new ToolFailed(
          "`ctags` does not support `--output-format=json`.",
          "Install Universal Ctags built with libjansson (Exuberant Ctags is not supported).",
        );
      }
      throw new ToolFailed(`\`ctags\` failed: ${res.stderr.trim().slice(0, 300)}`);
    }
    const parsed = parse(res.stdout);
    for (const rel of batch) {
      const tags = parsed.get(rel) ?? [];
      result.set(rel, tags);
      const [mt, sz] = stats.get(rel)!;
      cache.set(mode + join(cfg.workspaceRoot, rel), { mtime: mt, size: sz, tags });
    }
  }
  return result;
}

export async function ctagsForFile(cfg: Config, relPath: string): Promise<Tag[]> {
  return (await ctagsForFiles(cfg, [relPath])).get(relPath) ?? [];
}

export async function ctagsForTemp(cfg: Config, absPath: string, logicalPath: string): Promise<Tag[]> {
  await ensureCtags();
  const res = await runEngine("ctags", [...CTAGS_ARGS, absPath], { cwd: dirname(absPath), timeout: cfg.timeoutS });
  const out: Tag[] = [];
  for (const ts of parse(res.stdout).values()) for (const t of ts) out.push(t.withPath(logicalPath));
  return out;
}

export async function tryCtagsForFiles(cfg: Config, relPaths: string[], generic = false): Promise<Map<string, Tag[]>> {
  try {
    return await ctagsForFiles(cfg, relPaths, generic);
  } catch (e) {
    if (e instanceof StaticSightError) return new Map();
    throw e;
  }
}

function cmpStr(a: string, b: string): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

export function scopeCompare(a: Tag, b: Tag): number {
  return (
    a.end - a.line - (b.end - b.line) ||
    -a.line - -b.line ||
    (KIND_PRIORITY[a.kind] ?? 9) - (KIND_PRIORITY[b.kind] ?? 9) ||
    cmpStr(a.name, b.name)
  );
}

export function innermost(tags: Iterable<Tag>, line: number, kinds: Set<string> = BLOCK_KINDS): Tag | null {
  let best: Tag | null = null;
  for (const t of tags) {
    if (!kinds.has(t.kind) || !(t.line <= line && line <= t.end)) continue;
    if (best === null || scopeCompare(t, best) < 0) best = t;
  }
  return best;
}

export function clearCache(): void {
  cache.clear();
}

export { cmpStr };
