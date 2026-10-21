// track_state_mutations: classify reads/writes of a variable and check lock/atomic protection per access.
import { join } from "node:path";
import { type Config, isCppFile, loadConfig } from "../config.js";
import * as md from "../core/md.js";
import { stripCode } from "../core/cppText.js";
import { LockWalker, lineEvents } from "../core/locks.js";
import { FUNCTION_KINDS, innermost, type Tag, tryCtagsForFiles } from "../engines/ctags.js";
import { readLines, resolveInWorkspace } from "../core/paths.js";
import { rgSearch } from "../engines/rg.js";
import { InvalidArgument } from "../core/errors.js";
import { normalizeSymbol } from "./graphGtags.js";

const LOCK_DECL = /\b(lock_guard|unique_lock|scoped_lock|shared_lock)\b/;
const ATOMIC_DECL = /\bstd::atomic\b|\batomic\s*<|\b_Atomic\b|\batomic_\w+\b/;
const MUTATING_METHODS =
  "push_back|push_front|emplace\\w*|insert\\w*|erase|clear|reset|swap|assign|resize|pop_\\w+|push|store|exchange|" +
  "fetch_\\w+|compare_exchange\\w*|append|set\\w*|add\\w*|remove\\w*|update\\w*";

export function accessKind(code: string, sym: string): string {
  const s = md.escapeRegex(sym);
  if (
    new RegExp(`\\b${s}\\s*(?:\\[[^\\]]*\\]\\s*)*(?:=(?!=)|\\+=|-=|\\*=|/=|%=|&=|\\|=|\\^=|<<=|>>=|\\+\\+|--)`).test(code) ||
    new RegExp(`(?:\\+\\+|--)\\s*(?:[\\w\\])]+\\s*(?:\\.|->)\\s*)*${s}\\b`).test(code)
  ) {
    return "write";
  }
  if (new RegExp(`\\b${s}\\s*(?:\\.|->)\\s*(?:${MUTATING_METHODS})\\s*\\(`).test(code)) return "mutating call";
  if (new RegExp(`&\\s*${s}\\b(?!\\s*\\()`).test(code) && !new RegExp(`&&\\s*${s}\\b`).test(code)) return "address taken";
  return "read";
}

function activeLocks(stripped: string[], fn: Tag, line: number): Array<[string, number]> {
  // Locks alive at `line` inside fn, honouring block scope for RAII guards and explicit unlocks.
  const walker = new LockWalker();
  for (let n = fn.line; n < line; n++) walker.step(stripped[n - 1], n);
  return walker.held.map((h) => [h.kind, h.line]);
}

function isCtorDtor(fn: Tag): boolean {
  const short = fn.shortName;
  const cls = fn.scope ? fn.scope.split("::").pop()! : "";
  return short.startsWith("~") || (!!cls && short === cls);
}

