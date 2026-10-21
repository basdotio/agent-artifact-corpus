"""§8.3 rule 3 conflict table — known-conflicting pattern pairs for the same part.

This is the SEED table of guide §8.3 rule 3: the guide names exactly these four pairs
("singleton vs dependency-injection, service-locator vs dependency-injection, template-method
vs strategy for the same variation point, mock vs stub for the same test seam"), and the rule
requires that "conflicting pairs may not both be selected for the same part".

The table is maintained alongside the catalog: when a catalog record documents a new conflict
(in ``related_patterns_notes`` or pitfalls), the pair lands here so Stage E can enforce it.
Conflicts are symmetric for selection purposes — order within a pair carries no meaning.
"""

from __future__ import annotations

#: §8.3 seed conflict pairs (canonical kebab names, order-independent).
CONFLICT_PAIRS: tuple[tuple[str, str], ...] = (
    ("singleton", "dependency-injection"),
    ("service-locator", "dependency-injection"),
    ("template-method", "strategy"),
    ("mock", "stub"),
)


def conflicting(a: str, b: str) -> bool:
    """Order-independent membership test: do ``a`` and ``b`` form a known conflict pair?

    Implements the §8.3 rule 3 veto — a candidate conflicting with the primary may not join
    the supporting set (and two conflicting candidates may not both be selected for a part).
    """
    return (a, b) in CONFLICT_PAIRS or (b, a) in CONFLICT_PAIRS
