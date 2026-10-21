"""analyze_data: evidence-first data analysis for the laptop MCP server.

Design rule: CODE computes the numbers (pandas), the LLM only INTERPRETS them.
That is what keeps the analysis accurate instead of "vibes".

Accepted sources:
  - a file inside the workspace folder (.csv .xlsx .xls .json .txt .md)
  - raw data pasted inline (CSV text)
  - plain text, e.g. output of ask_about_screen or research_topic
"""
from __future__ import annotations

import io
import json
import os
import re
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from pdf_utils import md_to_pdf

# --- Config ------------------------------------------------------------------
WORKSPACE = Path(os.environ.get("MCP_WORKSPACE", Path.home() / "AlexaWorkspace")).resolve()
REPORTS = WORKSPACE / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
MAX_EVIDENCE_CHARS = 14000
MAX_TEXT_CHARS = 30000
TABLE_EXT = {".csv", ".xlsx", ".xls", ".json"}
TEXT_EXT = {".txt", ".md"}
# -----------------------------------------------------------------------------

_NUM_CLEAN = re.compile(r"[,\s₹$€£%]")
_TARGET_HINT = re.compile(
    r"revenue|sales|amount|total|profit|income|cost|price|value|close|spend|salary|score", re.I
)

INSTRUCTIONS = """You are a senior data analyst. Analyze the EVIDENCE and answer the USER REQUEST.

Rules:
- Use ONLY numbers that appear in the EVIDENCE or SUPPORTING CONTEXT. Never invent or recompute
  figures. If something is not there, say it cannot be determined.
- Separate facts (observed) from interpretation (hypotheses). Label hypotheses clearly.
  Correlation is not causation.
- A trend is real only if its trend_strength is "moderate" or "strong" AND it has at least 6
  periods. If it is "weak/noisy", call it noise or flat even when the first-to-last change looks
  large. Periods listed under partial_periods_excluded were left out on purpose.
- Confidence may be "high" only if there are at least 30 rows, the conclusions rest on strong
  signals, and the data is not just web snippets. Web search notes or text read off a screen are
  "medium" at best.
- Flag data-quality issues (missing values, duplicates, outliers, small samples).
- Be specific: every finding cites the number that supports it.
- Finance, health and legal questions: compare the options by evidence and relative risk. Do not
  tell the user to buy, sell, or take a treatment. Include one short sentence saying this is
  information, not professional advice.

Return ONLY a JSON object with these keys:
{
  "spoken_summary": "4 to 5 short sentences, plain speech, no markdown or symbols, with the most important numbers",
  "headline": "one-line takeaway",
  "key_findings": [{"finding": "...", "evidence": "..."}],
  "patterns_and_trends": [{"pattern": "...", "evidence": "..."}],
  "anomalies": [{"anomaly": "...", "evidence": "..."}],
  "likely_drivers": [{"hypothesis": "...", "support": "...", "caveat": "..."}],
  "risks_and_data_quality": ["..."],
  "recommendations": [{"action": "...", "why": "...", "priority": "high|medium|low"}],
  "confidence": "high|medium|low",
  "confidence_reason": "...",
  "follow_up_questions": ["max 3"]
}
Use empty lists where a section does not apply."""


# ----------------------------- file access -----------------------------------
def _safe_path(p: str) -> Path:
    """Resolve a path and refuse anything outside the workspace folder."""
    path = Path(p).expanduser()
    if not path.is_absolute():
        path = WORKSPACE / path
    path = path.resolve()
    if not path.is_relative_to(WORKSPACE):
        raise ValueError(f"Access denied: files must be inside {WORKSPACE}")
    return path


def _list_workspace() -> list[str]:
    return sorted(p.name for p in WORKSPACE.iterdir() if p.is_file())[:20]


def _is_text_like(s: pd.Series) -> bool:
    return pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s)


