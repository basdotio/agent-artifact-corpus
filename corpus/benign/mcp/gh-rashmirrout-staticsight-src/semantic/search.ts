// Hybrid (embedding + keyword) search, similar-code lookup and index reports (same output as the Python implementation).
import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { Config } from "../config.js";
import { InvalidArgument, StaticSightError } from "../core/errors.js";
import * as md from "../core/md.js";
import { decodeSource, matchesGlob, readLines, resolveInWorkspace, splitLines } from "../core/paths.js";
import { cmpStr, tryCtagsForFiles } from "../engines/ctags.js";
import { getEmbedder, modelId, SemanticUnavailable } from "../engines/embedder.js";
import { rgSearch } from "../engines/rg.js";
import type { ChunkRow } from "../engines/vectorStore.js";
import { chunkFile, header } from "./chunker.js";
import { isStructural, languageOf } from "./files.js";
import { getSemanticIndex, type SemanticIndex } from "./index.js";

const SEMANTIC_TOP = 60;
const LEXICAL_TOP = 60;
const RRF_K = 60;
const LEXICAL_WEIGHT = 0.5;
const EXCERPT_LINES = 6;
const TERM = /[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*/g;
const STOP = new Set(
  `a an and are as at be by can code does do for from how in is it its of on or that the this to use used uses using
what when where which who why with without we our you your function functions method methods class find show get
where's there their them then than into over under about some any all each every more most other such only same`.split(/\s+/),
);
const FENCE: Record<string, string> = {
  cpp: "cpp", c: "c", cuda: "cpp", csharp: "csharp", java: "java", python: "python", go: "go", rust: "rust", javascript: "javascript",
  typescript: "typescript", shell: "bash", powershell: "powershell", markdown: "markdown", json: "json", yaml: "yaml", xml: "xml",
  sql: "sql", ruby: "ruby", kotlin: "kotlin", swift: "swift", php: "php", cmake: "cmake", make: "make", toml: "toml", ini: "ini",
  html: "html", css: "css", lua: "lua", perl: "perl", scala: "scala", dockerfile: "dockerfile", batch: "bat",
};

export function queryTerms(query: string): string[] {
  const terms: string[] = [];
  for (const m of query.matchAll(TERM)) {
    const t = m[0];
    const low = t.toLowerCase();
    if (STOP.has(low) || t.length < 3) continue;
    if (!terms.some((x) => x.toLowerCase() === low)) terms.push(t);
  }
  return terms.slice(0, 8);
}

const score = (x: number) => md.roundTo(x, 4);

function rowCmp(a: ChunkRow, b: ChunkRow): number {
  return cmpStr(a[0], b[0]) || a[1] - b[1] || a[7] - b[7] || cmpStr(a[4], b[4]) || cmpStr(a[5], b[5]);
}

function groupKey(r: ChunkRow): string {
  // parts of one long unit collapse into one result; plain windows stay separate
  return r[5] ? `${r[0]}\u0000${r[4]}\u0000${r[5]}` : `${r[0]}\u0000${r[1]}\u0000${r[2]}\u0001`;
}

function filters(rows: ChunkRow[], pathGlob: string, language: string, kind: string): number[] {
  const lang = language.trim().toLowerCase();
  const knd = kind.trim().toLowerCase();
  const out: number[] = [];
  rows.forEach((r, i) => {
    if ((!pathGlob || matchesGlob(r[0], pathGlob)) && (!lang || r[3] === lang) && (!knd || r[4].toLowerCase() === knd)) out.push(i);
  });
  return out;
}

function dots(mat: Float32Array, dims: number, idx: number[], q: Float32Array): number[] {
  return idx.map((i) => {
    let s = 0;
    const base = i * dims;
    for (let k = 0; k < dims; k++) s += mat[base + k] * q[k];
    return s;
  });
}

async function lexical(cfg: Config, rows: ChunkRow[], allowed: number[], terms: string[]): Promise<Array<[number, number]>> {
  if (!terms.length) return [];
  let res;
  try {
    res = await rgSearch(cfg, terms, { fixed: true, ignoreCase: true, globs: [], maxCount: 200 });
  } catch (e) {
    if (e instanceof StaticSightError) return [];
    throw e;
  }
  const byPath = new Map<string, number[]>();
  for (const i of allowed) {
    if (!byPath.has(rows[i][0])) byPath.set(rows[i][0], []);
    byPath.get(rows[i][0])!.push(i);
  }
  const lows = terms.map((t) => t.toLowerCase());
  const hits = new Map<number, Set<string>>();
  const counts = new Map<number, number>();
  for (const [path, lines] of res.files) {
    const idxs = byPath.get(path);
    if (!idxs) continue;
    const starts = idxs.map((i) => rows[i][1]);
    for (const ln of lines) {
      if (!ln.isMatch) continue;
      const low = ln.text.toLowerCase();
      const found = lows.filter((t) => low.includes(t));
      if (!found.length) continue;
      let k = 0; // bisect_right
      let lo = 0;
      let hi = starts.length;
      while (lo < hi) {
        const mid = (lo + hi) >> 1;
        if (ln.line < starts[mid]) hi = mid;
        else lo = mid + 1;
      }
      k = lo;
      for (let j = k - 1; j > Math.max(-1, k - 13); j--) {
        const i = idxs[j];
        if (rows[i][1] <= ln.line && ln.line <= rows[i][2]) {
          if (!hits.has(i)) hits.set(i, new Set());
          for (const f of found) hits.get(i)!.add(f);
          counts.set(i, (counts.get(i) ?? 0) + 1);
        }
      }
    }
  }
  const ranked = [...hits.keys()].sort(
    (a, b) => hits.get(b)!.size - hits.get(a)!.size || Math.min(counts.get(b)!, 20) - Math.min(counts.get(a)!, 20) || rowCmp(rows[a], rows[b]),
  );
  return ranked.slice(0, LEXICAL_TOP).map((i) => [i, hits.get(i)!.size]);
}

function fuse(sem: Array<[number, number]>, lex: Array<[number, number]>): Array<[number, number, string]> {
  const fused = new Map<number, number>();
  sem.forEach(([i], r) => fused.set(i, (fused.get(i) ?? 0) + 1 / (RRF_K + r + 1)));
  lex.forEach(([i], r) => fused.set(i, (fused.get(i) ?? 0) + LEXICAL_WEIGHT / (RRF_K + r + 1)));
  const semSet = new Set(sem.map(([i]) => i));
  const lexSet = new Set(lex.map(([i]) => i));
  return [...fused.entries()].map(([i, f]) => [
    i,
    md.roundTo(f, 8),
    semSet.has(i) && lexSet.has(i) ? "semantic+keyword" : semSet.has(i) ? "semantic" : "keyword",
  ]);
}

function excerpt(cfg: Config, row: ChunkRow, cache: Map<string, string[]>): string[] {
  const [path, start, end] = row;
  if (!cache.has(path)) {
    try {
      cache.set(path, readLines(join(cfg.workspaceRoot, path)));
    } catch {
      cache.set(path, []);
    }
  }
  const lines = cache.get(path)!;
  if (!lines.length) return [];
  const body: Array<[number, string]> = [];
  for (let n = start; n <= Math.min(end, lines.length); n++) body.push([n, lines[n - 1]]);
  const shown = body.slice(0, EXCERPT_LINES);
  const width = shown.length ? String(shown[shown.length - 1][0]).length : 1;
  const out = shown.map(([n, t]) => `${String(n).padStart(width)} | ${md.clip(t, 140)}`);
  if (body.length > EXCERPT_LINES) out.push(`${" ".repeat(width)} | … ${body.length - EXCERPT_LINES} more lines`);
  return out;
}

function renderResult(cfg: Config, rank: number, row: ChunkRow, sim: number | undefined, how: string, cache: Map<string, string[]>): string {
  const [path, start, end, language, kind, symbol] = row;
  const what = symbol ? `${kind} \`${symbol}\`` : kind;
  const sc = sim !== undefined ? md.formatFixed(sim, 2) : "—";
  const head = `${rank}. \`${path}:${start}-${end}\` — ${what} (${language}) · ${sc} · ${how}`;
  const ex = excerpt(cfg, row, cache);
  if (!ex.length) return head;
  return head + "\n   ```" + (FENCE[language] ?? "text") + "\n" + ex.map((e) => "   " + e).join("\n") + "\n   ```";
}

function indexLine(idx: SemanticIndex, note: string): string {
  const c = idx.store.counts();
  return `Index: ${c.files} files, ${c.chunks} chunks (${modelId(idx.cfg)}). ${note}`;
}

async function keywordOnly(cfg: Config, query: string, pathGlob: string, topK: number, note: string): Promise<string> {
  const terms = queryTerms(query);
  const out = [`### 🔎 SEMANTIC SEARCH: "${md.clip(query, 100)}"`, note];
  if (!terms.length) return [...out, "No keywords to fall back on; retry when the index is ready."].join("\n");
  const res = await rgSearch(cfg, terms, { fixed: true, ignoreCase: true, globs: [], maxCount: 20 });
  const items: string[] = [];
  for (const m of res.matches()) {
    if (pathGlob && !matchesGlob(m.path, pathGlob)) continue;
    items.push(`- \`${m.path}:${m.line}\` ${md.codeSpan(m.text)}`);
  }
  out.push(`**Keyword-only results** for ${terms.map((t) => `\`${t}\``).join(", ")}:`);
  out.push(...(items.length ? md.truncateList(items, topK, "keyword hits") : ["_No keyword matches._"]));
  return out.join("\n");
}

export async function semanticSearchReport(cfg: Config, query: string, pathGlob = "", language = "", kind = "", topK = 10): Promise<string> {
  query = (query ?? "").trim();
  if (!query) throw new InvalidArgument("`query` is empty.", "Describe the code you are looking for, e.g. 'retry failed connections'.");
  topK = Math.max(1, Math.min(Math.trunc(topK || 10), 30));
  const idx = getSemanticIndex(cfg);
  const [note, usable] = await idx.ensureFresh();
  if (!usable) return keywordOnly(cfg, query, pathGlob, topK, note);
  const embedder = await getEmbedder(cfg, false);
  const [rows, mat, dims] = idx.matrix();
  const allowed = filters(rows, pathGlob, language, kind);
  const out = [`### 🔎 SEMANTIC SEARCH: "${md.clip(query, 100)}"`, indexLine(idx, note)];
  if (!allowed.length) {
    out.push("_No indexed chunks match the filters._");
    return out.join("\n");
  }
  const [qv] = await embedder.embed([query]);
  const sims = dots(mat, dims, allowed, qv);
  const order = allowed.map((_, k) => k).sort((a, b) => score(sims[b]) - score(sims[a]) || rowCmp(rows[allowed[a]], rows[allowed[b]]));
  const sem: Array<[number, number]> = order.slice(0, SEMANTIC_TOP).map((k) => [allowed[k], score(sims[k])]);
  const simOf = new Map<number, number>(allowed.map((i, k) => [i, score(sims[k])]));
  const lex = await lexical(cfg, rows, allowed, queryTerms(query));
  const fused = fuse(sem, lex).sort((a, b) => b[1] - a[1] || rowCmp(rows[a[0]], rows[b[0]]));
  const seen = new Set<string>();
  const picked: Array<[number, string]> = [];
  for (const [i, , how] of fused) {
    const g = groupKey(rows[i]);
    if (seen.has(g)) continue;
    seen.add(g);
    picked.push([i, how]);
    if (picked.length >= topK) break;
  }
  const cache = new Map<string, string[]>();
  picked.forEach(([i, how], r) => out.push(renderResult(cfg, r + 1, rows[i], simOf.get(i), how, cache)));
  out.push(
    "\n_Scores are cosine similarity from the local embedding model (higher is closer); results are ranked by fusing semantic and keyword matches. Verify the code before asserting._",
  );
  return out.join("\n");
}

