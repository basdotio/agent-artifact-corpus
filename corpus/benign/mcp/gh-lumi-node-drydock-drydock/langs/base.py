"""The language plugin contract.

A language backend answers three questions about one file, and nothing else:

    symbols(...)   what is defined in here?
    imports(...)   what does it reference?
    interface(...) what does it expose?

It does **not** decide where an import points -- that is `ModuleIndex`'s job,
because resolution needs whole-project knowledge a single-file parser cannot
have. Keeping the split means a new language needs no changes in any analyzer:
register a parser and codemap, boundaries, dependencies and interfaces all pick
it up at once. Pre-0.2 the same six languages were re-implemented, slightly
differently, inside four separate analyzers.

Backends ship stdlib-only (`ast` for Python, line regexes elsewhere). A
tree-sitter backend can be registered later against this same protocol without
touching a single analyzer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..core.models import ImportRef, Interface, Symbols

__all__ = ["LanguageParser", "BaseParser"]


@runtime_checkable
class LanguageParser(Protocol):
    """What a language backend must provide."""

    name: str
    """Language name, e.g. ``python``. Appears in output and stats."""

    extensions: tuple[str, ...]
    """Lowercase suffixes this backend claims, e.g. ``(".py", ".pyi")``."""

    fidelity: str
    """``"ast"`` or ``"regex"`` -- reported alongside results so consumers know
    how much to trust them. The README's language-support table is generated
    from this rather than hand-maintained and drifting out of date."""

    def symbols(self, source: str, path: str) -> Symbols:
        """Everything defined in the file."""
        ...

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        """Every import as written, unresolved."""
        ...

    def interface(self, source: str, path: str) -> Interface:
        """The file's public surface."""
        ...


class BaseParser:
    """Convenience base: implement `symbols`/`imports`, get `interface` free.

    Backends whose privacy rule is "the language's default convention" need
    only define the first two methods. Languages with an explicit export
    mechanism (Python's ``__all__``, JS ``export``) override `interface` to
    honour the declaration.
    """

    name: str = "unknown"
    extensions: tuple[str, ...] = ()
    fidelity: str = "regex"

    def symbols(self, source: str, path: str) -> Symbols:  # pragma: no cover
        raise NotImplementedError

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        return self.symbols(source, path).imports

    def interface(self, source: str, path: str) -> Interface:
        return Interface.from_symbols(self.symbols(source, path))

    def __repr__(self) -> str:  # pragma: no cover
        return f"<{type(self).__name__} {self.name} {self.fidelity}>"
