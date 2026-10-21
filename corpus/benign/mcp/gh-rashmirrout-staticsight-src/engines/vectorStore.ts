// SQLite store for the semantic index (schema: shared/semantic/schema.sql, identical to the Python implementation).
import { closeSync, mkdirSync, openSync, statSync, unlinkSync, utimesSync, writeSync } from "node:fs";
import { dirname } from "node:path";
import { sharedText } from "../shared.js";

export const SCHEMA_VERSION = "1";
const LOCK_STALE_S = 600; // a lock whose heartbeat is older than this is considered abandoned

// node:sqlite prints an ExperimentalWarning on first use; keep MCP logs clean.
const origEmit = process.emitWarning.bind(process);
process.emitWarning = ((warning: string | Error, ...rest: unknown[]) => {
  if (String((warning as Error)?.message ?? warning).includes("SQLite")) return;
  return (origEmit as (...a: unknown[]) => void)(warning, ...rest);
}) as typeof process.emitWarning;
const { DatabaseSync } = await import("node:sqlite");

export type ChunkRow = [string, number, number, string, string, string, string, number]; // path,start,end,lang,kind,symbol,signature,part
export type FileRow = [number, string, string, string, number]; // size, mtime_ns, sha1, status, chunks

export class VectorStore {
  db: InstanceType<typeof DatabaseSync>;
  constructor(public path: string) {
    mkdirSync(dirname(path), { recursive: true });
    this.db = new DatabaseSync(path);
    this.db.exec("PRAGMA journal_mode=WAL");
    this.db.exec("PRAGMA synchronous=NORMAL");
    this.db.exec(sharedText("semantic/schema.sql"));
  }

  getMeta(): Record<string, string> {
    const out: Record<string, string> = {};
    for (const r of this.db.prepare("SELECT key, value FROM meta").all() as Array<{ key: string; value: string }>) out[r.key] = r.value;
    return out;
  }

  setMeta(values: Record<string, string>): void {
    const st = this.db.prepare("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)");
    for (const [k, v] of Object.entries(values)) st.run(k, String(v));
  }

  reset(meta: Record<string, string>): void {
    this.db.exec("BEGIN");
    for (const t of ["chunks", "vectors", "files", "meta"]) this.db.exec(`DELETE FROM ${t}`);
    this.db.exec("COMMIT");
    this.setMeta(meta);
  }

  files(): Map<string, FileRow> {
    const out = new Map<string, FileRow>();
    for (const r of this.db.prepare("SELECT path, size, mtime_ns, sha1, status, chunks FROM files").all() as any[]) {
      out.set(r.path, [Number(r.size), String(r.mtime_ns), r.sha1, r.status, Number(r.chunks)]);
    }
    return out;
  }

  updateStat(path: string, size: number, mtimeNs: string): void {
    this.db.prepare("UPDATE files SET size=?, mtime_ns=? WHERE path=?").run(size, mtimeNs, path);
  }

  deleteFiles(paths: string[]): void {
    if (!paths.length) return;
    this.db.exec("BEGIN");
    const dc = this.db.prepare("DELETE FROM chunks WHERE path=?");
    const df = this.db.prepare("DELETE FROM files WHERE path=?");
    for (const p of paths) {
      dc.run(p);
      df.run(p);
    }
    this.db.exec("COMMIT");
  }

  /** Atomically replace one file's chunks. chunks: [start, end, language, kind, symbol, signature, part, hash]. */
  replaceFile(path: string, size: number, mtimeNs: string, sha1: string, language: string, status: string,
    chunks: Array<[number, number, string, string, string, string, number, string]>, vectors: Map<string, Uint8Array>): void {
    this.db.exec("BEGIN");
    try {
      this.db.prepare("DELETE FROM chunks WHERE path=?").run(path);
      const iv = this.db.prepare("INSERT OR IGNORE INTO vectors(text_hash, vector) VALUES(?, ?)");
      for (const [h, v] of vectors) iv.run(h, v);
      const ic = this.db.prepare(
        "INSERT INTO chunks(path, start_line, end_line, language, kind, symbol, signature, part, text_hash) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
      );
      for (const c of chunks) ic.run(path, ...c);
      this.db
        .prepare("INSERT OR REPLACE INTO files(path, size, mtime_ns, sha1, language, status, chunks) VALUES(?,?,?,?,?,?,?)")
        .run(path, size, mtimeNs, sha1, language, status, chunks.length);
      this.db.exec("COMMIT");
    } catch (e) {
      this.db.exec("ROLLBACK");
      throw e;
    }
  }

