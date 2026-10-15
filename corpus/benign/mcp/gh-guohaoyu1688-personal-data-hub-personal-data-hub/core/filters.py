"""A small expression grammar; user values never become SQL syntax."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any

# Each expression is a comparison, joined by AND. Quoted strings can contain AND.
TOKEN = re.compile(
    r"""\s*(?:(?P<field>[a-z][a-z0-9_]*)\s*(?P<op>!=|>=|<=|=|>|<|~)\s*(?P<value>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s;]+))"""
)


def parse_where(
    expression: str | None, columns: dict[str, dict[str, Any]], *, reveal: bool = False
) -> tuple[str, list[Any]]:
    if not expression:
        return "", []
    sql: list[str] = []
    values: list[Any] = []
    position = 0
    while position < len(expression):
        match = TOKEN.match(expression, position)
        if not match:
            raise ValueError(
                "where must be FIELD OP VALUE comparisons joined by AND; quote values containing spaces"
            )
        name, operator, value = match.group("field", "op", "value")
        if name not in columns:
            raise ValueError(f"unknown filter field: {name}")
        options = columns[name]
        if options.get("sensitive") and not reveal:
            raise ValueError("filtering sensitive fields requires reveal=true or --reveal")
        if value[:1] in {"'", '"'}:
            value = re.sub(r"\\(.)", r"\1", value[1:-1])
        if operator == "~":
            if options.get("type", "text") != "text":
                raise ValueError("fuzzy matching requires a text field")
            value = "%" + value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
            sql.append(f"\"{name}\" LIKE ? ESCAPE '\\'")
        else:
            column = f'"{name}"'
            if options.get("type") in {"integer", "decimal"} and value.lower() != "null":
                try:
                    if not Decimal(value).is_finite():
                        raise ValueError
                except (InvalidOperation, ValueError) as exc:
                    raise ValueError("numeric filter requires a finite number") from exc
                # Decimal comparisons use the registered exact comparator, avoiding float casts.
                sql.append(f"decimal_compare({column}, ?) {operator} 0")
            elif value.lower() == "null" and operator in {"=", "!="}:
                sql.append(f"{column} IS {'NOT ' if operator == '!=' else ''}NULL")
                position = match.end()
                if not expression[position:].strip():
                    break
                conjunction = re.match(r"\s+AND\s+", expression[position:], re.I)
                if not conjunction:
                    raise ValueError("only AND conjunctions are supported")
                position += conjunction.end()
                continue
            else:
                sql.append(f"{column} {operator} ?")
        values.append(value)
        position = match.end()
        if not expression[position:].strip():
            break
        conjunction = re.match(r"\s+AND\s+", expression[position:], re.I)
        if not conjunction:
            raise ValueError("only AND conjunctions are supported; SQL fragments are not accepted")
        position += conjunction.end()
    return " AND ".join(sql), values
