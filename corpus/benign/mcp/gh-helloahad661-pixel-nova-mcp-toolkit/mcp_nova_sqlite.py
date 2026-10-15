"""nova-sqlite — local SQLite access as an MCP server.

Replaces `@modelcontextprotocol/server-sqlite`, which returns HTTP 404 from
npm and therefore never worked.

Safety
------
Read-only by default. `execute_sql` refuses anything that is not a SELECT or
WITH unless the caller explicitly passes `allow_write=True`, and even then it
refuses schema-changing statements. Only databases under ALLOWED_ROOTS can be
opened, so this cannot be pointed at arbitrary files on the machine. Writes go
through a transaction that is rolled back on error.
"""
import os
import pathlib
import re
import sqlite3

from mcp.server.mcpserver import MCPServer

mcp = MCPServer("nova-sqlite")

# Only databases under these roots are reachable.
ALLOWED_ROOTS = [pathlib.Path.home() / "Nova", pathlib.Path("/tmp"),
                 pathlib.Path.home() / "jarvis-vault"]
MAX_ROWS = 500
MAX_BYTES = 64_000_000  # 64 MB ceiling; refuse to open anything larger

FORBIDDEN = ("attach", "detach", "pragma", "vacuum", "drop ", "alter ",
             "create ", "replac", "insert ", "update ", "delete ", "replace ")


def _normalized(sql: str) -> str:
    """Lowercase, strip comments, collapse whitespace — for guard checks.

    Without this, `DROP/**/TABLE` or `drop\\tusers` slips past a plain
    substring scan. The mode=ro connection remains the true guard; this
    just makes the scan honest.
    """
    s = re.sub(r"/\*.*?\*/", " ", sql, flags=re.S)
    s = re.sub(r"--[^\n]*", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def _resolve(db: str) -> pathlib.Path:
    p = pathlib.Path(db).expanduser().resolve()
    for root in ALLOWED_ROOTS:
        try:
            p.relative_to(root.resolve())
            break
        except ValueError:
            continue
    else:
        raise ValueError(
            "database must live under one of: %s" %
            ", ".join(str(r) for r in ALLOWED_ROOTS))
    if not p.exists():
        raise FileNotFoundError("no such database: %s" % p)
    if p.stat().st_size > MAX_BYTES:
        raise ValueError("database too large: %.1f MB" % (p.stat().st_size / 1e6))
    return p


def _connect(db: str, read_only: bool = True) -> sqlite3.Connection:
    p = _resolve(db)
    if read_only:
        uri = "file:%s?mode=ro" % p.as_posix().replace("?", "%3f").replace("#", "%23")
        con = sqlite3.connect(uri, uri=True, timeout=10)
    else:
        con = sqlite3.connect(str(p), timeout=10, isolation_level=None)
    con.row_factory = sqlite3.Row
    return con


@mcp.tool()
def list_databases(pattern: str = "") -> dict:
    """Find .db/.sqlite files under the allowed roots."""
    found = []
    for root in ALLOWED_ROOTS:
        if not root.exists():
            continue
        try:
            for p in root.rglob("*"):
                if p.suffix in (".db", ".sqlite", ".sqlite3") and p.is_file():
                    if pattern and pattern not in str(p):
                        continue
                    found.append({"path": str(p),
                                  "size_mb": round(p.stat().st_size / 1e6, 3)})
        except (OSError, PermissionError):
            continue
        if len(found) > 100:
            break
    return {"ok": True, "count": len(found), "databases": found,
            "allowed_roots": [str(r) for r in ALLOWED_ROOTS]}


@mcp.tool()
def list_tables(db: str) -> dict:
    """List tables and row counts in a database."""
    try:
        con = _connect(db)
    except (ValueError, FileNotFoundError, sqlite3.Error) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    try:
        rows = con.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table','view') ORDER BY name").fetchall()
        out = []
        for r in rows:
            entry = {"name": r["name"], "type": r["type"]}
            if r["type"] == "table":
                try:
                    entry["rows"] = con.execute(
                        'SELECT COUNT(*) FROM "%s"' % r["name"].replace('"', '""')
                    ).fetchone()[0]
                except sqlite3.Error:
                    entry["rows"] = None
            out.append(entry)
        return {"ok": True, "db": str(_resolve(db)), "count": len(out), "objects": out}
    finally:
        con.close()


@mcp.tool()
def schema(db: str, table: str = "") -> dict:
    """Show the SQL schema, optionally for one table."""
    try:
        con = _connect(db)
    except (ValueError, FileNotFoundError, sqlite3.Error) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    try:
        if table:
            rows = con.execute(
                "SELECT sql FROM sqlite_master WHERE name = ? AND sql IS NOT NULL",
                (table,)).fetchall()
        else:
            rows = con.execute(
                "SELECT name, sql FROM sqlite_master "
                "WHERE sql IS NOT NULL ORDER BY name").fetchall()
        return {"ok": True, "schema": [{"name": r["name"] if len(r) > 1 else table,
                                        "sql": r["sql"] if len(r) > 1 else r["sql"]}
                                       for r in rows]}
    finally:
        con.close()


@mcp.tool()
def query(db: str, sql: str, params: str = "") -> dict:
    """Run a read-only SQL query. SELECT/WITH only, capped at 500 rows."""
    s = sql.strip().rstrip(";")
    low = _normalized(s)
    if not (low.startswith("select") or low.startswith("with")):
        return {"ok": False,
                "error": "read-only tool: statement must start with SELECT or WITH"}
    for bad in FORBIDDEN:
        if bad in low:
            return {"ok": False, "error": "refused: contains %r" % bad.strip()}
    args = []
    if params:
        try:
            args = json.loads(params) if params.strip().startswith("[") else []
        except Exception as e:
            return {"ok": False, "error": "bad params: %s" % e}
    try:
        con = _connect(db)
    except (ValueError, FileNotFoundError, sqlite3.Error) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    try:
        cur = con.execute(s, args)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = [dict(zip(cols, r)) for r in cur.fetchmany(MAX_ROWS)]
        return {"ok": True, "columns": cols, "row_count": len(rows),
                "rows": rows, "truncated_at": MAX_ROWS}
    except sqlite3.Error as e:
        return {"ok": False, "error": "sqlite3: %s" % e}
    finally:
        con.close()


@mcp.tool()
def execute_write(db: str, sql: str, allow_write: bool = False) -> dict:
    """Run an INSERT/UPDATE/DELETE. Requires allow_write=True.

    Schema changes (CREATE/DROP/ALTER) are refused outright.
    """
    if not allow_write:
        return {"ok": False,
                "error": "refused: pass allow_write=True to confirm a write"}
    s = sql.strip().rstrip(";")
    low = s.lower()
    if not (low.startswith("insert") or low.startswith("update")
            or low.startswith("delete")):
        return {"ok": False, "error": "only INSERT/UPDATE/DELETE; "
                                      "use schema() for DDL"}
    try:
        con = _connect(db, read_only=False)
    except (ValueError, FileNotFoundError, sqlite3.Error) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, e)}
    try:
        con.execute("BEGIN")
        cur = con.execute(s)
        con.execute("COMMIT")
        return {"ok": True, "rows_affected": cur.rowcount}
    except sqlite3.Error as e:
        try:
            con.execute("ROLLBACK")
        except sqlite3.Error:
            pass
        return {"ok": False, "error": "sqlite3: %s" % e}
    finally:
        con.close()


if __name__ == "__main__":
    import json  # only needed for the optional params argument
    mcp.run()