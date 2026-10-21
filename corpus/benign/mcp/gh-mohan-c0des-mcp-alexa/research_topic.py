"""research_topic: plan -> multi-angle web search -> extract numbers -> analyze_data -> PDFs.

Flow (every research goes through analyze_data, so the analysis rules live in one place):
  1. The LLM decides how many searches are needed (3 to 8) and what each should ask.
  2. Each search runs on DuckDuckGo (news for time-sensitive angles, web otherwise).
  3. All findings are saved as a research dossier (.md + PDF).
  4. The LLM pulls the hard numbers out into a table (entity x metric). It only copies
     numbers that were stated; pandas does all the math inside analyze_data.
  5. analyze_data analyzes the table (or the dossier text) for the user's actual question.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Any

import pandas as pd
from ddgs import DDGS

from analyze_data import MAX_TEXT_CHARS, REPORTS, _gemini_json, analyze_data
from pdf_utils import md_to_pdf

MIN_QUERIES, MAX_QUERIES = 3, 8
RESULTS_PER_QUERY = 6
# Where the user is. In a real product this comes from the device/account; for the demo set it here.
USER_LOCATION = os.environ.get("USER_LOCATION", "India")
SEARCH_REGION = os.environ.get("SEARCH_REGION", "in-en")  # DuckDuckGo region code, e.g. "us-en", "uk-en"

PLAN_PROMPT = """You are a research planner. Today is {today}.
The user is located in {location}. Prefer that country's markets, sources, currency and rules
unless the question names another place.
The user asked: "{question}"

Plan web searches that will give a COMPLETE overview. Return ONLY JSON:
{"goal": "one sentence: what the final analysis must answer",
 "queries": [{"query": "...", "purpose": "...", "source": "news|web", "recency": "d|w|m|y|any"}]}

Rules:
- Choose between 3 and 8 queries: as many as a complete answer needs, no more.
- Each query is a specific search phrase (3 to 8 words), not a sentence, and adds something new.
- Include at least 2 queries that find hard NUMBERS (prices, percentage changes, ratios, volumes,
  rates) and at least 1 about risks or downsides.
- Use source "news" with recency "d" or "w" for anything time-sensitive (today, latest, this week).
- Put the date or month in time-sensitive queries.
- If the user wants to choose or compare options (stocks, products, places), name 4 to 6 well-known
  candidates yourself inside the number-finding queries, so the results hold comparable numbers."""

EXTRACT_PROMPT = """From the SEARCH NOTES below, extract the hard numbers that help answer:
"{question}"

Return ONLY JSON:
{"primary_metric": "<one metric name that best ranks or compares the entities>",
 "rows": [{"entity": "...", "metric": "...", "value": 123.4, "as_of": "...", "source_url": "..."}]}

Rules:
- Only numbers explicitly stated in the notes. Never estimate or calculate. If unsure, leave it out.
- Entities are the things being compared (stocks, indices, sectors, countries, products...).
  Spell each entity the same way every time.
- Metric names are lowercase snake_case with the unit inside, reused identically for every entity
  (for example price_inr, change_1d_pct, pe_ratio, volume_m, yield_pct).
