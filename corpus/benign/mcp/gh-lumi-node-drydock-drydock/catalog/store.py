"""The catalog API.

Everything a frontend needs, and nothing that assumes which frontend it is.
A CLI opens a `Catalog`, asks a question and exits; a GUI holds one open and
polls; an agent reaches it through MCP. All three see the same records, and
none of them get a database handle -- queries return plain dataclasses, so a
caller can hold results as long as it likes and hand them onward as JSON.

Two properties worth stating outright, because they shape everything else:

**Idempotent.** Ids are content-addressed. Ingesting the same repository at the
same commit twice updates the existing rows; it does not accumulate
near-duplicates that a user then has to weed. This is a library that gets added
to over months, so "run it again" has to be safe.

**Non-destructive by default.** Nothing removes rows or stored content unless
asked. `forget()` exists and says what it will delete before doing it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .models import (
    CapabilityRecord,
    ComponentRecord,
    FactRecord,
    RepoRecord,
    SearchHit,
    utc_now,
)
from .schema import SCHEMA_VERSION, CatalogVersionError, apply_migrations

__all__ = ["Catalog", "content_id", "default_root", "CatalogVersionError"]

#: Statements are batched in chunks this large to stay well under every real
#: SQLite build's SQLITE_MAX_VARIABLE_NUMBER (the oldest common default is
#: 999), even for a component with tens of thousands of capabilities.
_SQL_CHUNK = 500

#: Substrings of `sqlite3.OperationalError` messages worth a bounded retry.
#: `PRAGMA busy_timeout` already makes SQLite itself retry SQLITE_BUSY before
#: Python ever sees it, but under real concurrent load -- proven with two OS
#: processes, one doing `search()` while the other ingests -- the FTS5
#: `search` table's shadow-table writes still surface an occasional lock
#: error past that. This is a short backoff on top, not a replacement.
_LOCK_MARKERS = ("database is locked", "database is busy")

#: Overridable so a project can pin its own library, and so tests never touch
#: the real one.
ENV_ROOT = "DRYDOCK_CATALOG"


def default_root() -> Path:
    """Where a user's library lives unless told otherwise."""
    override = os.environ.get(ENV_ROOT)
    if override:
        return Path(override).expanduser()
    return Path.home() / ".drydock"


def content_id(kind: str, *parts: object) -> str:
    """Stable id derived from what a thing *is*, not when it was inserted.

    Same repository at the same commit yields the same id on any machine, so
    ids survive being written down, shared, or re-derived after the database is
    rebuilt.
    """
    digest = hashlib.sha256()
    digest.update(kind.encode())
    for part in parts:
        digest.update(b"\x1f")
        digest.update(str(part).encode())
    return f"{kind[:4]}_{digest.hexdigest()[:20]}"


