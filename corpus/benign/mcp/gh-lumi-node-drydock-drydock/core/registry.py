"""Analyzer contract, shared analysis context, and plugin discovery.

An analyzer declares its options *once*, as data. The CLI turns that
declaration into argparse flags and the MCP server turns the same declaration
into a typed tool signature. Nothing is written twice, so the two surfaces
cannot drift -- which is how pre-0.2 ended up with a ``--markdown`` flag that
`dependency_analyzer` registered but never read, and a ``--budget`` flag that
`context_compiler` documented, accepted, passed around and silently ignored.

`AnalysisContext` is the other half of the contract. It walks the tree once,
builds the module index once, and caches every file's parsed symbols, then
hands the same objects to every analyzer in the run. Before, each of the six
analyzers `context_compiler` invoked did its own walk with its own skip rules,
which was both slow and quietly inconsistent.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping, Protocol, Sequence

from .models import FileId, ImportRef, Interface, SourceFile, Symbols
from .output import Reporter
from .paths import ModuleIndex
from .walker import WalkPolicy, WalkResult, read_text, walk

__all__ = [
    "Option",
    "Analyzer",
    "AnalysisContext",
    "AnalyzerRegistry",
    "registry",
    "get_analyzer",
    "available",
]


@dataclass(frozen=True, slots=True)
class Option:
    """One analyzer option, rendered to both the CLI and the MCP signature."""

    name: str
    """Python identifier, e.g. ``min_cluster``. Becomes ``--min-cluster``."""

    type: type = str
    default: Any = None
    help: str = ""
    choices: tuple[str, ...] | None = None
    short: str | None = None

    minimum: int | None = None
    """Smallest accepted value for a numeric option.

    Declared here so it is enforced once, at the CLI boundary, for every
    analyzer. Without it `--max-files -5` analysed zero files and reported
    `truncated: true`, and `--top -1` listed all-but-one module -- neither
    failed, both produced a confident wrong answer from a typo.
    """
    maximum: int | None = None

    @property
    def flag(self) -> str:
        return "--" + self.name.replace("_", "-")

    @property
    def flags(self) -> tuple[str, ...]:
        return (self.flag, self.short) if self.short else (self.flag,)


class Analyzer(Protocol):
    """What every analyzer -- built-in or third-party -- must provide."""

    name: str
    """Registry key and CLI subcommand, e.g. ``boundaries``."""

    summary: str
    """One line. Shown in ``drydock --help`` and as the MCP tool summary."""

    description: str
    """Full prose for the MCP tool description; this is what a model reads to
    decide whether to call it, so it is written for that audience."""

    options: tuple[Option, ...]

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Produce the analysis. Must be free of side effects on the project."""
        ...

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render `result` for humans. Every section of the JSON should appear;
        `context_compiler`'s markdown renderer used to silently drop the entire
        interfaces section it had just spent time computing."""
        ...


class AnalysisContext:
    """Shared, cached view of one project for the duration of a run."""

    def __init__(
        self,
        root: Path | str,
        *,
        policy: WalkPolicy | None = None,
        reporter: Reporter | None = None,
        languages: Any = None,
    ) -> None:
        self.root = Path(root).resolve()
        self.policy = policy or WalkPolicy()
        self.reporter = reporter or Reporter()

        if languages is None:
            from ..langs import language_registry

            languages = language_registry()
        self.languages = languages

        self._walk: WalkResult | None = None
        self._index: ModuleIndex | None = None
        self._index_by_id: dict[FileId, SourceFile] | None = None
        self._symbols: dict[FileId, Symbols | None] = {}
        self._interfaces: dict[FileId, Interface | None] = {}
        self._source: dict[FileId, str | None] = {}
        self._started = time.monotonic()

    # -- lazily built, then shared -----------------------------------------

    @property
    def walk(self) -> WalkResult:
        if self._walk is None:
            self.reporter.sub("walking tree")
            self._walk = walk(
                self.root,
                self.policy,
                lang_for_suffix=self.languages.language_for_suffix,
            )
            if self._walk.truncated:
                self.reporter.warn(
                    f"file limit reached at {len(self._walk.files)} files; "
                    "results are partial (raise --max-files)"
                )
        return self._walk

    @property
    def index(self) -> ModuleIndex:
        if self._index is None:
            self.reporter.sub("indexing modules")
            self._index = ModuleIndex(self.root, self.walk.files)
            # Let backends declare runtime import roots (sys.path mutations).
            for sf in self.walk.files:
                if sf.lang != "python":
                    continue
                parser = self.languages.parser_for(sf.lang)
                hook = getattr(parser, "runtime_roots", None)
                if hook is None:
                    continue
                src = self.source(sf.id)
                if src is None:
                    continue
                roots = hook(src, sf.id)
                if roots:
                    self._index.register_runtime_roots(sf.id, roots)
        return self._index

    @property
    def _by_id(self) -> Mapping[FileId, SourceFile]:
        """Id -> file lookup, built once.

        `source()` is called once per file by several analyzers; resolving each
        id with a linear scan over the walk made that quadratic in the file
        count, which only shows up on the large repositories this tool is
        meant for.
        """
        if self._index_by_id is None:
            self._index_by_id = {f.id: f for f in self.walk.files}
        return self._index_by_id

    def file(self, fid: FileId) -> SourceFile | None:
        return self._by_id.get(fid)

    def source(self, fid: FileId) -> str | None:
        if fid not in self._source:
            sf = self._by_id.get(fid)
            self._source[fid] = read_text(sf, self.policy) if sf else None
        return self._source[fid]

    def symbols(self, sf: SourceFile) -> Symbols | None:
        """Parsed symbols for `sf`, computed at most once per run."""
        if sf.id in self._symbols:
            return self._symbols[sf.id]
        result: Symbols | None = None
        if sf.lang:
            parser = self.languages.parser_for(sf.lang)
            src = self.source(sf.id)
            if parser is not None and src is not None:
                try:
                    result = parser.symbols(src, sf.id)
                except Exception as exc:  # a bad parse must not sink the run
                    self.reporter.warn(f"{sf.id}: {type(exc).__name__}: {exc}")
        self._symbols[sf.id] = result
        return result

    def interface(self, sf: SourceFile) -> Interface | None:
        if sf.id in self._interfaces:
            return self._interfaces[sf.id]
        result: Interface | None = None
        if sf.lang:
            parser = self.languages.parser_for(sf.lang)
            src = self.source(sf.id)
            if parser is not None and src is not None:
                try:
                    result = parser.interface(src, sf.id)
                except Exception as exc:
                    self.reporter.warn(f"{sf.id}: {type(exc).__name__}: {exc}")
        self._interfaces[sf.id] = result
        return result

    def imports(self, sf: SourceFile) -> tuple[ImportRef, ...]:
        sym = self.symbols(sf)
        return sym.imports if sym else ()

    def source_files(self) -> list[SourceFile]:
        """Files with a recognised programming language.

        Note this is *not* filtered by role. Role is metadata; an analyzer that
        wants only non-test code filters explicitly and says so in its output.
        """
        return [f for f in self.walk.files if f.lang]

    def meta(self) -> dict[str, Any]:
        """Provenance block attached to every analyzer result."""
        return {
            "project": self.root.name,
            "root": str(self.root),
            "files_walked": len(self.walk.files),
            "truncated": self.walk.truncated,
            "include_tests": self.policy.include_tests,
            "elapsed_ms": round((time.monotonic() - self._started) * 1000),
        }


class AnalyzerRegistry:
    """Built-in and third-party analyzers, discovered through one path."""

    GROUP = "drydock.analyzers"

    def __init__(self) -> None:
        self._analyzers: dict[str, Analyzer] = {}
        self._loaded = False

    def register(self, analyzer: Analyzer) -> Analyzer:
        self._analyzers[analyzer.name] = analyzer
        return analyzer

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        from .. import analyzers as _builtin  # noqa: F401  (registers built-ins)

        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover
            return
        try:
            eps = entry_points(group=self.GROUP)
        except TypeError:  # pragma: no cover - Python 3.9 shape
            eps = entry_points().get(self.GROUP, [])  # type: ignore[attr-defined]
        for ep in eps:
            if ep.name in self._analyzers:
                continue
            try:
                self.register(ep.load()())
            except Exception:
                # A broken third-party plugin must not take down the CLI.
                continue

    def get(self, name: str) -> Analyzer | None:
        self._load()
        return self._analyzers.get(name)

    def all(self) -> dict[str, Analyzer]:
        self._load()
        return dict(sorted(self._analyzers.items()))

    def names(self) -> list[str]:
        return list(self.all())


registry = AnalyzerRegistry()


def get_analyzer(name: str) -> Analyzer | None:
    return registry.get(name)


def available() -> dict[str, Analyzer]:
    return registry.all()
