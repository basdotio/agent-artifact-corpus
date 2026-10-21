// cppcheck adapter: builds the command, runs it via the platform layer, parses the XML report.
import { statSync } from "node:fs";
import { dirname, join, relative, sep } from "node:path";
import type { Config } from "../config.js";
import { ToolFailed } from "../core/errors.js";
import { runEngine, toPosix } from "./base.js";

export const SEVERITY_ORDER: Record<string, number> = { error: 0, warning: 1, portability: 2, performance: 3, style: 4, information: 5 };
const NOISE_IDS = new Set([
  "missingInclude", "missingIncludeSystem", "checkersReport", "normalCheckLevelMaxBranches", "toomanyconfigs",
  "unmatchedSuppression", "noValidConfiguration", "unknownMacro", "syntaxError", "internalAstError", "preprocessorErrorDirective",
]);
const PARSE_PROBLEM_IDS = new Set(["syntaxError", "unknownMacro", "internalAstError", "preprocessorErrorDirective", "noValidConfiguration"]);

export interface Finding {
  id: string;
  severity: string;
  msg: string;
  cwe: string;
  line: number;
  locations: Array<[string, number, string]>;
}

function isDir(p: string): boolean {
  try {
    return statSync(p).isDirectory();
  } catch {
    return false;
  }
}

export function includeDirs(cfg: Config, absFile: string): string[] {
  const root = cfg.workspaceRoot;
  const dirs: string[] = [];
  let cur = dirname(absFile);
  for (;;) {
    dirs.push(cur);
    for (const sub of ["include", "inc"]) if (isDir(join(cur, sub))) dirs.push(join(cur, sub));
    const rel = relative(root, cur);
    if (cur === root || rel.startsWith("..") || rel === "") break;
    cur = dirname(cur);
  }
  for (const sub of ["include", "src", "inc"]) if (isDir(join(root, sub))) dirs.push(join(root, sub));
  const uniq = [...new Set(dirs)];
  return uniq.map((d) => (d === root ? "." : relative(root, d).split(sep).join("/"))).slice(0, 12);
}

function decodeEntities(s: string): string {
  return s.replace(/&(#x[0-9a-fA-F]+|#\d+|amp|lt|gt|quot|apos);/g, (_, e: string) => {
    if (e === "amp") return "&";
    if (e === "lt") return "<";
    if (e === "gt") return ">";
    if (e === "quot") return '"';
    if (e === "apos") return "'";
    if (e.startsWith("#x")) return String.fromCodePoint(parseInt(e.slice(2), 16));
    return String.fromCodePoint(parseInt(e.slice(1), 10));
  });
}

function attrs(tag: string): Record<string, string> {
  const out: Record<string, string> = {};
  const rx = /([\w:-]+)\s*=\s*("([^"]*)"|'([^']*)')/g;
  let m: RegExpExecArray | null;
  while ((m = rx.exec(tag)) !== null) out[m[1]] = decodeEntities(m[3] ?? m[4] ?? "");
  return out;
}

