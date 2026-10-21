"""SQLite passage index built from an OKF snapshot: FTS5 keywords plus vectors.

Passages are cut from concept sections (never across them), with table
header rows repeated when a long table is split. Source locations come from
the snapshot's extraction metadata, not from the Markdown, so rebuilding the
index preserves citations.

When an embedder is available, each passage also gets a normalized vector
and search fuses keyword (BM25) and semantic rankings with reciprocal-rank
fusion. Without one, search is keyword-only.
"""

import json
import re
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Protocol, Sequence, Tuple

import numpy as np

from okf_mcp_server.src.knowledge.bundle import (
    is_stale,
    iter_concepts,
    lifecycle_status,
    split_frontmatter,
    split_sections,
    to_jsonable,
    trust_tier,
)

MAX_PASSAGE_CHARS = 1500
MAX_LIMIT = 20
# Candidate passages fetched per requested result, before keeping one per section.
CANDIDATES_PER_RESULT = 5
TOKENIZE = "unicode61 remove_diacritics 2"
# Reciprocal-rank fusion constant (the usual 60): damps the weight of top ranks.
RRF_K = 60
# In-memory (numpy) vector search up to this many vectors, sqlite-vec above.
# Measured: numpy needs ~3.6 KB/vector of process memory (300k -> 1.1 GB, too
# much for a 512 MiB pod) but is ~6x faster; sqlite-vec stays at ~40 MB
# (300k: 180 ms/query vs 32 ms). 50k keeps numpy peaks around 180 MB.
VECTOR_MEMORY_LIMIT = 50_000


def load_sqlite_vec(conn: sqlite3.Connection) -> bool:
    """Load the sqlite-vec extension into `conn`; False if unavailable."""
    try:
        import sqlite_vec

        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.enable_load_extension(False)
        return True
    except (ImportError, AttributeError, sqlite3.OperationalError):
        return False


def choose_vector_backend(count: int, requested: str = "auto") -> str:
    """`numpy` or `sqlite-vec` for an index with `count` vectors.

    `auto` uses numpy up to VECTOR_MEMORY_LIMIT and sqlite-vec above it when
    the extension is installed (otherwise numpy).

    Raises:
        ValueError: For an unknown backend, or sqlite-vec requested but missing.
    """
    if requested not in ("auto", "numpy", "sqlite-vec"):
        raise ValueError(f"unknown vector backend: {requested}")
    available = load_sqlite_vec(sqlite3.connect(":memory:"))
    if requested == "sqlite-vec" and not available:
        raise ValueError(
            "sqlite-vec requested but not installed (pip install sqlite-vec)"
        )
    if requested != "auto":
        return requested
    return "sqlite-vec" if count > VECTOR_MEMORY_LIMIT and available else "numpy"


class Encoder(Protocol):
    """What the index needs from an embedder (see `knowledge.embed.Embedder`)."""

    model_id: str

    def encode(self, texts: List[str], kind: str) -> np.ndarray:
        """Return one normalized float32 vector per text."""
        ...


_TOKEN = re.compile(r"\w+", re.UNICODE)


def search_form(text: str) -> str:
    """Text as the index sees it: NFKC-folded, so math italics and ligatures match.

    PDFs encode variables as Unicode math letters (`𝑅𝑒𝑤𝑎𝑟𝑑`) and words with
    ligatures (`ﬁ`). Folding is applied to indexed text and queries only;
    displayed excerpts keep the original characters.
    """
    return unicodedata.normalize("NFKC", text)


_SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE passages (
    id INTEGER PRIMARY KEY,
    concept_id TEXT NOT NULL,
    section TEXT NOT NULL,
    section_title TEXT NOT NULL,
    text TEXT NOT NULL,
    title TEXT NOT NULL,
    type TEXT,
    tags TEXT NOT NULL,
    status TEXT NOT NULL,
    stale_after TEXT,
    verified TEXT NOT NULL,
    source_id TEXT,
    source_uri TEXT,
    source_revision TEXT,
    location TEXT NOT NULL,
    access TEXT,
    fts_title TEXT NOT NULL,
    fts_section TEXT NOT NULL,
    fts_text TEXT NOT NULL
);
CREATE TABLE vectors (
    id INTEGER PRIMARY KEY REFERENCES passages(id),
    text_hash TEXT NOT NULL,
    v BLOB NOT NULL
);
CREATE VIRTUAL TABLE passages_fts USING fts5(
    fts_title, fts_section, fts_text,
    content='passages', content_rowid='id',
    tokenize='{tokenize}'
);
"""


class SearchIndexError(RuntimeError):
    """Raised when the search index is missing, unusable or lacks FTS5."""


def check_fts5(conn: Optional[sqlite3.Connection] = None) -> None:
    """Verify this SQLite build can create an FTS5 table.

    Raises:
        SearchIndexError: If FTS5 is not compiled in.
    """
    own = conn is None
    conn = conn or sqlite3.connect(":memory:")
    try:
        conn.execute("CREATE VIRTUAL TABLE temp.fts5_probe USING fts5(x)")
        conn.execute("DROP TABLE temp.fts5_probe")
    except sqlite3.OperationalError as e:
        raise SearchIndexError(
            f"SQLite {sqlite3.sqlite_version} lacks FTS5: {e}"
        ) from e
    finally:
        if own:
            conn.close()


def _split_long(text: str, limit: int = MAX_PASSAGE_CHARS) -> List[str]:
    """Split section text into passages at blank-line blocks.

    A table block larger than the limit is split by rows, repeating its
    header and separator rows at the top of every piece.
    """
    blocks = [b for b in re.split(r"\n\s*\n", text) if b.strip()]
    pieces: List[str] = []
    for block in blocks:
        lines = block.split("\n")
        is_table = (
            len(lines) > 2
            and lines[0].lstrip().startswith("|")
            and set(lines[1].replace("|", "").strip()) <= set("-: ")
        )
        if len(block) <= limit or not is_table:
            pieces.append(block)
            continue
        header, rows = lines[:2], lines[2:]
        chunk: List[str] = []
        for row in rows:
            if chunk and len("\n".join(header + chunk + [row])) > limit:
                pieces.append("\n".join(header + chunk))
                chunk = []
            chunk.append(row)
        if chunk:
            pieces.append("\n".join(header + chunk))

    passages: List[str] = []
    current = ""
    for piece in pieces:
        if current and len(current) + len(piece) + 2 > limit:
            passages.append(current)
            current = ""
        if len(piece) > limit and not piece.lstrip().startswith("|"):
            # ponytail: hard cut of an oversized paragraph; split on sentences if recall suffers.
            passages.extend(piece[i : i + limit] for i in range(0, len(piece), limit))
            continue
        current = f"{current}\n\n{piece}" if current else piece
    if current:
        passages.append(current)
    return passages


def _load_locations(extraction_dir: Path, source_id: Optional[str]) -> Dict[str, Any]:
    """Return {section_slug: location} from the durable extraction metadata."""
    if not source_id:
        return {}
    path = extraction_dir / f"{source_id}.json"
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {s["slug"]: s.get("location") or {} for s in data.get("sections", [])}


def load_vectors(db_path: Path, model_id: str) -> Dict[str, bytes]:
    """Vectors of a previous index keyed by embedded-text hash, if the model matches.

    Lets a rebuild embed only new or changed passages.
    """
    if not db_path.is_file():
        return {}
    conn = sqlite3.connect(f"{db_path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        row = conn.execute(
            "SELECT value FROM meta WHERE key='embedding_model'"
        ).fetchone()
        if not row or row[0] != model_id:
            return {}
        return dict(conn.execute("SELECT text_hash, v FROM vectors"))
    except sqlite3.OperationalError:
        return {}  # index from before semantic search
    finally:
        conn.close()


def build_index(
    bundle_root: Path,
    extraction_dir: Path,
    db_path: Path,
    snapshot_id: str,
    embedder: Optional[Encoder] = None,
    reuse: Optional[Dict[str, bytes]] = None,
    stats: Optional[Dict[str, int]] = None,
    vector_backend: str = "auto",
) -> int:
    """Build a fresh index file for one snapshot. Returns the passage count.

    With an `embedder`, every passage is also embedded; vectors in `reuse`
    (from `load_vectors`) are copied instead of recomputed. `stats`, when
    given, receives `embedded` and `vectors_reused` counts.
    """
    from okf_mcp_server.src.knowledge.embed import passage_text, text_hash

    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    try:
        check_fts5(conn)
        conn.executescript(_SCHEMA.format(tokenize=TOKENIZE))
        conn.execute("INSERT INTO meta VALUES ('snapshot_id', ?)", (snapshot_id,))
        count = 0
        for concept_id, path in iter_concepts(bundle_root):
            fm, body = split_frontmatter(path.read_text(encoding="utf-8"))
            sources = fm.get("sources") or []
            source = sources[0] if sources and isinstance(sources[0], dict) else {}
            locations = _load_locations(extraction_dir, source.get("id"))
            for section in split_sections(body):
                for text in _split_long(section.text):
                    if not text.strip():
                        # Title-only sections carry no citable evidence; every
                        # passage already indexes the concept title.
                        continue
                    conn.execute(
                        "INSERT INTO passages (concept_id, section, section_title, text, title,"
                        " type, tags, status, stale_after, verified, source_id, source_uri,"
                        " source_revision, location, access, fts_title, fts_section,"
                        " fts_text) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            concept_id,
                            section.slug,
                            section.title,
                            text,
                            str(fm.get("title") or concept_id),
                            fm.get("type"),
                            json.dumps(to_jsonable(fm.get("tags") or [])),
                            lifecycle_status(fm),
                            json.dumps(to_jsonable(fm.get("stale_after"))),
                            json.dumps(to_jsonable(fm.get("verified"))),
                            source.get("id"),
                            source.get("resource"),
                            fm.get("source_revision"),
                            json.dumps(locations.get(section.slug, {})),
                            json.dumps(fm["access"]) if "access" in fm else None,
                            search_form(str(fm.get("title") or concept_id)),
                            search_form(section.title),
                            search_form(text),
                        ),
                    )
                    count += 1
        conn.execute("INSERT INTO passages_fts(passages_fts) VALUES ('rebuild')")
        if embedder is not None:
            reuse = reuse or {}
            rows = conn.execute(
                "SELECT id, title, section_title, text FROM passages ORDER BY id"
            ).fetchall()
            texts = [passage_text(t, st, x) for _, t, st, x in rows]
            hashes = [text_hash(t) for t in texts]
            todo = [i for i, h in enumerate(hashes) if h not in reuse]
            fresh = (
                embedder.encode([texts[i] for i in todo], "passage") if todo else None
            )
            new = (
                {
                    hashes[i]: fresh[n].astype(np.float32).tobytes()
                    for n, i in enumerate(todo)
                }
                if fresh is not None
                else {}
            )
            conn.executemany(
                "INSERT INTO vectors VALUES (?,?,?)",
                [(rows[i][0], h, new.get(h) or reuse[h]) for i, h in enumerate(hashes)],
            )
            conn.execute(
                "INSERT INTO meta VALUES ('embedding_model', ?)", (embedder.model_id,)
            )
            backend = choose_vector_backend(len(rows), vector_backend)
            if backend == "sqlite-vec" and rows:
                load_sqlite_vec(conn)
                dim = (
                    len(conn.execute("SELECT v FROM vectors LIMIT 1").fetchone()[0])
                    // 4
                )
                conn.execute(
                    f"CREATE VIRTUAL TABLE vec USING vec0(embedding float[{int(dim)}] distance_metric=cosine)"
                )
                conn.execute(
                    "INSERT INTO vec(rowid, embedding) SELECT id, v FROM vectors"
                )
            conn.execute("INSERT INTO meta VALUES ('vector_backend', ?)", (backend,))
            if stats is not None:
                stats["embedded"] = len(todo)
                stats["vectors_reused"] = len(rows) - len(todo)
        conn.commit()
        return count
    finally:
        conn.close()


def fts_query(query: str) -> str:
    """Turn free text into a safe FTS5 query.

    Each whitespace-separated term becomes a quoted phrase of its word
    characters (so `SKU-4471` matches the adjacent tokens `sku 4471`), and
    terms are OR-ed and ranked by BM25. User punctuation and FTS operators
    are never passed through as query syntax.
    """
    phrases = []
    for term in query.split():
        tokens = _TOKEN.findall(term)
        if tokens:
            phrases.append('"' + " ".join(tokens) + '"')
    return " OR ".join(dict.fromkeys(phrases))


def format_location(location: Dict[str, Any]) -> str:
    """Human-readable location from extraction metadata; empty if unknown."""
    parts = []
    pages = location.get("pages") or []
    if pages:
        parts.append(
            f"page {pages[0]}" if len(pages) == 1 else f"pages {pages[0]}–{pages[-1]}"
        )
    if location.get("sheet"):
        parts.append(f"sheet {location['sheet']}")
    if location.get("section"):
        parts.append(f"section “{location['section']}”")
    if location.get("lines"):
        start, end = location["lines"]
        parts.append(f"lines {start}–{end}")
    return ", ".join(parts)


@lru_cache(maxsize=512)
def _allowed_ids(
    db_uri: str, snapshot_id: str, where: str, params: Tuple[Any, ...]
) -> FrozenSet[int]:
    """Passage IDs a filter allows, cached per immutable snapshot.

    The scan costs ~200 ms at 300k passages; callers repeat the same
    principals and filters, so later queries skip it. `where` is built only
    from fixed fragments with ? placeholders (see SearchIndex._filter_sql).
    """
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        sql = f"SELECT p.id FROM passages p WHERE 1 = 1{where}"  # nosec B608
        return frozenset(r[0] for r in conn.execute(sql, params))
    finally:
        conn.close()


@lru_cache(maxsize=4)
def _vector_matrix(db_uri: str, snapshot_id: str) -> Tuple[np.ndarray, np.ndarray]:
    """(passage ids, vectors) for one immutable snapshot index, cached per process."""
    conn = sqlite3.connect(db_uri, uri=True)
    try:
        rows = conn.execute("SELECT id, v FROM vectors ORDER BY id").fetchall()
    finally:
        conn.close()
    ids = np.array([r[0] for r in rows], dtype=np.int64)
    matrix = (
        np.frombuffer(b"".join(r[1] for r in rows), dtype=np.float32).reshape(
            len(rows), -1
        )
        if rows
        else np.zeros((0, 0), dtype=np.float32)
    )
    return ids, matrix


class SearchIndex:
    """Read-only access to one snapshot's index file."""

    def __init__(self, db_path: Path, embedder: Optional[Encoder] = None):
        """Open the index read-only; snapshots are immutable once published.

        With an `embedder` whose model matches the one the index was built
        with, search is hybrid; otherwise it is keyword-only.
        """
        if not db_path.is_file():
            raise SearchIndexError(f"search index not found: {db_path.name}")
        self._uri = f"{db_path.resolve().as_uri()}?mode=ro&immutable=1"
        self.conn = sqlite3.connect(self._uri, uri=True)
        self.conn.row_factory = sqlite3.Row
        self.embedder = (
            embedder
            if embedder and self.embedding_model() == embedder.model_id
            else None
        )

    def close(self) -> None:
        """Close the connection."""
        self.conn.close()

    def __enter__(self) -> "SearchIndex":
        """Context-manager entry."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Context-manager exit."""
        self.close()

    def _meta(self, key: str) -> str:
        row = self.conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return row[0] if row else ""

    def snapshot_id(self) -> str:
        """Snapshot ID recorded when the index was built."""
        return self._meta("snapshot_id")

    def embedding_model(self) -> str:
        """Embedding model the vectors were built with; empty if keyword-only."""
        return self._meta("embedding_model")

    @property
    def mode(self) -> str:
        """`hybrid` when semantic search is active, else `keyword`."""
        return "hybrid" if self.embedder else "keyword"

    def _filter_sql(
        self,
        type_: Optional[str],
        tags: Sequence[str],
        principals: Optional[FrozenSet[str]] = None,
        default_access: str = "deny",
    ) -> Tuple[str, List[Any]]:
        """SQL filter fragment (fixed text, `?` placeholders) and its parameters.

        `principals` None means a trusted caller: no access filter.
        """
        sql, params = "", []
        if type_:
            sql += " AND p.type = ?"
            params.append(type_)
        for tag in tags:
            sql += " AND EXISTS (SELECT 1 FROM json_each(p.tags) WHERE value = ?)"
            params.append(tag)
        if principals is not None:
            marks = ",".join("?" * len(principals))  # placeholders only
            # Principals are bound parameters; only "?" placeholders are interpolated.
            sql += (
                " AND ((p.access IS NULL AND ? = 'authenticated')"  # nosec B608
                f" OR EXISTS (SELECT 1 FROM json_each(p.access) WHERE value IN ({marks})))"
            )
            params += [default_access, *sorted(principals)]
        return sql, params

    def _keyword_ids(
        self, query: str, where: str, params: List[Any], pool: int
    ) -> List[int]:
        match = fts_query(search_form(query))
        if not match:
            return []
        # `where` holds only fixed fragments with ? placeholders (see _filter_sql);
        # every user value is a bound parameter.
        sql = (
            "SELECT p.id FROM passages_fts JOIN passages p ON p.id = passages_fts.rowid"  # nosec B608
            f" WHERE passages_fts MATCH ?{where}"
            " ORDER BY bm25(passages_fts, 5.0, 2.0, 1.0) LIMIT ?"
        )
        return [r[0] for r in self.conn.execute(sql, [match, *params, pool])]

    def _semantic_ids(
        self, query: str, where: str, params: List[Any], pool: int
    ) -> List[int]:
        """Nearest passages to the query among those the filters allow.

        Filters (type, tags, access) are applied before ranking, so a caller
        who may see only a small part of the corpus still gets `pool`
        candidates: numpy masks disallowed rows; sqlite-vec widens its k until
        enough allowed rows are found.
        """
        if self.embedder is None or not query.strip():
            return []
        allowed: Optional[FrozenSet[int]] = None
        if where:
            allowed = _allowed_ids(self._uri, self.snapshot_id(), where, tuple(params))
            if not allowed:
                return []
        vector = self.embedder.encode([query], "query")[0].astype(np.float32)
        if self._meta("vector_backend") == "sqlite-vec" and load_sqlite_vec(self.conn):
            total = self.conn.execute("SELECT count(*) FROM vectors").fetchone()[0]
            k = pool * 4
            while True:
                found = [
                    r[0]
                    for r in self.conn.execute(
                        "SELECT rowid FROM vec WHERE embedding MATCH ? AND k = ?",
                        (vector.tobytes(), min(k, total)),
                    )
                ]
                top = [i for i in found if allowed is None or i in allowed]
                if len(top) >= pool or k >= total:
                    return top[:pool]
                k *= 4
        ids, matrix = _vector_matrix(self._uri, self.snapshot_id())
        if not len(ids):
            return []
        scores = matrix @ vector
        if allowed is not None:
            scores = np.where(np.isin(ids, list(allowed)), scores, -np.inf)
        order = np.argsort(-scores)[:pool]
        return [int(ids[i]) for i in order if np.isfinite(scores[i])]

    def search(
        self,
        query: str,
        type_: Optional[str] = None,
        tags: Sequence[str] = (),
        limit: int = 5,
        principals: Optional[FrozenSet[str]] = None,
        default_access: str = "deny",
    ) -> List[Dict[str, Any]]:
        """Return up to `limit` ranked sections with trust and lifecycle signals.

        With `principals` (an untrusted caller), only passages whose access
        list contains one of them are candidates; unlabelled passages follow
        `default_access`. Filtering happens before ranking, so hidden
        documents never take a result slot.

        Keyword and (when available) semantic rankings are fused with
        reciprocal-rank fusion. Each section appears once, represented by its
        best passage, and deprecated concepts rank after current ones.
        Each result says whether it `matched_by` keyword, semantic or both.
        """
        limit = max(1, min(int(limit), MAX_LIMIT))
        # ponytail: fixed candidate pool; a section with more passages than the
        # pool could still crowd out others. Use a window query if that shows up.
        pool = limit * CANDIDATES_PER_RESULT
        where, params = self._filter_sql(type_, tags, principals, default_access)
        rankings = {
            "keyword": self._keyword_ids(query, where, params, pool),
            "semantic": self._semantic_ids(query, where, params, pool),
        }
        fused: Dict[int, float] = {}
        matched: Dict[int, List[str]] = {}
        for name, ranked in rankings.items():
            for rank, pid in enumerate(ranked):
                fused[pid] = fused.get(pid, 0.0) + 1.0 / (RRF_K + rank)
                matched.setdefault(pid, []).append(name)
        if not fused:
            return []
        marks = ",".join("?" * len(fused))
        rows = {
            r["id"]: r
            for r in self.conn.execute(
                f"SELECT * FROM passages WHERE id IN ({marks})",  # nosec B608 - "?" only
                list(fused),
            )
        }
        ordered = sorted(
            fused, key=lambda pid: (rows[pid]["status"] == "deprecated", -fused[pid])
        )
        results: List[Dict[str, Any]] = []
        seen = set()
        for pid in ordered:
            row = rows[pid]
            key = (row["concept_id"], row["section"])
            if key in seen:
                continue
            seen.add(key)
            if len(results) == limit:
                break
            fm = {
                "status": row["status"],
                "stale_after": json.loads(row["stale_after"]),
                "verified": json.loads(row["verified"]),
            }
            location = json.loads(row["location"])
            results.append(
                {
                    "concept_id": row["concept_id"],
                    "title": row["title"],
                    "type": row["type"],
                    "section": row["section"],
                    "section_title": row["section_title"],
                    "excerpt": row["text"][:MAX_PASSAGE_CHARS],
                    "excerpt_truncated": len(row["text"]) > MAX_PASSAGE_CHARS,
                    "status": row["status"],
                    "trust_tier": trust_tier(fm),
                    "stale": is_stale(fm),
                    "matched_by": "both" if len(matched[pid]) == 2 else matched[pid][0],
                    "source": {
                        "id": row["source_id"],
                        "uri": row["source_uri"],
                        "revision": row["source_revision"],
                        "location": location,
                        "location_text": format_location(location),
                    },
                }
            )
        return results
