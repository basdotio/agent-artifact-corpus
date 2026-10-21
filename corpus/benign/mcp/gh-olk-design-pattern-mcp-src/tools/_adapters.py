"""Adapters of the tool boundary (DP-7): dict ⇄ pydantic forms and advisory findings.

Caller-supplied JSON (analysis payloads, design drafts) crosses this module. Conversions
validate strictly and raise :class:`~src.errors.MalformedDesignOverviewError` for a broken
design payload — the tool handlers map that onto their ``ERR_002`` response. No silent
placeholder synthesis happens at the adapter boundary.
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationError

from src.design_validation import design_integrity_findings as _design_integrity_findings
from src.errors import MalformedDesignOverviewError
from src.schemas.design import DesignResult
from src.schemas.selection import AnalysisResult


def analysis_to_pydantic(payload: AnalysisResult | dict[str, Any]) -> AnalysisResult:
    """A prior ``analyze_design`` payload as a strict :class:`AnalysisResult`."""
    if isinstance(payload, AnalysisResult):
        return payload
    return AnalysisResult.model_validate(payload)


def design_from_dict(payload: dict[str, Any]) -> DesignResult:
    """A caller-supplied design dict as a strict :class:`DesignResult`.

    Raises:
        MalformedDesignOverviewError: when the payload carries no ``overview`` object or does
            not validate against the ``DesignResult`` contract.
    """
    overview = payload.get("overview")
    if not isinstance(overview, dict):
        raise MalformedDesignOverviewError(
            "the design payload carries no 'overview' object (docs/result-schema.json)"
        )
    try:
        return DesignResult.model_validate(payload)
    except ValidationError as exc:
        raise MalformedDesignOverviewError(f"the design payload does not validate: {exc}") from exc


def design_to_pydantic(design: DesignResult | dict[str, Any]) -> DesignResult:
    """A design in either representation (pipeline model or caller dict) as :class:`DesignResult`."""
    if isinstance(design, DesignResult):
        return design
    return design_from_dict(design)


def design_integrity_findings(design: DesignResult) -> list[str]:
    """Advisory offline integrity findings for a design (:mod:`src.design_validation`)."""
    return _design_integrity_findings(design)
