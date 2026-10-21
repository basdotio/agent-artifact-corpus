"""Session storage for persisting browser authentication state."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stderr)

STORAGE_PATH = Path.home() / ".suno-mcp" / "session" / "storage_state.json"


class SessionStore:
    """Manages persistent browser session state (cookies, localStorage)."""

    def __init__(self, path: Optional[Path] = None) -> None:
        self.path = path or STORAGE_PATH

    def exists(self) -> bool:
        """Check if a saved session exists."""
        return self.path.exists()

    def load(self) -> Optional[dict[str, Any]]:
        """Load saved session state. Returns None if not found or invalid."""
        if not self.path.exists():
            return None
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            logger.info("Session state loaded from %s", self.path)
            return data
        except Exception as e:
            logger.warning("Failed to load session state: %s", e)
            return None

    def save(self, state: dict[str, Any]) -> None:
        """Save session state to disk."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(state), encoding="utf-8")
        logger.info("Session state saved to %s", self.path)

    def clear(self) -> None:
        """Delete saved session state."""
        if self.path.exists():
            self.path.unlink()
            logger.info("Session state cleared")
