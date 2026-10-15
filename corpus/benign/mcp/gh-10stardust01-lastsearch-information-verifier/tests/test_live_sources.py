from app.live_sources import (
    SearchResult,
    VerifiedWebRetriever,
    filter_relevant_passages,
    source_for_url,
)
from app.schemas import EvidencePassage


class FakeSearchClient:
    def search(self, query: str, *, limit: int = 10):
        return [
            SearchResult(
                title="Untrusted blog",
                url="https://example.com/post",
                snippet="A random claim about Bengaluru.",
            ),
            SearchResult(
                title="Bengaluru | Britannica",
                url="https://www.britannica.com/place/Bangalore-India",
                snippet="Bengaluru, city, capital of Karnataka state, southern India.",
            ),
        ]


def test_source_allowlist_accepts_subdomains_and_rejects_unknowns():
    assert source_for_url("https://www.britannica.com/place/Bangalore-India").name == "Britannica"
    assert source_for_url("https://example.com/post") is None


def test_relevance_filter_rejects_only_city_overlap():
    claim = "Paris is the new capital of Bangalore"
    passages = [
        EvidencePassage(
            title="BWSSB",
            body="Bangalore Water Supply and Sewerage Board contact details",
            source_name="BWSSB",
            source_url="https://bwssb.gov.in/home",
            published_date="2026-05-09",
        ),
        EvidencePassage(
            title="Bengaluru",
            body="Bengaluru is the capital of Karnataka state in southern India.",
            source_name="Britannica",
            source_url="https://www.britannica.com/place/Bangalore-India",
            published_date="2026-05-09",
        ),
    ]

    relevant = filter_relevant_passages(claim, passages)

    assert [passage.source_name for passage in relevant] == ["Britannica"]


def test_verified_web_retriever_uses_allowlisted_results(monkeypatch):
    retriever = VerifiedWebRetriever(search_client=FakeSearchClient())

    def fake_fetch(url, *, fallback_title, fallback_snippet):
        source = source_for_url(url)
        if source is None or not (fallback_title or fallback_snippet):
            return None
        return EvidencePassage(
            title=fallback_title,
            body=fallback_snippet,
            source_name=source.name,
            source_url=url,
            published_date="2026-05-09",
        )

    monkeypatch.setattr(retriever, "fetch_passage", fake_fetch)

    evidence = retriever.search("Paris is the new capital of Bangalore")

    assert len(evidence) == 1
    assert evidence[0].source_name == "Britannica"
