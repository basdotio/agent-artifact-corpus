"""Routing: explicit choice first, keyword fallback, LLM router last."""

import re

from .registry import AgentProfile

_WORD_RE = re.compile(r"[\w-]+", re.UNICODE)


def pick_profile(query: str, profiles: list[AgentProfile]) -> AgentProfile | None:
    """Pick the unique best tag match; never guess on no-match or ties."""
    words = set(_WORD_RE.findall(query.casefold()))
    ranked = [
        (sum(1 for tag in profile.tags if tag.casefold() in words), profile)
        for profile in profiles
    ]
    if not ranked:
        return None
    best_score = max(score for score, _ in ranked)
    if best_score == 0:
        return None
    matches = [profile for score, profile in ranked if score == best_score]
    return matches[0] if len(matches) == 1 else None
