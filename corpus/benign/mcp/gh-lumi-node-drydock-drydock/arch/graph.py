"""Dependency graph and the metrics architectural facts are derived from.

Everything here is arithmetic over the import graph and the symbol table. No
inference, no heuristic scoring, no model in the loop -- which is precisely
what makes the output usable as evidence rather than opinion. When a principle
is reported as holding or violated, the numbers that decided it travel with it.

The metrics are the standard package-design ones (Martin):

    Ca  afferent coupling   how many modules depend on this one
    Ce  efferent coupling   how many modules this one depends on
    I   instability         Ce / (Ca + Ce)      0 = maximally stable
    A   abstractness        abstract types / all types
    D   distance            |A + I - 1|         0 = on the main sequence

They are computed per module rather than per package because Drydock's unit of
identity is the file, and aggregating upward is lossless while the reverse is
not.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

from ..core.models import FileId, SourceFile
from ..core.registry import AnalysisContext

__all__ = ["Edge", "ModuleMetrics", "DependencyGraph", "build_graph"]


#: Import scopes that do NOT create a load-time dependency. A cycle that exists
#: only through these is a deliberate deferral, not a circular dependency --
#: it is the standard way a registry imports its own plugins.
DEFERRED_SCOPES = frozenset({"function", "conditional"})


@dataclass(frozen=True, slots=True)
class Edge:
    source: FileId
    target: FileId
    scope: str = "module"
    raw: str = ""

    @property
    def deferred(self) -> bool:
        return self.scope in DEFERRED_SCOPES


@dataclass(frozen=True, slots=True)
class ModuleMetrics:
    id: FileId
    ca: int
    ce: int
    abstract_types: int
    concrete_types: int
    data_types: int
    depth: int
    lang: str | None = None
    role: str = "unknown"

    @property
    def instability(self) -> float:
        total = self.ca + self.ce
        return (self.ce / total) if total else 0.0

    @property
    def abstractness(self) -> float:
        """A = (contracts + data schemas) / all types.

        Data schemas count toward abstractness, not against it. A module of
        frozen dataclasses, enums or TypedDicts that everything depends on is a
        stable *contract*, not an implementation -- Martin's original A was
        about classes carrying behaviour. Counting `core/models.py` as
        maximally concrete put a pure schema module in the "zone of pain" and
        recommended, in effect, adding indirection to a set of records.
        """
        total = self.abstract_types + self.concrete_types + self.data_types
        return ((self.abstract_types + self.data_types) / total) if total else 0.0

    @property
    def distance(self) -> float:
        """Distance from the main sequence, |A + I - 1|.

        0 means the module is either stable and abstract, or unstable and
        concrete -- both healthy. Near 1 means it is in the "zone of pain"
        (stable and concrete: hard to change, much depends on it) or the "zone
        of uselessness" (abstract and nothing depends on it).
        """
        return abs(self.abstractness + self.instability - 1.0)

    def as_dict(self) -> dict[str, object]:
        return {
            "module": self.id,
            "ca": self.ca,
            "ce": self.ce,
            "instability": round(self.instability, 3),
            "abstractness": round(self.abstractness, 3),
            "abstract_types": self.abstract_types,
            "data_types": self.data_types,
            "concrete_types": self.concrete_types,
            "distance": round(self.distance, 3),
            "depth": self.depth,
            "role": self.role,
        }


@dataclass
class DependencyGraph:
    """Resolved internal dependencies plus everything derived from them."""

    modules: dict[FileId, SourceFile] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)
    forward: dict[FileId, set[FileId]] = field(default_factory=lambda: defaultdict(set))
    reverse: dict[FileId, set[FileId]] = field(default_factory=lambda: defaultdict(set))
    metrics: dict[FileId, ModuleMetrics] = field(default_factory=dict)
    unresolved: int = 0
    external: int = 0
    _ctx: Any = None
    """The AnalysisContext this graph came from. Seam detection needs the
    symbol table; every other consumer can ignore it."""

    # -- structure ---------------------------------------------------------

    def load_time_edges(self) -> list[Edge]:
        return [e for e in self.edges if not e.deferred]

    def cycles(self, *, include_deferred: bool = False) -> list[list[FileId]]:
        """Elementary-ish cycles, found by DFS back-edge detection.

        By default only load-time edges are followed, so deliberately deferred
        imports do not show up as circular dependencies.
        """
        adj: dict[FileId, set[FileId]] = defaultdict(set)
        for e in self.edges:
            if include_deferred or not e.deferred:
                adj[e.source].add(e.target)

        WHITE, GREY, BLACK = 0, 1, 2
        colour: dict[FileId, int] = defaultdict(int)
        found: list[list[FileId]] = []
        seen: set[tuple[FileId, ...]] = set()

        def visit(node: FileId, stack: list[FileId]) -> None:
            colour[node] = GREY
            stack.append(node)
            for nxt in sorted(adj.get(node, ())):
                if colour[nxt] == GREY:
                    cycle = stack[stack.index(nxt):] + [nxt]
                    key = _canonical_cycle(cycle)
                    if key not in seen:
                        seen.add(key)
                        found.append(cycle)
                elif colour[nxt] == WHITE:
                    visit(nxt, stack)
            stack.pop()
            colour[node] = BLACK

        for node in sorted(self.modules):
            if colour[node] == WHITE:
                visit(node, [])
        return found

    def layers(self) -> dict[int, list[FileId]]:
        """Modules grouped by topological depth over load-time edges.

        Depth 0 depends on nothing internal; each level above depends only on
        levels below it. Cycles are broken by treating a revisited node as
        depth 0, so a cyclic graph still yields a usable stratification.
        """
        by_level: dict[int, list[FileId]] = defaultdict(list)
        for fid in sorted(self.modules):
            by_level[self.metrics[fid].depth].append(fid)
        return dict(sorted(by_level.items()))

    def package_of(self, fid: FileId) -> str:
        return fid.rsplit("/", 1)[0] if "/" in fid else ""

    def packages(self) -> dict[str, list[FileId]]:
        out: dict[str, list[FileId]] = defaultdict(list)
        for fid in sorted(self.modules):
            out[self.package_of(fid)].append(fid)
        return dict(sorted(out.items()))

    def package_metrics(self) -> dict[str, "ModuleMetrics"]:
        """Metrics aggregated to the directory that owns each module.

        For Go the package IS the unit of dependency -- an import names a
        directory, so every file in it shares the package's afferent coupling.
        Ranking modules individually then fills the "most depended upon" list
        with several files from one package and pushes the real interface hub
        out of view. Aggregating restores the comparison the metric intends.

        Coupling is counted across package boundaries only; imports between
        files of the same package are internal detail, not coupling.
        """
        members: dict[str, list[FileId]] = defaultdict(list)
        for fid in self.modules:
            members[self.package_of(fid)].append(fid)

        owner = {fid: self.package_of(fid) for fid in self.modules}
        ca: dict[str, set[str]] = defaultdict(set)
        ce: dict[str, set[str]] = defaultdict(set)
        for e in self.load_time_edges():
            src_pkg, dst_pkg = owner.get(e.source), owner.get(e.target)
            if src_pkg is None or dst_pkg is None or src_pkg == dst_pkg:
                continue
            ce[src_pkg].add(dst_pkg)
            ca[dst_pkg].add(src_pkg)

        out: dict[str, ModuleMetrics] = {}
        for pkg, files in members.items():
            out[pkg] = ModuleMetrics(
                id=pkg or ".",
                ca=len(ca.get(pkg, ())),
                ce=len(ce.get(pkg, ())),
                abstract_types=sum(self.metrics[f].abstract_types for f in files),
                concrete_types=sum(self.metrics[f].concrete_types for f in files),
                data_types=sum(self.metrics[f].data_types for f in files),
                depth=min(self.metrics[f].depth for f in files),
                role="package",
            )
        return dict(sorted(out.items()))

    def summary(self) -> dict[str, object]:
        cycles = self.cycles()
        return {
            "modules": len(self.modules),
            "edges": len(self.edges),
            "load_time_edges": len(self.load_time_edges()),
            "deferred_edges": len(self.edges) - len(self.load_time_edges()),
            "unresolved_imports": self.unresolved,
            "external_imports": self.external,
            "cycles": len(cycles),
            "layers": len(self.layers()),
        }


def _canonical_cycle(cycle: list[FileId]) -> tuple[FileId, ...]:
    """Rotation-invariant key, so one cycle is not reported several times."""
    nodes = cycle[:-1] if len(cycle) > 1 and cycle[0] == cycle[-1] else cycle
    if not nodes:
        return ()
    start = nodes.index(min(nodes))
    return tuple(nodes[start:] + nodes[:start])


def build_graph(ctx: AnalysisContext) -> DependencyGraph:
    """Resolve every internal import and compute per-module metrics."""
    graph = DependencyGraph()
    # Seam detection needs the symbol table to tell an implementer of a
    # contract from a mere consumer of it, which the graph alone cannot say.
    # Attached rather than passed so the Principle signature stays graph-only.
    object.__setattr__(graph, "_ctx", ctx)
    index = ctx.index

    files = ctx.source_files()
    graph.modules = {sf.id: sf for sf in files}

    for sf in files:
        for imp in ctx.imports(sf):
            res = index.resolve(imp, from_file=sf.id, lang=sf.lang or "")
            if res.targets:
                for target in res.targets:
                    if target == sf.id or target not in graph.modules:
                        continue
                    graph.edges.append(
                        Edge(sf.id, target, scope=imp.scope, raw=imp.raw)
                    )
                    graph.forward[sf.id].add(target)
                    graph.reverse[target].add(sf.id)
            elif res.external:
                graph.external += 1
            elif imp.raw:
                graph.unresolved += 1

    depths = _depths(graph)
    for fid, sf in graph.modules.items():
        abstract, concrete, data = _type_counts(ctx, sf)
        graph.metrics[fid] = ModuleMetrics(
            id=fid,
            ca=len(graph.reverse.get(fid, ())),
            ce=len(graph.forward.get(fid, ())),
            abstract_types=abstract,
            concrete_types=concrete,
            data_types=data,
            depth=depths.get(fid, 0),
            lang=sf.lang,
            role=sf.role,
        )
    return graph


def _depths(graph: DependencyGraph) -> dict[FileId, int]:
    """Longest-path depth over load-time edges, cycle-safe."""
    adj = defaultdict(set)
    for e in graph.load_time_edges():
        adj[e.source].add(e.target)

    depth: dict[FileId, int] = {}

    def resolve(node: FileId, on_stack: frozenset[FileId]) -> int:
        if node in depth:
            return depth[node]
        if node in on_stack:
            return 0  # cycle: stop rather than recurse forever
        below = [resolve(m, on_stack | {node}) for m in adj.get(node, ())]
        value = 1 + max(below) if below else 0
        depth[node] = value
        return value

    for node in graph.modules:
        resolve(node, frozenset())
    return depth


_ABSTRACT_MARKERS = ("protocol", "abc", "abstract", "interface")


_DATA_MARKERS = ("namedtuple", "typeddict", "enum", "intenum", "strenum", "basemodel")
_DATA_DECORATORS = ("dataclass", "attrs", "attr.s", "define", "frozen")


def _type_counts(ctx: AnalysisContext, sf: SourceFile) -> tuple[int, int, int]:
    """(abstract, concrete, data) type counts for a module.

    Three kinds, all identified by the language's own markers and never by
    naming:

    * abstract -- a declared contract: Protocol or ABC in Python, trait in
      Rust, interface in Go/Java/C#.
    * data -- a declared schema: dataclass, NamedTuple, TypedDict, Enum,
      pydantic model, Rust/Go structs with no methods.
    * concrete -- everything else, i.e. an implementation carrying behaviour.

    A class named ``AbstractThing`` with no marker is concrete. That is
    deliberate: the moment naming is used as evidence, the output stops being
    checkable.
    """
    sym = ctx.symbols(sf)
    if sym is None:
        return (0, 0, 0)

    abstract = concrete = data = 0
    for cls in sym.classes:
        if cls.kind in ("trait", "interface"):
            abstract += 1
            continue
        bases = " ".join(cls.bases).lower()
        decorators = " ".join(cls.decorators).lower()
        if any(m in bases for m in _ABSTRACT_MARKERS) or "abstractmethod" in decorators:
            abstract += 1
        elif any(m in bases for m in _DATA_MARKERS) or any(
            d in decorators for d in _DATA_DECORATORS
        ):
            data += 1
        elif cls.kind in ("struct", "enum") and not cls.methods:
            data += 1
        else:
            concrete += 1
    for t in sym.types:
        if t.kind in ("interface", "trait"):
            abstract += 1
        elif t.kind in ("enum", "struct", "alias", "type"):
            data += 1
    return (abstract, concrete, data)
