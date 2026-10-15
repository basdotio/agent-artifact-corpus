"""The import-rewriter contract.

A rewriter takes one file's source text and a map of old module path -> new
module path, and returns the text with its imports repointed, plus a count of
how many it changed.

Deliberately narrow. A rewriter does not decide what to extract, does not
touch the filesystem, and does not resolve anything -- the planner has already
worked out the mapping. That makes rewriters pure functions of (text, map),
which is what lets them be tested exhaustively without any project on disk.

Correctness bar: a rewriter must never corrupt a file. When it cannot
confidently rewrite something it must leave the text alone and report zero,
so the breakage shows up as a failed import in the extracted copy rather than
as silently mangled source. Returning the input unchanged is always a legal
answer; producing invalid syntax never is.
"""

from __future__ import annotations

from typing import Mapping, Protocol, runtime_checkable

__all__ = ["ImportRewriter", "BaseRewriter"]


@runtime_checkable
class ImportRewriter(Protocol):
    """Repoints imports in one file so the extracted copy resolves."""

    language: str

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:
        """Return (rewritten_source, number_of_imports_changed)."""
        ...


class BaseRewriter:
    """Shared helpers; subclasses implement `rewrite`."""

    language: str = "unknown"

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:  # pragma: no cover
        raise NotImplementedError

    @staticmethod
    def longest_prefix_match(
        dotted: str, module_map: Mapping[str, str]
    ) -> tuple[str, str] | None:
        """Find the most specific mapped prefix of `dotted`.

        ``pkg.sub.mod`` should prefer a mapping for ``pkg.sub`` over one for
        ``pkg``; matching the shorter prefix first would rewrite the same
        import twice or point it at the wrong package.

        Matches whole dotted segments only, so a mapping for ``pkg`` never
        matches ``pkgutil``.
        """
        best: tuple[str, str] | None = None
        for old, new in module_map.items():
            if dotted == old or dotted.startswith(old + "."):
                if best is None or len(old) > len(best[0]):
                    best = (old, new)
        return best

    @classmethod
    def remap(cls, dotted: str, module_map: Mapping[str, str]) -> str | None:
        """Rewrite one dotted path, or None if nothing maps."""
        match = cls.longest_prefix_match(dotted, module_map)
        if match is None:
            return None
        old, new = match
        suffix = dotted[len(old):]
        return new + suffix