async function regionText(cfg: Config, rel: string, lines: string[], start: number, end: number): Promise<[string, number, number, string]> {
  const language = languageOf(rel);
  if (end) {
    const body = lines
      .slice(start - 1, end)
      .map((ln) => Array.from(ln).slice(0, 300).join(""))
      .join("\n");
    return [header(rel, "region", "", "", 0) + "\n" + body, start, end, `lines ${start}-${end}`];
  }
  const tags = isStructural(language) ? (await tryCtagsForFiles(cfg, [rel], true)).get(rel) : null;
  const chunks = chunkFile(rel, lines, language, tags);
  const containing = chunks.filter((c) => c.startLine <= start && start <= c.endLine);
  if (!containing.length) throw new InvalidArgument(`No indexable code around \`${rel}:${start}\`.`, "Pass an explicit end_line.");
  const c = containing.reduce((best, x) => (x.endLine - x.startLine < best.endLine - best.startLine || (x.endLine - x.startLine === best.endLine - best.startLine && x.part < best.part) ? x : best));
  const label = c.symbol ? `${c.kind} \`${c.symbol}\`` : `${c.kind} lines ${c.startLine}-${c.endLine}`;
  return [c.text, c.startLine, c.endLine, label];
}

export async function similarCodeReport(cfg: Config, filePath: string, startLine: number, endLine = 0, topK = 8): Promise<string> {
  const [abs, rel] = resolveInWorkspace(cfg.workspaceRoot, filePath);
  const lines = splitLines(decodeSource(readFileSync(abs)));
  if (startLine < 1 || startLine > lines.length) throw new InvalidArgument(`Line ${startLine} is out of range: \`${rel}\` has ${lines.length} lines.`);
  if (endLine && endLine < startLine) throw new InvalidArgument(`Invalid range L${startLine}-${endLine}.`);
  endLine = endLine ? Math.min(endLine, lines.length) : 0;
  topK = Math.max(1, Math.min(Math.trunc(topK || 8), 30));
  const idx = getSemanticIndex(cfg);
  const [note, usable] = await idx.ensureFresh();
  const title = `### 🧬 SIMILAR CODE: \`${rel}:${startLine}` + (endLine ? `-${endLine}\`` : "`");
  if (!usable) return `${title}\n${note}`;
  const [text, a, b, label] = await regionText(cfg, rel, lines, startLine, endLine);
  const embedder = await getEmbedder(cfg, false);
  const [qv] = await embedder.embed([text]);
  const [rows, mat, dims] = idx.matrix();
  const cand: number[] = [];
  rows.forEach((r, i) => {
    if (!(r[0] === rel && r[1] <= b && a <= r[2])) cand.push(i);
  });
  const out = [title, `Source: ${label} (L${a}-${b}). ` + indexLine(idx, note)];
  if (!cand.length) {
    out.push("_Nothing else is indexed yet._");
    return out.join("\n");
  }
  const sims = dots(mat, dims, cand, qv);
  const order = cand.map((_, k) => k).sort((x, y) => score(sims[y]) - score(sims[x]) || rowCmp(rows[cand[x]], rows[cand[y]]));
  const seen = new Set<string>();
  const cache = new Map<string, string[]>();
  let rank = 0;
  for (const k of order) {
    const r = rows[cand[k]];
    const g = groupKey(r);
    if (seen.has(g)) continue;
    seen.add(g);
    rank++;
    const s = score(sims[k]);
    const tag = s >= 0.92 ? "near-duplicate" : s >= 0.85 ? "very similar" : "similar";
    out.push(renderResult(cfg, rank, r, s, tag, cache));
    if (rank >= topK) break;
  }
  out.push("\n_near-duplicate ≥ 0.92, very similar ≥ 0.85 (cosine). Check whether a fix in the source also applies to these places._");
  return out.join("\n");
}

