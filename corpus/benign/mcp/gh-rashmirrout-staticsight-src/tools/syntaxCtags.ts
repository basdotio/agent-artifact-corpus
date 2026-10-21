// Ctags-driven scope extraction and regex/brace-depth control-flow skeletons.
import { type Config, isCppFile, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { balancedParens, stripCode } from "../core/cppText.js";
import { BLOCK_KINDS, ctagsForFile, FUNCTION_KINDS, innermost, type Tag, cmpStr } from "../engines/ctags.js";
import { changedLines } from "../engines/git.js";
import { readLines, resolveInWorkspace } from "../core/paths.js";
import { InvalidArgument } from "../core/errors.js";

const MAX_SCOPE_LINES = 150;
const MAX_SKELETON_LINES = 3000;
const MAX_SKELETON_NODES = 150;
const NON_NS_BLOCK = new Set([...BLOCK_KINDS].filter((k) => k !== "namespace"));

function checkCpp(rel: string): void {
  if (!isCppFile(rel)) throw new InvalidArgument(`\`${rel}\` is not a C/C++ source or header file.`);
}

function windowRanges(start: number, end: number, target: number): Array<[number, number]> {
  if (end - start + 1 <= MAX_SCOPE_LINES) return [[start, end]];
  const ranges: Array<[number, number]> = [
    [start, Math.min(end, start + 14)],
    [Math.max(start, target - 30), Math.min(end, target + 30)],
    [Math.max(start, end - 9), end],
  ];
  ranges.sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  const merged: Array<[number, number]> = [];
  for (const [a, b] of ranges) {
    if (merged.length && a <= merged[merged.length - 1][1] + 1) {
      merged[merged.length - 1] = [merged[merged.length - 1][0], Math.max(merged[merged.length - 1][1], b)];
    } else merged.push([a, b]);
  }
  return merged;
}

function renderRanges(lines: string[], ranges: Array<[number, number]>, marks: Set<number>): string[] {
  const width = String(ranges[ranges.length - 1][1]).length;
  const out: string[] = [];
  let prevEnd: number | null = null;
  for (const [a, b] of ranges) {
    if (prevEnd !== null && a > prevEnd + 1) out.push(`${" ".repeat(width + 1)} … ${b && a - prevEnd - 1} lines elided …`);
    out.push(...md.numberedCode(lines.slice(a - 1, b), a, marks, width));
    prevEnd = b;
  }
  return out;
}

export async function enclosingScopeReport(cfg: Config, filePath: string, targetLine: number): Promise<string> {
  const [abs, rel] = resolveInWorkspace(cfg.workspaceRoot, filePath);
  checkCpp(rel);
  const lines = readLines(abs);
  if (targetLine < 1 || targetLine > lines.length) {
    throw new InvalidArgument(`Line ${targetLine} is out of range: \`${rel}\` has ${lines.length} lines.`);
  }
  const tags = await ctagsForFile(cfg, rel);
  const scope = innermost(tags, targetLine, NON_NS_BLOCK) ?? innermost(tags, targetLine, BLOCK_KINDS);
  if (scope === null || (scope.kind === "namespace" && scope.end - scope.line + 1 > MAX_SCOPE_LINES)) {
    const a = Math.max(1, targetLine - 12);
    const b = Math.min(lines.length, targetLine + 12);
    const out = [
      `### 📄 FILE-LEVEL CONTEXT: \`${rel}\` L${targetLine}`,
      "_No enclosing function/class found by ctags (global scope, preprocessor block, or code ctags could not parse)._",
    ];
    if (scope !== null) out.push(`- **Enclosing namespace:** \`${scope.qualified}\` (L${scope.line}-${scope.end})`);
    out.push("```cpp", ...md.numberedCode(lines.slice(a - 1, b), a, [targetLine]), "```");
    return out.join("\n");
  }
  const start = scope.line;
  const end = Math.min(scope.end, lines.length);
  const out = [
    `### 📦 ENCLOSING SCOPE: \`${scope.qualified}\` (${scope.kind})`,
    `- **File:** \`${rel}\` L${start}-${end} (${md.plural(end - start + 1, "line")})`,
  ];
  if (scope.kind === "function" || scope.kind === "macro") out.push(`- **Signature:** ${md.codeSpan(scope.displaySignature)}`);
  if (scope.scope) out.push(`- **Parent:** ${scope.scopeKind || "scope"} \`${scope.scope}\``);
  const ranges = windowRanges(start, end, targetLine);
  if (ranges.length > 1) out.push(`- _Large scope: showing head, ±30 lines around L${targetLine}, and tail._`);
  out.push("```cpp", ...renderRanges(lines, ranges, new Set([targetLine])), "```");
  return out.join("\n");
}

export async function get_enclosing_scope(args: { file_path: string; target_line: number }): Promise<string> {
  return enclosingScopeReport(loadConfig(), args.file_path, args.target_line);
}

// --------------------------------------------------------------------------- skeleton
const CONTROL = /(?:\}\s*)*(else\s+if|if|else|switch|case|default|for|while|do|try|catch|return|co_return|throw|break|continue|goto)\b/y;
const LOCK = /\b(?:lock_guard|unique_lock|scoped_lock|shared_lock)\b|(?:\.|->)(?:lock|lock_shared|try_lock)\s*\(\s*\)/;
const UNLOCK = /(?:\.|->)(?:unlock|unlock_shared)\s*\(\s*\)/;
const RELEASE = new RegExp(
  "\\b(?:free|fclose|munmap|close|closesocket|CloseHandle|CloseServiceHandle|RegCloseKey|FindClose|LocalFree|GlobalFree|" +
    "HeapFree|VirtualFree|CoTaskMemFree|SysFreeString|\\w*[Rr]elease\\w*|\\w*[Dd]ealloc\\w*|\\w+_free)\\s*\\(|\\bdelete\\b",
);
const ALLOC = new RegExp(
  "\\b(?:malloc|calloc|realloc|strdup|strndup|fopen|mmap|open|socket|accept|CreateFile\\w*|CreateEvent\\w*|CreateMutex\\w*|" +
    "CreateSemaphore\\w*|CreateThread|CreateProcess\\w*|OpenProcess|OpenThread|OpenService\\w*|OpenSCManager\\w*|" +
    "CreateService\\w*|FindFirstFile\\w*|CoTaskMemAlloc|SysAllocString\\w*|\\w*[Aa]lloc\\w*|\\w*[Aa]cquire\\w*)\\s*\\(|\\bnew\\b",
);
const COM_RELEASE = /(\w+)\s*(?:->|\.)\s*Release\s*\(/;
const ASSIGN_VAR = /(\w+)\s*=(?!=)/;
const RELEASE_VAR = /\bdelete(?:\s*\[\s*\])?\s+(\w+)|\(\s*&?\s*(\w+)/g;
const BRANCH_KEYS = new Set(["if", "else if", "switch", "for", "while", "catch"]);

function nullChecked(v: string, cond: string): boolean {
  const e = md.escapeRegex(v);
  return new RegExp(
    `!\\s*${e}\\b|\\b${e}\\s*==\\s*(?:nullptr|NULL|0|INVALID_HANDLE_VALUE|INVALID_SOCKET|-1)(?!\\w)|` +
      `\\b(?:nullptr|NULL|INVALID_HANDLE_VALUE|INVALID_SOCKET)\\s*==\\s*${e}\\b|\\b${e}\\s*<\\s*0\\b`,
  ).test(cond);
}

function leaks(pending: Map<string, number>, detail: string, conds: Map<number, string>): string[] {
  const active = [...conds.values()].join(" ");
  return [...pending.entries()]
    .sort((a, b) => a[1] - b[1] || cmpStr(a[0], b[0]))
    .filter(([v]) => !new RegExp(`\\b${md.escapeRegex(v)}\\b`).test(detail) && !nullChecked(v, active))
    .map(([v, ln]) => `\`${v}\` (L${ln})`);
}

export function buildSkeleton(lines: string[], start: number, end: number, label: string | null, rel: string, changed: Set<number>): string {
  const strippedAll = stripCode(lines);
  const nodes: string[] = [];
  let depth = 0;
  const pending = new Map<string, number>();
  const conds = new Map<number, string>();
  let single: [number, string] | null = null;
  const stats = { returns: 0, early: 0, throws: 0, loops: 0, warnings: 0 };

  const emit = (d: number, n: number, text: string): void => {
    const prefix = "│   ".repeat(Math.max(d - 1, 0)) + "├── ";
    const mark = changed.has(n) ? " ✏️" : "";
    nodes.push(`${prefix}[L${n}] ${text}${mark}`);
  };
  const exitText = (kw: string, detail: string, early: boolean): string => {
    if (kw === "throw") stats.throws++;
    else stats.returns++;
    if (early) stats.early++;
    let text = (early ? "🛑 " : "↩ ") + kw.toUpperCase();
    if (detail) text += " " + detail;
    const lk = leaks(pending, detail, conds);
    if (lk.length) {
      stats.warnings++;
      text += ` ⚠️ ${early ? "early exit; " : ""}${lk.join(", ")} not released on this path`;
    }
    return text;
  };
  const inlineStmt = (afterCode: string, afterOrig: string, d: number, n: number): void => {
    const im = /^(return|co_return|throw|break|continue|goto)\b/.exec(afterCode);
    if (!im) return;
    const ikw = im[1];
    const semi = afterCode.indexOf(";");
    const idetail = md.clip(afterOrig.slice(ikw.length, semi >= 0 ? semi : afterOrig.length).trim(), 80);
    if (ikw === "return" || ikw === "co_return" || ikw === "throw") emit(d + 1, n, exitText(ikw, idetail, true));
    else emit(d + 1, n, `${ikw.toUpperCase()} ${idetail}`.replace(/\s+$/u, ""));
  };

  const first = md.clip(lines[start - 1].trim(), 100);
  const headerMark = changed.has(start) ? " ✏️" : "";
  for (let n = start; n <= end; n++) {
    const code = strippedAll[n - 1];
    const orig = lines[n - 1];
    const s = code.trim();
    let tmp = s;
    let lead = 0;
    while (tmp.startsWith("}")) {
      lead++;
      tmp = tmp.slice(1).trimStart();
    }
    let eff = depth - lead;
    const opens = code.split("{").length - 1;
    const closes = code.split("}").length - 1;
    depth += opens - closes;
    if (n === start || !s) continue;
    for (const k of [...conds.keys()]) if (k > eff) conds.delete(k);
    if (single !== null) {
      eff = Math.max(eff, single[0] + 1);
      conds.set(eff, single[1]);
      single = null;
      if (s === "{") continue;
    }
    const tags: string[] = [];
    if (LOCK.test(code)) tags.push("🔒 LOCK");
    if (UNLOCK.test(code)) tags.push("🔓 UNLOCK");
    const relM = RELEASE.exec(code);
    if (relM) {
      const com = COM_RELEASE.exec(code);
      RELEASE_VAR.lastIndex = relM.index;
      const vm = com ? null : RELEASE_VAR.exec(code);
      const v = com ? com[1] : vm ? vm[1] || vm[2] || "" : "";
      tags.push(v ? `📤 RELEASE \`${v}\`` : "📤 RELEASE");
      if (v) pending.delete(v);
    } else {
      const allocM = ALLOC.exec(code);
      if (allocM) {
        const am = ASSIGN_VAR.exec(code.slice(0, allocM.index));
        const v = am ? am[1] : "";
        tags.push(v ? `📥 ALLOC \`${v}\`` : "📥 ALLOC");
        if (v) pending.set(v, n);
      }
    }
    const offset = code.length - code.trimStart().length;
    CONTROL.lastIndex = offset;
    const m = CONTROL.exec(code);
    if (!m) {
      if (tags.length) emit(eff, n, `${tags.join(" · ")} — ${md.clip(orig.trim(), 80)}`);
      continue;
    }
    const kw = m[1].replace(/\s+/g, " ");
    const kwEnd = m.index + m[0].length;
    const tagSuffix = tags.length ? " · " + tags.join(" · ") : "";
    if (BRANCH_KEYS.has(kw)) {
      const bp = balancedParens(code, kwEnd);
      const detail = bp ? md.clip(orig.slice(bp[0] + 1, bp[1]).trim(), 80) : "";
      if (kw === "for" || kw === "while") stats.loops++;
      emit(eff, n, (detail ? `${kw.toUpperCase()} (${detail})` : kw.toUpperCase()) + tagSuffix);
      const afterIdx = bp ? bp[1] + 1 : kwEnd;
      const afterCode = code.slice(afterIdx).trim();
      const afterOrig = orig.slice(afterIdx).trim();
      const cond = kw === "if" || kw === "else if" || kw === "while" ? detail : "";
      if (!afterCode) single = [eff, cond];
      else if (afterCode.startsWith("{")) conds.set(eff + 1, cond);
      else inlineStmt(afterCode, afterOrig, eff, n);
    } else if (kw === "else" || kw === "do" || kw === "try") {
      emit(eff, n, kw.toUpperCase() + tagSuffix);
      const afterCode = code.slice(kwEnd).trim();
      const afterOrig = orig.slice(kwEnd).trim();
      if (!afterCode) single = [eff, ""];
      else if (afterCode.startsWith("{")) conds.set(eff + 1, "");
      else inlineStmt(afterCode, afterOrig, eff, n);
    } else if (kw === "case" || kw === "default") {
      const colon = code.indexOf(":", kwEnd);
      const detail = md.clip(orig.slice(kwEnd, colon >= 0 ? colon : orig.length).trim(), 80);
      emit(eff, n, `${kw.toUpperCase()} ${detail}`.replace(/\s+$/u, "") + tagSuffix);
    } else if (kw === "return" || kw === "co_return" || kw === "throw") {
      const semi = code.indexOf(";", kwEnd);
      const detail = md.clip(orig.slice(kwEnd, semi >= 0 ? semi : orig.length).trim(), 80);
      emit(eff, n, exitText(kw, detail, eff >= 2) + tagSuffix);
    } else {
      const semi = code.indexOf(";", kwEnd);
      const detail = md.clip(orig.slice(kwEnd, semi >= 0 ? semi : orig.length).trim(), 80);
      emit(eff, n, `${kw.toUpperCase()} ${detail}`.replace(/\s+$/u, "") + tagSuffix);
    }
  }
  const title = label ? `\`${label}\` (\`${rel}\` L${start}-${end})` : `\`${rel}\` L${start}-${end}`;
  if (!nodes.length) return `### 🌿 BRANCH SKELETON: ${title}\n✅ No control-flow branches, locks or allocations found in this range.`;
  let summary =
    `Paths: ${md.plural(stats.returns, "return")}, ${md.plural(stats.throws, "throw")} ` +
    `(${md.plural(stats.early, "early exit")}), ${md.plural(stats.loops, "loop")}`;
  if (stats.warnings) summary += `; ⚠️ ${md.plural(stats.warnings, "potential leak path")}`;
  const bodyNodes = md.truncateList(nodes, MAX_SKELETON_NODES, "nodes", "Pass a narrower start_line/end_line range.");
  return [
    `### 🌿 BRANCH SKELETON: ${title}`,
    summary + ".",
    "```text",
    `[L${start}] ENTRY ${first}${headerMark}`,
    ...bodyNodes,
    "```",
    "_✏️ changed in diff · 🛑 early exit · ⚠️ heuristic (comment/string-stripped text + brace depth, not a compiler)._",
  ].join("\n");
}

function matchSymbol(tags: Tag[], symbol: string): Tag[] {
  const sym = symbol.trim();
  const short = sym.split("::").pop()!;
  const out: Tag[] = [];
  for (const t of tags) {
    if (!FUNCTION_KINDS.has(t.kind)) continue;
    if (t.qualified === sym || t.name === sym) out.push(t);
    else if (!sym.includes("::") && t.shortName === short) out.push(t);
    else if (sym.includes("::") && t.qualified.endsWith("::" + short) && t.qualified.endsWith(sym)) out.push(t);
  }
  const uniq = new Map<number, Tag>();
  for (const t of out) if (!uniq.has(t.line)) uniq.set(t.line, t);
  return [...uniq.keys()].sort((a, b) => a - b).map((k) => uniq.get(k)!);
}

export async function branchSkeletonReport(cfg: Config, filePath: string, symbol = "", startLine = 0, endLine = 0, baseRef = ""): Promise<string> {
  const [abs, rel] = resolveInWorkspace(cfg.workspaceRoot, filePath);
  checkCpp(rel);
  const lines = readLines(abs);
  const total = lines.length;
  let label: string | null = null;
  let note = "";
  let start: number;
  let end: number;
  if (symbol && symbol.trim()) {
    const tags = await ctagsForFile(cfg, rel);
    const found = matchSymbol(tags, symbol);
    if (!found.length) {
      const names = [...new Set(tags.filter((t) => FUNCTION_KINDS.has(t.kind)).map((t) => t.qualified))].sort(cmpStr);
      const listing = names.slice(0, 12).map((n) => `\`${n}\``).join(", ") || "none";
      throw new InvalidArgument(`No function named \`${symbol}\` found in \`${rel}\`.`, `Functions in this file: ${listing}.`);
    }
    start = found[0].line;
    end = found[0].end;
    label = found[0].qualified;
    if (found.length > 1) note = "_Overloads also at: " + found.slice(1).map((t) => `L${t.line}`).join(", ") + "._";
  } else if (startLine && endLine) {
    if (startLine < 1 || endLine < startLine || startLine > total) {
      throw new InvalidArgument(`Invalid range L${startLine}-${endLine}: \`${rel}\` has ${total} lines.`);
    }
    start = startLine;
    end = Math.min(endLine, total);
    const tags = await ctagsForFile(cfg, rel);
    const fn = innermost(tags, start, FUNCTION_KINDS);
    if (fn && fn.line === start) label = fn.qualified;
  } else if (startLine) {
    if (startLine < 1 || startLine > total) throw new InvalidArgument(`Line ${startLine} is out of range: \`${rel}\` has ${total} lines.`);
    const tags = await ctagsForFile(cfg, rel);
    const fn = innermost(tags, startLine, FUNCTION_KINDS) ?? innermost(tags, startLine, NON_NS_BLOCK);
    if (fn === null) {
      throw new InvalidArgument(`No function encloses \`${rel}:${startLine}\`.`, "Pass an explicit start_line and end_line range instead.");
    }
    start = fn.line;
    end = fn.end;
    label = fn.qualified;
  } else {
    throw new InvalidArgument("Provide `symbol`, or `start_line` (optionally with `end_line`).");
  }
  end = Math.min(end, total, start + MAX_SKELETON_LINES - 1);
  const changed = await changedLines(cfg, rel, baseRef);
  const report = buildSkeleton(lines, start, end, label, rel, changed);
  return report + (note ? "\n" + note : "");
}

export async function get_branch_skeleton(args: { file_path: string; symbol?: string; start_line?: number; end_line?: number }): Promise<string> {
  return branchSkeletonReport(loadConfig(), args.file_path, args.symbol ?? "", args.start_line ?? 0, args.end_line ?? 0);
}
