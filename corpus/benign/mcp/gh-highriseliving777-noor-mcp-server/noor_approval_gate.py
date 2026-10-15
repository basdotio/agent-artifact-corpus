#!/usr/bin/env python3
"""
noor_approval_gate.py - Human-in-the-loop approval gate.

Sovereign implementation using SQLite only. No LLM, no external services.
Stores approval requests and lets a human (via API or CLI) approve/deny them.

Used by noor_governance_mcp.py as the "request_approval" tool.
"""

import json
import os
import sqlite3
import secrets
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
META_DIR = BASE_DIR / "_meta"
META_DIR.mkdir(exist_ok=True)
DB_PATH = META_DIR / "noor.db"


def _init_table():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS approval_requests (
            id TEXT PRIMARY KEY,
            action TEXT NOT NULL,
            thread_id TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL,
            resolved_at TEXT,
            resolved_by TEXT,
            reason TEXT
        )
    """)
    conn.commit()
    conn.close()


_init_table()


def run_approval_gate(action: str, thread_id: str = "") -> dict:
    """Create an approval request. Returns immediately with status=pending.

    A human must approve or deny via approve() or deny() before the
    action can proceed.
    """
    if not action:
        return {"status": "error", "result": "No action provided"}

    approval_id = "apr_" + secrets.token_hex(8)
    created_at = datetime.now(timezone.utc).isoformat()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO approval_requests (id, action, thread_id, status, created_at) VALUES (?, ?, ?, 'pending', ?)",
        (approval_id, action, thread_id or approval_id, created_at),
    )
    conn.commit()
    conn.close()

    return {
        "status": "pending",
        "approval_id": approval_id,
        "action": action,
        "created_at": created_at,
        "result": "Approval request created. Awaiting human decision.",
    }


def approve(approval_id: str, approved_by: str = "human", reason: str = "") -> dict:
    """Mark an approval as approved."""
    return _resolve(approval_id, "approved", approved_by, reason)


def deny(approval_id: str, denied_by: str = "human", reason: str = "") -> dict:
    """Mark an approval as denied."""
    return _resolve(approval_id, "denied", denied_by, reason)


def _resolve(approval_id: str, new_status: str, resolved_by: str, reason: str) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT status FROM approval_requests WHERE id = ?", (approval_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "Approval not found"}
    if row[0] != "pending":
        conn.close()
        return {"ok": False, "error": f"Already {row[0]}"}

    resolved_at = datetime.now(timezone.utc).isoformat()
    c.execute(
        "UPDATE approval_requests SET status = ?, resolved_at = ?, resolved_by = ?, reason = ? WHERE id = ?",
        (new_status, resolved_at, resolved_by, reason, approval_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True, "approval_id": approval_id, "status": new_status}


def get_pending() -> list:
    """Return all pending approval requests."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, action, created_at FROM approval_requests WHERE status = 'pending' ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "action": r[1], "created_at": r[2]} for r in rows]


def get_status(approval_id: str) -> dict:
    """Get the status of a single approval request."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, action, status, created_at, resolved_at, resolved_by, reason FROM approval_requests WHERE id = ?", (approval_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"error": "Approval not found"}
    return {
        "id": row[0],
        "action": row[1],
        "status": row[2],
        "created_at": row[3],
        "resolved_at": row[4],
        "resolved_by": row[5],
        "reason": row[6],
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "pending":
        print(json.dumps(get_pending(), indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "approve":
        print(json.dumps(approve(sys.argv[2]), indent=2))
    elif len(sys.argv) > 2 and sys.argv[1] == "deny":
        print(json.dumps(deny(sys.argv[2]), indent=2))
    else:
        result = run_approval_gate("Test action from CLI", "test_thread")
        print(json.dumps(result, indent=2))
