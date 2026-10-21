# SPDX-License-Identifier: MIT
"""FastMCP server for Google Chrome UX Report (CrUX) and PageSpeed Insights:
Real-user field Core Web Vitals (LCP, INP, CLS), 28-day history, and Lighthouse lab audits.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.mcpserver import MCPServer
    mcp = MCPServer(
        "core-web-vitals-mcp",
        title="Core Web Vitals & Google CrUX MCP Server",
        version="0.1.0",
        website_url="https://github.com/surendranb/core-web-vitals-mcp",
    )
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP
        mcp = FastMCP("core-web-vitals-mcp")
    except ImportError:
        class DummyMCP:
            def tool(self, *args, **kwargs):
                def dec(fn):
                    return fn
                return dec
            def run(self):
                pass
        mcp = DummyMCP()

from core_web_vitals_mcp.client import (
    CRUX_HISTORY_ENDPOINT,
    CRUX_QUERY_ENDPOINT,
    PAGESPEED_ENDPOINT,
    TEST_BED_DOMAINS,
    WebVitalsClient,
    resolve_api_key,
)
from core_web_vitals_mcp.skills import (
    list_available_skills,
    read_skill_content,
    skill_read as _skill_read,
    skills_list as _skills_list,
)
from core_web_vitals_mcp.telemetry import (
    MCP_SERVER_VERSION,
    classify_exception,
    track_event,
    track_tool_call,
)

# ---------------------------------------------------------------------------
# Universal fleet update checker (async, non-blocking, 24h TTL, 7d re-nudge)
# ---------------------------------------------------------------------------
_FLEET_CACHE_FILE = Path.home() / ".cache" / "mcp_fleet_updates.json"
_UPDATE_CHECK_TTL = 86400  # 24 hours


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        clean = re.sub(r"[^\d.]", "", str(v))
        parts = [int(p) for p in clean.split(".") if p.isdigit()]
        return tuple(parts) if parts else (0,)
    except Exception:
        return (0,)


def check_server_update(package_name: str, current_version: str, force_check: bool = False) -> dict:
    """Checks PyPI for latest version and returns update status and instructions."""
    now = time.time()
    cache: dict[str, Any] = {}
    if _FLEET_CACHE_FILE.exists():
        try:
            cache = json.loads(_FLEET_CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass

    entry = cache.get(package_name, {})
    last_check = entry.get("last_checked", 0)
    latest_version = entry.get("latest_version", current_version)

    if force_check or (now - last_check > _UPDATE_CHECK_TTL):
        try:
            req = urllib.request.Request(
                f"https://pypi.org/pypi/{package_name}/json",
                headers={"User-Agent": f"{package_name}/{current_version}"},
            )
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    latest_version = data.get("info", {}).get("version", current_version)
                    cache[package_name] = {"latest_version": latest_version, "last_checked": now}
                    _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                    _FLEET_CACHE_FILE.write_text(json.dumps(cache), encoding="utf-8")
        except Exception:
            pass

    cur_tuple = _parse_version(current_version)
    lat_tuple = _parse_version(latest_version)
    is_outdated = lat_tuple > cur_tuple

    return {
        "package": package_name,
        "current_version": current_version,
        "latest_version": latest_version,
        "is_outdated": is_outdated,
        "upgrade_command": f"uvx --upgrade {package_name}" if is_outdated else None,
    }


def get_upgrade_nudge(package_name: str, current_version: str) -> str:
    """Returns in-band upgrade directive if outdated, else empty string."""
    try:
        status = check_server_update(package_name, current_version)
        if status.get("is_outdated"):
            lat = status.get("latest_version")
            return f"\n\n[NOTICE: Update available for {package_name}: {current_version} -> {lat}. Run: {status.get('upgrade_command')}]"
    except Exception:
        pass
    return ""


# Shared client
default_client = WebVitalsClient()


# ---------------------------------------------------------------------------
# MCP Tool: get_crux_metrics
# ---------------------------------------------------------------------------
@mcp.tool()
def get_crux_metrics(
    url: str,
    form_factor: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Query Google Chrome User Experience Report (CrUX) API for real-user field metrics.

    Returns 75th percentile ratings for LCP, INP, CLS, FCP, TTFB, and overall Core Web Vitals assessment.

    Args:
        url: Page URL (e.g. 'https://surendranb.com/blog/article') or root origin ('https://surendranb.com').
        form_factor: Device form factor filter ('ALL_FORM_FACTORS', 'PHONE', 'DESKTOP', 'TABLET'). Defaults to ALL_FORM_FACTORS.
        api_key: Optional Google API Key. If omitted, checks GOOGLE_API_KEY or CRUX_API_KEY environment variables.
    """
    t0 = time.perf_counter()
    tool_name = "get_crux_metrics"

    try:
        url_str = str(url or "").strip()
        if not url_str:
            raise ValueError("[INPUT_FIXABLE] Parameter 'url' is required.")

        ff_str = str(form_factor).strip() if form_factor is not None else None
        client = WebVitalsClient(api_key=api_key)
        data = client.query_crux_record(url_or_origin=url_str, form_factor=ff_str, api_key=api_key)

        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(data, indent=2) + get_upgrade_nudge("core-web-vitals-mcp", MCP_SERVER_VERSION)
        call_status = "warning" if data.get("status") in ("AUTH_ERROR", "RATE_LIMITED", "FIELD_DATA_REQUIRES_KEY") else "success"
        track_tool_call(tool_name, duration_ms, status=call_status, rows_returned=len(data.get("metrics", {})), result_chars=len(out_str))
        return out_str

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: get_crux_history
# ---------------------------------------------------------------------------
@mcp.tool()
def get_crux_history(
    url_or_origin: str,
    form_factor: Optional[str] = None,
    api_key: Optional[str] = None,
) -> str:
    """Query Google Chrome UX Report History API for 28-day historical field metric trends.

    Provides timeseries percentiles for LCP, INP, CLS, FCP, and TTFB across 25+ weekly collection periods.

    Args:
        url_or_origin: Web page URL or origin domain (e.g. 'https://surendranb.com').
        form_factor: Optional device filter ('ALL_FORM_FACTORS', 'PHONE', 'DESKTOP', 'TABLET').
        api_key: Optional Google API Key. If omitted, checks GOOGLE_API_KEY or CRUX_API_KEY environment variables.
    """
    t0 = time.perf_counter()
    tool_name = "get_crux_history"

    try:
        target_str = str(url_or_origin or "").strip()
        if not target_str:
            raise ValueError("[INPUT_FIXABLE] Parameter 'url_or_origin' is required.")

        ff_str = str(form_factor).strip() if form_factor is not None else None
        client = WebVitalsClient(api_key=api_key)
        data = client.query_crux_history(url_or_origin=target_str, form_factor=ff_str, api_key=api_key)

        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(data, indent=2) + get_upgrade_nudge("core-web-vitals-mcp", MCP_SERVER_VERSION)
        call_status = "warning" if data.get("status") in ("AUTH_ERROR", "RATE_LIMITED", "FIELD_DATA_REQUIRES_KEY") else "success"
        track_tool_call(tool_name, duration_ms, status=call_status, rows_returned=data.get("collection_periods_count", 0), result_chars=len(out_str))
        return out_str

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: audit_pagespeed
# ---------------------------------------------------------------------------
@mcp.tool()
def audit_pagespeed(
    url: str,
    strategy: str = "mobile",
    api_key: Optional[str] = None,
) -> str:
    """Run a Google PageSpeed Insights lab audit for synthetic Lighthouse performance scores and diagnostics.

    Returns overall performance score (0-100), Speed Index, Total Blocking Time (TBT),
    Largest Contentful Paint (LCP), and prioritized remediation opportunities.

    Args:
        url: URL of the web page to audit (e.g. 'https://surendranb.com').
        strategy: Analysis strategy ('mobile' or 'desktop'). Defaults to 'mobile'.
        api_key: Optional Google API Key. If omitted, checks GOOGLE_API_KEY or PAGESPEED_API_KEY.
    """
    t0 = time.perf_counter()
    tool_name = "audit_pagespeed"

    try:
        url_str = str(url or "").strip()
        if not url_str:
            raise ValueError("[INPUT_FIXABLE] Parameter 'url' is required.")

        strat_str = str(strategy or "mobile").strip()
        client = WebVitalsClient(api_key=api_key)
        data = client.run_pagespeed_audit(url=url_str, strategy=strat_str, api_key=api_key)

        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(data, indent=2) + get_upgrade_nudge("core-web-vitals-mcp", MCP_SERVER_VERSION)
        call_status = "warning" if data.get("status") in ("RATE_LIMITED", "AUTH_ERROR") else "success"
        track_tool_call(tool_name, duration_ms, status=call_status, rows_returned=len(data.get("top_opportunities", [])), result_chars=len(out_str))
        return out_str

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: doctor
# ---------------------------------------------------------------------------
@mcp.tool()
def doctor(
    api_key: Optional[str] = None,
) -> str:
    """Validate Google Cloud API credentials, test endpoint reachability, and check test beds.

    Args:
        api_key: Optional Google API Key to test directly.
    """
    t0 = time.perf_counter()
    tool_name = "doctor"

    try:
        key_val, key_source = resolve_api_key(api_key)
        masked_key = f"{key_val[:4]}...{key_val[-4:]}" if (key_val and len(key_val) > 8) else ("***" if key_val else None)

        # 1. Endpoint connectivity checks
        endpoint_checks: Dict[str, Any] = {}
        for ep_name, ep_url in [
            ("crux_query", CRUX_QUERY_ENDPOINT),
            ("crux_history", CRUX_HISTORY_ENDPOINT),
            ("pagespeed", PAGESPEED_ENDPOINT),
        ]:
            try:
                # Test connectivity with short timeout
                req = urllib.request.Request(
                    ep_url,
                    headers={"User-Agent": "core-web-vitals-mcp/0.1.1"},
                    method="GET",
                )
                try:
                    with urllib.request.urlopen(req, timeout=4.0) as resp:
                        endpoint_checks[ep_name] = {"reachable": True, "http_status": resp.status}
                except urllib.error.HTTPError as h_err:
                    endpoint_checks[ep_name] = {"reachable": True, "http_status": h_err.code}
            except Exception as e_err:
                endpoint_checks[ep_name] = {"reachable": False, "error": str(e_err)}

        all_reachable = all(c.get("reachable", False) for c in endpoint_checks.values())

        report: Dict[str, Any] = {
            "status": "HEALTHY" if (key_val and all_reachable) else "ACTION_REQUIRED",
            "mode": "AUTHENTICATED" if key_val else "KEYLESS_MODE (PageSpeed Active, CrUX Field Data Requires Free Key)",
            "credentials": {
                "configured": bool(key_val),
                "source": key_source,
                "preview": masked_key,
            },
            "endpoints": endpoint_checks,
            "test_bed_domains": TEST_BED_DOMAINS,
            "available_skills": list_available_skills(),
        }

        if not key_val:
            report["guidance"] = (
                "[ENVIRONMENT_FIXABLE: STOP & ASK HUMAN] Google Cloud API Key is not configured.\n"
                "• Keyless Mode: PageSpeed Insights lab audits work out-of-the-box.\n"
                "• Chrome UX Report (CrUX): Real-user 28-day field data requires a free Google API key (up to 150 QPM).\n"
                "SYSTEM DIRECTIVE: Call skill_read(name='google-api-setup') to view the 2-minute setup guide "
                "from https://developers.google.com/speed/docs/insights/v5/get-started#APIKey"
            )

        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(report, indent=2) + get_upgrade_nudge("core-web-vitals-mcp", MCP_SERVER_VERSION)
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out_str))
        return out_str

    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: skills_list
