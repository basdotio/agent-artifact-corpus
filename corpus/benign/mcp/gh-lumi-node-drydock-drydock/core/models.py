"""Canonical data types shared by every analyzer and language backend.

The single most important rule in this module:

    A file is identified, everywhere, by its POSIX path relative to the project
    root, *including* the extension. That string is a `FileId`.

The pre-0.2 code carried two competing identities for the same file -- the real
relative path (``pkg/a.py``) and an extension-stripped "normalized" key
(``pkg/a``) -- and leaked one into an API that expected the other. The result
was that `find_orphans` subtracted a set of `pkg/a` from a set of `pkg/a.py`,
the sets never intersected, and *every file in every project* was reported as
having no import relationships.

Extension-stripped keys still exist, but only inside `ModuleIndex`, where they
are a lookup key for resolving an import specifier to a `FileId` -- never an
identity, and never something an analyzer returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

__all__ = [
    "FileId",
    "Role",
    "SourceFile",
    "ImportRef",
    "Param",
    "Func",
    "Class",
    "Constant",
    "TypeDef",
    "Export",
    "Symbols",
    "Interface",
]

#: POSIX-relative path from the project root, with extension. The identity of a
#: file across the entire codebase. Never strip the extension from one of these.
FileId = str

Role = Literal["source", "test", "config", "docs", "build", "generated", "data", "unknown"]


@dataclass(frozen=True, slots=True)
class SourceFile:
    """One file discovered by the walker."""

    id: FileId
    """POSIX path relative to the project root, with extension."""

    path: Path
    """Absolute path on disk."""

    lang: str | None = None
    """Language name from the language registry, or None if unrecognised."""

    role: Role = "unknown"
    size: int = 0
    lines: int = 0

    @property
    def suffix(self) -> str:
        return Path(self.id).suffix.lower()

    @property
    def parts(self) -> tuple[str, ...]:
        return tuple(self.id.split("/"))


@dataclass(frozen=True, slots=True)
class ImportRef:
    """A single import as written in a source file, before resolution.

    Resolution to a `FileId` is the job of `ModuleIndex`, not the parser. A
    language backend reports what the source says; it does not guess where the
    target lives on disk.
    """

    raw: str
    """The specifier exactly as written, e.g. ``pkg.a``, ``./util``, ``crate::x``."""

    kind: Literal["absolute", "relative", "external", "unknown"] = "unknown"

    level: int = 0
    """Number of leading dots for Python-style relative imports (0 if absolute)."""

    symbols: tuple[str, ...] = ()
    """Names pulled from the module, e.g. ``from . import a, b`` -> ``("a", "b")``.

    Needed to resolve ``from . import sibling``, which the old extractor got
    wrong: it resolved to the package's own ``__init__.py`` rather than to
    ``sibling``.
    """

    line: int = 0

    scope: Literal["module", "function", "conditional", "unknown"] = "module"
    """Where the import statement sits.

    A cycle through a *module-level* import is a genuine circular dependency. A
    cycle through a function-level or `if TYPE_CHECKING:` import is a deliberate
    inversion -- the standard way to let a registry import its plugins without
    a load-time cycle. Drydock's own `core/registry.py` does exactly that, and
    without this field every one of those deferred imports reads as an
    architectural violation rather than the fix for one.
    """


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    type: str | None = None
    default: str | None = None

    def render(self) -> str:
        out = self.name
        if self.type:
            out += f": {self.type}"
        if self.default is not None:
            out += f" = {self.default}"
        return out


@dataclass(frozen=True, slots=True)
class Func:
    name: str
    params: tuple[Param, ...] = ()
    returns: str | None = None
    line: int = 0
    is_async: bool = False
    decorators: tuple[str, ...] = ()
    doc: str | None = None
    params_raw: str | None = None
    """Verbatim parameter text, for regex backends that cannot split reliably."""

    @property
    def is_private(self) -> bool:
        return _is_private(self.name)

    def render(self) -> str:
        if self.params_raw is not None and not self.params:
            args = self.params_raw
        else:
            args = ", ".join(p.render() for p in self.params)
        out = f"{'async ' if self.is_async else ''}{self.name}({args})"
        if self.returns:
            out += f" -> {self.returns}"
        return out


@dataclass(frozen=True, slots=True)
class Class:
    name: str
    bases: tuple[str, ...] = ()
    methods: tuple[Func, ...] = ()
    class_methods: tuple[Func, ...] = ()
    properties: tuple[Func, ...] = ()
    line: int = 0
    decorators: tuple[str, ...] = ()
    doc: str | None = None
    kind: Literal["class", "struct", "trait", "interface", "enum", "impl"] = "class"

    @property
    def is_private(self) -> bool:
        return _is_private(self.name)


@dataclass(frozen=True, slots=True)
class Constant:
    name: str
    value: str | None = None
    type: str | None = None
    line: int = 0

    @property
    def is_private(self) -> bool:
        return _is_private(self.name)


@dataclass(frozen=True, slots=True)
class TypeDef:
    name: str
    kind: Literal["type", "interface", "enum", "trait", "alias", "struct"] = "type"
    definition: str | None = None
    bases: tuple[str, ...] = ()
    line: int = 0

    @property
    def is_private(self) -> bool:
        return _is_private(self.name)


@dataclass(frozen=True, slots=True)
class Export:
    name: str
    source: str | None = None
    """Module the name is re-exported from, for ``export {x} from './y'``."""
    line: int = 0


@dataclass(frozen=True, slots=True)
class Symbols:
    """Everything a language backend can pull out of one file.

    Backends fill in what they can and leave the rest empty. `codemap` consumes
    the whole thing; `interfaces` consumes a public-only projection of it (see
    `Interface.from_symbols`).
    """

    classes: tuple[Class, ...] = ()
    functions: tuple[Func, ...] = ()
    constants: tuple[Constant, ...] = ()
    types: tuple[TypeDef, ...] = ()
    exports: tuple[Export, ...] = ()
    imports: tuple[ImportRef, ...] = ()
    package: str | None = None
    """Declared package/module name where the language has one (Go, Java)."""

    def is_empty(self) -> bool:
        return not (
            self.classes or self.functions or self.constants
            or self.types or self.exports
        )


@dataclass(frozen=True, slots=True)
class Interface:
    """The public surface of one module.

    Deliberately a distinct type from `Symbols`: "everything in the file" and
    "what the file exposes" are different questions, and conflating them is how
    private constants ended up in the pre-0.2 public-interface output.
    """

    classes: tuple[Class, ...] = ()
    functions: tuple[Func, ...] = ()
    constants: tuple[Constant, ...] = ()
    types: tuple[TypeDef, ...] = ()
    exports: tuple[Export, ...] = ()
    package: str | None = None
    declared: bool = False
    """True when the module states its own surface (``__all__``, ``export``)."""

    def is_empty(self) -> bool:
        return not (
            self.classes or self.functions or self.constants
            or self.types or self.exports
        )

    @classmethod
    def from_symbols(cls, sym: Symbols, *, explicit: frozenset[str] | None = None) -> Interface:
        """Project `Symbols` down to its public surface.

        `explicit` is the module's own declaration of what is public -- Python's
        ``__all__``, or the set of exported names in JS/TS. When present it wins
        outright. When absent, the language's privacy convention applies.

        Every category is filtered, constants included. The pre-0.2 code applied
        its privacy check via ``getattr(node, "name")``, which `ast.Assign` does
        not have, so module constants bypassed the filter entirely and
        ``_SECRET_KEY`` was reported as part of the public API.
        """
        if explicit is not None:
            keep = lambda n: n in explicit  # noqa: E731
        else:
            keep = lambda n: not _is_private(n)  # noqa: E731

        return cls(
            classes=tuple(c for c in sym.classes if keep(c.name)),
            functions=tuple(f for f in sym.functions if keep(f.name)),
            constants=tuple(k for k in sym.constants if keep(k.name)),
            types=tuple(t for t in sym.types if keep(t.name)),
            exports=sym.exports,
            package=sym.package,
            declared=explicit is not None,
        )


def _is_private(name: str) -> bool:
    """Privacy by leading-underscore convention, with dunders kept public.

    ``__init__`` and friends are part of a class's usable surface; ``_helper``
    and ``_SECRET_KEY`` are not.
    """
    if not name:
        return True
    if name.startswith("__") and name.endswith("__"):
        return False
    return name.startswith("_")
