"""
Source trust tiering and recency ranker for Preflight.
Evaluates search results from SerpApi and ranks them by authority and freshness.
"""

import re
from datetime import datetime
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple

from preflight.models import EvidenceItem, TrustTier
from preflight.trusted_domains import get_domain_tier, normalize_host

# Regex for detecting versions in text (e.g., v2.0, 15.0, v3)
VERSION_REGEX = re.compile(r"\b(?:v|version)?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b", re.IGNORECASE)
MAJOR_VERSION_REGEX = re.compile(r"\b(?:v|version)\s*([0-9]+)\b", re.IGNORECASE)

# Keywords indicating breaking changes or deprecations
DEPRECATION_SIGNALS = [
    "deprecated", "deprecated in", "removed in", "renamed to", "moved to",
    "breaking change", "migration guide", "no longer supported", "has been replaced",
    "legacy", "obsolete", "discontinued"
]

# Keywords indicating current confirmation
CONFIRMATION_SIGNALS = [
    "stable", "latest", "introduced in", "still supported", "current version",
    "official documentation", "supported in", "actively maintained"
]

# Explicit tie-break sort order: Tier 1 > Tier 2 > Tier 3 > Tier 0 (Untrusted)
TIER_SORT_ORDER: Dict[int, int] = {1: 0, 2: 1, 3: 2, 0: 3}

# Retained from the design: 1.1x path bonus clamped to [0, 1]
PATH_AUTHORITY_BONUS = 1.1
PATH_AUTHORITY_MARKERS = ("/docs/", "/migration/", "/changelog/", "/guide/")

_CTRL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_SNIPPET_OPEN = "<untrusted_search_snippet>"
_SNIPPET_CLOSE = "</untrusted_search_snippet>"


def sanitize_snippet(text: str) -> str:
    """Strip control characters. Printable code and markup remain intact."""
    return _CTRL_CHARS.sub("", text or "").strip()


def wrap_untrusted(snippet: str) -> str:
    """Wrap raw snippet in untrusted delimiter boundary."""
    return f"{_SNIPPET_OPEN}\n{sanitize_snippet(snippet)}\n{_SNIPPET_CLOSE}"


def unwrap_untrusted(snippet: str) -> str:
    """Strip delimiter tags for internal regex analysis only. Never emit to caller."""
    s = snippet or ""
    if s.startswith(_SNIPPET_OPEN):
        s = s[len(_SNIPPET_OPEN):]
    if s.endswith(_SNIPPET_CLOSE):
        s = s[:-len(_SNIPPET_CLOSE)]
    return s.strip()


def path_authority_multiplier(url: str) -> float:
    path = urlparse(url or "").path.lower()
    return PATH_AUTHORITY_BONUS if any(m in path for m in PATH_AUTHORITY_MARKERS) else 1.0


def extract_domain(url: str) -> str:
    """Legacy helper: delegates directly to normalize_host."""
    return normalize_host(url)


def score_evidence(url: str, date_str: Optional[str]) -> Tuple[TrustTier, float]:
    """Single source of truth for tier + score. Clamped to [0.0, 1.0]."""
    host = normalize_host(url)
    tier, base = get_domain_tier(host)
    recency = ResultRanker.calculate_recency_score(date_str)
    raw = base * recency * path_authority_multiplier(url)
    return tier, ResultRanker.clamp_trust_score(raw)


