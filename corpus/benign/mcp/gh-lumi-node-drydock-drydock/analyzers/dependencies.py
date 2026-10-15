"""
Dependency analysis: external packages, declared vs. used, most-imported modules.

Analyzes both manifest files (requirements.txt, package.json, Cargo.toml, go.mod)
and actual imports in source code to find:
  - Which external packages are declared vs. actually used
  - Which external packages are used but not declared
  - Most imported/importing modules
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from typing import Any, Mapping

from ..core.models import FileId
from ..core.output import to_jsonable
from ..core.registry import AnalysisContext, Option
from ..core.toml import loads_toml

__all__ = ["DependenciesAnalyzer"]


class DependenciesAnalyzer:
    """Analyzes project dependencies across multiple languages.

    Reads manifest files (requirements.txt, package.json, Cargo.toml, go.mod)
    and resolves actual imports to classify dependencies as:
    - Declared but unused
    - Used but undeclared
    - Properly declared and used
    - External (stdlib, third-party)
    """

    name = "dependencies"
    summary = "Analyze external and internal dependencies"
    description = (
        "Enumerates external third-party dependencies from manifests "
        "(requirements.txt, package.json, Cargo.toml, go.mod), tracks actual "
        "imports in source code, and reports declared-vs-used mismatches. "
        "Classifies internal imports by module and identifies most-imported and "
        "most-importing modules."
    )

    # Test inclusion is a *scope* concern, owned by WalkPolicy and exposed
    # once as the shared --no-tests flag. Re-declaring it here would give the
    # analyzer a second, competing switch for the same thing.
    options: tuple[Option, ...] = ()

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Run dependency analysis."""

        ctx.reporter.step("Analyzing Python dependencies")
        python_result = self._analyze_python(ctx)

        ctx.reporter.step("Analyzing JavaScript/TypeScript dependencies")
        js_result = self._analyze_javascript(ctx)

        ctx.reporter.step("Analyzing Rust dependencies")
        rust_result = self._analyze_rust(ctx)

        ctx.reporter.step("Analyzing Go dependencies")
        go_result = self._analyze_go(ctx)

        # Collect all analyses
        analyses = [r for r in [python_result, js_result, rust_result, go_result] if r]

        # Summary of all external deps
        all_external: set[str] = set()
        for analysis in analyses:
            all_external.update(analysis.get("third_party", []))
            all_external.update(analysis.get("used_packages", []))
            all_external.update(analysis.get("dependencies", {}).keys())
            all_external.update(analysis.get("requires", {}).keys())

        return {
            "summary": {
                "languages_found": sorted([a["language"] for a in analyses]),
                "total_external_deps": len(all_external),
            },
            "analyses": analyses,
            "meta": ctx.meta(),
        }

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render dependency analysis as markdown."""
        lines = [
            f"# Dependency Analysis: {result['meta']['project']}",
            "",
            "## Summary",
            "",
            f"**Languages:** {', '.join(result['summary']['languages_found'])}",
            f"**Total External Dependencies:** {result['summary']['total_external_deps']}",
            "",
        ]

        for analysis in result["analyses"]:
            lang = analysis["language"]
            lines.extend([f"## {lang.replace('/', ' / ').title()}", ""])

            # Third-party dependencies (Python)
            if "third_party" in analysis:
                lines.extend(["### Third-Party Dependencies", ""])
                if analysis["third_party"]:
                    for dep in analysis["third_party"]:
                        lines.append(f"- `{dep}`")
                    lines.append("")
                else:
                    lines.extend(["None found.", ""])

            # Declared dependencies (JS/Node)
            if "declared_deps" in analysis:
                lines.extend(["### Declared Dependencies", ""])
                if analysis["declared_deps"]:
                    lines.extend(["| Package | Version |", "|---------|---------|"])
                    for pkg, ver in sorted(analysis["declared_deps"].items()):
                        lines.append(f"| `{pkg}` | {ver} |")
                    lines.append("")
                else:
                    lines.extend(["None declared.", ""])

            # Unused declared (JS/Node)
            if analysis.get("unused_declared"):
                lines.extend(["### Unused Declared Dependencies", ""])
                for dep in analysis["unused_declared"]:
                    lines.append(f"- `{dep}`")
                lines.extend(["", ""])

            # Undeclared used (JS/Node)
            if analysis.get("undeclared_used"):
                lines.extend(["### Used But Not Declared", ""])
                for dep in analysis["undeclared_used"]:
                    lines.append(f"- `{dep}`")
                lines.extend(["", ""])

            # Cargo dependencies (Rust)
            if "dependencies" in analysis and lang.lower() == "rust":
                lines.extend(["### Cargo Dependencies", ""])
                if analysis["dependencies"]:
                    lines.extend(["| Crate | Version |", "|-------|---------|"])
                    for crate, ver in sorted(analysis["dependencies"].items()):
                        lines.append(f"| `{crate}` | {ver} |")
                    lines.append("")
                else:
                    lines.extend(["None declared.", ""])

            # Go module requirements
            if "requires" in analysis:
                lines.extend(["### Module Requirements", ""])
                if analysis["requires"]:
                    lines.extend(["| Module | Version |", "|--------|---------|"])
                    for mod, ver in sorted(analysis["requires"].items()):
                        lines.append(f"| `{mod}` | {ver} |")
                    lines.append("")
                else:
                    lines.extend(["None declared.", ""])

            # Most imported
            if analysis.get("most_imported"):
                lines.extend(["### Most Imported", ""])
                lines.extend(["| Module | Count |", "|--------|-------|"])
                for mod, count in analysis["most_imported"][:15]:
                    lines.append(f"| `{mod}` | {count} |")
                lines.append("")

            # Most importing
            if analysis.get("most_importing"):
                lines.extend(["### Most Importing", ""])
                lines.extend(["| Module | Count |", "|--------|-------|"])
                for mod, count in analysis["most_importing"][:15]:
                    lines.append(f"| `{mod}` | {count} |")
                lines.append("")

        return "\n".join(lines)

    # -- Python --------------------------------------------------------

    def _analyze_python(self, ctx: AnalysisContext) -> dict[str, Any] | None:
        """Analyze Python dependencies from manifests and imports."""
        # Check if project has Python files
        py_files = [
            sf for sf in ctx.source_files() if sf.suffix == ".py"
        ]
        if not py_files:
            return None

        ctx.reporter.sub("analyzing Python imports and manifests")

        # Get stdlib modules
        stdlib = self._get_stdlib_modules()

        # Find project packages (directories with __init__.py)
        project_packages: set[str] = set()
        for sf in py_files:
            if sf.id.endswith("__init__.py"):
                # Extract package name from __init__.py path
                parts = sf.id.split("/")[:-1]  # Remove __init__.py
                if parts:
                    project_packages.add(parts[0])  # Top-level package

        # Parse manifests
        declared_deps = self._parse_requirements(ctx)
        if not declared_deps:
            declared_deps = self._parse_pyproject(ctx)

        # Analyze actual imports
        all_third_party: set[str] = set()
        all_stdlib: set[str] = set()
        all_local: set[str] = set()
        import_graph: dict[str, set[str]] = defaultdict(set)
        imported_by: dict[str, set[str]] = defaultdict(set)

        for sf in py_files:
            imports = ctx.imports(sf)

            for imp in imports:
                # Get the top-level package name
                top_level = imp.raw.split(".")[0] if imp.raw else ""
                if not top_level:
                    continue

                # Classify
                if top_level in stdlib:
                    all_stdlib.add(top_level)
                else:
                    # Try to resolve locally
                    res = ctx.index.resolve(imp, from_file=sf.id, lang="python")
                    if res.targets:
                        all_local.add(top_level)
                    else:
                        # External
                        all_third_party.add(top_level)

                # Update graph
                module_key = sf.id.replace("/", ".").replace(".py", "")
                if imp.raw:
                    import_graph[module_key].add(imp.raw)
                    imported_by[imp.raw].add(module_key)

        # Declared vs. used
        declared_set = set(declared_deps.keys())
        unused = sorted(declared_set - all_third_party)
        undeclared = sorted(all_third_party - declared_set)

        # Most imported/importing
        most_imported = sorted(
            [(mod, len(deps)) for mod, deps in imported_by.items()],
            key=lambda x: (-x[1], x[0]),
        )[:20]
        most_importing = sorted(
            [(mod, len(deps)) for mod, deps in import_graph.items()],
            key=lambda x: (-x[1], x[0]),
        )[:20]

        return {
            "language": "python",
            "files_analyzed": len(py_files),
            "declared_dependencies": declared_deps,
            "third_party": sorted(all_third_party),
            "stdlib": sorted(all_stdlib),
            "local": sorted(all_local),
            "unused_declared": unused,
            "undeclared_used": undeclared,
            "most_imported": most_imported,
            "most_importing": most_importing,
        }

    def _parse_requirements(self, ctx: AnalysisContext) -> dict[str, str]:
        """Parse requirements.txt or requirements/*.txt."""
        reqs: dict[str, str] = {}

        for pattern in ["requirements.txt", "requirements/*.txt"]:
            # Try to find files matching pattern
            for sf in ctx.walk.files:
                if not sf.id.endswith(".txt"):
                    continue
                if "requirements" not in sf.id:
                    continue

                try:
                    src = ctx.source(sf.id)
                    if not src:
                        continue

                    for line in src.split("\n"):
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        # Parse: package==version or package>=version etc
                        m = re.match(r"^([a-zA-Z0-9_\-]+)", line)
                        if m:
                            pkg = m.group(1)
                            version = line[len(pkg) :].strip() or ""
                            reqs[pkg.lower()] = version
                except Exception:
                    pass

        return reqs

    def _parse_pyproject(self, ctx: AnalysisContext) -> dict[str, str]:
        """Parse pyproject.toml for dependencies."""
        reqs: dict[str, str] = {}

        for sf in ctx.walk.files:
            if sf.id != "pyproject.toml":
                continue

            try:
                src = ctx.source(sf.id)
                if not src:
                    continue

                # A real parse when any TOML reader exists, otherwise the
                # line-regex approximation below. `loads_toml` centralises the
                # "which reader, if any" question -- see drydock/core/toml.py.
                data = loads_toml(src)
                if data is None:
                    # Last resort: regex parsing
                    data = {}
                    for line in src.split("\n"):
                        m = re.match(r'^([a-z0-9_\-]+)\s*=', line, re.I)
                        if m:
                            pkg = m.group(1)
                            reqs[pkg.lower()] = ""

                # Extract from [project] dependencies
                if "project" in data and "dependencies" in data["project"]:
                    for dep in data["project"]["dependencies"]:
                        m = re.match(r"^([a-zA-Z0-9_\-]+)", dep)
                        if m:
                            pkg = m.group(1)
                            version = dep[len(pkg) :].strip() or ""
                            reqs[pkg.lower()] = version

                # Also check [tool.poetry] dependencies
                if "tool" in data and "poetry" in data["tool"]:
                    poetry = data["tool"]["poetry"]
                    if "dependencies" in poetry:
                        for pkg, version in poetry["dependencies"].items():
                            if pkg.lower() != "python":
                                reqs[pkg.lower()] = str(version)

            except Exception:
                pass

        return reqs

    def _get_stdlib_modules(self) -> set[str]:
        """Get Python stdlib module names."""
        if hasattr(sys, "stdlib_module_names"):
            return set(sys.stdlib_module_names)

        # Fallback for Python < 3.10
        return {
            "abc", "argparse", "ast", "asyncio", "base64", "bisect",
            "collections", "concurrent", "configparser", "contextlib",
            "copy", "csv", "ctypes", "dataclasses", "datetime", "decimal",
            "difflib", "email", "enum", "fileinput", "fnmatch", "fractions",
            "functools", "glob", "gzip", "hashlib", "heapq", "hmac", "html",
            "http", "importlib", "inspect", "io", "ipaddress", "itertools",
            "json", "keyword", "linecache", "locale", "logging", "lzma",
            "math", "mimetypes", "multiprocessing", "numbers", "operator",
            "os", "pathlib", "pickle", "platform", "pprint", "profile",
            "queue", "random", "re", "readline", "secrets", "select",
            "shelve", "shlex", "shutil", "signal", "site", "smtplib",
            "socket", "sqlite3", "ssl", "stat", "statistics", "string",
            "struct", "subprocess", "sys", "syslog", "tempfile", "textwrap",
            "threading", "time", "timeit", "token", "tokenize", "tomllib",
            "trace", "traceback", "tracemalloc", "typing", "types",
            "unicodedata", "unittest", "urllib", "uuid", "venv", "warnings",
            "weakref", "webbrowser", "xml", "xmlrpc", "zipfile", "zipimport",
            "zlib", "_thread",
        }

    # -- JavaScript/TypeScript -----------------------------------------

    def _analyze_javascript(self, ctx: AnalysisContext) -> dict[str, Any] | None:
        """Analyze JavaScript/TypeScript dependencies."""
        # Check if project has JS/TS files
        js_files = [
            sf for sf in ctx.source_files()
            if sf.suffix in (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
        ]
        if not js_files:
            return None

        ctx.reporter.sub("analyzing JavaScript/TypeScript imports and manifests")

        # Parse package.json
        declared_deps: dict[str, str] = {}
        declared_dev_deps: dict[str, str] = {}

        for sf in ctx.walk.files:
            if sf.id != "package.json":
                continue

            try:
                import json

                src = ctx.source(sf.id)
                if not src:
                    continue

                data = json.loads(src)
                declared_deps = data.get("dependencies", {})
                declared_dev_deps = data.get("devDependencies", {})
            except Exception:
                pass

        # Analyze actual imports
        used_packages: set[str] = set()
        import_graph: dict[str, set[str]] = defaultdict(set)
        imported_by: dict[str, set[str]] = defaultdict(set)

        for sf in js_files:
            imports = ctx.imports(sf)

            for imp in imports:
                spec = imp.raw

                # Skip relative imports
                if spec.startswith(".") or spec.startswith("/"):
                    continue

                # Extract package name
                if spec.startswith("@"):
                    parts = spec.split("/")
                    pkg = "/".join(parts[:2]) if len(parts) >= 2 else spec
                else:
                    pkg = spec.split("/")[0]

                used_packages.add(pkg)

                # Update graph
                module_key = sf.id.replace("/", ".").replace(".js", "")
                import_graph[module_key].add(pkg)
                imported_by[pkg].add(module_key)

        # Declared vs. used
        all_declared = set(declared_deps.keys()) | set(declared_dev_deps.keys())
        unused = sorted(all_declared - used_packages)
        undeclared = sorted(used_packages - all_declared)

        # Most imported/importing
        most_imported = sorted(
            [(mod, len(deps)) for mod, deps in imported_by.items()],
            key=lambda x: (-x[1], x[0]),
        )[:20]
        most_importing = sorted(
            [(mod, len(deps)) for mod, deps in import_graph.items()],
            key=lambda x: (-x[1], x[0]),
        )[:20]

        return {
            "language": "javascript/typescript",
            "files_analyzed": len(js_files),
            "declared_deps": declared_deps,
            "declared_dev_deps": declared_dev_deps,
            "used_packages": sorted(used_packages),
            "unused_declared": unused,
            "undeclared_used": undeclared,
            "most_imported": most_imported,
            "most_importing": most_importing,
        }

    # -- Rust ----------------------------------------------------------

    def _analyze_rust(self, ctx: AnalysisContext) -> dict[str, Any] | None:
        """Analyze Rust dependencies from Cargo.toml."""
        # Check if project has Rust files
        rust_files = [sf for sf in ctx.source_files() if sf.suffix == ".rs"]
        if not rust_files:
            return None

        ctx.reporter.sub("analyzing Rust dependencies from Cargo.toml")

        deps: dict[str, str] = {}
        dev_deps: dict[str, str] = {}
        build_deps: dict[str, str] = {}

        # Parse Cargo.toml
        for sf in ctx.walk.files:
            if sf.id != "Cargo.toml":
                continue

            try:
                src = ctx.source(sf.id)
                if not src:
                    continue

                current_section = ""
                for line in src.split("\n"):
                    line = line.strip()
                    m = re.match(r"^\[([^\]]+)\]", line)
                    if m:
                        current_section = m.group(1)
                        continue

                    if "=" not in line or not current_section:
                        continue

                    parts = line.split("=", 1)
                    name = parts[0].strip()
                    val = parts[1].strip().strip("\"'")

                    if current_section == "dependencies":
                        deps[name] = val
                    elif current_section == "dev-dependencies":
                        dev_deps[name] = val
                    elif current_section == "build-dependencies":
                        build_deps[name] = val

            except Exception:
                pass

        # Scan for actual crate usage
        used_crates: set[str] = set()
        for sf in rust_files:
            src = ctx.source(sf.id)
            if not src:
                continue

            for m in re.finditer(r"(?:use|extern crate)\s+(\w+)", src):
                crate = m.group(1)
                if crate not in ("crate", "self", "super", "std", "core", "alloc"):
                    used_crates.add(crate)

        return {
            "language": "rust",
            "files_analyzed": len(rust_files),
            "dependencies": deps,
            "dev_dependencies": dev_deps,
            "build_dependencies": build_deps,
            "used_crates": sorted(used_crates),
        }

    # -- Go ----------------------------------------------------------

    def _analyze_go(self, ctx: AnalysisContext) -> dict[str, Any] | None:
        """Analyze Go dependencies from go.mod."""
        # Check if project has Go files
        go_files = [sf for sf in ctx.source_files() if sf.suffix == ".go"]
        if not go_files:
            return None

        ctx.reporter.sub("analyzing Go module requirements")

        module_name = ""
        go_version = ""
        requires: dict[str, str] = {}

        # Parse go.mod
        for sf in ctx.walk.files:
            if sf.id != "go.mod":
                continue

            try:
                src = ctx.source(sf.id)
                if not src:
                    continue

                m = re.search(r"^module\s+(\S+)", src, re.MULTILINE)
                if m:
                    module_name = m.group(1)

                m = re.search(r"^go\s+(\S+)", src, re.MULTILINE)
                if m:
                    go_version = m.group(1)

                in_require = False
                for line in src.split("\n"):
                    line = line.strip()
                    if line.startswith("require ("):
                        in_require = True
                        continue
                    if in_require and line == ")":
                        in_require = False
                        continue

                    if in_require:
                        parts = line.split()
                        if len(parts) >= 2:
                            requires[parts[0]] = parts[1]
                    elif line.startswith("require "):
                        parts = line.split()
                        if len(parts) >= 3:
                            requires[parts[1]] = parts[2]

            except Exception:
                pass

        return {
            "language": "go",
            "files_analyzed": len(go_files),
            "module": module_name,
            "go_version": go_version,
            "requires": requires,
        }
