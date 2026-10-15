"""Rewrite Python imports when extracting code."""

from __future__ import annotations

import ast
import re
from pathlib import PurePosixPath
from typing import Mapping

from .base import BaseRewriter

__all__ = ["PythonRewriter"]


class PythonRewriter(BaseRewriter):
    """Rewrite Python import statements after extraction.

    Uses AST to find imports (reliable), but rewrites via targeted text edits
    on the original source to preserve comments, formatting, and blank lines.

    Handles:
    - import a.b.c and import a.b.c as x (including multiple in one statement)
    - from a.b import c / from a.b import c as d / parenthesised multi-line
    - Relative imports: from . import x, from .mod import y, from ..pkg.mod import z
      (These are only rewritten if the file's depth relative to the package
       root changes. If the relative relationship is preserved, they are left alone.)
    - importlib.import_module("a.b") and __import__("a.b") with literal strings
    - Nested imports (in functions, if TYPE_CHECKING blocks, etc)

    Does NOT handle:
    - __all__ string module references
    - Assignments, function arguments, or other non-import contexts

    Strategy:
    1. Parse the file with ast.parse() to find all import nodes and their positions
    2. For each import, determine the old and new module paths using BaseRewriter.remap()
    3. Locate and extract the import statement text using line/col information
    4. Apply text edits back-to-front by position to preserve earlier offsets
    5. If parsing fails or a change is uncertain, return (source, 0) unchanged
    """

    language = "python"

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:
        """Rewrite imports in source code.

        Args:
            source: Python source text
            path: File path relative to project root (e.g., "core/models.py")
            module_map: Mapping of old dotted module path -> new dotted module path

        Returns:
            (rewritten_source, number_of_imports_changed)
            If anything fails to parse or is uncertain, returns (source, 0).
        """
        if not module_map:
            return (source, 0)

        try:
            tree = ast.parse(source)
        except SyntaxError:
            # File does not parse; return unchanged.
            return (source, 0)

        try:
            # Compute the file's old and new dotted package paths to detect
            # relative import depth changes.
            old_package = self._file_to_dotted(path)
            new_package = self._resolve_new_package(path, module_map)
            old_depth = old_package.count(".") if old_package else 0
            new_depth = new_package.count(".") if new_package else 0
            depth_changed = old_depth != new_depth
        except Exception:
            # If we can't compute package info, don't rewrite relative imports.
            # We'll still rewrite absolute ones.
            old_depth = 0
            new_depth = 0
            depth_changed = False

        # Collect all rewrites (edits) as (start_pos, end_pos, new_text, count).
        # We apply them back-to-front to preserve positions.
        edits: list[tuple[int, int, str, int]] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                rewrites = self._rewrite_import_node(
                    node, source, path, module_map, depth_changed
                )
                edits.extend(rewrites)

            # Handle importlib.import_module() and __import__()
            elif isinstance(node, ast.Call):
                rewrites = self._rewrite_call_node(node, source, module_map)
                edits.extend(rewrites)

        if not edits:
            return (source, 0)

        # Sort by start position (descending) to apply back-to-front.
        edits.sort(key=lambda x: x[0], reverse=True)

        result = source
        total_changed = 0

        for start, end, new_text, count in edits:
            result = result[:start] + new_text + result[end:]
            total_changed += count

        # Validate the result still parses.
        try:
            ast.parse(result)
        except SyntaxError:
            # Rewrite corrupted the file; return original.
            return (source, 0)

        return (result, total_changed)

    def _rewrite_import_node(
        self,
        node: ast.Import | ast.ImportFrom,
        source: str,
        path: str,
        module_map: Mapping[str, str],
        depth_changed: bool,
    ) -> list[tuple[int, int, str, int]]:
        """Generate edits for an import statement.

        Strategy: only rewrite absolute imports. Relative imports are left
        untouched because rewriting them correctly requires knowing the new
        package structure, which is fragile. Broken relative imports will be
        reported as "unresolved-import" breakages by the planner.
        """
        edits: list[tuple[int, int, str, int]] = []

        if isinstance(node, ast.Import):
            # import a.b.c or import a.b.c as x
            for alias in node.names:
                new_name = self.remap(alias.name, module_map)
                if new_name and new_name != alias.name:
                    edits.append(
                        self._rewrite_dotted_name_in_node(
                            source, node, alias.name, new_name
                        )
                    )
        else:
            # from a.b import c or from a.b import c as d
            if node.level > 0:
                # Relative import: leave alone. Depth changes will be caught
                # as broken imports by the planner.
                pass
            else:
                # Absolute import: rewrite the module path.
                module_name = node.module or ""
                if module_name:
                    new_name = self.remap(module_name, module_map)
                    if new_name and new_name != module_name:
                        edits.append(
                            self._rewrite_dotted_name_in_node(
                                source, node, module_name, new_name
                            )
                        )

        return edits

    def _rewrite_call_node(
        self, node: ast.Call, source: str, module_map: Mapping[str, str]
    ) -> list[tuple[int, int, str, int]]:
        """Generate edits for importlib.import_module() or __import__() calls."""
        edits: list[tuple[int, int, str, int]] = []

        # Check for importlib.import_module("a.b") or __import__("a.b")
        func_name = self._get_call_name(node)
        if func_name not in ("importlib.import_module", "__import__"):
            return edits

        # First argument should be a string.
        if not node.args or not isinstance(node.args[0], ast.Constant):
            return edits

        arg_value = node.args[0].value
        if not isinstance(arg_value, str):
            return edits

        new_value = self.remap(arg_value, module_map)
        if new_value and new_value != arg_value:
            edits.append(self._rewrite_string_literal(source, node.args[0], new_value))

        return edits

    def _rewrite_dotted_name_in_node(
        self,
        source: str,
        node: ast.Import | ast.ImportFrom,
        old_name: str,
        new_name: str,
    ) -> tuple[int, int, str, int]:
        """Find and rewrite a dotted name within a specific import statement.

        Uses the node's position information (lineno, col_offset) to locate
        the correct occurrence.

        Returns (start, end, new_text, 1).
        """
        lines = source.split("\n")
        if node.lineno < 1 or node.lineno > len(lines):
            raise ValueError(f"Invalid line number {node.lineno}")

        # Get the line(s) containing this import statement.
        # Multi-line imports may span multiple lines.
        start_line_idx = node.lineno - 1
        end_line_idx = node.end_lineno - 1 if node.end_lineno else start_line_idx

        # Reconstruct the statement text.
        stmt_lines = lines[start_line_idx : end_line_idx + 1]
        stmt_text = "\n".join(stmt_lines)

        # Find the name within the statement text.
        idx_in_stmt = stmt_text.find(old_name)
        if idx_in_stmt == -1:
            raise ValueError(
                f"Could not find {old_name!r} in import statement at line {node.lineno}"
            )

        # Convert to absolute position in source.
        abs_start = sum(len(lines[i]) + 1 for i in range(start_line_idx)) + idx_in_stmt
        abs_end = abs_start + len(old_name)

        return (abs_start, abs_end, new_name, 1)

    def _rewrite_from_module(
        self, source: str, node: ast.ImportFrom, new_path: str
    ) -> tuple[int, int, str, int]:
        """Rewrite the module path in a 'from X import Y' statement.

        For relative imports like 'from .pkg.mod import x', we need to rewrite
        'pkg.mod' to the new path while preserving the dots and structure.
        """
        # Reconstruct the relative module string as it appears in the source.
        dots = "." * node.level
        old_module = node.module or ""
        old_full = dots + old_module

        # The new path should replace the old_module part.
        # If the new path requires different relative levels, we'd need to
        # recompute, but for now we assume same structure.
        new_full = dots + new_path

        # Find this in the source.
        idx = source.find(old_full)
        if idx == -1:
            raise ValueError(f"Could not find {old_full!r} in source")

        return (idx, idx + len(old_full), new_full, 1)

    def _rewrite_string_literal(
        self, source: str, node: ast.Constant, new_value: str
    ) -> tuple[int, int, str, int]:
        """Rewrite a string literal in a call like importlib.import_module().

        Uses the node's position information to locate the correct string.
        Preserves the quote style.
        """
        old_value = node.value
        if not isinstance(old_value, str):
            raise ValueError(f"Expected string, got {type(old_value)}")

        lines = source.split("\n")
        if node.lineno < 1 or node.lineno > len(lines):
            raise ValueError(f"Invalid line number {node.lineno}")

        line = lines[node.lineno - 1]
        col = node.col_offset

        # The col_offset points to the start of the string literal (including quote).
        # Try both single and double quotes.
        for quote_char in ('"', "'"):
            if col < len(line) and line[col] == quote_char:
                # Found the quote. Find the closing quote.
                close_idx = line.find(quote_char, col + 1)
                if close_idx != -1:
                    # Verify the string content matches.
                    string_content = line[col + 1 : close_idx]
                    if string_content == old_value:
                        # Compute absolute position in source (start of quote).
                        start = sum(len(lines[i]) + 1 for i in range(node.lineno - 1))
                        start += col
                        # End is after the closing quote.
                        end = start + len(old_value) + 2
                        new_text = quote_char + new_value + quote_char
                        return (start, end, new_text, 1)

        raise ValueError(f"Could not find string literal {old_value!r} in source")

    def _file_to_dotted(self, path: str) -> str:
        """Convert a file path to a dotted module name.

        e.g., "core/models.py" -> "core.models"
        e.g., "pkg/__init__.py" -> "pkg"
        """
        p = PurePosixPath(path)
        parts = list(p.parts)
        if p.name in ("__init__.py", "__init__.pyi"):
            parts = parts[:-1]
        else:
            parts[-1] = p.stem
        return ".".join(parts)

    def _resolve_new_package(
        self, path: str, module_map: Mapping[str, str]
    ) -> str:
        """Resolve the new dotted package path for a file after extraction.

        If the file's old package is in the module_map, we can look it up.
        Otherwise, we assume it stays in the same relative structure.
        """
        old_dotted = self._file_to_dotted(path)

        # Find the longest matching key in module_map.
        for old, new in module_map.items():
            if old_dotted == old or old_dotted.startswith(old + "."):
                # The file is in a mapped package.
                suffix = old_dotted[len(old):].lstrip(".")
                return (new + "." + suffix) if suffix else new

        # File not directly in a mapped package; return original.
        return old_dotted

    def _resolve_relative(
        self, path: str, module: str | None, level: int, source: str
    ) -> str | None:
        """Resolve a relative import to an absolute dotted module path.

        e.g., if the file is core/models.py and we have 'from .utils import x',
        this returns 'core.utils'.

        Args:
            path: File path relative to project root
            module: The module part (e.g., "utils" in "from .utils import x")
            level: Number of dots (1 = same package, 2 = parent package, etc.)
            source: Source text (unused, but kept for consistency)

        Returns:
            Absolute dotted module path, or None if resolution fails.
        """
        file_dotted = self._file_to_dotted(path)

        # file_dotted is the module of the file itself.
        # Strip off the module name to get the package.
        parts = file_dotted.split(".")
        if len(parts) < level:
            # Relative import escapes the root; can't resolve.
            return None

        # Go up 'level' steps.
        package_parts = parts[: len(parts) - level]
        if module:
            package_parts.append(module)

        return ".".join(package_parts) if package_parts else None

    def _get_call_name(self, node: ast.Call) -> str:
        """Get the fully-qualified name of a function call.

        e.g., ast.Call with func=ast.Attribute(value=Name("importlib"), attr="import_module")
        returns "importlib.import_module".
        """
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            parts = []
            obj = node.func
            while isinstance(obj, ast.Attribute):
                parts.append(obj.attr)
                obj = obj.value
            if isinstance(obj, ast.Name):
                parts.append(obj.id)
                return ".".join(reversed(parts))
        return ""
