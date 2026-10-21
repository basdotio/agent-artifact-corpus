"""Environment variable expansion for configuration files.

Supports {env:VAR} and {env:VAR:-default} placeholder syntax.
"""

import os
import re
from typing import Any

_ENV_PATTERN = re.compile(r"\{env:([A-Z_][A-Z0-9_]*)(?::-([^}]*))?\}")


def expand_env(value: str, environ: dict[str, str] | None = None) -> str:
    """Expand {env:VAR} and {env:VAR:-default} placeholders in a string."""
    env = environ if environ is not None else os.environ

    def repl(m: re.Match[str]) -> str:
        var = m.group(1)
        default = m.group(2)
        return env.get(var, default if default is not None else "")

    return _ENV_PATTERN.sub(repl, value)


def expand_env_in_obj(obj: Any, environ: dict[str, str] | None = None) -> Any:
    """Recursively expand {env:...} placeholders in a dict/list/str structure."""
    if isinstance(obj, str):
        return expand_env(obj, environ)
    if isinstance(obj, dict):
        return {k: expand_env_in_obj(v, environ) for k, v in obj.items()}
    if isinstance(obj, list):
        return [expand_env_in_obj(v, environ) for v in obj]
    return obj
