"""
SerpApi search client with caching, explicit live execution, and honest verbatim replay support.
"""

import os
import re
import json
import time
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import httpx
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("preflight.search_client")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

CACHE_DIR = Path(os.getenv("PREFLIGHT_CACHE_DIR", ".preflight_cache"))
FIXTURES_DIR = Path(__file__).parent / "fixtures"

_REDACT_RE = re.compile(r"(api_key['\"]?\s*[:=]\s*['\"]?)[^&'\"\s]+", re.IGNORECASE)
CACHE_TTL_SECONDS = 7 * 86400


def redact_sensitive(text: str) -> str:
    """Route every log line, error string, and exception repr through this."""
    return _REDACT_RE.sub(r"\1[REDACTED]", text or "")


def cache_key(query: str) -> str:
    """FIPS-safe MD5 query hash."""
    return hashlib.md5(query.strip().lower().encode("utf-8"), usedforsecurity=False).hexdigest()


def cache_is_fresh(path: Path) -> bool:
    """Returns True if the cached file is within the 7-day TTL window."""
    try:
        return (time.time() - path.stat().st_mtime) <= CACHE_TTL_SECONDS
    except OSError:
        return False


def prune_expired_cache(cache_dir: Path) -> int:
    """Delete only entries older than the TTL window."""
    removed = 0
    now = time.time()
    try:
        entries = list(cache_dir.glob("*.json"))
    except OSError:
        return 0
    for p in entries:
        try:
            if now - p.stat().st_mtime > CACHE_TTL_SECONDS:
                p.unlink()
                removed += 1
        except OSError:
            continue
    return removed


