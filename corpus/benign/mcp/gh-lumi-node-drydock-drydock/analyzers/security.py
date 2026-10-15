"""Architectural security analyzer.

Answers the questions a vulnerability scanner cannot, because they need a
resolved dependency graph rather than a package manifest:

  who can reach the code that handles credentials?
  can a module that accepts outside input reach a subprocess call?
  how much third-party code does the sensitive path drag in?

Deliberately not a vulnerability scanner. Snyk, Semgrep and GitHub Advanced
Security already match CVEs better than this ever would, and duplicating them
would add noise without adding information.

Every finding carries the evidence and, where a claim is about a path, the
path itself. And every finding is bounded by one honest limitation, repeated in
the output rather than buried here: **this sees imports, not data flow.** A
route from an ingress module to a subprocess module means the dependency graph
contains such a route -- somewhere to look, not proof of exploitability. A
security report that overstates its certainty is worse than no report, because
it spends attention that had somewhere better to go.
"""

from __future__ import annotations

from typing import Any, Mapping

from ..arch.graph import build_graph
from ..arch.security import (
    DANGEROUS_PATHS,
    SENSITIVITY,
    classify,
    external_surface,
    path_between,
    reaches,
)
from ..core.registry import AnalysisContext, Option

__all__ = ["SecurityAnalyzer"]

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}