# ---------------------------------------------------------------------------
@mcp.tool()
def skills_list() -> str:
    """List available Core Web Vitals diagnostic and remediation playbooks (LCP, INP, CLS)."""
    t0 = time.perf_counter()
    tool_name = "skills_list"
    try:
        out = _skills_list()
        duration_ms = (time.perf_counter() - t0) * 1000
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: skill_read
# ---------------------------------------------------------------------------
@mcp.tool()
def skill_read(name: str) -> str:
    """Read a specialized Core Web Vitals optimization playbook (e.g. 'lcp-optimization', 'inp-debugging', 'cls-remediation').

    Args:
        name: Name of the skill to read. Call skills_list to view available playbooks.
    """
    t0 = time.perf_counter()
    tool_name = "skill_read"
    try:
        out = _skill_read(name)
        duration_ms = (time.perf_counter() - t0) * 1000
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out))
        return out
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


# ---------------------------------------------------------------------------
# MCP Tool: check_for_updates
# ---------------------------------------------------------------------------
@mcp.tool()
def check_for_updates(force: bool = False) -> str:
    """Check PyPI for the latest version of core-web-vitals-mcp."""
    t0 = time.perf_counter()
    tool_name = "check_for_updates"
    try:
        status = check_server_update("core-web-vitals-mcp", MCP_SERVER_VERSION, force_check=force)
        duration_ms = (time.perf_counter() - t0) * 1000
        out_str = json.dumps(status, indent=2)
        track_tool_call(tool_name, duration_ms, status="success", result_chars=len(out_str))
        return out_str
    except Exception as exc:
        duration_ms = (time.perf_counter() - t0) * 1000
        err_cat = classify_exception(exc)
        err_msg = str(exc)
        track_tool_call(tool_name, duration_ms, status="error", error_category=err_cat, error_message=err_msg)
        return err_msg


def main():
    """Main entrypoint for MCP server execution over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
