"""Offline integrity findings for a candidate design (advisory, never raising).

The checks are deterministic and model-free: they run over the assembled
:class:`~src.schemas.design.DesignResult` and re-expose what the pipeline's own stages would
flag — an empty design, a dominant pattern that is not applied, a documented conflict pair
(:mod:`src.conflicts`), duplicated application ids, applications without participants or a
language binding. Findings are advisory text: callers surface them next to a scoring result,
they never fail a request.
"""

from __future__ import annotations

from src.conflicts import conflicting
from src.schemas.design import DesignResult


def design_integrity_findings(design: DesignResult) -> list[str]:
    """Deterministic integrity findings for ``design``; empty list when nothing is flagged."""
    findings: list[str] = []
    if not design.applications:
        findings.append("the design carries no pattern application")
        return findings

    applied = [application.pattern for application in design.applications]
    if design.overview.primary_pattern not in applied:
        findings.append(
            f"dominant pattern {design.overview.primary_pattern!r} is not applied by any application"
        )

    seen_ids: set[str] = set()
    for application in design.applications:
        if application.id in seen_ids:
            findings.append(f"duplicated application id {application.id!r}")
        seen_ids.add(application.id)
        if not application.participants:
            findings.append(f"application {application.id!r} names no participant")
        if application.language_binding is None:
            findings.append(f"application {application.id!r} has no language binding")

    for index, pattern in enumerate(applied):
        for other in applied[index + 1 :]:
            if pattern != other and conflicting(pattern, other):
                findings.append(
                    f"conflicting pattern pair selected: {pattern!r} vs {other!r} (§8.3 rule 3)"
                )
    return findings
