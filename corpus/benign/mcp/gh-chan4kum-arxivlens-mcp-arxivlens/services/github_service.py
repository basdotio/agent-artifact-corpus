"""Asynchronous GitHub repository discovery service for academic papers."""

from __future__ import annotations

import logging
import os
import re
from typing import List, Optional

import httpx

from arxivlens.models import CodeRepository

logger = logging.getLogger(__name__)

STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "with",
    "by", "about", "against", "between", "into", "through", "during", "before",
    "after", "above", "below", "from", "up", "down", "of", "off", "over", "under",
    "again", "further", "then", "once", "is", "are", "was", "were", "be", "been",
    "being", "have", "has", "had", "having", "do", "does", "did", "doing", "paper",
    "using", "via", "towards", "based", "new", "novel", "approach", "method"
}


class GitHubService:
    """Service to search for open-source code repositories matching research papers."""

    BASE_URL = "https://api.github.com/search/repositories"

    def __init__(
        self,
        token: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
        timeout: float = 10.0,
    ) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN")
        self._client = client
        self._timeout = timeout

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client

        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "ArXivLens-MCP/0.1.0 (Research Intelligence)",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return httpx.AsyncClient(headers=headers, timeout=self._timeout, follow_redirects=True)

    def _extract_title_keywords(self, title: str, max_words: int = 4) -> str:
        """Extract meaningful keywords from paper title for repository search."""
        words = re.findall(r"\b[A-Za-z0-9\-]+\b", title)
        filtered = [w for w in words if w.lower() not in STOP_WORDS and len(w) > 2]
        return " ".join(filtered[:max_words])

    def _parse_repo_item(self, item: dict) -> CodeRepository:
        """Parse GitHub API item dict into a CodeRepository model."""
        license_name = None
        if item.get("license") and isinstance(item["license"], dict):
            license_name = item["license"].get("spdx_id") or item["license"].get("name")

        return CodeRepository(
            name=item.get("name", "unknown"),
            full_name=item.get("full_name", "unknown/unknown"),
            url=item.get("html_url", ""),
            description=item.get("description"),
            stars=item.get("stargazers_count", 0),
            forks=item.get("forks_count", 0),
            language=item.get("language"),
            updated_at=item.get("updated_at"),
            license=license_name,
        )

    async def find_repositories(
        self,
        arxiv_id: str,
        title: str = "",
        max_results: int = 5,
    ) -> List[CodeRepository]:
        """Search GitHub for repositories implementing or referencing the paper."""
        client = await self._get_client()
        should_close = self._client is None
        repositories: List[CodeRepository] = []
        seen_urls = set()

        try:
            # Query 1: Search by exact arXiv identifier
            clean_id = arxiv_id.strip()
            # Remove version suffix if any (e.g., 2310.06825v1 -> 2310.06825)
            base_id = re.sub(r"v\d+$", "", clean_id)
            query_id = f'"{base_id}" in:description,readme'

            response = await client.get(
                self.BASE_URL,
                params={"q": query_id, "sort": "stars", "order": "desc", "per_page": max_results},
            )

            if response.status_code == 200:
                data = response.json()
                for item in data.get("items", []):
                    repo = self._parse_repo_item(item)
                    if repo.url not in seen_urls:
                        seen_urls.add(repo.url)
                        repositories.append(repo)

            # Query 2: If few or no results found, search by title keywords
            if len(repositories) < max_results and title:
                keywords = self._extract_title_keywords(title)
                if keywords:
                    query_title = f"{keywords} in:name,description"
                    resp_title = await client.get(
                        self.BASE_URL,
                        params={
                            "q": query_title,
                            "sort": "stars",
                            "order": "desc",
                            "per_page": max_results - len(repositories),
                        },
                    )
                    if resp_title.status_code == 200:
                        data_title = resp_title.json()
                        for item in data_title.get("items", []):
                            repo = self._parse_repo_item(item)
                            if repo.url not in seen_urls:
                                seen_urls.add(repo.url)
                                repositories.append(repo)

        except Exception as err:
            logger.warning("GitHub search failed for paper %s: %s", arxiv_id, err)
        finally:
            if should_close:
                await client.aclose()

        # Return sorted by stars descending
        repositories.sort(key=lambda r: r.stars, reverse=True)
        return repositories[:max_results]