/** Near-duplicates of changed functions in OTHER files, for review_changes (uses the index as is). */
export async function similarForReview(cfg: Config, targets: Array<[string, number, string]>, threshold = 0.85, perTarget = 3): Promise<string[]> {
  const idx = getSemanticIndex(cfg);
  let embedder;
  let rows: ChunkRow[];
  let mat: Float32Array;
  let dims: number;
  try {
    if (idx.building || !idx.exists() || !idx.compatible()) return [];
    embedder = await getEmbedder(cfg, false);
    [rows, mat, dims] = idx.matrix();
  } catch (e) {
    if (e instanceof StaticSightError) return [];
    throw e;
  }
  if (!rows.length) return [];
  const out: string[] = [];
  for (const [rel, line, name] of targets) {
    let text: string;
    try {
      const lines = splitLines(decodeSource(readFileSync(join(cfg.workspaceRoot, rel))));
      [text] = await regionText(cfg, rel, lines, line, 0);
    } catch {
      continue;
    }
    const [qv] = await embedder.embed([text]);
    const cand: number[] = [];
    rows.forEach((r, i) => {
      if (r[0] !== rel) cand.push(i);
    });
    if (!cand.length) continue;
    const sims = dots(mat, dims, cand, qv);
    const order = cand.map((_, k) => k).sort((x, y) => score(sims[y]) - score(sims[x]) || rowCmp(rows[cand[x]], rows[cand[y]]));
    const hits: string[] = [];
    const seen = new Set<string>();
    for (const k of order) {
      const s = score(sims[k]);
      if (s < threshold || hits.length >= perTarget) break;
      const r = rows[cand[k]];
      if (seen.has(groupKey(r))) continue;
      seen.add(groupKey(r));
      const what = r[5] ? `\`${r[5]}\`` : r[4];
      hits.push(`\`${r[0]}:${r[1]}-${r[2]}\` ${what} (${md.formatFixed(s, 2)})`);
    }
    if (hits.length) out.push(`- \`${name}\` (\`${rel}:${line}\`) resembles: ` + hits.join("; "));
  }
  return out;
}

