"""The one file walker every analyzer uses.

Pre-0.2 each analyzer carried its own `SKIP_DIRS` set and its own idea of what
a "source file" was. Three consequences, all of them real bugs:

* `dependency_analyzer` tested its skip list with ``any(skip in str(filepath))``
  against the *absolute* path, so a project living anywhere under a directory
  named ``build``, ``dist``, ``vendor``, ``target`` or ``env`` analysed zero
  files and reported "no dependencies" rather than an error.
* `interface_extractor` skipped ``test/`` and ``tests/``; the others did not.
  `context_compiler` therefore built its sections from different file sets and
  said nothing about it.
* `codemap` classified everything under ``scripts/`` as role ``build`` and then
  refused to parse anything whose role was not ``source``, so projects keeping
  code in ``scripts/`` got an empty code map.

So: one walker, matching on path *components*, with a single explicit policy
object that analyzers may tighten but never silently reinterpret. Role is
metadata attached to a file, never a gate on whether the file gets parsed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Iterator, Sequence

from .models import FileId, Role, SourceFile
from .paths import file_id, is_within

__all__ = ["WalkPolicy", "WalkResult", "walk", "classify_role", "DEFAULT_SKIP_DIRS"]


#: Directory *names* that are never worth walking into. Matched as whole path
#: components -- a project at ``/srv/build/myapp`` is walked normally, because
#: ``build`` is an ancestor of the root rather than a component beneath it.
DEFAULT_SKIP_DIRS: frozenset[str] = frozenset(
    {
        ".git", ".hg", ".svn", ".bzr",
        "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".cache",
        "node_modules", "bower_components", "jspm_packages",
        "venv", ".venv", "virtualenv", ".tox", ".nox", ".eggs",
        "dist", "build", "out", "target", "bin", "obj",
        ".next", ".nuxt", ".svelte-kit", ".output", ".parcel-cache",
        "vendor", "third_party", "Godeps",
        ".idea", ".vscode", ".vs",
        "coverage", "htmlcov", ".coverage",
        ".terraform", ".serverless",
        "site",  # mkdocs build output
    }
)

DEFAULT_SKIP_FILES: frozenset[str] = frozenset(
    {".DS_Store", "Thumbs.db", "desktop.ini"}
)

#: Suffixes that are data or binaries, never worth reading as text.
BINARY_SUFFIXES: frozenset[str] = frozenset(
    {
        ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".webp", ".svg",
        ".pdf", ".zip", ".tar", ".gz", ".bz2", ".xz", ".7z", ".rar",
        ".so", ".dylib", ".dll", ".exe", ".bin", ".o", ".a", ".class",
        ".pyc", ".pyo", ".woff", ".woff2", ".ttf", ".eot", ".otf",
        ".mp3", ".mp4", ".avi", ".mov", ".wav", ".webm",
        ".db", ".sqlite", ".sqlite3", ".parquet",
    }
)


@dataclass(frozen=True, slots=True)
class WalkPolicy:
    """What to walk. Explicit, shared, and reported in analyzer output.

    Analyzers may pass a tightened policy, but the defaults are identical for
    all of them so that a compiled context is internally consistent.
    """

    skip_dirs: frozenset[str] = DEFAULT_SKIP_DIRS
    skip_files: frozenset[str] = DEFAULT_SKIP_FILES
    skip_hidden: bool = True
    """Skip dot-directories. Dot-*files* are kept -- ``.eslintrc``,
    ``.python-version`` and friends are meaningful configuration."""

    include_tests: bool = True
    """Tests are walked and classified by default. They are part of the
    codebase and excluding them silently distorts every count. Analyzers that
    want to exclude them do so by filtering on `SourceFile.role`, visibly."""

    follow_symlinks: bool = False
    max_files: int | None = None
    max_file_bytes: int = 2_000_000
    """Files above this are inventoried but not parsed."""

    extra_skip_dirs: frozenset[str] = frozenset()

    def with_extra_skips(self, names: Sequence[str]) -> WalkPolicy:
        return replace(self, extra_skip_dirs=self.extra_skip_dirs | frozenset(names))

    def should_skip_dir(self, name: str) -> bool:
        if name in self.skip_dirs or name in self.extra_skip_dirs:
            return True
        if self.skip_hidden and name.startswith(".") and name not in (".", ".."):
            return True
        return False


@dataclass(slots=True)
class WalkResult:
    """Files found, plus an honest account of what was left out."""

    root: Path
    files: list[SourceFile] = field(default_factory=list)
    truncated: bool = False
    """True when `max_files` cut the walk short -- surfaced in analyzer output
    rather than left for the caller to infer from a suspiciously round count."""
    skipped_dirs: int = 0
    total_seen: int = 0

    def by_role(self, *roles: Role) -> list[SourceFile]:
        wanted = set(roles)
        return [f for f in self.files if f.role in wanted]

    def with_lang(self) -> list[SourceFile]:
        return [f for f in self.files if f.lang]

    def ids(self) -> set[FileId]:
        return {f.id for f in self.files}


# --------------------------------------------------------------------------
# Role classification
# --------------------------------------------------------------------------

_TEST_DIR_NAMES = frozenset({"test", "tests", "__tests__", "spec", "specs", "testing"})
_DOC_DIR_NAMES = frozenset({"doc", "docs", "documentation", "man"})
_BUILD_DIR_NAMES = frozenset({"ci", ".github", ".gitlab", "infra", "deploy"})

_CONFIG_FILENAMES = frozenset(
    {
        "pyproject.toml", "setup.py", "setup.cfg", "pipfile", "poetry.lock",
        "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
        "tsconfig.json", "jsconfig.json", "cargo.toml", "cargo.lock",
        "go.mod", "go.sum", "gemfile", "composer.json", "composer.lock",
        "requirements.txt", "environment.yml", "conda.yaml",
        "dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "makefile", "justfile", "taskfile.yml", "rakefile",
        ".editorconfig", ".gitignore", ".gitattributes", ".dockerignore",
        ".nvmrc", ".node-version", ".python-version", ".ruby-version",
        "mkdocs.yml", "mkdocs.yaml",
    }
)

_CONFIG_SUFFIXES = frozenset({".toml", ".ini", ".cfg", ".yaml", ".yml", ".properties"})
_DOC_SUFFIXES = frozenset({".md", ".rst", ".adoc", ".txt"})
_DATA_SUFFIXES = frozenset({".json", ".csv", ".tsv", ".xml", ".jsonl", ".ndjson"})

_DOC_STEMS = frozenset(
    {"readme", "changelog", "license", "licence", "contributing", "authors",
     "notice", "code_of_conduct", "security", "history"}
)

_GENERATED_MARKERS = ("min.", "bundle.", ".generated.", "_pb2", ".pb.go", "_generated.")


def classify_role(fid: FileId, *, lang: str | None = None) -> Role:
    """Classify a file by whole path components and filename, never substrings.

    Precedence is fixed and documented: generated > test > config > docs >
    build > source > data > unknown. A file with a recognised programming
    language always beats the ``data``/``unknown`` buckets, so a ``.py`` file
    inside ``scripts/`` is still source code -- it just also happens to live in
    a build directory.
    """
    p = _segments(fid)
    dirs = {d.lower() for d in p[:-1]}
    filename = p[-1]
    lower = filename.lower()
    stem, _, suffix = _split_name(lower)

    if any(marker in lower for marker in _GENERATED_MARKERS):
        return "generated"

    if dirs & _TEST_DIR_NAMES:
        return "test"
    if stem.startswith("test_") or stem.endswith("_test"):
        return "test"
    if ".test" in lower or ".spec" in lower:
        return "test"

    if lower in _CONFIG_FILENAMES:
        return "config"

    if dirs & _DOC_DIR_NAMES or stem in _DOC_STEMS:
        return "docs"
    if suffix in _DOC_SUFFIXES:
        return "docs"

    # A recognised language wins over the generic buckets below, which is what
    # keeps ``scripts/deploy.py`` parseable instead of being filed as build
    # output and never read.
    if lang:
        if dirs & _BUILD_DIR_NAMES:
            return "build"
        return "source"

    if suffix in _CONFIG_SUFFIXES:
        return "config"
    if dirs & _BUILD_DIR_NAMES:
        return "build"
    if suffix in _DATA_SUFFIXES:
        return "data"
    return "unknown"


def _segments(fid: FileId) -> tuple[str, ...]:
    """Whole path segments. Classification compares these, never substrings."""
    return tuple(fid.split("/"))


def _split_name(lower: str) -> tuple[str, str, str]:
    if "." in lower[1:]:
        idx = lower.rindex(".")
        return lower[:idx], ".", lower[idx:]
    return lower, "", ""


# --------------------------------------------------------------------------
# The walk
# --------------------------------------------------------------------------

def walk(
    root: Path | str,
    policy: WalkPolicy | None = None,
    *,
    lang_for_suffix=None,
) -> WalkResult:
    """Walk `root`, returning files in deterministic order.

    `lang_for_suffix` is a callable mapping a lowercase suffix to a language
    name; the language registry supplies it. Kept as a parameter so the walker
    has no import-time dependency on the language plugins.
    """
    policy = policy or WalkPolicy()
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(f"Project path not found: {root}")
    if not root_path.is_dir():
        raise NotADirectoryError(f"Project path is not a directory: {root}")

    result = WalkResult(root=root_path)
    seen_dirs: set[tuple[int, int]] = set()

    for dirpath, dirnames, filenames in os.walk(
        root_path, topdown=True, followlinks=policy.follow_symlinks
    ):
        before = len(dirnames)
        dirnames[:] = sorted(d for d in dirnames if not policy.should_skip_dir(d))
        result.skipped_dirs += before - len(dirnames)

        if policy.follow_symlinks:
            # Guard against symlink cycles and against escaping the project.
            try:
                st = os.stat(dirpath)
                key = (st.st_dev, st.st_ino)
            except OSError:
                continue
            if key in seen_dirs:
                dirnames[:] = []
                continue
            seen_dirs.add(key)
            if not is_within(Path(dirpath), root_path):
                dirnames[:] = []
                continue

        for filename in sorted(filenames):
            if filename in policy.skip_files:
                continue

            abs_path = Path(dirpath) / filename
            result.total_seen += 1

            if policy.max_files is not None and len(result.files) >= policy.max_files:
                result.truncated = True
                return result

            suffix = abs_path.suffix.lower()
            if suffix in BINARY_SUFFIXES:
                continue

            try:
                stat = abs_path.stat()
            except OSError:
                continue
            if not abs_path.is_file():
                continue

            try:
                fid = file_id(abs_path, root_path)
            except ValueError:
                continue

            lang = lang_for_suffix(suffix) if lang_for_suffix else None
            role = classify_role(fid, lang=lang)

            if role == "test" and not policy.include_tests:
                continue

            result.files.append(
                SourceFile(
                    id=fid,
                    path=abs_path,
                    lang=lang,
                    role=role,
                    size=stat.st_size,
                    lines=0,
                )
            )

    result.files.sort(key=lambda f: f.id)
    return result


def read_text(sf: SourceFile, policy: WalkPolicy | None = None) -> str | None:
    """Read a file's text, or None if it is too large or undecodable.

    Centralised so every backend applies the same size ceiling and the same
    lenient decoding, instead of each one inventing its own try/except.
    """
    policy = policy or WalkPolicy()
    if sf.size > policy.max_file_bytes:
        return None
    try:
        return sf.path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeError):
        return None
