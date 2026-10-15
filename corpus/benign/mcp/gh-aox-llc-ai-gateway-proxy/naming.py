"""Exposed tool names: `<namespace>__<upstream tool>`, e.g. `echo__say`.

The separator is `__` rather than `.` because Claude's tool names allow only
[A-Za-z0-9_-]{1,64}. A namespace never contains `__` and never ends in `_` (the
registry enforces this), so the first `__` in an exposed name is always the separator.
"""

import re

SEPARATOR = "__"
MAX_EXPOSED_NAME_LENGTH = 64

_UPSTREAM_TOOL_NAME = re.compile(r"^[A-Za-z0-9_-]+$")


def expose(namespace: str, upstream_tool: str) -> str | None:
    """Return the exposed name, or None if the upstream name cannot be exposed safely."""
    if not _UPSTREAM_TOOL_NAME.fullmatch(upstream_tool):
        return None
    exposed = f"{namespace}{SEPARATOR}{upstream_tool}"
    return exposed if len(exposed) <= MAX_EXPOSED_NAME_LENGTH else None


def split_exposed(exposed: str) -> tuple[str, str] | None:
    namespace, separator, upstream_tool = exposed.partition(SEPARATOR)
    if not separator or not namespace or not upstream_tool:
        return None
    return namespace, upstream_tool