class SerpApiSearchClient:
    """Client for executing live queries against SerpApi or replaying recorded queries."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_enabled: bool = True,
        cache_dir: Optional[Path] = None,
    ):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY")
        self.cache_enabled = cache_enabled
        self.cache_dir = cache_dir or CACHE_DIR
        if self.cache_enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    _query_hash = staticmethod(cache_key)

    def _get_cached(self, query: str) -> Optional[Dict[str, Any]]:
        if not self.cache_enabled:
            return None
        cache_file = self.cache_dir / f"{cache_key(query)}.json"
        if cache_file.exists():
            if not cache_is_fresh(cache_file):
                try:
                    cache_file.unlink()
                except OSError:
                    pass
                return None
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    data["_from_cache"] = True
                    return data
            except Exception as e:
                logger.warning(redact_sensitive(f"Error reading cache for '{query}': {e}"))
        return None

    def _set_cached(self, query: str, data: Dict[str, Any]) -> None:
        if not self.cache_enabled:
            return
        cache_file = self.cache_dir / f"{cache_key(query)}.json"
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            prune_expired_cache(self.cache_dir)
        except Exception as e:
            logger.warning(redact_sensitive(f"Error writing cache for '{query}': {e}"))

    FIXTURE_TOPIC_RULES = {
        "pydantic_v2_replay.json": ["pydantic", "basesettings"],
        "nextjs_15_replay.json": ["next", "params"],
        "requests_verify_replay.json": ["requests", "verify"],
        "react_19_forwardref_replay.json": ["react", "forwardref"],
    }

    def _find_replay_fixture(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Search bundled fixtures for pre-recorded real SerpApi responses.
        Strict matching: matches only when ALL required topic keywords
        for that specific benchmark recording are present in the query.
        """
        if not FIXTURES_DIR.exists():
            return None

        query_norm = query.strip().lower()

        for fixture_file, required_terms in self.FIXTURE_TOPIC_RULES.items():
            if all(term in query_norm for term in required_terms):
                path = FIXTURES_DIR / fixture_file
                if path.exists():
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            content = json.load(f)
                            content["_is_replayed"] = True
                            content["_fixture_name"] = fixture_file
                            return content
                    except Exception as e:
                        logger.debug(f"Fixture read failed on {path}: {e}")

        # Fallback to direct search_parameters match
        for fixture_file in FIXTURES_DIR.glob("*.json"):
            try:
                with open(fixture_file, "r", encoding="utf-8") as f:
                    content = json.load(f)
                    if "search_parameters" in content:
                        sq = content.get("search_parameters", {}).get("q", "").lower().strip()
                        if sq and (sq == query_norm or sq in query_norm or query_norm in sq):
                            content["_is_replayed"] = True
                            content["_fixture_name"] = fixture_file.name
                            return content
            except Exception as e:
                logger.debug(f"Fixture check failed on {fixture_file}: {e}")

        return None

    async def search(
        self,
        query: str,
        num_results: int = 5,
        force_replay: bool = False,
        bypass_cache: bool = False,
        client: Optional[httpx.AsyncClient] = None,
    ) -> Dict[str, Any]:
        """
        Execute search for a query with explicit live and replay separation.
        """
        # ==========================================
        # PATH A: EXPLICIT REPLAY MODE
        # ==========================================
        if force_replay:
            fixture = self._find_replay_fixture(query)
            if fixture:
                fixture["_is_replayed"] = True
                logger.info(f"📦 [REPLAY FIXTURE] Matched recorded query from {fixture.get('_fixture_name', 'fixture')}")
                return fixture

            logger.warning(f"Replay mode requested but no recorded fixture matches query: '{query}'")
            return {
                "search_metadata": {
                    "status": "No matching replay fixture found",
                    "error": f"No pre-recorded SerpApi fixture exists for query: '{query}'. Provide SERPAPI_API_KEY for live search.",
                },
                "organic_results": [],
                "_is_replayed": True,
                "_fixture_missing": True,
            }

        # ==========================================
        # PATH B: LIVE SERPAPI MODE
        # ==========================================
        if not self.api_key:
            logger.warning(f"Live search requested for query '{query}', but SERPAPI_API_KEY is unset.")
            return {
                "search_metadata": {
                    "status": "Missing SERPAPI_API_KEY",
                    "error": "No SERPAPI_API_KEY configured in environment or CLI. Replay mode was not enabled.",
                },
                "organic_results": [],
                "_is_replayed": False,
                "_unverifiable_due_to_missing_key": True,
            }

        # Check local cache first (unless bypassed)
        if not bypass_cache:
            cached = self._get_cached(query)
            if cached:
                cached["_is_replayed"] = False
                logger.debug(f"Returning cached live result for query: '{query}'")
                return cached

        # Execute live HTTP request to SerpApi
        params = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": num_results,
            "gl": "us",
            "hl": "en",
        }

        logger.info(f"🌐 [LIVE SERPAPI] Outbound HTTP GET: https://serpapi.com/search (q='{query}')")
        start_http = time.perf_counter()

        async def _execute_get(http_client: httpx.AsyncClient):
            resp = await http_client.get("https://serpapi.com/search", params=params)
            http_duration_ms = (time.perf_counter() - start_http) * 1000

            if resp.status_code == 200:
                data = resp.json()
                data["_is_replayed"] = False
                data["_http_duration_ms"] = round(http_duration_ms, 1)
                logger.info(f"🌐 [LIVE SERPAPI] Received HTTP 200 OK in {http_duration_ms:.1f}ms")
                self._set_cached(query, data)
                return data
            elif resp.status_code in (401, 403):
                err_msg = f"SerpApi Authentication Error (HTTP {resp.status_code}): Invalid or expired API key"
                logger.error(f"❌ [LIVE SERPAPI] {err_msg}")
                return {
                    "search_metadata": {"status": "Auth Error", "error": err_msg},
                    "organic_results": [],
                    "_is_replayed": False,
                    "_api_error": err_msg,
                }
            else:
                err_msg = redact_sensitive(f"SerpApi Error (HTTP {resp.status_code}): {resp.text[:200]}")
                logger.error(f"❌ [LIVE SERPAPI] {err_msg}")
                return {
                    "search_metadata": {"status": "API Error", "error": err_msg},
                    "organic_results": [],
                    "_is_replayed": False,
                    "_api_error": err_msg,
                }

        try:
            if client is not None:
                return await _execute_get(client)
            else:
                async with httpx.AsyncClient(timeout=15.0) as local_client:
                    return await _execute_get(local_client)
        except httpx.TimeoutException:
            err_msg = "SerpApi request timed out after 15 seconds"
            logger.error(f"❌ [LIVE SERPAPI] {err_msg}")
            return {
                "search_metadata": {"status": "Timeout", "error": err_msg},
                "organic_results": [],
                "_is_replayed": False,
                "_api_error": err_msg,
            }
        except Exception as e:
            err_msg = redact_sensitive(f"Live SerpApi call failed: {str(e)}")
            logger.error(f"❌ [LIVE SERPAPI] {err_msg}")
            return {
                "search_metadata": {"status": "Network Error", "error": err_msg},
                "organic_results": [],
                "_is_replayed": False,
                "_api_error": err_msg,
            }
