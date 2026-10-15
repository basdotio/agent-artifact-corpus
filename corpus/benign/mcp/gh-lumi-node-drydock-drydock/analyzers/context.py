"""Context compiler -- one-shot project understanding.

Runs every other analyzer over a single shared `AnalysisContext`, so the tree
is walked once, each file is parsed once, and every section describes the same
set of files. Pre-0.2 this orchestrator invoked six analyzers that each did
their own walk with their own skip rules, which was both slow and quietly
inconsistent: `interface_extractor` excluded tests while its siblings included
them, and nothing in the output said so.

Two other things it now does honestly:

* ``--budget`` actually trims. The old flag was accepted, documented as
  "max ~5000 lines", threaded through the call and never read -- output was
  byte-identical at ``--budget 10`` and ``--budget 100000``. Here it drives a
  defined sequence of trims and reports exactly which ones fired.
* Markdown renders every section. The old renderer computed the interfaces
  section and then never emitted it, so ``--markdown`` silently discarded a
  whole analyzer's work.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from ..core.output import dumps
from ..core.registry import AnalysisContext, Option, registry

__all__ = ["ContextAnalyzer"]


#: Section order is also priority order: earlier sections survive trimming
#: longest, because they are the ones that orient a reader who knows nothing
#: about the project.
SECTIONS: tuple[tuple[str, str], ...] = (
    ("structure", "structure"),
    ("platforms", "platforms"),
    ("codemap", "codemap"),
    ("interfaces", "interfaces"),
    ("boundaries", "boundaries"),
    ("architecture", "architecture"),
    ("dependencies", "dependencies"),
)


class ContextAnalyzer:
    name = "context"
    summary = "Run every analyzer at once and compile a single project briefing."
    description = """
Compile complete project context by running ALL analyzers over one shared pass.

This is the "understand everything" tool: use it first when dropped into an
unfamiliar codebase. Returns structure, detected platforms, a code map with
classes and functions, public interfaces per module, component boundaries with
extraction risk, the architectural principles the codebase holds to (with the
evidence for each), and the dependency picture -- plus the project's own README
and architecture docs.

