# SPDX-FileCopyrightText: 2026 The avenir-mcp contributors
# SPDX-License-Identifier: MIT

"""Tell the agent, once a day at most, that a newer avenir-mcp is on PyPI.

A server pinned to a version, or started from a cached copy, never learns that a
fix was released. At start-up, unless switched off (see off), the server asks
PyPI for the latest release, remembers the answer for a day, and adds a line to its
instructions when it is behind. It never upgrades itself: the user decides, and only
they know how it was installed.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

PYPI_URL = "https://pypi.org/pypi/avenir-mcp/json"
"""PyPI's JSON page for the project: one GET, no account, no identifier sent."""

TIMEOUT_SECONDS = 1.5
"""Start-up never waits longer than this on PyPI."""

FRESH_FOR = timedelta(days=1)
"""How long an answer, or a failure, is remembered."""

_RELEASE = re.compile(r"\d+(\.\d+)*")

Getter = Callable[..., Any]


def release_number(version: str) -> tuple[int, ...] | None:
    """The numbers of a plain release such as 0.2.1.

    Args:
        version: A version string, from PyPI or from this package.

    Returns:
        The numbers, or None for a pre-release or anything that is not a version.
    """
    if not _RELEASE.fullmatch(version):
        return None
    return tuple(int(part) for part in version.split("."))


def newer(current: str, latest: str) -> bool:
    """Say whether latest is a plain release above current.

    Args:
        current: The running version.
        latest: The version PyPI publishes.

    Returns:
        True when latest is a higher release number.
    """
    mine, theirs = release_number(current), release_number(latest)
    return mine is not None and theirs is not None and theirs > mine


def get_latest(get: Getter = httpx.get) -> str | None:
    """Get the latest release from PyPI.

    Args:
        get: httpx.get, or a stand-in in tests.

    Returns:
        The version string, or None when PyPI cannot be reached or answers oddly.
    """
    try:
        response = get(PYPI_URL, timeout=TIMEOUT_SECONDS, follow_redirects=False)
        response.raise_for_status()
        version = response.json()["info"]["version"]
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as error:
        logger.info("Update check skipped: %s", error)
        return None
    return version if isinstance(version, str) else None


def cache_path(env: Mapping[str, str]) -> Path:
    """Locate the file that remembers the last check.

    Args:
        env: The environment.

    Returns:
        latest-version.json in the XDG cache directory.
    """
    cache_home = env.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(cache_home) / "avenir-mcp" / "latest-version.json"


def latest_version(path: Path, now: datetime, get: Getter = httpx.get) -> str | None:
    """Give the latest release, from a check less than a day old or from PyPI.

    Args:
        path: The cache file.
        now: The current time, timezone-aware.
        get: httpx.get, or a stand-in in tests.

    Returns:
        The latest version, or None when unknown.
    """
    try:
        # The cache holds the JSON written below, which json.dumps escapes to ASCII, so
        # every encoding Python can be told to use here reads back the same text. On its
        # own line, so the pragma covers no more than this one read.
        remembered = path.read_text(encoding="utf-8")  # pragma: no mutate
        cached = json.loads(remembered)
        if now - datetime.fromisoformat(cached["checked_at"]) < FRESH_FOR:
            latest = cached["latest"]
            return latest if isinstance(latest, str) else None
    except (OSError, ValueError, KeyError, TypeError):
        pass
    latest = get_latest(get)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        answer = json.dumps({"checked_at": now.isoformat(), "latest": latest})
        # json.dumps escapes anything beyond ASCII, so every encoding Python can be told
        # to use here writes the same bytes. On its own line, so the pragma covers no
        # more than this one write.
        path.write_text(answer, encoding="utf-8")  # pragma: no mutate
    except OSError as error:
        logger.info("Update check not remembered: %s", error)
    return latest


def notice(current: str, latest: str | None) -> str | None:
    """Write the line added to the instructions when a newer release exists.

    Only a plain release number from PyPI is ever quoted, so nothing else from the
    network reaches the agent.

    Args:
        current: The running version.
        latest: The version PyPI publishes, or None.

    Returns:
        The line, or None when the server is up to date or the answer is unusable.
    """
    if latest is None or not newer(current, latest):
        return None
    return (
        f"Update: avenir-mcp {latest} is available; this server runs {current}. Tell the "
        "user once, briefly, and leave the upgrade to them: with uvx, start "
        "avenir-mcp@latest or change the pinned version, then reconnect the server "
        "(https://pypi.org/project/avenir-mcp/). The check is turned off with "
        "AVENIR_MCP_NO_UPDATE_CHECK=1."
    )


def off(env: Mapping[str, str]) -> bool:
    """Say whether the check is switched off.

    Args:
        env: The environment.

    Returns:
        True with AVENIR_MCP_NO_UPDATE_CHECK=1, with DO_NOT_TRACK=1 (the common
        convention for tools that would call home), or in a CI run (CI=true or 1).
    """
    # The empty default only marks "no CI variable", and it is matched against "true" and
    # "1", so another default answers the same. On its own line, so the pragma covers no
    # more than this one lookup.
    in_ci = env.get("CI", "")  # pragma: no mutate
    return (
        env.get("AVENIR_MCP_NO_UPDATE_CHECK") == "1"
        or env.get("DO_NOT_TRACK") == "1"
        or in_ci.lower() in {"true", "1"}
    )


def check(
    env: Mapping[str, str], current: str, now: datetime, get: Getter = httpx.get
) -> str | None:
    """Check for a newer release, as the server starts.

    Args:
        env: The environment.
        current: The running version.
        now: The current time, timezone-aware.
        get: httpx.get, or a stand-in in tests.

    Returns:
        The line to add to the instructions, or None.
    """
    if off(env):
        return None
    return notice(current, latest_version(cache_path(env), now, get))
