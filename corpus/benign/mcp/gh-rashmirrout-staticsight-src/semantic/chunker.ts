// Language-agnostic chunking into embeddable units (identical algorithm to the Python implementation):
// structural languages via ctags (innermost units, container gaps, file-level gaps), markdown by heading, the rest by
// line windows; long chunks are split into overlapping windows. Lengths are counted in code points like Python.
import { cmpStr, Tag } from "../engines/ctags.js";
import { cpLength, isStructural, rules } from "./files.js";

export const MAX_CHARS = 1200;
export const WINDOW_OVERLAP = 2;
export const LINE_CLIP = 300;
export const MAX_COMMENT_LINES = 15;
const SIGNIFICANT = /[A-Za-z0-9]/;
const HEADING = /^(#{1,6})\s+(.*?)\s*#*\s*$/;
export const CONTAINER_KINDS = new Set([
  "class", "struct", "union", "enum", "interface", "trait", "impl", "implementation", "namespace", "module",
  "type", "record", "protocol", "object", "package", "anonymousClass",
]);

export interface Chunk {
  path: string;
  startLine: number;
  endLine: number;
  language: string;
  kind: string;
  symbol: string;
  signature: string;
  part: number;
  text: string;
}

function significant(line: string): boolean {
  return SIGNIFICANT.test(line);
}

function clipCp(line: string, n: number): string {
  // eslint-disable-next-line no-control-regex
  if (/^[\x00-\x7f]*$/.test(line)) return line.slice(0, n);
  return Array.from(line).slice(0, n).join("");
}

export function header(path: string, kind: string, symbol: string, signature: string, part: number): string {
  let h = `${path} | ${kind}`;
  if (symbol) h += ` ${symbol}`;
  if (signature) h += ` | ${signature}`;
  if (part) h += ` (part ${part + 1})`;
  return h;
}

function windows(start: number, end: number, lines: string[]): Array<[number, number]> {
  const out: Array<[number, number]> = [];
  let s = start;
  while (s <= end) {
    let size = 0;
    let e = s;
    while (e <= end) {
      const add = Math.min(cpLength(lines[e - 1]), LINE_CLIP) + 1;
      if (size + add > MAX_CHARS && e > s) break;
      size += add;
      e++;
    }
    e--;
    out.push([s, e]);
    if (e >= end) break;
    s = Math.max(e - WINDOW_OVERLAP + 1, s + 1);
  }
  return out;
}

function emit(chunks: Chunk[], path: string, lines: string[], start: number, end: number, language: string, kind: string, symbol: string, signature: string): void {
  windows(start, end, lines).forEach(([a, b], part) => {
    const body = lines.slice(a - 1, b).map((ln) => clipCp(ln, LINE_CLIP)).join("\n");
    chunks.push({ path, startLine: a, endLine: b, language, kind, symbol, signature, part, text: header(path, kind, symbol, signature, part) + "\n" + body });
  });
}

function ranges(covered: boolean[], lo: number, hi: number): Array<[number, number]> {
  const runs: Array<[number, number]> = [];
  let s: number | null = null;
  for (let n = lo; n <= hi; n++) {
    if (!covered[n]) {
      if (s === null) s = n;
    } else if (s !== null) {
      runs.push([s, n - 1]);
      s = null;
    }
  }
  if (s !== null) runs.push([s, hi]);
  return runs;
}

function trim(lines: string[], a: number, b: number): [number, number] | null {
  while (a <= b && !lines[a - 1].trim()) a++;
  while (b >= a && !lines[b - 1].trim()) b--;
  if (a > b) return null;
  let sig = 0;
  for (let n = a; n <= b; n++) if (significant(lines[n - 1])) sig++;
  return sig < 2 ? null : [a, b];
}

function isComment(line: string, prefixes: string[]): boolean {
  const s = line.trim();
  return !!s && prefixes.some((p) => s.startsWith(p));
}

export function chunkStructural(path: string, lines: string[], language: string, tags: Tag[]): Chunk[] {
  const unitKinds = new Set(rules().unit_kinds);
  const n = lines.length;
  const seen = new Set<string>();
  const units: Tag[] = [];
  const sorted = [...tags].sort((a, b) => a.line - b.line || b.end - a.end || cmpStr(a.name, b.name));
  for (const t of sorted) {
    const end = Math.min(t.end, n);
    // multi-line units only: one-line members/functions stay in the surrounding gap chunk
    if (!unitKinds.has(t.kind) || t.line < 1 || t.line > n || end <= t.line) continue;
    const key = `${t.line}:${end}`;
    if (seen.has(key)) continue;
    seen.add(key);
    units.push(new Tag(t.name, t.kind, t.line, end, t.path, t.scope, t.scopeKind, t.signature, t.typeref));
  }
  const contains = (a: Tag, b: Tag) => a !== b && a.line <= b.line && b.end <= a.end && !(a.line === b.line && a.end === b.end);
  const children = new Map<Tag, Tag[]>(units.map((u) => [u, units.filter((v) => contains(u, v))]));
  const leaves = units.filter((u) => !children.get(u)!.length);
  const containers = units.filter((u) => children.get(u)!.length);
  const prefixes = rules().comment_prefixes[language] ?? [];
  const covered: boolean[] = new Array(n + 2).fill(false);
  for (const u of units) for (let k = u.line; k <= u.end; k++) covered[k] = true;
  const attached: boolean[] = new Array(n + 2).fill(false);
  const commentStart = new Map<Tag, number>();
  const attachComments = (u: Tag): number => {
    let start = u.line;
    let k = u.line - 1;
    let steps = 0;
    while (k >= 1 && steps < MAX_COMMENT_LINES && !covered[k] && isComment(lines[k - 1], prefixes)) {
      start = k;
      k--;
      steps++;
    }
    for (let c = start; c < u.line; c++) {
      covered[c] = true;
      attached[c] = true;
    }
    return start;
  };
  const bottomUp = [...leaves, ...containers].sort((a, b) => b.line - a.line || a.end - b.end);
  for (const u of bottomUp) commentStart.set(u, attachComments(u));
  const chunks: Chunk[] = [];
  for (const u of leaves) {
    const sig = CONTAINER_KINDS.has(u.kind) ? "" : u.signature;
    emit(chunks, path, lines, commentStart.get(u)!, u.end, language, u.kind, u.qualified, sig);
  }
  for (const u of containers) {
    const inner = [...attached];
    for (const v of children.get(u)!) for (let k = v.line; k <= v.end; k++) inner[k] = true;
    const sig = CONTAINER_KINDS.has(u.kind) ? "" : u.signature;
    for (let [a, b] of ranges(inner, u.line, u.end)) {
      if (a === u.line) a = commentStart.get(u)!;
      const tr = trim(lines, a, b);
      if (tr) emit(chunks, path, lines, tr[0], tr[1], language, u.kind, u.qualified, sig);
    }
  }
  for (const [a, b] of ranges(covered, 1, n)) {
    const tr = trim(lines, a, b);
    if (tr) emit(chunks, path, lines, tr[0], tr[1], language, "file", "", "");
  }
  chunks.sort((x, y) => x.startLine - y.startLine || x.endLine - y.endLine || x.part - y.part || cmpStr(x.kind, y.kind) || cmpStr(x.symbol, y.symbol));
  return chunks;
}

export function chunkMarkdown(path: string, lines: string[], language: string): Chunk[] {
  const heads: Array<[number, string]> = [];
  let fence = false;
  lines.forEach((ln, i) => {
    if (ln.trimStart().startsWith("```") || ln.trimStart().startsWith("~~~")) {
      fence = !fence;
      return;
    }
    const m = fence ? null : HEADING.exec(ln);
    if (m) heads.push([i + 1, m[2]]);
  });
  const bounds: Array<[number, number, string]> = [];
  if (!heads.length || heads[0][0] > 1) bounds.push([1, heads.length ? heads[0][0] - 1 : lines.length, ""]);
  heads.forEach(([ln, title], j) => bounds.push([ln, j + 1 < heads.length ? heads[j + 1][0] - 1 : lines.length, title]));
  const chunks: Chunk[] = [];
  for (let [a, b, title] of bounds) {
    let tr: [number, number] | null;
    if (title) {
      while (b > a && !lines[b - 1].trim()) b--;
      tr = [a, b];
    } else tr = trim(lines, a, b);
    if (tr) {
      let any = false;
      for (let k = tr[0]; k <= tr[1]; k++) if (significant(lines[k - 1])) any = true;
      if (any) emit(chunks, path, lines, tr[0], tr[1], language, "section", title, "");
    }
  }
  return chunks;
}

export function chunkPlain(path: string, lines: string[], language: string): Chunk[] {
  let tr = trim(lines, 1, lines.length);
  if (!tr) {
    const a = lines.findIndex((ln) => significant(ln)) + 1;
    if (!a) return [];
    tr = [a, a];
  }
  const chunks: Chunk[] = [];
  emit(chunks, path, lines, tr[0], tr[1], language, "window", "", "");
  return chunks;
}

export function chunkFile(path: string, lines: string[], language: string, tags: Tag[] | null | undefined): Chunk[] {
  if (language === "markdown") return chunkMarkdown(path, lines, language);
  if (isStructural(language) && tags && tags.length) return chunkStructural(path, lines, language, tags);
  return chunkPlain(path, lines, language);
}
