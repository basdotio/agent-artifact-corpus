"""The ledger: sources, runs and the append-only event log (SQLite).

TypeDB holds the current analysis of each run; the ledger holds what it cannot:
the source texts (immutable, versioned), the runs, and every change ever made.
Each event keeps the TypeQL it ran, so a run's graph can be rebuilt (replay) or
branched (fork) from the log alone.

Writes are serialised with BEGIN IMMEDIATE: allocating an event number and ids,
writing to TypeDB and appending the event happen under one lock, so several
scholars (processes) can work on the same run.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from .util import QlsError, now, sha256_text

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
  id TEXT, version INTEGER, sha TEXT, title TEXT, meta TEXT, text TEXT, units TEXT, created TEXT,
  PRIMARY KEY (id, version));
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, parent TEXT, fork_at INTEGER, method TEXT, method_hash TEXT, intent TEXT,
  config TEXT, db TEXT, status TEXT DEFAULT 'open', checkpoint_seq INTEGER, created TEXT);
CREATE TABLE IF NOT EXISTS events (
  run TEXT, seq INTEGER, action TEXT, actor TEXT, model TEXT, params TEXT, result TEXT,
  queries TEXT, reason TEXT, ts TEXT, meta TEXT, PRIMARY KEY (run, seq));
CREATE TABLE IF NOT EXISTS counters (run TEXT, prefix TEXT, n INTEGER, PRIMARY KEY (run, prefix));
CREATE TABLE IF NOT EXISTS reads (
  run TEXT, after_seq INTEGER, actor TEXT, session TEXT, tool TEXT, args TEXT, size INTEGER, ts TEXT);
CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY, run TEXT, actor TEXT, task TEXT, stage TEXT, prompt TEXT, prompt_sha TEXT, harness TEXT,
  model TEXT, config TEXT, started TEXT, ended TEXT, exit INTEGER, log TEXT);
"""

# Provenance (who, with which model, harness, prompt and stage; what was read) is kept for the
# researcher. The agent's tools never return it.


