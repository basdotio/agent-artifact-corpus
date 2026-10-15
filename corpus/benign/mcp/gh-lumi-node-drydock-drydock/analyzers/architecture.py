"""Architecture analyzer: the design facts of a codebase, with their evidence.

Answers "how is this built, and on what principles?" without inference. Every
verdict is arithmetic over the import graph and the symbol table, and every
verdict ships the numbers it was computed from, so a reader can check it rather
than take it on trust.

That constraint is the point. Drydock is meant to be usable for learning from
other people's codebases, and an architectural claim nobody can verify is worse
than no claim -- it teaches confidently wrong things. "Uses dependency
inversion" is an opinion; "7 of the 10 most-depended-upon modules define a
Protocol, here they are" is a fact.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..arch.graph import build_graph
from ..arch.principle import Finding, principles
from ..core.registry import AnalysisContext, Option

__all__ = ["ArchitectureAnalyzer"]

_VERDICT_MARK = {
    "holds": "holds",
    "violated": "violated",
    "partial": "partial",
    "not_applicable": "n/a",
}


class ArchitectureAnalyzer:
    name = "architecture"
    summary = "Derive architectural principles and design facts, with evidence."
    description = """
Extract the architecture of a codebase as checkable facts rather than prose.

Builds the internal dependency graph and reports: whether dependencies are
acyclic at load time, how many layers they form, whether they flow toward
stable modules, whether the most-depended-upon modules define abstract
contracts, whether any module is a chokepoint, and whether tests target the
public surface.

Every finding carries the evidence it was derived from -- module names, counts
and ratios -- so the claim can be verified. Nothing here is inferred or
guessed; the analysis is deterministic, and identical input yields identical
output.

Distinguishes load-time imports from deferred ones (inside functions or
TYPE_CHECKING blocks), because a cycle that exists only through a deferred
import is a deliberate inversion rather than a circular dependency.

Use this to understand an unfamiliar codebase's design, to compare the design
of several projects, or to check whether a change has degraded the structure.
""".strip()

    options: tuple[Option, ...] = (
        Option("only", str, "",
               help="Comma-separated verdicts to report "
                    "(holds,violated,partial,not_applicable); default reports all"),
        Option("include_metrics", bool, True,
               help="Include the per-module metrics table (Ca, Ce, I, A, D)"),
        Option("top", int, 15, minimum=1,
               help="How many modules to list in ranked evidence tables"),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        include_metrics = bool(opts.get("include_metrics", True))
        # `or 15` made --top 0 mean 15, because 0 is falsy.
        top = int(opts.get("top", 15) if opts.get("top") is not None else 15)
        only = {v.strip() for v in str(opts.get("only") or "").split(",") if v.strip()}

        ctx.reporter.step("building dependency graph")
        graph = build_graph(ctx)

        ctx.reporter.step("evaluating principles")
        findings: list[Finding] = []
        for principle in principles.all().values():
            try:
                finding = principle.evaluate(graph)
            except Exception as exc:
                ctx.reporter.warn(f"{principle.id} failed: {type(exc).__name__}: {exc}")
                continue
            if finding is not None and (not only or finding.verdict in only):
                findings.append(finding)

        result: dict[str, Any] = {
            "meta": ctx.meta(),
            "graph": graph.summary(),
            "principles": [f.as_dict() for f in findings],
            "verdicts": {
                v: sum(1 for f in findings if f.verdict == v)
                for v in ("holds", "violated", "partial", "not_applicable")
            },
        }

        if include_metrics:
            ranked = sorted(graph.metrics.values(), key=lambda m: (-m.ca, m.id))
            result["metrics"] = {
                "per_module": [m.as_dict() for m in ranked],
                "layers": {str(k): v for k, v in graph.layers().items()},
                "most_depended_upon": [m.as_dict() for m in ranked[:top]],
                "furthest_from_main_sequence": [
                    m.as_dict()
                    for m in sorted(graph.metrics.values(), key=lambda m: -m.distance)[:top]
                    if (m.abstract_types + m.concrete_types) > 0
                ],
            }

        if graph.unresolved:
            result["caveat"] = (
                f"{graph.unresolved} imports could not be resolved; the graph, and "
                "every conclusion drawn from it, is incomplete by that much."
            )
        return result

    # -- markdown ----------------------------------------------------------

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        meta = result.get("meta", {})
        g = result.get("graph", {})
        out: list[str] = [
            f"# Architecture: {meta.get('project', '?')}",
            "",
            f"{g.get('modules', '?')} modules · {g.get('load_time_edges', '?')} load-time "
            f"dependencies · {g.get('deferred_edges', '?')} deferred · "
            f"{g.get('layers', '?')} levels",
            "",
        ]
        if result.get("caveat"):
            out += [f"> **Caveat.** {result['caveat']}", ""]

        out += ["## Principles", ""]
        for f in result.get("principles", []):
            out += [
                f"### {f['name']} — {_VERDICT_MARK.get(f['verdict'], f['verdict'])}",
                "",
                f["summary"],
                "",
            ]
            ev = f.get("evidence") or {}
            if ev:
                out.append("<details><summary>evidence</summary>")
                out.append("")
                for k, v in ev.items():
                    out.append(f"- `{k}`: {_render(v)}")
                out.append("")
                out.append("</details>")
                out.append("")
            for viol in (f.get("violations") or [])[:10]:
                out.append(f"- {_render(viol)}")
            if f.get("violations"):
                out.append("")

        metrics = result.get("metrics")
        if metrics:
            out += ["## Most depended upon", "",
                    "| Module | Ca | Ce | I | A | D |", "|---|---|---|---|---|---|"]
            for m in metrics.get("most_depended_upon", []):
                out.append(
                    f"| `{m['module']}` | {m['ca']} | {m['ce']} | "
                    f"{m['instability']} | {m['abstractness']} | {m['distance']} |"
                )
            out += ["",
                    "*Ca* modules depending on this · *Ce* modules it depends on · "
                    "*I* instability · *A* abstractness · *D* distance from the "
                    "main sequence (0 is healthy).", ""]

            out += ["## Dependency levels", ""]
            for level, mods in sorted(
                metrics.get("layers", {}).items(), key=lambda kv: -int(kv[0])
            ):
                out.append(f"- **L{level}** ({len(mods)}): " +
                           ", ".join(f"`{m}`" for m in mods[:6]) +
                           (" …" if len(mods) > 6 else ""))
            out.append("")
        return "\n".join(out)


def _render(value: Any) -> str:
    if isinstance(value, list):
        if not value:
            return "none"
        if all(isinstance(v, str) for v in value):
            return ", ".join(f"`{v}`" for v in value[:8])
        return "; ".join(_render(v) for v in value[:5])
    if isinstance(value, dict):
        return ", ".join(f"{k}={_render(v)}" for k, v in value.items())
    return str(value)
