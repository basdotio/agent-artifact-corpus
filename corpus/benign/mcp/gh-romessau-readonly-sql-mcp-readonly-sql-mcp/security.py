"""AST-based query validation."""

from __future__ import annotations

from sqlglot import exp, parse
from sqlglot.errors import ParseError


class QueryValidationError(ValueError):
    """SQL does not meet the server's read-only policy."""


MAX_QUERY_LENGTH = 50_000

_DANGEROUS_FUNCTIONS = frozenset(
    {
        "load_extension",
        "readfile",
        "sqlite3_load_extension",
        "sqlite_load_extension",
        "writefile",
    }
)

_FORBIDDEN_NODES = (
    exp.Alter,
    exp.Attach,
    exp.Command,
    exp.Copy,
    exp.Create,
    exp.Delete,
    exp.Detach,
    exp.Drop,
    exp.Insert,
    exp.Into,
    exp.Merge,
    exp.Pragma,
    exp.Transaction,
    exp.Update,
)

_COMPOUND_NODES = (exp.Union, exp.Intersect, exp.Except)


def is_pragma_name(name: str) -> bool:
    """Return whether a normalized SQL name exposes SQLite pragma data."""
    return name.lower().startswith("pragma_")


def _function_name(node: exp.Func) -> str:
    if isinstance(node, exp.Anonymous):
        return node.name.lower()
    return node.key.lower()


def _unwrap(node: exp.Expression) -> exp.Expression:
    current = node
    while isinstance(current, exp.Subquery) and current.this is not None:
        current = current.this
    return current


def _is_read_shape(node: exp.Expression) -> bool:
    query = _unwrap(node)
    if isinstance(query, _COMPOUND_NODES):
        left = query.this
        right = query.args.get("expression")
        return (
            isinstance(left, exp.Expression)
            and isinstance(right, exp.Expression)
            and _is_read_shape(left)
            and _is_read_shape(right)
        )
    return isinstance(query, (exp.Select, exp.Values))


def _referenced_names(statement: exp.Expression) -> list[str]:
    names: list[str] = []
    for table in statement.find_all(exp.Table):
        if table.name:
            names.append(table.name.lower())
        this = table.this
        if isinstance(this, exp.Func):
            names.append(_function_name(this))
    for function in statement.find_all(exp.Func):
        names.append(_function_name(function))
    return names


def validate_query(sql: str, dialect: str = "sqlite") -> str:
    """Require one read-only query and reject dangerous AST constructs."""
    # Bound parser work before building an AST from untrusted client input.
    if len(sql) > MAX_QUERY_LENGTH:
        raise QueryValidationError("query exceeds the maximum length")
    candidate = sql.strip()
    try:
        statements = [
            statement
            for statement in parse(candidate, read=dialect)
            if statement and not isinstance(statement, exp.Semicolon)
        ]
    except (ParseError, ValueError) as exc:
        raise QueryValidationError("query is not valid SQL") from exc
    if len(statements) != 1:
        raise QueryValidationError("query must contain exactly one statement")

    statement = statements[0]
    if not _is_read_shape(statement):
        raise QueryValidationError("query must be a SELECT statement")
    if any(statement.find(node_type) is not None for node_type in _FORBIDDEN_NODES):
        raise QueryValidationError("query contains a forbidden operation")

    for name in _referenced_names(statement):
        if is_pragma_name(name):
            raise QueryValidationError("query contains a forbidden operation")
        if name in _DANGEROUS_FUNCTIONS:
            raise QueryValidationError("query calls a forbidden function")
    return candidate
