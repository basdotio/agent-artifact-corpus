"""Pure functions over an EDGAR companyfacts payload.

Every value is read from a single filing (accession number), so numbers are
"as filed" in that document, never silently replaced by a later restatement.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date


@dataclass(frozen=True)
class Filing:
    accn: str
    form: str
    fy: int | None
    fp: str | None
    filed: str
    period_end: str


@dataclass(frozen=True)
class Fact:
    concept: str
    value: float
    end: str
    start: str | None
    accn: str

    @property
    def duration_days(self) -> int | None:
        if self.start is None:
            return None
        return (date.fromisoformat(self.end) - date.fromisoformat(self.start)).days + 1

    def to_dict(self) -> dict:
        d = asdict(self)
        if self.start is not None:
            d["duration_days"] = self.duration_days
        return d


def _rows(facts: dict, concept: str, unit: str, taxonomy: str = "us-gaap") -> list[dict]:
    return facts.get("facts", {}).get(taxonomy, {}).get(concept, {}).get("units", {}).get(unit, [])


def concept_names(facts: dict, taxonomy: str = "us-gaap") -> list[str]:
    return sorted(facts.get("facts", {}).get(taxonomy, {}))


def list_filings(facts: dict, form: str) -> list[Filing]:
    """Filings of one form type, newest period first.

    A filing's period end is the latest date any of its facts reports, because
    each filing also carries prior-period comparatives with earlier dates.
    """
    by_accn: dict[str, Filing] = {}
    for concept in facts.get("facts", {}).get("us-gaap", {}).values():
        for rows in concept.get("units", {}).values():
            for r in rows:
                if r.get("form") != form:
                    continue
                prev = by_accn.get(r["accn"])
                if prev is None or r["end"] > prev.period_end:
                    by_accn[r["accn"]] = Filing(
                        accn=r["accn"],
                        form=r["form"],
                        fy=r.get("fy"),
                        fp=r.get("fp"),
                        filed=r["filed"],
                        period_end=r["end"],
                    )
    return sorted(by_accn.values(), key=lambda f: (f.period_end, f.filed), reverse=True)


def instant(facts: dict, concept: str, accn: str, end: str, unit: str = "USD") -> Fact | None:
    for r in _rows(facts, concept, unit):
        if r["accn"] == accn and r["end"] == end and "start" not in r:
            return Fact(concept, r["val"], r["end"], None, accn)
    return None


def duration(
    facts: dict, concept: str, accn: str, end: str, start: str | None = None, unit: str = "USD"
) -> Fact | None:
    """A duration fact ending at `end`. With no `start`, the longest one wins
    (the full year in a 10-K, year-to-date in a 10-Q)."""
    best = None
    for r in _rows(facts, concept, unit):
        if r["accn"] != accn or r["end"] != end or "start" not in r:
            continue
        if start is not None and r["start"] != start:
            continue
        if best is None or r["start"] < best["start"]:
            best = r
    return Fact(concept, best["val"], best["end"], best["start"], accn) if best else None


def first_instant(facts: dict, concepts: list[str], accn: str, end: str, unit: str = "USD") -> Fact | None:
    for c in concepts:
        if (f := instant(facts, c, accn, end, unit)) is not None:
            return f
    return None


def first_duration(
    facts: dict, concepts: list[str], accn: str, end: str, start: str | None = None, unit: str = "USD"
) -> Fact | None:
    for c in concepts:
        if (f := duration(facts, c, accn, end, start, unit)) is not None:
            return f
    return None


# Companies tag the same line item differently, and tags changed over the years
# (e.g. ASC 606 replaced SalesRevenueNet in 2018). First match wins.
REVENUE = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
COST_OF_REVENUE = [
    "CostOfGoodsAndServicesSold",
    "CostOfRevenue",
    "CostOfGoodsSold",
    "CostOfServices",
]
TOTAL_EQUITY = [
    "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    "StockholdersEquity",
]
CFO = ["NetCashProvidedByUsedInOperatingActivities"]
CFI = ["NetCashProvidedByUsedInInvestingActivities"]
CFF = ["NetCashProvidedByUsedInFinancingActivities"]
CAPEX = ["PaymentsToAcquirePropertyPlantAndEquipment", "PaymentsToAcquireProductiveAssets"]

INCOME_STATEMENT = {
    "revenue": REVENUE,
    "cost_of_revenue": COST_OF_REVENUE,
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss"],
}
CASH_FLOW = {
    "operating_cash_flow": CFO,
    "investing_cash_flow": CFI,
    "financing_cash_flow": CFF,
    "capex": CAPEX,
}
BALANCE_SHEET = {
    "total_assets": ["Assets"],
    "total_liabilities": ["Liabilities"],
    "total_equity": TOTAL_EQUITY,
    "cash_and_equivalents": ["CashAndCashEquivalentsAtCarryingValue"],
}


def financials(facts: dict, filing: Filing) -> dict:
    """Core line items for one filing. Missing items are reported as null
    rather than guessed."""
    end, accn = filing.period_end, filing.accn
    items: dict[str, dict | None] = {}
    for name, concepts in {**INCOME_STATEMENT, **CASH_FLOW}.items():
        f = first_duration(facts, concepts, accn, end)
        items[name] = f.to_dict() if f else None
    for name, concepts in BALANCE_SHEET.items():
        f = first_instant(facts, concepts, accn, end)
        items[name] = f.to_dict() if f else None
    eps = duration(facts, "EarningsPerShareDiluted", accn, end, unit="USD/shares")
    items["eps_diluted"] = eps.to_dict() if eps else None

    cfo, capex = items["operating_cash_flow"], items["capex"]
    if cfo and capex and cfo["start"] == capex["start"]:
        items["free_cash_flow"] = {
            "value": cfo["value"] - capex["value"],
            "derived": "operating_cash_flow - capex",
            "start": cfo["start"],
            "end": end,
        }
    else:
        items["free_cash_flow"] = None
    return {"filing": asdict(filing), "line_items": items}
