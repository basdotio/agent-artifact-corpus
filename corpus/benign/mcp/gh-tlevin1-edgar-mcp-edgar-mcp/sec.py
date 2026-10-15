"""Thin HTTP client for SEC EDGAR's free JSON endpoints.

SEC requires every request to carry a User-Agent naming the requester and a
contact address (https://www.sec.gov/os/accessing-edgar-data). It is read from
EDGAR_USER_AGENT at request time rather than import time, so the server can be
started and inspected without it.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
CACHE_TTL_SECONDS = 3600


class SecError(Exception):
    """A request to EDGAR failed or could not be made."""


@dataclass(frozen=True)
class Company:
    cik: int
    ticker: str
    name: str


class SecClient:
    def __init__(self, user_agent: str | None = None, http: httpx.Client | None = None):
        self._user_agent = user_agent
        self._http = http or httpx.Client(timeout=30.0, follow_redirects=True)
        self._cache: dict[str, tuple[float, object]] = {}

    def _headers(self) -> dict[str, str]:
        ua = self._user_agent or os.environ.get("EDGAR_USER_AGENT")
        if not ua:
            raise SecError(
                "EDGAR_USER_AGENT is not set. SEC requires a User-Agent with a "
                'contact, e.g. EDGAR_USER_AGENT="Jane Doe jane@example.com".'
            )
        return {"User-Agent": ua, "Accept-Encoding": "gzip, deflate"}

    def _get_json(self, url: str):
        hit = self._cache.get(url)
        if hit and time.monotonic() - hit[0] < CACHE_TTL_SECONDS:
            return hit[1]
        try:
            resp = self._http.get(url, headers=self._headers())
        except httpx.HTTPError as e:
            raise SecError(f"Request to {url} failed: {e}") from e
        if resp.status_code == 404:
            raise SecError(f"EDGAR has no data at {url}")
        if resp.status_code != 200:
            raise SecError(f"EDGAR returned HTTP {resp.status_code} for {url}")
        data = resp.json()
        self._cache[url] = (time.monotonic(), data)
        return data

    def companies(self) -> list[Company]:
        raw = self._get_json(TICKERS_URL)
        return [
            Company(cik=int(r["cik_str"]), ticker=r["ticker"].upper(), name=r["title"])
            for r in raw.values()
        ]

    def company_facts(self, cik: int) -> dict:
        return self._get_json(FACTS_URL.format(cik=cik))
