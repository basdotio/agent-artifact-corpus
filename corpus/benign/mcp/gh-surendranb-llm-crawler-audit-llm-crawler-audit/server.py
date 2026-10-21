# SPDX-License-Identifier: MIT
"""AI & LLM crawler readiness MCP Server.

Audits robots.txt for AI bots, validates /llms.txt and /llms-full.txt compliance,
and verifies markdown mirror content negotiation for GEO/AEO optimization.
"""
from __future__ import annotations

import json
import os
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from mcp.server.mcpserver import MCPServer as FastMCP
except ImportError:
    from mcp.server.fastmcp import FastMCP

from llm_crawler_audit.crawler_rules import (
    AI_USER_AGENTS,
    HeadLinkParser,
    RobotsTxt,
    parse_link_headers,
    validate_llms_txt_content,
)
from llm_crawler_audit.skills import skill_read as _skill_read, skills_list as _skills_list
from llm_crawler_audit.telemetry import (
    MCP_SERVER_VERSION,
    track_tool_call,
)

SERVER_NAME = "llm-crawler-audit"
mcp = FastMCP("llm-crawler-audit")

USER_AGENT = f"llm-crawler-audit/{MCP_SERVER_VERSION} (+https://llm-crawler.builditwithai.xyz)"
DEFAULT_TIMEOUT = 8.0

_FLEET_CACHE_FILE = Path.home() / ".cache" / "llm-crawler-audit" / "fleet_cache.json"
_UPDATE_CHECK_TTL = 86400.0


def _parse_version(v: str) -> tuple:
    try:
        clean = "".join(c for c in v if c.isdigit() or c == ".").strip(".")
        return tuple(int(x) for x in clean.split("."))
    except Exception:
        return (0,)


def check_server_update(package_name: str, current_version: str, force_check: bool = False) -> dict:
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
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                latest_version = data.get("info", {}).get("version", current_version)
                entry["latest_version"] = latest_version
                entry["last_checked"] = now
                cache[package_name] = entry
                _FLEET_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                tmp = _FLEET_CACHE_FILE.with_suffix(".tmp")
                tmp.write_text(json.dumps(cache), encoding="utf-8")
                tmp.replace(_FLEET_CACHE_FILE)
        except Exception:
            pass

    has_update = _parse_version(latest_version) > _parse_version(current_version)
    return {
        "package": package_name,
        "current_version": current_version,
        "latest_version": latest_version,
        "has_update": has_update,
        "update_command": f"uvx --refresh {package_name}" if has_update else None,
    }


def _normalize_url(url: str) -> str:
    """Validate and normalize user-provided URL."""
    u = (url or "").strip()
    if not u:
        raise ValueError("[INPUT_FIXABLE] URL cannot be empty. Please provide a valid URL like 'https://example.com'.")
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    parsed = urllib.parse.urlparse(u)
    if not parsed.netloc:
        raise ValueError(f"[INPUT_FIXABLE] Malformed URL '{url}'. Domain name is required (e.g. 'https://example.com').")
    return u


def _fetch_url(url: str, headers: Optional[Dict[str, str]] = None, timeout: float = DEFAULT_TIMEOUT) -> Tuple[int, Dict[str, str], bytes]:
    """Fetch URL and return (status_code, headers_dict, body_bytes)."""
    req_headers = {"User-Agent": USER_AGENT}
    if headers:
        req_headers.update(headers)

    req = urllib.request.Request(url, headers=req_headers)
    ctx = ssl.create_default_context()

    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            status = resp.status
            resp_headers = {k.lower(): v for k, v in resp.headers.items()}
            body = resp.read()
            return status, resp_headers, body
    except urllib.error.HTTPError as e:
        resp_headers = {k.lower(): v for k, v in e.headers.items()} if e.headers else {}
        body = e.read() if hasattr(e, "read") else b""
        return e.code, resp_headers, body
    except urllib.error.URLError as e:
        reason = str(e.reason).lower()
        if "timed out" in reason or "timeout" in reason or "temporarily unavailable" in reason:
            raise RuntimeError(f"[TRANSIENT] Connection timed out while contacting '{url}': {e.reason}")
        if "nodename nor servname provided" in reason or "name resolution" in reason:
            raise RuntimeError(f"[INPUT_FIXABLE] Could not resolve host for '{url}': verify domain name spelling.")
        if "certificate" in reason or "ssl" in reason:
            raise RuntimeError(f"[TRANSIENT] SSL/TLS handshake failed for '{url}': {e.reason}")
        raise RuntimeError(f"[TRANSIENT] Network error connecting to '{url}': {e.reason}")
    except Exception as e:
        raise RuntimeError(f"[TRANSIENT] Unexpected error accessing '{url}': {e}")