def _resolve_source(source: str):
    """Return (dataframe | None, text | None, origin_label)."""
    s = source.strip()
    if not s:
        raise ValueError("source is empty")

    single_line = "\n" not in s and len(s) < 300
    if single_line and Path(s).suffix.lower() in TABLE_EXT | TEXT_EXT:
        path = _safe_path(s)
        if not path.exists():
            raise FileNotFoundError(f"'{s}' not found. Files in workspace: {_list_workspace()}")
        ext = path.suffix.lower()
        if ext == ".csv":
            return pd.read_csv(path), None, path.name
        if ext in (".xlsx", ".xls"):
            return pd.read_excel(path), None, path.name  # needs openpyxl
        if ext == ".json":
            return pd.read_json(path), None, path.name
        return None, path.read_text(encoding="utf-8", errors="ignore")[:MAX_TEXT_CHARS], path.name

    # Inline: try to read it as a table, otherwise treat it as plain text.
    try:
        df = pd.read_csv(io.StringIO(s), sep=None, engine="python")
        if df.shape[0] >= 3 and df.shape[1] >= 2:
            coerced = _coerce(df)
            if len(coerced.select_dtypes(include="number").columns) >= 1:
                return df, None, "inline table"
    except Exception:
        pass
    return None, s[:MAX_TEXT_CHARS], "inline text"


# ----------------------------- evidence --------------------------------------
def _round(x, n: int = 4):
    try:
        return round(float(x), n)
    except Exception:
        return x


def _d(ts) -> str:
    """Timestamp or Period -> 'YYYY-MM-DD' (keeps type checkers happy)."""
    if isinstance(ts, pd.Period):
        ts = ts.start_time
    return str(pd.Timestamp(ts).date())


def _coerce(df: pd.DataFrame) -> pd.DataFrame:
    """Turn '₹1,200' / '12%' into numbers and date-looking text into datetimes."""
    df = df.copy()
    for c in df.columns:
        s = df[c]
        if not _is_text_like(s):
            continue
        non_null = s.dropna().astype(str)
        if non_null.empty:
            continue
        cleaned = non_null.str.replace(_NUM_CLEAN, "", regex=True)
        if pd.to_numeric(cleaned, errors="coerce").notna().mean() > 0.9:
            df[c] = pd.to_numeric(s.astype(str).str.replace(_NUM_CLEAN, "", regex=True), errors="coerce")
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            if pd.to_datetime(non_null, errors="coerce").notna().mean() > 0.9:
                df[c] = pd.to_datetime(s, errors="coerce")
    return df


def _pick_target(num_cols: list, focus: str):
    if focus:
        by_lower = {str(c).lower(): c for c in num_cols}
        if focus.lower() in by_lower:
            return by_lower[focus.lower()]
    for c in num_cols:
        if _TARGET_HINT.search(str(c)):
            return c
    return num_cols[0] if num_cols else None


