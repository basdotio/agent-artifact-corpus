"""Go import rewriter for extraction.

Fidelity: Regex-based rewriting of import statements and package declarations.

Go imports are full module paths (e.g., github.com/org/repo/pkg). When a Go
package is extracted, its module path changes (e.g., github.com/org/repo/pkg
becomes extracted/repo/pkg). Imports must be repointed to the new path.

What this rewriter handles:
- Single imports: import "x/y"
- Grouped imports: import ( ... ) blocks
- Aliased imports: import alias "x/y"
- Blank imports: import _ "x/y"
- Dot imports: import . "x/y"
- Preserves formatting and gofmt-style alignment

What is deliberately NOT rewritten (and why):
- Standard library imports (fmt, net/http, io, etc.) - always third-party
- Third-party imports not matching old module path - different packages
- Package declarations - rarely need renaming, high risk of breakage

Correctness bar: grouped import blocks must remain syntactically valid with
balanced parentheses. Returning the input unchanged with count 0 is always legal
and safe; emitting invalid syntax is a data corruption error.
"""

from __future__ import annotations

import re
from typing import Mapping

from .base import BaseRewriter

__all__ = ["GoRewriter"]


class GoRewriter(BaseRewriter):
    """Rewrite Go imports when extracting packages.

    The extracted package gets a new module path. All internal imports
    (those matching the old module path) are rewritten to the new path.
    Third-party and stdlib imports are left alone.
    """

    language = "go"

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:
        """Return (rewritten_source, number_of_imports_changed).

        module_map: file path mappings (old -> new). Extract the old and new
        module paths from these file paths and rewrite internal imports.
        """
        if not module_map:
            return source, 0

        try:
            # Derive old and new module paths from file mappings.
            # File paths are like: old_module/pkg/file.go -> new_module/pkg/file.go
            old_module, new_module = self._extract_module_paths(module_map)

            if not old_module or not new_module or old_module == new_module:
                # No rewrite needed if module path doesn't change.
                return source, 0

            # Rewrite grouped imports first (highest risk for corruption).
            result, count_grouped = self._rewrite_grouped_imports(source, old_module, new_module)
            # Then rewrite single imports.
            result, count_single = self._rewrite_single_imports(result, old_module, new_module)

            return result, count_grouped + count_single

        except Exception:
            # Catch everything: if anything goes wrong, return unchanged.
            return source, 0

    @staticmethod
    def _extract_module_paths(module_map: Mapping[str, str]) -> tuple[str | None, str | None]:
        """Extract old and new module paths from file path mappings.

        Assumes file paths follow pattern: module_path/subpath/file.go
        Returns (old_module, new_module) by finding the common prefix change.

        Strategy: Find the longest common prefix across all OLD paths that is
        NOT present in the new paths. This gives us the module root that changed.
        """
        if not module_map:
            return None, None

        old_paths = list(module_map.keys())
        new_paths = list(module_map.values())

        # Find longest common prefix across all old paths (the module root).
        old_module = GoRewriter._longest_common_directory(old_paths)
        new_module = GoRewriter._longest_common_directory(new_paths)

        return old_module, new_module

    @staticmethod
    def _longest_common_directory(paths: list[str]) -> str | None:
        """Find the longest common directory prefix across file paths.

        Examples:
        - ["github.com/org/repo/pkg/a.go", "github.com/org/repo/pkg/b.go"]
          -> "github.com/org/repo/pkg"
        - ["src/main.rs", "src/lib.rs"] -> "src"
        """
        if not paths:
            return None

        # Remove filenames and get directory paths.
        dirs = ["/".join(p.split("/")[:-1]) for p in paths]
        dirs = [d for d in dirs if d]  # Filter empty
        if not dirs:
            return None

        # Find common prefix across all directories.
        parts_list = [d.split("/") for d in dirs]
        common = []
        for i in range(min(len(parts) for parts in parts_list)):
            if len(set(parts[i] for parts in parts_list)) == 1:
                common.append(parts_list[0][i])
            else:
                break

        return "/".join(common) if common else None


    @staticmethod
    def _rewrite_grouped_imports(
        source: str, old_module: str, new_module: str
    ) -> tuple[str, int]:
        """Rewrite imports inside import ( ... ) blocks.

        Preserves formatting and handles aliases, blank, and dot imports.
        Returns (rewritten_source, count_of_imports_changed).
        """
        count = 0

        def replace_group(match: re.Match[str]) -> str:
            nonlocal count
            import_block = match.group(1)
            lines = import_block.split("\n")
            rewritten_lines = []

            for line in lines:
                # Skip comments and empty lines.
                stripped = line.strip()
                if not stripped or stripped.startswith("//"):
                    rewritten_lines.append(line)
                    continue

                # Match: [alias/blank/dot] "path"
                # Preserve leading whitespace for alignment.
                leading_ws = len(line) - len(line.lstrip())
                ws_str = line[:leading_ws]

                # Extract alias and path.
                m = re.match(
                    r'(import\s+)?(?:(\w+|_|\.)\s+)?["\']([^"\']+)["\']',
                    stripped,
                )

                if not m:
                    rewritten_lines.append(line)
                    continue

                alias_part = m.group(2)
                path = m.group(3)

                # Check if this is an internal import (starts with old module).
                if not (path == old_module or path.startswith(old_module + "/")):
                    rewritten_lines.append(line)
                    continue

                # Rewrite: replace old module with new module.
                if path == old_module:
                    new_path = new_module
                else:
                    suffix = path[len(old_module) :]
                    new_path = new_module + suffix

                # Reconstruct the line, preserving format.
                if alias_part:
                    new_line = f'{ws_str}{alias_part} "{new_path}"'
                else:
                    new_line = f'{ws_str}"{new_path}"'

                rewritten_lines.append(new_line)
                count += 1

            return "import (\n" + "\n".join(rewritten_lines) + "\n)"

        # Match: import ( ... ) with any content inside.
        result = re.sub(
            r"import\s*\(\s*(.*?)\s*\)",
            replace_group,
            source,
            flags=re.DOTALL,
        )
        return result, count

    @staticmethod
    def _rewrite_single_imports(
        source: str, old_module: str, new_module: str
    ) -> tuple[str, int]:
        """Rewrite single import statements outside grouped blocks.

        Returns (rewritten_source, count_of_imports_changed).
        """
        count = 0

        def replace_single(match: re.Match[str]) -> str:
            nonlocal count
            # Match: import [alias] "path"
            alias_part = match.group(1)
            path = match.group(2)

            # Check if this is an internal import.
            if not (path == old_module or path.startswith(old_module + "/")):
                return match.group(0)

            # Rewrite.
            if path == old_module:
                new_path = new_module
            else:
                suffix = path[len(old_module) :]
                new_path = new_module + suffix

            count += 1

            if alias_part:
                return f'import {alias_part} "{new_path}"'
            else:
                return f'import "{new_path}"'

        # Match single imports: import [alias] "path" (NOT inside groups).
        # Use negative lookbehind/lookahead to avoid matching inside import (...).
        result = re.sub(
            r'import\s+(?:(\w+|_|\.)\s+)?["\']([^"\']+)["\']',
            replace_single,
            source,
        )

        return result, count
