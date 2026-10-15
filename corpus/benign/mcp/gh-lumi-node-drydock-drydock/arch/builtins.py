"""Built-in architectural principles.

Each one is arithmetic over the dependency graph. None of them consult a
model, and none of them guess from naming -- a principle either has a
structural signal or it reports `not_applicable`.
"""

from __future__ import annotations

from collections import defaultdict

from .graph import DependencyGraph
from .principle import Finding, Principle, principles
from .seams import find_seams

__all__ = [
    "AcyclicDependencies",
    "PluginSeams",
    "Layering",
    "StableDependencies",
    "StableAbstractions",
    "DependencyInversion",
    "NoGodModules",
    "TestsUsePublicSurface",
]


class AcyclicDependencies:
    id = "acyclic-dependencies"
    name = "Acyclic Dependencies"
    question = "Can the modules be loaded in some order without circularity?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        if not graph.edges:
            return None
        load_cycles = graph.cycles()
        all_cycles = graph.cycles(include_deferred=True)
        deferred_only = len(all_cycles) - len(load_cycles)

        if not load_cycles:
            summary = "No circular dependencies at load time."
            if deferred_only:
                summary += (
                    f" {deferred_only} cycle(s) exist only through deferred imports "
                    "(inside functions or TYPE_CHECKING blocks), which is the "
                    "standard way to invert a registry dependency deliberately."
                )
            return Finding(
                id=self.id, name=self.name, verdict="holds", summary=summary,
                evidence={
                    "load_time_cycles": 0,
                    "deferred_only_cycles": deferred_only,
                    "load_time_edges": len(graph.load_time_edges()),
                    "deferred_edges": len(graph.edges) - len(graph.load_time_edges()),
                },
            )

        return Finding(
            id=self.id, name=self.name, verdict="violated",
            summary=f"{len(load_cycles)} circular dependencies at load time.",
            evidence={
                "load_time_cycles": len(load_cycles),
                "deferred_only_cycles": deferred_only,
            },
            violations=tuple(
                {"cycle": c, "length": len(c) - 1}
                for c in sorted(load_cycles, key=len)[:20]
            ),
        )


class Layering:
    id = "layering"
    name = "Layering"
    question = "Do dependencies flow in one direction through distinct levels?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        layers = graph.layers()
        if len(graph.modules) < 3:
            return None

        # Do directories line up with depth? If a package's modules cluster at
        # one level, the layout expresses the layering; if they are scattered,
        # the layering exists in the graph but not in the folder structure.
        spread: dict[str, set[int]] = defaultdict(set)
        for fid, m in graph.metrics.items():
            spread[graph.package_of(fid)].add(m.depth)
        aligned = sum(1 for levels in spread.values() if len(levels) <= 2)

        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if len(layers) > 1 else "not_applicable",
            summary=(
                f"{len(layers)} dependency levels; "
                f"{aligned}/{len(spread)} packages sit within two adjacent levels, "
                "so the directory layout "
                + ("reflects" if aligned * 2 >= len(spread) else "does not reflect")
                + " the dependency structure."
            ),
            evidence={
                "levels": len(layers),
                "modules_per_level": {str(k): len(v) for k, v in layers.items()},
                "foundation": layers.get(0, [])[:10],
                "packages_aligned_with_levels": aligned,
                "packages_total": len(spread),
            },
        )


class StableDependencies:
    id = "stable-dependencies"
    name = "Stable Dependencies Principle"
    question = "Do modules depend in the direction of greater stability?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        edges = graph.load_time_edges()
        if not edges:
            return None
        m = graph.metrics
        offenders = [
            e for e in edges
            if e.source in m and e.target in m
            and m[e.source].instability < m[e.target].instability - 1e-9
        ]
        ratio = len(offenders) / len(edges)
        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if ratio <= 0.05 else ("partial" if ratio <= 0.2 else "violated"),
            summary=(
                f"{len(edges) - len(offenders)} of {len(edges)} load-time dependencies "
                "point toward equally or more stable modules."
            ),
            evidence={
                "edges": len(edges),
                "violating_edges": len(offenders),
                "violation_ratio": round(ratio, 3),
            },
            violations=tuple(
                {
                    "from": e.source, "to": e.target,
                    "from_instability": round(m[e.source].instability, 3),
                    "to_instability": round(m[e.target].instability, 3),
                }
                for e in sorted(
                    offenders,
                    key=lambda e: m[e.target].instability - m[e.source].instability,
                    reverse=True,
                )[:15]
            ),
        )


class StableAbstractions:
    id = "stable-abstractions"
    name = "Stable Abstractions Principle"
    question = "Are the modules everything depends on abstract rather than concrete?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        typed = [m for m in graph.metrics.values()
                 if (m.abstract_types + m.concrete_types) > 0]
        if not typed:
            return None
        pain = [m for m in typed if m.ca >= 3 and m.instability < 0.3 and m.abstractness < 0.2]
        useless = [m for m in typed if m.ca == 0 and m.abstractness > 0.8]
        return Finding(
            id=self.id, name=self.name,
            verdict="violated" if len(pain) > len(typed) * 0.25 else "holds",
            summary=(
                f"{len(pain)} module(s) are heavily depended upon but concrete "
                f"(zone of pain); {len(useless)} are abstract but unused."
            ),
            evidence={
                "modules_with_types": len(typed),
                "zone_of_pain": [m.id for m in sorted(pain, key=lambda x: -x.ca)][:10],
                "zone_of_uselessness": [m.id for m in useless][:10],
                "mean_distance_from_main_sequence": round(
                    sum(m.distance for m in typed) / len(typed), 3
                ),
            },
            violations=tuple(
                {"module": m.id, "ca": m.ca,
                 "instability": round(m.instability, 3),
                 "abstractness": round(m.abstractness, 3),
                 "note": "many modules depend on this, and it is concrete"}
                for m in sorted(pain, key=lambda x: -x.ca)[:10]
            ),
        )