- value must be a plain number: no symbols, no commas."""


# ----------------------------- planning & searching ---------------------------
def _plan(question: str) -> tuple[str, list[dict]]:
    today = datetime.now().strftime("%A, %d %B %Y")
    prompt = (PLAN_PROMPT.replace("{today}", today).replace("{location}", USER_LOCATION)
              .replace("{question}", question))
    plan = _gemini_json(prompt)
    queries = [q for q in plan.get("queries", []) if isinstance(q, dict) and q.get("query")]
    queries = queries[:MAX_QUERIES]
    if len(queries) < MIN_QUERIES:  # planner under-delivered: fall back to the raw question
        queries.append({"query": question, "purpose": "direct search", "source": "web", "recency": "any"})
    return plan.get("goal") or question, queries


def _run_search(ddgs: Any, q: dict) -> tuple[list[dict], str]:
    """Run one planned search. Returns (results, last_error)."""
    query, kind, rec = q["query"], q.get("source", "web"), q.get("recency", "any")
    limit = rec if rec in ("d", "w", "m", "y") else None
    attempts = [("news", None if limit == "y" else limit), ("text", limit)] if kind == "news" else [("text", limit)]
    last_err = ""
    for mode, tl in attempts:
        for _ in range(2):  # one retry (DuckDuckGo rate-limits now and then)
            try:
                fn = ddgs.news if mode == "news" else ddgs.text
                raw = fn(query, region=SEARCH_REGION, timelimit=tl, max_results=RESULTS_PER_QUERY)
                rows = [
                    {
                        "title": (r.get("title") or "").strip(),
                        "snippet": (r.get("body") or "").strip(),
                        "url": r.get("url") or r.get("href") or "",
                        "date": r.get("date") or "",
                        "source": r.get("source") or "",
                    }
                    for r in (raw or [])
                ]
                if rows:
                    return rows, ""
                break  # empty result: try the next mode
            except Exception as e:  # noqa: BLE001
                last_err = f"{type(e).__name__}: {e}"
                time.sleep(1.5)
    return [], last_err


def _dossier_markdown(question: str, goal: str, searches: list[dict]) -> str:
    lines = [
        f"# Research dossier: {question}",
        "",
        f"Generated {datetime.now():%d %b %Y, %H:%M}. Goal: {goal}",
        "",
        "## Search plan",
    ]
    for i, s in enumerate(searches, 1):
        q = s["plan"]
        lines.append(f"- {i}. [{q.get('source', 'web')}/{q.get('recency', 'any')}] {q['query']} - {q.get('purpose', '')}")
    lines += ["", "## Findings"]
    for i, s in enumerate(searches, 1):
        lines += ["", f"### {i}. {s['plan']['query']}"]
        if not s["results"]:
            lines.append(f"- No results ({s['error'] or 'empty'})")
        for r in s["results"]:
            meta = ", ".join(x for x in (r["source"], r["date"]) if x)
            lines.append(f"- {r['title']} ({meta}): {r['snippet']} [{r['url']}]")
    return "\n".join(lines)


# ----------------------------- numbers -> table -------------------------------
def _extract_table(question: str, notes: str) -> tuple[pd.DataFrame | None, str, int]:
    """Pull stated numbers into an entity x metric table. Returns (table, primary_metric, n_numbers)."""
    try:
        prompt = EXTRACT_PROMPT.replace("{question}", question) + "\n\nSEARCH NOTES:\n" + notes[:MAX_TEXT_CHARS]
        data = _gemini_json(prompt)
        df = pd.DataFrame(data.get("rows") or [])
        if df.empty or not {"entity", "metric", "value"} <= set(df.columns):
            return None, "", 0
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna(subset=["entity", "metric", "value"])
        wide = df.pivot_table(index="entity", columns="metric", values="value", aggfunc="first")
        if wide.shape[0] < 3:  # too few entities for meaningful table statistics
            return None, "", len(df)
        primary = data.get("primary_metric") or ""
        return wide.reset_index(), (primary if primary in wide.columns else ""), len(df)
    except Exception:  # noqa: BLE001  extraction is a bonus; the text analysis still works
        return None, "", 0


# ----------------------------- the MCP tool ----------------------------------
def research_topic(question: str) -> dict:
    """Research anything that needs CURRENT or outside information (news, markets, prices,
    comparisons, 'what is happening with...'). Pass the user's full request as `question`.
    The tool decides how many searches are needed, searches the web from several angles
    (including searches for hard numbers and for risks), saves a research PDF, then runs
    analyze_data on everything it found. It already includes the analysis, so do NOT call
    analyze_data again afterwards. Returns spoken_summary (4-5 sentences to read aloud),
    report_pdf_path (the analysis PDF), dossier_pdf_path (the raw research PDF) and the list
    of searches that were run."""
    goal, queries = _plan(question)

    ddgs = DDGS()
    searches, seen = [], set()
    for q in queries:
        results, err = _run_search(ddgs, q)
        fresh = []
        for r in results:  # skip pages we already collected under another query
            if r["url"] and r["url"] in seen:
                continue
            seen.add(r["url"])
            fresh.append(r)
        searches.append({"plan": q, "results": fresh, "error": err})
        time.sleep(0.8)  # be polite to the search engine

    total = sum(len(s["results"]) for s in searches)
    if total == 0:
        errors = "; ".join(s["error"] for s in searches if s["error"]) or "no results"
        raise RuntimeError(f"Web search returned nothing ({errors}). Check the internet connection and try again.")

    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    dossier = _dossier_markdown(question, goal, searches)
    dossier_md = REPORTS / f"research_{stamp}.md"
    dossier_md.write_text(dossier, encoding="utf-8")
    dossier_pdf = md_to_pdf(dossier, dossier_md.with_suffix(".pdf"), title=f"Research: {question}")

    table, primary, n_numbers = _extract_table(question, dossier)
    ask = f"{question}\n\nResearch goal: {goal}"
    if table is not None:
        csv_path = REPORTS / f"research_{stamp}_numbers.csv"
        table.to_csv(csv_path, index=False)
        result = analyze_data(str(csv_path), ask, focus_column=primary, context=dossier)
    else:
        result = analyze_data(str(dossier_md), ask)

    return {
        "spoken_summary": result["spoken_summary"],
        "headline": result["headline"],
        "confidence": result["confidence"],
        "report_pdf_path": result["report_pdf_path"],
        "dossier_pdf_path": str(dossier_pdf),
        "searches_run": [{"query": s["plan"]["query"], "results": len(s["results"])} for s in searches],
        "numbers_extracted": n_numbers,
        "report_markdown": result["report_markdown"],
    }