class SecurityAnalyzer:
    name = "security"
    summary = "Architectural security: reachability, blast radius, supply-chain surface."
    description = """
Structural security analysis over the dependency graph -- not vulnerability
scanning.

Reports which modules handle credentials, accept external input, execute code
or deserialize data, classified by the imports they actually make rather than
by their names. Then answers the questions that need a graph: how much of the
codebase can reach the sensitive modules (blast radius), whether a module
accepting outside input can reach a subprocess call or a deserializer (with
the import path shown), and how much third-party code the sensitive paths pull
in transitively.

Complements a vulnerability scanner rather than replacing one: it finds
structural exposure, not known CVEs.

Important limitation, also stated in the output: this analyses imports, not
data flow. A reported path means the dependency graph contains that route, not
that untrusted input demonstrably reaches the call. Treat findings as places
to look.
""".strip()

    options: tuple[Option, ...] = (
        Option("max_paths", int, 5, minimum=1,
               help="How many example paths to show per finding"),
        Option("path_limit", int, 6, minimum=2,
               help="Longest import chain to search when looking for a path"),
        Option("include_hashing", bool, False,
               help="Treat hashing (often checksums) as sensitive too"),
        # NOT `include_tests`: that name is already the shared --no-tests
        # scope flag, whose dest is `include_tests` and whose default is True,
        # so an analyzer Option of that name is silently overwritten by it.
        Option("include_test_modules", bool, False,
               help="Classify test modules too; they are not deployed, so they "
                    "are excluded by default"),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        max_paths = int(opts.get("max_paths", 5))
        path_limit = int(opts.get("path_limit", 6))
        include_hashing = bool(opts.get("include_hashing", False))
        include_test_modules = bool(opts.get("include_test_modules", False))

        ctx.reporter.step("building dependency graph")
        graph = build_graph(ctx)

        ctx.reporter.step("classifying modules by sensitive imports")
        classified = classify(ctx, graph, include_tests=include_test_modules)

        by_class: dict[str, set[str]] = {k: set() for k in SENSITIVITY}
        for fid, c in classified.items():
            for cls in c.classes:
                by_class[cls].add(fid)
        if not include_hashing:
            by_class.pop("hashing", None)

        findings: list[dict[str, Any]] = []

        ctx.reporter.step("tracing dangerous paths")
        findings += self._dangerous_paths(graph, by_class, max_paths, path_limit)

        ctx.reporter.step("measuring blast radius")
        findings += self._blast_radius(graph, by_class)

        ctx.reporter.step("measuring supply-chain surface")
        findings += self._supply_chain(ctx, graph, by_class)

        findings.sort(key=lambda f: (_SEVERITY_ORDER.get(f["severity"], 9), f["id"]))

        return {
            "meta": ctx.meta(),
            "summary": {
                "modules": len(graph.modules),
                "classified": len(classified),
                "tests_included": include_test_modules,
                "by_class": {k: len(v) for k, v in sorted(by_class.items())},
                "findings": len(findings),
                "by_severity": {
                    s: sum(1 for f in findings if f["severity"] == s)
                    for s in ("high", "medium", "low", "info")
                },
            },
            "classified": [c.as_dict() for c in
                           sorted(classified.values(), key=lambda x: x.module)],
            "findings": findings,
            "limitation": (
                "Imports are analysed, not data flow. A reported path exists in "
                "the dependency graph; it is not evidence that untrusted input "
                "reaches the call. Use these as places to look."
            ),
        }

    # -- findings ----------------------------------------------------------

    def _dangerous_paths(self, graph, by_class, max_paths, path_limit) -> list[dict]:
        out = []
        for src_cls, dst_cls, why in DANGEROUS_PATHS:
            sources = by_class.get(src_cls) or set()
            targets = by_class.get(dst_cls) or set()
            if not sources or not targets:
                continue
            paths = []
            for src in sorted(sources):
                if src in targets:
                    continue  # same module: not a path worth reporting
                p = path_between(graph, src, targets, limit=path_limit)
                if p:
                    paths.append({"from": p[0], "to": p[-1], "hops": len(p) - 1,
                                  "path": p})
                if len(paths) >= max_paths:
                    break
            if paths:
                out.append({
                    "id": f"path-{src_cls}-to-{dst_cls}",
                    "title": f"{src_cls} can reach {dst_cls}",
                    "severity": "high" if dst_cls in ("execution", "deserialization") else "medium",
                    "summary": (
                        f"{len(paths)} module(s) classified `{src_cls}` have an "
                        f"import path to a module classified `{dst_cls}` -- {why}."
                    ),
                    "evidence": {
                        f"{src_cls}_modules": len(sources),
                        f"{dst_cls}_modules": len(targets),
                        "paths_found": len(paths),
                    },
                    "paths": paths,
                })
        return out

    def _blast_radius(self, graph, by_class) -> list[dict]:
        out = []
        total = max(len(graph.modules), 1)
        for cls in ("secrets", "execution"):
            mods = by_class.get(cls) or set()
            if not mods:
                continue
            radius = reaches(graph, mods) - mods
            share = len(radius) / total
            out.append({
                "id": f"blast-radius-{cls}",
                "title": f"blast radius of {cls} modules",
                "severity": "medium" if share > 0.5 else "low",
                "summary": (
                    f"{len(radius)} of {total} modules ({share:.0%}) can reach the "
                    f"{len(mods)} module(s) handling {cls}."
                ),
                "evidence": {
                    f"{cls}_modules": sorted(mods),
                    "reachable_from_count": len(radius),
                    "share_of_codebase": round(share, 3),
                    "sample": sorted(radius)[:10],
                },
            })
        return out

    def _supply_chain(self, ctx, graph, by_class) -> list[dict]:
        out = []
        for cls in ("secrets", "ingress"):
            mods = by_class.get(cls) or set()
            if not mods:
                continue
            packages = external_surface(ctx, graph, mods)
            out.append({
                "id": f"supply-chain-{cls}",
                "title": f"third-party surface reachable from {cls} code",
                "severity": "medium" if len(packages) > 30 else "info",
                "summary": (
                    f"code classified `{cls}` transitively depends on "
                    f"{len(packages)} third-party package(s)."
                ),
                "evidence": {
                    "modules": sorted(mods)[:10],
                    "package_count": len(packages),
                    "packages": sorted(packages)[:40],
                },
            })
        return out

    # -- markdown ----------------------------------------------------------

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        s = result.get("summary", {})
        out = [
            f"# Architectural security: {result.get('meta',{}).get('project','?')}",
            "",
            f"{s.get('classified','?')} of {s.get('modules','?')} modules touch "
            f"something security-relevant · {s.get('findings','?')} findings",
            "",
            f"> {result.get('limitation','')}",
            "",
            "## Modules by class",
            "",
            "| Class | Modules |", "|---|---|",
        ]
        for cls, n in (s.get("by_class") or {}).items():
            out.append(f"| `{cls}` | {n} |")
        out += ["", "## Findings", ""]
        for f in result.get("findings", []):
            out += [f"### {f['title']} — {f['severity']}", "", f["summary"], ""]
            for p in (f.get("paths") or [])[:5]:
                out.append("- " + " → ".join(f"`{x}`" for x in p["path"]))
            if f.get("paths"):
                out.append("")
            ev = f.get("evidence") or {}
            if ev:
                out += ["<details><summary>evidence</summary>", ""]
                for k, v in ev.items():
                    if isinstance(v, list):
                        v = ", ".join(f"`{x}`" for x in v[:10]) or "none"
                    out.append(f"- `{k}`: {v}")
                out += ["", "</details>", ""]
        return "\n".join(out)