export async function refreshReport(cfg: Config, full = false): Promise<string> {
  const idx = getSemanticIndex(cfg);
  const title = "### 🧠 SEMANTIC INDEX REFRESH";
  if (idx.building) return `${title}\n${idx.progressNote()}`;
  const exists = idx.exists() && idx.compatible();
  const pending = exists && !full ? (await idx.drift()).total : null;
  if (pending !== null && pending <= cfg.semanticAutoRefreshFiles) {
    const summary = await idx.refresh(false);
    return `${title}\n✅ ${summary[0].toUpperCase() + summary.slice(1)}. ` + indexLine(idx, "").trimEnd();
  }
  idx.startBackground(full || !exists);
  const what = full || !exists ? "Full rebuild" : `Refresh of ${pending} changed files`;
  return (
    `${title}\n🏗️ ${what} started in the background (${idx.progressNote(true)}). ` +
    "Call get_index_status to follow progress; semantic_search keeps working on the current index meanwhile."
  );
}

export async function statusSection(cfg: Config): Promise<string[]> {
  const idx = getSemanticIndex(cfg);
  const out = ["", "### 🧠 SEMANTIC INDEX"];
  try {
    if (idx.building) out.push(`- **State:** building. ${idx.progressNote()}`);
    else if (idx.state.status === "failed") out.push(`- **State:** last refresh failed: ${idx.state.error}`);
    else if (!idx.exists()) out.push("- **State:** not built yet (built automatically on the first semantic_search, or call refresh_semantic_index)");
    else if (!idx.compatible()) out.push("- **State:** needs a rebuild (model or format changed); the next search starts it");
    else {
      const meta = idx.store.getMeta();
      const age = Math.floor(Date.now() / 1000 - Number(meta.updated_at ?? "0"));
      out.push(`- **State:** ready (last refresh ${age}s ago${meta.head ? ", HEAD " + meta.head.slice(0, 10) : ""})`);
    }
    if (idx.exists()) {
      const c = idx.store.counts();
      const sk = idx.store.skippedByReason();
      out.push(`- **Content:** ${c.files} files, ${c.chunks} chunks, ${c.vectors} vectors; skipped: ` + (sk.map(([r, n]) => `${n} ${r}`).join(", ") || "none"));
      const langs = idx.store.languages().slice(0, 8);
      if (langs.length) out.push("- **Languages:** " + langs.map(([l, n]) => `${l} (${n})`).join(", "));
    }
    out.push(`- **Model:** ${modelId(cfg)}`);
    out.push(`- **Database:** \`${idx.dbPath}\` (${idx.dataDirReason})`);
    if (idx.state.lastSummary) out.push(`- **Last refresh:** ${idx.state.lastSummary}`);
  } catch (e) {
    if (!(e instanceof SemanticUnavailable)) throw e;
    out.push(`- **State:** unavailable: ${e.message}` + (e.hint ? ` 💡 ${e.hint}` : ""));
  }
  return out;
}
