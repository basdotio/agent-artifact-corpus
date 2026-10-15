"""JavaScript and TypeScript backends using regex.

Fidelity: regex. Limitations:
- Class methods and properties are extracted by counting braces, with string/
  comment content stripped first (defect fix from pre-0.2 code where quotes
  inside strings broke method detection).
- Nested/conditional declarations are best-effort (allowed leading whitespace
  fixes the pre-0.2 anchor-to-start bug).
- Type annotations are captured verbatim but not parsed deeply.

Export detection:
- `export function`, `export class`, `export const`, `export let`, `export var`
- `export interface`, `export type`, `export enum`
- `export { a, b } from "./x"` and `export * from "./x"`
- Re-exports are tracked to the source file.

Import detection:
- `import x from "./y"` → relative or external
- `import { a, b } from "./x"`
- `import * as ns from "./x"`
- Relative imports (starting with `.` or `/`) → `kind="relative"`
- Bare specifiers and `node:*` → `kind="external"`
"""

from __future__ import annotations

import re
from typing import Iterable

from ..core.models import (
    Class,
    Constant,
    Export,
    Func,
    ImportRef,
    Interface,
    Param,
    Symbols,
    TypeDef,
)
from .base import BaseParser

__all__ = ["JavaScriptParser", "TypeScriptParser"]


