"""LegalLibrary: the domain layer behind the MCP tools (search, lookup, citation), independent of MCP itself."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from legalsearch.corpus import Document, chunk_documents
from legalsearch.embeddings import Encoder, WordLlamaEncoder
from legalsearch.fulltext import query_terms
from legalsearch.search import HybridSearcher

DEFAULT_CORPUS = Path(__file__).resolve().parent / "data" / "corpus.jsonl"


@dataclass
class Act:
    code: str
    name: str
    year: int
    articles: int

    @property
    def abbreviation(self) -> str:
        return "".join(w[0] for w in self.name.split() if w[0].isupper())


class ArticleNotFound(KeyError):
    pass


class LegalLibrary:
    def __init__(self, corpus: str | Path = DEFAULT_CORPUS, encoder: Encoder | None = None):
        with open(corpus, encoding="utf-8") as f:
            self.docs = [Document(str(r["_id"]), r.get("title", ""), r["text"], r.get("metadata", {}))
                         for r in map(json.loads, f)]
        self.by_id = {d.id: d for d in self.docs}
        self.searcher = HybridSearcher(encoder or WordLlamaEncoder())
        self.searcher.index(chunk_documents(self.docs, max_words=250))
        acts: dict[str, Act] = {}
        for d in self.docs:
            m = d.metadata
            a = acts.setdefault(m["act_code"], Act(m["act_code"], m["act"], m["year"], 0))
            a.articles += 1
        self.acts = acts

    # ---------- lookups ----------
    def article(self, article_id: str) -> Document:
        doc = self.by_id.get(article_id.strip().upper())
        if doc is None:
            raise ArticleNotFound(f"No article '{article_id}'. IDs look like 'RT-2' (act code + article number); "
                                  f"act codes: {', '.join(sorted(self.acts))}.")
        return doc

    def act_articles(self, code: str) -> list[Document]:
        code = code.strip().upper()
        if code not in self.acts:
            raise ArticleNotFound(f"No act '{code}'. Available: {', '.join(sorted(self.acts))}.")
        return sorted((d for d in self.docs if d.metadata["act_code"] == code), key=lambda d: d.metadata["article"])

    def cite(self, article_id: str, style: str = "full") -> str:
        d = self.article(article_id)
        m, act = d.metadata, self.acts[d.metadata["act_code"]]
        heading = d.title.split(": ", 1)[-1]
        if style == "short":
            return f"{act.abbreviation} {m['year']}, art. {m['article']}"
        return f"{m['act']} ({m['year']}), Article {m['article']} ({heading})"

    # ---------- search ----------
    @staticmethod
    def snippet(text: str, query: str, width: int = 220) -> str:
        """The passage window with the most query terms, with matches in **bold**."""
        terms = {t[:5] for t in query_terms(query)}
        words = text.split()
        if len(words) * 7 <= width:
            window = words
        else:
            n = max(10, width // 7)
            best = max(range(0, max(1, len(words) - n + 1)),
                       key=lambda i: sum(re.sub(r"\W", "", w.lower())[:5] in terms for w in words[i:i + n]))
            window = words[best:best + n]
            window = (["…"] if best > 0 else []) + window + (["…"] if best + n < len(words) else [])
        return " ".join(f"**{w}**" if re.sub(r"\W", "", w.lower())[:5] in terms and len(w) > 2 else w
                        for w in window)

    def search(self, query: str, k: int = 5, act_codes: list[str] | None = None, year_from: int | None = None,
               year_to: int | None = None, mode: str = "hybrid") -> list[dict]:
        filters: dict = {}
        if act_codes:
            unknown = [c for c in act_codes if c.upper() not in self.acts]
            if unknown:
                raise ArticleNotFound(f"Unknown act code(s) {unknown}. Available: {', '.join(sorted(self.acts))}.")
            filters["act_code"] = [c.upper() for c in act_codes]
        if year_from is not None or year_to is not None:
            filters["year"] = {op: v for op, v in (("gte", year_from), ("lte", year_to)) if v is not None}
        resp = self.searcher.search(query, k=k * 3, mode=mode, filters=filters or None)
        results, seen = [], set()
        for h in resp.hits:  # passages of the same article are merged into one result
            doc_id = h.doc.doc_id
            if doc_id in seen:
                continue
            seen.add(doc_id)
            results.append({"id": doc_id, "citation": self.cite(doc_id), "snippet": self.snippet(h.doc.text, query),
                            "score": round(h.score, 5)})
            if len(results) == k:
                break
        return results