export function parseCppcheckXml(xmlText: string, rel: string): [Finding[], number, string, boolean, string[]] {
  let start = xmlText.indexOf("<?xml");
  if (start < 0) start = xmlText.indexOf("<results");
  if (start < 0) throw new ToolFailed("cppcheck produced no XML output.");
  const xml = xmlText.slice(start);
  if (!/<results[\s>]/.test(xml) || !xml.includes("</results>")) throw new ToolFailed("Could not parse cppcheck XML: unterminated document");
  const ver = /<cppcheck\b([^>]*)\/?>/.exec(xml);
  const version = ver ? attrs(ver[1]).version ?? "" : "";
  const findings: Finding[] = [];
  let elsewhere = 0;
  let parseProblem = false;
  const macros: string[] = [];
  const errRx = /<error\b([^>]*?)(\/>|>([\s\S]*?)<\/error>)/g;
  let m: RegExpExecArray | null;
  while ((m = errRx.exec(xml)) !== null) {
    const a = attrs(m[1]);
    const eid = a.id ?? "";
    if (PARSE_PROBLEM_IDS.has(eid)) {
      parseProblem = true;
      const mm = /If (\w+) is a macro/.exec(a.msg ?? "");
      if (mm && !macros.includes(mm[1])) macros.push(mm[1]);
    }
    if (NOISE_IDS.has(eid)) continue;
    const body = m[3] ?? "";
    const locs: Array<[string, number, string]> = [];
    const locRx = /<location\b([^>]*?)\/?>/g;
    let lm: RegExpExecArray | null;
    while ((lm = locRx.exec(body)) !== null) {
      const la = attrs(lm[1]);
      locs.push([toPosix(la.file ?? ""), parseInt(la.line ?? "0", 10) || 0, la.info ?? ""]);
    }
    const own = locs.filter((l) => l[0] === rel);
    if (!own.length) {
      elsewhere++;
      continue;
    }
    findings.push({ id: eid, severity: a.severity ?? "information", msg: a.msg ?? "", cwe: a.cwe ?? "", line: own[0][1], locations: own });
  }
  const uniq = new Map<string, Finding>();
  for (const f of findings) {
    const k = `${f.line}\u0000${f.id}\u0000${f.msg}`;
    if (!uniq.has(k)) uniq.set(k, f);
  }
  const ordered = [...uniq.values()].sort(
    (x, y) => (SEVERITY_ORDER[x.severity] ?? 9) - (SEVERITY_ORDER[y.severity] ?? 9) || x.line - y.line || (x.id < y.id ? -1 : x.id > y.id ? 1 : 0),
  );
  return [ordered, elsewhere, version, parseProblem, macros];
}

const WIN_INCLUDE = /^\s*#\s*include\s*[<"](?:windows|winbase|windef|wtypes|winerror|atlbase|objbase|winsock2|ntddk|wdm|ntifs)\.h[">]/im;
const SAL = /\b(?:_In_|_Out_|_Inout_|_In_opt_|_Out_opt_|_Inout_opt_|_In_reads_\w*|_Out_writes_\w*|__in|__out|__inout|__in_opt|__out_opt)\b/;
const WIN_TYPES = /\b(?:HRESULT|DWORD|HANDLE|LPCWSTR|LPWSTR|LPCSTR|BOOL|WINAPI|__stdcall|HKEY|SC_HANDLE)\b/g;
export const MSVC_ARGS = ["--library=windows", "--platform=win64", "-D_WIN32", "-D_MSC_VER=1930"];

/** Heuristic: does this file target Windows/MSVC? (STATICSIGHT_CPPCHECK_MSVC=0 disables, =1 forces.) */
export function wantsMsvc(sourceText: string): boolean {
  const mode = (process.env.STATICSIGHT_CPPCHECK_MSVC ?? "auto").trim().toLowerCase();
  if (["0", "false", "no", "off"].includes(mode)) return false;
  if (["1", "true", "yes", "on"].includes(mode)) return true;
  if (WIN_INCLUDE.test(sourceText) || SAL.test(sourceText)) return true;
  return new Set(sourceText.match(WIN_TYPES) ?? []).size >= 2;
}

export function baseArgs(rel: string): string[] {
  const lang = rel.toLowerCase().endsWith(".c") ? "c" : "c++";
  return [
    "--xml", "--xml-version=2", "--enable=warning,style,performance,portability", "--inline-suppr",
    `--language=${lang}`, lang === "c" ? "--std=c11" : "--std=c++17", "--quiet", "--max-configs=4",
    "--suppress=missingIncludeSystem", "--suppress=missingInclude", "--suppress=unmatchedSuppression", "--suppress=checkersReport",
    ...(process.env.STATICSIGHT_CPPCHECK_ARGS ?? "").split(/\s+/).filter(Boolean),
  ];
}

export async function runCppcheck(cfg: Config, rel: string, absPath: string, include: boolean, extra: string[] = []): Promise<[Finding[], number, string, boolean, string[]]> {
  const args = [...baseArgs(rel), ...extra, ...(include ? includeDirs(cfg, absPath).map((d) => `-I${d}`) : [])];
  args.push(rel.startsWith("-") ? "./" + rel : rel);
  const res = await runEngine("cppcheck", args, { cwd: cfg.workspaceRoot, timeout: cfg.cppcheckTimeoutS });
  if (!res.stderr.includes("<results")) {
    throw new ToolFailed(`cppcheck failed (exit ${res.returncode}): ${(res.stderr || res.stdout).trim().slice(0, 300)}`);
  }
  return parseCppcheckXml(res.stderr, rel);
}
