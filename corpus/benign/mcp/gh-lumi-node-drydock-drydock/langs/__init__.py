"""Language backend registry.

Backends register here and every analyzer picks them up at once. Adding a
language is one file plus one entry-point line -- no analyzer changes.
"""

from __future__ import annotations

from typing import Iterable

from .base import BaseParser, LanguageParser

__all__ = ["LanguageRegistry", "language_registry", "BaseParser", "LanguageParser"]


class LanguageRegistry:
    """Maps file suffixes to language backends."""

    GROUP = "drydock.languages"

    def __init__(self) -> None:
        self._parsers: dict[str, LanguageParser] = {}
        self._by_suffix: dict[str, LanguageParser] = {}
        self._loaded = False

    def register(self, parser: LanguageParser) -> LanguageParser:
        self._parsers[parser.name] = parser
        for ext in parser.extensions:
            # First registration wins, so a plugin cannot silently hijack a
            # suffix from a backend the user already relies on. Explicit
            # replacement goes through `replace()`.
            self._by_suffix.setdefault(ext.lower(), parser)
        return parser

    def replace(self, parser: LanguageParser) -> LanguageParser:
        """Register `parser`, taking over its suffixes from any incumbent.

        The upgrade path for an optional higher-fidelity backend, e.g. swapping
        the regex Rust reader for a tree-sitter one.
        """
        self._parsers[parser.name] = parser
        for ext in parser.extensions:
            self._by_suffix[ext.lower()] = parser
        return parser

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        from . import builtins as _builtins  # noqa: F401

        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover
            return
        try:
            eps = entry_points(group=self.GROUP)
        except TypeError:  # pragma: no cover
            eps = entry_points().get(self.GROUP, [])  # type: ignore[attr-defined]
        for ep in eps:
            if ep.name in self._parsers:
                continue
            try:
                self.register(ep.load()())
            except Exception:
                continue

    def language_for_suffix(self, suffix: str) -> str | None:
        self._load()
        parser = self._by_suffix.get(suffix.lower())
        return parser.name if parser else None

    def parser_for(self, language: str) -> LanguageParser | None:
        self._load()
        return self._parsers.get(language)

    def parser_for_suffix(self, suffix: str) -> LanguageParser | None:
        self._load()
        return self._by_suffix.get(suffix.lower())

    def all(self) -> dict[str, LanguageParser]:
        self._load()
        return dict(sorted(self._parsers.items()))

    def support_matrix(self) -> list[dict[str, str]]:
        """Machine-readable language support, so the docs table stops lying.

        The README claimed "Partial" C# and Java interface extraction that did
        not exist in any lookup table. Generating the table from the registry
        makes that class of drift impossible.
        """
        return [
            {
                "language": p.name,
                "extensions": " ".join(p.extensions),
                "fidelity": p.fidelity,
            }
            for p in self.all().values()
        ]


_REGISTRY = LanguageRegistry()


def language_registry() -> LanguageRegistry:
    return _REGISTRY
