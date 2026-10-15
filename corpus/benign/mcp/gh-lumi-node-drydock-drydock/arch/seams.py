"""Detection of plugin-shaped seams: where a codebase can be cut cleanly.

A seam is a contract plus the modules that implement it. It is the shape that
makes a component both **extractable** and **pluggable**, which are the same
property read in two directions: if a group of modules depends on one declared
contract and little else, you can lift it out, and whatever you lift out can
be plugged back in somewhere else against that same contract.

Measured, not guessed. Drydock's own `langs/base.py` scores 0.80 and is the
component that was successfully extracted into a standalone package; its
`extract/rewriters/base.py` scores 1.00 with zero escaping dependencies. The
number predicted the outcome before the extraction was attempted.

The distinction that makes the score meaningful is between a module that
*implements* a contract (declares a type deriving from it) and one that merely
*uses* it. Only implementers belong to the extractable unit; consumers stay
behind and keep depending on the contract. Counting consumers as members makes
every popular interface look like a huge, incohesive seam.

A contract can also be declared and not honoured. `internal/plugins/plugin.go`
in one real Go project has 27 dependents and 45 escaping dependencies -- a
plugin interface exists on paper, but the plugins are not actually decoupled.
That gap is worth reporting rather than smoothing over.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..core.models import FileId
from ..core.registry import AnalysisContext
from .graph import DependencyGraph

__all__ = ["Seam", "find_seams"]


@dataclass(frozen=True, slots=True)
class Seam:
    """A contract and the modules implementing it."""

    contract: FileId
    contract_types: tuple[str, ...]
    implementers: tuple[FileId, ...]
    consumers: tuple[FileId, ...]
    escapes: tuple[FileId, ...]
    """Dependencies of the unit that lie outside it -- what would come along."""

    @property
    def unit(self) -> tuple[FileId, ...]:
        return tuple(sorted({self.contract, *self.implementers}))

    @property
    def cohesion(self) -> float:
        """|unit| / (|unit| + |escapes|). 1.0 means nothing else comes with it."""
        size = len(self.unit)
        return size / (size + len(self.escapes)) if size else 0.0

    @property
    def verdict(self) -> str:
        """How honoured the contract is, structurally."""
        if not self.implementers:
            return "declared-unused"
        if self.cohesion >= 0.9:
            return "clean"
        if self.cohesion >= 0.6:
            return "extractable"
        return "entangled"

    def as_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract,
            "contract_types": list(self.contract_types),
            "implementers": list(self.implementers),
            "implementer_count": len(self.implementers),
            "consumers": list(self.consumers),
            "escapes": list(self.escapes),
            "escape_count": len(self.escapes),
            "unit_size": len(self.unit),
            "cohesion": round(self.cohesion, 3),
            "verdict": self.verdict,
        }


def find_seams(
    ctx: AnalysisContext,
    graph: DependencyGraph,
    *,
    min_implementers: int = 2,
) -> list[Seam]:
    """Find every contract-shaped seam, best first.

    Ranked by cohesion then by how many implementers the contract has, so the
    cleanest cut points come first.
    """
    contracts = _contract_types(ctx, graph)
    seams: list[Seam] = []

    for contract_id, type_names in contracts.items():
        dependents = sorted(graph.reverse.get(contract_id, ()))
        if not dependents:
            continue

        implementers = tuple(
            d for d in dependents if _implements(ctx, graph, d, type_names)
        )
        consumers = tuple(d for d in dependents if d not in set(implementers))
        if len(implementers) < min_implementers:
            continue

        unit = {contract_id, *implementers}
        escapes: set[FileId] = set()
        for member in unit:
            escapes |= graph.forward.get(member, set()) - unit

        seams.append(
            Seam(
                contract=contract_id,
                contract_types=tuple(sorted(type_names)),
                implementers=implementers,
                consumers=consumers,
                escapes=tuple(sorted(escapes)),
            )
        )

    seams.sort(key=lambda s: (-s.cohesion, -len(s.implementers), s.contract))
    return seams


def _contract_types(
    ctx: AnalysisContext, graph: DependencyGraph
) -> dict[FileId, set[str]]:
    """Modules declaring an abstract contract, and the names they declare."""
    out: dict[FileId, set[str]] = {}
    for fid, sf in graph.modules.items():
        if graph.metrics[fid].abstract_types < 1:
            continue
        sym = ctx.symbols(sf)
        if sym is None:
            continue

        # The contract SURFACE is every type the module declares, not only the
        # abstract ones. These modules almost always ship a protocol plus a
        # convenience base that implements it -- `LanguageParser` alongside
        # `BaseParser` -- and implementers derive from the base. Matching only
        # the protocol name found zero implementers for a package that plainly
        # has seven.
        names = {cls.name for cls in sym.classes}
        names |= {t.name for t in sym.types}
        if names:
            out[fid] = names
    return out


def _implements(
    ctx: AnalysisContext, graph: DependencyGraph, module: FileId, type_names: set[str]
) -> bool:
    """True if `module` declares a type deriving from one of `type_names`.

    Matched on the final segment of each base, so `base.LanguageParser` and a
    bare `LanguageParser` both count. Languages without declared inheritance
    (Go satisfies interfaces structurally) fall back to treating a dependent
    that declares any type of its own as an implementer -- imprecise, and the
    docstring says so rather than the result pretending otherwise.
    """
    sf = graph.modules.get(module)
    if sf is None:
        return False
    sym = ctx.symbols(sf)
    if sym is None:
        return False

    for cls in sym.classes:
        for base in cls.bases:
            if base.split(".")[-1].split("[")[0].strip() in type_names:
                return True

    if sf.lang == "go":
        # Go has no `implements` keyword; a type in a package that imports the
        # interface is the best structural signal available without full type
        # checking.
        return bool(sym.classes or sym.types)
    return False
