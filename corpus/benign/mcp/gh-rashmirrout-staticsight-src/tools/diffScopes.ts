// get_diff_scopes: map the current git diff to C++ scopes, detect signature/layout/header/macro changes.
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { extname, join } from "node:path";
import { type Config, isCppFile, isHeader, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { BLOCK_KINDS, cmpStr, ctagsForFiles, ctagsForTemp, FUNCTION_KINDS, innermost, type Tag, TYPE_KINDS } from "../engines/ctags.js";
import { collectDiff, type DiffInfo, type FileDiff, showBlob } from "../engines/git.js";
import { matchesGlob, readLines } from "../core/paths.js";
import { StaticSightError } from "../core/errors.js";

const DEFINE = /^\s*#\s*define\s+(\w+)/;
const SCOPE_KINDS = new Set([...BLOCK_KINDS].filter((k) => k !== "namespace"));

export class ScopeChange {
  lines = new Set<number>();
  removed = 0;
  isNew = false;
  signatureChanged = "";
  layout = false;
  constructor(public tag: Tag) {}
  get kind(): string {
    return this.tag.kind;
  }
}

export class FileReport {
  scopes: ScopeChange[] = [];
  fileLevel = new Set<number>();
  macros: string[] = [];
  removedSymbols: Tag[] = [];
  includeChanges = false;
  constructor(public diff: FileDiff) {}
}

export class DiffScopes {
  constructor(public info: DiffInfo, public reports: FileReport[], public otherFiles: FileDiff[]) {}
  changedFunctions(): Array<[FileReport, ScopeChange]> {
    const out: Array<[FileReport, ScopeChange]> = [];
    for (const r of this.reports) for (const s of r.scopes) if (FUNCTION_KINDS.has(s.kind)) out.push([r, s]);
    return out;
  }
  changedTypes(): Array<[FileReport, ScopeChange]> {
    const out: Array<[FileReport, ScopeChange]> = [];
    for (const r of this.reports) for (const s of r.scopes) if (TYPE_KINDS.has(s.kind)) out.push([r, s]);
    return out;
  }
  changedHeaders(): FileReport[] {
    return this.reports.filter((r) => isHeader(r.diff.path));
  }
}

function sigKey(t: Tag): string {
  return `${t.returnType} ${t.signature}`.trim().replace(/\s+/g, " ");
}

async function oldTags(cfg: Config, sha: string, fd: FileDiff): Promise<Tag[] | null> {
  const blob = await showBlob(cfg, sha, fd.oldPath);
  if (blob === null) return null;
  const suffix = extname(fd.oldPath) || ".cpp";
  const dir = mkdtempSync(join(tmpdir(), "staticsight-"));
  try {
    const p = join(dir, `old${suffix}`);
    writeFileSync(p, blob, "utf8");
    return await ctagsForTemp(cfg, p, fd.oldPath);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function rangeSet(a: number, b: number): Set<number> {
  const s = new Set<number>();
  for (let k = a; k <= b; k++) s.add(k);
  return s;
}

function intersect(a: Set<number>, b: Set<number>): Set<number> {
  return new Set([...a].filter((x) => b.has(x)));
}

export async function analyseDiff(cfg: Config, baseRef = "", pathGlob = ""): Promise<DiffScopes> {
  const info = await collectDiff(cfg, baseRef);
  const cppFiles = info.files.filter((f) => isCppFile(f.path) && !f.binary && matchesGlob(f.path, pathGlob));
  const other = info.files.filter((f) => !cppFiles.includes(f) && matchesGlob(f.path, pathGlob));
  const live = cppFiles.filter((f) => f.status !== "deleted").map((f) => f.path);
  const tagsByFile = live.length ? await ctagsForFiles(cfg, live) : new Map<string, Tag[]>();
  const reports: FileReport[] = [];
  for (const fd of cppFiles) {
    const rep = new FileReport(fd);
    reports.push(rep);
    let old: Tag[] | null = null;
    if (["modified", "renamed", "deleted"].includes(fd.status)) {
      try {
        old = await oldTags(cfg, info.baseSha, fd);
      } catch (e) {
        if (!(e instanceof StaticSightError)) throw e;
        old = null;
      }
    }
    if (fd.status === "deleted") {
      rep.removedSymbols = (old ?? []).filter((t) => SCOPE_KINDS.has(t.kind) && !t.scope).sort((a, b) => a.line - b.line);
      continue;
    }
    const tags = tagsByFile.get(fd.path) ?? [];
    let lines: string[] = [];
    try {
      lines = readLines(join(cfg.workspaceRoot, fd.path));
    } catch {
      lines = [];
    }
    const byKey = new Map<string, ScopeChange>();
    const touched = [...fd.touchedLines].sort((a, b) => a - b);
    for (const ln of touched) {
      const probe = Math.min(Math.max(ln, 1), Math.max(lines.length, 1));
      const tag = innermost(tags, probe, SCOPE_KINDS);
      const text = probe > 0 && probe <= lines.length ? lines[probe - 1] : "";
      const dm = fd.addedLines.has(ln) ? DEFINE.exec(text) : null;
      if (dm && !rep.macros.includes(dm[1])) rep.macros.push(dm[1]);
      if (fd.addedLines.has(ln) && /^\s*#\s*include\b/.test(text)) rep.includeChanges = true;
      if (tag === null) {
        if (fd.addedLines.has(ln) && text.trim()) rep.fileLevel.add(ln);
        continue;
      }
      const key = `${tag.line}\u0000${tag.kind}\u0000${tag.qualified}`;
      let sc = byKey.get(key);
      if (!sc) {
        sc = new ScopeChange(tag);
        byKey.set(key, sc);
      }
      if (fd.addedLines.has(ln)) sc.lines.add(ln);
      sc.removed += fd.removedAt.get(ln) ?? 0;
    }
    const memberLines = new Set(tags.filter((t) => t.kind === "member" || t.kind === "enumerator").map((t) => t.line));
    for (const sc of byKey.values()) {
      const span = rangeSet(sc.tag.line, sc.tag.end);
      sc.isNew = fd.status === "added" || fd.status === "untracked" || [...span].every((x) => fd.addedLines.has(x));
      if (TYPE_KINDS.has(sc.kind)) {
        const t2 = intersect(fd.touchedLines, span);
        sc.layout = [...t2].some(
          (ln) => memberLines.has(ln) || !fd.addedLines.has(ln) || (ln > 0 && ln <= lines.length && /\bvirtual\b/.test(lines[ln - 1])),
        );
      }
    }
    if (old !== null) {
      const oldByName = new Map<string, Tag[]>();
      for (const t of old) {
        if (SCOPE_KINDS.has(t.kind) || t.kind === "prototype") {
          if (!oldByName.has(t.qualified)) oldByName.set(t.qualified, []);
          oldByName.get(t.qualified)!.push(t);
        }
      }
      const newNames = new Set(tags.map((t) => t.qualified));
      for (const sc of byKey.values()) {
        const olds = oldByName.get(sc.tag.qualified);
        if (!olds || !olds.length) continue;
        sc.isNew = false;
        if (["function", "prototype", "macro"].includes(sc.kind)) {
          const oldSigs = new Set(olds.filter((o) => o.kind === sc.kind).map(sigKey));
          const newSig = sigKey(sc.tag);
          if (oldSigs.size && !oldSigs.has(newSig)) sc.signatureChanged = `${[...oldSigs].sort(cmpStr)[0]} -> ${newSig}`;
        }
      }
      const removed: Tag[] = [];
      for (const [name, ts] of oldByName) if (!newNames.has(name)) for (const t of ts) if (SCOPE_KINDS.has(t.kind)) removed.push(t);
      rep.removedSymbols = removed.sort((a, b) => a.line - b.line || cmpStr(a.qualified, b.qualified));
      for (const t of tags) {
        const touchedT = intersect(fd.touchedLines, rangeSet(t.line, t.end));
        if (t.kind !== "prototype" || !touchedT.size) continue;
        const oldSigs = new Set((oldByName.get(t.qualified) ?? []).filter((o) => o.kind === "prototype").map(sigKey));
        const key = `${t.line}\u0000${t.kind}\u0000${t.qualified}`;
        if (!oldSigs.size) {
          const sc = new ScopeChange(t);
          sc.lines = intersect(touchedT, fd.addedLines);
          sc.isNew = true;
          byKey.set(key, sc);
        } else if (!oldSigs.has(sigKey(t))) {
          const sc = new ScopeChange(t);
          sc.lines = intersect(touchedT, fd.addedLines);
          sc.signatureChanged = `${[...oldSigs].sort(cmpStr)[0]} -> ${sigKey(t)}`;
          byKey.set(key, sc);
        }
      }
    }
    rep.scopes = [...byKey.values()].sort((a, b) => a.tag.line - b.tag.line || cmpStr(a.tag.qualified, b.tag.qualified));
  }
  return new DiffScopes(info, reports, other);
}

function statusLabel(fd: FileDiff): string {
  if (fd.status === "renamed") return `renamed from \`${fd.oldPath}\``;
  return fd.status === "untracked" ? "new, untracked" : fd.status;
}

function scopeLine(sc: ScopeChange): string {
  const t = sc.tag;
  const rng = t.line === t.end ? `L${t.line}` : `L${t.line}-${t.end}`;
  const parts = [`\`${t.qualified}\` (${t.kind}, ${rng})`];
  if (sc.isNew) parts.push("🆕 new");
  else {
    const detail = sc.lines.size ? md.compressRanges(sc.lines) : "";
    if (detail) parts.push(`changed ${detail}`);
    if (sc.removed) parts.push(`${sc.removed} line(s) removed`);
  }
  if (sc.signatureChanged) {
    const idx = sc.signatureChanged.indexOf(" -> ");
    parts.push(`🔁 signature \`${sc.signatureChanged.slice(0, idx)}\` → \`${sc.signatureChanged.slice(idx + 4)}\``);
  }
  if (TYPE_KINDS.has(t.kind) && !sc.isNew) {
    parts.push(sc.layout ? "🧱 layout change (data members/virtuals)" : "declarations changed (no data-member change detected)");
  }
  return "- " + parts.join(" — ");
}

function newFileLine(rep: FileReport, limit: number): string {
  const fns = rep.scopes.filter((sc) => FUNCTION_KINDS.has(sc.kind));
  const types = rep.scopes.filter((sc) => TYPE_KINDS.has(sc.kind));
  const macros = rep.scopes.filter((sc) => sc.kind === "macro");
  let line = `- 🆕 new file: ${md.plural(fns.length, "function")}, ${md.plural(types.length, "type")}, ${md.plural(macros.length, "macro")}`;
  const names = [...fns, ...types].map((sc) => `\`${sc.tag.qualified}\``).slice(0, Math.min(limit, 8));
  if (names.length) {
    const extra = fns.length + types.length - names.length;
    line += ": " + names.join(", ") + (extra > 0 ? `, … (+${extra} more)` : "");
  }
  return line;
}

export function suggestions(ds: DiffScopes, limit: number): string[] {
  const out: string[] = [];
  for (const [rep, sc] of ds.changedFunctions()) {
    if (sc.isNew && !sc.signatureChanged) continue;
    out.push(`\`get_branch_skeleton("${rep.diff.path}", symbol="${sc.tag.qualified}")\``);
    out.push(`\`get_upstream_callers("${sc.tag.shortName}")\``);
  }
  for (const rep of ds.reports)
    for (const sc of rep.scopes)
      if (sc.kind === "prototype" && (sc.signatureChanged || sc.isNew)) out.push(`\`get_upstream_callers("${sc.tag.shortName}")\` — declaration changed`);
  for (const [, sc] of ds.changedTypes()) if (sc.layout && !sc.isNew) out.push(`\`track_struct_risks("${sc.tag.shortName}")\``);
  for (const rep of ds.reports) {
    if (isHeader(rep.diff.path)) out.push(`\`get_include_blast_radius("${rep.diff.path}")\``);
    else if (rep.diff.status !== "deleted") out.push(`\`run_file_static_audit("${rep.diff.path}", only_changed_lines=true)\``);
    for (const t of rep.removedSymbols)
      if (FUNCTION_KINDS.has(t.kind)) out.push(`\`get_upstream_callers("${t.shortName}")\` — removed, check for dangling callers`);
  }
  for (const [rep, sc] of ds.changedFunctions()) {
    if (sc.isNew && !sc.signatureChanged) out.push(`\`get_branch_skeleton("${rep.diff.path}", symbol="${sc.tag.qualified}")\` — audit the new function`);
  }
  return md.truncateList([...new Set(out)], limit, "suggestions");
}

export function renderDiffScopes(ds: DiffScopes, cfg: Config, compact = false): string {
  const info = ds.info;
  const adds = ds.reports.reduce((a, r) => a + r.diff.additions, 0);
  const dels = ds.reports.reduce((a, r) => a + r.diff.deletions, 0);
  const out = [`### 🧭 DIFF SCOPES vs ${info.baseLabel}`];
  if (!ds.reports.length && !ds.otherFiles.length) {
    out.push("✅ No changes found (committed, staged, unstaged or untracked) relative to the base.");
    return out.join("\n");
  }
  out.push(
    `${md.plural(ds.reports.length, "C/C++ file")} changed (+${adds} / -${dels})` +
      (ds.otherFiles.length ? `; ${md.plural(ds.otherFiles.length, "other file")} ignored` : "") +
      ".",
  );
  const limit = cfg.maxResults;
  const counts = new Map<string, number>();
  for (const rep of ds.reports) counts.set(rep.diff.status, (counts.get(rep.diff.status) ?? 0) + 1);
  if (ds.reports.length > 1) {
    out.push("By status: " + [...counts.entries()].sort((a, b) => cmpStr(a[0], b[0])).map(([s, n]) => `${n} ${s}`).join(", ") + ".");
  }
  if (ds.reports.length > 20) out.push("_Large diff: new files are summarised; use `path_glob` to focus on one area._");
  for (const rep of ds.reports) {
    const fd = rep.diff;
    const kind = isHeader(fd.path) ? "header" : "source";
    out.push("");
    out.push(`#### \`${fd.path}\` (${kind}, ${statusLabel(fd)}, +${fd.additions} -${fd.deletions})`);
    if (fd.status === "deleted") {
      if (rep.removedSymbols.length) {
        out.push(`- 🗑️ file deleted; top-level symbols removed: ${rep.removedSymbols.slice(0, limit).map((t) => `\`${t.qualified}\``).join(", ")}`);
      } else out.push("- 🗑️ file deleted");
      continue;
    }
    if (fd.status === "added" || fd.status === "untracked") {
      out.push(newFileLine(rep, limit));
      continue;
    }
    out.push(...md.truncateList(rep.scopes.map(scopeLine), limit, "changed scopes", "Use path_glob to focus on one file."));
    if (rep.fileLevel.size) out.push(`- file-level lines (outside any function/type): ${md.compressRanges(rep.fileLevel, 12)}`);
    if (rep.macros.length) out.push("- 🔣 macros defined/changed: " + rep.macros.slice(0, limit).map((m) => `\`${m}\``).join(", "));
    if (rep.includeChanges) out.push("- 📎 #include lines changed");
    if (rep.removedSymbols.length) {
      out.push("- 🗑️ removed: " + rep.removedSymbols.slice(0, limit).map((t) => `\`${t.qualified}\` (${t.kind})`).join(", "));
    }
  }
  if (!compact) {
    const sugg = suggestions(ds, limit);
    if (sugg.length) out.push("", "#### 🔎 Suggested next calls", ...sugg.map((s) => (s.startsWith("_") ? s : `- ${s}`)));
  }
  return out.join("\n");
}

export async function get_diff_scopes(args: { base_ref?: string; path_glob?: string }): Promise<string> {
  const cfg = loadConfig();
  const ds = await analyseDiff(cfg, args.base_ref ?? "", args.path_glob ?? "");
  return renderDiffScopes(ds, cfg);
}
