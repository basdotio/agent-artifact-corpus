import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from typing import Iterable
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from app.schemas import EvidencePassage

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VerifiedSource:
    name: str
    domain: str
    tier: str


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


VERIFIED_SOURCES = [
    VerifiedSource("BMRCL", "bmrcl.co.in", "official"),
    VerifiedSource("BMRCL", "bmrc.co.in", "official"),
    VerifiedSource("BBMP", "bbmp.gov.in", "official"),
    VerifiedSource("BWSSB", "bwssb.gov.in", "official"),
    VerifiedSource("BESCOM", "bescom.karnataka.gov.in", "official"),
    VerifiedSource("BDA", "bda.karnataka.gov.in", "official"),
    VerifiedSource("BMTC", "mybmtc.karnataka.gov.in", "official"),
    VerifiedSource("Karnataka Government", "karnataka.gov.in", "official"),
    VerifiedSource("Bengaluru Urban District", "bengaluruurban.nic.in", "official"),
    VerifiedSource("PIB", "pib.gov.in", "official"),
    VerifiedSource("Incredible India", "incredibleindia.gov.in", "official"),
    VerifiedSource("Karnataka Tourism", "karnatakatourism.org", "official"),
    VerifiedSource("Bengaluru Traffic Police", "btp.gov.in", "official"),
    VerifiedSource("Bengaluru Traffic Police", "bangaloretrafficpolice.gov.in", "official"),
    VerifiedSource("The Hindu", "thehindu.com", "trusted_news"),
    VerifiedSource("Deccan Herald", "deccanherald.com", "trusted_news"),
    VerifiedSource("Indian Express", "indianexpress.com", "trusted_news"),
    VerifiedSource("New Indian Express", "newindianexpress.com", "trusted_news"),
    VerifiedSource("Britannica", "britannica.com", "trusted_reference"),
]

BACKGROUND_URLS = {
    "bengaluru_capital": [
        "https://www.britannica.com/place/Bangalore-India",
        "https://karnatakatourism.org/en/destinations/bengaluru",
    ]
}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "been",
    "being",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "into",
    "is",
    "it",
    "new",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "will",
    "with",
}

CITY_TERMS = {"bangalore", "bengaluru", "blr"}
ENTITY_QUERY_HINTS = {
    "bbmp": "BBMP Bengaluru",
    "bmrcl": "BMRCL Bengaluru metro",
    "metro": "BMRCL Bengaluru metro",
    "bwssb": "BWSSB Bengaluru water",
    "bescom": "BESCOM Bengaluru power",
    "bmtc": "BMTC Bengaluru bus",
    "traffic": "Bengaluru Traffic Police",
}


def source_for_url(url: str) -> VerifiedSource | None:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    for source in VERIFIED_SOURCES:
        domain = source.domain.lower()
        if host == domain or host.endswith(f".{domain}"):
            return source
    return None


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOPWORDS
    }


def expanded_tokens(text: str) -> set[str]:
    tokens = tokenize(text)
    if tokens & CITY_TERMS:
        tokens |= CITY_TERMS
    return tokens


def relevance_score(claim: str, passage: EvidencePassage) -> int:
    claim_tokens = expanded_tokens(claim)
    text_tokens = expanded_tokens(f"{passage.title} {passage.body}")
    overlap = claim_tokens & text_tokens

    score = len(overlap)
    if overlap <= CITY_TERMS:
        score = 0
    if "capital" in claim_tokens and "capital" in text_tokens:
        score += 2
    if any(entity in claim_tokens & text_tokens for entity in ENTITY_QUERY_HINTS):
        score += 2
    return score


def filter_relevant_passages(
    claim: str, passages: Iterable[EvidencePassage], *, min_score: int = 2
) -> list[EvidencePassage]:
    scored = [
        (relevance_score(claim, passage), passage)
        for passage in passages
        if passage.body.strip() or passage.title.strip()
    ]
    scored = [(score, passage) for score, passage in scored if score >= min_score]
    scored.sort(key=lambda item: item[0], reverse=True)
    return [passage for _, passage in scored]