def _trend(s: pd.Series):
    """Trend facts for one series: first/last, peak/trough, and how well a straight line fits."""
    if len(s) < 3:
        return None
    y = s.to_numpy(dtype=float)
    x = np.arange(len(y), dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    ss_res = float(((y - (slope * x + intercept)) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot else 0.0
    scale = abs(float(y.mean())) or 1.0
    strength = "strong" if r2 >= 0.6 else ("moderate" if r2 >= 0.3 else "weak/noisy")
    if abs(slope) * len(y) < 0.02 * scale:
        direction = "flat"
    else:
        direction = "up" if slope > 0 else "down"
    first, last = float(y[0]), float(y[-1])
    return {
        "periods": int(len(y)),
        "first": {"period": _d(s.index[0]), "value": _round(first, 2)},
        "last": {"period": _d(s.index[-1]), "value": _round(last, 2)},
        "pct_change_first_to_last": _round((last - first) / abs(first) * 100, 1) if first else None,
        "peak": {"period": _d(s.idxmax()), "value": _round(y.max(), 2)},
        "trough": {"period": _d(s.idxmin()), "value": _round(y.min(), 2)},
        "direction": direction,
        "trend_fit_r2": _round(r2, 2),
        "trend_strength": strength,
        "avg_change_per_period_pct": _round(slope / scale * 100, 2),
    }


def _partial_periods(dates: pd.Series, level: str, periods) -> list:
    """First/last periods that the data only partly covers (they would distort a trend)."""
    ps = sorted(periods)
    if level == "D" or len(ps) < 3:
        return []
    lo, hi = dates.min().normalize(), dates.max().normalize()

    def length(p):
        return (p.end_time.normalize() - p.start_time.normalize()).days + 1

    out = []
    if ((ps[0].end_time.normalize() - lo).days + 1) / length(ps[0]) < 0.85:
        out.append(ps[0])
    if ((hi - ps[-1].start_time.normalize()).days + 1) / length(ps[-1]) < 0.85:
        out.append(ps[-1])
    return out


def _profile(df: pd.DataFrame, focus: str = "") -> dict:
    """Compute a compact, factual evidence pack from a table."""
    df = _coerce(df)
    n = len(df)
    ev: dict = {"rows": n, "columns": len(df.columns)}
    ev["column_types"] = {str(c): str(df[c].dtype) for c in df.columns[:60]}

    missing = (df.isna().mean() * 100).round(1)
    ev["missing_pct"] = {str(c): float(v) for c, v in missing.items() if v > 0}
    ev["duplicate_rows"] = int(df.duplicated().sum())

    def id_like(s: pd.Series) -> bool:
        return pd.api.types.is_integer_dtype(s) and len(s) > 10 and s.nunique() == len(s)

    num_cols = [c for c in df.select_dtypes(include="number").columns if not id_like(df[c])]
    cat_cols = [c for c in df.columns if _is_text_like(df[c]) or isinstance(df[c].dtype, pd.CategoricalDtype)]
    date_cols = list(df.select_dtypes(include="datetime").columns)

    target = _pick_target(num_cols, focus)
    if target is not None:
        num_cols = [target] + [c for c in num_cols if c != target]
        ev["main_metric"] = str(target)

    # Numeric summary + outliers
    if num_cols:
        desc = df[num_cols[:20]].describe().T
        ev["numeric_summary"] = {
            str(c): {k: _round(v) for k, v in row.items()} for c, row in desc.iterrows()
        }
        outliers = {}
        for c in num_cols[:15]:
            s = df[c].dropna()
            if len(s) < 8:
                continue
            q1, q3 = s.quantile([0.25, 0.75]).tolist()
            iqr = q3 - q1
            if iqr == 0:
                continue
            mask = (s < q1 - 1.5 * iqr) | (s > q3 + 1.5 * iqr)
            if mask.any():
                vals = s[mask]
                worst = vals.iloc[np.argsort(-np.abs(vals.to_numpy(dtype=float)))[:3]]
                outliers[str(c)] = {
                    "count": int(mask.sum()),
                    "pct_of_rows": _round(100 * mask.mean(), 1),
                    "most_extreme": [_round(v, 2) for v in worst],
                }
        if outliers:
            ev["outliers_iqr"] = outliers

    # Strong correlations
    if len(num_cols) >= 2 and n >= 8:
        corr = df[num_cols[:20]].corr(numeric_only=True)
        cols = list(corr.columns)
        pairs = []
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                # corr.iloc[i, j] can be a NumPy scalar; convert it to a plain Python float
                # before passing into float() so static type checkers accept it.
                r = float(np.asarray(corr.iloc[i, j]).item())
                if not np.isnan(r) and abs(r) >= 0.4:
                    pairs.append({"a": str(cols[i]), "b": str(cols[j]), "r": _round(r, 2)})
        pairs.sort(key=lambda p: -abs(p["r"]))
        if pairs:
            ev["strong_correlations"] = pairs[:6]

    # Time trends (sum and average per period, because we don't know which one matters)
    if date_cols and num_cols:
        dc = date_cols[0]
        d = df.dropna(subset=[dc]).sort_values(dc)
        if len(d) >= 4:
            span_days = (d[dc].max() - d[dc].min()).days
            level = "M" if span_days > 120 else ("W" if span_days > 21 else "D")
            d = d.assign(_p=d[dc].dt.to_period(level))
            dropped = _partial_periods(d[dc], level, d["_p"].unique())
            ev["time_column"] = str(dc)
            ev["time_granularity"] = {"M": "monthly", "W": "weekly", "D": "daily"}[level]
            if dropped:
                ev["partial_periods_excluded"] = [str(p) for p in dropped]
            trends = {}
            for c in num_cols[:3]:
                grouped = d.groupby("_p")[c]
                t_sum = _trend(grouped.sum(min_count=1).dropna().drop(dropped, errors="ignore"))
                t_mean = _trend(grouped.mean().dropna().drop(dropped, errors="ignore"))
                if t_sum or t_mean:
                    trends[str(c)] = {"per_period_total": t_sum, "per_period_average": t_mean}
            if trends:
                ev["trends"] = trends

    # Segment breakdowns for the main metric
    if target is not None and cat_cols:
        segs = {}
        for c in cat_cols[:3]:
            k = df[c].nunique()
            if not 2 <= k <= 30:
                continue
            g = df.groupby(c)[target].agg(["sum", "mean", "count"]).sort_values("sum", ascending=False)
            total = g["sum"].sum()

            def rows(part):
                return [
                    {
                        "segment": str(i),
                        "sum": _round(r["sum"], 2),
                        "mean": _round(r["mean"], 2),
                        "count": int(r["count"]),
                        "share_pct": _round(100 * r["sum"] / total, 1) if total else None,
                    }
                    for i, r in part.iterrows()
                ]

            segs[str(c)] = {"top": rows(g.head(5))}
            if k > 7:
                segs[str(c)]["bottom"] = rows(g.tail(2))
        if segs:
            ev["segments_for_main_metric"] = segs

    # Categorical mix + a few raw rows for context
    cats = {}
    for c in cat_cols[:10]:
        k = df[c].nunique()
        if 1 < k <= 50:
            vc = df[c].value_counts(normalize=True).head(5)
            cats[str(c)] = {"unique": int(k), "top_share_pct": {str(i): _round(100 * v, 1) for i, v in vc.items()}}
    if cats:
        ev["categorical_mix"] = cats
    ev["sample_rows"] = df.iloc[:5, :15].astype(str).to_dict("records")
    return ev


def _evidence_json(ev: dict) -> str:
    """Serialize, dropping the least important parts if the pack is too large."""
    for drop in (None, "sample_rows", "categorical_mix", "numeric_summary"):
        if drop:
            ev.pop(drop, None)
        txt = json.dumps(ev, ensure_ascii=False, default=str)
        if len(txt) <= MAX_EVIDENCE_CHARS:
            return txt
    return txt[:MAX_EVIDENCE_CHARS] + " ...[truncated]"


# ----------------------------- LLM -------------------------------------------
def _gemini_text(prompt: str, json_mode: bool = False, max_tokens: int = 12000) -> str:
    """One Gemini call that returns plain text (or JSON text when json_mode is on)."""
    config = {"temperature": 0.2, "maxOutputTokens": max_tokens}
    if json_mode:
        config["responseMimeType"] = "application/json"
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent",
        headers={"x-goog-api-key": os.environ["GOOGLE_API_KEY"]},
        json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config},
        timeout=120,
    )
    if not r.ok:
        raise RuntimeError(f"Gemini {r.status_code}: {r.text}")
    cand = r.json()["candidates"][0]
    text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", [])).strip()
    if not text:
        raise RuntimeError(f"Gemini returned no text (finishReason={cand.get('finishReason')})")
    return text


def _gemini_json(prompt: str) -> dict:
    """Ask Gemini for JSON; retry once if the reply is cut off or malformed."""
    last: Exception | None = None
    for _ in range(2):
        text = re.sub(r"^```(?:json)?|```$", "", _gemini_text(prompt, json_mode=True), flags=re.M).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            last = e
    raise RuntimeError(f"Gemini returned invalid JSON twice: {last}")


def _fmt(item) -> str:
    if isinstance(item, dict):
        return "- " + "; ".join(f"**{k}**: {v}" for k, v in item.items())
    return f"- {item}"


def _render(rep: dict) -> str:
    lines = [
        f"# {rep.get('headline', 'Analysis')}",
        "",
        f"**Confidence:** {rep.get('confidence', '?')} - {rep.get('confidence_reason', '')}",
        "",
    ]
    sections = [
        ("Key findings", "key_findings"),
        ("Patterns and trends", "patterns_and_trends"),
        ("Anomalies", "anomalies"),
        ("Likely drivers (hypotheses)", "likely_drivers"),
        ("Risks and data quality", "risks_and_data_quality"),
        ("Recommendations", "recommendations"),
        ("Follow-up questions", "follow_up_questions"),
    ]
    for title, key in sections:
        items = rep.get(key) or []
        if items:
            lines.append(f"## {title}")
            lines.extend(_fmt(i) for i in items)
            lines.append("")
    return "\n".join(lines)


# ----------------------------- the MCP tool ----------------------------------
def analyze_data(source: str, question: str = "", focus_column: str = "", context: str = "") -> dict:
    """Analyze data deeply and explain what matters. Use for ANY analysis request on data you
    already have: a spreadsheet or CSV file, numbers read off the screen, or pasted text.
    `source` is either a file name inside the workspace folder (for example 'sales.csv') or the
    raw data/text itself (for example text returned by ask_about_screen). To look things up on
    the web, call research_topic instead; it runs this tool itself. Real statistics are computed
    in code first, then interpreted, so the figures are reliable. `question` is what the user
    wants to know. `focus_column` optionally names the main metric column. `context` is optional
    extra notes. Returns spoken_summary (4-5 sentences to read aloud), report_pdf_path (the saved
    PDF report), report_path (the same report as .md) and report_markdown."""
    df, text, origin = _resolve_source(source)

    if df is not None:
        evidence = _evidence_json(_profile(df, focus_column))
        kind = "TABLE EVIDENCE (statistics computed with pandas; these figures are exact)"
    else:
        evidence = text
        kind = ("TEXT INPUT (no computed statistics available; quote figures exactly as written "
                "and say when something cannot be verified)")
    ctx = ""
    if context.strip():
        ctx = ("\n\nSUPPORTING CONTEXT (web research notes; unverified, cite them as such):\n"
               + context[:MAX_TEXT_CHARS])

    request = question.strip() or "Analyze this thoroughly and explain what matters most."
    prompt = f"{INSTRUCTIONS}\n\nUSER REQUEST: {request}\n\nSOURCE: {origin}\n\n{kind}:\n{evidence}{ctx}"

    report = _gemini_json(prompt)
    markdown = _render(report)
    stamp = f"{datetime.now():%Y%m%d_%H%M%S}"
    md_path = REPORTS / f"analysis_{stamp}.md"
    md_path.write_text(markdown, encoding="utf-8")
    pdf_path = md_to_pdf(markdown, md_path.with_suffix(".pdf"), title=report.get("headline", "Analysis"))

    return {
        "spoken_summary": report.get("spoken_summary", ""),
        "headline": report.get("headline", ""),
        "confidence": report.get("confidence", ""),
        "report_pdf_path": str(pdf_path),
        "report_path": str(md_path),
        "report_markdown": markdown,
    }