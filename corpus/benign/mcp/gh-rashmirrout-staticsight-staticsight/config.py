"""Runtime configuration, read from environment variables on every call so tests and clients can override it."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path

from .platform import current as current_platform

CPP_EXTENSIONS = (
    ".c", ".cc", ".cpp", ".cxx", ".c++", ".h", ".hh", ".hpp", ".hxx", ".h++", ".inl", ".ipp", ".tpp", ".tcc",
)
HEADER_EXTENSIONS = (".h", ".hh", ".hpp", ".hxx", ".h++", ".inl", ".ipp", ".tpp", ".tcc")
CPP_GLOBS = tuple(f"*{ext}" for ext in CPP_EXTENSIONS)

DEFAULT_EXCLUDES = (
    "**/.git/**",
    "**/build/**",
    "**/out/**",
    "**/third_party/**",
    "**/external/**",
    "**/node_modules/**",
    "*.pb.h",
    "*.pb.cc",
    "**/.staticsight/**",
)
DATA_DIR_NAME = ".staticsight"
_DATA_GITIGNORE = "# StaticSight data (indexes); safe to delete, rebuilt on demand. Ignores itself.\n*\n"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    workspace_root: Path
    max_results: int = 15
    max_chars: int = 6000
    review_max_chars: int = 16000
    timeout_s: int = 20
    cppcheck_timeout_s: int = 60
    base_ref: str = ""
    excludes: tuple[str, ...] = field(default=DEFAULT_EXCLUDES)
    gtags_in_repo: bool = False
    cache_dir: Path = Path(".")
    reindex_after_s: int = 300
    # semantic search
    embed_model: str = "jina-code"
    embed_model_dir: str = ""
    semantic_auto_refresh: bool = True
    semantic_auto_refresh_files: int = 200
    semantic_max_file_kb: int = 512
    semantic_allow_download: bool = True
    embed_batch: int = 16
    embed_threads: int = 0
    data_dir_mode: str = "repo"   # repo | cache | <absolute path>
    root_explicit: bool = False   # WORKSPACE_ROOT / --repo given (vs discovered from the current folder)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name, "").strip().lower()
    if not raw:
        return default
    return raw not in ("0", "false", "no", "off")


def find_repo_root(start: Path) -> Path:
    """Nearest folder at or above `start` holding `.staticsight/` or `.git` (a dir, or a file in worktrees); else `start`."""
    start = Path(os.path.realpath(start))
    for cand in (start, *start.parents):
        if (cand / DATA_DIR_NAME).is_dir() or (cand / ".git").exists():
            return cand
    return start


def load_config() -> Config:
    explicit = os.environ.get("WORKSPACE_ROOT")
    root = Path(os.path.realpath(Path(explicit).expanduser())) if explicit else find_repo_root(Path(os.getcwd()))
    extra = tuple(p.strip() for p in os.environ.get("STATICSIGHT_EXCLUDES", "").split(",") if p.strip())
    ignore_file = root / ".staticsightignore"
    if ignore_file.is_file():
        try:
            extra += tuple(
                ln.strip() for ln in ignore_file.read_text(errors="replace").splitlines()
                if ln.strip() and not ln.strip().startswith("#")
            )
        except OSError:
            pass
    cache = os.environ.get("STATICSIGHT_CACHE_DIR")
    return Config(
        workspace_root=root,
        root_explicit=bool(explicit),
        max_results=max(1, _int_env("STATICSIGHT_MAX_RESULTS", 15)),
        max_chars=max(500, _int_env("STATICSIGHT_MAX_CHARS", 6000)),
        review_max_chars=max(1000, _int_env("STATICSIGHT_REVIEW_MAX_CHARS", 16000)),
        timeout_s=max(1, _int_env("STATICSIGHT_TIMEOUT", 20)),
        cppcheck_timeout_s=max(1, _int_env("STATICSIGHT_CPPCHECK_TIMEOUT", 60)),
        base_ref=os.environ.get("STATICSIGHT_BASE_REF", "").strip(),
        excludes=DEFAULT_EXCLUDES + extra,
        gtags_in_repo=os.environ.get("STATICSIGHT_GTAGS_IN_REPO", "") in ("1", "true", "yes"),
        cache_dir=Path(cache).expanduser() if cache else current_platform().default_cache_dir(),
        reindex_after_s=max(0, _int_env("STATICSIGHT_REINDEX_SECONDS", 300)),
        embed_model=os.environ.get("STATICSIGHT_EMBED_MODEL", "").strip() or "jina-code",
        embed_model_dir=os.environ.get("STATICSIGHT_EMBED_MODEL_DIR", "").strip(),
        semantic_auto_refresh=_bool_env("STATICSIGHT_SEMANTIC_AUTO_REFRESH", True),
        semantic_auto_refresh_files=max(0, _int_env("STATICSIGHT_SEMANTIC_AUTO_REFRESH_FILES", 200)),
        semantic_max_file_kb=max(1, _int_env("STATICSIGHT_SEMANTIC_MAX_FILE_KB", 512)),
        semantic_allow_download=_bool_env("STATICSIGHT_SEMANTIC_ALLOW_DOWNLOAD", True),
        embed_batch=max(1, _int_env("STATICSIGHT_EMBED_BATCH", 16)),
        embed_threads=max(0, _int_env("STATICSIGHT_EMBED_THREADS", 0)),
        data_dir_mode=os.environ.get("STATICSIGHT_DATA_DIR", "").strip() or "repo",
    )


def workspace_cache_dir(cfg: Config) -> Path:
    """Per-workspace folder inside the per-user cache (the `cache` data mode, and the legacy location)."""
    digest = hashlib.sha1(current_platform().path_key(str(cfg.workspace_root)).encode()).hexdigest()[:16]
    return cfg.cache_dir / digest


def _ensure_repo_data_dir(d: Path) -> bool:
    """Create `<repo>/.staticsight/` with a self-ignoring .gitignore. False when the repo is not writable."""
    try:
        d.mkdir(exist_ok=True)
        gi = d / ".gitignore"
        if not gi.exists():
            gi.write_text(_DATA_GITIGNORE, encoding="utf-8")
        probe = d / f".write-test-{os.getpid()}-{os.urandom(4).hex()}"
        probe.write_text("x", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def workspace_data_dir(cfg: Config, create: bool = True) -> tuple[Path, str]:
    """Where per-repository data (GNU Global database, semantic index) lives, and why.

    Default: `<repo>/.staticsight/` (one index per clone/worktree; ignored by git through its own .gitignore).
    STATICSIGHT_DATA_DIR=cache keeps data in the per-user cache; any other value is an explicit folder.
    A read-only repository falls back to the per-user cache.
    """
    mode = cfg.data_dir_mode
    if mode == "cache":
        return workspace_cache_dir(cfg), "per-user cache (STATICSIGHT_DATA_DIR=cache)"
    if mode != "repo":
        # one sub-folder per repository, so a user-wide setting never mixes indexes of different repositories
        return Path(mode).expanduser().resolve() / workspace_cache_dir(cfg).name, "STATICSIGHT_DATA_DIR"
    d = cfg.workspace_root / DATA_DIR_NAME
    if not create and d.is_dir():
        return d, "repository"
    if not (d.is_dir() or cfg.root_explicit or (cfg.workspace_root / ".git").exists()):
        # a folder that is not a repository (e.g. $HOME as an MCP server's start folder) gets no .staticsight/,
        # which would otherwise become a repository-root marker for everything below it
        return workspace_cache_dir(cfg), "per-user cache (not a git repository)"
    if create and _ensure_repo_data_dir(d):
        _migrate_legacy(cfg, d)
        return d, "repository"
    if not create:
        return d, "repository (not created yet)"
    return workspace_cache_dir(cfg), "per-user cache (repository is not writable)"


_LEGACY_FILES = ("semantic.db", "semantic.db-wal", "semantic.db-shm", "GTAGS", "GRTAGS", "GPATH")


def _migrate_legacy(cfg: Config, d: Path) -> None:
    """Move indexes built by older versions (per-user cache) into `.staticsight/` instead of rebuilding them."""
    old = workspace_cache_dir(cfg)
    if not old.is_dir() or (d / "semantic.db").exists() or (d / "GTAGS").exists():
        return
    for name in _LEGACY_FILES:
        src = old / name
        if src.is_file():
            try:
                os.replace(src, d / name)
            except OSError:
                import shutil

                try:
                    shutil.move(str(src), str(d / name))
                except OSError:
                    pass


def is_cpp_file(path: str) -> bool:
    return path.lower().endswith(CPP_EXTENSIONS)


def is_header(path: str) -> bool:
    return path.lower().endswith(HEADER_EXTENSIONS)
