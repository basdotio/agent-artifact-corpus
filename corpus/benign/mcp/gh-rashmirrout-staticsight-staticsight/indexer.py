"""WorkspaceIndexer: builds/updates the GNU Global (gtags) index in the background.

Rules:
- If `WORKSPACE_ROOT/GTAGS` exists, the in-repo database is reused and refreshed with `global -u`.
- Otherwise the database lives in the per-repository data folder `<repo>/.staticsight/` (ignored by git through its own
  `.gitignore`); STATICSIGHT_DATA_DIR=cache moves it to the per-user cache, and a read-only repository falls back there.
  `STATICSIGHT_GTAGS_IN_REPO=1` (deprecated) builds it in the repository root instead (`gtags -i`).
- Missing `gtags`/`global` is not fatal: state becomes `unavailable` and graph tools fall back to ripgrep.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path

from .config import Config, load_config, workspace_data_dir
from .core.errors import StaticSightError
from .engines import gnu_global
from .engines.rg import rg_files

log = logging.getLogger("staticsight.indexer")


class WorkspaceIndexer:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.root = cfg.workspace_root
        self.state = "not_started"  # not_started | building | ready | failed | unavailable
        self.detail = ""
        self.db_path: Path | None = None
        self.last_built: float | None = None
        self.last_duration: float | None = None
        self._task: asyncio.Task | None = None
        self._lock = asyncio.Lock()

    # ---------------------------------------------------------------- public
    def start(self) -> asyncio.Task:
        """Kick off a background (re)index; returns the task (callers may await it)."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run())
        return self._task

    async def ensure_ready(self, grace_s: float = 2.0) -> bool:
        """True when the index can answer queries. Waits briefly for an in-flight build."""
        if self.state == "not_started":
            self.start()
        if self.state in ("building", "not_started") and self._task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=grace_s)
            except asyncio.TimeoutError:
                pass
        if self.state == "ready" and self.cfg.reindex_after_s and self.last_built:
            if time.time() - self.last_built > self.cfg.reindex_after_s and (self._task is None or self._task.done()):
                self.start()  # stale: refresh in the background, keep serving current data
        return self.state == "ready" or (self.state == "building" and self.last_built is not None)

    def env(self) -> dict[str, str]:
        env = {"GTAGSFORCECPP": "1", "GTAGSROOT": str(self.root)}
        if self.db_path is not None:
            env["GTAGSDBPATH"] = str(self.db_path)
        return env

    def status(self) -> dict[str, object]:
        age = None if self.last_built is None else int(time.time() - self.last_built)
        return {
            "state": self.state,
            "detail": self.detail,
            "db_path": str(self.db_path) if self.db_path else "",
            "age_s": age,
            "duration_s": None if self.last_duration is None else round(self.last_duration, 1),
        }

    # --------------------------------------------------------------- private
    def _cache_db_path(self) -> Path:
        return workspace_data_dir(self.cfg)[0]

    async def _run(self) -> None:
        async with self._lock:
            if not gnu_global.available():
                self.state = "unavailable"
                self.detail = "GNU Global (`gtags`/`global`) is not installed; graph tools use the ripgrep fallback."
                log.warning(self.detail)
                return
            prev_state = self.state
            self.state = "building"
            started = time.time()
            try:
                if (self.root / "GTAGS").exists():
                    self.db_path = self.root
                    res = await gnu_global.update_in_place(self.root, self.env())
                    action = "global -u (in-repo database)"
                else:
                    if self.cfg.gtags_in_repo:
                        self.db_path = self.root
                    else:
                        self.db_path = self._cache_db_path()
                        self.db_path.mkdir(parents=True, exist_ok=True)
                    files = await rg_files(self.cfg)
                    incremental = (self.db_path / "GTAGS").exists()
                    res, action = await gnu_global.build(self.root, self.db_path, self.env(), files, incremental)
                if res.returncode != 0:
                    raise StaticSightError(f"gtags exited with {res.returncode}: {res.stderr.strip()[:300]}")
                self.state = "ready"
                self.last_built = time.time()
                self.last_duration = self.last_built - started
                self.detail = f"Indexed via `{action}` in {self.last_duration:.1f}s."
                log.info(self.detail)
            except StaticSightError as exc:
                self.state = "ready" if prev_state == "ready" else "failed"
                self.detail = f"Indexing failed: {exc.message}"
                log.warning(self.detail)
            except Exception as exc:  # never let indexing kill the server
                self.state = "failed"
                self.detail = f"Indexing failed: {exc!r}"
                log.exception("indexing failed")


_indexers: dict[str, WorkspaceIndexer] = {}


def get_indexer(cfg: Config | None = None) -> WorkspaceIndexer:
    cfg = cfg or load_config()
    key = str(cfg.workspace_root)
    idx = _indexers.get(key)
    if idx is None:
        idx = WorkspaceIndexer(cfg)
        _indexers[key] = idx
    return idx


def reset_indexers() -> None:
    _indexers.clear()


def db_exists(idx: WorkspaceIndexer) -> bool:
    return idx.db_path is not None and os.path.exists(idx.db_path / "GTAGS")
