"""Logger module for MCP Appium server."""
import logging
import sys
from typing import Any, Dict

# Configure logging format
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT,
    stream=sys.stderr,
)

logger = logging.getLogger('appium-mcp')


def debug(message: str, data: Any = None) -> None:
    """Log debug message with optional data."""
    if data is not None:
        logger.debug(f"{message}: {data}")
    else:
        logger.debug(message)


def info(message: str, data: Any = None) -> None:
    """Log info message with optional data."""
    if data is not None:
        logger.info(f"{message}: {data}")
    else:
        logger.info(message)


def error(message: str, data: Any = None) -> None:
    """Log error message with optional data."""
    if data is not None:
        logger.error(f"{message}: {data}")
    else:
        logger.error(message)


def warn(message: str, data: Any = None) -> None:
    """Log warning message with optional data."""
    if data is not None:
        logger.warning(f"{message}: {data}")
    else:
        logger.warning(message)


def debug(message: str, data: Any = None) -> None:
    """Log debug message with optional data."""
    if data is not None:
        logger.debug(f"{message}: {data}")
    else:
        logger.debug(message)