class DependencyInversion:
    id = "dependency-inversion"
    name = "Dependency Inversion"
    question = "Do the most-depended-upon modules define contracts?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        # Evaluated per PACKAGE. In Go an import names a directory, so every
        # file in a widely-used package inherits its coupling; ranking files
        # individually fills the hub list with siblings from one package and
        # hides the module that actually defines the contract.
        hubs = sorted(
            (m for m in graph.package_metrics().values() if m.ca >= 3),
            key=lambda m: -m.ca,
        )[:10]
        if not hubs:
            return None
        with_contracts = [m for m in hubs if m.abstract_types > 0]
        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if len(with_contracts) >= max(1, len(hubs) // 3) else "partial",
            summary=(
                f"{len(with_contracts)} of the {len(hubs)} most-depended-upon packages "
                "define an abstract contract (Protocol, ABC, trait or interface)."
            ),
            evidence={
                "hubs": [
                    {"package": m.id, "ca": m.ca,
                     "abstract_types": m.abstract_types,
                     "concrete_types": m.concrete_types}
                    for m in hubs
                ],
            },
        )


class NoGodModules:
    id = "no-god-modules"
    name = "No God Modules"
    question = "Is any single module a bottleneck for the rest?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        if len(graph.modules) < 8:
            return None
        n = len(graph.modules)
        # A module both depended on by, and depending on, a large share of the
        # codebase is a chokepoint regardless of its size.
        gods = [
            m for m in graph.metrics.values()
            if m.ca >= n * 0.25 and m.ce >= n * 0.25
        ]
        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if not gods else "violated",
            summary=(
                "No module is both widely depended upon and widely dependent."
                if not gods else
                f"{len(gods)} module(s) sit at the centre of the graph in both directions."
            ),
            evidence={
                "modules": n,
                "threshold_ca_ce": round(n * 0.25, 1),
                "widest_fan_in": [
                    {"module": m.id, "ca": m.ca}
                    for m in sorted(graph.metrics.values(), key=lambda x: -x.ca)[:5]
                ],
                "widest_fan_out": [
                    {"module": m.id, "ce": m.ce}
                    for m in sorted(graph.metrics.values(), key=lambda x: -x.ce)[:5]
                ],
            },
            violations=tuple({"module": m.id, "ca": m.ca, "ce": m.ce} for m in gods),
        )


class TestsUsePublicSurface:
    id = "tests-use-public-surface"
    name = "Tests Target the Public Surface"
    question = "Do tests exercise public entry points, or reach into internals?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        tests = [fid for fid, sf in graph.modules.items() if sf.role == "test"]
        if not tests:
            return None
        private_reach = []
        for t in tests:
            for target in sorted(graph.forward.get(t, ())):
                name = target.rsplit("/", 1)[-1]
                if name.startswith("_") and not name.startswith("__"):
                    private_reach.append({"test": t, "imports": target})
        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if not private_reach else "partial",
            summary=(
                f"{len(tests)} test modules; "
                f"{len(private_reach)} import a private module directly."
            ),
            evidence={
                "test_modules": len(tests),
                "private_imports": len(private_reach),
                "mean_imports_per_test": round(
                    sum(len(graph.forward.get(t, ())) for t in tests) / len(tests), 2
                ),
            },
            violations=tuple(private_reach[:10]),
        )


class PluginSeams:
    id = "plugin-seams"
    name = "Plugin Seams"
    question = "Are there contracts with implementations that could be lifted out whole?"

    def evaluate(self, graph: DependencyGraph) -> Finding | None:
        ctx = getattr(graph, "_ctx", None)
        if ctx is None:
            return None
        seams = find_seams(ctx, graph)
        if not seams:
            # No declared contract with implementers. That is a real finding
            # about the codebase, not a failure to measure -- but it is only
            # meaningful if there was something to measure at all.
            if not graph.edges:
                return None
            return Finding(
                id=self.id, name=self.name, verdict="not_applicable",
                summary=(
                    "No contract with two or more implementations. Components "
                    "here have no declared plug point to be lifted out along."
                ),
                evidence={"seams": 0, "modules": len(graph.modules)},
            )

        clean = [s for s in seams if s.verdict in ("clean", "extractable")]
        entangled = [s for s in seams if s.verdict == "entangled"]
        return Finding(
            id=self.id, name=self.name,
            verdict="holds" if clean else "partial",
            summary=(
                f"{len(seams)} contract(s) with implementations; "
                f"{len(clean)} could be extracted largely intact, "
                f"{len(entangled)} are declared but entangled with the rest of "
                "the codebase."
            ),
            evidence={
                "seams": [s.as_dict() for s in seams[:10]],
                "cleanest": seams[0].contract,
                "cleanest_cohesion": round(seams[0].cohesion, 3),
            },
            violations=tuple(
                {"contract": s.contract, "implementers": len(s.implementers),
                 "escapes": len(s.escapes), "cohesion": round(s.cohesion, 3),
                 "note": "a plug point exists, but its implementations are not decoupled"}
                for s in entangled[:5]
            ),
        )


for _p in (
    AcyclicDependencies(), Layering(), StableDependencies(), StableAbstractions(),
    DependencyInversion(), NoGodModules(), TestsUsePublicSurface(), PluginSeams(),
):
    principles.register(_p)
