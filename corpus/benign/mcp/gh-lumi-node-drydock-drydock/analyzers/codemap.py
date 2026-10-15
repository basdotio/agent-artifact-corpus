"""Code map analyzer - indexed inventory of every symbol in the codebase.

Produces a structured, deterministic code map showing:
- Files with languages, roles, sizes, and line counts
- Symbols extracted from each file (classes, functions, constants, types, exports)
- Language and role statistics
- Entry points (main.py, index.ts, package.json main, Cargo.toml [[bin]], etc.)

Written for AI model consumption: every symbol helps a model understand the
codebase without reading every file.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from ..core.models import Class, Constant, Export, FileId, Func, SourceFile, Symbols, TypeDef
from ..core.registry import AnalysisContext, Option
from ..core.toml import load_toml
from ..core.output import Reporter

__all__ = ["CodemapAnalyzer"]


class CodemapAnalyzer:
    """Index every file and symbol in the codebase.

    Entry points are detected by exact filename segment matching (not substring),
    plus explicit declarations in package.json, pyproject.toml, and Cargo.toml.
    """

    name = "codemap"
    summary = "Indexed inventory of every symbol: classes, functions, constants, types, exports."
    description = (
        "Produces a structured code map of all files, their roles, sizes, line counts, "
        "and extracted symbols (classes with methods/bases, functions with signatures, "
        "constants, type definitions, exports). Includes language and role statistics, "
        "detected entry points, and surfaces any truncation. Use this to understand the "
        "codebase structure and find where specific symbols are defined."
    )

    options = (
        Option(
            name="max_depth",
            type=int,
            default=None,
            help="Limit reported directory depth in markdown output (None = unlimited)",
        ),
        Option(
            name="include_symbols",
            type=bool,
            default=True,
            help="Include symbol details (classes, functions, etc.); set False for fast inventory",
        ),
        Option(
            name="roles",
            type=str,
            default=None,
            help="Comma-separated roles to include (e.g. 'source,test'); None = all",
        ),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Run the analyzer."""
        max_depth: int | None = opts.get("max_depth")
        include_symbols: bool = opts.get("include_symbols", True)
        roles_filter: str | None = opts.get("roles")

        ctx.reporter.step("scanning codemap")

        # Parse roles filter
        wanted_roles: frozenset[str] | None = None
        if roles_filter:
            wanted_roles = frozenset(r.strip() for r in roles_filter.split(",") if r.strip())

        # Scan all source files
        ctx.reporter.sub(f"scanning {len(ctx.source_files())} source files")
        files_data: list[dict[str, Any]] = []
        lang_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"files": 0, "lines": 0})
        role_stats: dict[str, int] = defaultdict(int)

        for sf in sorted(ctx.source_files(), key=lambda f: f.id):
            # Filter by role if requested
            if wanted_roles is not None and sf.role not in wanted_roles:
                continue

            file_entry = self._scan_file(sf, ctx, include_symbols)
            files_data.append(file_entry)

            # Update stats
            role_stats[sf.role] += 1
            if sf.lang:
                lang_stats[sf.lang]["files"] += 1
                lang_stats[sf.lang]["lines"] += file_entry.get("line_count", 0)

        # Detect entry points
        ctx.reporter.sub("detecting entry points")
        entry_points = self._find_entry_points(ctx.root, files_data)

        # Build result
        result = {
            "meta": ctx.meta(),
            "summary": {
                "files": len(files_data),
                "languages": dict(sorted(lang_stats.items())),
                "roles": dict(sorted(role_stats.items())),
                "truncated": ctx.walk.truncated,
            },
            "entry_points": sorted(entry_points, key=lambda x: x["path"]),
            "files": files_data,
        }

        return result

    def _scan_file(
        self, sf: SourceFile, ctx: AnalysisContext, include_symbols: bool
    ) -> dict[str, Any]:
        """Scan one file and return its entry."""
        entry: dict[str, Any] = {
            "id": sf.id,
            "lang": sf.lang,
            "role": sf.role,
            "size": sf.size,
            "line_count": self._count_lines(sf, ctx),
        }

        if include_symbols and sf.lang:
            sym = ctx.symbols(sf)
            if sym:
                self._add_symbols_to_entry(entry, sym)

        return entry

    def _count_lines(self, sf: SourceFile, ctx: AnalysisContext) -> int:
        """Count lines in a file by reading its source."""
        src = ctx.source(sf.id)
        if src is None:
            return 0
        return src.count("\n") + 1 if src else 0

    def _add_symbols_to_entry(self, entry: dict[str, Any], sym: Symbols) -> None:
        """Add symbol details to a file entry."""
        if sym.classes:
            entry["classes"] = [self._serialize_class(c) for c in sym.classes]
        if sym.functions:
            entry["functions"] = [self._serialize_func(f) for f in sym.functions]
        if sym.constants:
            entry["constants"] = [self._serialize_constant(c) for c in sym.constants]
        if sym.types:
            entry["types"] = [self._serialize_type(t) for t in sym.types]
        if sym.exports:
            entry["exports"] = [self._serialize_export(e) for e in sym.exports]
        if sym.package:
            entry["package"] = sym.package

    def _serialize_class(self, c: Class) -> dict[str, Any]:
        """Serialize a class."""
        return {
            "name": c.name,
            "bases": list(c.bases) if c.bases else None,
            "methods": [self._serialize_func(m) for m in c.methods] if c.methods else None,
            "class_methods": (
                [self._serialize_func(m) for m in c.class_methods]
                if c.class_methods
                else None
            ),
            "properties": (
                [self._serialize_func(p) for p in c.properties] if c.properties else None
            ),
            "kind": c.kind,
            "line": c.line,
        }

    def _serialize_func(self, f: Func) -> dict[str, Any]:
        """Serialize a function."""
        return {
            "name": f.name,
            "params": [p.render() for p in f.params] if f.params else None,
            "returns": f.returns,
            "is_async": f.is_async if f.is_async else None,
            "line": f.line,
        }

    def _serialize_constant(self, c: Constant) -> dict[str, Any]:
        """Serialize a constant."""
        return {
            "name": c.name,
            "value": c.value,
            "type": c.type,
            "line": c.line,
        }

    def _serialize_type(self, t: TypeDef) -> dict[str, Any]:
        """Serialize a type definition."""
        return {
            "name": t.name,
            "kind": t.kind,
            "definition": t.definition,
            "bases": list(t.bases) if t.bases else None,
            "line": t.line,
        }

    def _serialize_export(self, e: Export) -> dict[str, Any]:
        """Serialize an export."""
        return {
            "name": e.name,
            "source": e.source,
            "line": e.line,
        }

    def _find_entry_points(self, root: Path, files_data: list[dict[str, Any]]) -> list[dict[str, str]]:
        """Detect entry points by filename and manifest inspection."""
        entry_points: list[dict[str, str]] = []
        seen: set[str] = set()

        # Filename-based detection: match final path SEGMENT only, not substring
        indicators = [
            ("main.py", "python"),
            ("app.py", "python"),
            ("server.py", "python"),
            ("__main__.py", "python"),
            ("manage.py", "python (django)"),
            ("wsgi.py", "python (wsgi)"),
            ("asgi.py", "python (asgi)"),
            ("index.js", "javascript"),
            ("index.ts", "typescript"),
            ("server.js", "javascript"),
            ("server.ts", "typescript"),
            ("app.js", "javascript"),
            ("app.ts", "typescript"),
            ("main.rs", "rust"),
            ("lib.rs", "rust (library)"),
            ("main.go", "go"),
            ("Program.cs", "csharp"),
            ("Main.java", "java"),
        ]

        file_ids = {f["id"] for f in files_data}

        for filename, lang in indicators:
            for fid in sorted(file_ids):
                # Compare final path SEGMENT only, not a substring
                path_parts = fid.split("/")
                final_segment = path_parts[-1]

                if final_segment == filename:
                    if fid not in seen:
                        entry_points.append({"path": fid, "source": f"filename ({lang})"})
                        seen.add(fid)

        # Check package.json for main and scripts
        pkg_json_path = root / "package.json"
        if pkg_json_path.exists():
            try:
                content = pkg_json_path.read_text(encoding="utf-8")
                data = json.loads(content)

                if "main" in data:
                    main_path = data["main"]
                    if main_path not in seen:
                        entry_points.append({"path": main_path, "source": "package.json main"})
                        seen.add(main_path)

                if "bin" in data:
                    bins = data["bin"]
                    if isinstance(bins, dict):
                        for bin_path in bins.values():
                            if bin_path not in seen:
                                entry_points.append(
                                    {"path": bin_path, "source": "package.json bin"}
                                )
                                seen.add(bin_path)
                    elif isinstance(bins, str):
                        if bins not in seen:
                            entry_points.append({"path": bins, "source": "package.json bin"})
                            seen.add(bins)

                if "scripts" in data:
                    for key in ("start", "dev", "serve"):
                        if key in data["scripts"]:
                            script_val = data["scripts"][key]
                            script_path = f"package.json scripts.{key}"
                            if script_path not in seen:
                                entry_points.append(
                                    {"path": script_path, "source": script_val[:60]}
                                )
                                seen.add(script_path)
            except (OSError, ValueError):
                pass

        # Check pyproject.toml for [project.scripts] and [project.entry-points]
        pyproject_path = root / "pyproject.toml"
        if pyproject_path.exists():
            # `load_toml` returns None when no TOML parser exists (Python
            # 3.10 without the optional backport) instead of raising. The
            # guarded import used to live here, and the `except` below listed
            # only (OSError, ValueError) -- which does not catch
            # ModuleNotFoundError -- so this analyzer crashed outright on a
            # clean 3.10 install.
            data = load_toml(pyproject_path)
            if data is not None:
                project = data.get("project", {})
                if "scripts" in project:
                    for name, value in project["scripts"].items():
                        entry_path = f"pyproject.toml scripts.{name}"
                        if entry_path not in seen:
                            entry_points.append(
                                {"path": entry_path, "source": value[:60]}
                            )
                            seen.add(entry_path)

                if "entry-points" in project:
                    for group_name, group_entries in project["entry-points"].items():
                        for name, value in group_entries.items():
                            entry_path = f"pyproject.toml entry-points.{group_name}.{name}"
                            if entry_path not in seen:
                                entry_points.append(
                                    {"path": entry_path, "source": value[:60]}
                                )
                                seen.add(entry_path)

        # Check Cargo.toml for [[bin]]
        cargo_path = root / "Cargo.toml"
        if cargo_path.exists():
            data = load_toml(cargo_path)
            if data is not None:
                if "bin" in data:
                    for bin_entry in data["bin"]:
                        if "path" in bin_entry:
                            bin_path = bin_entry["path"]
                            if bin_path not in seen:
                                bin_name = bin_entry.get("name", "bin")
                                entry_points.append(
                                    {"path": bin_path, "source": f"Cargo.toml [[bin]] {bin_name}"}
                                )
                                seen.add(bin_path)

        return entry_points

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render result as markdown."""
        lines: list[str] = []

        # Header
        meta = result.get("meta", {})
        project = meta.get("project", "project")
        lines.append(f"# Code Map: {project}")
        lines.append("")

        # Summary
        summary = result.get("summary", {})
        lines.append("## Summary")
        lines.append("")
        lines.append(f"**Files:** {summary.get('files', 0)}")

        if summary.get("truncated"):
            lines.append("**Status:** Results truncated (raise --max-files for complete scan)")

        lines.append("")

        # Languages
        langs = summary.get("languages", {})
        if langs:
            lines.append("### Languages")
            lines.append("")
            lines.append("| Language | Files | Lines |")
            lines.append("|----------|-------|-------|")

            for lang in sorted(langs.keys()):
                stats = langs[lang]
                files = stats.get("files", 0)
                line_count = stats.get("lines", 0)
                lines.append(f"| {lang} | {files} | {line_count:,} |")

            lines.append("")

        # Roles
        roles = summary.get("roles", {})
        if roles:
            lines.append("### Roles")
            lines.append("")
            lines.append("| Role | Files |")
            lines.append("|------|-------|")

            for role in sorted(roles.keys()):
                count = roles[role]
                lines.append(f"| {role} | {count} |")

            lines.append("")

        # Entry points
        entry_points = result.get("entry_points", [])
        if entry_points:
            lines.append("## Entry Points")
            lines.append("")

            for ep in entry_points:
                path = ep.get("path", "")
                source = ep.get("source", "")
                lines.append(f"- `{path}` ({source})")

            lines.append("")

        # Files grouped by directory
        files_list = result.get("files", [])
        if files_list:
            lines.append("## Files")
            lines.append("")

            # Group by top-level directory
            by_dir: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for f in files_list:
                fid = f.get("id", "")
                parts = fid.split("/")
                dir_key = parts[0] if len(parts) > 1 else "."
                by_dir[dir_key].append(f)

            for dir_name in sorted(by_dir.keys()):
                dir_files = by_dir[dir_name]
                lines.append(f"### {dir_name}/")
                lines.append("")

                for f in sorted(dir_files, key=lambda x: x.get("id", "")):
                    fid = f.get("id", "")
                    lang = f.get("lang", "?")
                    role = f.get("role", "?")
                    size = f.get("size", 0)
                    line_count = f.get("line_count", 0)

                    # Collect symbol summary
                    symbols: list[str] = []

                    classes = f.get("classes", [])
                    for c in classes:
                        name = c.get("name", "?")
                        methods = c.get("methods", [])
                        method_count = len(methods) if methods else 0
                        symbols.append(f"class `{name}` [{method_count}m]")

                    functions = f.get("functions", [])
                    for func in functions:
                        name = func.get("name", "?")
                        symbols.append(f"fn `{name}`")

                    constants = f.get("constants", [])
                    for const in constants:
                        name = const.get("name", "?")
                        symbols.append(f"const `{name}`")

                    types = f.get("types", [])
                    for typ in types:
                        name = typ.get("name", "?")
                        kind = typ.get("kind", "type")
                        symbols.append(f"{kind} `{name}`")

                    exports = f.get("exports", [])
                    for exp in exports:
                        name = exp.get("name", "?")
                        symbols.append(f"export `{name}`")

                    symbol_str = ""
                    if symbols:
                        symbol_str = f" — {'; '.join(symbols[:5])}"
                        if len(symbols) > 5:
                            symbol_str += f" +{len(symbols) - 5}"

                    lines.append(
                        f"- `{fid}` ({lang}/{role}, {size:,}B, {line_count} lines){symbol_str}"
                    )

                lines.append("")

        return "\n".join(lines)
