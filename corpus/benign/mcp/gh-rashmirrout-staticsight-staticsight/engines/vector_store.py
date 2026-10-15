"""SQLite store for the semantic index (schema: shared/semantic/schema.sql, identical in Python and TypeScript)."""

from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path
from typing import Iterable

from ..shared import shared_text

SCHEMA_VERSION = "1"
LOCK_STALE_S = 600   # a lock whose heartbeat is older than this is considered abandoned


class VectorStore:
    def __init__(self, db_path: Path):
        self.path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(db_path), isolation_level=None, check_same_thread=False)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.executescript(shared_text("semantic/schema.sql"))

    # ------------------------------------------------------------------ meta
    def get_meta(self) -> dict[str, str]:
        return {k: v for k, v in self.db.execute("SELECT key, value FROM meta")}

    def set_meta(self, **values: str) -> None:
        self.db.executemany("INSERT OR REPLACE INTO meta(key, value) VALUES(?, ?)", [(k, str(v)) for k, v in values.items()])

    def reset(self, **meta: str) -> None:
        self.db.execute("BEGIN")
        for t in ("chunks", "vectors", "files", "meta"):
            self.db.execute(f"DELETE FROM {t}")
        self.db.execute("COMMIT")
        self.set_meta(**meta)

    # ----------------------------------------------------------------- files
    def files(self) -> dict[str, tuple[int, str, str, str, int]]:
        """path -> (size, mtime_ns, sha1, status, chunks)"""
        return {r[0]: (r[1], r[2], r[3], r[4], r[5]) for r in self.db.execute(
            "SELECT path, size, mtime_ns, sha1, status, chunks FROM files")}

    def update_stat(self, path: str, size: int, mtime_ns: str) -> None:
        self.db.execute("UPDATE files SET size=?, mtime_ns=? WHERE path=?", (size, mtime_ns, path))

    def delete_files(self, paths: Iterable[str]) -> None:
        paths = list(paths)
        if not paths:
            return
        self.db.execute("BEGIN")
        for p in paths:
            self.db.execute("DELETE FROM chunks WHERE path=?", (p,))
            self.db.execute("DELETE FROM files WHERE path=?", (p,))
        self.db.execute("COMMIT")

    def replace_file(self, path: str, size: int, mtime_ns: str, sha1: str, language: str, status: str,
                     chunks: list[tuple], vectors: dict[str, bytes]) -> None:
        """Atomically replace one file's chunks. chunks: (start, end, language, kind, symbol, signature, part, hash)."""
        self.db.execute("BEGIN")
        try:
            self.db.execute("DELETE FROM chunks WHERE path=?", (path,))
            self.db.executemany("INSERT OR IGNORE INTO vectors(text_hash, vector) VALUES(?, ?)", list(vectors.items()))
            self.db.executemany(
                "INSERT INTO chunks(path, start_line, end_line, language, kind, symbol, signature, part, text_hash) "
                "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [(path, *c) for c in chunks],
            )
            self.db.execute(
                "INSERT OR REPLACE INTO files(path, size, mtime_ns, sha1, language, status, chunks) VALUES(?,?,?,?,?,?,?)",
                (path, size, mtime_ns, sha1, language, status, len(chunks)),
            )
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def known_hashes(self, hashes: Iterable[str]) -> set[str]:
        hashes = list(dict.fromkeys(hashes))
        found: set[str] = set()
        for i in range(0, len(hashes), 500):
            part = hashes[i : i + 500]
            q = "SELECT text_hash FROM vectors WHERE text_hash IN (%s)" % ",".join("?" * len(part))
            found.update(r[0] for r in self.db.execute(q, part))
        return found

    def gc_vectors(self) -> int:
        cur = self.db.execute("DELETE FROM vectors WHERE text_hash NOT IN (SELECT DISTINCT text_hash FROM chunks)")
        return cur.rowcount or 0

    # ---------------------------------------------------------------- search
    def load_matrix(self):
        """(chunk rows, float32 matrix) for all chunks, ordered by path/start/part."""
        import numpy as np

        rows = self.db.execute(
            "SELECT c.path, c.start_line, c.end_line, c.language, c.kind, c.symbol, c.signature, c.part, v.vector "
            "FROM chunks c JOIN vectors v ON v.text_hash = c.text_hash ORDER BY c.path, c.start_line, c.part, c.kind, c.symbol"
        ).fetchall()
        if not rows:
            return [], np.zeros((0, 0), dtype=np.float32)
        dims = len(rows[0][8]) // 4
        mat = np.frombuffer(b"".join(r[8] for r in rows), dtype="<f4").reshape(len(rows), dims)
        return [r[:8] for r in rows], mat

    def chunks_of(self, path: str) -> list[tuple]:
        return self.db.execute(
            "SELECT c.start_line, c.end_line, c.language, c.kind, c.symbol, c.signature, c.part, v.vector FROM chunks c "
            "JOIN vectors v ON v.text_hash = c.text_hash WHERE c.path=? ORDER BY c.start_line, c.part", (path,)
        ).fetchall()

    def counts(self) -> dict[str, int]:
        files = self.db.execute("SELECT COUNT(*) FROM files WHERE status='indexed'").fetchone()[0]
        skipped = self.db.execute("SELECT COUNT(*) FROM files WHERE status LIKE 'skipped:%'").fetchone()[0]
        chunks = self.db.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        vectors = self.db.execute("SELECT COUNT(*) FROM vectors").fetchone()[0]
        return {"files": files, "skipped": skipped, "chunks": chunks, "vectors": vectors}

    def skipped_by_reason(self) -> dict[str, int]:
        return {r[0].split(":", 1)[1]: r[1] for r in self.db.execute(
            "SELECT status, COUNT(*) FROM files WHERE status LIKE 'skipped:%' GROUP BY status ORDER BY status")}

    def languages(self) -> list[tuple[str, int]]:
        return [(r[0], r[1]) for r in self.db.execute(
            "SELECT language, COUNT(*) FROM files WHERE status='indexed' GROUP BY language ORDER BY COUNT(*) DESC, language")]

    def close(self) -> None:
        self.db.close()


class IndexLock:
    """Cross-process build lock: an O_EXCL lock file with a heartbeat (portable; no OS-specific APIs)."""

    def __init__(self, path: Path):
        self.path = path
        self.held = False

    def acquire(self) -> bool:
        for _ in range(2):
            try:
                fd = os.open(str(self.path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.write(fd, f"{os.getpid()} {time.time():.0f}".encode())
                os.close(fd)
                self.held = True
                return True
            except FileExistsError:
                try:
                    age = time.time() - self.path.stat().st_mtime
                except OSError:
                    continue
                if age > LOCK_STALE_S:
                    try:
                        self.path.unlink()
                    except OSError:
                        return False
                    continue
                return False
        return False

    def heartbeat(self) -> None:
        if self.held:
            try:
                os.utime(self.path, None)
            except OSError:
                pass

    def release(self) -> None:
        if self.held:
            try:
                self.path.unlink()
            except OSError:
                pass
            self.held = False
