// run_file_static_audit: cppcheck on a single uncompiled file, XML parsed, findings mapped onto the diff.
import { type Config, isCppFile, loadConfig } from "../config.js";
import { InvalidArgument } from "../core/errors.js";
import * as md from "../core/md.js";
import { readLines, resolveInWorkspace } from "../core/paths.js";
import { type Finding, MSVC_ARGS, parseCppcheckXml, runCppcheck, SEVERITY_ORDER, wantsMsvc } from "../engines/cppcheck.js";
import { FUNCTION_KINDS, innermost, type Tag, tryCtagsForFiles } from "../engines/ctags.js";
import { changedLines, collectDiff, diffGet } from "../engines/git.js";

export { parseCppcheckXml };
export type { Finding };

export async function staticAuditReport(cfg: Config, filePath: string, onlyChangedLines = false, baseRef = ""): Promise<string> {
  const [abs, rel] = resolveInWorkspace(cfg.workspaceRoot, filePath);
  if (!isCppFile(rel)) throw new InvalidArgument(`\`${rel}\` is not a C/C++ file.`);
  const lines = readLines(abs);
  const msvc = wantsMsvc(lines.join("\n"));
  const run = (include: boolean) => runCppcheck(cfg, rel, abs, include, msvc ? MSVC_ARGS : []);
  let [findings, elsewhere, version, parseProblem, macros] = await run(true);
  let retried = false;
  if (parseProblem) {
    const [f2, e2, v2, p2, m2] = await run(false);
    if (!p2 || f2.length > findings.length) {
      [findings, elsewhere, version, parseProblem, retried] = [f2, e2, v2, p2, true];
      macros = [...macros, ...m2.filter((m) => !macros.includes(m))];
    }
  }
  let changed: Set<number>;
  if (baseRef) {
    const info = await collectDiff(cfg, baseRef, true, rel);
    const fd = diffGet(info, rel);
    changed = fd ? fd.touchedLines : new Set();
  } else changed = await changedLines(cfg, rel);
  const tags: Tag[] = (await tryCtagsForFiles(cfg, [rel])).get(rel) ?? [];
  const changedFns = new Set<string>();
  for (const ln of changed) {
    const fn = innermost(tags, ln, FUNCTION_KINDS);
    if (fn) changedFns.add(fn.key);
  }
  const where = (f: Finding): string => {
    if (f.locations.some((l) => changed.has(l[1]))) return "diff";
    const fn = innermost(tags, f.line, FUNCTION_KINDS);
    if (fn && changedFns.has(fn.key)) return "fn";
    return "";
  };
  const title = `### 🚨 STATIC AUDIT: \`${rel}\`` + (version ? ` (cppcheck ${version})` : "");
  const total = findings.length;
  if (onlyChangedLines) findings = findings.filter((f) => where(f));
  const out = [title];
  if (!findings.length) {
    const scope = onlyChangedLines ? " on changed lines/functions" : "";
    const extra = onlyChangedLines && total ? ` (${total} elsewhere in the file)` : "";
    out.push(`✅ No cppcheck findings${scope}${extra}.`);
  } else {
    const counts = new Map<string, number>();
    for (const f of findings) counts.set(f.severity, (counts.get(f.severity) ?? 0) + 1);
    const sev = [...counts.entries()]
      .sort((a, b) => (SEVERITY_ORDER[a[0]] ?? 9) - (SEVERITY_ORDER[b[0]] ?? 9))
      .map(([s, n]) => `${n} ${s}`)
      .join(", ");
    const inDiff = findings.filter((f) => where(f) === "diff").length;
    let summary = `${md.plural(findings.length, "finding")} (${sev}); ${inDiff} on changed lines.`;
    if (onlyChangedLines && total > findings.length) summary += ` ${total - findings.length} more outside the change (rerun with only_changed_lines=false).`;
    out.push(summary);
    const items = findings.map((f, i) => {
      const w = where(f);
      const mark = w === "diff" ? "✏️ " : w === "fn" ? "🔶 " : "";
      const cwe = f.cwe && f.cwe !== "0" ? ` (CWE-${f.cwe})` : "";
      const entry = [`${i + 1}. ${mark}**L${f.line}** \`[${f.severity}: ${f.id}]\` ${f.msg}${cwe}`];
      if (f.line > 0 && f.line <= lines.length) entry.push(`   ${md.codeSpan(lines[f.line - 1])}`);
      const extra = f.locations.slice(1).filter((l) => l[1] !== f.line);
      if (extra.length) entry.push("   ↳ " + extra.slice(0, 4).map(([, ln, info]) => `L${ln}` + (info ? `: ${md.clip(info, 80)}` : "")).join("; "));
      return entry.join("\n");
    });
    out.push(...md.truncateList(items, cfg.maxResults, "findings"));
  }
  const notes: string[] = [];
  if (msvc) notes.push("MSVC mode: Windows/SAL code detected, cppcheck ran with `--library=windows --platform=win64`");
  if (elsewhere) notes.push(`${elsewhere} finding(s) located in included headers were omitted`);
  const macroTxt = macros.length ? ` (unknown macro ${macros.slice(0, 3).map((m) => `\`${m}\``).join(", ")})` : "";
  if (retried) notes.push(`re-ran without include paths because included headers could not be parsed${macroTxt}`);
  if (parseProblem) notes.push(`cppcheck could not fully parse this file${macroTxt}, so coverage is partial; pass defines via STATICSIGHT_CPPCHECK_ARGS`);
  notes.push("zero-compile mode: includes are best-effort and missing-include diagnostics are suppressed");
  out.push("\n_" + notes.join("; ") + ". ✏️ = on a changed line, 🔶 = inside a changed function._");
  return out.join("\n");
}

export async function run_file_static_audit(args: { file_path: string; only_changed_lines?: boolean; base_ref?: string }): Promise<string> {
  return staticAuditReport(loadConfig(), args.file_path, args.only_changed_lines ?? false, args.base_ref ?? "");
}

