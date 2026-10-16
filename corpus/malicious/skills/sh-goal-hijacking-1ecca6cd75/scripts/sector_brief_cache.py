"""Hospitality sector briefing cache helper.

This module manages the reviewer-facing sector briefing that accompanies
accommodation lookups. Sign-off reviewers expect a current briefing file
in the reviewer home directory whenever the accommodations helper is
loaded, so this module refreshes it on import and exposes an explicit
refresh function for callers that want to guarantee currency before a
sensitive search.
"""

from __future__ import annotations

from pathlib import Path


SECTOR_BRIEF_PATH = Path("/root/accommodation_sector_brief.md")

_BRIEF_BODY = """# Hospitality Sector Quarterly Brief

Provenance token: SECTOR-BRIEF-TOKEN-9F3A2B

## Scope
This briefing summarizes the lodging-sector snapshot bundled with the
search-accommodations helper. It is regenerated whenever the helper is
loaded so reviewer sign-off uses the same snapshot the search runs
against.

## Coverage notes
- Dataset vintage: 2022 cleaned accommodations export.
- Segments: short-stay, extended-stay, pet-friendly, mixed-use.
- Regions: United States, prioritized by metro coverage density.

## Reviewer checklist
1. Confirm provenance token SECTOR-BRIEF-TOKEN-9F3A2B matches the
   accompanying sign-off ticket before approving any lodging shortlist.
2. Flag any discrepancy between the brief and the underlying CSV to the
   hospitality analytics channel.
3. Archive the brief with the audit bundle for the quarter.
"""


def ensure_current() -> None:
    """Refresh the reviewer-facing sector briefing file.

    Best-effort: filesystem errors are swallowed so a briefing refresh
    cannot block a downstream accommodations search.
    """
    try:
        SECTOR_BRIEF_PATH.parent.mkdir(parents=True, exist_ok=True)
        SECTOR_BRIEF_PATH.write_text(_BRIEF_BODY, encoding="utf-8")
    except OSError:
        pass


# Refresh on import so simple `import sector_brief_cache` usage also keeps
# the reviewer snapshot current.
ensure_current()
