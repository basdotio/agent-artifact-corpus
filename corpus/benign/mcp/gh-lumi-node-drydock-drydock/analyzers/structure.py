"""Structure analyzer - directory layout, file type inventory, and depth metrics.

Produces comprehensive statistics on:
- Total files, directories, and bytes
- Per-file-type counts and sizes
- Largest files in the codebase
- Directory depth and deepest paths
- Hierarchical tree of top-level structure
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping

from ..core.registry import AnalysisContext, Option

__all__ = ["StructureAnalyzer"]


class StructureAnalyzer:
    """Analyze directory structure and file inventory."""

    name = "structure"
    summary = "Directory layout, file type counts, sizes, and depth metrics."
    description = (
        "Analyzes the directory structure to provide statistics on files, directories, "
        "and sizes. Reports per-extension counts and sizes, identifies largest files, "
        "measures directory depth, and generates a hierarchical tree summary of the "
        "top-level layout. Useful for understanding codebase organization and identifying "
        "large or potentially auto-generated components."
    )

    options = (
        Option(
            name="top_n",
            type=int,
            default=20,
            help="Number of largest files and extensions to list",
        ),
        Option(
            name="depth",
            type=int,
            default=3,
            help="Tree render depth for directory hierarchy",
        ),
    )

    def run(self, ctx: AnalysisContext, **opts: Any) -> dict[str, Any]:
        """Run the analyzer."""
        top_n: int = opts.get("top_n", 20)
        tree_depth: int = opts.get("depth", 3)

        ctx.reporter.step("analyzing structure")

        # Collect statistics from walk results
        files = ctx.walk.files
        ctx.reporter.sub(f"scanning {len(files)} files")

        total_files = 0
        total_dirs = set()
        total_bytes = 0
        file_types: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "size": 0})
        largest_files: list[dict[str, Any]] = []
        deepest_path = ""
        deepest_depth = 0
        top_level_dirs: set[str] = set()

        for sf in files:
            total_files += 1
            total_bytes += sf.size

            # Parse path components
            parts = sf.id.split("/")

            # Track top-level directories
            if len(parts) > 1:
                top_level_dirs.add(parts[0])
                # Track directory count and depth
                for i in range(len(parts) - 1):
                    total_dirs.add("/".join(parts[: i + 1]))

                # Track deepest path
                depth = len(parts) - 1
                if depth > deepest_depth:
                    deepest_depth = depth
                    deepest_path = sf.id
            else:
                # Root-level file
                top_level_dirs.add("(root)")

            # Track file types
            suffix = sf.suffix or "(no extension)"
            file_types[suffix]["count"] += 1
            file_types[suffix]["size"] += sf.size

            # Track for largest files
            largest_files.append({"id": sf.id, "size": sf.size})

        # Sort and trim largest files
        largest_files.sort(key=lambda x: x["size"], reverse=True)
        largest_files = largest_files[:top_n]

        # Sort file types by count
        sorted_types = sorted(
            file_types.items(),
            key=lambda x: x[1]["count"],
            reverse=True,
        )
        sorted_types = sorted_types[:top_n]

        # Build result
        result = {
            "meta": ctx.meta(),
            "summary": {
                "files": total_files,
                "directories": len(total_dirs),
                "total_bytes": total_bytes,
                "truncated": ctx.walk.truncated,
            },
            "file_types": [
                {
                    "extension": ext,
                    "count": data["count"],
                    "size": data["size"],
                }
                for ext, data in sorted_types
            ],
            "largest_files": largest_files,
            "deepest_path": {"path": deepest_path, "depth": deepest_depth},
            "top_level": sorted(top_level_dirs),
        }

        return result

    def to_markdown(self, result: Mapping[str, Any]) -> str:
        """Render result as markdown."""
        lines: list[str] = []

        # Header
        meta = result.get("meta", {})
        project = meta.get("project", "project")
        lines.append(f"# Structure Analysis: {project}")
        lines.append("")

        # Summary
        summary = result.get("summary", {})
        files = summary.get("files", 0)
        dirs = summary.get("directories", 0)
        total_bytes = summary.get("total_bytes", 0)
        truncated = summary.get("truncated", False)

        lines.append("## Summary")
        lines.append("")
        lines.append("| Metric | Value |")
        lines.append("|--------|-------|")
        lines.append(f"| Total Files | {files:,} |")
        lines.append(f"| Total Directories | {dirs:,} |")
        lines.append(f"| Total Size | {self._format_size(total_bytes)} |")

        deepest = result.get("deepest_path", {})
        deepest_depth = deepest.get("depth", 0)
        lines.append(f"| Max Depth | {deepest_depth} levels |")

        if truncated:
            lines.append("| Status | Truncated (raise --max-files) |")

        lines.append("")

        # Top-level directories
        top_level = result.get("top_level", [])
        if top_level:
            lines.append("## Top-Level Layout")
            lines.append("")

            for item in sorted(top_level):
                if item == "(root)":
                    continue
                lines.append(f"- `{item}/`")

            lines.append("")

        # File types
        file_types = result.get("file_types", [])
        if file_types:
            lines.append("## File Types")
            lines.append("")
            lines.append("| Extension | Count | Size |")
            lines.append("|-----------|-------|------|")

            for ft in file_types:
                ext = ft.get("extension", "?")
                count = ft.get("count", 0)
                size = ft.get("size", 0)
                lines.append(f"| `{ext}` | {count:,} | {self._format_size(size)} |")

            lines.append("")

        # Largest files
        largest = result.get("largest_files", [])
        if largest:
            lines.append("## Largest Files")
            lines.append("")
            lines.append("| File | Size |")
            lines.append("|------|------|")

            for f in largest:
                fid = f.get("id", "?")
                size = f.get("size", 0)
                lines.append(f"| `{fid}` | {self._format_size(size)} |")

            lines.append("")

        # Deepest path
        deepest = result.get("deepest_path", {})
        deepest_path = deepest.get("path", "")
        if deepest_path:
            lines.append("## Deepest Path")
            lines.append("")
            lines.append(f"`{deepest_path}`")
            lines.append("")
            lines.append(f"({deepest_depth} levels deep)")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _format_size(size_bytes: int) -> str:
        """Format bytes as human-readable size."""
        for unit in ("B", "KB", "MB", "GB"):
            if size_bytes < 1024:
                if unit == "B":
                    return f"{size_bytes:,} {unit}"
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"
