import json

from aiosqlite import Connection


async def append_event(
    db: Connection,
    session_id: str,
    kind: str,
    payload: dict,
) -> None:
    """Append an event; SQLite serializes writers and the unique key protects ordering."""
    await db.execute(
        """INSERT INTO session_events (session_id, seq, kind, payload)
           SELECT ?, COALESCE(MAX(seq), 0) + 1, ?, ?
           FROM session_events WHERE session_id = ?""",
        (session_id, kind, json.dumps(payload, ensure_ascii=False), session_id),
    )
    await db.commit()


async def get_events(db: Connection, session_id: str) -> list[dict]:
    cur = await db.execute(
        "SELECT seq, kind, payload, created_at FROM session_events "
        "WHERE session_id = ? ORDER BY seq",
        (session_id,),
    )
    rows = await cur.fetchall()
    return [
        {
            "seq": row["seq"],
            "kind": row["kind"],
            "payload": json.loads(row["payload"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
