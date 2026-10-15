"""C# backend using regex.

Fidelity: regex. Limitations:
- Nested/conditional declarations are best-effort.
- Type signatures are captured but complex generics may be truncated.
- Properties are tracked but field backing is not distinguished.
- Attributes are not extracted.

Export detection:
- Public or protected members (no private, no internal).
- Classes, structs, interfaces, enums, methods, properties, constants.
- Namespaces are captured but not used to filter visibility (C# treats public
  in a namespace as public to external consumers).

Import detection:
- `using Namespace;` → kind="external"
- `using Alias = Namespace;` → kind="external"
"""

from __future__ import annotations

import re

from ..core.models import (
    Class,
    Constant,
    Func,
    ImportRef,
    Interface,
    Symbols,
    TypeDef,
)
from .base import BaseParser

__all__ = ["CSharpParser"]


class CSharpParser(BaseParser):
    name = "csharp"
    extensions = (".cs",)
    fidelity = "regex"

    def symbols(self, source: str, path: str) -> Symbols:
        """Extract symbols from C# source."""
        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []

        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # Public/protected classes
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:static\s+)?(?:abstract\s+)?(?:partial\s+)?class\s+(\w+)(?:\s*[:{])?",
                line,
            )
            if match:
                class_name = match.group(1)
                classes.append(Class(name=class_name, line=i, kind="class"))
                continue

            # Public/protected structs
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:static\s+)?(?:partial\s+)?struct\s+(\w+)",
                line,
            )
            if match:
                struct_name = match.group(1)
                classes.append(Class(name=struct_name, line=i, kind="struct"))
                continue

            # Public/protected interfaces
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:partial\s+)?interface\s+(\w+)",
                line,
            )
            if match:
                iface_name = match.group(1)
                types.append(
                    TypeDef(name=iface_name, kind="interface", line=i)
                )
                continue

            # Public/protected enums
            match = re.match(
                r"^\s*(?:public|protected)\s+enum\s+(\w+)",
                line,
            )
            if match:
                enum_name = match.group(1)
                types.append(
                    TypeDef(name=enum_name, kind="enum", line=i)
                )
                continue

            # Public/protected methods
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:static\s+)?(?:async\s+)?(?:override\s+)?(?:virtual\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*\(([^)]*)\)",
                line,
            )
            if match:
                method_name, params_raw = match.groups()
                functions.append(
                    Func(
                        name=method_name,
                        params_raw=params_raw.strip() if params_raw else None,
                        line=i,
                    )
                )
                continue

            # Public/protected properties (get/set)
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:static\s+)?(?:virtual\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*\{",
                line,
            )
            if match:
                prop_name = match.group(1)
                functions.append(
                    Func(
                        name=prop_name,
                        line=i,
                    )
                )
                continue

            # Public/protected constants/fields
            match = re.match(
                r"^\s*(?:public|protected)\s+(?:static\s+)?(?:readonly\s+)?(?:const\s+)?(\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*(?:=\s*([^;]+))?;",
                line,
            )
            if match:
                type_hint, const_name, value = match.groups()
                constants.append(
                    Constant(
                        name=const_name,
                        type=_truncate(type_hint.strip()) if type_hint else None,
                        value=_truncate(value.strip()) if value else None,
                        line=i,
                    )
                )
                continue

        return Symbols(
            classes=tuple(classes),
            functions=tuple(functions),
            constants=tuple(constants),
            types=tuple(types),
            imports=self.imports(source, path),
        )

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        """Extract imports from C# source."""
        refs: list[ImportRef] = []

        for match in re.finditer(
            r"^\s*using\s+(?:(?:static|async)\s+)?(?:(\w+)\s*=\s*)?([^;]+);",
            source,
            re.MULTILINE,
        ):
            alias, namespace = match.groups()
            # Use the namespace, or the alias if aliased
            spec = namespace.strip() if not alias else alias.strip()
            refs.append(
                ImportRef(
                    raw=spec,
                    kind="external",
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Deduplicate
        seen = set()
        unique_refs = []
        for ref in refs:
            if ref.raw not in seen:
                seen.add(ref.raw)
                unique_refs.append(ref)

        return tuple(sorted(unique_refs, key=lambda r: r.line))

    def interface(self, source: str, path: str) -> Interface:
        """Public surface: public and protected members only."""
        sym = self.symbols(source, path)
        # Filter is already done in symbols(), so just project
        return Interface.from_symbols(sym)


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _truncate(text: str | None, limit: int = 120) -> str | None:
    """Truncate text to limit, adding ellipsis if needed."""
    if text is None:
        return None
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit] + "…"
    return text