@mcp.tool()
def audit_robots_for_ai(url: str) -> str:
    """Audit robots.txt for 9 major AI search and training crawlers under RFC 9309 rules.

    Simulates permissions for GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai,
    PerplexityBot, Applebot-Extended, Bytespider, Google-Extended, and CCBot.
    Returns status (allowed, disallowed, unspecified), crawl delay, and AEO impact.
    """
    t0 = time.perf_counter()
    try:
        norm_url = _normalize_url(url)
    except Exception as e:
        msg = str(e)
        track_tool_call("audit_robots_for_ai", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="ValidationError", msg=msg)
        return json.dumps({"error": msg, "classification": "[INPUT_FIXABLE]"}, indent=2)

    parsed = urllib.parse.urlparse(norm_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    robots_url = f"{origin}/robots.txt"
    test_path = parsed.path if parsed.path else "/"

    try:
        status, headers, body = _fetch_url(robots_url)
    except Exception as e:
        msg = str(e)
        track_tool_call("audit_robots_for_ai", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="NetworkError", msg=msg)
        return json.dumps({"error": msg, "robots_url": robots_url, "classification": "[TRANSIENT]"}, indent=2)

    if status == 404 or status >= 400:
        # Under RFC 9309, missing robots.txt permits all crawler access
        report = {
            "origin": origin,
            "robots_url": robots_url,
            "http_status": status,
            "exists": False,
            "rfc_9309_default": "allow_all",
            "summary": "robots.txt is missing (HTTP 404). Under RFC 9309, all crawlers are permitted by default, but no explicit AI policy or sitemaps are communicated.",
            "agents_audit": [
                {
                    "agent": a["name"],
                    "operator": a["operator"],
                    "category": a["category"],
                    "status": "allowed",
                    "matched_group": "none",
                    "rule_type": "rfc9309_default_allow",
                    "rule_pattern": None,
                    "crawl_delay": None,
                }
                for a in AI_USER_AGENTS
            ],
            "allowed_count": len(AI_USER_AGENTS),
            "disallowed_count": 0,
            "sitemaps": [],
            "ai_readiness_score": 70,
            "recommendations": [
                "Create a /robots.txt declaring explicit permissions for GPTBot, ClaudeBot, and PerplexityBot to guarantee citation indexing.",
                "Include a Sitemap: directive pointing to your XML sitemap.",
                "Add an '# LLMs: /llms.txt' comment for automated agent discovery.",
            ],
        }
        out = json.dumps(report, indent=2)
        track_tool_call("audit_robots_for_ai", (time.perf_counter() - t0) * 1000, "success", len(AI_USER_AGENTS), len(out))
        return out

    raw_text = body.decode("utf-8", "replace")
    parser = RobotsTxt(raw_text)

    agent_results = []
    allowed_count = 0
    disallowed_count = 0
    search_disallowed = []
    training_disallowed = []

    for a in AI_USER_AGENTS:
        res = parser.simulate_agent(a["name"], path=test_path)
        res["operator"] = a["operator"]
        res["category"] = a["category"]
        res["description"] = a["description"]
        if res["status"] == "allowed":
            allowed_count += 1
        else:
            disallowed_count += 1
            if a["category"] == "live_search" or a["name"] in ("GPTBot", "ClaudeBot", "PerplexityBot"):
                search_disallowed.append(a["name"])
            else:
                training_disallowed.append(a["name"])
        agent_results.append(res)

    # Score calculation (0 - 100 for robots component)
    if disallowed_count == 0:
        robots_score = 100
        verdict = f"Fully Accessible: All {len(AI_USER_AGENTS)} AI search and training agents permitted."
    elif len(search_disallowed) == 0:
        robots_score = 80
        verdict = f"Search-Only Policy: Real-time search citations allowed, but training crawlers blocked ({', '.join(training_disallowed)})."
    elif allowed_count == 0:
        robots_score = 0
        verdict = f"Strict AI Block: All {len(AI_USER_AGENTS)} AI user agents are disallowed."
    else:
        robots_score = max(10, int((allowed_count / len(AI_USER_AGENTS)) * 100))
        verdict = f"Partially Restricted: Blocked search crawlers: {', '.join(search_disallowed)}."

    recommendations: List[str] = []
    if search_disallowed:
        recommendations.append(
            f"Unblock search indexers ({', '.join(search_disallowed)}) to ensure your content can be cited in ChatGPT Search, Claude, and Perplexity."
        )
    if not parser.sitemaps:
        recommendations.append("Declare one or more XML sitemaps using 'Sitemap: https://...' in robots.txt.")
    if not parser.llm_directives:
        recommendations.append("Add '# LLMs: https://yourdomain.com/llms.txt' to guide automated agent crawlers.")

    report = {
        "origin": origin,
        "robots_url": robots_url,
        "http_status": status,
        "exists": True,
        "test_path": test_path,
        "verdict": verdict,
        "ai_readiness_score": robots_score,
        "allowed_count": allowed_count,
        "disallowed_count": disallowed_count,
        "search_bots_blocked": search_disallowed,
        "training_bots_blocked": training_disallowed,
        "sitemaps": parser.sitemaps,
        "llm_comments": parser.llm_directives,
        "agents_audit": agent_results,
        "recommendations": recommendations,
    }
    out = json.dumps(report, indent=2)
    track_tool_call("audit_robots_for_ai", (time.perf_counter() - t0) * 1000, "success", len(AI_USER_AGENTS), len(out))
    return out


@mcp.tool()
def validate_llms_txt(url: str) -> str:
    """Fetch and validate /llms.txt and /llms-full.txt compliance against llmstxt.org standard.

    Verifies H1 presence, blockquote summary, section layout, markdown link structure,
    estimated tokens, and returns an actionable compliance score (0-100).
    """
    t0 = time.perf_counter()
    try:
        norm_url = _normalize_url(url)
    except Exception as e:
        msg = str(e)
        track_tool_call("validate_llms_txt", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="ValidationError", msg=msg)
        return json.dumps({"error": msg, "classification": "[INPUT_FIXABLE]"}, indent=2)

    parsed = urllib.parse.urlparse(norm_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    llms_txt_url = f"{origin}/llms.txt"
    llms_full_url = f"{origin}/llms-full.txt"

    # Fetch /llms.txt
    try:
        status_txt, headers_txt, body_txt = _fetch_url(llms_txt_url)
    except Exception as e:
        status_txt, headers_txt, body_txt = 0, {}, b""

    # Fetch /llms-full.txt
    try:
        status_full, headers_full, body_full = _fetch_url(llms_full_url)
    except Exception as e:
        status_full, headers_full, body_full = 0, {}, b""

    has_llms_txt = status_txt == 200 and len(body_txt) > 0
    has_llms_full = status_full == 200 and len(body_full) > 0

    llms_txt_details: Dict[str, Any] = {}
    if has_llms_txt:
        text_content = body_txt.decode("utf-8", "replace")
        llms_txt_details = validate_llms_txt_content(text_content)
        llms_txt_details["http_status"] = status_txt
        llms_txt_details["content_type"] = headers_txt.get("content-type", "")
    else:
        llms_txt_details = {
            "valid": False,
            "http_status": status_txt,
            "compliance_score": 0,
            "title": None,
            "summary": None,
            "sections": [],
            "links_count": 0,
            "links": [],
            "character_count": 0,
            "estimated_tokens": 0,
            "warnings": [f"Missing /llms.txt endpoint (HTTP {status_txt or 'Unreachable'})"],
        }

    llms_full_details: Dict[str, Any] = {
        "exists": has_llms_full,
        "http_status": status_full,
        "content_type": headers_full.get("content-type", "") if has_llms_full else None,
        "size_bytes": len(body_full) if has_llms_full else 0,
        "estimated_tokens": max(0, round(len(body_full) / 4)) if has_llms_full else 0,
    }

    # Composite compliance score (0-100)
    score = llms_txt_details.get("compliance_score", 0)
    if has_llms_full:
        score = min(100, score + 20)
    else:
        score = min(80, score)

    recommendations: List[str] = []
    if not has_llms_txt:
        recommendations.append("Create /llms.txt at domain root containing project title (# Title), summary quote (> Summary), and curated documentation links.")
    else:
        recommendations.extend(llms_txt_details.get("warnings", []))

    if not has_llms_full:
        recommendations.append("Provide /llms-full.txt bundling comprehensive documentation for full-context agent ingestion.")

    report = {
        "origin": origin,
        "llms_txt_url": llms_txt_url,
        "llms_full_url": llms_full_url,
        "compliance_score": score,
        "llms_txt": llms_txt_details,
        "llms_full_txt": llms_full_details,
        "recommendations": recommendations,
    }
    out = json.dumps(report, indent=2)
    track_tool_call("validate_llms_txt", (time.perf_counter() - t0) * 1000, "success", 1, len(out))
    return out


@mcp.tool()
def audit_markdown_mirror(url: str) -> str:
    """Audit markdown mirror availability and content negotiation for agentic consumption.

    Inspects HTML <head> for <link rel="alternate" type="text/markdown">, checks HTTP
    Link headers, and verifies Accept: text/markdown content negotiation.
    """
    t0 = time.perf_counter()
    try:
        norm_url = _normalize_url(url)
    except Exception as e:
        msg = str(e)
        track_tool_call("audit_markdown_mirror", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="ValidationError", msg=msg)
        return json.dumps({"error": msg, "classification": "[INPUT_FIXABLE]"}, indent=2)

    # 1. Fetch standard HTML response
    try:
        status_html, headers_html, body_html = _fetch_url(
            norm_url,
            headers={"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"},
        )
    except Exception as e:
        msg = str(e)
        track_tool_call("audit_markdown_mirror", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="NetworkError", msg=msg)
        return json.dumps({"error": msg, "target_url": norm_url, "classification": "[TRANSIENT]"}, indent=2)

    html_text = body_html.decode("utf-8", "replace")

    # 2. Extract alternate link from HTTP Link header
    link_header = headers_html.get("link", "")
    header_links = parse_link_headers(link_header)
    header_md_links = [l["url"] for l in header_links if l.get("rel") == "alternate" and l.get("type") in ("text/markdown", "text/x-markdown")]

    # 3. Extract alternate link from HTML <head>
    head_parser = HeadLinkParser()
    try:
        head_parser.feed(html_text)
    except Exception:
        pass
    head_md_links = head_parser.alternate_markdown_links

    discovered_mirrors = list(dict.fromkeys(header_md_links + head_md_links))
    primary_mirror_url: Optional[str] = None
    if discovered_mirrors:
        primary_mirror_url = urllib.parse.urljoin(norm_url, discovered_mirrors[0])

    # 4. Test Content Negotiation (Accept: text/markdown)
    negotiation_supported = False
    negotiation_content_type: Optional[str] = None
    negotiated_bytes = 0
    vary_header = headers_html.get("vary", "")
    has_vary_accept = "accept" in vary_header.lower()

    try:
        status_md, headers_md, body_md = _fetch_url(
            norm_url,
            headers={"Accept": "text/markdown, text/x-markdown;q=0.9, text/plain;q=0.5"},
        )
        md_ct = headers_md.get("content-type", "").lower()
        negotiation_content_type = md_ct
        if status_md == 200 and ("text/markdown" in md_ct or "text/x-markdown" in md_ct):
            negotiation_supported = True
            negotiated_bytes = len(body_md)
        elif status_md == 200 and ("text/html" not in md_ct):
            # Check if body starts with markdown indicators
            md_snippet = body_md[:200].decode("utf-8", "replace").strip()
            if md_snippet.startswith(("---", "# ", "## ", "- ")):
                negotiation_supported = True
                negotiated_bytes = len(body_md)
    except Exception:
        pass

    # 5. Verify discovered mirror URL if found
    mirror_verified = False
    mirror_status = 0
    mirror_bytes = 0
    mirror_preview = ""
    if primary_mirror_url:
        try:
            m_status, m_headers, m_body = _fetch_url(primary_mirror_url)
            mirror_status = m_status
            if m_status == 200:
                mirror_verified = True
                mirror_bytes = len(m_body)
                mirror_preview = m_body[:300].decode("utf-8", "replace")
        except Exception:
            pass

    # Direct .md probe fallback if no link tag
    probed_md_url: Optional[str] = None
    probe_success = False
    if not primary_mirror_url and not negotiation_supported:
        probe_target = norm_url.rstrip("/") + ".md"
        try:
            p_status, _, p_body = _fetch_url(probe_target)
            if p_status == 200 and len(p_body) > 20:
                probed_md_url = probe_target
                probe_success = True
                mirror_bytes = len(p_body)
        except Exception:
            pass

    # Score calculation (0 - 100)
    score = 0
    if primary_mirror_url and mirror_verified:
        score += 50
    elif primary_mirror_url:
        score += 25
    elif probe_success:
        score += 30

    if negotiation_supported:
        score += 50
    elif has_vary_accept:
        score += 10

    recommendations: List[str] = []
    if not primary_mirror_url:
        recommendations.append(
            'Add <link rel="alternate" type="text/markdown" href="/path.md"> in HTML <head> for fast agent discovery.'
        )
    elif not mirror_verified:
        recommendations.append(f"Declared markdown mirror '{primary_mirror_url}' returned HTTP {mirror_status}; ensure endpoint is publicly accessible.")

    if not negotiation_supported:
        recommendations.append(
            "Enable content negotiation on your edge or CDN: serve markdown when incoming request contains 'Accept: text/markdown'."
        )
    if not has_vary_accept:
        recommendations.append("Ensure HTTP responses include 'Vary: Accept' header so caches don't serve HTML to markdown-requesting agents.")

    report = {
        "target_url": norm_url,
        "markdown_score": min(100, score),
        "link_tag_discovered": bool(primary_mirror_url),
        "primary_mirror_url": primary_mirror_url or probed_md_url,
        "mirror_verified": mirror_verified or probe_success,
        "mirror_size_bytes": mirror_bytes,
        "mirror_estimated_tokens": max(0, round(mirror_bytes / 4)),
        "content_negotiation_supported": negotiation_supported,
        "negotiated_content_type": negotiation_content_type,
        "vary_accept_header": has_vary_accept,
        "discovered_links": {
            "from_html_head": head_md_links,
            "from_http_headers": header_md_links,
        },
        "preview": mirror_preview[:200] if mirror_preview else None,
        "recommendations": recommendations,
    }
    out = json.dumps(report, indent=2)
    track_tool_call("audit_markdown_mirror", (time.perf_counter() - t0) * 1000, "success", 1, len(out))
    return out


@mcp.tool()
def audit_full_ai_readiness(url: str) -> str:
    """Compute a composite 0-100 GEO/AEO AI readiness score across robots.txt, llms.txt, and markdown parity.

    Combines crawler access policies (35%), structured knowledge availability (35%),
    and token-efficient markdown mirrors (30%) with a prioritized fix checklist.
    """
    t0 = time.perf_counter()
    try:
        norm_url = _normalize_url(url)
    except Exception as e:
        msg = str(e)
        track_tool_call("audit_full_ai_readiness", (time.perf_counter() - t0) * 1000, "error", 0, len(msg), cat="ValidationError", msg=msg)
        return json.dumps({"error": msg, "classification": "[INPUT_FIXABLE]"}, indent=2)

    # Run component audits
    robots_raw = audit_robots_for_ai(norm_url)
    llms_raw = validate_llms_txt(norm_url)
    mirror_raw = audit_markdown_mirror(norm_url)

    robots_data = json.loads(robots_raw)
    llms_data = json.loads(llms_raw)
    mirror_data = json.loads(mirror_raw)

    robots_score = int(robots_data.get("ai_readiness_score", 0))
    llms_score = int(llms_data.get("compliance_score", 0))
    mirror_score = int(mirror_data.get("markdown_score", 0))

    # Weighted calculation
    composite = round((robots_score * 0.35) + (llms_score * 0.35) + (mirror_score * 0.30))
    composite = max(0, min(100, composite))

    if composite >= 90:
        grade = "A+ / Highly AI-Ready"
    elif composite >= 75:
        grade = "A / AI Optimized"
    elif composite >= 50:
        grade = "B / Partially Ready"
    elif composite >= 25:
        grade = "C / Needs Attention"
    else:
        grade = "F / AI Blocked or Inaccessible"

    # Prioritized punchlist
    punchlist: List[Dict[str, str]] = []
    for r in robots_data.get("recommendations", []):
        punchlist.append({"priority": "P0 - Crawler Access", "action": r})
    for r in llms_data.get("recommendations", []):
        punchlist.append({"priority": "P1 - Structured Knowledge", "action": r})
    for r in mirror_data.get("recommendations", []):
        punchlist.append({"priority": "P2 - Markdown Mirroring", "action": r})

    report = {
        "url": norm_url,
        "composite_score": composite,
        "grade": grade,
        "breakdown": {
            "robots_ai_accessibility": {
                "score": robots_score,
                "weight": "35%",
                "contribution": round(robots_score * 0.35, 1),
                "allowed_agents": f"{robots_data.get('allowed_count', 0)}/{len(AI_USER_AGENTS)}",
                "verdict": robots_data.get("verdict"),
            },
            "llms_txt_compliance": {
                "score": llms_score,
                "weight": "35%",
                "contribution": round(llms_score * 0.35, 1),
                "has_llms_txt": llms_data.get("llms_txt", {}).get("valid", False),
                "has_llms_full": llms_data.get("llms_full_txt", {}).get("exists", False),
            },
            "markdown_mirror_parity": {
                "score": mirror_score,
                "weight": "30%",
                "contribution": round(mirror_score * 0.30, 1),
                "mirror_found": mirror_data.get("link_tag_discovered", False),
                "content_negotiation": mirror_data.get("content_negotiation_supported", False),
            },
        },
        "actionable_punchlist": punchlist,
    }
    out = json.dumps(report, indent=2)
    track_tool_call("audit_full_ai_readiness", (time.perf_counter() - t0) * 1000, "success", 1, len(out))
    return out


@mcp.tool()
def doctor() -> str:
    """Run diagnostic checks on network resolution, environment variables, and sample testbeds."""
    t0 = time.perf_counter()
    testbeds = [
        ("surendranb.com", "https://surendranb.com/robots.txt"),
        ("builditwithai.xyz", "https://builditwithai.xyz/robots.txt"),
        ("github_raw", "https://raw.githubusercontent.com/surendranb/llm-crawler-audit/main/skills/ai-robots-txt-playbook.md"),
    ]

    connectivity: Dict[str, Any] = {}
    for name, t_url in testbeds:
        t_start = time.perf_counter()
        try:
            status, _, body = _fetch_url(t_url, timeout=3.5)
            connectivity[name] = {
                "reachable": True,
                "status_code": status,
                "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
                "bytes": len(body),
            }
        except Exception as e:
            connectivity[name] = {
                "reachable": False,
                "error": str(e),
                "latency_ms": round((time.perf_counter() - t_start) * 1000, 1),
            }

    skills_found = _skills_list()
    skills_data = json.loads(skills_found)

    res = {
        "server": SERVER_NAME,
        "version": MCP_SERVER_VERSION,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "telemetry_opt_out": os.getenv("DO_NOT_TRACK") == "1" or os.getenv("MCP_TELEMETRY_OPT_OUT") == "1",
        "connectivity_tests": connectivity,
        "skills_discovered": skills_data.get("skills", []),
        "status": "healthy" if all(c.get("reachable") for c in connectivity.values()) else "degraded",
    }
    out = json.dumps(res, indent=2)
    track_tool_call("doctor", (time.perf_counter() - t0) * 1000, "success", 1, len(out))
    return out


@mcp.tool()
def skills_list() -> str:
    """List available AI crawler and AEO optimization playbooks."""
    return _skills_list()


@mcp.tool()
def skill_read(name: str) -> str:
    """Read a specific AI crawler, llms.txt, or markdown mirror playbook."""
    return _skill_read(name)


@mcp.tool()
def check_for_updates() -> str:
    """Check PyPI for newer versions of llm-crawler-audit and get upgrade instructions."""
    res = check_server_update(SERVER_NAME, MCP_SERVER_VERSION, force_check=True)
    return json.dumps(res, indent=2)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
