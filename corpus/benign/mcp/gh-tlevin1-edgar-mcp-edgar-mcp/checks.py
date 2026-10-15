"""Deterministic tie-out checks on a single filing.

Each check states its formula, the exact facts it used and the difference. A
check whose inputs are not all tagged in the filing is "skipped", never passed
by assumption.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, timedelta

from . import facts as F

DEFAULT_REL_TOL = 0.0005  # 0.05%: absorbs rounding to millions, catches real breaks
ABS_TOL = 1_000_000.0  # $1M floor so tiny line items aren't failed on rounding

RESTRICTED_CASH_BALANCE = [
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations",
]

# (change-in-cash concept, candidate balance concepts, whether the change includes FX)
CASH_FAMILIES = [
    (
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseIncludingExchangeRateEffect",
        RESTRICTED_CASH_BALANCE,
        True,
    ),
    (
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsPeriodIncreaseDecreaseExcludingExchangeRateEffect",
        RESTRICTED_CASH_BALANCE,
        False,
    ),
    (
        "CashAndCashEquivalentsPeriodIncreaseDecrease",
        ["CashAndCashEquivalentsAtCarryingValue"],
        True,
    ),
]
# Temporary ("mezzanine") equity sits between liabilities and equity. Filers tag
# either a total or its parts, so: the total if present; otherwise parent plus
# redeemable NCI, where RNCI is its own total or the sum of its parts. Measured
# on every 10-K/10-Q in 2026Q1 (see edgar_bulk/): when parent and RNCI differ
# they are separate lines (summing ties out 12/12); when exactly equal it is one
# line tagged twice (e.g. KKR), counted once. edgar_bulk uses these same names.
TEMP_EQUITY_TOTAL = "TemporaryEquityCarryingAmountIncludingPortionAttributableToNoncontrollingInterests"
TEMP_EQUITY_PARENT = "TemporaryEquityCarryingAmountAttributableToParent"
RNCI_TOTAL = "RedeemableNoncontrollingInterestEquityCarryingAmount"
RNCI_PARTS = [
    "RedeemableNoncontrollingInterestEquityCommonCarryingAmount",
    "RedeemableNoncontrollingInterestEquityPreferredCarryingAmount",
    "RedeemableNoncontrollingInterestEquityOtherCarryingAmount",
]

FX_EFFECT = [
    "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
    "EffectOfExchangeRateOnCashCashEquivalentsRestrictedCashAndRestrictedCashEquivalentsIncludingDisposalGroupAndDiscontinuedOperations",
    "EffectOfExchangeRateOnCashAndCashEquivalents",
]


@dataclass
class CheckResult:
    name: str
    formula: str
    status: str  # "pass" | "fail" | "skipped"
    reported: float | None = None
    computed: float | None = None
    difference: float | None = None
    tolerance: float | None = None
    inputs: list[dict] = field(default_factory=list)
    note: str | None = None


def _compare(name, formula, reported: F.Fact, parts: list[tuple[int, F.Fact]], rel_tol, note=None):
    computed = sum(sign * f.value for sign, f in parts)
    diff = computed - reported.value
    tol = max(ABS_TOL, rel_tol * max(abs(computed), abs(reported.value)))
    return CheckResult(
        name=name,
        formula=formula,
        status="pass" if abs(diff) <= tol else "fail",
        reported=reported.value,
        computed=computed,
        difference=diff,
        tolerance=tol,
        inputs=[reported.to_dict()] + [f.to_dict() for _, f in parts],
        note=note,
    )


def _skip(name, formula, missing: list[str]):
    return CheckResult(name, formula, "skipped", note="Not tagged in this filing: " + ", ".join(missing))


def temporary_equity(facts, acc: str, end: str) -> tuple[list[F.Fact], str | None]:
    """The facts that make up temporary equity, and a note when a rule applied."""
    total = F.instant(facts, TEMP_EQUITY_TOTAL, acc, end)
    if total:
        return [total], None
    parent = F.instant(facts, TEMP_EQUITY_PARENT, acc, end)
    rnci_total = F.instant(facts, RNCI_TOTAL, acc, end)
    rnci = [rnci_total] if rnci_total else [f for t in RNCI_PARTS if (f := F.instant(facts, t, acc, end))]
    if parent and rnci and parent.value == sum(f.value for f in rnci):
        return [parent], "Parent and redeemable NCI temporary equity are equal: one line tagged twice, counted once."
    return [f for f in [parent, *rnci] if f], None


def balance_sheet(facts, filing: F.Filing, rel_tol) -> CheckResult:
    name, formula = "balance_sheet_balances", "Assets = LiabilitiesAndStockholdersEquity"
    a = F.instant(facts, "Assets", filing.accn, filing.period_end)
    le = F.instant(facts, "LiabilitiesAndStockholdersEquity", filing.accn, filing.period_end)
    if not (a and le):
        return _skip(name, formula, [n for n, v in [("Assets", a), ("LiabilitiesAndStockholdersEquity", le)] if not v])
    return _compare(name, formula, le, [(1, a)], rel_tol)


def liabilities_plus_equity(facts, filing: F.Filing, rel_tol) -> CheckResult:
    name = "liabilities_plus_equity"
    formula = "Liabilities + total equity (+ temporary equity) = LiabilitiesAndStockholdersEquity"
    acc, end = filing.accn, filing.period_end
    le = F.instant(facts, "LiabilitiesAndStockholdersEquity", acc, end)
    liab = F.instant(facts, "Liabilities", acc, end)
    eq = F.first_instant(facts, F.TOTAL_EQUITY, acc, end)
    missing = [n for n, v in [("LiabilitiesAndStockholdersEquity", le), ("Liabilities", liab), ("StockholdersEquity", eq)] if not v]
    if missing:
        note = None
        if le and eq and not liab:
            note = "Many filers never tag a Liabilities subtotal; this is a tagging gap, not a break."
        r = _skip(name, formula, missing)
        r.note = f"{r.note}. {note}" if note else r.note
        return r
    parts = [(1, liab), (1, eq)]
    notes = []
    if eq.concept == "StockholdersEquity":
        nci = F.instant(facts, "MinorityInterest", acc, end)
        if nci:
            parts.append((1, nci))
            notes.append("Added MinorityInterest because only parent equity was tagged.")
    temp, temp_note = temporary_equity(facts, acc, end)
    if temp:
        parts.extend((1, f) for f in temp)
        notes.append(f"Added temporary equity ({', '.join(f.concept for f in temp)}).")
    if temp_note:
        notes.append(temp_note)
    return _compare(name, formula, le, parts, rel_tol, " ".join(notes) or None)


def gross_profit(facts, filing: F.Filing, rel_tol) -> CheckResult:
    name, formula = "gross_profit", "Revenue - CostOfRevenue = GrossProfit"
    acc, end = filing.accn, filing.period_end
    gp = F.duration(facts, "GrossProfit", acc, end)
    if not gp:
        return _skip(name, formula, ["GrossProfit"])
    # Same period for every term: a 10-Q tags both the quarter and year-to-date.
    rev = F.first_duration(facts, F.REVENUE, acc, end, gp.start)
    cogs = F.first_duration(facts, F.COST_OF_REVENUE, acc, end, gp.start)
    if not (rev and cogs):
        return _skip(name, formula, [n for n, v in [("Revenue", rev), ("CostOfRevenue", cogs)] if not v])
    return _compare(name, formula, gp, [(1, rev), (-1, cogs)], rel_tol)


def _cash_family(facts, filing: F.Filing):
    for change_concept, balance_concepts, includes_fx in CASH_FAMILIES:
        ch = F.duration(facts, change_concept, filing.accn, filing.period_end)
        if ch:
            return ch, balance_concepts, includes_fx
    return None, None, None


def cash_flow_sum(facts, filing: F.Filing, rel_tol) -> CheckResult:
    name = "cash_flow_sections_sum"
    formula = "CFO + CFI + CFF (+ FX effect) = change in cash"
    acc, end = filing.accn, filing.period_end
    ch, _, includes_fx = _cash_family(facts, filing)
    if not ch:
        return _skip(name, formula, ["change in cash"])
    sections = [F.first_duration(facts, c, acc, end, ch.start) for c in (F.CFO, F.CFI, F.CFF)]
    if not all(sections):
        labels = ["CFO", "CFI", "CFF"]
        return _skip(name, formula, [l for l, s in zip(labels, sections) if not s])
    parts = [(1, s) for s in sections]
    note = None
    if includes_fx:
        fx = F.first_duration(facts, FX_EFFECT, acc, end, ch.start)
        if fx:
            parts.append((1, fx))
        else:
            note = "No FX effect tagged; treated as zero."
    return _compare(name, formula, ch, parts, rel_tol, note)


def cash_roll_forward(facts, filing: F.Filing, rel_tol) -> CheckResult:
    name = "cash_roll_forward"
    formula = "ending cash - beginning cash = change in cash"
    ch, balance_concepts, includes_fx = _cash_family(facts, filing)
    if not ch:
        return _skip(name, formula, ["change in cash"])
    if not includes_fx:
        return CheckResult(name, formula, "skipped", note="Change in cash is tagged excluding FX, so balances will not roll forward on it.")
    begin_date = (date.fromisoformat(ch.start) - timedelta(days=1)).isoformat()
    # Both balances must come from the same concept, or the difference is meaningless.
    for concept in balance_concepts:
        ending = F.instant(facts, concept, filing.accn, filing.period_end)
        beginning = F.instant(facts, concept, filing.accn, begin_date)
        if ending and beginning:
            break
    else:
        return _skip(name, formula, [f"cash balance at both {begin_date} and {filing.period_end}"])
    return _compare(name, formula, ch, [(1, ending), (-1, beginning)], rel_tol)


ALL_CHECKS = [balance_sheet, liabilities_plus_equity, gross_profit, cash_flow_sum, cash_roll_forward]


def run_checks(facts: dict, filing: F.Filing, rel_tol: float = DEFAULT_REL_TOL) -> dict:
    results = [check(facts, filing, rel_tol) for check in ALL_CHECKS]
    counts = {s: sum(r.status == s for r in results) for s in ("pass", "fail", "skipped")}
    return {
        "filing": asdict(filing),
        "summary": counts,
        "checks": [asdict(r) for r in results],
    }
