"""stderr-only logger. stdout is reserved for the MCP stdio transport."""

from __future__ import annotations

import logging
import sys
from typing import Final

_LOGGER_NAME: Final = "manus_mcp"
_CONFIGURED = False


def get_logger(name: str | None = None) -> logging.Logger:
    global _CONFIGURED
    if not _CONFIGURED:
        root = logging.getLogger(_LOGGER_NAME)
        root.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        root.addHandler(handler)
        root.propagate = False
        _CONFIGURED = True
    return logging.getLogger(_LOGGER_NAME if name is None else f"{_LOGGER_NAME}.{name}")


def set_level(level: str) -> None:
    logging.getLogger(_LOGGER_NAME).setLevel(level.upper())
