// review_changes: one-call, budgeted review bundle built from the other StaticSight tools.
import { join } from "node:path";
import { type Config, isHeader, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { stripCode } from "../core/cppText.js";
import { cmpStr, FUNCTION_KINDS, tryCtagsForFiles } from "../engines/ctags.js";
import { readLines } from "../core/paths.js";
import { StaticSightError } from "../core/errors.js";
import { analyseDiff, type DiffScopes, type FileReport, renderDiffScopes, type ScopeChange } from "./diffScopes.js";
import { callersReport, FileCache, findDefinitions } from "./graphGtags.js";
import { blastRadiusReport, structRisksReport } from "./ripgrepMem.js";
import { lockOrderReport } from "./lockOrder.js";
import { stateMutationsReport } from "./stateMutation.js";
import { lineEvents } from "../core/locks.js";
import { staticAuditReport } from "./staticCpp.js";
import { branchSkeletonReport } from "./syntaxCtags.js";
import { similarForReview } from "../semantic/search.js";

const CALLEE = /\b([A-Za-z_]\w*)\s*\(/g;
const NOT_CALLEES = new Set([
  "if", "for", "while", "switch", "return", "sizeof", "alignof", "decltype", "static_cast", "reinterpret_cast",
  "const_cast", "dynamic_cast", "catch", "throw", "noexcept", "defined", "static_assert", "typeid", "alignas",
  "assert", "co_return", "co_await", "new", "delete", "operator",
]);
const SECTION_CHARS = 2200;
const DECL_BEFORE =
  /(?:^|[\s(,;{])(?!(?:return|else|throw|co_return|co_await|case|delete|new)\b)[A-Za-z_][\w:]*(?:<[^()]*>)?(?:\s+|\s*(?:\*+|&(?!&))\s*)$/;

function section(title: string, body: string, limit: number): string {
  return `## ${title}\n` + md.enforceBudget(body, limit);
}

async function safe(p: Promise<string>): Promise<string> {
  try {
    return await p;
  } catch (e) {
    if (e instanceof StaticSightError) return md.errorCard(e.title, e.message, e.hint);
    throw e;
  }
}

export async function reviewReport(cfg: Config, baseRef = "", maxSymbols = 8): Promise<string> {
  maxSymbols = Math.max(1, Math.min(Math.trunc(maxSymbols || 8), 25));
  const ds = await analyseDiff(cfg, baseRef);
  const parts: string[] = [`# 🔬 STATICSIGHT REVIEW BUNDLE vs ${ds.info.baseLabel}`];
  if (!ds.reports.length) {
    parts.push(renderDiffScopes(ds, cfg, true));
    return parts.join("\n\n");
  }
  const checklist: string[] = [];
  parts.push(section("1. What changed", renderDiffScopes(ds, cfg, true), 3500));

  const audits: string[] = [];
  for (const rep of ds.reports.slice(0, 6)) {
    if (rep.diff.status === "deleted" || isHeader(rep.diff.path)) continue;
    audits.push(md.enforceBudget(await safe(staticAuditReport(cfg, rep.diff.path, true, baseRef)), 1200));
  }
  if (audits.length) {
    const text = audits.join("\n\n");
    if (text.includes("[error:")) checklist.push("Fix the cppcheck **errors** on changed lines (✏️) first; they are the strongest evidence.");
    parts.push(section("2. Static audit (cppcheck, changed lines)", text, SECTION_CHARS * 2));
  }

  const live = ds.changedFunctions().filter(([r]) => r.diff.status !== "deleted");
  const funcs = [...live.filter(([, s]) => !s.isNew), ...live.filter(([, s]) => s.isNew)].slice(0, maxSymbols);
  const skels: string[] = [];
  const flat: string[] = [];
  for (const [rep, sc] of funcs) {
    const sk = await safe(branchSkeletonReport(cfg, rep.diff.path, "", sc.tag.line, 0, baseRef));
    if (sk.includes("✅ No control-flow branches")) {
      flat.push(`\`${sc.tag.qualified}\``);
      continue;
    }
    skels.push(md.enforceBudget(sk, 1400));
  }
  if (flat.length) skels.push("_No branches, locks or allocations in: " + flat.join(", ") + "._");
  if (skels.length) {
    const text = skels.join("\n\n");
    if (text.includes("⚠️") && text.includes("not released")) {
      checklist.push("Confirm every allocation/acquire flagged ⚠️ is released on the early-exit paths shown in the skeletons.");
    }
    parts.push(section("3. Branch skeletons of changed functions", text, SECTION_CHARS * 2));
  }

  let targets: string[] = [];
  for (const [, sc] of ds.changedFunctions()) if (!sc.isNew || sc.signatureChanged) targets.push(sc.tag.shortName);
  for (const rep of ds.reports) {
    for (const sc of rep.scopes) if (sc.kind === "prototype" && sc.signatureChanged) targets.push(sc.tag.shortName);
    for (const t of rep.removedSymbols) if (FUNCTION_KINDS.has(t.kind)) targets.push(t.shortName);
  }
  targets = [...new Set(targets)].slice(0, maxSymbols);
  const callers: string[] = [];
  for (const name of targets) callers.push(md.enforceBudget(await safe(callersReport(cfg, name)), 1000));
  if (callers.length) {
    const text = callers.join("\n\n");
    if (text.includes("result ignored")) checklist.push("Some callers ignore return values of changed functions: check new/changed error codes are handled.");
    parts.push(section("4. Caller impact", text, SECTION_CHARS));
  }

  const types = ds.changedTypes().filter(([, sc]) => sc.layout && !sc.isNew).map(([, sc]) => sc.tag.shortName);
  const risks: string[] = [];
  for (const name of [...new Set(types)].slice(0, 3)) risks.push(md.enforceBudget(await safe(structRisksReport(cfg, name)), 1500));
  if (risks.length) {
    const text = risks.join("\n\n");
    if (text.includes("may break")) {
      checklist.push(
        "Layout-changed types are copied/sent/cast as raw bytes: check wire/disk format versioning, peers built from old code, and add/update `static_assert(sizeof(...))`.",
      );
    }
    parts.push(section("5. Memory-layout risks of changed types", text, SECTION_CHARS));
  }

  const radii: string[] = [];
  for (const rep of ds.changedHeaders().slice(0, 3)) radii.push(md.enforceBudget(await safe(blastRadiusReport(cfg, rep.diff.path, 2)), 900));
  if (radii.length) {
    checklist.push("Changed headers recompile every includer listed in the blast radius: rebuild and run their tests.");
    parts.push(section("6. Header blast radius", radii.join("\n\n"), SECTION_CHARS));
  }

  const members = await touchedMembers(cfg, ds, funcs);
  const locks: string[] = [];
  for (const name of members.slice(0, 4)) {
    const t = await safe(stateMutationsReport(cfg, name));
    if (t.includes("Inconsistent locking")) locks.push(md.enforceBudget(t, 1400));
  }
  if (locks.length) {
    checklist.push("Members are accessed both with and without their mutex: confirm thread-safety or restore the lock.");
    parts.push(section("7. Lock consistency", locks.join("\n\n"), SECTION_CHARS));
  }

  // 8. lock order: only when a changed function takes a lock (the analysis scans every locking file)
  const focus = lockingFunctions(cfg, live);
  if (focus.size) {
    const text = await safe(lockOrderReport(cfg, "", "", focus));
    if (text) {
      if (text.includes("deadlock cycle") || text.includes("taken twice")) {
        checklist.push("Locks are taken in conflicting orders (or twice): fix the order before merging; this can deadlock.");
      }
      if (text.includes("blocking calls")) {
        checklist.push("A lock is held across a blocking call: shrink the critical section or document why it is safe.");
      }
      parts.push(section("8. Lock order", text, SECTION_CHARS));
    }
  }

  const callees = newCallees(cfg, ds);
  if (callees.length) {
    parts.push(
      "## 9. Calls introduced by the diff\n" +
        callees.map((c) => `\`${c}\``).join(", ") +
        "\n_Check their contracts with `get_symbol_contract` (preconditions, ownership, required pairing)._",
    );
  }
  // 10. near-duplicates elsewhere (semantic index, if built): the same bug/fix may apply there too
  const simTargets: Array<[string, number, string]> = funcs.filter(([, sc]) => !sc.isNew).slice(0, 3).map(([r, sc]) => [r.diff.path, sc.tag.line, sc.tag.qualified]);
  const similar = simTargets.length ? await similarForReview(cfg, simTargets) : [];
  if (similar.length) {
    checklist.push("Near-duplicate code exists elsewhere (section 10): check whether the same change is needed there.");
    parts.push("## 10. Similar code elsewhere (semantic index)\n" + similar.join("\n"));
  }

  checklist.push(
    "Re-read each changed function's skeleton for missing error handling on new branches.",
    "For signature/return-value changes, confirm every caller in section 4 still satisfies the new contract.",
  );
  parts.push("## ✅ Reviewer checklist\n" + [...new Set(checklist)].map((c) => `- [ ] ${c}`).join("\n"));
  return md.enforceBudget(parts.join("\n\n"), cfg.reviewMaxChars);
}

/** Changed functions whose body takes a lock, as "path\0qualified". */
function lockingFunctions(cfg: Config, live: Array<[FileReport, ScopeChange]>): Set<string> {
  const out = new Set<string>();
  const cache = new Map<string, string[]>();
  for (const [rep, sc] of live) {
    const path = rep.diff.path;
    if (!cache.has(path)) {
      try {
        cache.set(path, stripCode(readLines(join(cfg.workspaceRoot, path))));
      } catch (e) {
        if (!(e instanceof StaticSightError)) throw e;
        cache.set(path, []);
      }
    }
    const lines = cache.get(path)!;
    for (let n = sc.tag.line; n <= Math.min(sc.tag.end, lines.length); n++) {
      if (lineEvents(lines[n - 1]).length) {
        out.add(`${path}\0${sc.tag.qualified}`);
        break;
      }
    }
  }
  return out;
}

async function touchedMembers(cfg: Config, ds: DiffScopes, funcs: Array<[FileReport, ScopeChange]>): Promise<string[]> {
  const classes = [...new Set(funcs.map(([, sc]) => sc.tag.scope).filter(Boolean))].sort(cmpStr);
  if (!classes.length) return [];
  const fc = new FileCache(cfg);
  const memberNames = new Map<string, string>();
  const files: string[] = ds.reports.filter((r) => r.diff.status !== "deleted").map((r) => r.diff.path);
  for (const cls of classes) {
    const [defs] = await findDefinitions(cfg, cls.split("::").pop()!, fc);
    files.push(...defs.map((d) => d.path));
  }
  const tags = await tryCtagsForFiles(cfg, [...new Set(files)]);
  const shortClasses = new Set(classes.map((c) => c.split("::").pop()!));
  for (const ts of tags.values()) for (const t of ts) if (t.kind === "member" && shortClasses.has(t.scope.split("::").pop()!)) memberNames.set(t.shortName, t.scope);
  if (!memberNames.size) return [];
  const ranked = new Map<string, number>();
  for (const [rep, sc] of funcs) {
    let lines: string[];
    try {
      lines = stripCode(readLines(join(cfg.workspaceRoot, rep.diff.path)));
    } catch {
      continue;
    }
    const touched = rep.diff.touchedLines;
    for (let n = sc.tag.line; n <= Math.min(sc.tag.end, lines.length); n++) {
      const weight = touched.has(n) ? 3 : 1;
      for (const ident of lines[n - 1].match(/\b[A-Za-z_]\w*\b/g) ?? []) {
        if (memberNames.has(ident)) ranked.set(ident, (ranked.get(ident) ?? 0) + weight);
      }
    }
  }
  return [...ranked.entries()].sort((a, b) => b[1] - a[1] || cmpStr(a[0], b[0])).map(([k]) => k);
}

function newCallees(cfg: Config, ds: DiffScopes): string[] {
  const seen: string[] = [];
  const own = new Set(ds.reports.flatMap((r) => r.scopes.map((sc) => sc.tag.shortName)));
  for (const rep of ds.reports) {
    if (rep.diff.status === "deleted") continue;
    let lines: string[];
    try {
      lines = stripCode(readLines(join(cfg.workspaceRoot, rep.diff.path)));
    } catch {
      continue;
    }
    for (const n of [...rep.diff.addedLines].sort((a, b) => a - b)) {
      if (!(n > 0 && n <= lines.length) || /^\s*#/.test(lines[n - 1])) continue;
      const code = lines[n - 1];
      for (const m of code.matchAll(CALLEE)) {
        const name = m[1];
        const rawBefore = code.slice(0, m.index);
        const before = rawBefore.replace(/\s+$/u, "");
        if (NOT_CALLEES.has(name) || own.has(name) || /^[A-Z][A-Z0-9_]*$/.test(name)) continue;
        if (DECL_BEFORE.test(rawBefore) || before.endsWith("operator") || /(?<!:):$/.test(before)) continue;
        if (!seen.includes(name)) seen.push(name);
      }
    }
  }
  return seen.slice(0, 10);
}

export async function review_changes(args: { base_ref?: string; max_symbols?: number }): Promise<string> {
  return reviewReport(loadConfig(), args.base_ref ?? "", args.max_symbols ?? 8);
}
