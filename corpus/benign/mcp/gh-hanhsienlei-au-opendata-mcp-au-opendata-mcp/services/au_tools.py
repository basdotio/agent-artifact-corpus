import datetime
import re

from pydantic import BaseModel

# The ATO's published modulus-89 weighting.
ABN_WEIGHTS: tuple[int, ...] = (10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19)
_SEPARATORS = re.compile(r"[\s\-]")


class AbnResult(BaseModel):
    valid: bool
    normalised: str | None
    reason: str | None


class FinancialYearResult(BaseModel):
    label: str
    start_date: str
    end_date: str


def validate_abn(abn: str) -> AbnResult:
    """Check an ABN against the ATO's modulus-89 checksum.

    Deterministic by design: a model asked to 'check this ABN' would otherwise guess.
    """
    stripped = _SEPARATORS.sub("", abn or "")

    if len(stripped) != 11:
        return AbnResult(
            valid=False,
            normalised=None,
            reason=f"an ABN must be 11 digits; this has {len(stripped)}",
        )
    if not stripped.isdigit():
        return AbnResult(valid=False, normalised=None, reason="an ABN must contain only digits")

    digits = [int(c) for c in stripped]
    digits[0] -= 1  # the ATO's first step
    total = sum(d * w for d, w in zip(digits, ABN_WEIGHTS, strict=True))

    if total % 89 != 0:
        return AbnResult(valid=False, normalised=None, reason="the ABN failed its checksum")

    normalised = f"{stripped[:2]} {stripped[2:5]} {stripped[5:8]} {stripped[8:]}"
    return AbnResult(valid=True, normalised=normalised, reason=None)


def au_financial_year(date: str) -> FinancialYearResult:
    """Map a date to the Australian financial year, which runs 1 July to 30 June."""
    try:
        parsed = datetime.date.fromisoformat(date.strip()[:10])
    except (ValueError, AttributeError) as exc:
        raise ValueError(f"{date!r} could not be read as a date; use YYYY-MM-DD") from exc

    start_year = parsed.year if parsed.month >= 7 else parsed.year - 1
    end_year = start_year + 1
    return FinancialYearResult(
        label=f"FY{start_year}–{end_year % 100:02d}",
        start_date=f"{start_year}-07-01",
        end_date=f"{end_year}-06-30",
    )
