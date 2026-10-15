"""Rust backend using regex.

Fidelity: regex. Limitations:
- Nested/conditional declarations are best-effort (allowed leading whitespace
  fixes the pre-0.2 anchor-to-start bug).
- Type signatures are captured but complex generics may be truncated.
- Attributes/macros are not extracted.

Export detection:
- Visible if marked with `pub`, `pub(crate)`, `pub(super)`, or `pub(in path)`.
- Functions, structs, traits, enums, type aliases, impl blocks.

Import detection:
- `use x::y` → kind="absolute" with `crate::` prefix kept in `raw`
- `use crate::x` → kind="absolute"
- `use super::x` or `use self::x` → kind="relative"
- `use std::*` or `use crate::{a, b}` → each name yields an `ImportRef`
- Bare module declarations `mod foo;` → kind="relative"
"""

from __future__ import annotations

import re
from dataclasses import replace

from ..core.models import (
    Class,
    Constant,
    Export,
    Func,
    ImportRef,
    Interface,
    Symbols,
    TypeDef,
)
from .base import BaseParser

__all__ = ["RustParser"]


class RustParser(BaseParser):
    name = "rust"
    extensions = (".rs",)
    fidelity = "regex"

    def symbols(self, source: str, path: str) -> Symbols:
        """Extract symbols from Rust source."""
        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []

        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # Public functions
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+(?:async\s+)?(?:unsafe\s+)?(?:extern\s+)?fn\s+(\w+)",
                line,
            )
            if match:
                func_name = match.group(1)
                functions.append(Func(name=func_name, line=i))
                continue

            # Public structs
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+struct\s+(\w+)",
                line,
            )
            if match:
                struct_name = match.group(1)
                classes.append(
                    Class(name=struct_name, line=i, kind="struct")
                )
                continue

            # Public traits
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+trait\s+(\w+)",
                line,
            )
            if match:
                trait_name = match.group(1)
                types.append(
                    TypeDef(name=trait_name, kind="trait", line=i)
                )
                continue

            # Public enums
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+enum\s+(\w+)",
                line,
            )
            if match:
                enum_name = match.group(1)
                types.append(
                    TypeDef(name=enum_name, kind="enum", line=i)
                )
                continue

            # Public type aliases
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+type\s+(\w+)(?:<[^>]*>)?\s*=\s*(.+);",
                line,
            )
            if match:
                type_name, definition = match.groups()
                types.append(
                    TypeDef(
                        name=type_name,
                        kind="alias",
                        definition=_truncate(definition.strip()),
                        line=i,
                    )
                )
                continue

            # Public constants
            match = re.match(
                r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+const\s+(\w+)(?:\s*:\s*([^=]+))?\s*=\s*([^;]+);",
                line,
            )
            if match:
                const_name, type_hint, value = match.groups()
                constants.append(
                    Constant(
                        name=const_name,
                        type=_truncate(type_hint.strip()) if type_hint else None,
                        value=_truncate(value.strip()),
                        line=i,
                    )
                )
                continue

            # impl blocks (for methods)
            match = re.match(r"^\s*impl(?:<[^>]*>)?\s+(\w+)", line)
            if match:
                impl_name = match.group(1)
                # This is tracked as a Class for code mapping purposes
                # (actual Rust impl blocks are not traditional classes, but
                # for the purposes of code analysis we group methods with
                # their receiver type)
                # We'll extract methods below in a separate pass

        # Extract methods from impl blocks
        impl_pattern = r"^\s*impl(?:<[^>]*>)?\s+(\w+)\s*(?:\{|where)"
        for match in re.finditer(impl_pattern, source, re.MULTILINE):
            impl_name = match.group(1)
            # Find the impl block bounds
            impl_start = match.end()
            brace_count = 0
            block_start = -1
            block_end = -1

            for idx, char in enumerate(source[impl_start:], impl_start):
                if char == "{":
                    if block_start == -1:
                        block_start = idx + 1
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        block_end = idx
                        break

            if block_start > 0 and block_end > 0:
                impl_body = source[block_start:block_end]
                methods = []
                for method_match in re.finditer(
                    r"^\s*pub(?:\s*\(\s*(?:crate|super|in\s+[^)]+)\s*\))?\s+(?:unsafe\s+)?(?:async\s+)?fn\s+(\w+)",
                    impl_body,
                    re.MULTILINE,
                ):
                    method_name = method_match.group(1)
                    methods.append(
                        Func(name=method_name, line=source[: block_start + method_match.start()].count("\n") + 1)
                    )

                if methods:
                    # Find or create the struct/class entry
                    existing = next((c for c in classes if c.name == impl_name), None)
                    if existing:
                        idx = classes.index(existing)
                        classes[idx] = replace(existing, methods=tuple(methods))
                    else:
                        classes.append(
                            Class(name=impl_name, methods=tuple(methods), kind="struct")
                        )

        return Symbols(
            classes=tuple(classes),
            functions=tuple(functions),
            constants=tuple(constants),
            types=tuple(types),
            imports=self.imports(source, path),
        )

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        """Extract imports from Rust source.

        Handles both single-line and multi-line use statements, and mod declarations.
        """
        refs: list[ImportRef] = []

        # Extract all use statements (including multi-line)
        # Match: use ...  ;
        for match in re.finditer(r"^\s*use\s+(.+?);\s*$", source, re.MULTILINE | re.DOTALL):
            use_path = match.group(1).strip()
            line_num = source[: match.start()].count("\n") + 1

            # Normalize whitespace in use path
            use_path = " ".join(use_path.split())

            # Handle `use {a, b, c}` style imports
            if "{" in use_path:
                # Multi-import: use crate::{a, b}
                prefix_match = re.match(r"^([^{]+)\{([^}]+)\}", use_path)
                if prefix_match:
                    prefix, items = prefix_match.groups()
                    prefix = prefix.rstrip(":")
                    for item in items.split(","):
                        item = item.strip().split(" as ")[0].strip()
                        if item and item != "*":
                            full_path = f"{prefix}::{item}"
                            kind = _use_kind(full_path)
                            refs.append(
                                ImportRef(
                                    raw=full_path,
                                    kind=kind,
                                    line=line_num,
                                )
                            )
            else:
                # Single import
                kind = _use_kind(use_path)
                refs.append(
                    ImportRef(
                        raw=use_path,
                        kind=kind,
                        line=line_num,
                    )
                )

        # Module declarations: `mod foo;`, `pub mod foo;`, `pub(crate) mod foo;`
        #
        # `raw` carries the module NAME only. Including the `mod ` keyword made
        # the index look for a file literally named `mod foo.rs`, so every
        # module declaration in a crate root went unresolved -- which is most
        # of the internal structure of a typical Rust project.
        for match in re.finditer(
            r"^\s*(?:pub(?:\([^)]*\))?\s+)?mod\s+(\w+)\s*;", source, re.MULTILINE
        ):
            refs.append(
                ImportRef(
                    raw=match.group(1),
                    kind="relative",
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        return tuple(sorted(refs, key=lambda r: r.line))

    def interface(self, source: str, path: str) -> Interface:
        """Public surface: `pub`, `pub(crate)`, `pub(super)`, `pub(in path)` items."""
        sym = self.symbols(source, path)
        # Filter: only items that are pub are in the interface
        # This is handled by symbols() already (only extracting pub items)
        return Interface.from_symbols(sym)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _use_kind(use_path: str) -> str:
    """Determine import kind from Rust use path."""
    if use_path.startswith("crate::"):
        return "absolute"
    if use_path.startswith("super::"):
        return "relative"
    if use_path.startswith("self::"):
        return "relative"
    # External crate (e.g., std::, serde::)
    return "external"


def _truncate(text: str | None, limit: int = 120) -> str | None:
    """Truncate text to limit, adding ellipsis if needed."""
    if text is None:
        return None
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit] + "…"
    return text