function cell(text: string): string {
  return md.clip(text.trim(), 70).replace(/\|/g, "\\|").replace(/`/g, "'");
}

interface Row {
  path: string;
  line: number;
  fn: string;
  access: string;
  sync: string;
  text: string;
}

export async function stateMutationsReport(cfg: Config, symbol: string, filePath = ""): Promise<string> {
  const sym = normalizeSymbol(symbol);
  const paths: string[] = [];
  if (filePath && filePath.trim()) {
    const [, rel] = resolveInWorkspace(cfg.workspaceRoot, filePath);
    if (!isCppFile(rel)) throw new InvalidArgument(`\`${rel}\` is not a C/C++ file.`);
    paths.push(rel);
  }
  const res = await rgSearch(cfg, sym, { word: true, fixed: true, paths });
  const title = `### 🔒 STATE MUTATION & ACCESS SITES: \`${sym}\``;
  const files = res.sortedPaths();
  if (!files.length) return `${title}\n✅ \`${sym}\` is not referenced` + (paths.length ? ` in \`${paths[0]}\`.` : " in any C/C++ file.");
  const tagsByFile = await tryCtagsForFiles(cfg, files);
  const rows: Row[] = [];
  let atomicDecl = false;
  const word = new RegExp(`\\b${md.escapeRegex(sym)}\\b`);
  const esc = md.escapeRegex(sym);
  for (const path of files) {
    let lines: string[];
    try {
      lines = readLines(join(cfg.workspaceRoot, path));
    } catch {
      continue;
    }
    const stripped = stripCode(lines);
    const tags = tagsByFile.get(path) ?? [];
    for (const m of res.files.get(path)!) {
      if (!m.isMatch || !(m.line > 0 && m.line <= lines.length) || !word.test(stripped[m.line - 1])) continue;
      const code = stripped[m.line - 1];
      const decl = tags.find((t) => t.line === m.line && t.shortName === sym && ["member", "variable", "externvar"].includes(t.kind));
      const fn = innermost(tags, m.line, FUNCTION_KINDS);
      if (decl && fn === null) {
        if (ATOMIC_DECL.test(code)) atomicDecl = true;
        rows.push({ path, line: m.line, fn: decl.scope || "(file scope)", access: "declaration", sync: ATOMIC_DECL.test(code) ? "atomic" : "—", text: lines[m.line - 1] });
        continue;
      }
      const access = accessKind(code, sym);
      if (
        (LOCK_DECL.test(code) && new RegExp(`\\(\\s*[\\w.\\->]*\\b${esc}\\b`).test(code)) ||
        new RegExp(`\\b${esc}\\s*(?:\\.|->)\\s*(?:lock|lock_shared|try_lock|unlock|unlock_shared)\\s*\\(`).test(code) ||
        lineEvents(code).some((e) => e.mutexes.some((mx) => mx.split(".").pop() === sym))
      ) {
        rows.push({ path, line: m.line, fn: fn ? fn.qualified : "(file scope)", access: "lock operation", sync: "— (this is the mutex)", text: lines[m.line - 1] });
        continue;
      }
      let sync: string;
      if (fn === null) sync = "file scope";
      else if (isCtorDtor(fn)) sync = "ctor/dtor";
      else {
        const locks = activeLocks(stripped, fn, m.line);
        if (locks.length) {
          const [kind, ln] = locks[locks.length - 1];
          sync = `🔒 ${kind} (L${ln})`;
          if ((access === "write" || access === "mutating call") && kind === "shared_lock") sync += " ⚠️ shared lock for a write";
        } else sync = "❌ BARE";
      }
      rows.push({ path, line: m.line, fn: fn ? fn.qualified : "(file scope)", access, sync, text: lines[m.line - 1] });
    }
  }
  if (atomicDecl) for (const r of rows) if (r.sync === "❌ BARE") r.sync = "⚛️ atomic";
  const accesses = rows.filter((r) => r.access !== "declaration" && r.access !== "lock operation");
  if (!rows.length) return `${title}\n✅ Only comment/string mentions of \`${sym}\` were found.`;
  const locked = accesses.filter((r) => r.sync.startsWith("🔒"));
  const bare = accesses.filter((r) => r.sync === "❌ BARE");
  const writes = accesses.filter((r) => r.access === "write" || r.access === "mutating call");
  const lockOps = rows.filter((r) => r.access === "lock operation").length;
  let summary = `${md.plural(accesses.length, "access", "es")} (${md.plural(writes.length, "write")})`;
  if (lockOps) summary += `, ${md.plural(lockOps, "lock operation")}`;
  const out = [title, `${summary} in ${md.plural(new Set(rows.map((r) => r.path)).size, "file")}.`];
  if (atomicDecl) out.push("⚛️ Declared atomic: individual operations are race-free, but check compound read-modify-write sequences.");
  else if (locked.length && bare.length) {
    const where = bare.slice(0, 5).map((r) => `\`${r.path}:${r.line}\` (${r.fn}, ${r.access})`).join(", ");
    out.push(
      `⚠️ **Inconsistent locking:** accessed under a lock in ${locked.length} place(s) but without one in ${bare.length}: ${where}. ` +
        "Potential data race if these run concurrently.",
    );
  } else if (bare.length && writes.length && !locked.length) {
    out.push("ℹ️ No lock protects any access. If this state is shared across threads it is unsynchronised.");
  }
  const body = rows.map((r) => `| \`${r.path}:${r.line}\` | \`${r.fn}\` | ${r.access} | ${r.sync} | \`${cell(r.text)}\` |`);
  out.push("", "| Location | Function | Access | Sync | Code |", "|---|---|---|---|---|", ...md.truncateList(body, cfg.maxResults, "accesses", "Pass file_path to focus on one file."));
  out.push("\n_Heuristic: lock scope inferred from RAII guards/.lock() inside the enclosing function; locks held by callers are not visible._");
  return out.join("\n");
}

export async function track_state_mutations(args: { symbol: string; file_path?: string }): Promise<string> {
  return stateMutationsReport(loadConfig(), args.symbol, args.file_path ?? "");
}
