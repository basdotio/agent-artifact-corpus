"""Trusted service origins. Keys select an environment, never an arbitrary URL."""

from __future__ import annotations

import re

# Each key prefix names exactly one service. A missing origin disables that
# environment; never substitute staging for an unavailable production service.
_API_ORIGINS: dict[str, str | None] = {
    "test": "https://control-api-staging-3b57.up.railway.app",
    "live": "https://api.isagoge.in",
}


class ConfigurationError(ValueError):
    """An actionable configuration failure containing no credential material."""


def api_origin(api_key: str) -> str:
    match = re.fullmatch(r"lw_(?:(test|live)_)?([a-f0-9]{32})\.([A-Za-z0-9_-]{43})", api_key)
    if match is None:
        raise ConfigurationError(
            "this is not a LeanWarp API key; copy the whole key from the LeanWarp dashboard "
            "(it starts with lw_live_)"
        )
    # Before production existed, only staging issued untagged keys. This legacy
    # format always means test; production rejects it. Never probe other origins.
    origin = _API_ORIGINS[match[1] or "test"]
    if origin is None:
        raise ConfigurationError("this SDK release cannot use the LeanWarp service for this key")
    return origin
