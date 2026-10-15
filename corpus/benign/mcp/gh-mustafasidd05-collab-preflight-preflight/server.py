"""
FastMCP Server implementation for Preflight.
Exposes verify_claim and quick_check tools, prompts, and resources.
"""

import os
import json
import time
import asyncio
import logging
from typing import Optional, Dict, Any, List
import httpx
from fastmcp import FastMCP

from preflight import __version__
from preflight.models import PreflightVerdict, QuickCheckResponse, Ecosystem
from preflight.query_engine import QueryEngine
from preflight.search_client import SerpApiSearchClient, redact_sensitive
from preflight.ranker import ResultRanker
from preflight.synthesizer import VerdictSynthesizer
from preflight.trusted_domains import TIER_1_EXACT_HOSTS, TIER_2_EXACT_HOSTS

# Configure logging
logging.basicConfig(level=os.getenv("PREFLIGHT_LOG_LEVEL", "INFO"))
logger = logging.getLogger("preflight.server")

SEARCH_DEADLINE_S = 10.0

# Initialize FastMCP Server
mcp = FastMCP(
    "Preflight",
    version=__version__,
    instructions=(
        "You have access to Preflight, an authoritative live-verification MCP engine powered by SerpApi. "
        "Whenever you are about to write code relying on potentially deprecated APIs, renamed methods, "
        "library migration guides, or version-specific features, call `verify_claim` with your assertion. "
        "Preflight will cross-reference live official documentation and return a structured verdict "
        "(CONFIRMED, OUTDATED, CONFLICTING, or UNVERIFIABLE) along with the exact modern correction and canonical link."
    ),
)


async def gather_search_vectors(
    client: SerpApiSearchClient,
    queries: List[str],
    replay: bool = False,
    deadline: float = SEARCH_DEADLINE_S,
) -> List[Dict[str, Any]]:
    """Run all search vectors concurrently over one connection pool with deadline."""
    if not queries:
        return []

    async with httpx.AsyncClient(timeout=httpx.Timeout(deadline)) as http_client:
        tasks = [
            asyncio.create_task(client.search(q, num_results=5, force_replay=replay, client=http_client))
            for q in queries
        ]
        done, pending = await asyncio.wait(tasks, timeout=deadline)

        for t in pending:
            t.cancel()
        if pending:
            await asyncio.gather(*pending, return_exceptions=True)

        results: List[Dict[str, Any]] = []
        errors: List[str] = []
        for t in done:
            if t.cancelled():
                errors.append(f"vector timed out after {deadline}s")
                continue
            exc = t.exception()
            if exc is not None:
                errors.append(redact_sensitive(f"{type(exc).__name__}: {exc}"))
            else:
                results.append(t.result())

        for msg in errors:
            logger.warning("search vector failed: %s", msg)
        return results


@mcp.tool(
    name="verify_claim",
    description=(
        "Verifies a technical, library, or API claim against live documentation via SerpApi. "
        "Returns a structured verdict (CONFIRMED, OUTDATED, CONFLICTING, or UNVERIFIABLE), "
        "confidence score, canonical reference URL, and exact code corrections."
    ),
)
async def verify_claim(
    claim: str,
    ecosystem: Optional[str] = None,
    target_package: Optional[str] = None,
    replay: bool = False,
    serpapi_key: Optional[str] = None,
) -> str:
    """
    Verify a code or API claim against live official docs.

    Args:
        claim: The assertion to verify (e.g. "In Pydantic v2, BaseSettings is in pydantic")
        ecosystem: Optional ecosystem hint (python, javascript, typescript, rust, go)
        target_package: Optional library/package name hint
        replay: If True, uses cached real SerpApi responses (ideal for testing without API keys)
        serpapi_key: (Deprecated) Optional explicit SerpApi API key override
    """
    if serpapi_key:
        logger.warning(
            "Passing 'serpapi_key' to verify_claim is deprecated for security; "
            "set SERPAPI_API_KEY in the environment instead."
        )

    start_time = time.perf_counter_ns()
    logger.info(f"Preflight: Verifying claim: '{claim}' (mode={'REPLAY' if replay else 'LIVE'})")

    # 1. Analyze and formulate queries
    eco_hint = ecosystem.lower() if ecosystem in ["python", "javascript", "typescript", "rust", "go", "general"] else None
    analysis = QueryEngine.analyze_claim(
        claim=claim,
        ecosystem_hint=eco_hint,  # type: ignore
        package_hint=target_package,
    )

    client = SerpApiSearchClient(api_key=serpapi_key)

    # 2. Search SerpApi for formulated query vectors concurrently
    search_vectors = analysis.search_queries[:3] if len(analysis.search_queries) >= 3 else analysis.search_queries
    queries_run = list(search_vectors)

    raw_responses = await gather_search_vectors(
        client=client,
        queries=search_vectors,
        replay=replay,
        deadline=SEARCH_DEADLINE_S,
    )

    is_any_replayed = any(r.get("_is_replayed") for r in raw_responses)
    unverifiable_due_to_key = any(r.get("_unverifiable_due_to_missing_key") for r in raw_responses)
    fixture_missing = any(r.get("_fixture_missing") for r in raw_responses)
    api_error = next((r.get("_api_error") for r in raw_responses if r.get("_api_error")), None)

    # 3. Rank results by domain authority and recency
    evidence_items = ResultRanker.rank_results(raw_responses)

    # 4. Synthesize final structured verdict
    verdict: PreflightVerdict = VerdictSynthesizer.synthesize(
        claim=claim,
        analysis=analysis,
        evidence=evidence_items,
        queries_executed=queries_run,
        start_time_ns=start_time,
        is_replayed=is_any_replayed,
        unverifiable_missing_key=unverifiable_due_to_key and not evidence_items,
        api_error=api_error if not evidence_items else None,
        fixture_missing=fixture_missing and not evidence_items,
    )

    total_duration_ms = verdict.response_time_ms
    logger.info(f"Preflight: Verified in {total_duration_ms}ms -> Verdict: {verdict.verdict} (Confidence: {verdict.confidence:.2f})")
    return verdict.model_dump_json(indent=2)


