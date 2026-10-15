"""Tool implementations (plain functions). Registered on the FastMCP server
in server.py and unit-tested directly here. All data is bundled synthetic."""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = set("the a an and or of to in on for with is are was were be as at by it this that".split())


def _tokenize(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _load_docs(data_dir: str) -> list[dict]:
    docs = []
    for path in sorted(Path(data_dir, "docs").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        title = lines[0].lstrip("# ").strip() if lines else path.stem
        docs.append({"id": path.stem, "title": title, "text": text})
    return docs


def _bm25_search(docs: list[dict], query: str, k: int = 3) -> list[dict]:
    doc_tokens = [_tokenize(d["title"] + " " + d["text"]) for d in docs]
    df: dict[str, int] = {}
    for toks in doc_tokens:
        for term in set(toks):
            df[term] = df.get(term, 0) + 1
    n = len(docs)
    avgdl = sum(len(t) for t in doc_tokens) / max(n, 1)
    qterms = _tokenize(query)

    def score(i: int) -> float:
        tf: dict[str, int] = {}
        for t in doc_tokens[i]:
            tf[t] = tf.get(t, 0) + 1
        dl = len(doc_tokens[i])
        s = 0.0
        for term in set(qterms):
            df_t = df.get(term, 0)
            if not df_t:
                continue
            idf = math.log(1 + (n - df_t + 0.5) / (df_t + 0.5))
            f = tf.get(term, 0)
            s += idf * (f * 2.5) / (f + 1.5 * (1 - 0.75 + 0.75 * dl / avgdl))
        return s

    ranked = sorted(range(n), key=score, reverse=True)
    out = []
    for i in ranked[:k]:
        sc = round(score(i), 4)
        if sc > 0:
            out.append({"id": docs[i]["id"], "title": docs[i]["title"],
                        "snippet": " ".join(docs[i]["text"].split())[:300],
                        "score": sc})
    return out


def doc_search_impl(query: str, data_dir: str, k: int = 3) -> list[dict]:
    """Search bundled support docs (read-only)."""
    return _bm25_search(_load_docs(data_dir), query, k)


def record_lookup_impl(record_id: str, data_dir: str) -> dict | None:
    """Look up a bundled record by ID (e.g. 'R-2003')."""
    records = json.loads(Path(data_dir, "records.json").read_text(encoding="utf-8"))
    rid = record_id.strip().upper()
    for r in records:
        if r["record_id"].upper() == rid:
            return r
    return None


def text_stats_impl(text: str) -> dict:
    """Compute basic statistics for a piece of text."""
    words = _tokenize(text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    content_words = [w for w in words if w not in _STOP]
    top = Counter(content_words).most_common(5)
    n_words = len(words)
    return {
        "chars": len(text),
        "words": n_words,
        "sentences": len(sentences),
        "reading_time_minutes": round(n_words / 200, 2),
        "top_keywords": [{"word": w, "count": c} for w, c in top],
    }
