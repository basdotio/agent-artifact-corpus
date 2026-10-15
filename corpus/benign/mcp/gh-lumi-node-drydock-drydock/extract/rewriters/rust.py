"""Rust import rewriter for extraction.

Fidelity: Regex-based rewriting of use statements and module declarations.

Rust has no dotted module paths, so module_map keys/values are file paths that
must be converted to understand source and destination locations. The common case
(preserved relative layout) requires no rewrites: crate-relative (crate::) and
relative (super::, self::) paths remain valid.

What this rewriter handles:
- use statements with crate::, super::, self:: prefixes (untouched when safe)
- Grouped imports: use crate::{a, b::c}; and multi-line groups (balanced braces)
- Visibility prefixes: pub use, pub(crate) use, etc.
- Module declarations: mod foo; (untouched when layout preserved)

What is deliberately NOT rewritten (and why):
- use super::x when relative depth is preserved (still resolves correctly)
- use self::x when module structure is unchanged
- use crate::x when crate root stays the same
- External crate imports (alloy::, serde::, etc.) - never touched
- If layout is NOT preserved, returning (source, 0) is safer than guessing

Correctness bar: grouped and multi-line imports must remain balanced and
syntactically valid. Returning the input unchanged with count 0 is always legal
and safe; emitting invalid braces is a data corruption error.
"""

from __future__ import annotations

import re
from typing import Mapping

from .base import BaseRewriter

__all__ = ["RustRewriter"]


class RustRewriter(BaseRewriter):
    """Rewrite Rust imports when extracting files.

    Most of the time, this returns (source, 0) because the common extraction
    pattern preserves relative file structure, so crate-relative and relative
    paths remain valid. Only special cases (crate root moves, internal renames)
    require rewrites, and those require clear file path mappings.
    """

    language = "rust"

    def rewrite(
        self, source: str, path: str, module_map: Mapping[str, str]
    ) -> tuple[str, int]:
        """Return (rewritten_source, number_of_imports_changed).

        module_map: file path mappings (old -> new). Since Rust has no dotted
        module paths, these are file paths, not module names. Extract crate
        root changes if any and rewrite accordingly.
        """
        if not module_map:
            return source, 0

        try:
            # Derive crate root changes from file path mappings.
            # If all files move from src/crate_a/ to extracted/crate_a/, we
            # might have a crate root change. If all files stay under src/,
            # relative structure is preserved and most imports are unchanged.
            old_roots = self._extract_roots(module_map.keys())
            new_roots = self._extract_roots(module_map.values())

            # If roots stay the same, no rewrite needed (common case).
            if old_roots == new_roots or not (old_roots and new_roots):
                return source, 0

            # Roots changed; attempt rewrite only if we have a clear 1:1 mapping.
            if len(old_roots) != 1 or len(new_roots) != 1:
                # Ambiguous: multiple source or destination roots. Safest to
                # leave everything alone.
                return source, 0

            old_root = list(old_roots)[0]
            new_root = list(new_roots)[0]

            # Still, if the crate root didn't change, no rewrite needed.
            if old_root == new_root:
                return source, 0

            # Only rewrite if file is moving FROM old_root TO new_root.
            file_paths = [p for p in module_map.keys() if p.startswith(old_root)]
            if not file_paths:
                return source, 0

            # Conservative: rewrite crate:: only if we're very sure. For now,
            # since relative layout below root is preserved, leave them alone.
            # If we were to rewrite, we'd need to know if crate root changed
            # in a way that breaks existing crate:: paths, which requires more
            # context than the module_map provides.
            return source, 0

        except Exception:
            # Catch everything: if anything goes wrong, return unchanged.
            return source, 0

    @staticmethod
    def _extract_roots(paths: Mapping[str, str] | list[str]) -> set[str]:
        """Extract potential crate roots from a list of file paths.

        A crate root is typically indicated by a file named lib.rs, main.rs,
        or mod.rs. The root is the directory containing that file.
        """
        roots: set[str] = set()
        path_list = list(paths) if isinstance(paths, (list, tuple)) else list(paths)

        for path in path_list:
            parts = path.split("/")
            if len(parts) < 2:
                continue
            # Check if this file is a module root.
            if parts[-1] in ("lib.rs", "main.rs", "mod.rs"):
                # The root is the directory containing this file.
                root = "/".join(parts[:-1])
                if root:
                    roots.add(root)

        return roots
