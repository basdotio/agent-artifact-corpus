"""Extract public API surfaces from source code.

Answers: "What does this module/package expose?" by analyzing the public surface
of each module, including function signatures, class definitions, exported types,
and re-exports. Respects module-level declarations (__all__, export statements)
when present, otherwise applies language conventions.

Key improvements over pre-0.2:
- Private members properly filtered across all categories (was leaking constants)
- Explicit __all__ honored when declared, with `declared: true` flag
- Language support matrix generated from registry (no false claims)
- Consistent scope: uses shared walk policy, not per-analyzer skip rules
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping

from ..core.models import Class, SourceFile
from ..core.registry import AnalysisContext, Option

__all__ = ["InterfacesAnalyzer"]


class InterfacesAnalyzer:
    """Extract public API surfaces from each module in a codebase."""

    name = "interfaces"
    summary = "Extract public API surfaces from modules"
    description = (
        "Analyzes each module to identify its public surface: exported classes "
        "with their public methods, functions with signatures, type definitions, "
        "constants, and re-exports. Respects __all__ declarations when present "
        "and applies language naming conventions otherwise. Reports whether each "
        "module explicitly declared its surface and provides a language support matrix."
    )

    options = (
        Option(
            name="min_members",
            type=int,
            default=0,
            help="Omit modules exposing fewer than N public members",
        ),
        Option(
            name="include_constants",
            type=bool,
            default=True,
            help="Include module-level constants in the public surface",
        ),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Extract public interfaces from all source files."""
        min_members: int = opts.get("min_members", 0)
        include_constants: bool = opts.get("include_constants", True)

        ctx.reporter.step("Extracting public interfaces")

        # Collect interfaces by language and module
        modules_by_lang: dict[str, list[dict[str, Any]]] = defaultdict(list)
        total_modules = 0
        filtered_low_members = 0

        for sf in ctx.source_files():
            if sf.lang is None:
                continue

            interface = ctx.interface(sf)
            if interface is None:
                continue

            total_modules += 1

            # Filter constants if requested
            constants = interface.constants if include_constants else ()

            # Count public members
            member_count = (
                len(interface.classes)
                + len(interface.functions)
                + len(constants)
                + len(interface.types)
                + len(interface.exports)
            )

            if member_count < min_members:
                filtered_low_members += 1
                continue

            # Build module record
            module_dict = {
                "path": sf.id,
                "language": sf.lang,
                "declared": interface.declared,
                "classes": sorted(
                    [self._class_to_dict(c) for c in interface.classes],
                    key=lambda x: x["name"],
                ),
                "functions": sorted(
                    [self._func_to_dict(f) for f in interface.functions],
                    key=lambda x: x["name"],
                ),
                "constants": sorted(
                    [self._const_to_dict(c) for c in constants],
                    key=lambda x: x["name"],
                ),
                "types": sorted(
                    [self._type_to_dict(t) for t in interface.types],
                    key=lambda x: x["name"],
                ),
                "exports": sorted(
                    [{"name": e.name, "source": e.source} for e in interface.exports],
                    key=lambda x: x["name"],
                ),
                "public_members": member_count,
            }

            # Remove empty sections
            module_dict = {k: v for k, v in module_dict.items() if v or k == "declared"}

            modules_by_lang[sf.lang].append(module_dict)

        # Sort modules within each language by path
        for lang in modules_by_lang:
            modules_by_lang[lang].sort(key=lambda m: m["path"])

        # Count summary by language
        summary_by_lang = {}
        for lang, modules in modules_by_lang.items():
            summary_by_lang[lang] = {
                "modules": len(modules),
                "total_classes": sum(len(m.get("classes", [])) for m in modules),
                "total_functions": sum(len(m.get("functions", [])) for m in modules),
                "total_constants": sum(len(m.get("constants", [])) for m in modules),
                "total_types": sum(len(m.get("types", [])) for m in modules),
                "with_explicit_all": sum(
                    1 for m in modules if m.get("declared", False)
                ),
            }

        ctx.reporter.sub(f"extracted {total_modules} modules")
        if filtered_low_members:
            ctx.reporter.sub(
                f"filtered {filtered_low_members} modules with < {min_members} members"
            )

        return {
            "summary": {
                "total_modules_scanned": total_modules,
                "modules_reported": sum(
                    len(m) for m in modules_by_lang.values()
                ),
                "filtered_low_members": filtered_low_members,
                "include_constants": include_constants,
                "min_members": min_members,
                "by_language": summary_by_lang,
            },
            "modules": dict(modules_by_lang),
            "language_support": ctx.languages.support_matrix(),
            "meta": ctx.meta(),
        }

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render analysis result as markdown."""
        lines = [
            f"# Public Interfaces: {result['meta']['project']}",
            "",
            "## Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
        ]

        s = result["summary"]
        lines.extend([
            f"| Modules Scanned | {s['total_modules_scanned']} |",
            f"| Modules Reported | {s['modules_reported']} |",
            f"| Filtered (< {s['min_members']} members) | {s['filtered_low_members']} |",
            f"| Include Constants | {'Yes' if s['include_constants'] else 'No'} |",
            "",
        ])

        # Language summary
        if s.get("by_language"):
            lines.extend([
                "## By Language",
                "",
                "| Language | Modules | Classes | Functions | Types | With __all__ |",
                "|----------|---------|---------|-----------|-------|--------------|",
            ])
            for lang in sorted(s["by_language"].keys()):
                ls = s["by_language"][lang]
                lines.append(
                    f"| {lang} | {ls['modules']} | {ls['total_classes']} | "
                    f"{ls['total_functions']} | {ls['total_types']} | "
                    f"{ls['with_explicit_all']} |"
                )
            lines.append("")

        # Modules by language
        modules = result.get("modules", {})
        for lang in sorted(modules.keys()):
            if modules[lang]:
                lines.extend([
                    f"## {lang.title()} Modules",
                    "",
                ])
                for mod in modules[lang]:
                    lines.append(f"### `{mod['path']}`")
                    lines.append("")

                    declared = "✓ explicit `__all__`" if mod.get("declared") else "✗ by convention"
                    lines.append(f"**Declaration:** {declared}")
                    lines.append("")

                    # Classes
                    if mod.get("classes"):
                        lines.append("**Classes:**")
                        for cls in mod["classes"]:
                            methods = ", ".join(
                                m["name"] + ("(...)" if m.get("params") else "")
                                for m in cls.get("methods", [])
                            )
                            if methods:
                                methods = f" — {methods}"
                            lines.append(f"- `{cls['name']}`{methods}")
                        lines.append("")

                    # Functions
                    if mod.get("functions"):
                        lines.append("**Functions:**")
                        for func in mod["functions"]:
                            sig = self._render_func_sig(func)
                            lines.append(f"- `{sig}`")
                        lines.append("")

                    # Types
                    if mod.get("types"):
                        lines.append("**Types:**")
                        for typ in mod["types"]:
                            lines.append(f"- `{typ['name']}`")
                        lines.append("")

                    # Constants
                    if mod.get("constants"):
                        lines.append("**Constants:**")
                        for const in mod["constants"]:
                            lines.append(f"- `{const['name']}`")
                        lines.append("")

        # Language support matrix
        if result.get("language_support"):
            lines.extend([
                "## Language Support",
                "",
                "| Language | Extensions | Fidelity |",
                "|----------|-----------|----------|",
            ])
            for lang in result["language_support"]:
                lines.append(
                    f"| {lang['language']} | {lang['extensions']} | "
                    f"{lang['fidelity']} |"
                )
            lines.append("")

        return "\n".join(lines)

    # ---- helpers ----

    @staticmethod
    def _class_to_dict(cls: Class) -> dict[str, Any]:
        return {
            "name": cls.name,
            "bases": sorted(cls.bases),
            "methods": [
                {"name": m.name, "params": m.params_raw or str([p.name for p in m.params])}
                for m in cls.methods
            ],
            "class_methods": [
                {"name": m.name}
                for m in cls.class_methods
            ],
            "properties": [
                {"name": p.name}
                for p in cls.properties
            ],
        }

    @staticmethod
    def _func_to_dict(func) -> dict[str, Any]:
        return {
            "name": func.name,
            "params": [p.name for p in func.params],
            "returns": func.returns,
        }

    @staticmethod
    def _const_to_dict(const) -> dict[str, Any]:
        return {
            "name": const.name,
            "value": const.value,
            "type": const.type,
        }

    @staticmethod
    def _type_to_dict(typ) -> dict[str, Any]:
        return {
            "name": typ.name,
            "kind": typ.kind,
            "definition": typ.definition,
        }

    @staticmethod
    def _render_func_sig(func_dict: dict[str, Any]) -> str:
        params = ", ".join(func_dict.get("params", []))
        sig = f"{func_dict['name']}({params})"
        if func_dict.get("returns"):
            sig += f" -> {func_dict['returns']}"
        return sig
