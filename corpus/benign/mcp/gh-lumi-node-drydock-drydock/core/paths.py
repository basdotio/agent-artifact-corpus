"""Path identity and import resolution.

Two jobs, kept strictly apart:

* `file_id` / `is_within` -- turn a real path into the canonical `FileId` used
  as a file's identity everywhere else.
* `ModuleIndex` -- turn an import *specifier* (``pkg.a``, ``./util``,
  ``crate::x``) into the `FileId`\\(s) it points at.

The pre-0.2 code merged the two: it built one dict keyed by extension-stripped
paths and used it both as the file inventory and as the import lookup table.
That is what made `find_orphans` compare `pkg/a` against `pkg/a.py` and report
every file as an orphan, and it is why import resolution only ever worked for
packages sitting directly at the project root -- a ``src/`` layout, or the flat
sibling imports Drydock's own ``Tools/`` uses, resolved to nothing at all.

Resolution here is tiered and *honest about failure*: anything it cannot place
is returned as unresolved rather than silently dropped, so an analyzer can say
"47 imports could not be resolved" instead of printing an empty graph and
looking like the project simply has no structure.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Iterable, Mapping, Sequence

from .models import FileId, ImportRef, SourceFile

__all__ = [
    "file_id",
    "is_within",
    "common_prefix",
    "Resolution",
    "ModuleIndex",
]


def file_id(path: Path, root: Path) -> FileId:
    """Canonical identity for `path` relative to `root`: POSIX, with extension.

    Raises ValueError if `path` is not under `root` -- callers should filter
    with `is_within` first rather than passing in strays.
    """
    return PurePosixPath(path.resolve().relative_to(root.resolve())).as_posix()


def is_within(path: Path, root: Path) -> bool:
    """True if `path` is `root` or lives underneath it.

    Used to keep symlinked trees from walking out of the project, and to guard
    destructive operations against a path that escaped its intended parent.
    """
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def common_prefix(ids: Iterable[FileId]) -> str | None:
    """Longest shared *directory* prefix of the given file ids.

    Compares whole path segments, never characters -- ``src/apple/a.py`` and
    ``src/apricot/b.py`` share ``src``, not ``src/ap``.
    """
    parts_list = [i.split("/")[:-1] for i in ids]
    if not parts_list:
        return None
    shared: list[str] = []
    for level in zip(*parts_list):
        if len(set(level)) == 1:
            shared.append(level[0])
        else:
            break
    return "/".join(shared) or None


@dataclass(frozen=True, slots=True)
class Resolution:
    """Outcome of resolving one import specifier."""

    targets: tuple[FileId, ...] = ()
    """Files the specifier points at. Usually 0 or 1; Go package imports and
    Python ``from pkg import *`` style package references can yield several."""

    external: bool = False
    """True when the specifier clearly refers to something outside the project
    (a third-party package, a stdlib module, a bare npm specifier)."""

    ambiguous: bool = False
    """True when several unrelated candidates matched and none could be
    preferred. Deliberately *not* resolved -- a wrong edge is worse than a
    missing one, but the caller is told it happened."""

    tier: str = ""
    """Which rule produced the answer, for debugging and for `--explain`."""

    @property
    def resolved(self) -> bool:
        return bool(self.targets)


# Import specifiers that are obviously not project-local, per language.
_EXTERNAL_HINTS: Mapping[str, re.Pattern[str]] = {
    "javascript": re.compile(r"^[^./]"),
    "typescript": re.compile(r"^[^./]"),
}

_JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
_JS_INDEX_STEMS = ("index",)


class ModuleIndex:
    """Resolves import specifiers to `FileId`s for a single project.

    Build it once per analysis from the walker's file list; it is read-only
    afterwards and cheap to query.
    """

    def __init__(self, root: Path | str, files: Sequence[SourceFile]) -> None:
        # `walk()` and `AnalysisContext` both take `Path | str`; accepting only
        # Path here made the one type in the chain that behaved differently.
        self.root = Path(root).resolve()
        self._files: dict[FileId, SourceFile] = {f.id: f for f in files}

        # Directory -> file ids directly inside it. Go imports a directory.
        self._by_dir: dict[str, list[FileId]] = defaultdict(list)
        for fid in self._files:
            self._by_dir[str(PurePosixPath(fid).parent).strip(".")].append(fid)

        # Dotted module path -> file ids, one entry per plausible source root.
        self._py_modules: dict[str, set[FileId]] = defaultdict(set)
        self._py_source_roots: set[str] = set()
        self._build_python_index()

        # Extensionless path -> file ids, for JS/TS relative specifiers.
        self._js_stems: dict[str, set[FileId]] = defaultdict(set)
        self._build_js_index()

        self._go_module = self._read_go_module()
        self._rust_roots = self._find_rust_roots()

        # Files that inject import paths at runtime, e.g.
        # ``sys.path.insert(0, Path(__file__).parent / "analyzers")``. Drydock's
        # own MCP server does exactly this, and refusing to model it is what
        # made the tool report zero import edges against its own source tree.
        self._extra_roots: dict[FileId, tuple[str, ...]] = {}

    # -- construction ------------------------------------------------------

    def _build_python_index(self) -> None:
        """Index every .py file under each source root that could contain it.

        The source root for a module is found by walking up from the file while
        each directory is a package (has ``__init__.py``); the first ancestor
        that is *not* a package is the root. That single rule handles flat
        layouts, ``src/`` layouts and nested packages without special cases:

            src/mypkg/foo.py  + src/mypkg/__init__.py  -> root ``src``,   module ``mypkg.foo``
            Tools/analyzers/codemap.py (no __init__)   -> root ``Tools/analyzers``, module ``codemap``

        The file is also indexed under the project root, so ``Tools.analyzers.codemap``
        resolves too. Both spellings are legitimate; which one a project uses
        depends on how it is invoked.
        """
        for fid, sf in self._files.items():
            if sf.suffix != ".py":
                continue
            p = PurePosixPath(fid)
            parts = list(p.parts)
            stem_parts = parts[:-1] + [p.stem]
            if p.stem == "__init__":
                stem_parts = parts[:-1]
                if not stem_parts:
                    continue

            # Walk up while the containing directory is an importable package.
            depth = len(parts) - 1
            root_depth = depth
            while root_depth > 0:
                pkg_marker = "/".join(parts[:root_depth] + ["__init__.py"])
                if pkg_marker in self._files:
                    root_depth -= 1
                else:
                    break

            self._py_source_roots.add("/".join(parts[:root_depth]))

            # Index under every root from the package root up to the project
            # root, so both `mypkg.foo` and `src.mypkg.foo` resolve.
            for d in range(root_depth, -1, -1):
                dotted = ".".join(stem_parts[d:])
                if dotted:
                    self._py_modules[dotted].add(fid)

    def _build_js_index(self) -> None:
        for fid, sf in self._files.items():
            if sf.suffix not in _JS_EXTENSIONS:
                continue
            p = PurePosixPath(fid)
            stem = str(p.with_suffix("")) if p.suffix else str(p)
            # ".d.ts" leaves a stray ".d" behind.
            if stem.endswith(".d"):
                stem = stem[:-2]
            self._js_stems[stem].add(fid)
            if p.stem in _JS_INDEX_STEMS:
                parent = str(p.parent).strip(".")
                if parent:
                    self._js_stems[parent].add(fid)

    def _read_go_module(self) -> str | None:
        go_mod = self.root / "go.mod"
        if not go_mod.is_file():
            return None
        try:
            text = go_mod.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return None
        m = re.search(r"^module\s+(\S+)", text, re.MULTILINE)
        return m.group(1) if m else None

    def _find_rust_roots(self) -> tuple[str, ...]:
        """Directories that behave as a Rust crate root (contain lib.rs/main.rs)."""
        roots: set[str] = set()
        for fid in self._files:
            p = PurePosixPath(fid)
            if p.name in ("lib.rs", "main.rs"):
                roots.add(str(p.parent).strip("."))
        return tuple(sorted(roots))

    def register_runtime_roots(self, fid: FileId, roots: Iterable[str]) -> None:
        """Record extra import roots a specific file establishes at runtime.

        Populated by the Python backend when it sees a ``sys.path`` mutation.
        Scoped to the file that performs it, so one module's path hack does not
        silently change how the rest of the project resolves.
        """
        cleaned = tuple(sorted({r.strip("/") for r in roots if r}))
        if cleaned:
            self._extra_roots[fid] = cleaned

    # -- queries -----------------------------------------------------------

    @property
    def source_roots(self) -> tuple[str, ...]:
        return tuple(sorted(self._py_source_roots))

    def files(self) -> Mapping[FileId, SourceFile]:
        return self._files

    def resolve(self, imp: ImportRef, *, from_file: FileId, lang: str) -> Resolution:
        """Resolve one import to the file(s) it refers to."""
        if lang == "python":
            return self._resolve_python(imp, from_file)
        if lang in ("javascript", "typescript"):
            return self._resolve_js(imp, from_file)
        if lang == "go":
            return self._resolve_go(imp, from_file)
        if lang == "rust":
            return self._resolve_rust(imp, from_file)
        return Resolution(tier="unsupported-language")

    # -- python ------------------------------------------------------------

    def _resolve_python(self, imp: ImportRef, from_file: FileId) -> Resolution:
        if imp.level > 0:
            return self._resolve_python_relative(imp, from_file)

        dotted = imp.raw
        hits = self._py_modules.get(dotted)
        if hits:
            return Resolution(targets=tuple(sorted(hits)), tier="python-absolute")

        # A file that inserted a directory onto sys.path can import modules
        # sitting directly inside it by bare name.
        for extra in self._extra_roots.get(from_file, ()):  # pragma: no branch
            candidate = f"{extra}/{dotted.replace('.', '/')}"
            for suffix in (".py", "/__init__.py"):
                fid = f"{candidate}{suffix}"
                if fid in self._files:
                    return Resolution(targets=(fid,), tier="python-sys-path")

        # ``import pkg.sub.mod`` where only the package is indexed.
        head = dotted.split(".")[0]
        if head in self._py_modules and "." in dotted:
            return Resolution(
                targets=tuple(sorted(self._py_modules[head])), tier="python-package-head"
            )

        return Resolution(external=True, tier="python-external")

    def _resolve_python_relative(self, imp: ImportRef, from_file: FileId) -> Resolution:
        """Resolve ``from . import x`` / ``from ..pkg.mod import y``.

        `level` counts dots: one dot means the current package (the importing
        file's own directory), two means its parent, and so on.

        The symbol list matters here. ``from . import sibling`` names no module
        at all -- the target is in `symbols`. The old extractor ignored that and
        resolved such imports to the package's own ``__init__.py``, drawing an
        edge from a module to its own package instead of to its sibling.
        """
        here = PurePosixPath(from_file).parent
        up = imp.level - 1
        base_parts = list(here.parts)
        if up > len(base_parts):
            return Resolution(tier="python-relative-overflow")
        base = base_parts[: len(base_parts) - up] if up else base_parts

        if imp.raw:
            target_parts = base + imp.raw.split(".")
            found = self._python_file_at("/".join(target_parts))
            if found:
                return Resolution(targets=found, tier="python-relative")
            return Resolution(tier="python-relative-unresolved")

        # No module name: each imported symbol may itself be a submodule.
        targets: list[FileId] = []
        for sym in imp.symbols:
            found = self._python_file_at("/".join(base + [sym]))
            targets.extend(found)
        if targets:
            return Resolution(targets=tuple(sorted(set(targets))), tier="python-relative-symbol")

        pkg_init = "/".join(base + ["__init__.py"])
        if pkg_init in self._files:
            return Resolution(targets=(pkg_init,), tier="python-relative-package")
        return Resolution(tier="python-relative-unresolved")

    def _python_file_at(self, path_no_ext: str) -> tuple[FileId, ...]:
        for suffix in (".py", "/__init__.py"):
            fid = f"{path_no_ext}{suffix}"
            if fid in self._files:
                return (fid,)
        return ()

    # -- javascript / typescript -------------------------------------------

    def _resolve_js(self, imp: ImportRef, from_file: FileId) -> Resolution:
        spec = imp.raw
        if not spec.startswith("."):
            if spec.startswith("/"):
                return Resolution(tier="js-absolute-unsupported")
            return Resolution(external=True, tier="js-external")

        here = PurePosixPath(from_file).parent
        target = _normalize_posix(str(here / spec))
        hits = self._js_stems.get(target)
        if hits:
            return Resolution(targets=tuple(sorted(hits)), tier="js-relative")

        # Explicit extension in the specifier, e.g. ``./util.js``.
        if target in self._files:
            return Resolution(targets=(target,), tier="js-relative-exact")
        stem = str(PurePosixPath(target).with_suffix(""))
        hits = self._js_stems.get(stem)
        if hits:
            return Resolution(targets=tuple(sorted(hits)), tier="js-relative-stem")

        return Resolution(tier="js-unresolved")

    # -- go ----------------------------------------------------------------

    def _resolve_go(self, imp: ImportRef, from_file: FileId) -> Resolution:
        spec = imp.raw
        if not self._go_module or not spec.startswith(self._go_module):
            return Resolution(external=True, tier="go-external")
        rel = spec[len(self._go_module) :].strip("/")
        members = self._by_dir.get(rel, [])
        # `_test.go` files belong to the package but are never linked into an
        # importer, so an import of the package does not depend on them.
        # Counting them made every test file in a widely-imported package look
        # like a hub with the same afferent coupling as the package itself.
        go_files = tuple(
            sorted(
                f for f in members
                if f.endswith(".go") and not f.endswith("_test.go")
            )
        )
        if go_files:
            # A Go import names a package (a directory), so every file in it is
            # a genuine target.
            return Resolution(targets=go_files, tier="go-package")
        return Resolution(tier="go-unresolved")

    # -- rust --------------------------------------------------------------

    def _resolve_rust(self, imp: ImportRef, from_file: FileId) -> Resolution:
        """Resolve a Rust path to the file that defines it.

        The subtlety is what ``super::`` means, which depends on whether the
        importing file *is* its module's root:

        * ``src/kernel/pool.rs`` is the module ``kernel::pool``. Its parent
          module is ``kernel``, whose files live in ``src/kernel`` -- the
          file's own directory.
        * ``src/kernel/mod.rs`` *is* the module ``kernel``. Its parent is the
          crate root, one directory up.

        Treating both as "one directory up" (as this did originally) sent
        every ``super::`` in a non-``mod.rs`` file to the wrong directory. On a
        real Rust project that was half of all local imports left unresolved.

        A trailing path segment may also name an *item* rather than a module --
        ``use super::DexAdapter`` where ``DexAdapter`` is a type re-exported by
        ``adapters/mod.rs``. When no module file matches, the module root is
        the correct target.
        """
        spec = imp.raw
        path = PurePosixPath(from_file)
        here = path.parent

        # Dispatch on the specifier's own prefix, before considering the
        # backend's `kind` label. ``super::`` is arguably "relative" and
        # arguably "absolute-within-crate", and backends reasonably disagree;
        # resolution must not depend on which word a parser chose. Getting this
        # ordering wrong sent every `super::` import into the sibling branch,
        # where it looked for a file literally named `super.rs`.
        if spec.startswith("self::"):
            name = spec.split("::", 1)[1].split("::")[0]
            found = self._rust_file_at(str(here), name)
            return (
                Resolution(targets=found, tier="rust-self")
                if found
                else Resolution(tier="rust-unresolved")
            )

        if imp.kind == "relative" and not spec.startswith(("super::", "crate::")):
            name = spec.split("::")[0]  # ``mod foo;``
            found = self._rust_file_at(str(here), name)
            return (
                Resolution(targets=found, tier="rust-sibling")
                if found
                else Resolution(tier="rust-unresolved")
            )

        if spec.startswith("super::"):
            is_module_root = path.name in ("mod.rs", "lib.rs", "main.rs")
            target_dir = str(here.parent) if is_module_root else str(here)
            rest = spec.split("::", 1)[1].split("::")
            found = self._rust_file_at(target_dir, rest[0])
            if found:
                return Resolution(targets=found, tier="rust-super")
            # Not a module: an item defined or re-exported by the parent module.
            found = self._rust_module_root(target_dir)
            if found:
                return Resolution(targets=found, tier="rust-super-item")
            return Resolution(tier="rust-unresolved")

        if spec.startswith("crate::"):
            rest = spec.split("::", 1)[1].split("::")
            for croot in self._rust_roots:
                found = self._rust_file_at(croot, rest[0])
                if found:
                    return Resolution(targets=found, tier="rust-crate")
            # ``crate::Item`` -- defined at the crate root itself.
            for croot in self._rust_roots:
                found = self._rust_module_root(croot)
                if found:
                    return Resolution(targets=found, tier="rust-crate-item")
            return Resolution(tier="rust-unresolved")

        return Resolution(external=True, tier="rust-external")

    def _rust_module_root(self, directory: str) -> tuple[FileId, ...]:
        """The file that *is* the module for `directory` (mod.rs/lib.rs/main.rs)."""
        directory = directory.strip(".").strip("/")
        prefix = f"{directory}/" if directory else ""
        for candidate in ("mod.rs", "lib.rs", "main.rs"):
            fid = f"{prefix}{candidate}"
            if fid in self._files:
                return (fid,)
        return ()

    def _rust_file_at(self, directory: str, name: str) -> tuple[FileId, ...]:
        directory = directory.strip(".").strip("/")
        prefix = f"{directory}/" if directory else ""
        for candidate in (f"{prefix}{name}.rs", f"{prefix}{name}/mod.rs"):
            if candidate in self._files:
                return (candidate,)
        return ()


def _normalize_posix(path: str) -> str:
    """Collapse ``.``/``..`` segments without touching the filesystem."""
    out: list[str] = []
    for part in path.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if out:
                out.pop()
            continue
        out.append(part)
    return "/".join(out)