Every section reports its own status, so a section that failed is visibly
absent rather than silently empty. Use `budget` to cap the size of the result
when feeding it into a limited context window; the response records which
trims were applied.
""".strip()

    options: tuple[Option, ...] = (
        Option("budget", int, 0, minimum=0,
               help="Target output size in lines (0 = no limit). Trims detail "
                    "progressively and reports what it dropped."),
        Option("skip", str, "",
               help="Comma-separated section names to skip "
                    "(structure,platforms,codemap,interfaces,boundaries,architecture,dependencies)"),
        Option("include_docs", bool, True,
               help="Include README / architecture doc excerpts"),
        Option("doc_lines", int, 60, minimum=1,
               help="Max lines to keep from each project doc"),
    )

    # -- run ---------------------------------------------------------------

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        budget = int(opts.get("budget") or 0)
        skip = {s.strip() for s in str(opts.get("skip") or "").split(",") if s.strip()}
        include_docs = bool(opts.get("include_docs", True))
        doc_lines = int(opts.get("doc_lines") if opts.get("doc_lines") is not None else 60)

        result: dict[str, Any] = {
            "meta": ctx.meta() | {"compiler": "drydock.context", "version": _version()},
            "sections": {},
        }

        planned = [(key, aname) for key, aname in SECTIONS if key not in skip]
        for i, (key, analyzer_name) in enumerate(planned, 1):
            analyzer = registry.get(analyzer_name)
            if analyzer is None:
                result["sections"][key] = {
                    "status": "unavailable",
                    "error": f"analyzer '{analyzer_name}' is not registered",
                }
                continue

            ctx.reporter.step(f"[{i}/{len(planned)}] {key}")
            try:
                defaults = {o.name: o.default for o in analyzer.options}
                section = analyzer.run(ctx, **defaults)
                section["status"] = "ok"
                result["sections"][key] = section
            except Exception as exc:
                ctx.reporter.warn(f"{key} failed: {type(exc).__name__}: {exc}")
                result["sections"][key] = {
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }

        if include_docs:
            ctx.reporter.step("reading project docs")
            result["docs"] = _read_docs(ctx, doc_lines)

        result["language_support"] = ctx.languages.support_matrix()

        ok = sum(1 for s in result["sections"].values() if s.get("status") == "ok")
        result["meta"]["sections_ok"] = ok
        result["meta"]["sections_total"] = len(result["sections"])

        if budget:
            result["budget"] = _apply_budget(result, budget, ctx)

        return result

    # -- markdown ----------------------------------------------------------

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        meta = result.get("meta", {})
        out: list[str] = [
            f"# Project Context: {meta.get('project', '?')}",
            "",
            f"`{meta.get('root', '')}`",
            "",
            f"{meta.get('files_walked', '?')} files walked · "
            f"{meta.get('sections_ok', '?')}/{meta.get('sections_total', '?')} sections ok"
            + (" · **results are partial (file limit reached)**"
               if meta.get("truncated") else ""),
            "",
        ]

        budget = result.get("budget")
        if budget and budget.get("trims_applied"):
            out += [
                f"> Trimmed to a {budget['target_lines']}-line budget: "
                f"{', '.join(budget['trims_applied'])}.",
                "",
            ]

        # Every section gets rendered, including failures. A section that broke
        # is information; hiding it is what made the old output untrustworthy.
        for key, section in result.get("sections", {}).items():
            analyzer = registry.get(dict(SECTIONS).get(key, key))
            out.append(f"## {key.title()}")
            out.append("")
            status = section.get("status")
            if status != "ok":
                out += [f"*{status}: {section.get('error', 'no detail')}*", ""]
                continue
            if analyzer is not None:
                try:
                    body = analyzer.to_markdown(section).strip()
                except Exception as exc:  # a renderer bug must not lose the rest
                    body = f"*render failed: {type(exc).__name__}: {exc}*"
                out += [_demote_headings(body), ""]
            else:
                out += ["```json", dumps(section), "```", ""]

        support = result.get("language_support")
        if support:
            out += ["## Language Support", "",
                    "| Language | Extensions | Fidelity |",
                    "|---|---|---|"]
            for row in support:
                out.append(
                    f"| {row['language']} | `{row['extensions']}` | {row['fidelity']} |"
                )
            out.append("")

        docs = result.get("docs") or {}
        if docs:
            out += ["## Project Documentation", ""]
            for filename, content in docs.items():
                out += [f"### {filename}", "", content, ""]

        return "\n".join(out)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------

def _version() -> str:
    from .. import __version__

    return __version__


def _read_docs(ctx: AnalysisContext, max_lines: int) -> dict[str, str]:
    """Excerpt the project's own documentation, largest signal first."""
    wanted = (
        "README.md", "README.rst", "README.txt", "README",
        "ARCHITECTURE.md", "DESIGN.md", "CONTRIBUTING.md",
        "docs/README.md", "docs/index.md", "docs/architecture.md",
    )
    docs: dict[str, str] = {}
    for rel in wanted:
        path = ctx.root / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        lines = text.splitlines()
        if len(lines) > max_lines:
            lines = lines[:max_lines] + ["", "*(truncated)*"]
        docs[rel] = "\n".join(lines)
    return docs


def _demote_headings(markdown: str) -> str:
    """Push a section's own headings one level down so nesting stays sane."""
    out = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            out.append("#" + line)
        else:
            out.append(line)
    return "\n".join(out)


# -- budget ----------------------------------------------------------------

def _measure(result: Mapping[str, Any]) -> int:
    return dumps(result).count("\n") + 1


def _apply_budget(result: dict[str, Any], target: int, ctx: AnalysisContext) -> dict[str, Any]:
    """Trim `result` in place until it fits `target` lines.

    Trims run in a fixed, documented order, from least to most costly in terms
    of what a reader loses. Each one that fires is recorded, so the consumer
    can tell the difference between "this project has no orphan files" and
    "the orphan list was dropped to save room".
    """
    trims: list[tuple[str, Callable[[dict[str, Any]], None]]] = [
        ("doc excerpts", _trim_docs),
        ("per-file symbol detail", _trim_codemap_detail),
        ("interface member lists", _trim_interface_detail),
        ("boundary file lists", _trim_boundary_detail),
        ("dependency file map", _trim_dependency_detail),
        ("file inventory", _trim_file_inventory),
        ("full file listing", _trim_drop_file_lists),
        ("interface bodies", _trim_drop_interface_modules),
    ]

    applied: list[str] = []
    start = _measure(result)
    for label, fn in trims:
        if _measure(result) <= target:
            break
        fn(result)
        applied.append(label)

    # Last resort: shed whole sections from the tail of the priority order.
    # Sections are dropped to a summary stub rather than deleted outright, so
    # the consumer can still see the section existed and why it is not here.
    if _measure(result) > target:
        for key, _ in reversed(SECTIONS):
            if _measure(result) <= target:
                break
            section = _section(result, key)
            if section is None:
                continue
            result["sections"][key] = {
                "status": "ok",
                "omitted_for_budget": True,
                "summary": section.get("summary", {}),
            }
            applied.append(f"{key} section body")

    final = _measure(result)
    if final > target:
        ctx.reporter.warn(
            f"could not reach the {target}-line budget; smallest form is {final} lines"
        )

    return {
        "target_lines": target,
        "initial_lines": start,
        "final_lines": final,
        "within_budget": final <= target,
        "trims_applied": applied,
        "trims_available": [label for label, _ in trims],
    }


