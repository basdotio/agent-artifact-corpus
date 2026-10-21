// GNU Global powered navigation: callers, definitions and contracts (with ripgrep + ctags fallback).
import { join } from "node:path";
import { type Config, isCppFile, isHeader, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { balancedParens, extractLeadingComment, stripCode } from "../core/cppText.js";
import { cmpStr, DEFINITION_KINDS, FUNCTION_KINDS, innermost, Tag, tryCtagsForFiles, TYPE_KINDS } from "../engines/ctags.js";
import { matchesGlob, readLines } from "../core/paths.js";
import { rgSearch } from "../engines/rg.js";
import { InvalidArgument } from "../core/errors.js";
import * as gnuGlobal from "../engines/gnuGlobal.js";
import type { Hit } from "../engines/gnuGlobal.js";
import { getIndexer } from "../indexer.js";

const IDENT = /^[A-Za-z_~][A-Za-z0-9_]*$/;
export const GLOBAL_LINE = gnuGlobal.GLOBAL_LINE;
const MAX_FILES_FALLBACK = 300;
export const SOURCE_GLOBAL = "GNU Global";
export const SOURCE_RG = "ripgrep fallback: text match, lower precision";

export type { Hit };

export function normalizeSymbol(symbol: string): string {
  let sym = (symbol ?? "").trim();
  if (sym.endsWith("()")) sym = sym.slice(0, -2);
  const short = sym.split("::").pop() ?? "";
  if (!IDENT.test(short)) {
    throw new InvalidArgument(`\`${symbol}\` is not a valid C++ identifier.`, "Pass a plain name such as `process_packet` or `Router::process_packet`.");
  }
  return short;
}

export class FileCache {
  lines = new Map<string, string[]>();
  stripped = new Map<string, string[]>();
  tags = new Map<string, Tag[]>();
  constructor(public cfg: Config) {}

  getLines(path: string): string[] {
    if (!this.lines.has(path)) {
      try {
        this.lines.set(path, readLines(join(this.cfg.workspaceRoot, path)));
      } catch {
        this.lines.set(path, []);
      }
    }
    return this.lines.get(path)!;
  }

  getStripped(path: string): string[] {
    if (!this.stripped.has(path)) this.stripped.set(path, stripCode(this.getLines(path)));
    return this.stripped.get(path)!;
  }

  async loadTags(paths: string[]): Promise<void> {
    const todo = [...new Set(paths)].filter((p) => !this.tags.has(p));
    if (todo.length) {
      const got = await tryCtagsForFiles(this.cfg, todo);
      for (const p of todo) this.tags.set(p, got.get(p) ?? []);
    }
  }
}

export async function globalQuery(cfg: Config, flag: string, symbol: string): Promise<Hit[] | null> {
  const idx = getIndexer(cfg);
  if (!(await idx.ensureReady())) return null;
  return gnuGlobal.query(cfg, idx.env(), flag, symbol);
}

async function candidateFiles(cfg: Config, sym: string): Promise<string[]> {
  const res = await rgSearch(cfg, sym, { word: true, fixed: true, maxCount: 1 });
  return res.sortedPaths().slice(0, MAX_FILES_FALLBACK);
}

export async function findDefinitions(cfg: Config, sym: string, fc: FileCache): Promise<[Tag[], string]> {
  const hits = await globalQuery(cfg, "-xd", sym);
  let source = SOURCE_GLOBAL;
  const defs: Tag[] = [];
  if (hits && hits.length) {
    await fc.loadTags(hits.filter((h) => isCppFile(h.path)).map((h) => h.path));
    for (const h of hits) {
      const tag = (fc.tags.get(h.path) ?? []).find((t) => t.line === h.line && t.shortName === sym && t.kind !== "prototype");
      defs.push(tag ?? new Tag(sym, "definition", h.line, h.line, h.path));
    }
  }
  if (!defs.length) {
    if (hits === null) source = SOURCE_RG;
    const files = await candidateFiles(cfg, sym);
    await fc.loadTags(files);
    for (const p of files) for (const t of fc.tags.get(p) ?? []) if (t.shortName === sym && DEFINITION_KINDS.has(t.kind)) defs.push(t);
    if (hits !== null && defs.length) source = "ctags (GNU Global had no definition)";
  }
  const uniq = new Map<string, Tag>();
  for (const t of defs) uniq.set(`${t.path}\u0000${t.line}\u0000${t.kind}`, t);
  const out = [...uniq.values()].sort((a, b) => cmpStr(a.path, b.path) || a.line - b.line || cmpStr(a.kind, b.kind));
  return [out, source];
}

export async function findDeclarations(cfg: Config, sym: string, fc: FileCache): Promise<Tag[]> {
  const files = await candidateFiles(cfg, sym);
  await fc.loadTags(files);
  const out: Tag[] = [];
  for (const p of files) for (const t of fc.tags.get(p) ?? []) if (t.shortName === sym && t.kind === "prototype") out.push(t);
  return out.sort((a, b) => Number(!isHeader(a.path)) - Number(!isHeader(b.path)) || cmpStr(a.path, b.path) || a.line - b.line);
}

// --------------------------------------------------------------------------- callers
const CHAIN = /^[\w.\->\[\]()*&:\s]*$/;

export function classifyCall(code: string, sym: string): string {
  const m = new RegExp(`\\b${md.escapeRegex(sym)}\\b`).exec(code);
  if (!m) return "";
  const mEnd = m.index + m[0].length;
  const afterSym = code.slice(mEnd).trimStart();
  if (!afterSym.startsWith("(") && !afterSym.startsWith("<")) return "referenced (address/callback)";
  const bp = balancedParens(code, mEnd);
  const after = bp ? code.slice(bp[1] + 1).trim() : "";
  const prefix = code.slice(0, m.index).trim();
  if (/\(\s*void\s*\)\s*[\w.\->:]*$/.test(prefix)) return "result explicitly discarded";
  if (after === ";" && CHAIN.test(prefix) && !prefix.replace(/->/g, "").includes("(") && !prefix.startsWith("return")) return "⚠️ result ignored";
  return "result used";
}

export async function callersReport(cfg: Config, symbol: string, pathGlob = ""): Promise<string> {
  const sym = normalizeSymbol(symbol);
  const fc = new FileCache(cfg);
  let hits = await globalQuery(cfg, "-xr", sym);
  let source = SOURCE_GLOBAL;
  if (hits === null) {
    source = SOURCE_RG;
    const res = await rgSearch(cfg, `\\b${sym}\\s*\\(|&\\s*(?:\\w+::)*${sym}\\b`);
    hits = res.matches().map((m) => ({ path: m.path, line: m.line, text: m.text }));
  }
  hits = hits.filter((h) => isCppFile(h.path) && matchesGlob(h.path, pathGlob));
  await fc.loadTags(hits.map((h) => h.path));
  const [defs] = await findDefinitions(cfg, sym, fc);
  const retTypes = new Set(defs.filter((t) => (FUNCTION_KINDS.has(t.kind) || t.kind === "prototype") && t.returnType).map((t) => t.returnType));
  const returnsVoid = retTypes.size > 0 && [...retTypes].every((t) => t === "void");
  const symRx = new RegExp(`\\b${md.escapeRegex(sym)}\\b`);
  const rows: Array<[string, number, string, string, string]> = [];
  for (const h of hits) {
    const stripped = fc.getStripped(h.path);
    const lines = fc.getLines(h.path);
    if (!(h.line > 0 && h.line <= lines.length)) continue;
    const code = stripped[h.line - 1];
    if (!symRx.test(code)) continue;
    const tags = fc.tags.get(h.path) ?? [];
    if (tags.some((t) => t.line === h.line && t.shortName === sym && ["prototype", "function", "macro"].includes(t.kind))) continue;
    const fn = innermost(tags, h.line, FUNCTION_KINDS);
    const caller = fn ? fn.qualified : "(file scope)";
    const usageKind = classifyCall(code, sym);
    const e = md.escapeRegex(sym);
    if (usageKind === "referenced (address/callback)" && !new RegExp(`&\\s*(?:\\w+::)*${e}\\b|(?:\\w+::|\\.|->)${e}\\b\\s*[,)]`).test(code)) {
      continue; // same-named variable/parameter, not a call or function reference
    }
    const usage = returnsVoid ? "" : usageKind;
    rows.push([h.path, h.line, caller, usage, lines[h.line - 1].trim()]);
  }
  const title = `### 📞 UPSTREAM CALLERS: \`${sym}\``;
  if (!rows.length) {
    return `${title}\n✅ No call sites found (source: ${source}). The symbol may be unused, called via macro, or only referenced dynamically.`;
  }
  const files = [...new Set(rows.map((r) => r[0]))].sort(cmpStr);
  const ignored = rows.filter((r) => r[3].startsWith("⚠️")).length;
  const head = [title, `Found ${md.plural(rows.length, "call site")} in ${md.plural(files.length, "file")} (source: ${source}).`];
  if (retTypes.size) {
    const rt = [...retTypes].sort(cmpStr).map((t) => `\`${t}\``).join(", ");
    head.push(`Returns ${rt}` + (ignored ? `; ⚠️ ${ignored} caller(s) ignore the result — check they tolerate new error values.` : "."));
  }
  const items: string[] = [];
  let cur: string | null = null;
  rows.forEach(([path, line, caller, usage, text], i) => {
    const entry: string[] = [];
    if (path !== cur) {
      entry.push(`**\`${path}\`**`);
      cur = path;
    }
    entry.push(`${i + 1}. L${line} in \`${caller}\`${usage ? ` — ${usage}` : ""}`);
    entry.push(`   ${md.codeSpan(text)}`);
    items.push(entry.join("\n"));
  });
  const shown = md.truncateList(items, cfg.maxResults, "call sites", "Use path_glob to focus on a directory.");
  if (rows.length > cfg.maxResults) {
    const counts = new Map<string, number>();
    for (const r of rows) counts.set(r[0], (counts.get(r[0]) ?? 0) + 1);
    const top = [...counts.entries()].sort((a, b) => b[1] - a[1] || cmpStr(a[0], b[0])).slice(0, 8);
    shown.push("_Top files: " + top.map(([p, n]) => `\`${p}\` (${n})`).join(", ") + "._");
  }
  return [...head, "", ...shown].join("\n");
}

export async function get_upstream_callers(args: { symbol: string; path_glob?: string }): Promise<string> {
  return callersReport(loadConfig(), args.symbol, args.path_glob ?? "");
}

// --------------------------------------------------------------------------- definitions
function loc(t: Tag): string {
  return t.end <= t.line ? `${t.path}:${t.line}` : `${t.path}:${t.line}-${t.end}`;
}

export async function definitionsReport(cfg: Config, symbol: string): Promise<string> {
  const sym = normalizeSymbol(symbol);
  const fc = new FileCache(cfg);
  const [defs, source] = await findDefinitions(cfg, sym, fc);
  const title = `### 📍 DEFINITIONS: \`${sym}\``;
  if (!defs.length) {
    return `${title}\n❌ No definition found (source: ${source}). It may come from a system/third-party header or be generated by a macro.`;
  }
  const items = defs.map((t, i) => {
    let line = `${i + 1}. \`${loc(t)}\` — ${t.kind} \`${t.qualified}\``;
    if ((t.kind === "function" || t.kind === "macro") && t.signature) line += `\n   ${md.codeSpan(t.displaySignature)}`;
    else if (t.kind === "definition") {
      const ls = fc.getLines(t.path);
      const text = t.line > 0 && t.line <= ls.length ? ls[t.line - 1].trim() : "";
      if (text) line += `\n   ${md.codeSpan(text)}`;
    }
    return line;
  });
  return [`${title} (${defs.length}, source: ${source})`, ...md.truncateList(items, cfg.maxResults, "definitions")].join("\n");
}

export async function get_symbol_definition(args: { symbol: string }): Promise<string> {
  return definitionsReport(loadConfig(), args.symbol);
}

// --------------------------------------------------------------------------- contract
const QUALIFIERS: Array<[string, RegExp]> = [
  ["[[nodiscard]]", /\[\[\s*nodiscard/],
  ["[[deprecated]]", /\[\[\s*deprecated/],
  ["template", /^\s*template\s*</],
  ["virtual", /\bvirtual\b/],
  ["pure virtual (= 0)", /\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?=\s*0\s*;/],
  ["static", /\bstatic\b/],
  ["inline", /\binline\b/],
  ["constexpr", /\bconstexpr\b/],
  ["explicit", /\bexplicit\b/],
  ["const", /\)\s*const\b/],
  ["noexcept", /\bnoexcept\b/],
  ["override", /\boverride\b/],
  ["final", /\bfinal\b/],
  ["= delete", /=\s*delete\b/],
  ["= default", /=\s*default\b/],
];
const DOXY_TAG = /^[@\\](pre|post|return|returns|retval|throws|throw|exception|warning|note|attention|invariant|param|thread_safety|deprecated)\b/;
const OBLIGATION =
  /\b(must|shall|never|always|required?|do not|don't|only|thread[- ]safe|not thread[- ]safe|ownership|owns|caller|callee|non-null|not null|nullptr|lock(?:ed)?|mutex|reentrant|blocking|free|release|paired)\b/i;

function declText(stripped: string[], lines: string[], t: Tag): string {
  const start = Math.max(t.line - 2, 0);
  const chunk: string[] = [];
  for (let i = start; i < Math.min(lines.length, t.line + 6); i++) {
    chunk.push(stripped[i]);
    if (i >= t.line - 1 && (stripped[i].includes("{") || stripped[i].includes(";"))) break;
  }
  return chunk.join(" ");
}

function qualifiers(decl: string): string[] {
  const head = decl.split("{")[0];
  return QUALIFIERS.filter(([, rx]) => rx.test(head)).map(([n]) => n);
}

function obligations(doc: string[]): string[] {
  const out: string[] = [];
  let cur: string | null = null;
  for (const line of [...doc, ""]) {
    const tm = DOXY_TAG.exec(line);
    if (tm || !line.trim()) {
      if (cur) out.push(cur);
      cur = null;
      if ((tm && tm[1] !== "param") || (tm && OBLIGATION.test(line))) cur = line.trim();
      continue;
    }
    if (cur !== null) cur += " " + line.trim();
    else if (OBLIGATION.test(line)) out.push(line.trim());
  }
  return [...new Set(out)];
}

export async function contractReport(cfg: Config, symbol: string): Promise<string> {
  const sym = normalizeSymbol(symbol);
  const fc = new FileCache(cfg);
  const [defs, source] = await findDefinitions(cfg, sym, fc);
  const decls = await findDeclarations(cfg, sym, fc);
  const title = `### 🧩 SYMBOL CONTRACT: \`${sym}\``;
  if (!defs.length && !decls.length) return `${title}\n❌ No declaration or definition found (source: ${source}).`;
  const out = [title, `_Sources: ${source}; declarations via ctags._`];
  const entries: Array<[string, Tag]> = [
    ...decls.slice(0, 3).map((t) => ["Declaration", t] as [string, Tag]),
    ...defs.slice(0, 3).map((t) => ["Definition", t] as [string, Tag]),
  ];
  const quals: string[] = [];
  for (const [label, t] of entries) {
    const lines = fc.getLines(t.path);
    const stripped = fc.getStripped(t.path);
    if (!(t.line > 0 && t.line <= lines.length)) continue;
    const sig = FUNCTION_KINDS.has(t.kind) || t.kind === "prototype" || t.kind === "macro" ? t.displaySignature : `${t.kind} ${t.qualified}`;
    out.push(`- **${label}:** \`${loc(t)}\` — ${md.codeSpan(sig)}`);
    for (const q of qualifiers(declText(stripped, lines, t))) if (!quals.includes(q)) quals.push(q);
  }
  if (decls.length + defs.length > entries.length) {
    out.push(`- _…and ${decls.length + defs.length - entries.length} more declarations/definitions (overloads)._`);
  }
  if (quals.length) out.push("- **Qualifiers:** " + quals.map((q) => `\`${q}\``).join(", "));
  let docShown = false;
  for (const [, t] of entries) {
    const lines = fc.getLines(t.path);
    const doc = extractLeadingComment(lines, t.line - 1);
    if (!doc.length) continue;
    out.push(`\n**📜 Doc comment** (\`${t.path}:${t.line}\`):`);
    out.push(...doc.slice(0, 25).map((d) => (d ? `> ${md.clip(d, 200)}` : ">")));
    if (doc.length > 25) out.push(`> _…${doc.length - 25} more lines_`);
    const obl = obligations(doc);
    if (obl.length) {
      out.push("\n**⚖️ Obligations / preconditions:**");
      out.push(...obl.slice(0, 10).map((o) => `- ${md.clip(o, 240)}`));
    }
    docShown = true;
    break;
  }
  if (!docShown) out.push("\n_No doc comment found above the declaration/definition. Infer the contract from the body and callers._");
  const bodyDef = defs.find((t) => FUNCTION_KINDS.has(t.kind) || TYPE_KINDS.has(t.kind));
  if (bodyDef) {
    const lines = fc.getLines(bodyDef.path);
    const span = bodyDef.end - bodyDef.line + 1;
    const limit = FUNCTION_KINDS.has(bodyDef.kind) ? 25 : 40;
    if (span > 1 && span <= limit) {
      out.push(`\n**Body** (\`${loc(bodyDef)}\`):`, "```cpp", ...md.numberedCode(lines.slice(bodyDef.line - 1, bodyDef.end), bodyDef.line), "```");
    } else if (span > limit) {
      out.push(`\n_Body is ${span} lines: use \`get_branch_skeleton("${bodyDef.path}", symbol="${bodyDef.qualified}")\`._`);
    }
  }
  return out.join("\n");
}

export async function get_symbol_contract(args: { symbol: string }): Promise<string> {
  return contractReport(loadConfig(), args.symbol);
}
