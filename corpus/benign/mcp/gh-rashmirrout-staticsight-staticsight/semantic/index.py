"""Incremental semantic index: scan, drift detection, (background) refresh, and the in-memory search matrix."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass, field

from ..config import Config, load_config, workspace_data_dir
from ..core.errors import StaticSightError
from ..core.paths import decode_source, split_lines
from ..engines.ctags import try_ctags_for_files
from ..engines.embedder import get_embedder, model_id, numpy_ok
from ..engines.git import head_sha
from ..engines.rg import rg_files
from ..engines.vector_store import SCHEMA_VERSION, IndexLock, VectorStore
from .chunker import chunk_file
from .files import FileStat, content_skip_reason, is_structural, language_of, pre_skip_reason

log = logging.getLogger("staticsight.semantic")

CHUNKER_VERSION = "1"
GROUP_FILES = 48   # files per transaction / progress step


@dataclass
class Drift:
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    deleted: list[str] = field(default_factory=list)
    stats: dict[str, FileStat] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.added) + len(self.changed) + len(self.deleted)


@dataclass
class BuildState:
    status: str = "idle"          # idle | building | failed
    phase: str = ""
    done: int = 0
    total: int = 0
    embedded: int = 0
    started: float = 0.0
    error: str = ""
    last_summary: str = ""


def text_hash(model: str, text: str) -> str:
    return hashlib.sha1((model + "\0" + text).encode("utf-8")).hexdigest()


def _priority(path: str) -> int:
    """Embedding order for big builds: code first (useful soonest), then docs, then everything else."""
    lang = language_of(path)
    if is_structural(lang):
        return 0
    if lang in ("markdown", "rst", "asciidoc", "text"):
        return 1
    return 2


class SemanticIndex:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        data_dir, self.data_dir_reason = workspace_data_dir(cfg)
        self.db_path = data_dir / "semantic.db"
        self.state = BuildState()
        self._store: VectorStore | None = None
        self._lock = asyncio.Lock()
        self._task: asyncio.Task | None = None
        self._matrix: tuple[str, list, object] | None = None  # (generation, rows, matrix)

    # ------------------------------------------------------------------ store
    @property
    def store(self) -> VectorStore:
        if self._store is None:
            self._store = VectorStore(self.db_path)
        return self._store

    def exists(self) -> bool:
        return self.db_path.exists() and bool(self.store.get_meta().get("updated_at"))

    def expected_meta(self) -> dict[str, str]:
        return {"schema_version": SCHEMA_VERSION, "model": model_id(self.cfg), "chunker": CHUNKER_VERSION}

    def compatible(self) -> bool:
        meta = self.store.get_meta()
        return all(meta.get(k) == v for k, v in self.expected_meta().items())

    # ------------------------------------------------------------------- scan
    async def scan(self) -> dict[str, FileStat]:
        paths = await rg_files(self.cfg, globs=())
        out: dict[str, FileStat] = {}
        root = self.cfg.workspace_root
        for p in paths:
            try:
                st = os.stat(root / p)
            except OSError:
                continue
            out[p] = FileStat(p, st.st_size, str(st.st_mtime_ns))
        return out

    async def drift(self) -> Drift:
        stats = await self.scan()
        known = self.store.files() if self.db_path.exists() else {}
        d = Drift(stats=stats)
        for p, st in stats.items():
            row = known.get(p)
            if row is None:
                d.added.append(p)
            elif row[0] != st.size or row[1] != st.mtime_ns:
                d.changed.append(p)
        d.deleted = sorted(p for p in known if p not in stats)
        d.added.sort()
        d.changed.sort()
        return d

    # ---------------------------------------------------------------- refresh
    @property
    def building(self) -> bool:
        return self._task is not None and not self._task.done()

    def start_background(self, full: bool = False) -> bool:
        """Start a background refresh unless one is running. Returns True if a new one was started."""
        if self.building:
            return False
        self._task = asyncio.get_running_loop().create_task(self._background(full))
        return True

    async def wait_for_background(self) -> None:
        if self._task is not None:
            await asyncio.shield(self._task)

    async def _background(self, full: bool) -> None:
        try:
            await self.refresh(full=full)
        except StaticSightError as exc:
            self.state.status, self.state.error = "failed", exc.message + (f" ({exc.hint})" if exc.hint else "")
            log.warning("semantic index refresh failed: %s", exc.message)
        except Exception as exc:  # background work must never crash the server
            self.state.status, self.state.error = "failed", repr(exc)
            log.exception("semantic index refresh failed")

    async def refresh(self, full: bool = False, progress=None) -> str:
        """Incremental (or full) refresh. Returns a one-line summary."""
        numpy_ok()
        async with self._lock:
            st = self.state
            st.status, st.error, st.done, st.total, st.embedded, st.started = "building", "", 0, 0, 0, time.time()
            st.phase = "loading model"

            def note(msg: str) -> None:
                st.phase = msg
                if progress:
                    progress(msg)

            try:
                embedder = await asyncio.to_thread(get_embedder, self.cfg, True, note)
                if full or not self.compatible():
                    self.store.reset(**self.expected_meta())
                    self._matrix = None
                note("scanning files")
                drift = await self.drift()
                if drift.total == 0:
                    self.store.set_meta(updated_at=f"{time.time():.0f}", head=await head_sha(self.cfg))
                    st.status, st.phase = "idle", ""
                    st.last_summary = "index already up to date"
                    return st.last_summary
                lock = IndexLock(self.db_path.with_suffix(".lock"))
                if not lock.acquire():
                    raise StaticSightError(
                        "Another process is refreshing this semantic index.", "Retry in a moment (see get_index_status)."
                    )
                try:
                    summary = await self._apply(drift, embedder, lock, note)
                finally:
                    lock.release()
                st.status, st.phase, st.last_summary = "idle", "", summary
                return summary
            except BaseException:
                if st.status == "building":
                    st.status = "failed" if not st.error else st.status
                raise

    async def _apply(self, drift: Drift, embedder, lock: IndexLock, note) -> str:
        store, st, cfg = self.store, self.state, self.cfg
        mid = model_id(cfg)
        store.delete_files(drift.deleted)
        todo = sorted(drift.added + drift.changed, key=lambda p: (_priority(p), p))  # code first, config last
        st.total = len(todo)
        known = store.files()
        reembedded = 0
        content_changed = 0
        for g in range(0, len(todo), GROUP_FILES):
            group = todo[g : g + GROUP_FILES]
            prepared: list[tuple] = []
            structural: list[str] = []
            for path in group:
                fs = drift.stats[path]
                full = cfg.workspace_root / path
                reason = pre_skip_reason(path, fs.size, cfg.semantic_max_file_kb)
                try:
                    data = b"" if reason else full.read_bytes()
                except OSError:
                    store.delete_files([path])
                    continue
                sha = hashlib.sha1(data).hexdigest() if data else ""
                old = known.get(path)
                if old is not None and not reason and old[2] == sha:
                    store.update_stat(path, fs.size, fs.mtime_ns)   # touched but identical content
                    continue
                language = language_of(path)
                content_changed += 1
                if not reason:
                    text = decode_source(data)
                    reason = content_skip_reason(data, text)
                if reason:
                    prepared.append((path, fs, sha, language, f"skipped:{reason}", None))
                    continue
                lines = split_lines(text)
                prepared.append((path, fs, sha, language, "indexed", lines))
                if is_structural(language):
                    structural.append(path)
            tags = await try_ctags_for_files(cfg, structural, generic=True) if structural else {}
            file_chunks: list[tuple] = []
            texts: dict[str, str] = {}
            for path, fs, sha, language, status, lines in prepared:
                chunks = chunk_file(path, lines, language, tags.get(path)) if lines is not None else []
                rows = []
                for c in chunks:
                    h = text_hash(mid, c.text)
                    texts.setdefault(h, c.text)
                    rows.append((c.start_line, c.end_line, c.language, c.kind, c.symbol, c.signature, c.part, h))
                file_chunks.append((path, fs, sha, language, status, rows))
            have = store.known_hashes(texts.keys())
            missing = [h for h in texts if h not in have]
            vectors: dict[str, bytes] = {}
            if missing:
                note(f"embedding {st.done}/{st.total} files")
                mat = await asyncio.to_thread(embedder.embed, [texts[h] for h in missing])
                for h, vec in zip(missing, mat):
                    vectors[h] = vec.astype("<f4").tobytes()
                reembedded += len(missing)
                st.embedded += len(missing)
            for path, fs, sha, language, status, rows in file_chunks:
                store.replace_file(path, fs.size, fs.mtime_ns, sha, language, status, rows,
                                   {r[7]: vectors[r[7]] for r in rows if r[7] in vectors})
            st.done = min(st.total, g + len(group))
            if not store.get_meta().get("updated_at"):
                store.set_meta(updated_at=f"{time.time():.0f}", **self.expected_meta())  # partial index is searchable
            self._matrix = None
            lock.heartbeat()
        store.gc_vectors()
        gen = int(store.get_meta().get("generation", "0")) + 1
        store.set_meta(generation=str(gen), updated_at=f"{time.time():.0f}", head=await head_sha(cfg), **self.expected_meta())
        self._matrix = None
        if content_changed == 0 and not drift.deleted:
            return "index already up to date"
        return (f"re-indexed {content_changed} changed file(s), removed {len(drift.deleted)}; "
                f"embedded {reembedded} new chunk(s)")

    # ----------------------------------------------------------------- search
    def matrix(self):
        gen = self.store.get_meta().get("generation", "0")
        if self._matrix is None or self._matrix[0] != gen:
            rows, mat = self.store.load_matrix()
            self._matrix = (gen, rows, mat)
        return self._matrix[1], self._matrix[2]

    async def ensure_fresh(self) -> tuple[str, bool]:
        """Drift policy for tool calls. Returns (freshness note, index_usable)."""
        cfg = self.cfg
        if not self.exists() or not self.compatible():
            if self.building:
                return self.progress_note(), False
            if not cfg.semantic_auto_refresh:
                return ("The semantic index has not been built yet (automatic refresh is disabled). "
                        "Call refresh_semantic_index."), False
            self.start_background(full=self.exists())
            return ("The semantic index is being built for the first time in the background "
                    f"({self.progress_note(short=True)}). Keyword results are shown meanwhile; call get_index_status "
                    "to follow progress and retry when it is ready."), False
        if self.building:
            return self.progress_note() + " Results come from the current (partly stale) index.", True
        d = await self.drift()
        if d.total == 0:
            return "Index is up to date.", True
        if not cfg.semantic_auto_refresh:
            return (f"⚠️ {d.total} file(s) changed since the last refresh (automatic refresh disabled): results may be "
                    "stale. Call refresh_semantic_index."), True
        if d.total <= cfg.semantic_auto_refresh_files:
            summary = await self.refresh()
            if summary == "index already up to date":
                return "Index is up to date.", True
            return f"Refreshed before searching: {summary}.", True
        self.start_background()
        return (f"⚠️ {d.total} files changed since the last refresh; a background refresh has started. Results come from "
                "the stale index; call get_index_status and retry for fresh results."), True

    def progress_note(self, short: bool = False) -> str:
        st = self.state
        if st.status != "building":
            return "starting" if self.building else "idle"
        pct = f"{(100 * st.done // st.total) if st.total else 0}%"
        base = f"{st.phase or 'building'}; {st.done}/{st.total} files ({pct}), {st.embedded} chunks embedded"
        if short:
            return base
        elapsed = time.time() - st.started
        eta = ""
        if st.done and st.total and st.done < st.total:
            eta = f", ~{int(elapsed / st.done * (st.total - st.done))}s left"
        return f"🏗️ Semantic index refresh in progress: {base}{eta}."


_indexes: dict[str, SemanticIndex] = {}


def get_semantic_index(cfg: Config | None = None) -> SemanticIndex:
    cfg = cfg or load_config()
    key = f"{cfg.workspace_root}|{cfg.cache_dir}|{cfg.data_dir_mode}|{cfg.embed_model}|{cfg.embed_model_dir}"
    idx = _indexes.get(key)
    if idx is None:
        idx = SemanticIndex(cfg)
        _indexes[key] = idx
    else:
        idx.cfg = cfg  # pick up changed knobs (auto-refresh, thresholds)
    return idx


def reset_semantic_indexes() -> None:
    for idx in _indexes.values():
        if idx._store is not None:
            idx._store.close()
    _indexes.clear()