  knownHashes(hashes: Iterable<string>): Set<string> {
    const list = [...new Set(hashes)];
    const found = new Set<string>();
    for (let i = 0; i < list.length; i += 500) {
      const part = list.slice(i, i + 500);
      const q = `SELECT text_hash FROM vectors WHERE text_hash IN (${part.map(() => "?").join(",")})`;
      for (const r of this.db.prepare(q).all(...part) as any[]) found.add(r.text_hash);
    }
    return found;
  }

  gcVectors(): void {
    this.db.exec("DELETE FROM vectors WHERE text_hash NOT IN (SELECT DISTINCT text_hash FROM chunks)");
  }

  /** [chunk rows, contiguous float32 matrix, dims] for all chunks, ordered by path/start/part. */
  loadMatrix(): [ChunkRow[], Float32Array, number] {
    const rows = this.db
      .prepare(
        "SELECT c.path, c.start_line, c.end_line, c.language, c.kind, c.symbol, c.signature, c.part, v.vector " +
          "FROM chunks c JOIN vectors v ON v.text_hash = c.text_hash ORDER BY c.path, c.start_line, c.part, c.kind, c.symbol",
      )
      .all() as any[];
    if (!rows.length) return [[], new Float32Array(0), 0];
    const dims = (rows[0].vector as Uint8Array).byteLength / 4;
    const mat = new Float32Array(rows.length * dims);
    const out: ChunkRow[] = [];
    rows.forEach((r, i) => {
      const b = r.vector as Uint8Array;
      mat.set(new Float32Array(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength)), i * dims);
      out.push([r.path, Number(r.start_line), Number(r.end_line), r.language, r.kind, r.symbol, r.signature, Number(r.part)]);
    });
    return [out, mat, dims];
  }

  counts(): { files: number; skipped: number; chunks: number; vectors: number } {
    const one = (q: string) => Number((this.db.prepare(q).get() as any).n);
    return {
      files: one("SELECT COUNT(*) AS n FROM files WHERE status='indexed'"),
      skipped: one("SELECT COUNT(*) AS n FROM files WHERE status LIKE 'skipped:%'"),
      chunks: one("SELECT COUNT(*) AS n FROM chunks"),
      vectors: one("SELECT COUNT(*) AS n FROM vectors"),
    };
  }

  skippedByReason(): Array<[string, number]> {
    return (this.db.prepare("SELECT status, COUNT(*) AS n FROM files WHERE status LIKE 'skipped:%' GROUP BY status ORDER BY status").all() as any[]).map(
      (r) => [String(r.status).split(":").slice(1).join(":"), Number(r.n)],
    );
  }

  languages(): Array<[string, number]> {
    return (this.db.prepare("SELECT language, COUNT(*) AS n FROM files WHERE status='indexed' GROUP BY language ORDER BY COUNT(*) DESC, language").all() as any[]).map(
      (r) => [r.language, Number(r.n)],
    );
  }

  close(): void {
    this.db.close();
  }
}

/** Cross-process build lock: an exclusive-create lock file with a heartbeat (portable; no OS-specific APIs). */
export class IndexLock {
  held = false;
  constructor(public path: string) {}

  acquire(): boolean {
    for (let attempt = 0; attempt < 2; attempt++) {
      try {
        const fd = openSync(this.path, "wx");
        writeSync(fd, `${process.pid} ${Math.floor(Date.now() / 1000)}`);
        closeSync(fd);
        this.held = true;
        return true;
      } catch (e) {
        if ((e as NodeJS.ErrnoException).code !== "EEXIST") return false;
        let age: number;
        try {
          age = Date.now() / 1000 - statSync(this.path).mtimeMs / 1000;
        } catch {
          continue;
        }
        if (age > LOCK_STALE_S) {
          try {
            unlinkSync(this.path);
          } catch {
            return false;
          }
          continue;
        }
        return false;
      }
    }
    return false;
  }

  heartbeat(): void {
    if (this.held) {
      try {
        const now = new Date();
        utimesSync(this.path, now, now);
      } catch {
        /* ignore */
      }
    }
  }

  release(): void {
    if (this.held) {
      try {
        unlinkSync(this.path);
      } catch {
        /* ignore */
      }
      this.held = false;
    }
  }
}