@mcp.tool(
    name="quick_check",
    description="Lightweight shorthand verification for a specific package and API symbol.",
)
async def quick_check(
    package: str,
    symbol: str,
    version: Optional[str] = None,
    replay: bool = False,
    serpapi_key: Optional[str] = None,
) -> str:
    """Check a specific package symbol status."""
    if serpapi_key:
        logger.warning(
            "Passing 'serpapi_key' to quick_check is deprecated for security; "
            "set SERPAPI_API_KEY in the environment instead."
        )

    claim = f"In {package} {f'v{version}' if version else ''}, `{symbol}` usage and availability"
    verdict_json = await verify_claim(
        claim=claim,
        target_package=package,
        replay=replay,
        serpapi_key=serpapi_key,
    )
    v_data = json.loads(verdict_json)
    resp = QuickCheckResponse(
        package=package,
        symbol=symbol,
        status=v_data.get("verdict", "UNVERIFIABLE"),
        latest_reference=v_data.get("canonical_reference"),
        note=v_data.get("summary", ""),
    )
    return resp.model_dump_json(indent=2)


@mcp.prompt(name="pre_flight_api_audit")
def pre_flight_api_audit(package_list: str) -> str:
    """Prompt template for checking dependencies before writing integration code."""
    return (
        f"You are preparing to write code utilizing the following libraries: {package_list}.\n"
        "Before generating implementation code, check your assertions about deprecated methods, "
        "recent version breaking changes, and import paths using the `verify_claim` tool.\n"
        "If any API has changed, adopt the suggested modern correction immediately."
    )


@mcp.resource("preflight://status")
def get_status() -> str:
    """Resource returning Preflight runtime status and SerpApi connectivity."""
    has_key = bool(os.getenv("SERPAPI_API_KEY"))
    status_info = {
        "server": "Preflight",
        "version": __version__,
        "tools": ["verify_claim", "quick_check"],
        "serpapi_live_configured": has_key,
        "mode": "live_and_replay" if has_key else "replay_only",
        "supported_ecosystems": ["python", "javascript", "typescript", "rust", "go", "general"],
        "cache_dir": str(SerpApiSearchClient().cache_dir),
    }
    return json.dumps(status_info, indent=2)


@mcp.resource("preflight://trusted-domains")
def get_trusted_domains() -> str:
    """Resource exposing the developer domain trust hierarchy."""
    hierarchy = {
        "tier_1_authoritative_registries_and_docs": sorted(list(TIER_1_EXACT_HOSTS)),
        "tier_2_community_and_discussion": sorted(list(TIER_2_EXACT_HOSTS)),
        "description": "Tier 1 domains carry full 1.0 trust weighting. Tier 2 carries 0.75.",
    }
    return json.dumps(hierarchy, indent=2)


def main():
    """Server CLI entrypoint."""
    mcp.run()


if __name__ == "__main__":
    main()