class Catalog:
    """A user's accumulated library of ingested repositories and components."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root).expanduser() if root else default_root()
        self.components_dir = self.root / "components"
        self.db_path = self.root / "catalog.db"
        self._conn: sqlite3.Connection | None = None

    # -- lifecycle ---------------------------------------------------------

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            try:
                self.root.mkdir(parents=True, exist_ok=True)
            except FileExistsError as exc:
                # mkdir(exist_ok=True) only tolerates an existing *directory*;
                # a stray file at the catalog root raises this same error
                # whether it's Python or the OS reporting it, so translate it
                # into something that says what's actually wrong.
                raise NotADirectoryError(
                    f"catalog root exists but is not a directory: {self.root}"
                ) from exc
            try:
                self.components_dir.mkdir(parents=True, exist_ok=True)
            except OSError:
                # May be a read-only catalog directory. That only matters if
                # something tries to store component content into it; a
                # reader should still be able to open the database below.
                pass
            self._conn = self._open_db()
        return self._conn

    def _open_db(self) -> sqlite3.Connection:
        """Open `catalog.db`, read-write if possible, read-only otherwise.

        WAL mode needs to create `-wal`/`-shm` sidecar files, which is the
        first thing that actually requires write access to the directory --
        so a catalog whose directory has gone read-only (a shared mount, a
        library someone else owns) fails right here, not lazily on some
        later query. When that happens, and there is already a database to
        read, fall back to an explicit read-only connection instead of
        refusing outright: a GUI browsing a catalog it can't write to is a
        real, intended use, not an error.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            # WAL so a GUI can read while a CLI ingest is writing.
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA busy_timeout = 5000")
            apply_migrations(conn)
            return conn
        except sqlite3.OperationalError as exc:
            if "readonly database" not in str(exc).lower() or not self.db_path.exists():
                raise
            original = exc

        # A WAL-mode database -- and `catalog.db` always is one, once opened
        # read-write even once -- needs to create its `-shm` index file to be
        # opened at all, even purely for reading: the wal-index is a shared,
        # writable structure by design, not an implementation accident. A
        # plain `mode=ro` URI still hits that and fails exactly like above.
        # `immutable=1` skips it, but only reads the main database file, so
        # it is only correct here when there is no unreplayed WAL data to
        # miss -- i.e. the database was cleanly checkpointed (normal on
        # close()) before the directory went read-only. If a `-wal` file
        # with content is still sitting there, treating this database as
        # immutable would silently return a stale snapshot, which is worse
        # than refusing to open it.
        wal_file = self.db_path.with_name(self.db_path.name + "-wal")
        if wal_file.exists() and wal_file.stat().st_size > 0:
            raise original
        conn = sqlite3.connect(f"file:{self.db_path}?mode=ro&immutable=1", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        apply_migrations(conn)
        return conn

    # -- transient-lock retry ----------------------------------------------
    #
    # A defensive layer on top of `PRAGMA busy_timeout`, not a substitute for
    # it: see `_LOCK_MARKERS` above. Every statement retried here is a single
    # already-atomic SQLite operation, so retrying it never double-applies a
    # write that partially succeeded.

    def _retry_locked(self, fn):
        attempts, base_delay = 6, 0.05
        last: sqlite3.OperationalError | None = None
        for attempt in range(attempts):
            try:
                return fn()
            except sqlite3.OperationalError as exc:
                if not any(marker in str(exc).lower() for marker in _LOCK_MARKERS):
                    raise
                last = exc
                if attempt < attempts - 1:
                    time.sleep(base_delay * (2 ** attempt))
        assert last is not None
        raise last

    def _execute(self, sql: str, args: Sequence[Any] = ()) -> sqlite3.Cursor:
        return self._retry_locked(lambda: self.conn.execute(sql, args))

    def _executemany(self, sql: str, rows: Sequence[Sequence[Any]]) -> sqlite3.Cursor:
        rows = list(rows)
        return self._retry_locked(lambda: self.conn.executemany(sql, rows))

    def _query_all(self, sql: str, args: Sequence[Any] = ()) -> list[sqlite3.Row]:
        # Fetching is inside the retried callable, not chained after it: the
        # lock observed in practice can surface while pulling rows just as
        # readily as at statement-start, and a retry that only covers
        # `execute()` would miss it.
        return self._retry_locked(lambda: self.conn.execute(sql, args).fetchall())

    def _query_one(self, sql: str, args: Sequence[Any] = ()) -> sqlite3.Row | None:
        return self._retry_locked(lambda: self.conn.execute(sql, args).fetchone())

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None

    def __enter__(self) -> Catalog:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        conn = self.conn
        try:
            yield conn
            # The exclusive lock a writer needs is typically acquired here,
            # at COMMIT, not on the individual statements beforehand -- so
            # this is the point actually worth retrying on lock contention,
            # confirmed by real concurrent-process testing (see
            # `_retry_locked`).
            self._retry_locked(conn.commit)
        except Exception:
            conn.rollback()
            raise

    # -- writing -----------------------------------------------------------

    def put_repo(
        self,
        *,
        name: str,
        source: str,
        source_kind: str = "path",
        commit_sha: str | None = None,
        branch: str | None = None,
        languages: Sequence[str] = (),
        file_count: int = 0,
        notes: str | None = None,
        payload: dict[str, Any] | None = None,
        drydock_ver: str = "",
    ) -> RepoRecord:
        """Insert or update a repository at a commit."""
        rid = content_id("repo", source, commit_sha or "")
        record = RepoRecord(
            id=rid,
            name=name,
            source=source,
            source_kind=source_kind,  # type: ignore[arg-type]
            commit_sha=commit_sha,
            branch=branch,
            ingested_at=utc_now(),
            drydock_ver=drydock_ver,
            languages=tuple(sorted(languages)),
            file_count=file_count,
            notes=notes,
            payload=payload or {},
        )
        with self.transaction():
            self._execute(
                """
                INSERT INTO repos (id, name, source, source_kind, commit_sha, branch,
                                   ingested_at, drydock_ver, languages, file_count,
                                   notes, payload)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, branch=excluded.branch,
                    ingested_at=excluded.ingested_at, drydock_ver=excluded.drydock_ver,
                    languages=excluded.languages, file_count=excluded.file_count,
                    notes=COALESCE(excluded.notes, repos.notes),
                    payload=excluded.payload
                """,
                (rid, name, source, source_kind, commit_sha, branch,
                 record.ingested_at, drydock_ver, json.dumps(record.languages),
                 file_count, notes, json.dumps(record.payload)),
            )
            self._index(rid, "repo", rid, name,
                        f"{source} {' '.join(record.languages)} {notes or ''}")
        return record

    def put_component(
        self,
        *,
        repo_id: str,
        name: str,
        kind: str,
        contract: str | None = None,
        selection: dict[str, Any] | None = None,
        cohesion: float | None = None,
        verdict: str | None = None,
        file_count: int = 0,
        languages: Sequence[str] = (),
        external_deps: dict[str, list[str]] | None = None,
        summary: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> ComponentRecord:
        cid = content_id("comp", repo_id, kind, contract or name)
        record = ComponentRecord(
            id=cid, repo_id=repo_id, name=name, kind=kind,  # type: ignore[arg-type]
            contract=contract, selection=selection or {}, cohesion=cohesion,
            verdict=verdict, file_count=file_count,
            languages=tuple(sorted(languages)), external_deps=external_deps or {},
            summary=summary, payload=payload or {},
        )
        with self.transaction():
            self._execute(
                """
                INSERT INTO components (id, repo_id, name, kind, contract, selection,
                                        cohesion, verdict, file_count, languages,
                                        external_deps, summary, payload)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, selection=excluded.selection,
                    cohesion=excluded.cohesion, verdict=excluded.verdict,
                    file_count=excluded.file_count, languages=excluded.languages,
                    external_deps=excluded.external_deps, summary=excluded.summary,
                    payload=excluded.payload
                """,
                (cid, repo_id, name, kind, contract, json.dumps(record.selection),
                 cohesion, verdict, file_count, json.dumps(record.languages),
                 json.dumps(record.external_deps), summary,
                 json.dumps(record.payload)),
            )
            self._index(cid, "component", repo_id, name,
                        f"{contract or ''} {summary or ''} {' '.join(record.languages)}")
        return record

    def store_component_content(self, component_id: str, tree: Path | str) -> Path:
        """Copy an extracted tree into the catalog and record where it went.

        Copied rather than referenced, so the library keeps working when the
        source repository moves, is deleted, or drifts to another commit. A
        library of pointers into other people's checkouts is a bookmark list.
        """
        source = Path(tree).resolve()
        if not source.is_dir():
            raise NotADirectoryError(f"not a directory: {source}")

        # `component_id` is meant to be a single content-addressed path
        # segment (see `content_id`), never a path. Reject anything that
        # could turn `components_dir / component_id` into a path outside the
        # catalog -- a path separator, or a literal "." / ".." segment --
        # before it ever reaches the filesystem. Checked on the raw id
        # rather than only after resolving, so a component_id that merely
        # *looks* safe once symlinks are resolved is still refused.
        if not component_id or component_id in (".", ".."):
            raise ValueError(f"invalid component id: {component_id!r}")
        if "/" in component_id or os.sep in component_id or (
            os.altsep and os.altsep in component_id
        ):
            raise ValueError(f"invalid component id: {component_id!r}")

        dest = self.components_dir / component_id
        resolved = dest.resolve()
        if resolved.parent != self.components_dir.resolve():
            raise ValueError(f"component id escapes the catalog: {component_id!r}")

        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(source, dest)

        rel = dest.relative_to(self.root).as_posix()
        with self.transaction():
            self._execute(
                "UPDATE components SET content_path = ?, stored_at = ? WHERE id = ?",
                (rel, utc_now(), component_id),
            )
        return dest

    def put_fact(
        self, *, repo_id: str, principle: str, name: str, verdict: str,
        summary: str, derived: str = "deterministic",
        evidence: dict[str, Any] | None = None,
    ) -> FactRecord:
        fid = content_id("fact", repo_id, principle)
        record = FactRecord(
            id=fid, repo_id=repo_id, principle=principle, name=name,
            verdict=verdict, summary=summary, derived=derived,
            evidence=evidence or {}, recorded_at=utc_now(),
        )
        with self.transaction():
            self._execute(
                """
                INSERT INTO facts (id, repo_id, principle, name, verdict, summary,
                                   derived, evidence, recorded_at)
                VALUES (?,?,?,?,?,?,?,?,?)
                ON CONFLICT(id) DO UPDATE SET
                    verdict=excluded.verdict, summary=excluded.summary,
                    derived=excluded.derived, evidence=excluded.evidence,
                    recorded_at=excluded.recorded_at
                """,
                (fid, repo_id, principle, name, verdict, summary, derived,
                 json.dumps(record.evidence), record.recorded_at),
            )
            self._index(fid, "fact", repo_id, name, summary)
        return record

    def put_capabilities(
        self, component_id: str | None, repo_id: str, items: Iterable[dict[str, Any]]
    ) -> int:
        """Record exposed symbols, replacing the previous set for this owner.

        `component_id` may be None, meaning "part of the repository but not
        inside any detected component". Most of a real project is in that
        state -- only about a quarter of modules fall inside a seam or cluster
        -- and without it three quarters of an ingested repository was
        invisible to search.
        """
        rows = []
        for item in items:
            symbol = str(item.get("symbol", "")).strip()
            if not symbol:
                continue
            module = str(item.get("module", ""))
            rows.append((
                content_id("cap", repo_id, component_id or "-", module, symbol),
                component_id, repo_id, module, symbol,
                str(item.get("kind", "symbol")),
                item.get("signature"), item.get("doc"), item.get("lang"),
            ))
        with self.transaction():
            # Capture every capability id this component *used to* have
            # before replacing them. Re-ingesting a component whose symbol
            # set shrank (a function removed at a later commit) must drop
            # the search entries for the vanished symbols too, not just the
            # ones that survived -- otherwise `search()` keeps surfacing a
            # capability id that no longer exists in `capabilities` at all.
            # Scoped by repo as well as component. `component_id IS NULL`
            # alone matches the unowned capabilities of EVERY repository, so
            # ingesting one project silently deleted another's.
            stale_ids = [
                r[0] for r in self._execute(
                    "SELECT id FROM capabilities "
                    "WHERE component_id IS ? AND repo_id = ?",
                    (component_id, repo_id),
                )
            ]
            self._execute(
                "DELETE FROM capabilities WHERE component_id IS ? AND repo_id = ?",
                (component_id, repo_id),
            )
            self._executemany(
                """INSERT OR REPLACE INTO capabilities
                   (id, component_id, repo_id, module, symbol, kind, signature, doc, lang)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                rows,
            )
            # Batched rather than one DELETE+INSERT pair per capability: on
            # a component with thousands of symbols the per-row form spends
            # nearly all its time on individual FTS5 shadow-table round
            # trips (measured: ~9s for 15k symbols, vs ~0.03s batched).
            self._delete_search_ids(stale_ids)
            self._index_many([
                (row[0], "capability", repo_id, row[4],
                 f"{row[3]} {row[6] or ''} {row[7] or ''}")
                for row in rows
            ])
        return len(rows)

    # -- reading -----------------------------------------------------------

    def repos(self, *, name: str | None = None, limit: int = 0) -> list[RepoRecord]:
        sql = "SELECT * FROM repos"
        args: list[Any] = []
        if name:
            sql += " WHERE name LIKE ?"
            args.append(f"%{name}%")
        sql += " ORDER BY ingested_at DESC"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [_repo(r) for r in self._query_all(sql, args)]

    def repo(self, repo_id: str) -> RepoRecord | None:
        row = self._query_one("SELECT * FROM repos WHERE id = ?", (repo_id,))
        return _repo(row) if row else None

    def components(
        self, *, repo_id: str | None = None, kind: str | None = None,
        language: str | None = None, min_cohesion: float | None = None,
        stored_only: bool = False, limit: int = 0,
    ) -> list[ComponentRecord]:
        sql = "SELECT * FROM components WHERE 1=1"
        args: list[Any] = []
        if repo_id:
            sql += " AND repo_id = ?"; args.append(repo_id)
        if kind:
            sql += " AND kind = ?"; args.append(kind)
        if language:
            sql += " AND languages LIKE ?"; args.append(f'%"{language}"%')
        if min_cohesion is not None:
            sql += " AND cohesion >= ?"; args.append(min_cohesion)
        if stored_only:
            sql += " AND content_path IS NOT NULL"
        sql += " ORDER BY cohesion DESC NULLS LAST, name"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [_component(r) for r in self._query_all(sql, args)]

    def component(self, component_id: str) -> ComponentRecord | None:
        row = self._query_one("SELECT * FROM components WHERE id = ?", (component_id,))
        return _component(row) if row else None

    def facts(self, *, repo_id: str | None = None,
              principle: str | None = None, verdict: str | None = None) -> list[FactRecord]:
        sql = "SELECT * FROM facts WHERE 1=1"
        args: list[Any] = []
        if repo_id:
            sql += " AND repo_id = ?"; args.append(repo_id)
        if principle:
            sql += " AND principle = ?"; args.append(principle)
        if verdict:
            sql += " AND verdict = ?"; args.append(verdict)
        sql += " ORDER BY principle"
        return [_fact(r) for r in self._query_all(sql, args)]

    def capabilities(self, *, component_id: str | None = None,
                     symbol: str | None = None, limit: int = 0) -> list[CapabilityRecord]:
        sql = "SELECT * FROM capabilities WHERE 1=1"
        args: list[Any] = []
        if component_id:
            sql += " AND component_id = ?"; args.append(component_id)
        if symbol:
            sql += " AND symbol LIKE ?"; args.append(f"%{symbol}%")
        sql += " ORDER BY module, symbol"
        if limit:
            sql += f" LIMIT {int(limit)}"
        return [_capability(r) for r in self._query_all(sql, args)]

    def search(self, query: str, *, kind: str | None = None,
               limit: int = 25) -> list[SearchHit]:
        """Full-text search across repos, components, capabilities and facts.

        This is the question the catalog exists to answer: "do I already have
        something that does X?"
        """
        if not query.strip():
            return []
        sql = (
            "SELECT subject_id, subject_kind, repo_id, title, "
            "       snippet(search, 4, '', '', '…', 12) AS snip, rank "
            "FROM search WHERE search MATCH ?"
        )
        args: list[Any] = [_fts_query(query)]
        if kind:
            sql += " AND subject_kind = ?"; args.append(kind)
        sql += f" ORDER BY rank LIMIT {max(int(limit) * 4, int(limit) + 20)}"
        try:
            rows = self._query_all(sql, args)
        except sqlite3.OperationalError:
            return []   # malformed FTS expression: no results, not a crash
        # Collapse hits that are the same thing seen twice. A file can belong
        # to more than one component -- a seam and a cluster that overlaps it --
        # so its symbols are indexed once per component. That is correct in the
        # data model ("this component exposes X") but reads as a broken search
        # when the same name comes back three times. Dedupe on what a reader
        # can actually distinguish, keeping the best-ranked instance.
        seen: set[tuple[str, str, str, str]] = set()
        hits: list[SearchHit] = []
        for r in rows:
            snippet = (r["snip"] or "").strip()
            key = (r["subject_kind"], r["repo_id"], r["title"], snippet)
            if key in seen:
                continue
            seen.add(key)
            hits.append(
                SearchHit(
                    subject_id=r["subject_id"], subject_kind=r["subject_kind"],
                    repo_id=r["repo_id"], title=r["title"],
                    snippet=snippet, rank=float(r["rank"] or 0.0),
                )
            )
        return hits[:limit]

    def stats(self) -> dict[str, Any]:
        one = lambda q: self._query_one(q)[0]  # noqa: E731
        return {
            "root": str(self.root),
            "schema_version": one("PRAGMA user_version"),
            "repos": one("SELECT COUNT(*) FROM repos"),
            "components": one("SELECT COUNT(*) FROM components"),
            "components_stored": one(
                "SELECT COUNT(*) FROM components WHERE content_path IS NOT NULL"),
            "facts": one("SELECT COUNT(*) FROM facts"),
            "capabilities": one("SELECT COUNT(*) FROM capabilities"),
            "languages": sorted({
                lang
                for (raw,) in self._query_all("SELECT languages FROM repos")
                for lang in json.loads(raw or "[]")
            }),
        }

    # -- removal -----------------------------------------------------------

    def forget(self, repo_id: str, *, delete_content: bool = True) -> dict[str, int]:
        """Remove a repository and everything derived from it.

        Reports what it removed. Stored component trees are deleted only when
        asked, because they may be the only surviving copy of code whose source
        has since moved on.
        """
        components = self.components(repo_id=repo_id)
        removed_content = 0
        if delete_content:
            for comp in components:
                path = comp.path(self.root)
                if path and path.exists():
                    shutil.rmtree(path, ignore_errors=True)
                    removed_content += 1

        with self.transaction():
            ids = [c.id for c in components]
            for i in range(0, len(ids), _SQL_CHUNK):
                chunk = ids[i:i + _SQL_CHUNK]
                marks = ",".join("?" * len(chunk))
                self._execute(
                    f"DELETE FROM capabilities WHERE component_id IN ({marks})", chunk)
            self._delete_search_ids(ids)
            self._execute("DELETE FROM components WHERE repo_id = ?", (repo_id,))
            self._execute("DELETE FROM facts WHERE repo_id = ?", (repo_id,))
            self._execute("DELETE FROM search WHERE repo_id = ?", (repo_id,))
            self._execute("DELETE FROM repos WHERE id = ?", (repo_id,))

        return {
            "components": len(components),
            "content_trees_deleted": removed_content,
        }

    # -- internals ---------------------------------------------------------

    def _index(self, subject_id: str, subject_kind: str, repo_id: str,
               title: str, body: str) -> None:
        self._execute("DELETE FROM search WHERE subject_id = ?", (subject_id,))
        self._execute(
            "INSERT INTO search (subject_id, subject_kind, repo_id, title, body) "
            "VALUES (?,?,?,?,?)",
            # Identifiers are expanded into their words so a search for
            # "parser" finds `BaseParser`. See `split_identifier`.
            (subject_id, subject_kind, repo_id, title,
             f"{split_identifier(title)} {body}"),
        )

    def _delete_search_ids(self, subject_ids: Sequence[str]) -> None:
        """Batched `DELETE ... WHERE subject_id IN (...)`, chunked to stay
        under every real SQLite build's bound-parameter limit."""
        subject_ids = list(subject_ids)
        for i in range(0, len(subject_ids), _SQL_CHUNK):
            chunk = subject_ids[i:i + _SQL_CHUNK]
            marks = ",".join("?" * len(chunk))
            self._execute(f"DELETE FROM search WHERE subject_id IN ({marks})", chunk)

    def _index_many(self, entries: Sequence[tuple[str, str, str, str, str]]) -> None:
        """Batched insert for (subject_id, subject_kind, repo_id, title, body)
        rows. Callers are responsible for clearing any stale rows first --
        this only inserts.

        Identifier expansion happens HERE, not in the caller, so the batched
        path and the single-row path cannot disagree. They did briefly: the
        expansion was added to `_index` only, so component names became
        searchable by word while capability symbols -- the ones that actually
        answer "do I have something that parses TOML?" -- did not.
        """
        if entries:
            self._executemany(
                "INSERT INTO search (subject_id, subject_kind, repo_id, title, body) "
                "VALUES (?,?,?,?,?)",
                [
                    (sid, kind, rid, title, f"{split_identifier(title)} {body}")
                    for sid, kind, rid, title, body in entries
                ],
            )


def split_identifier(name: str) -> str:
    """Expand an identifier into its constituent words.

    `BaseParser` -> "BaseParser Base Parser", `parse_toml` -> "parse_toml parse
    toml", `HTTPServer` -> "HTTPServer HTTP Server".

    Without this the catalog cannot answer the question it exists for. FTS5
    tokenises on non-alphanumerics, so `BaseParser` is a single token and a
    search for "parser" matches nothing -- yet "do I already have something
    that parses TOML?" is precisely the query someone composing from their
    library will type. Identifiers are the data here, and identifiers are
    camelCase and snake_case far more often than they are prose.
    """
    if not name:
        return ""
    parts = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z]+|[a-z]+|\d+", name)
    words = [w for w in parts if len(w) > 1]
    return " ".join([name, *words]) if words else name


def _fts_query(raw: str) -> str:
    """Turn user input into a safe FTS5 expression.

    Users type `parse toml`, not `parse AND toml`, and typing a bare `-` or a
    stray quote should not raise. Each term is quoted and prefix-matched.
    """
    terms = [t for t in "".join(ch if ch.isalnum() or ch in "_-." else " "
                                for ch in raw).split() if t]
    return " AND ".join(f'"{t}"*' for t in terms) if terms else '""'


def _json(value: str | None, default):
    try:
        return json.loads(value) if value else default
    except (ValueError, TypeError):
        return default


def _repo(row) -> RepoRecord:
    return RepoRecord(
        id=row["id"], name=row["name"], source=row["source"],
        source_kind=row["source_kind"], commit_sha=row["commit_sha"],
        branch=row["branch"], ingested_at=row["ingested_at"],
        drydock_ver=row["drydock_ver"],
        languages=tuple(_json(row["languages"], [])),
        file_count=row["file_count"], notes=row["notes"],
        payload=_json(row["payload"], {}),
    )


def _component(row) -> ComponentRecord:
    return ComponentRecord(
        id=row["id"], repo_id=row["repo_id"], name=row["name"], kind=row["kind"],
        contract=row["contract"], selection=_json(row["selection"], {}),
        cohesion=row["cohesion"], verdict=row["verdict"],
        file_count=row["file_count"], languages=tuple(_json(row["languages"], [])),
        external_deps=_json(row["external_deps"], {}),
        content_path=row["content_path"], stored_at=row["stored_at"],
        summary=row["summary"], payload=_json(row["payload"], {}),
    )


def _fact(row) -> FactRecord:
    return FactRecord(
        id=row["id"], repo_id=row["repo_id"], principle=row["principle"],
        name=row["name"], verdict=row["verdict"], summary=row["summary"],
        derived=row["derived"], evidence=_json(row["evidence"], {}),
        recorded_at=row["recorded_at"],
    )


def _capability(row) -> CapabilityRecord:
    return CapabilityRecord(
        id=row["id"], component_id=row["component_id"], repo_id=row["repo_id"],
        module=row["module"], symbol=row["symbol"], kind=row["kind"],
        signature=row["signature"], doc=row["doc"], lang=row["lang"],
    )
