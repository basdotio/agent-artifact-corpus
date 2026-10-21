# /// script
# requires-python = ">=3.10"
# dependencies = ["mcp>=1.2,<2"]  # pinned: v1 API (FastMCP) — what most docs & AI assistants use
# ///
"""
LAYER 1 — MCP SERVER (the hands)

Your team's MCP server over the Suki Mart sandbox (data/store.db).

Run standalone to check it starts (Ctrl+C to stop):
    uv run mcp-server/server.py

Register with Hermes (use the ABSOLUTE path to this file):
    hermes mcp add suki --command uv --args run /ABSOLUTE/PATH/TO/mcp-server/server.py
    # restart Hermes, then:
    hermes mcp test suki

Rules of thumb for good tools:
  * One tool = one business question. Name it like a verb phrase:
      find_stockout_risks, list_overdue_tickets, draft_winback_list ...
  * A generic "run any SQL" tool scores low with the judges. Keep SQL inside
    your tools; expose clear parameters (branch_code, days, limit ...).
  * Return small, structured results (lists of dicts). The agent reasons
    better over 20 clean rows than 2,000 raw ones.
  * Write the docstring for the AI: it's what Hermes reads to decide when to
    call your tool and what to pass.
"""
import os
import sqlite3
from typing import Any

from mcp.server.fastmcp import FastMCP

# The database path is resolved relative to THIS file, not the working
# directory — Hermes launches MCP servers from its own folder.
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "store.db")

mcp = FastMCP("suki")  # rename to your team's server name


def query(sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Read helper: returns rows as dicts."""
    con = sqlite3.connect(f"file:{os.path.abspath(DB_PATH)}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params).fetchall()]
    finally:
        con.close()


def execute(sql: str, params: tuple = ()) -> int:
    """Write helper: returns affected row count. Use for tools that take action
    (e.g. resolve a ticket, create a purchase order). Reset data anytime with
    `python data/seed.py`."""
    con = sqlite3.connect(os.path.abspath(DB_PATH))
    try:
        cur = con.execute(sql, params)
        con.commit()
        return cur.rowcount
    finally:
        con.close()


# --------------------------------------------------------------------------
# Scaffolding — helps the agent (and you) explore. Keep or remove.
# --------------------------------------------------------------------------
@mcp.tool()
def describe_sandbox() -> dict:
    """Describe the Suki Mart sandbox: business context, the current date
    inside the data ("sandbox_now"), and every table with its columns and
    row count. Call this first when you need to understand the data."""
    info = {r["key"]: r["value"] for r in query("SELECT key, value FROM sandbox_info")}
    tables = {}
    for t in query("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        name = t["name"]
        cols = [f'{c["name"]} {c["type"]}' for c in query(f"PRAGMA table_info({name})")]
        count = query(f"SELECT COUNT(*) AS n FROM {name}")[0]["n"]
        tables[name] = {"rows": count, "columns": cols}
    return {"info": info, "tables": tables}


# --------------------------------------------------------------------------
# Example domain tool — shows the pattern. Replace it with your own.
# --------------------------------------------------------------------------
@mcp.tool()
def list_branches(city: str | None = None) -> list[dict]:
    """List Suki Mart branches with their code, type, city and whether they
    offer delivery. Optionally filter by city (e.g. "Quezon City")."""
    sql = "SELECT code, name, branch_type, city, area, has_delivery FROM branches"
    if city:
        return query(sql + " WHERE city = ? ORDER BY code", (city,))
    return query(sql + " ORDER BY code")


# TODO(team): add your domain tools below. For example:
#
# @mcp.tool()
# def your_tool_name(branch_code: str, days: int = 7) -> list[dict]:
#     """What business question this answers, and when the agent should use it."""
#     return query("SELECT ... WHERE ... ", (branch_code, days))


if __name__ == "__main__":
    mcp.run()
