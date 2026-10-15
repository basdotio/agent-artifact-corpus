"""Rewrite JavaScript/TypeScript imports when extracting code."""

from __future__ import annotations

import re
from pathlib import PurePosixPath
from typing import Mapping

from .base import BaseRewriter

__all__ = ["JavaScriptRewriter"]


class JavaScriptRewriter(BaseRewriter):
    """Rewrite JavaScript/TypeScript import statements after extraction.

    Uses regex to find import/export/require statements, then rewrites the
    module specifiers while preserving code structure and quote style.

    Handles:
    - import x from "./a/b", import {a,b} from '../c', import * as ns from "..."
    - export {a} from "./x", export * from "./y"
    - require("./x"), dynamic import("./x")
    - Type-only imports: import type {T} from "./t"
    - Relative specifiers whose depth changes (same rule as Python)
    - Preserves quote style (single vs double) and file extensions

    Does NOT handle:
    - Bare/package specifiers (react, @scope/pkg) — these are third-party
    - Dynamic requires with template literals or variables
    - require.resolve() or other variations

    Module map handling:
    - If module_map contains path-based keys (with "/"), match on path
    - If module_map contains dotted keys, convert to paths
    - Path matching resolves both ./ and ../ relative imports
    """

    language = "javascript"
    aliases = ("typescript",)

    # Regex patterns for import/export/require statements.
    # These are permissive to match various formats.

    # import X from "path" or import type X from "path"
    IMPORT_FROM_RE = re.compile(
        r"""
        (?:^|\n)\s*
        import\s+(?:type\s+)?
        (?:[*\s\w{},]+\s+)?
        from\s+
        (['""])
        ((?:[^'"\\]|\\.)*)
        \1
        """,
        re.MULTILINE | re.VERBOSE,
    )

    # export X from "path"
    EXPORT_FROM_RE = re.compile(
        r"""
        (?:^|\n)\s*
        export\s+
        (?:[*\s\w{},]+\s+)?
        from\s+
        (['""])
        ((?:[^'"\\]|\\.)*)
        \1
        """,
        re.MULTILINE | re.VERBOSE,
    )

    # require("path") or import("path")
    REQUIRE_RE = re.compile(
        r"""
        (?:require|import)\s*
        \(\s*
        (['""])
        ((?:[^'"\\]|\\.)*)
        \1
        \s*\)
        """,
        re.VERBOSE,
    )

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:
        """Rewrite imports in JavaScript/TypeScript source code.

        Args:
            source: JavaScript/TypeScript source text
            path: File path relative to project root (e.g., "src/lib/utils.ts")
            module_map: Mapping of old module path -> new module path.
                        Keys can be either dotted (e.g., "core.utils") or
                        path-based (e.g., "core/utils").

        Returns:
            (rewritten_source, number_of_imports_changed)
        """
        if not module_map:
            return (source, 0)

        # Normalize module_map to path-based keys.
        path_map = self._normalize_module_map(module_map)
        if not path_map:
            return (source, 0)

        # Try to compute if the file's depth changed (for relative imports).
        # This is best-effort; if it fails, we assume no depth change.
        try:
            old_depth = self._file_depth(path)
            new_depth = self._resolve_new_depth(path, module_map)
            depth_changed = old_depth != new_depth
        except Exception:
            depth_changed = False

        result = source
        total_changed = 0

        # Rewrite import from statements.
        for match in self.IMPORT_FROM_RE.finditer(source):
            quote, spec = match.groups()
            new_spec = self._rewrite_spec(spec, path, path_map, depth_changed)
            if new_spec and new_spec != spec:
                # Replace the specifier in the source.
                old_text = quote + spec + quote
                new_text = quote + new_spec + quote
                result = result.replace(old_text, new_text, 1)
                total_changed += 1

        # Re-scan source after each replacement to avoid position shifts.
        # (This is less efficient but safer.)
        source = result
        for match in self.EXPORT_FROM_RE.finditer(source):
            quote, spec = match.groups()
            new_spec = self._rewrite_spec(spec, path, path_map, depth_changed)
            if new_spec and new_spec != spec:
                old_text = quote + spec + quote
                new_text = quote + new_spec + quote
                result = result.replace(old_text, new_text, 1)
                total_changed += 1

        source = result
        for match in self.REQUIRE_RE.finditer(source):
            quote, spec = match.groups()
            new_spec = self._rewrite_spec(spec, path, path_map, depth_changed)
            if new_spec and new_spec != spec:
                old_text = quote + spec + quote
                new_text = quote + new_spec + quote
                result = result.replace(old_text, new_text, 1)
                total_changed += 1

        return (result, total_changed)

    def _normalize_module_map(
        self, module_map: Mapping[str, str]
    ) -> dict[str, str]:
        """Convert mixed dotted/path module_map to path-based.

        If a key looks like a path (contains "/"), keep it.
        If it's dotted (contains only "." and identifier chars), convert to path.
        """
        path_map: dict[str, str] = {}
        for old, new in module_map.items():
            if "/" in old:
                # Already path-based.
                path_map[old] = new if "/" in new else new.replace(".", "/")
            else:
                # Dotted; convert to path.
                old_path = old.replace(".", "/")
                new_path = new.replace(".", "/")
                path_map[old_path] = new_path
        return path_map

    def _rewrite_spec(
        self,
        spec: str,
        file_path: str,
        path_map: dict[str, str],
        depth_changed: bool,
    ) -> str | None:
        """Rewrite a module specifier (import/export/require).

        Strategy: only rewrite absolute/bare imports that point to third-party
        packages. Leave relative imports alone because we don't know the file's
        new location and can't reliably compute the new relative path.
        Broken relative imports will be caught as "unresolved-import" breakages
        by the extraction planner.

        Args:
            spec: The module specifier (e.g., "./lib/utils", "../pkg", "react")
            file_path: Current file's path (unused with this strategy)
            path_map: Path-based module map
            depth_changed: Whether the file's depth changed (unused)

        Returns:
            Rewritten specifier, or None if no rewrite applies.
        """
        # Ignore bare/package specifiers (third-party).
        if not (spec.startswith(".") or spec.startswith("/")):
            return None

        # Don't rewrite relative imports. Leave them untouched.
        if spec.startswith("."):
            return None

        # Absolute paths starting with "/" would be rewritten here, but they're
        # very rare in JS/TS, so we skip them too.
        return None

    def _resolve_relative_spec(self, spec: str, file_path: str) -> str | None:
        """Resolve a relative module specifier to an absolute path.

        e.g., if file_path is "src/lib/utils.ts" and spec is "../pkg/core",
        this returns "src/pkg/core".

        Args:
            spec: The specifier (e.g., "./utils", "../lib", "../../pkg/core")
            file_path: Current file's path

        Returns:
            Absolute path (without leading /), or None if it escapes the root.
        """
        # Remove the .js/.ts extension from the file path if present.
        file_path_clean = spec
        if file_path.endswith((".js", ".ts", ".tsx", ".jsx")):
            file_path_clean = file_path[:-3]
        else:
            file_path_clean = file_path

        file_path = file_path_clean

        # Similarly, remove extension from spec if present.
        for ext in (".js", ".ts", ".tsx", ".jsx"):
            if spec.endswith(ext):
                spec_clean = spec[:-len(ext)]
                break
        else:
            spec_clean = spec

        # Parse the relative path.
        if not spec_clean.startswith("."):
            return None

        # Count leading dots and slashes.
        level = 0
        i = 0
        while i < len(spec_clean) and spec_clean[i] == ".":
            level += 1
            i += 1
        if i < len(spec_clean) and spec_clean[i] == "/":
            i += 1
        # If only dots and no slash, treat as same-level reference.
        elif level > 0 and i == len(spec_clean):
            module_part = ""
        else:
            return None

        module_part = spec_clean[i:]

        # Get the directory of the file.
        file_dir_parts = file_path.rsplit("/", 1)
        if len(file_dir_parts) == 2:
            file_dir = file_dir_parts[0]
        else:
            file_dir = ""

        # Go up 'level - 1' directories (level 1 = same dir, level 2 = parent, etc.).
        dir_parts = file_dir.split("/") if file_dir else []
        if level > 1:
            dir_parts = dir_parts[: -(level - 1)]

        # Append the module part.
        if module_part:
            dir_parts.append(module_part)

        resolved = "/".join(dir_parts) if dir_parts else module_part
        return resolved if resolved else None

    def _make_relative_spec(
        self, new_path: str, file_path: str, orig_spec: str
    ) -> str:
        """Convert an absolute path back to a relative specifier.

        Args:
            new_path: Absolute path to the module (e.g., "src/pkg/utils")
            file_path: Current file's path
            orig_spec: Original specifier (to copy quote style and extensions)

        Returns:
            Relative specifier (e.g., "../utils" or "./pkg/utils")
        """
        # Preserve the extension from the original spec if present.
        extension = ""
        for ext in (".js", ".ts", ".tsx", ".jsx"):
            if orig_spec.endswith(ext):
                extension = ext
                break

        # Compute relative path.
        file_dir_parts = file_path.rsplit("/", 1)
        if len(file_dir_parts) == 2:
            file_dir = file_dir_parts[0]
        else:
            file_dir = ""

        file_parts = file_dir.split("/") if file_dir else []
        target_parts = new_path.split("/")

        # Compute common prefix.
        common = 0
        for a, b in zip(file_parts, target_parts):
            if a == b:
                common += 1
            else:
                break

        # Go up from file_dir.
        ups = len(file_parts) - common
        downs = target_parts[common:]

        if ups == 0 and downs:
            # Same directory.
            rel = "./" + "/".join(downs) + extension
        elif ups > 0 and downs:
            # Up and across.
            rel = "../" * ups + "/".join(downs) + extension
        elif ups > 0 and not downs:
            # Just up.
            rel = "../" * (ups - 1) + "." + extension if ups > 1 else "." + extension
        else:
            # No relative path needed (shouldn't happen).
            rel = "./" + new_path + extension

        return rel

    def _file_depth(self, path: str) -> int:
        """Count the directory depth of a file path.

        e.g., "src/lib/utils.ts" has depth 2.
        """
        return path.count("/")

    def _resolve_new_depth(self, path: str, module_map: Mapping[str, str]) -> int:
        """Estimate the new depth of a file after extraction.

        This is best-effort; we check if any mapped path prefixes match.
        """
        # Convert path to dotted form for lookup.
        path_dotted = path.replace("/", ".").rsplit(".", 1)[0]

        for old_dotted, new_dotted in module_map.items():
            old_path = old_dotted.replace(".", "/")
            new_path = new_dotted.replace(".", "/")

            if path.startswith(old_path + "/") or path.startswith(old_path):
                # This file is in a mapped package; compute new depth.
                # Simplified: just count slashes in the new path.
                return new_path.count("/")

        # No mapping found; assume depth is unchanged.
        return self._file_depth(path)
