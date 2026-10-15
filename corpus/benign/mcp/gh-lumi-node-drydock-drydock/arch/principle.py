"""The architectural-principle contract.

A principle answers one question about a codebase and shows its working. The
contract forces that: a `Finding` cannot be returned without the `evidence`
that produced it.

This is the whole design constraint. An architectural claim without its
supporting data is an opinion, and a tool meant for learning from other
people's code cannot afford to emit opinions the reader has no way to check.
"Uses dependency injection" is not useful; "31 of 34 service constructors take
a Protocol, here they are, and the 3 that do not are X, Y, Z" is.

Principles are plugins, registered the same way analyzers and language
backends are, so a new one is additive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

from .graph import DependencyGraph

__all__ = ["Verdict", "Finding", "Principle", "PrincipleRegistry", "principles"]

Verdict = Literal["holds", "violated", "partial", "not_applicable"]


@dataclass(frozen=True, slots=True)
class Finding:
    """One principle's assessment, inseparable from its evidence."""

    id: str
    name: str
    verdict: Verdict
    summary: str
    """One sentence, stating the fact rather than advising."""

    evidence: dict[str, Any] = field(default_factory=dict)
    """The numbers and module lists the verdict was computed from. Always
    populated -- a Finding without evidence is not a finding."""

    violations: tuple[dict[str, Any], ...] = ()
    """Concrete counterexamples, each naming the modules involved."""

    derived: Literal["deterministic", "heuristic"] = "deterministic"
    """How the verdict was reached. Everything built in is deterministic;
    the field exists so that anything less certain must say so explicitly
    rather than blending in."""

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "verdict": self.verdict,
            "summary": self.summary,
            "derived": self.derived,
            "evidence": self.evidence,
            "violations": list(self.violations),
        }


@runtime_checkable
class Principle(Protocol):
    """Assesses one architectural property of a dependency graph."""

    id: str
    name: str
    question: str
    """What this principle actually asks, in plain words -- shown in output so
    a reader learning from the report knows what was measured."""

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        """Return a Finding, or None when the codebase gives no signal."""
        ...


class PrincipleRegistry:
    GROUP = "drydock.principles"

    def __init__(self) -> None:
        self._items: dict[str, Principle] = {}
        self._loaded = False

    def register(self, principle: Principle) -> Principle:
        self._items[principle.id] = principle
        return principle

    def _load(self) -> None:
        if self._loaded:
            return
        self._loaded = True
        # Imported as `builtins`, not `principles`: this module already
        # exports a registry object named `principles`, and the package
        # attribute shadowed the module of the same name so nothing loaded.
        from . import builtins as _builtin  # noqa: F401

        try:
            from importlib.metadata import entry_points
        except ImportError:  # pragma: no cover
            return
        try:
            eps = entry_points(group=self.GROUP)
        except TypeError:  # pragma: no cover
            eps = entry_points().get(self.GROUP, [])  # type: ignore[attr-defined]
        for ep in eps:
            if ep.name in self._items:
                continue
            try:
                self.register(ep.load()())
            except Exception:
                continue

    def all(self) -> dict[str, Principle]:
        self._load()
        return dict(sorted(self._items.items()))


principles = PrincipleRegistry()
