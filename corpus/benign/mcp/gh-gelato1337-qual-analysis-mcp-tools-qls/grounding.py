"""Quote grounding: find where a model's quote sits in the transcript.

Returns character spans, not just a yes/no, so every quote can be shown in
context and compared across runs by position. Order of attempts:

1. exact substring
2. same words, ignoring case and whitespace differences
3. fuzzy best-matching substring (rapidfuzz partial_ratio_alignment),
   accepted at >= threshold (earlier pipelines used 85 with Levenshtein)
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Span:
    start: int
    end: int
    score: float
    method: str


def locate(quote: str, text: str, threshold: float = 90) -> Span | None:
    quote = (quote or "").strip().strip('"“”«»').strip()
    if not quote or not text:
        return None
    i = text.find(quote)
    if i >= 0:
        return Span(i, i + len(quote), 100.0, "exact")
    words = quote.split()
    if words:
        pat = r"\s+".join(re.escape(w) for w in words)
        m = re.search(pat, text, flags=re.IGNORECASE)
        if m:
            return Span(m.start(), m.end(), 100.0, "normalized")
    from rapidfuzz import fuzz

    q, t = quote.lower(), text.lower()
    if len(q) != len(quote) or len(t) != len(text):  # lower() changed length; fall back to raw
        q, t = quote, text
    al = fuzz.partial_ratio_alignment(q, t)
    if al is not None and al.score >= threshold:
        return Span(al.dest_start, al.dest_end, round(al.score, 1), "fuzzy")
    return None


def ground(quote: str, segment_id: str | None, segments: list[dict], threshold: float = 90) -> tuple[dict, Span] | None:
    """Find the quote in the named segment, else anywhere in the document's segments."""
    by_id = {s["id"]: s for s in segments}
    order = []
    if segment_id in by_id:
        order.append(by_id[segment_id])
    order += [s for s in segments if s["id"] != segment_id]
    best = None
    for seg in order:
        sp = locate(quote, seg["text"], threshold)
        if sp and (best is None or sp.score > best[1].score):
            best = (seg, sp)
            if sp.score >= 100:
                break
    return best
