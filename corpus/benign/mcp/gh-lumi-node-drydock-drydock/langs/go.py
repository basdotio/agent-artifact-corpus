"""Go backend using regex.

Fidelity: regex. Limitations:
- Nested/conditional declarations are best-effort.
- Type signatures are captured but complex generics may be truncated.
- Interface methods and struct fields are not extracted separately.

Export detection:
- Exported if identifier starts with capital letter (Go convention).
- Functions, methods (with receiver), structs, interfaces, consts, type decls.
- Package name is captured in `Symbols.package`.

Import detection:
- `import "x/y"` → kind="absolute" (Go package path)
- Both grouped `import ( ... )` and single `import "x"` forms.
- Aliased imports `import alias "x"`.
- Blank imports `import _ "x"`.
- Dot imports `import . "x"`.
"""

from __future__ import annotations

import re
from dataclasses import replace

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

__all__ = ["GoParser"]


class GoParser(BaseParser):
    name = "go"
    extensions = (".go",)
    fidelity = "regex"

    def symbols(self, source: str, path: str) -> Symbols:
        """Extract symbols from Go source."""
        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []
        package = None

        lines = source.split("\n")

        for i, line in enumerate(lines, 1):
            # Package declaration
            match = re.match(r"^\s*package\s+(\w+)", line)
            if match and not package:
                package = match.group(1)
                continue

            # Exported functions (capitalized)
            match = re.match(
                r"^\s*func\s+([A-Z]\w*)\s*\(([^)]*)\)(?:\s*(?:\(([^)]*)\)|(\S+)))?",
                line,
            )
            if match:
                func_name, params_raw, returns_tuple, returns_single = match.groups()
                returns = (returns_tuple or returns_single or "").strip() or None
                functions.append(
                    Func(
                        name=func_name,
                        params_raw=params_raw.strip() if params_raw else None,
                        returns=_truncate(returns) if returns else None,
                        line=i,
                    )
                )
                continue

            # Exported methods on types (capitalized receiver type)
            match = re.match(
                r"^\s*func\s+\(\s*(\w+)\s+\*?(\w+)\s*\)\s+([A-Z]\w*)\s*\(([^)]*)\)(?:\s*(?:\(([^)]*)\)|(\S+)))?",
                line,
            )
            if match:
                receiver_name, receiver_type, method_name, params_raw, returns_tuple, returns_single = match.groups()
                returns = (returns_tuple or returns_single or "").strip() or None
                # Only track if receiver type is exported (capitalized)
                if receiver_type[0].isupper():
                    methods = [
                        Func(
                            name=method_name,
                            params_raw=params_raw.strip() if params_raw else None,
                            returns=_truncate(returns) if returns else None,
                            line=i,
                        )
                    ]
                    # Find or create struct entry
                    existing = next((c for c in classes if c.name == receiver_type), None)
                    if existing:
                        idx = classes.index(existing)
                        classes[idx] = replace(
                            existing,
                            methods=tuple(list(existing.methods) + methods)
                        )
                    else:
                        classes.append(
                            Class(name=receiver_type, methods=tuple(methods), kind="struct", line=i)
                        )
                continue

            # Exported structs (capitalized)
            match = re.match(r"^\s*type\s+([A-Z]\w*)\s+struct\s*(?:\{|$)", line)
            if match:
                struct_name = match.group(1)
                classes.append(Class(name=struct_name, line=i, kind="struct"))
                continue

            # Exported interfaces (capitalized)
            match = re.match(r"^\s*type\s+([A-Z]\w*)\s+interface\s*(?:\{|$)", line)
            if match:
                iface_name = match.group(1)
                types.append(
                    TypeDef(name=iface_name, kind="interface", line=i)
                )
                continue

            # Type aliases/definitions (capitalized)
            match = re.match(r"^\s*type\s+([A-Z]\w*)\s+([^{}\n;]+)(?:\s*[{};]|$)", line)
            if match:
                type_name, definition = match.groups()
                # Skip if already matched as struct/interface
                if not any(c.name == type_name for c in classes) and not any(t.name == type_name for t in types):
                    types.append(
                        TypeDef(
                            name=type_name,
                            kind="type",
                            definition=_truncate(definition.strip()),
                            line=i,
                        )
                    )
                continue

            # Exported constants (capitalized, usually UPPER_CASE but check first letter)
            match = re.match(
                r"^\s*const\s+([A-Z]\w*)\s*(?:(?:int|string|float64|bool|[A-Z]\w*)\s+)?=\s*(.+)",
                line,
            )
            if match:
                const_name, value = match.groups()
                constants.append(
                    Constant(
                        name=const_name,
                        value=_truncate(value.strip()),
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
        """Extract imports from Go source."""
        refs: list[ImportRef] = []

        # Handle grouped imports: import ( ... )
        grouped_match = re.search(r"import\s*\(([^)]+)\)", source)
        if grouped_match:
            import_block = grouped_match.group(1)
            for line in import_block.split("\n"):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue

                # Parse import line: [alias] "path"
                match = re.match(r'(?:(\w+|_|\.)\s+)?["\']([^"\']+)["\']', line)
                if match:
                    alias, pkg_path = match.groups()
                    refs.append(
                        ImportRef(
                            raw=pkg_path,
                            kind="absolute",
                            line=source[: source.find(line)].count("\n") + 1,
                        )
                    )

        # Handle single imports: import "x"
        for match in re.finditer(r'import\s+(?:(\w+|_|\.)\s+)?["\']([^"\']+)["\']', source):
            pkg_path = match.group(2)
            refs.append(
                ImportRef(
                    raw=pkg_path,
                    kind="absolute",
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
        """Public surface: capitalized identifiers only."""
        sym = self.symbols(source, path)
        # In Go, interface is determined by capitalization, which is already
        # handled in symbols(). So we just return the interface from symbols.
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
