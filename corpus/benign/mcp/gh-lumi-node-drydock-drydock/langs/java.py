"""Java backend using regex.

Fidelity: regex. Limitations:
- Nested/conditional declarations are best-effort.
- Type signatures are captured but complex generics may be truncated.
- Inner classes and anonymous classes are not extracted separately.
- Annotations are not extracted.

Export detection:
- Public members only (no package-private, no protected, no private).
- Classes, interfaces, enums, methods, constants.
- Package name is captured in `Symbols.package`.

Import detection:
- `import package.Class;` → kind="external"
- `import package.*;` → kind="external"
- `import static package.Class.method;` → kind="external"
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

__all__ = ["JavaParser"]


class JavaParser(BaseParser):
    name = "java"
    extensions = (".java",)
    fidelity = "regex"

    def symbols(self, source: str, path: str) -> Symbols:
        """Extract symbols from Java source."""
        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []
        package = None

        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # Package declaration
            match = re.match(r"^\s*package\s+([a-z0-9_.]+);", line)
            if match and not package:
                package = match.group(1)
                continue

            # Public classes
            match = re.match(
                r"^\s*(?:@\w+\s+)*public\s+(?:static\s+)?(?:final\s+)?(?:abstract\s+)?class\s+(\w+)",
                line,
            )
            if match:
                class_name = match.group(1)
                classes.append(Class(name=class_name, line=i, kind="class"))
                continue

            # Public interfaces
            match = re.match(
                r"^\s*(?:@\w+\s+)*public\s+(?:static\s+)?interface\s+(\w+)",
                line,
            )
            if match:
                iface_name = match.group(1)
                types.append(
                    TypeDef(name=iface_name, kind="interface", line=i)
                )
                continue

            # Public enums
            match = re.match(
                r"^\s*(?:@\w+\s+)*public\s+(?:static\s+)?enum\s+(\w+)",
                line,
            )
            if match:
                enum_name = match.group(1)
                types.append(
                    TypeDef(name=enum_name, kind="enum", line=i)
                )
                continue

            # Public methods
            match = re.match(
                r"^\s*(?:@\w+\s+)*public\s+(?:static\s+)?(?:synchronized\s+)?(?:final\s+)?(?:\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*\(([^)]*)\)",
                line,
            )
            if match:
                method_name, params_raw = match.groups()
                # Skip constructors that look like class names
                if method_name[0].isupper() and not any(c.name == method_name for c in classes):
                    # This is a constructor
                    pass
                functions.append(
                    Func(
                        name=method_name,
                        params_raw=params_raw.strip() if params_raw else None,
                        line=i,
                    )
                )
                continue

            # Public constants/fields (usually public static final)
            match = re.match(
                r"^\s*(?:@\w+\s+)*public\s+(?:static\s+)?(?:final\s+)?(\w+(?:<[^>]*>)?(?:\[\])?)\s+(\w+)\s*(?:=\s*([^;]+))?;",
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
            package=package,
        )

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        """Extract imports from Java source."""
        refs: list[ImportRef] = []

        for match in re.finditer(
            r"^\s*import\s+(?:static\s+)?([^;]+);",
            source,
            re.MULTILINE,
        ):
            import_spec = match.group(1).strip()
            refs.append(
                ImportRef(
                    raw=import_spec,
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
        """Public surface: public members only."""
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
