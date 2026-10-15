"""VulnWatch MCP server — read-mostly bridge to the VulnWatch Public Developer API.

Thin stdio wrapper over https://app.vulnwatch.tech/api. Auth: Bearer PAT
(env VULNWATCH_API_TOKEN). Read-only tools are the default surface:
stats, history, status, report. Starting a scan (a side-effecting action)
is gated behind VULNWATCH_MCP_ALLOW_SCAN=1 to avoid a prompt-injected agent
launching arbitrary scans (confused-deputy guard).
"""

from __future__ import annotations

import os
from typing import Optional

import httpx
from fastmcp import FastMCP

DEFAULT_BASE_URL = os.environ.get("VULNWATCH_API_BASE", "https://app.vulnwatch.tech/api")

# Whether the *write* action (submit_scan) is enabled. Kept off by default.
_ALLOW_SCAN = os.environ.get("VULNWATCH_MCP_ALLOW_SCAN", "0").strip().lower() in {"1", "true", "yes", "on"}


class VulnWatchClient:
    """Minimal authenticated client. Ownership-isolation and error semantics
    are whatever the API returns — we do not second-guess the server."""

    def __init__(self, base_url: str, token: str) -> None:
        self._base = base_url.rstrip("/")
        self._http = httpx.Client(
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            timeout=30.0,
        )

    def _req(self, method: str, path: str, **kw) -> dict:
        url = f"{self._base}{path}"
        resp = self._http.request(method, url, **kw)
        # Non-JSON / error handling: surface HTTP + message verbatim.
        if resp.status_code >= 400:
            detail = resp.text[:600]
            raise RuntimeError(f"HTTP {resp.status_code}: {detail}")
        try:
            return resp.json()
        except Exception:
            return {"_raw": resp.text[:2000]}


def _client() -> VulnWatchClient:
    token = os.environ.get("VULNWATCH_API_TOKEN", "").strip()
    if not token:
        raise RuntimeError("VULNWATCH_API_TOKEN is not set")
    return VulnWatchClient(os.environ.get("VULNWATCH_API_BASE", DEFAULT_BASE_URL), token)


mcp = FastMCP(
    "vulnwatch",
    instructions=(
        "Bridge to the VulnWatch vulnerability-scanning platform API. "
        "Auth is a personal access token set at server start (VULNWATCH_API_TOKEN), "
        "never passed per-call. Tools cover account quota, scan history, per-scan "
        "status and reports. Submitting a scan is a side effect and is only "
        "available when the server was started with VULNWATCH_MCP_ALLOW_SCAN=1."
    ),
)


# ---------------------------------------------------------------------------
# Read-only surface
# ---------------------------------------------------------------------------

@mcp.tool()
def vw_get_stats() -> dict:
    """Account usage: free monthly allowance (used/remaining), concurrency,
    totals (completed/failed/in_progress), and credits left."""
    return _client()._req("GET", "/scan/action/stats")


@mcp.tool()
def vw_scan_history(
    status: Optional[str] = None,
    per_page: int = 10,
    page: int = 1,
) -> dict:
    """Paginated list of the account's own API scans (newest first).
    status: 'completed' | 'failed' | 'in_progress' (optional filter)."""
    params: dict = {"per_page": per_page, "page": page}
    if status:
        params["status"] = status
    return _client()._req("GET", "/scan/action/history", params=params)


@mcp.tool()
def vw_scan_status(check_uuid: str) -> dict:
    """Status of one scan by its check_uuid (ownership-isolated; another
    account's uuid → 404). Reflects in_progress/completed/failed."""
    return _client()._req("GET", f"/scan/action/{check_uuid}")


@mcp.tool()
def vw_scan_report(check_uuid: str) -> dict:
    """Full JSON vulnerability report for a completed scan. 409 until the scan
    completes; ownership-isolated (foreign uuid → 404)."""
    return _client()._req("GET", f"/scan/action/{check_uuid}/report")


# ---------------------------------------------------------------------------
# Side-effecting (gated)
# ---------------------------------------------------------------------------

@mcp.tool()
def vw_submit_scan(
    url: str,
    scan_type: str = "basic",
    tools: Optional[list[str]] = None,
    ai_analyst: bool = False,
) -> dict:
    """Start an asynchronous scan of a URL and return its check_uuid.
    Consumes the free monthly allowance, else one credit. Concurrency capped at 1.
    ONLY ENABLED when the server runs with VULNWATCH_MCP_ALLOW_SCAN=1; otherwise
    raises a clear error."""
    if not _ALLOW_SCAN:
        raise RuntimeError(
            "submit_scan is disabled: start the server with VULNWATCH_MCP_ALLOW_SCAN=1 "
            "to allow it (a side-effecting action)."
        )
    body_raw: dict = {"url": url, "scan_type": scan_type, "ai_analyst": ai_analyst}
    if tools:
        body_raw["tools"] = tools
    return _client()._req("POST", "/scan/action", json=body_raw)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()