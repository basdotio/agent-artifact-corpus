"""Asynchronous arXiv API integration service."""

from __future__ import annotations

import datetime
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional

import httpx

from arxivlens.models import CategoryInfo, FeedResponse, PaperMetadata

logger = logging.getLogger(__name__)

ATOM_NS = "{http://www.w3.org/2005/Atom}"
ARXIV_NS = "{http://arxiv.org/schemas/atom}"

SUPPORTED_CATEGORIES = [
    CategoryInfo(
        code="cs.AI",
        name="Artificial Intelligence",
        description="Foundational AI, reasoning, knowledge representation, and autonomous agents.",
    ),
    CategoryInfo(
        code="cs.LG",
        name="Machine Learning (CS)",
        description="Deep learning, neural network architectures, optimization, and reinforcement learning.",
    ),
    CategoryInfo(
        code="cs.CL",
        name="Computation and Language (NLP)",
        description="Large language models, natural language understanding, translation, and speech.",
    ),
    CategoryInfo(
        code="cs.CV",
        name="Computer Vision and Pattern Recognition",
        description="Image recognition, generative models, diffusion architectures, and 3D perception.",
    ),
    CategoryInfo(
        code="cs.RO",
        name="Robotics",
        description="Embodied agents, motion planning, robot learning, and sensor fusion.",
    ),
    CategoryInfo(
        code="cs.SE",
        name="Software Engineering",
        description="Automated programming, code intelligence, testing, verification, and architecture.",
    ),
    CategoryInfo(
        code="stat.ML",
        name="Machine Learning (Statistics)",
        description="Statistical learning theory, Bayesian methods, high-dimensional data, and inference.",
    ),
]


DEFAULT_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Accept-Encoding": "gzip, deflate",
}