class Ledger:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path, isolation_level=None, timeout=60, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.executescript(SCHEMA)
        cols = {r["name"] for r in self.db.execute("PRAGMA table_info(events)")}
        if "meta" not in cols:  # ledgers made before provenance was recorded
            self.db.execute("ALTER TABLE events ADD COLUMN meta TEXT")

    @contextmanager
    def lock(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    # -- sources ----------------------------------------------------------------

    def add_source(self, sid: str, text: str, units: list[dict], title: str, meta: dict) -> int:
        sha = sha256_text(text)
        cur = self.db.execute("SELECT version, sha FROM sources WHERE id=? ORDER BY version DESC LIMIT 1", (sid,)).fetchone()
        if cur and cur["sha"] == sha:
            return cur["version"]
        version = (cur["version"] + 1) if cur else 1
        self.db.execute("INSERT INTO sources VALUES (?,?,?,?,?,?,?,?)",
                        (sid, version, sha, title, json.dumps(meta), text, json.dumps(units), now()))
        return version

    def source(self, sid: str, version: int | None = None) -> dict:
        q = "SELECT * FROM sources WHERE id=?" + (" AND version=?" if version else "") + " ORDER BY version DESC LIMIT 1"
        row = self.db.execute(q, (sid, version) if version else (sid,)).fetchone()
        if not row:
            raise QlsError(f"No source {sid!r}" + (f" version {version}" if version else ""))
        d = dict(row)
        d["meta"], d["units"] = json.loads(d["meta"]), json.loads(d["units"])
        return d

    def sources(self) -> list[dict]:
        rows = self.db.execute("SELECT id, MAX(version) AS version, title FROM sources GROUP BY id ORDER BY id").fetchall()
        return [dict(r) for r in rows]

    # -- runs -------------------------------------------------------------------

    def create_run(self, rid: str, method: str, method_hash: str, intent: dict, config: dict, db: str,
                   parent: str | None = None, fork_at: int | None = None) -> None:
        if self.db.execute("SELECT 1 FROM runs WHERE id=?", (rid,)).fetchone():
            raise QlsError(f"Run {rid!r} exists")
        self.db.execute("INSERT INTO runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (rid, parent, fork_at, method, method_hash, json.dumps(intent), json.dumps(config), db, "open", None, now()))

    def run(self, rid: str) -> dict:
        row = self.db.execute("SELECT * FROM runs WHERE id=?", (rid,)).fetchone()
        if not row:
            raise QlsError(f"No run {rid!r}. Runs: {', '.join(r['id'] for r in self.runs()) or 'none'}")
        d = dict(row)
        d["intent"], d["config"] = json.loads(d["intent"]), json.loads(d["config"])
        return d

    def runs(self) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT id, parent, fork_at, method, status, created FROM runs ORDER BY created")]

    def set_status(self, rid: str, status: str, checkpoint_seq: int | None = None) -> None:
        self.db.execute("UPDATE runs SET status=?, checkpoint_seq=COALESCE(?, checkpoint_seq) WHERE id=?", (status, checkpoint_seq, rid))

    def delete_run(self, rid: str) -> None:
        for t in ("events", "counters"):
            self.db.execute(f"DELETE FROM {t} WHERE run=?", (rid,))
        self.db.execute("DELETE FROM runs WHERE id=?", (rid,))

    # -- events -----------------------------------------------------------------

    def next_seq(self, rid: str) -> int:
        row = self.db.execute("SELECT MAX(seq) AS m FROM events WHERE run=?", (rid,)).fetchone()
        return (row["m"] or 0) + 1

    def new_id(self, rid: str, prefix: str) -> str:
        row = self.db.execute("SELECT n FROM counters WHERE run=? AND prefix=?", (rid, prefix)).fetchone()
        n = (row["n"] if row else 0) + 1
        self.db.execute("INSERT INTO counters VALUES (?,?,?) ON CONFLICT(run, prefix) DO UPDATE SET n=excluded.n", (rid, prefix, n))
        return f"{prefix}-{n}"

    def counter(self, rid: str, prefix: str) -> int:
        row = self.db.execute("SELECT n FROM counters WHERE run=? AND prefix=?", (rid, prefix)).fetchone()
        return row["n"] if row else 0

    def set_counter(self, rid: str, prefix: str, n: int) -> None:
        self.db.execute("INSERT INTO counters VALUES (?,?,?) ON CONFLICT(run, prefix) DO UPDATE SET n=MAX(n, excluded.n)", (rid, prefix, n))

    def append(self, rid: str, seq: int, action: str, actor: str, params: dict, result: dict, queries: list[str],
               reason: str = "", model: str | None = None, meta: dict | None = None) -> None:
        self.db.execute("INSERT INTO events (run, seq, action, actor, model, params, result, queries, reason, ts, meta) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        (rid, seq, action, actor, model, json.dumps(params, ensure_ascii=False),
                         json.dumps(result, ensure_ascii=False), json.dumps(queries, ensure_ascii=False), reason, now(),
                         json.dumps(meta or {}, ensure_ascii=False)))

    def events(self, rid: str, since: int = 0, until: int | None = None) -> list[dict]:
        q, args = "SELECT * FROM events WHERE run=? AND seq>?", [rid, since]
        if until is not None:
            q, args = q + " AND seq<=?", args + [until]
        out = []
        for r in self.db.execute(q + " ORDER BY seq", args):
            d = dict(r)
            for k in ("params", "result", "queries"):
                d[k] = json.loads(d[k])
            d["meta"] = json.loads(d.get("meta") or "{}")
            out.append(d)
        return out

    def copy_events(self, src: str, dst: str, until: int) -> int:
        """Copy events (and the id counters they imply) into a fork."""
        evs = self.events(src, until=until)
        for e in evs:
            self.append(dst, e["seq"], e["action"], e["actor"], e["params"], e["result"], e["queries"], e["reason"], e["model"],
                        {**e["meta"], "copied_from": src})
            for oid in e["result"].get("ids", []):
                prefix, _, n = oid.rpartition("-")
                if n.isdigit():
                    self.set_counter(dst, prefix, int(n))
            if "codebook_version" in e["result"]:
                self.set_counter(dst, "CBV", e["result"]["codebook_version"])
        return len(evs)

    # -- provenance ---------------------------------------------------------------

    def log_read(self, rid: str, actor: str, session: str | None, tool: str, args: dict, size: int) -> None:
        self.db.execute("INSERT INTO reads VALUES (?,?,?,?,?,?,?,?)",
                        (rid, self.next_seq(rid) - 1, actor, session, tool, json.dumps(args, ensure_ascii=False), size, now()))

    def reads(self, rid: str, session: str | None = None) -> list[dict]:
        q, args = "SELECT * FROM reads WHERE run=?", [rid]
        if session:
            q, args = q + " AND session=?", args + [session]
        return [dict(r) for r in self.db.execute(q + " ORDER BY rowid", args)]

    def start_session(self, sid: str, rid: str, actor: str, task: str, stage: str | None, prompt: str, harness: str,
                      model: str | None, config: dict, log: str) -> None:
        self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (sid, rid, actor, task, stage, prompt, sha256_text(prompt), harness, model,
                         json.dumps(config, ensure_ascii=False), now(), None, None, log))

    def end_session(self, sid: str, exit_code: int, model: str | None = None) -> None:
        self.db.execute("UPDATE sessions SET ended=?, exit=?, model=COALESCE(?, model) WHERE id=?", (now(), exit_code, model, sid))

    def sessions(self, rid: str) -> list[dict]:
        return [dict(r) for r in self.db.execute("SELECT * FROM sessions WHERE run=? ORDER BY started", (rid,))]