class ResultRanker:
    """Ranks and weights raw SerpApi search results based on domain trust and recency."""

    extract_domain = staticmethod(normalize_host)

    @staticmethod
    def detect_signals(text: str) -> List[str]:
        """Detect deprecation and confirmation signals in snippets and titles using word-boundary matching."""
        text_lower = text.lower()
        signals = []
        for kw in DEPRECATION_SIGNALS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                signals.append(f"deprecation:{kw}")
        for kw in CONFIRMATION_SIGNALS:
            if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                signals.append(f"confirmation:{kw}")
        return signals

    extract_signals = detect_signals

    @staticmethod
    def calculate_recency_score(date_str: Optional[str]) -> float:
        """Calculate freshness score multiplier based on date string."""
        if not date_str:
            return 0.60
        dl = date_str.lower().strip()

        if any(t in dl for t in ("hour", "minute", "second", "day", "today", "yesterday", "just now")):
            return 1.00
        if "week" in dl:
            return 0.95

        # Numeric months BEFORE generic "month" branch
        m = re.search(r"\b(\d+)\s*month", dl)
        if m:
            months = int(m.group(1))
            if months <= 6:
                return 0.85
            return 0.70 if months < 24 else 0.40
        if "month" in dl:
            return 0.85

        # Numeric years BEFORE generic "year" branch
        m = re.search(r"\b(\d+)\s*year", dl)
        if m:
            return 0.70 if int(m.group(1)) == 1 else 0.40
        if re.search(r"\b(?:a|an|one)\s*year", dl):
            return 0.70

        # Bare calendar year compared dynamically against current year
        m = re.search(r"\b(20\d{2})\b", dl)
        if m:
            return 0.70 if (datetime.now().year - int(m.group(1))) <= 1 else 0.40

        return 0.60

    @staticmethod
    def clamp_trust_score(raw: float) -> float:
        """Clamp composite trust score to [0.0, 1.0]."""
        return max(0.0, min(1.0, round(raw, 3)))

    @classmethod
    def process_serp_item(cls, item: Dict[str, Any]) -> Optional[EvidenceItem]:
        """Convert a single SerpApi organic result into an EvidenceItem."""
        link = item.get("link", "") or item.get("url", "")
        title = item.get("title", "")
        raw_snippet = item.get("snippet", "")

        if not link or not (title or raw_snippet):
            return None

        domain = normalize_host(link)
        date_str = item.get("date")

        trust_tier, trust_score = score_evidence(link, date_str)

        # Detect signals on unwrapped text before wrapping
        combined_text = f"{title} {raw_snippet}"
        signals = cls.detect_signals(combined_text)

        # Detect versions in title and snippet
        v_match = VERSION_REGEX.search(combined_text) or MAJOR_VERSION_REGEX.search(combined_text)
        detected_version = v_match.group(1) if v_match else None

        # Wrap untrusted snippet with boundaries
        wrapped_snippet = wrap_untrusted(raw_snippet)

        return EvidenceItem(
            title=title,
            url=link,
            snippet=wrapped_snippet,
            domain=domain,
            trust_tier=trust_tier,
            trust_score=trust_score,
            published_date=date_str,
            detected_version=detected_version,
            signals=signals,
        )

    @classmethod
    def rank_results(cls, raw_serp_responses: List[Dict[str, Any]]) -> List[EvidenceItem]:
        """Extract, deduplicate, and sort evidence items by trust score and relevance."""
        seen_urls = set()
        evidence_list: List[EvidenceItem] = []

        for resp in raw_serp_responses:
            if not resp or not isinstance(resp, dict):
                continue

            # Process answer box if present
            answer_box = resp.get("answer_box", {})
            if answer_box and isinstance(answer_box, dict):
                ab_link = answer_box.get("link") or resp.get("search_parameters", {}).get("q", "")
                ab_snippet = answer_box.get("snippet") or answer_box.get("answer", "")
                if ab_snippet:
                    item = cls.process_serp_item({
                        "link": ab_link or "https://serpapi.com/answer-box",
                        "title": answer_box.get("title", "Instant Answer"),
                        "snippet": ab_snippet,
                    })
                    if item and item.url not in seen_urls:
                        seen_urls.add(item.url)
                        evidence_list.append(item)

            # Process organic results
            for org in resp.get("organic_results", []):
                item = cls.process_serp_item(org)
                if item and item.url not in seen_urls:
                    seen_urls.add(item.url)
                    evidence_list.append(item)

        # Sort: Primary by trust score descending, secondary by Tier priority (Tier 1 > Tier 2 > Tier 3 > Tier 0)
        evidence_list.sort(key=lambda ev: (-ev.trust_score, TIER_SORT_ORDER.get(ev.trust_tier, 3)))
        return evidence_list