class ArxivService:
    """Async service to query arXiv API and parse Atom XML responses."""

    BASE_URL = "https://export.arxiv.org/api/query"

    def __init__(self, client: Optional[httpx.AsyncClient] = None, timeout: float = 15.0) -> None:
        self._client = client
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        return httpx.AsyncClient(headers=DEFAULT_HEADERS, timeout=self._timeout, follow_redirects=True)

    def _clean_text(self, text: Optional[str]) -> str:
        """Strip and normalize multi-line strings and whitespace."""
        if not text:
            return ""
        return re.sub(r"\s+", " ", text.strip())

    def _extract_arxiv_id(self, raw_id: str) -> str:
        """Extract canonical arXiv ID from URL or URN string."""
        raw_id = raw_id.strip()
        match = re.search(r"(\d{4}\.\d{4,5}(?:v\d+)?|[a-z\-]+(?:\.[A-Z]{2})?/\d{7}(?:v\d+)?)", raw_id)
        if match:
            return match.group(1)
        return raw_id.split("/")[-1]

    def _parse_entry(self, entry: ET.Element) -> Optional[PaperMetadata]:
        """Parse a single <entry> XML node into a PaperMetadata model."""
        id_elem = entry.find(f"{ATOM_NS}id")
        if id_elem is None or not id_elem.text:
            return None

        raw_id = id_elem.text.strip()
        arxiv_id = self._extract_arxiv_id(raw_id)

        title_elem = entry.find(f"{ATOM_NS}title")
        title = self._clean_text(title_elem.text) if title_elem is not None else "Untitled Paper"

        summary_elem = entry.find(f"{ATOM_NS}summary")
        summary = self._clean_text(summary_elem.text) if summary_elem is not None else ""

        published_elem = entry.find(f"{ATOM_NS}published")
        published = published_elem.text.strip() if published_elem is not None and published_elem.text else ""

        updated_elem = entry.find(f"{ATOM_NS}updated")
        updated = updated_elem.text.strip() if updated_elem is not None and updated_elem.text else published

        authors = []
        for author in entry.findall(f"{ATOM_NS}author"):
            name_elem = author.find(f"{ATOM_NS}name")
            if name_elem is not None and name_elem.text:
                authors.append(self._clean_text(name_elem.text))

        # Categories
        categories = []
        primary_cat = ""
        prim_elem = entry.find(f"{ARXIV_NS}primary_category")
        if prim_elem is not None and "term" in prim_elem.attrib:
            primary_cat = prim_elem.attrib["term"]

        for cat in entry.findall(f"{ATOM_NS}category"):
            term = cat.attrib.get("term")
            if term:
                categories.append(term)
                if not primary_cat:
                    primary_cat = term

        if not primary_cat:
            primary_cat = "cs.AI"

        # Links
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        arxiv_url = f"https://arxiv.org/abs/{arxiv_id}"
        for link in entry.findall(f"{ATOM_NS}link"):
            rel = link.attrib.get("rel")
            title_attr = link.attrib.get("title")
            href = link.attrib.get("href", "")
            if title_attr == "pdf" or (rel == "related" and "pdf" in href):
                pdf_url = href
            elif rel == "alternate":
                arxiv_url = href

        # Optional attributes
        comment_elem = entry.find(f"{ARXIV_NS}comment")
        comment = self._clean_text(comment_elem.text) if comment_elem is not None else None

        journal_elem = entry.find(f"{ARXIV_NS}journal_ref")
        journal_ref = self._clean_text(journal_elem.text) if journal_elem is not None else None

        doi_elem = entry.find(f"{ARXIV_NS}doi")
        doi = self._clean_text(doi_elem.text) if doi_elem is not None else None

        return PaperMetadata(
            arxiv_id=arxiv_id,
            title=title,
            summary=summary,
            authors=authors,
            published=published,
            updated=updated,
            primary_category=primary_cat,
            categories=categories,
            pdf_url=pdf_url,
            arxiv_url=arxiv_url,
            comment=comment,
            journal_ref=journal_ref,
            doi=doi,
        )

    def parse_feed_xml(self, xml_content: str) -> List[PaperMetadata]:
        """Parse raw Atom XML string and return list of PaperMetadata."""
        papers = []
        try:
            root = ET.fromstring(xml_content)
            for entry in root.findall(f"{ATOM_NS}entry"):
                paper = self._parse_entry(entry)
                if paper:
                    papers.append(paper)
        except ET.ParseError as err:
            logger.error("Failed to parse arXiv Atom XML: %s", err)
        return papers

    async def search_papers(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",
        sort_order: str = "descending",
    ) -> List[PaperMetadata]:
        """Search papers on arXiv using query syntax."""
        sort_map = {
            "relevance": "relevance",
            "lastUpdatedDate": "lastUpdatedDate",
            "submittedDate": "submittedDate",
            "recent": "submittedDate",
        }
        api_sort_by = sort_map.get(sort_by, "relevance")

        # Format query for arXiv API if no prefix provided
        formatted_query = query.strip()
        if not any(formatted_query.startswith(p) for p in ["all:", "ti:", "au:", "abs:", "cat:", "co:", "jr:"]):
            formatted_query = f"all:{formatted_query}"

        limit = min(max(1, max_results), 30)
        # Construct query URL directly
        query_url = f"{self.BASE_URL}?search_query={formatted_query}&start=0&max_results={limit}"
        if api_sort_by != "relevance":
            query_url += f"&sortBy={api_sort_by}&sortOrder={sort_order}"

        client = await self._get_client()
        should_close = self._client is None
        try:
            response = await client.get(query_url)
            response.raise_for_status()
            return self.parse_feed_xml(response.text)
        except Exception as err:
            logger.error("arXiv search query failed for '%s': %s", query, err)
            return []
        finally:
            if should_close:
                await client.aclose()

    async def get_paper_by_id(self, arxiv_id: str) -> Optional[PaperMetadata]:
        """Fetch full details for a specific arXiv ID."""
        clean_id = self._extract_arxiv_id(arxiv_id)
        query_url = f"{self.BASE_URL}?id_list={clean_id}"

        client = await self._get_client()
        should_close = self._client is None
        try:
            response = await client.get(query_url)
            response.raise_for_status()
            papers = self.parse_feed_xml(response.text)
            return papers[0] if papers else None
        except Exception as err:
            logger.error("Failed to fetch arXiv paper '%s': %s", clean_id, err)
            return None
        finally:
            if should_close:
                await client.aclose()

    async def get_category_feed(
        self, category: str = "cs.AI", max_results: int = 10
    ) -> FeedResponse:
        """Fetch the latest submitted papers in a specific category."""
        clean_cat = category.strip()
        query = f"cat:{clean_cat}"
        papers = await self.search_papers(
            query=query,
            max_results=max_results,
            sort_by="submittedDate",
            sort_order="descending",
        )
        return FeedResponse(
            category=clean_cat,
            fetched_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            total_papers=len(papers),
            papers=papers,
        )

    def get_supported_categories(self) -> List[CategoryInfo]:
        """Return list of supported academic categories and descriptions."""
        return SUPPORTED_CATEGORIES
