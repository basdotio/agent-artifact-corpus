"""Local browser isolation and CSRF defenses; no user authentication claims."""

import asyncio
import secrets
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from backend.agent.models import Conversation

COOKIE = "homeresolve_demo"


class SessionLimitError(ValueError):
    """The bounded local session store is temporarily full."""


@dataclass
class BrowserSession:
    csrf: str = field(default_factory=lambda: secrets.token_urlsafe(32))
    created: float = field(default_factory=time.monotonic)
    conversations: OrderedDict[str, Conversation] = field(default_factory=OrderedDict)
    responses: OrderedDict[str, tuple[str, Any]] = field(default_factory=OrderedDict)
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


class SessionStore:
    def __init__(self) -> None:
        self.sessions: dict[str, BrowserSession] = {}

    def get(self, identifier: str | None) -> BrowserSession | None:
        now = time.monotonic()
        for key in list(self.sessions):
            if now - self.sessions[key].created >= 3600:
                del self.sessions[key]
        return self.sessions.get(identifier or "")

    def create(self) -> tuple[str, BrowserSession]:
        self.get(None)
        if len(self.sessions) >= 100:
            raise SessionLimitError("Local browser session limit reached")
        identifier = secrets.token_urlsafe(32)
        session = BrowserSession()
        self.sessions[identifier] = session
        return identifier, session
