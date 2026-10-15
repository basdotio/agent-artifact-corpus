import ipaddress
import socket
from collections.abc import Callable, Collection
from urllib.parse import urlparse

import sqlglot
from sqlglot import exp

from au_opendata_mcp.errors import DownloadFailed, SqlRejected

SAFE_SCHEMES = frozenset({"http", "https"})
MAX_REDIRECTS = 5


def _resolve_host(host: str) -> list[str]:
    return [info[4][0] for info in socket.getaddrinfo(host, None)]


def assert_safe_url(url: str, *, resolve: Callable[[str], list[str]] = _resolve_host) -> None:
    """Refuse anything that is not a public http(s) address.

    Every resolved address is checked, not just the first, so a host that answers with
    one public and one private address cannot slip through.
    """
    parsed = urlparse(url)
    scheme = parsed.scheme.lower()
    if scheme not in SAFE_SCHEMES:
        raise DownloadFailed(
            f"refusing {scheme or 'scheme-less'} URL; only http and https are allowed"
        )

    host = parsed.hostname
    if not host:
        raise DownloadFailed(f"URL has no host: {url!r}")

    try:
        addresses = resolve(host)
    except OSError as exc:
        raise DownloadFailed(f"could not resolve host {host!r}: {exc}") from exc

    if not addresses:
        raise DownloadFailed(f"host {host!r} resolved to no addresses")

    for raw in addresses:
        ip = ipaddress.ip_address(raw)
        # `is_global` is the basis rather than enumerating private/loopback/link-local/
        # reserved/unspecified by hand: hand-enumerated ranges are exactly what let
        # CGNAT space (100.64.0.0/10) through undetected, and new reserved ranges get
        # allocated over time. `is_multicast` must still be checked separately and
        # surprisingly: `ip.is_global` is True for multicast addresses (e.g.
        # 224.0.0.1), so `not is_global` alone would let multicast through.
        if not ip.is_global or ip.is_multicast:
            raise DownloadFailed(
                f"refusing to fetch {host!r}: it resolves to the non-public address {ip}"
            )


def assert_url_in_catalog(url: str, catalog_urls: Collection[str]) -> None:
    """Only URLs the portal itself published for this resource may be fetched."""
    if url not in set(catalog_urls):
        raise DownloadFailed(
            "refusing to fetch a URL that is not listed in the dataset's catalog metadata"
        )


QUERY_TABLE = "t"

# Table-valued and file-reading functions. The DuckDB lockdown in services/query.py is the
# real defence; this makes the rejection message specific instead of a PermissionException.
DENIED_FUNCTIONS = frozenset(
    {
        "read_csv",
        "read_csv_auto",
        "read_parquet",
        "read_json",
        "read_json_auto",
        "read_ndjson",
        "read_text",
        "read_blob",
        "glob",
        "parquet_scan",
        "csv_scan",
    }
)

# sqlglot gives some functions a dedicated AST class instead of exp.Anonymous — verified for
# read_csv -> exp.ReadCSV and read_parquet -> exp.ReadParquet; every other DENIED_FUNCTIONS
# name still resolves to exp.Anonymous. Checked by type here, not just by name, so a future
# sqlglot version that promotes another denied name to its own class still cannot slip
# through: the name-based check alone is tied to today's sqlglot AST shape.
DENIED_FUNCTION_TYPES: tuple[type[exp.Func], ...] = (exp.ReadCSV, exp.ReadParquet)


def _func_name(node: exp.Func) -> str:
    """Resolve a function node's name uniformly across exp.Anonymous and dedicated classes.

    exp.Anonymous.sql_name() returns the literal string "ANONYMOUS" and is useless — use
    .name instead. Dedicated classes (e.g. exp.ReadCSV) have no meaningful .name, but their
    .sql_name() gives the real SQL keyword (e.g. "READ_CSV").
    """
    name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
    return name.lower()


def validate_sql(sql: str) -> str:
    """Accept a single read-only DuckDB query over the table `t`. Reject everything else.

    Parsing rather than pattern matching, because comments, string literals and stacked
    statements all defeat pattern matching.
    """
    if not sql or not sql.strip():
        raise SqlRejected("SQL is empty")

    try:
        parsed = sqlglot.parse(sql, read="duckdb")
    except sqlglot.ParseError as exc:
        raise SqlRejected(f"could not parse SQL as DuckDB: {exc}") from exc

    # Do not filter out None entries: sqlglot yields one for each empty statement between
    # consecutive semicolons (e.g. "SELECT * FROM t;;" parses to [Select, None]), and that
    # must count as a second statement rather than be silently dropped.
    if len(parsed) != 1:
        raise SqlRejected(
            f"expected exactly one statement, found {len(parsed)}; submit a single SELECT"
        )

    tree = parsed[0]
    if not isinstance(tree, exp.Query):
        raise SqlRejected(
            f"only SELECT queries are allowed; this is a {type(tree).__name__.upper()} statement"
        )

    allowed_tables = {QUERY_TABLE} | {cte.alias_or_name for cte in tree.find_all(exp.CTE)}
    for table in tree.find_all(exp.Table):
        if table.name not in allowed_tables:
            shown = table.name or "a table-valued function"
            raise SqlRejected(f"only the table {QUERY_TABLE!r} may be queried; found {shown!r}")

    for func in tree.find_all(exp.Func):
        if isinstance(func, DENIED_FUNCTION_TYPES) or _func_name(func) in DENIED_FUNCTIONS:
            raise SqlRejected(f"the function {_func_name(func)}() is not allowed")

    return tree.sql(dialect="duckdb")


def wrap_with_limit(sql: str, limit: int) -> str:
    """Enforce the row cap by wrapping. The caller's query is never rewritten.

    One extra row is requested so truncation can be detected.
    """
    return f"SELECT * FROM ({sql}) LIMIT {limit + 1}"
