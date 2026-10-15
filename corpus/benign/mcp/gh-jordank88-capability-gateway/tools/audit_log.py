"""
audit_log.py -- append-only audit trail for consequential tool actions.

Storage: .cache/audit_log.db (SQLite, append-only by design -- no UPDATE/DELETE).

Modes
-----
append      Write one record. Fields: tool, args_summary, result_summary,
            session_id, user, tags (list of strings).
query       Filter log: date_from, date_to, tool, session_id, user, tag.
tail        Last N records (default 20).
stats       Count by tool, by day, by user.
export_csv  Dump filtered log to a CSV file.

Design note: args_summary and result_summary should be trimmed -- not full payloads.
             Keep them short enough to be useful in a log entry.

Usage (CLI)
-----------
  python tools/audit_log.py '{"mode": "append", "tool": "my_tool", "args_summary": "weekly report 2026-06-30", "result_summary": "uploaded OK"}'
  python tools/audit_log.py '{"mode": "tail", "count": 10}'
  python tools/audit_log.py '{"mode": "query", "tool": "my_tool", "date_from": "2026-07-01"}'
  python tools/audit_log.py '{"mode": "stats"}'
"""

import csv
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # repo root, for _utils
from _utils import read_args, emit, ok, fail

_ROOT = Path(__file__).resolve().parent.parent
_DB_PATH = _ROOT / ".cache" / "audit_log.db"


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _conn() -> sqlite3.Connection:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at      TEXT    NOT NULL,
            tool            TEXT    NOT NULL,
            args_summary    TEXT,
            result_summary  TEXT,
            session_id      TEXT,
            user            TEXT,
            tags_json       TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_al_tool ON audit_log(tool)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_al_date ON audit_log(created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_al_session ON audit_log(session_id)")
    conn.commit()
    return conn


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    tags_raw = d.pop("tags_json", None)
    d["tags"] = json.loads(tags_raw) if tags_raw else []
    return d


# ---------------------------------------------------------------------------
# Mode handlers
# ---------------------------------------------------------------------------

def _append(conn, args: dict) -> dict:
    tool           = args.get("tool", "")
    args_summary   = args.get("args_summary", "")
    result_summary = args.get("result_summary", "")
    session_id     = args.get("session_id")
    user           = args.get("user")
    tags           = args.get("tags", [])

    if not tool:
        return fail("'tool' is required for append mode")

    now = _now()
    cur = conn.execute(
        "INSERT INTO audit_log (created_at, tool, args_summary, result_summary, session_id, user, tags_json) "
        "VALUES (?,?,?,?,?,?,?)",
        (now, tool, args_summary, result_summary, session_id, user, json.dumps(tags)),
    )
    conn.commit()
    return ok(id=cur.lastrowid, tool=tool, created_at=now)


def _query(conn, args: dict) -> dict:
    clauses = []
    params  = []

    if args.get("tool"):
        clauses.append("tool = ?")
        params.append(args["tool"])
    if args.get("session_id"):
        clauses.append("session_id = ?")
        params.append(args["session_id"])
    if args.get("user"):
        clauses.append("user = ?")
        params.append(args["user"])
    if args.get("date_from"):
        clauses.append("created_at >= ?")
        params.append(args["date_from"])
    if args.get("date_to"):
        clauses.append("created_at <= ?")
        params.append(args["date_to"] + "Z")
    if args.get("tag"):
        # tags stored as JSON array -- use LIKE for simplicity
        clauses.append("tags_json LIKE ?")
        params.append(f'%"{args["tag"]}"%')

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    limit = int(args.get("limit", 200))
    sql   = f"SELECT * FROM audit_log {where} ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    rows = conn.execute(sql, params).fetchall()
    return ok(records=[_row_to_dict(r) for r in rows], count=len(rows))


def _tail(conn, count: int) -> dict:
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?", (count,)
    ).fetchall()
    return ok(records=[_row_to_dict(r) for r in rows], count=len(rows))


def _stats(conn) -> dict:
    by_tool = conn.execute(
        "SELECT tool, COUNT(*) as count FROM audit_log GROUP BY tool ORDER BY count DESC"
    ).fetchall()
    by_day = conn.execute(
        "SELECT substr(created_at,1,10) as day, COUNT(*) as count "
        "FROM audit_log GROUP BY day ORDER BY day DESC LIMIT 30"
    ).fetchall()
    by_user = conn.execute(
        "SELECT coalesce(user,'(unknown)') as user, COUNT(*) as count "
        "FROM audit_log GROUP BY user ORDER BY count DESC"
    ).fetchall()
    total = conn.execute("SELECT COUNT(*) as n FROM audit_log").fetchone()["n"]
    return ok(
        total=total,
        by_tool=[dict(r) for r in by_tool],
        by_day=[dict(r) for r in by_day],
        by_user=[dict(r) for r in by_user],
    )


def _export_csv(conn, args: dict) -> dict:
    # Reuse query logic
    result = _query(conn, args)
    if not result["success"]:
        return result

    out_path = args.get("output_file") or str(
        _ROOT / ".cache" / f"audit_log_{_now()[:10]}.csv"
    )
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)

    records = result["records"]
    if not records:
        return ok(output_file=out_path, rows_written=0)

    fieldnames = list(records[0].keys())
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)

    return ok(output_file=out_path, rows_written=len(records))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(arguments: dict) -> dict:
    mode = arguments.get("mode", "tail")

    try:
        conn = _conn()
    except Exception as exc:
        return fail(f"DB open failed: {exc}")

    try:
        if mode == "append":
            return _append(conn, arguments)
        elif mode == "query":
            return _query(conn, arguments)
        elif mode == "tail":
            count = int(arguments.get("count", 20))
            return _tail(conn, count)
        elif mode == "stats":
            return _stats(conn)
        elif mode == "export_csv":
            return _export_csv(conn, arguments)
        else:
            return fail(f"Unknown mode: {mode}")
    except Exception as exc:
        return fail(str(exc))
    finally:
        conn.close()


if __name__ == "__main__":
    emit(run(read_args({"mode": "tail"})))
