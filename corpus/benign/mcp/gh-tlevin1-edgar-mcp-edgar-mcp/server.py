"""FastMCP server exposing SEC EDGAR financial data and tie-out checks."""

from __future__ import annotations

import difflib
from dataclasses import asdict
from typing import Literal

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations

from . import checks
from . import facts as F
from .sec import Company, SecClient, SecError

INSTRUCTIONS = """\
Financial data for US-listed companies, straight from SEC EDGAR XBRL filings.
Values are "as filed" in a specific filing (accession number) and every number
carries its XBRL concept and period, so cite them. Durations in a 10-Q are
year-to-date unless the period says otherwise. Never compute totals or ratios
yourself when a tool can return them; use check_tieouts to verify a filing's
internal consistency before relying on its numbers. Coverage is US GAAP in USD;
foreign filers reporting under IFRS will mostly come back empty."""

READ_ONLY = ToolAnnotations(read_only_hint=True, open_world_hint=True)
FormType = Literal["10-K", "10-Q"]


def create_server(sec: SecClient | None = None) -> FastMCP:
    sec = sec or SecClient()
    mcp = FastMCP("edgar", instructions=INSTRUCTIONS)

    def resolve(ticker_or_cik: str) -> Company:
        q = ticker_or_cik.strip().upper()
        try:
            companies = sec.companies()
        except SecError as e:
            raise ToolError(str(e)) from e
        for c in companies:
            if c.ticker == q or (q.isdigit() and c.cik == int(q)):
                return c
        raise ToolError(f"No company with ticker or CIK '{ticker_or_cik}'. Try lookup_company.")

    def load(company: Company) -> dict:
        try:
            return sec.company_facts(company.cik)
        except SecError as e:
            raise ToolError(str(e)) from e

    def pick_filing(facts: dict, form: str, accession: str | None) -> F.Filing:
        filings = F.list_filings(facts, form)
        if not filings:
            raise ToolError(
                f"No {form} filings with XBRL data for this company. If it was recently "
                "reorganized, its history may sit under a predecessor CIK; try lookup_company."
            )
        if accession is None:
            return filings[0]
        for f in filings:
            if f.accn == accession:
                return f
        raise ToolError(f"Accession {accession} is not a {form} for this company. Use list_filings.")

    @mcp.tool(annotations=READ_ONLY)
    def lookup_company(query: str, limit: int = 10) -> list[dict]:
        """Find companies by ticker or name. Returns ticker, CIK and SEC name."""
        q = query.strip().upper()
        try:
            companies = sec.companies()
        except SecError as e:
            raise ToolError(str(e)) from e
        exact = [c for c in companies if c.ticker == q]
        partial = [c for c in companies if c not in exact and (q in c.name.upper() or q in c.ticker)]
        return [asdict(c) for c in (exact + partial)[:limit]]

    @mcp.tool(annotations=READ_ONLY)
    def list_filings(ticker: str, form: FormType = "10-K", limit: int = 8) -> dict:
        """List a company's 10-K or 10-Q filings that carry XBRL data, newest first.
        Use an accession number from here to target a specific filing."""
        company = resolve(ticker)
        filings = F.list_filings(load(company), form)
        return {"company": asdict(company), "filings": [asdict(f) for f in filings[:limit]]}

    @mcp.tool(annotations=READ_ONLY)
    def get_financials(ticker: str, form: FormType = "10-K", periods: int = 3) -> dict:
        """Core income statement, balance sheet and cash flow line items for the most
        recent filings. Each value includes its XBRL concept, period and accession
        number. Missing items are null, not estimated."""
        company = resolve(ticker)
        facts = load(company)
        filings = F.list_filings(facts, form)[:periods]
        if not filings:
            raise ToolError(f"No {form} filings with XBRL data for {company.ticker}.")
        return {"company": asdict(company), "periods": [F.financials(facts, f) for f in filings]}

    @mcp.tool(annotations=READ_ONLY)
    def get_concept(
        ticker: str,
        concept: str,
        form: FormType | None = None,
        taxonomy: Literal["us-gaap", "dei"] = "us-gaap",
        limit: int = 20,
    ) -> dict:
        """Raw reported values for any XBRL concept (e.g. 'ResearchAndDevelopmentExpense'),
        newest first. Use when get_financials doesn't cover the line item you need.
        Unknown concepts return close matches from this company's filings."""
        company = resolve(ticker)
        facts = load(company)
        node = facts.get("facts", {}).get(taxonomy, {}).get(concept)
        if node is None:
            names = F.concept_names(facts, taxonomy)
            close = difflib.get_close_matches(concept, names, n=8, cutoff=0.5)
            if not close:
                needle = concept.lower()
                close = [n for n in names if needle in n.lower()][:8]
            raise ToolError(f"{company.ticker} has never reported {taxonomy}:{concept}. Close matches: {close}")
        values = []
        seen = set()
        for unit, rows in node.get("units", {}).items():
            for r in rows:
                if form and r.get("form") != form:
                    continue
                key = (unit, r.get("start"), r["end"], r["accn"])
                if key in seen:
                    continue
                seen.add(key)
                values.append({"unit": unit, **{k: r[k] for k in ("start", "end", "val", "accn", "form", "fy", "fp", "filed") if k in r}})
        values.sort(key=lambda v: (v["end"], v["filed"]), reverse=True)
        return {
            "company": asdict(company),
            "concept": concept,
            "label": node.get("label"),
            "description": node.get("description"),
            "values": values[:limit],
        }

    @mcp.tool(annotations=READ_ONLY)
    def check_tieouts(
        ticker: str,
        form: FormType = "10-K",
        accession: str | None = None,
        rel_tolerance: float = checks.DEFAULT_REL_TOL,
    ) -> dict:
        """Verify a filing is internally consistent, computed in code: the balance sheet
        balances, revenue minus cost of revenue equals gross profit, the three cash
        flow sections sum to the change in cash, and cash rolls forward from the
        beginning balance. Defaults to the latest filing of the given form. Each
        check shows its formula, inputs and difference; checks whose inputs are
        not tagged are reported as skipped."""
        company = resolve(ticker)
        facts = load(company)
        filing = pick_filing(facts, form, accession)
        return {"company": asdict(company), **checks.run_checks(facts, filing, rel_tolerance)}

    return mcp


mcp = create_server()
