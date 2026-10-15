"""Deterministic eligibility checks: age range and sex only.

The API reports ``sex``, ``minimumAge`` and ``maximumAge`` as structured
fields, so those can be checked exactly. Everything else in a study's
criteria is free text written for clinicians. This module never guesses at
the free text; the tool returns it unchanged for a human to review. See
docs/adr/0002-eligibility-deterministic-fields-only.md.
"""

from __future__ import annotations

import re
from typing import Any

from .models import CriterionCheck, EligibilityResult, parse_eligibility, parse_summary

_AGE_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(years?|months?|weeks?|days?|hours?)\s*$", re.IGNORECASE
)

_UNIT_TO_YEARS = {
    "year": 1.0,
    "month": 1.0 / 12.0,
    "week": 1.0 / 52.0,
    "day": 1.0 / 365.0,
    "hour": 1.0 / (365.0 * 24.0),
}


def parse_age_to_years(raw: str | None) -> float | None:
    """Parse an API age string such as '18 Years' or '6 Months' into years.

    Returns None when the value is missing or 'N/A', meaning the study does
    not state that bound.
    """
    if raw is None:
        return None
    match = _AGE_PATTERN.match(raw)
    if match is None:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower().rstrip("s")
    return value * _UNIT_TO_YEARS[unit]


def normalize_sex(raw: str | None) -> str | None:
    """Normalize a sex value to 'male', 'female', or None if not recognized."""
    if raw is None:
        return None
    value = raw.strip().lower()
    if value in {"male", "m", "man"}:
        return "male"
    if value in {"female", "f", "woman"}:
        return "female"
    return None


def _check_age(
    patient_age: float | None,
    minimum_raw: str | None,
    maximum_raw: str | None,
) -> CriterionCheck:
    minimum = parse_age_to_years(minimum_raw)
    maximum = parse_age_to_years(maximum_raw)
    if patient_age is None:
        return CriterionCheck(
            criterion="age",
            result="unknown",
            detail="No patient age was provided, so the age range cannot be checked.",
        )
    bounds = []
    if minimum_raw:
        bounds.append(f"minimum {minimum_raw}")
    if maximum_raw:
        bounds.append(f"maximum {maximum_raw}")
    stated = ", ".join(bounds) if bounds else "no stated age range"
    if minimum is not None and patient_age < minimum:
        return CriterionCheck(
            criterion="age",
            result="fail",
            detail=(
                f"Patient age {patient_age:g} years is below the study minimum of {minimum_raw}."
            ),
        )
    if maximum is not None and patient_age > maximum:
        return CriterionCheck(
            criterion="age",
            result="fail",
            detail=(
                f"Patient age {patient_age:g} years is above the study maximum of {maximum_raw}."
            ),
        )
    if minimum is None and maximum is None and (minimum_raw or maximum_raw):
        return CriterionCheck(
            criterion="age",
            result="unknown",
            detail=f"The study states an age range ({stated}) in a form that cannot be parsed.",
        )
    return CriterionCheck(
        criterion="age",
        result="pass",
        detail=f"Patient age {patient_age:g} years is within the stated range ({stated}).",
    )


def _check_sex(patient_sex: str | None, study_sex: str | None) -> CriterionCheck:
    study_value = (study_sex or "").strip().upper()
    if study_value in ("", "ALL"):
        return CriterionCheck(
            criterion="sex",
            result="pass",
            detail="The study enrolls all sexes.",
        )
    patient = normalize_sex(patient_sex)
    if patient is None:
        return CriterionCheck(
            criterion="sex",
            result="unknown",
            detail=(
                f"The study enrolls {study_value.lower()} participants only, and no "
                "usable patient sex was provided."
            ),
        )
    if patient.upper() == study_value:
        return CriterionCheck(
            criterion="sex",
            result="pass",
            detail=f"The study enrolls {study_value.lower()} participants; patient sex matches.",
        )
    return CriterionCheck(
        criterion="sex",
        result="fail",
        detail=(
            f"The study enrolls {study_value.lower()} participants only; patient sex is {patient}."
        ),
    )


def evaluate_eligibility(
    study: dict[str, Any],
    *,
    patient_age: float | None,
    patient_sex: str | None,
) -> EligibilityResult:
    """Evaluate age and sex for one raw study dict. Nothing else is judged."""
    eligibility = parse_eligibility(study)
    checks = [
        _check_age(patient_age, eligibility.minimum_age, eligibility.maximum_age),
        _check_sex(patient_sex, eligibility.sex),
    ]
    results = {check.result for check in checks}
    if "fail" in results:
        verdict = "does_not_meet"
    elif "unknown" in results:
        verdict = "cannot_determine"
    else:
        verdict = "meets"
    return EligibilityResult(
        nct_id=parse_summary(study).nct_id,
        verdict=verdict,
        checks=checks,
        criteria_text=eligibility.criteria_text,
    )
