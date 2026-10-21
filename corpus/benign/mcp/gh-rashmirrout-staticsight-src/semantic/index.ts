// Incremental semantic index: scan, drift detection, (background) refresh, and the in-memory search matrix.
import { createHash } from "node:crypto";
import { existsSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import { type Config, loadConfig, workspaceDataDir } from "../config.js";
import { StaticSightError } from "../core/errors.js";
import { decodeSource, splitLines } from "../core/paths.js";
import { tryCtagsForFiles } from "../engines/ctags.js";
import { type Embedder, getEmbedder, modelId } from "../engines/embedder.js";
import { headSha } from "../engines/git.js";
import { rgFiles } from "../engines/rg.js";
import { type ChunkRow, IndexLock, SCHEMA_VERSION, VectorStore } from "../engines/vectorStore.js";
import { chunkFile } from "./chunker.js";
import { contentSkipReason, type FileStat, isStructural, languageOf, preSkipReason } from "./files.js";

export const CHUNKER_VERSION = "1";
const GROUP_FILES = 48;

function log(msg: string): void {
  process.stderr.write(`[staticsight.semantic] ${msg}\n`);
}

export class Drift {
  added: string[] = [];
  changed: string[] = [];
  deleted: string[] = [];
  stats = new Map<string, FileStat>();
  get total(): number {
    return this.added.length + this.changed.length + this.deleted.length;
  }
}

export interface BuildState {
  status: "idle" | "building" | "failed";
  phase: string;
  done: number;
  total: number;
  embedded: number;
  started: number;
  error: string;
  lastSummary: string;
}

export function textHash(model: string, text: string): string {
  return createHash("sha1").update(model + "\0" + text, "utf8").digest("hex");
}

/** Embedding order for big builds: code first (useful soonest), then docs, then everything else. */
function priority(path: string): number {
  const lang = languageOf(path);
  if (isStructural(lang)) return 0;
  if (["markdown", "rst", "asciidoc", "text"].includes(lang)) return 1;
  return 2;
}

export class SemanticIndex {
  dbPath: string;
  dataDirReason: string;
  state: BuildState = { status: "idle", phase: "", done: 0, total: 0, embedded: 0, started: 0, error: "", lastSummary: "" };
  private storeInst: VectorStore | null = null;
  private running: Promise<string> | null = null;
  private bg: Promise<void> | null = null;
  private matrixCache: { gen: string; rows: ChunkRow[]; mat: Float32Array; dims: number } | null = null;

  constructor(public cfg: Config) {
    const [dataDir, reason] = workspaceDataDir(cfg);
    this.dbPath = join(dataDir, "semantic.db");
    this.dataDirReason = reason;
  }

  get store(): VectorStore {
    if (!this.storeInst) this.storeInst = new VectorStore(this.dbPath);
    return this.storeInst;
  }

  exists(): boolean {
    return existsSync(this.dbPath) && !!this.store.getMeta().updated_at;
  }

  expectedMeta(): Record<string, string> {
    return { schema_version: SCHEMA_VERSION, model: modelId(this.cfg), chunker: CHUNKER_VERSION };
  }

  compatible(): boolean {
    const meta = this.store.getMeta();
    return Object.entries(this.expectedMeta()).every(([k, v]) => meta[k] === v);
  }

  async scan(): Promise<Map<string, FileStat>> {
    const out = new Map<string, FileStat>();
    for (const p of await rgFiles(this.cfg, [])) {
      try {
        const st = statSync(join(this.cfg.workspaceRoot, p), { bigint: true });
        out.set(p, { path: p, size: Number(st.size), mtimeNs: st.mtimeNs.toString() });
      } catch {
        /* vanished */
      }
    }
    return out;
  }

  async drift(): Promise<Drift> {
    const stats = await this.scan();
    const known = existsSync(this.dbPath) ? this.store.files() : new Map();
    const d = new Drift();
    d.stats = stats;
    for (const [p, st] of stats) {
      const row = known.get(p);
      if (!row) d.added.push(p);
      else if (row[0] !== st.size || row[1] !== st.mtimeNs) d.changed.push(p);
    }
    d.deleted = [...known.keys()].filter((p) => !stats.has(p)).sort();
    const cmp = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);
    d.added.sort(cmp);
    d.changed.sort(cmp);
    return d;
  }

  get building(): boolean {
    return this.bg !== null;
  }

  /** Start a background refresh unless one is running. Returns true if a new one was started. */
  startBackground(full = false): boolean {
    if (this.bg) return false;
    this.bg = this.refresh(full)
      .then(() => undefined)
      .catch((e) => {
        this.state.status = "failed";
        this.state.error = e instanceof StaticSightError ? e.message + (e.hint ? ` (${e.hint})` : "") : String(e);
        log(`refresh failed: ${this.state.error}`);
      })
      .finally(() => {
        this.bg = null;
      });
    return true;
  }

  async waitForBackground(): Promise<void> {
    if (this.bg) await this.bg;
  }

  /** Incremental (or full) refresh. Returns a one-line summary. Concurrent calls share one run. */
  refresh(full = false, progress?: (m: string) => void): Promise<string> {
    if (this.running) return this.running.then(() => this.refresh(full, progress));
    this.running = this.doRefresh(full, progress).finally(() => {
      this.running = null;
    });
    return this.running;
  }

  private async doRefresh(full: boolean, progress?: (m: string) => void): Promise<string> {
    const st = this.state;
    Object.assign(st, { status: "building", error: "", done: 0, total: 0, embedded: 0, started: Date.now() / 1000, phase: "loading model" });
    const note = (msg: string) => {
      st.phase = msg;
      progress?.(msg);
    };
    try {
      const embedder = await getEmbedder(this.cfg, true, note);
      if (full || !this.compatible()) {
        this.store.reset(this.expectedMeta());
        this.matrixCache = null;
      }
      note("scanning files");
      const drift = await this.drift();
      if (drift.total === 0) {
        this.store.setMeta({ updated_at: String(Math.floor(Date.now() / 1000)), head: await headSha(this.cfg) });
        Object.assign(st, { status: "idle", phase: "", lastSummary: "index already up to date" });
        return st.lastSummary;
      }
      const lock = new IndexLock(this.dbPath.replace(/\.db$/, ".lock"));
      if (!lock.acquire()) throw new StaticSightError("Another process is refreshing this semantic index.", "Retry in a moment (see get_index_status).");
      let summary: string;
      try {
        summary = await this.apply(drift, embedder, lock, note);
      } finally {
        lock.release();
      }
      Object.assign(st, { status: "idle", phase: "", lastSummary: summary });
      return summary;
    } catch (e) {
      if (st.status === "building") st.status = "failed";
      throw e;
    }
  }

  private async apply(drift: Drift, embedder: Embedder, lock: IndexLock, note: (m: string) => void): Promise<string> {
    const { store, state: st, cfg } = this;
    const mid = modelId(cfg);
    store.deleteFiles(drift.deleted);
    const todo = [...drift.added, ...drift.changed].sort((a, b) => priority(a) - priority(b) || (a < b ? -1 : a > b ? 1 : 0)); // code first, config last
    st.total = todo.length;
    const known = store.files();
    let reembedded = 0;
    let contentChanged = 0;
    for (let g = 0; g < todo.length; g += GROUP_FILES) {
      const group = todo.slice(g, g + GROUP_FILES);
      const prepared: Array<[string, FileStat, string, string, string, string[] | null]> = [];
      const structural: string[] = [];
      for (const path of group) {
        const fs = drift.stats.get(path)!;
        let reason = preSkipReason(path, fs.size, cfg.semanticMaxFileKb);
        let data: Uint8Array;
        try {
          data = reason ? new Uint8Array(0) : readFileSync(join(cfg.workspaceRoot, path));
        } catch {
          store.deleteFiles([path]);
          continue;
        }
        const sha = data.length ? createHash("sha1").update(data).digest("hex") : "";
        const old = known.get(path);
        if (old && !reason && old[2] === sha) {
          store.updateStat(path, fs.size, fs.mtimeNs); // touched but identical content
          continue;
        }
        const language = languageOf(path);
        contentChanged++;
        let text = "";
        if (!reason) {
          text = decodeSource(data);
          reason = contentSkipReason(data, text);
        }
        if (reason) {
          prepared.push([path, fs, sha, language, `skipped:${reason}`, null]);
          continue;
        }
        prepared.push([path, fs, sha, language, "indexed", splitLines(text)]);
        if (isStructural(language)) structural.push(path);
      }
      const tags = structural.length ? await tryCtagsForFiles(cfg, structural, true) : new Map();
      const fileChunks: Array<[string, FileStat, string, string, string, Array<[number, number, string, string, string, string, number, string]>]> = [];
      const texts = new Map<string, string>();
      for (const [path, fs, sha, language, status, lines] of prepared) {
        const chunks = lines ? chunkFile(path, lines, language, tags.get(path)) : [];
        const rows: Array<[number, number, string, string, string, string, number, string]> = [];
        for (const c of chunks) {
          const h = textHash(mid, c.text);
          if (!texts.has(h)) texts.set(h, c.text);
          rows.push([c.startLine, c.endLine, c.language, c.kind, c.symbol, c.signature, c.part, h]);
        }
        fileChunks.push([path, fs, sha, language, status, rows]);
      }
      const have = store.knownHashes(texts.keys());
      const missing = [...texts.keys()].filter((h) => !have.has(h));
      const vectors = new Map<string, Uint8Array>();
      if (missing.length) {
        note(`embedding ${st.done}/${st.total} files`);
        const mat = await embedder.embed(missing.map((h) => texts.get(h)!));
        missing.forEach((h, i) => vectors.set(h, new Uint8Array(mat[i].buffer.slice(mat[i].byteOffset, mat[i].byteOffset + mat[i].byteLength))));
        reembedded += missing.length;
        st.embedded += missing.length;
      }
      for (const [path, fs, sha, language, status, rows] of fileChunks) {
        const mine = new Map<string, Uint8Array>();
        for (const r of rows) if (vectors.has(r[7])) mine.set(r[7], vectors.get(r[7])!);
        store.replaceFile(path, fs.size, fs.mtimeNs, sha, language, status, rows, mine);
      }
      st.done = Math.min(st.total, g + group.length);
      if (!store.getMeta().updated_at) store.setMeta({ updated_at: String(Math.floor(Date.now() / 1000)), ...this.expectedMeta() }); // partial index is searchable
      this.matrixCache = null;
      lock.heartbeat();
    }
    store.gcVectors();
    const gen = Number(store.getMeta().generation ?? "0") + 1;
    store.setMeta({ generation: String(gen), updated_at: String(Math.floor(Date.now() / 1000)), head: await headSha(cfg), ...this.expectedMeta() });
    this.matrixCache = null;
    if (contentChanged === 0 && drift.deleted.length === 0) return "index already up to date";
    return `re-indexed ${contentChanged} changed file(s), removed ${drift.deleted.length}; embedded ${reembedded} new chunk(s)`;
  }

  matrix(): [ChunkRow[], Float32Array, number] {
    const gen = this.store.getMeta().generation ?? "0";
    if (!this.matrixCache || this.matrixCache.gen !== gen) {
      const [rows, mat, dims] = this.store.loadMatrix();
      this.matrixCache = { gen, rows, mat, dims };
    }
    return [this.matrixCache.rows, this.matrixCache.mat, this.matrixCache.dims];
  }

  /** Drift policy for tool calls. Returns [freshness note, index usable]. */
  async ensureFresh(): Promise<[string, boolean]> {
    const cfg = this.cfg;
    if (!this.exists() || !this.compatible()) {
      if (this.building) return [this.progressNote(), false];
      if (!cfg.semanticAutoRefresh) {
        return ["The semantic index has not been built yet (automatic refresh is disabled). Call refresh_semantic_index.", false];
      }
      this.startBackground(this.exists());
      return [
        "The semantic index is being built for the first time in the background " +
          `(${this.progressNote(true)}). Keyword results are shown meanwhile; call get_index_status to follow progress and retry when it is ready.`,
        false,
      ];
    }
    if (this.building) return [this.progressNote() + " Results come from the current (partly stale) index.", true];
    const d = await this.drift();
    if (d.total === 0) return ["Index is up to date.", true];
    if (!cfg.semanticAutoRefresh) {
      return [`⚠️ ${d.total} file(s) changed since the last refresh (automatic refresh disabled): results may be stale. Call refresh_semantic_index.`, true];
    }
    if (d.total <= cfg.semanticAutoRefreshFiles) {
      const summary = await this.refresh();
      if (summary === "index already up to date") return ["Index is up to date.", true];
      return [`Refreshed before searching: ${summary}.`, true];
    }
    this.startBackground();
    return [
      `⚠️ ${d.total} files changed since the last refresh; a background refresh has started. Results come from the stale index; call get_index_status and retry for fresh results.`,
      true,
    ];
  }

  progressNote(short = false): string {
    const st = this.state;
    if (st.status !== "building") return this.building ? "starting" : "idle";
    const pct = `${st.total ? Math.floor((100 * st.done) / st.total) : 0}%`;
    const base = `${st.phase || "building"}; ${st.done}/${st.total} files (${pct}), ${st.embedded} chunks embedded`;
    if (short) return base;
    const elapsed = Date.now() / 1000 - st.started;
    let eta = "";
    if (st.done && st.total && st.done < st.total) eta = `, ~${Math.floor((elapsed / st.done) * (st.total - st.done))}s left`;
    return `🏗️ Semantic index refresh in progress: ${base}${eta}.`;
  }
}

const indexes = new Map<string, SemanticIndex>();

export function getSemanticIndex(cfg?: Config): SemanticIndex {
  const c = cfg ?? loadConfig();
  const key = `${c.workspaceRoot}|${c.cacheDir}|${c.dataDirMode}|${c.embedModel}|${c.embedModelDir}`;
  let idx = indexes.get(key);
  if (!idx) {
    idx = new SemanticIndex(c);
    indexes.set(key, idx);
  } else idx.cfg = c; // pick up changed knobs (auto-refresh, thresholds)
  return idx;
}

export function resetSemanticIndexes(): void {
  for (const idx of indexes.values()) {
    try {
      idx.store.close();
    } catch {
      /* ignore */
    }
  }
  indexes.clear();
}