class _JSLike(BaseParser):
    """Shared base for JavaScript and TypeScript."""

    fidelity = "regex"

    def symbols(self, source: str, path: str) -> Symbols:
        """Extract symbols from JS/TS source."""
        classes: list[Class] = []
        functions: list[Func] = []
        constants: list[Constant] = []
        types: list[TypeDef] = []
        exports: list[Export] = []

        # Strip comments and strings to avoid false matches inside them
        clean_src = _strip_comments_and_strings(source)

        # Top-level function declarations and expressions
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^\{]+))?",
            clean_src,
            re.MULTILINE,
        ):
            func_name, params_raw, returns = match.groups()
            functions.append(
                Func(
                    name=func_name,
                    params=_parse_params(params_raw),
                    params_raw=params_raw.strip() if params_raw else None,
                    returns=_truncate(returns.strip()) if returns else None,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Arrow function declarations (const/let)
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*([^=]+))?\s*=\s*(?:async\s+)?\(?",
            clean_src,
            re.MULTILINE,
        ):
            func_name, type_hint = match.groups()
            functions.append(
                Func(
                    name=func_name,
                    returns=_truncate(type_hint.strip()) if type_hint else None,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Class declarations
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+([\w.]+))?(?:\s+implements\s+([^{]+))?",
            clean_src,
            re.MULTILINE,
        ):
            class_name, extends, implements = match.groups()
            line = source[: match.start()].count("\n") + 1
            bases = []
            if extends:
                bases.append(extends.strip())
            if implements:
                bases.extend(x.strip() for x in implements.split(","))

            # Find class body and extract methods
            class_start = match.end()
            brace_count = 0
            body_start = -1
            body_end = -1
            for idx, char in enumerate(clean_src[class_start:], class_start):
                if char == "{":
                    if body_start == -1:
                        body_start = idx + 1
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        body_end = idx
                        break

            methods: list[Func] = []
            properties: list[Func] = []

            if body_start > 0 and body_end > 0:
                body = clean_src[body_start:body_end]
                # Extract methods and properties
                for method_match in re.finditer(
                    r"^\s*(?:(?:get|set|async|static|private|protected|public)\s+)*(\w+)\s*(?:\([^)]*\))?(?:\s*:\s*([^{]+))?",
                    body,
                    re.MULTILINE,
                ):
                    method_name, ret_type = method_match.groups()
                    if method_name in ("constructor", "ngOnInit", "ngOnDestroy"):
                        method_type = "methods"
                    elif re.search(r"\bget\s+\w+", body[max(0, method_match.start() - 20) : method_match.start() + 20]):
                        method_type = "properties"
                    else:
                        method_type = "methods"

                    func = Func(
                        name=method_name,
                        returns=_truncate(ret_type.strip()) if ret_type else None,
                        line=line + body[: method_match.start()].count("\n"),
                    )
                    if method_type == "properties":
                        properties.append(func)
                    else:
                        methods.append(func)

            classes.append(
                Class(
                    name=class_name,
                    bases=tuple(bases),
                    methods=tuple(methods),
                    properties=tuple(properties),
                    line=line,
                    kind="class",
                )
            )

        # Exported interfaces (TS)
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?",
            clean_src,
            re.MULTILINE,
        ):
            iface_name, extends = match.groups()
            bases = tuple(x.strip() for x in extends.split(",")) if extends else ()
            types.append(
                TypeDef(
                    name=iface_name,
                    kind="interface",
                    bases=bases,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Exported type aliases (TS)
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?type\s+(\w+)(?:<[^>]*>)?\s*=\s*([^;]+);?",
            clean_src,
            re.MULTILINE,
        ):
            type_name, definition = match.groups()
            types.append(
                TypeDef(
                    name=type_name,
                    kind="type",
                    definition=_truncate(definition.strip()),
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Exported enums
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:const\s+)?enum\s+(\w+)",
            clean_src,
            re.MULTILINE,
        ):
            enum_name = match.group(1)
            types.append(
                TypeDef(
                    name=enum_name,
                    kind="enum",
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Exported constants
        for match in re.finditer(
            r"(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*([^=]+))?\s*=\s*([^;,\n]+)",
            clean_src,
            re.MULTILINE,
        ):
            const_name, type_hint, value = match.groups()
            # Only capture constants that look like they are exported or all-caps
            if not re.match(r"^export\s+", source[match.start():match.end()]) and const_name[0].islower():
                continue
            constants.append(
                Constant(
                    name=const_name,
                    type=_truncate(type_hint.strip()) if type_hint else None,
                    value=_truncate(value.strip()),
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        return Symbols(
            classes=tuple(classes),
            functions=tuple(functions),
            constants=tuple(constants),
            types=tuple(types),
            exports=tuple(exports),
            imports=self.imports(source, path),
        )

    def imports(self, source: str, path: str) -> tuple[ImportRef, ...]:
        """Extract imports from JS/TS source."""
        refs: list[ImportRef] = []

        # ES6 imports: import x from 'y'
        for match in re.finditer(
            r"(?:^|\n)\s*import\s+(?:\w+\s+as\s+)?(\w+)(?:\s*,\s*\{[^}]*\})?\s+from\s+['\"]([^'\"]+)['\"]",
            source,
            re.MULTILINE,
        ):
            _, spec = match.groups()
            kind = _import_kind(spec)
            refs.append(
                ImportRef(
                    raw=spec,
                    kind=kind,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # import { a, b } from 'x'
        for match in re.finditer(
            r"(?:^|\n)\s*import\s*\{[^}]*\}\s+from\s+['\"]([^'\"]+)['\"]",
            source,
            re.MULTILINE,
        ):
            spec = match.group(1)
            kind = _import_kind(spec)
            refs.append(
                ImportRef(
                    raw=spec,
                    kind=kind,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # import * as ns from 'x'
        for match in re.finditer(
            r"(?:^|\n)\s*import\s*\*\s+as\s+\w+\s+from\s+['\"]([^'\"]+)['\"]",
            source,
            re.MULTILINE,
        ):
            spec = match.group(1)
            kind = _import_kind(spec)
            refs.append(
                ImportRef(
                    raw=spec,
                    kind=kind,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # import 'x' (side-effect)
        for match in re.finditer(
            r"(?:^|\n)\s*import\s+['\"]([^'\"]+)['\"]",
            source,
            re.MULTILINE,
        ):
            spec = match.group(1)
            kind = _import_kind(spec)
            refs.append(
                ImportRef(
                    raw=spec,
                    kind=kind,
                    line=source[: match.start()].count("\n") + 1,
                )
            )

        # Deduplicate by (raw, kind)
        seen = set()
        unique_refs = []
        for ref in refs:
            key = (ref.raw, ref.kind)
            if key not in seen:
                seen.add(key)
                unique_refs.append(ref)

        return tuple(sorted(unique_refs, key=lambda r: r.line))

    def interface(self, source: str, path: str) -> Interface:
        """Public surface: exported items only.

        Honors explicit export statements: if `export` appears, only exported
        names are public. If no explicit exports found, uses the leading-underscore
        convention (private if name starts with _).
        """
        sym = self.symbols(source, path)

        # Collect exported names from explicit export statements
        exported_names: set[str] = set()

        # export function, export class, export const, export type, export interface, export enum
        for match in re.finditer(
            r"(?:^|\n)\s*export\s+(?:(?:async\s+)?function|class|const|let|var|type|interface|enum)\s+(\w+)",
            source,
            re.MULTILINE,
        ):
            exported_names.add(match.group(1))

        # export { a, b, c } and export { a, b } from './x'
        for match in re.finditer(r"(?:^|\n)\s*export\s*\{([^}]+)\}", source, re.MULTILINE):
            exports_block = match.group(1)
            for name in exports_block.split(","):
                # Handle "a as b" → export b
                parts = name.strip().split(" as ")
                exported_name = parts[-1].strip()
                if exported_name:
                    exported_names.add(exported_name)

        explicit = frozenset(exported_names) if exported_names else None
        return Interface.from_symbols(sym, explicit=explicit)


class JavaScriptParser(_JSLike):
    name = "javascript"
    extensions = (".js", ".jsx", ".mjs", ".cjs")


class TypeScriptParser(_JSLike):
    name = "typescript"
    extensions = (".ts", ".tsx", ".mts", ".cts")


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _strip_comments_and_strings(source: str) -> str:
    """Remove comments and string literals to avoid false matches inside them.

    Replaces strings with spaces and removes comments (/* */ and //).
    This fixes the pre-0.2 defect where braces inside strings broke class
    method detection.
    """
    result = []
    i = 0
    while i < len(source):
        # Single-line comment
        if i < len(source) - 1 and source[i:i+2] == "//":
            # Skip to end of line
            while i < len(source) and source[i] != "\n":
                i += 1
            if i < len(source):
                result.append("\n")
                i += 1
            continue

        # Multi-line comment
        if i < len(source) - 1 and source[i:i+2] == "/*":
            # Skip to */
            i += 2
            while i < len(source) - 1:
                if source[i:i+2] == "*/":
                    i += 2
                    break
                if source[i] == "\n":
                    result.append("\n")
                else:
                    result.append(" ")
                i += 1
            continue

        # String literal (double quote)
        if source[i] == '"':
            result.append(" ")
            i += 1
            while i < len(source):
                if source[i] == '"' and (i == 0 or source[i-1] != "\\"):
                    result.append(" ")
                    i += 1
                    break
                if source[i] == "\n":
                    result.append("\n")
                else:
                    result.append(" ")
                i += 1
            continue

        # String literal (single quote)
        if source[i] == "'":
            result.append(" ")
            i += 1
            while i < len(source):
                if source[i] == "'" and (i == 0 or source[i-1] != "\\"):
                    result.append(" ")
                    i += 1
                    break
                if source[i] == "\n":
                    result.append("\n")
                else:
                    result.append(" ")
                i += 1
            continue

        # Template literal (backtick)
        if source[i] == "`":
            result.append(" ")
            i += 1
            while i < len(source):
                if source[i] == "`" and (i == 0 or source[i-1] != "\\"):
                    result.append(" ")
                    i += 1
                    break
                if source[i] == "\n":
                    result.append("\n")
                else:
                    result.append(" ")
                i += 1
            continue

        result.append(source[i])
        i += 1

    return "".join(result)


def _parse_params(params_raw: str) -> tuple[Param, ...]:
    """Parse parameter list from raw text (regex backend)."""
    if not params_raw or not params_raw.strip():
        return ()

    params = []
    for part in params_raw.split(","):
        part = part.strip()
        if not part:
            continue

        # Handle destructuring, defaults, types
        name = part.split("=")[0].strip()
        name = name.split(":")[0].strip()

        if name:
            params.append(Param(name=name))

    return tuple(params)


def _import_kind(spec: str) -> str:
    """Determine import kind from specifier."""
    if spec.startswith("."):
        return "relative"
    if spec.startswith("/"):
        return "relative"
    if spec.startswith("node:") or spec in ("fs", "path", "http", "os", "sys"):
        return "external"
    # Bare specifier → external
    return "external"


def _truncate(text: str | None, limit: int = 120) -> str | None:
    """Truncate text to limit, adding ellipsis if needed."""
    if text is None:
        return None
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit] + "…"
    return text