class BingRssSearchClient:
    def __init__(self, session: requests.Session | None = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0"})

    def search(self, query: str, *, limit: int = 10) -> list[SearchResult]:
        response = self.session.get(
            "https://www.bing.com/search",
            params={"format": "rss", "q": query},
            timeout=15,
        )
        response.raise_for_status()

        root = ET.fromstring(response.text)
        results = []
        for item in root.findall("./channel/item"):
            title = item.findtext("title") or ""
            url = item.findtext("link") or ""
            snippet = item.findtext("description") or ""
            if title and url:
                results.append(
                    SearchResult(
                        title=unescape(title).strip(),
                        url=url.strip(),
                        snippet=clean_text(snippet),
                    )
                )
            if len(results) >= limit:
                break
        return results


class VerifiedWebRetriever:
    def __init__(
        self,
        *,
        search_client: BingRssSearchClient | None = None,
        session: requests.Session | None = None,
    ):
        self.search_client = search_client or BingRssSearchClient()
        self.session = session or requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "Mozilla/5.0 (compatible; Bengaluru-Misinfo-Layer/1.0; "
                    "+https://example.invalid/verified-source-check)"
                )
            }
        )

    def search(self, claim: str, *, size: int = 5) -> list[EvidencePassage]:
        candidates: list[EvidencePassage] = []
        seen_urls: set[str] = set()

        for url in self._background_urls_for_claim(claim):
            passage = self.fetch_passage(url, fallback_title="", fallback_snippet="")
            if passage and passage.source_url not in seen_urls:
                candidates.append(passage)
                seen_urls.add(passage.source_url)

        for query in self.build_queries(claim):
            try:
                results = self.search_client.search(query, limit=12)
            except Exception as error:
                logger.warning("Verified web search failed for %r: %s", query, error)
                continue

            for result in results:
                if result.url in seen_urls or source_for_url(result.url) is None:
                    continue
                passage = self.fetch_passage(
                    result.url,
                    fallback_title=result.title,
                    fallback_snippet=result.snippet,
                )
                if passage:
                    candidates.append(passage)
                    seen_urls.add(passage.source_url)

        return filter_relevant_passages(claim, candidates)[:size]

    def build_queries(self, claim: str) -> list[str]:
        normalized = claim.strip()
        queries = [
            f"{normalized} Bengaluru Bangalore",
            f"{normalized} official source",
        ]

        tokens = expanded_tokens(claim)
        for entity, hint in ENTITY_QUERY_HINTS.items():
            if entity in tokens:
                queries.append(f"{hint} {normalized}")

        if "capital" in tokens and tokens & CITY_TERMS:
            queries.append("Bengaluru capital Karnataka official")

        deduped = []
        for query in queries:
            if query not in deduped:
                deduped.append(query)
        return deduped

    def _background_urls_for_claim(self, claim: str) -> list[str]:
        tokens = expanded_tokens(claim)
        if "capital" in tokens and tokens & CITY_TERMS:
            return BACKGROUND_URLS["bengaluru_capital"]
        return []

    def fetch_passage(
        self,
        url: str,
        *,
        fallback_title: str,
        fallback_snippet: str,
    ) -> EvidencePassage | None:
        source = source_for_url(url)
        if source is None:
            return None

        title = fallback_title
        body = fallback_snippet
        published_date = datetime.now(timezone.utc).date().isoformat()

        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "text/html" in content_type or not content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                title = extract_title(soup) or title
                body = extract_body(soup) or body
                published_date = extract_date(soup) or published_date
        except Exception as error:
            logger.warning("Could not fetch verified source %s: %s", url, error)

        body = clean_text(body)
        title = clean_text(title)
        if not title and not body:
            return None

        return EvidencePassage(
            title=title,
            body=body[:5000],
            source_name=source.name,
            source_url=url,
            published_date=published_date,
        )


def extract_title(soup: BeautifulSoup) -> str:
    element = soup.select_one("meta[property='og:title'], h1, title")
    if not element:
        return ""
    return element.get("content", "") or element.get_text(" ", strip=True)


def extract_body(soup: BeautifulSoup) -> str:
    for element in soup.select("script, style, noscript, svg, nav, footer"):
        element.decompose()

    candidates = []
    selectors = [".topic-content", ".articlebodycontent", "article", "main", "[role='main']", ".content", "body"]
    for selector in selectors:
        for element in soup.select(selector):
            paragraphs = [
                clean_text(child.get_text(" ", strip=True))
                for child in element.select("p, li")
                if clean_text(child.get_text(" ", strip=True))
            ]
            if paragraphs:
                candidate = clean_text(" ".join(paragraphs))
                if len(candidate) > 200:
                    return candidate
                candidates.append(candidate)
            else:
                candidates.append(clean_text(element.get_text(" ", strip=True)))

    candidates = [candidate for candidate in candidates if candidate]
    if not candidates:
        return ""
    return max(candidates, key=len)


def extract_date(soup: BeautifulSoup) -> str:
    selectors = [
        "meta[property='article:published_time']",
        "meta[name='date']",
        "meta[name='publishdate']",
        "time[datetime]",
    ]
    for element in soup.select(",".join(selectors)):
        value = element.get("content", "") or element.get("datetime", "")
        match = re.search(r"\d{4}-\d{2}-\d{2}", value)
        if match:
            return match.group(0)
    return ""


def clean_text(text: str) -> str:
    text = unescape(text or "")
    if "<" in text and ">" in text:
        text = BeautifulSoup(text, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()
