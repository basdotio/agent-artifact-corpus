"""Reading TOML without requiring a TOML reader.

`tomllib` entered the stdlib in 3.11, and this package supports 3.10 with no
dependencies. So on 3.10 there may be no TOML parser at all, and every caller
has to cope with that.

Each caller coping separately is how this broke: the guarded import was
duplicated at four sites, and at one of them the surrounding `except` clause
listed `(OSError, ValueError)` — which does not catch `ModuleNotFoundError`.
`drydock codemap` therefore crashed outright on a clean Python 3.10 install.
CI never saw it, because CI installs the `dev` extra, which pulls in `tomli`.

One function, one place to get it right. A missing parser is not an error here:
TOML files are read for enrichment (entry points, platform versions, declared
dependencies), and the correct behaviour without a reader is to return nothing
and carry on.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

__all__ = ["load_toml", "loads_toml", "toml_available"]

_READER: Any = None
_CHECKED = False


def _reader() -> Any:
    global _READER, _CHECKED
    if not _CHECKED:
        _CHECKED = True
        try:
            import tomllib as _t  # Python 3.11+
        except ModuleNotFoundError:
            try:
                import tomli as _t  # 3.10 backport, optional
            except ModuleNotFoundError:
                _t = None
        _READER = _t
    return _READER


def toml_available() -> bool:
    """Whether any TOML parser is importable in this environment."""
    return _reader() is not None


def load_toml(path: Path | str) -> dict[str, Any] | None:
    """Parse a TOML file, or return None.

    Returns None when there is no parser available, the file is missing, or it
    is malformed. Never raises -- callers read TOML to enrich a result, and a
    missing enrichment must not sink an analysis.
    """
    reader = _reader()
    if reader is None:
        return None
    try:
        with open(path, "rb") as handle:
            data = reader.load(handle)
    except (OSError, ValueError, AttributeError):
        return None
    return data if isinstance(data, dict) else None


def loads_toml(source: str) -> dict[str, Any] | None:
    """Parse TOML already held as text, or return None.

    Same contract as `load_toml` for callers that read the file themselves
    (the walker hands analyzers decoded source, so re-reading from disk would
    be a second read and a second chance to disagree about encoding).
    """
    reader = _reader()
    if reader is None:
        return None
    try:
        data = reader.loads(source)
    except (ValueError, AttributeError, TypeError):
        return None
    return data if isinstance(data, dict) else None
