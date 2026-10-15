"""SQLite store.

Every durable fact lives here, never in the process. A tool opens a connection, does one
thing, and closes it, so any process with the same database file answers any request.

Every row carries its owner, and every read and write names the owner it acts for. A
handle alone is a name, not a capability: `get(owner, bookmark_id)` finds nothing when the
bookmark belongs to someone else, which is the same nothing it finds for a handle that was
never minted.
"""

import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from typing import Final

from . import paging
from .ids import new_bookmark_id
from .models import Bookmark

TABLE: Final = """
CREATE TABLE IF NOT EXISTS bookmarks (
    bookmark_id TEXT PRIMARY KEY,
    owner       TEXT NOT NULL,
    url         TEXT NOT NULL,
    title       TEXT,
    tags        TEXT NOT NULL,
    archived    INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
)
"""

INDEX: Final = """
CREATE INDEX IF NOT EXISTS bookmarks_owner_newest_first
    ON bookmarks (owner, created_at DESC, bookmark_id DESC)
"""

MAX_LIMIT: Final = 100


class _Unset:
    """Marker for "leave this field alone" in `update`."""


UNSET: Final = _Unset()


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds")


def normalize_tags(tags: list[str] | None) -> list[str]:
    """Lower-case, stripped, deduplicated, order kept."""
    seen: dict[str, None] = {}
    for tag in tags or []:
        cleaned = tag.strip().lower()
        if cleaned:
            seen.setdefault(cleaned, None)
    return list(seen)


def _row_to_bookmark(row: sqlite3.Row) -> Bookmark:
    return Bookmark(
        bookmark_id=row["bookmark_id"],
        url=row["url"],
        title=row["title"],
        tags=json.loads(row["tags"]),
        archived=bool(row["archived"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        with closing(self._connect()) as conn:
            conn.execute(TABLE)
            self._migrate(conn)
            conn.execute(INDEX)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        """A database from before owners gets the column, and every existing row is
        `anonymous`. Runs before the index is created, since the index names the column."""
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(bookmarks)")}
        if "owner" not in columns:
            conn.execute("ALTER TABLE bookmarks ADD COLUMN owner TEXT NOT NULL DEFAULT 'anonymous'")
            conn.execute("DROP INDEX IF EXISTS bookmarks_newest_first")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn

    def add(self, owner: str, url: str, title: str | None, tags: list[str] | None) -> Bookmark:
        now = _now()
        bookmark = Bookmark(
            bookmark_id=new_bookmark_id(),
            url=url,
            title=title,
            tags=normalize_tags(tags),
            archived=False,
            created_at=now,
            updated_at=now,
        )
        with closing(self._connect()) as conn:
            conn.execute(
                "INSERT INTO bookmarks VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    bookmark.bookmark_id,
                    owner,
                    bookmark.url,
                    bookmark.title,
                    json.dumps(bookmark.tags),
                    0,
                    now,
                    now,
                ),
            )
        return bookmark

    def get(self, owner: str, bookmark_id: str) -> Bookmark | None:
        with closing(self._connect()) as conn:
            row = conn.execute(
                "SELECT * FROM bookmarks WHERE owner = ? AND bookmark_id = ?",
                (owner, bookmark_id),
            ).fetchone()
        return _row_to_bookmark(row) if row else None

    def list_page(
        self,
        owner: str,
        *,
        tag: str | None,
        include_archived: bool,
        limit: int,
        cursor: str | None = None,
    ) -> tuple[list[Bookmark], str | None]:
        """One page, newest first, and the cursor for the next one or None on the last.

        The order, the strictly-after predicate, and the cursor's contents are one fact,
        and they live here: a caller passes a cursor through and never knows its shape.
        Fetches one row past the page to learn whether a next page exists; the cursor
        encodes the last row kept. Raises `paging.InvalidCursor` for a cursor that is not
        a position in this listing.
        """
        clauses = ["owner = ?"]
        params: list[object] = [owner]
        if not include_archived:
            clauses.append("archived = 0")
        if tag is not None:
            clauses.append("EXISTS (SELECT 1 FROM json_each(bookmarks.tags) WHERE value = ?)")
            params.append(tag.strip().lower())
        if cursor is not None:
            created_at, bookmark_id = paging.decode(cursor)
            clauses.append("(created_at, bookmark_id) < (?, ?)")
            params.extend([created_at, bookmark_id])
        where = f"WHERE {' AND '.join(clauses)}"
        params.append(limit + 1)
        with closing(self._connect()) as conn:
            rows = conn.execute(
                f"SELECT * FROM bookmarks {where} "
                "ORDER BY created_at DESC, bookmark_id DESC LIMIT ?",
                params,
            ).fetchall()
        page = rows[:limit]
        next_cursor = (
            paging.encode(page[-1]["created_at"], page[-1]["bookmark_id"])
            if len(rows) > limit
            else None
        )
        return [_row_to_bookmark(row) for row in page], next_cursor

    def update(
        self,
        owner: str,
        bookmark_id: str,
        *,
        title: str | None | _Unset = UNSET,
        tags: list[str] | _Unset = UNSET,
    ) -> Bookmark | None:
        sets = []
        params: list[object] = []
        if not isinstance(title, _Unset):
            sets.append("title = ?")
            params.append(title)
        if not isinstance(tags, _Unset):
            sets.append("tags = ?")
            params.append(json.dumps(normalize_tags(tags)))
        if not sets:
            return self.get(owner, bookmark_id)
        sets.append("updated_at = ?")
        params.extend([_now(), owner, bookmark_id])
        with closing(self._connect()) as conn:
            conn.execute(
                f"UPDATE bookmarks SET {', '.join(sets)} WHERE owner = ? AND bookmark_id = ?",
                params,
            )
        return self.get(owner, bookmark_id)

    def archive(self, owner: str, bookmark_id: str) -> Bookmark | None:
        with closing(self._connect()) as conn:
            conn.execute(
                "UPDATE bookmarks SET archived = 1, updated_at = ? "
                "WHERE owner = ? AND bookmark_id = ? AND archived = 0",
                (_now(), owner, bookmark_id),
            )
        return self.get(owner, bookmark_id)

    def delete(self, owner: str, bookmark_id: str) -> bool:
        with closing(self._connect()) as conn:
            cursor = conn.execute(
                "DELETE FROM bookmarks WHERE owner = ? AND bookmark_id = ?", (owner, bookmark_id)
            )
            return cursor.rowcount == 1
