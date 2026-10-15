"""Catalog schema and migrations.

SQLite, via the stdlib `sqlite3`, so the catalog costs the project nothing in
dependencies while still giving real queries. A JSON-file store would have been
simpler to write and worse to live with: the point of a catalog is asking
questions across twenty ingested repositories at once, and that is a query
problem.

Schema changes go through `MIGRATIONS`. The version is recorded in the database
from the first write, so an old catalog can always be identified and upgraded
rather than silently misread -- this is a user's accumulated library and it is
expected to outlive any particular release.

Design notes that matter downstream:

* Ids are content-addressed (see `store.content_id`), so re-ingesting the same
  repository at the same commit updates rows instead of duplicating them.
* Analyzer output is stored as JSON in `payload` columns rather than shredded
  into tables. The analyzers are plugins and their result shapes are theirs to
  change; freezing those shapes into DDL would make the catalog the thing that
  blocks an analyzer from evolving. What *is* promoted to real columns is only
  what the catalog itself needs to query and rank on.
"""

from __future__ import annotations

__all__ = ["SCHEMA_VERSION", "MIGRATIONS", "apply_migrations", "CatalogVersionError"]

SCHEMA_VERSION = 2


class CatalogVersionError(RuntimeError):
    """A catalog database is newer than this build of drydock understands.

    Raised instead of silently opening it: an old build reading a newer
    schema can misinterpret column meanings that changed between versions,
    and a wrong-but-plausible read is worse than a refusal to open.
    """

#: Applied in order; each entry is (version, list-of-statements).
MIGRATIONS: list[tuple[int, list[str]]] = [
    (
        1,
        [
            """
            CREATE TABLE IF NOT EXISTS meta (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS repos (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                source        TEXT NOT NULL,
                source_kind   TEXT NOT NULL DEFAULT 'path',
                commit_sha    TEXT,
                branch        TEXT,
                ingested_at   TEXT NOT NULL,
                drydock_ver   TEXT NOT NULL,
                languages     TEXT NOT NULL DEFAULT '[]',
                file_count    INTEGER NOT NULL DEFAULT 0,
                notes         TEXT,
                payload       TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_repos_name ON repos(name)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_repos_src ON repos(source, commit_sha)",
            """
            CREATE TABLE IF NOT EXISTS components (
                id            TEXT PRIMARY KEY,
                repo_id       TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                name          TEXT NOT NULL,
                kind          TEXT NOT NULL,
                contract      TEXT,
                selection     TEXT NOT NULL DEFAULT '{}',
                cohesion      REAL,
                verdict       TEXT,
                file_count    INTEGER NOT NULL DEFAULT 0,
                languages     TEXT NOT NULL DEFAULT '[]',
                external_deps TEXT NOT NULL DEFAULT '{}',
                content_path  TEXT,
                stored_at     TEXT,
                summary       TEXT,
                payload       TEXT NOT NULL DEFAULT '{}'
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_components_repo ON components(repo_id)",
            "CREATE INDEX IF NOT EXISTS idx_components_kind ON components(kind)",
            "CREATE INDEX IF NOT EXISTS idx_components_cohesion ON components(cohesion DESC)",
            """
            CREATE TABLE IF NOT EXISTS facts (
                id           TEXT PRIMARY KEY,
                repo_id      TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                principle    TEXT NOT NULL,
                name         TEXT NOT NULL,
                verdict      TEXT NOT NULL,
                summary      TEXT NOT NULL,
                derived      TEXT NOT NULL DEFAULT 'deterministic',
                evidence     TEXT NOT NULL DEFAULT '{}',
                recorded_at  TEXT NOT NULL
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_facts_repo ON facts(repo_id)",
            "CREATE INDEX IF NOT EXISTS idx_facts_principle ON facts(principle)",
            """
            CREATE TABLE IF NOT EXISTS capabilities (
                id           TEXT PRIMARY KEY,
                component_id TEXT NOT NULL REFERENCES components(id) ON DELETE CASCADE,
                repo_id      TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                module       TEXT NOT NULL,
                symbol       TEXT NOT NULL,
                kind         TEXT NOT NULL,
                signature    TEXT,
                doc          TEXT,
                lang         TEXT
            )
            """,
            "CREATE INDEX IF NOT EXISTS idx_caps_component ON capabilities(component_id)",
            "CREATE INDEX IF NOT EXISTS idx_caps_symbol ON capabilities(symbol)",
            # Full-text search over what a component exposes and what it is.
            # This is the query a user (or an agent) actually wants to make:
            # "do I already have something that parses TOML?"
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(
                subject_id UNINDEXED,
                subject_kind UNINDEXED,
                repo_id UNINDEXED,
                title,
                body,
                tokenize = "unicode61"
            )
            """,
        ],
    ),
    (
        2,
        [
            # A capability may belong to no component. Only ~26% of a real
            # repository's modules fall inside a detected component, so tying
            # every symbol to one made three quarters of an ingested project
            # unsearchable -- a user searching their own library for a module
            # they had just ingested got nothing back.
            "ALTER TABLE capabilities RENAME TO capabilities_v1",
            """
            CREATE TABLE capabilities (
                id           TEXT PRIMARY KEY,
                component_id TEXT REFERENCES components(id) ON DELETE CASCADE,
                repo_id      TEXT NOT NULL REFERENCES repos(id) ON DELETE CASCADE,
                module       TEXT NOT NULL,
                symbol       TEXT NOT NULL,
                kind         TEXT NOT NULL,
                signature    TEXT,
                doc          TEXT,
                lang         TEXT
            )
            """,
            """
            INSERT INTO capabilities
                (id, component_id, repo_id, module, symbol, kind, signature, doc, lang)
            SELECT id, component_id, repo_id, module, symbol, kind, signature, doc, lang
            FROM capabilities_v1
            """,
            "DROP TABLE capabilities_v1",
            "CREATE INDEX IF NOT EXISTS idx_caps_component ON capabilities(component_id)",
            "CREATE INDEX IF NOT EXISTS idx_caps_symbol ON capabilities(symbol)",
            "CREATE INDEX IF NOT EXISTS idx_caps_repo ON capabilities(repo_id)",
        ],
    ),
]


def apply_migrations(conn) -> int:
    """Bring `conn` up to `SCHEMA_VERSION`, returning the version applied.

    Raises `CatalogVersionError` if the database is *newer* than this build
    knows about. Without this check, opening a catalog written by a future
    drydock would silently succeed -- every migration is a no-op once
    `version <= current` -- and any column whose meaning changed since would
    be misread rather than rejected.
    """
    cur = conn.execute("PRAGMA user_version")
    current = cur.fetchone()[0]

    if current > SCHEMA_VERSION:
        raise CatalogVersionError(
            f"catalog schema is version {current}, but this build of "
            f"drydock only understands up to version {SCHEMA_VERSION}. "
            "Refusing to open it -- upgrade drydock before using this "
            "catalog, or point DRYDOCK_CATALOG at a different one."
        )

    for version, statements in MIGRATIONS:
        if version <= current:
            continue
        for statement in statements:
            conn.execute(statement)
        conn.execute(f"PRAGMA user_version = {version}")
        current = version

    conn.commit()
    return current