def _section(result: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    section = result.get("sections", {}).get(key)
    return section if isinstance(section, dict) and section.get("status") == "ok" else None


def _trim_docs(result: dict[str, Any]) -> None:
    docs = result.get("docs")
    if not docs:
        return
    result["docs"] = {
        name: "\n".join(text.splitlines()[:12] + ["", "*(trimmed for budget)*"])
        for name, text in docs.items()
    }


def _trim_codemap_detail(result: dict[str, Any]) -> None:
    section = _section(result, "codemap")
    if not section:
        return
    for entry in section.get("files", []) or []:
        for key in ("classes", "structs"):
            items = entry.get(key)
            if isinstance(items, list):
                entry[key] = [
                    {"name": c.get("name"), "methods": len(c.get("methods", []) or [])}
                    for c in items if isinstance(c, dict)
                ]
        for key in ("functions", "types", "constants", "exports"):
            items = entry.get(key)
            if isinstance(items, list):
                entry[key] = [
                    c.get("name") if isinstance(c, dict) else c for c in items
                ]
    section["_trimmed"] = "symbol detail reduced to names"


def _trim_interface_detail(result: dict[str, Any]) -> None:
    section = _section(result, "interfaces")
    if not section:
        return
    modules = section.get("modules")
    if isinstance(modules, dict):
        for name, iface in modules.items():
            if not isinstance(iface, dict):
                continue
            for key in ("classes", "functions", "types", "constants", "exports"):
                items = iface.get(key)
                if isinstance(items, list):
                    iface[key] = [
                        c.get("name") if isinstance(c, dict) else c for c in items
                    ]
    section["_trimmed"] = "interface members reduced to names"


def _trim_boundary_detail(result: dict[str, Any]) -> None:
    section = _section(result, "boundaries")
    if not section:
        return
    for cluster in section.get("clusters", []) or []:
        files = cluster.get("files")
        if isinstance(files, list) and len(files) > 5:
            cluster["files"] = files[:5]
            cluster["files_omitted"] = len(files) - 5
    for key in ("orphans", "bridges", "import_graph"):
        value = section.get(key)
        if isinstance(value, (list, dict)) and len(value) > 10:
            section[key] = (
                value[:10] if isinstance(value, list)
                else dict(list(value.items())[:10])
            )
            section[f"{key}_omitted"] = True
    section["_trimmed"] = "boundary lists capped"


def _trim_dependency_detail(result: dict[str, Any]) -> None:
    section = _section(result, "dependencies")
    if not section:
        return
    for key in ("file_imports", "internal_graph"):
        if key in section:
            section.pop(key, None)
            section[f"{key}_omitted"] = True
    section["_trimmed"] = "per-file dependency map dropped"


def _trim_drop_file_lists(result: dict[str, Any]) -> None:
    """Drop the per-file listing entirely, keeping only aggregate counts."""
    section = _section(result, "codemap")
    if section and isinstance(section.get("files"), list):
        section["files_omitted"] = len(section["files"])
        section["files"] = []
        section["_trimmed"] = "file listing dropped; see summary for counts"


def _trim_drop_interface_modules(result: dict[str, Any]) -> None:
    """Drop interface module bodies, keeping the per-language summary."""
    section = _section(result, "interfaces")
    if not section:
        return
    modules = section.get("modules")
    if isinstance(modules, dict) and modules:
        section["modules_omitted"] = sum(
            len(v) if isinstance(v, list) else 1 for v in modules.values()
        )
        section["modules"] = {}
        section["_trimmed"] = "module bodies dropped; see summary for counts"


def _trim_file_inventory(result: dict[str, Any]) -> None:
    section = _section(result, "codemap")
    if not section:
        return
    files = section.get("files")
    if isinstance(files, list) and len(files) > 40:
        section["files"] = files[:40]
        section["files_omitted"] = len(files) - 40
    structure = _section(result, "structure")
    if structure:
        for key in ("largest_files", "tree"):
            if key in structure:
                structure.pop(key, None)
                structure[f"{key}_omitted"] = True
    section["_trimmed"] = "file inventory capped"
