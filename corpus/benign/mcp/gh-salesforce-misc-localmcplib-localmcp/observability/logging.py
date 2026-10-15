"""Structured file-only logging for stdio MCP servers."""

from __future__ import annotations

import logging
import sys
from collections.abc import Mapping, Sequence
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from typing import Any, cast

import structlog

_DEFAULT_LEVEL = logging.WARNING
_HANDLER_NAME = "localmcp-file"
_LAST_RESORT: logging.Handler = logging.NullHandler()
logging.lastResort = _LAST_RESORT
logging.raiseExceptions = False
logging.captureWarnings(True)

_SHARED_PROCESSORS: list[structlog.typing.Processor] = [
    structlog.contextvars.merge_contextvars,
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.processors.TimeStamper(fmt="iso", utc=True),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
]


def resolve_log_level(
    env: Mapping[str, str],
    *,
    env_var: str,
    file_level: str | None = None,
    default: int = _DEFAULT_LEVEL,
) -> int:
    """Resolve env > file > default; invalid configured values use default."""
    raw = env.get(env_var)
    if raw and raw.strip():
        return logging.getLevelNamesMapping().get(raw.strip().upper(), default)
    if file_level and file_level.strip():
        return logging.getLevelNamesMapping().get(file_level.strip().upper(), default)
    return default


def _configure_structlog() -> None:
    structlog.configure(
        processors=[*_SHARED_PROCESSORS, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=False,
    )


def configure_logging(
    *,
    log_file: Path,
    level: int,
    rotation_when: str = "midnight",
    backup_count: int = 7,
    managed_loggers: Sequence[str] = ("fastmcp",),
) -> None:
    """Install exactly one JSON file handler, falling back to a null handler."""
    _configure_structlog()
    handler: logging.Handler
    try:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        handler = TimedRotatingFileHandler(
            log_file,
            when=rotation_when,
            backupCount=backup_count,
            utc=True,
            encoding="utf-8",
        )
        handler.setFormatter(
            structlog.stdlib.ProcessorFormatter(
                processor=structlog.processors.JSONRenderer(),
                foreign_pre_chain=_SHARED_PROCESSORS,
            )
        )
    except OSError:
        handler = logging.NullHandler()
    handler.set_name(_HANDLER_NAME)

    root = logging.getLogger()
    _replace_handlers(root, handler)
    root.setLevel(level)

    for name in managed_loggers:
        logger = logging.getLogger(name)
        _close_handlers(logger)
        logger.setLevel(logging.NOTSET)
        logger.propagate = True

    logging.captureWarnings(True)
    logging.lastResort = _LAST_RESORT
    logging.raiseExceptions = False


def _replace_handlers(logger: logging.Logger, handler: logging.Handler) -> None:
    _close_handlers(logger)
    logger.addHandler(handler)


def _close_handlers(logger: logging.Logger) -> None:
    for existing in list(logger.handlers):
        logger.removeHandler(existing)
        try:
            existing.close()
        except Exception:
            pass


def _is_stdio_handler(handler: logging.Handler) -> bool:
    if not isinstance(handler, logging.StreamHandler) or isinstance(handler, logging.FileHandler):
        return False
    return getattr(handler, "stream", None) in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__)


def _ensure_safe_route(name: str | None = None) -> None:
    logging.lastResort = _LAST_RESORT
    logging.raiseExceptions = False
    node: logging.Logger | None = logging.getLogger(name)
    while node is not None:
        for handler in list(node.handlers):
            if _is_stdio_handler(handler):
                node.removeHandler(handler)
                try:
                    handler.close()
                except Exception:
                    pass
        node = node.parent
    root = logging.getLogger()
    if not root.handlers:
        null = logging.NullHandler()
        null.set_name(_HANDLER_NAME)
        root.addHandler(null)


class _SafeLogger:
    __slots__ = ("_name",)

    def __init__(self, name: str | None) -> None:
        self._name = name

    def __getattr__(self, attr: str) -> Any:
        if not structlog.is_configured():
            _configure_structlog()
        _ensure_safe_route(self._name)
        return getattr(structlog.get_logger(self._name), attr)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a lazy logger that cannot fall back to stdout or stderr."""
    return cast(structlog.stdlib.BoundLogger, _SafeLogger(name))


_configure_structlog()
_ensure_safe_route()
