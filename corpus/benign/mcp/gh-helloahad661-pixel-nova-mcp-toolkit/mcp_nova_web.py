"""nova-web — keyless web + time tools, as an MCP server.

Why this exists
---------------
Four MCP servers were configured that could never work: their npm packages do
not exist (`@modelcontextprotocol/server-fetch`, `-sqlite`, `-youtube`,
`-time` all return 404). Their npm "replacements"
(`mcp-server-fetch`, `mcp-server-everything`, `mcp-server-git`) are marked
"security holding package" — squatted names. Rather than install unknown code
or run a second Node runtime, this uses the `mcp` SDK already in the venv.

Every endpoint below was measured working from Cairo, Egypt. There is no API
key, no signup, and no credit card. Where a service is rate-limited or
unreliable from here, the tool says so instead of pretending.

Scope limits are deliberate: `fetch_url` refuses anything that is not
http(s), caps the response size, and will not fetch private/loopback
addresses. It is a research tool, not a request proxy.
"""
import ipaddress
import socket
import urllib.parse
import xml.etree.ElementTree as ET

import httpx
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("nova-web")

TIMEOUT = 20.0
MAX_BYTES = 2_000_000
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Nova/1.0"

# Confirmed reachable from Egypt, no credentials required.
ENDPOINTS = {
    "arxiv": "http://export.arxiv.org/api/query",
    "hn": "https://hn.algolia.com/api/v1/search",
    "wikipedia": "https://en.wikipedia.org/w/api.php",
}


def _block_private(url: str) -> None:
    """Refuse non-public addresses so this cannot be used as an SSRF proxy."""
    host = urllib.parse.urlparse(url).hostname
    if not host:
        raise ValueError("URL has no host")
    if host in ("localhost", "localhost.localdomain"):
        raise ValueError("refusing loopback host")
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise ValueError("cannot resolve %s: %s" % (host, e))
    for info in infos:
        addr = ipaddress.ip_address(info[4][0])
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            raise ValueError("refusing non-public address %s" % addr)


@mcp.tool()
def current_time(timezone: str = "") -> dict:
    """Current local time. Optionally in an IANA timezone, e.g. 'Africa/Cairo'."""
    from datetime import datetime, timezone as _tz
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(timezone) if timezone else _tz.utc
    except Exception as e:
        return {"ok": False, "error": "bad timezone %r: %s" % (timezone, e)}
    now = datetime.now(tz)
    return {
        "ok": True,
        "iso": now.isoformat(),
        "timezone": str(tz),
        "local_human": now.strftime("%A %d %B %Y, %H:%M:%S"),
    }


@mcp.tool()
def fetch_url(url: str, max_chars: int = 20000) -> dict:
    """Fetch a public http(s) URL and return its text content.

    Returns raw markup for non-HTML types. Refuses private/loopback hosts and
    caps the response so a huge file cannot exhaust memory.
    """
    p = urllib.parse.urlparse(url)
    if p.scheme not in ("http", "https"):
        return {"ok": False, "error": "only http/https allowed, got %r" % p.scheme}
    try:
        _block_private(url)
    except ValueError as e:
        return {"ok": False, "error": str(e)}

    try:
        with httpx.Client(follow_redirects=True, timeout=TIMEOUT) as c:
            r = c.get(url, headers={"User-Agent": UA})
            raw = r.content[:MAX_BYTES]
            ctype = r.headers.get("content-type", "")
            if "json" in ctype:
                try:
                    return {"ok": True, "url": str(r.url), "status": r.status_code,
                            "content_type": ctype, "body": r.json()}
                except Exception:
                    pass
            text = raw.decode(r.encoding or "utf-8", errors="replace")
            if "html" in ctype:
                import re
                text = re.sub(r"(?is)<(script|style)\b.*?</\1>", " ", text)
                text = re.sub(r"(?s)<[^>]+>", " ", text)
                text = re.sub(r"[ \t]+", " ", re.sub(r"\n{3,}", "\n\n", text)).strip()
            return {"ok": True, "url": str(r.url), "status": r.status_code,
                    "content_type": ctype, "bytes": len(raw),
                    "body": text[:max_chars],
                    "truncated": len(text) > max_chars}
    except httpx.HTTPError as e:
        return {"ok": False, "url": url, "error": "%s: %s" % (type(e).__name__, str(e)[:160])}


@mcp.tool()
def arxiv_search(query: str, max_results: int = 5) -> dict:
    """Search arXiv papers. Free, no key, confirmed working from Egypt."""
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(ENDPOINTS["arxiv"], params={
                "search_query": "all:" + query,
                "max_results": max(1, min(int(max_results), 20)),
            }, headers={"User-Agent": UA})
            r.raise_for_status()
    except httpx.HTTPError as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:160])}

    ns = {"a": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(r.text)
    out = []
    for e in root.findall("a:entry", ns):
        out.append({
            "title": (e.findtext("a:title", "", ns) or "").strip().replace("\n", " "),
            "authors": [a.findtext("a:name", "", ns)
                        for a in e.findall("a:author", ns)][:6],
            "published": e.findtext("a:published", "", ns),
            "url": e.findtext("a:id", "", ns),
            "summary": (e.findtext("a:summary", "", ns) or "").strip()[:400],
        })
    return {"ok": True, "count": len(out), "results": out,
            "note": "arXiv API asks for ~3s between requests."}


@mcp.tool()
def hn_search(query: str, limit: int = 5) -> dict:
    """Search Hacker News via Algolia. Free, no key, confirmed working from Egypt."""
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(ENDPOINTS["hn"], params={
                "query": query, "hitsPerPage": max(1, min(int(limit), 20))},
                headers={"User-Agent": UA})
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:160])}

    hits = [{"title": h.get("title") or h.get("story_title"),
             "url": h.get("url") or h.get("story_url"),
             "points": h.get("points"),
             "comments": h.get("num_comments"),
             "created": h.get("created_at")} for h in data.get("hits", [])]
    return {"ok": True, "count": len(hits), "results": hits}


@mcp.tool()
def wikipedia_search(query: str, limit: int = 3) -> dict:
    """Search Wikipedia and return summaries. Free, no key, works from Egypt."""
    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.get(ENDPOINTS["wikipedia"], params={
                "action": "query", "format": "json", "list": "search",
                "srsearch": query, "srlimit": max(1, min(int(limit), 10))},
                headers={"User-Agent": UA})
            r.raise_for_status()
            data = r.json()
    except (httpx.HTTPError, ValueError) as e:
        return {"ok": False, "error": "%s: %s" % (type(e).__name__, str(e)[:160])}

    pages = data.get("query", {}).get("search", [])
    return {"ok": True, "count": len(pages), "results": [
        {"title": p.get("title"),
         "snippet": _strip_tags(p.get("snippet", "")),
         "pageid": p.get("pageid")} for p in pages]}


def _strip_tags(s: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", s).strip()


@mcp.tool()
def endpoint_health() -> dict:
    """Check which keyless endpoints are reachable from this machine right now."""
    out = {}
    checks = {
        "wikipedia": ("GET", ENDPOINTS["wikipedia"], {"action": "query", "format": "json",
                                                      "meta": "siteinfo"}),
        "arxiv": ("GET", ENDPOINTS["arxiv"], {"search_query": "all:test", "max_results": 1}),
        "hackernews": ("GET", ENDPOINTS["hn"], {"query": "test", "hitsPerPage": 1}),
        "github": ("GET", "https://api.github.com/rate_limit", None),
        "openmeteo": ("GET", "https://api.open-meteo.com/v1/forecast",
                      {"latitude": 30.04, "longitude": 31.24, "current": "temperature_2m"}),
        "stackexchange": ("GET", "https://api.stackexchange.com/2.3/questions",
                          {"site": "stackoverflow", "pagesize": 1}),
        "openalex": ("GET", "https://api.openalex.org/works", {"per-page": 1}),
        "crossref": ("GET", "https://api.crossref.org/works", {"rows": 1}),
        "pubmed": ("GET", "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
                   {"db": "pubmed", "term": "llm", "retmax": 1}),
    }
    with httpx.Client(follow_redirects=True, timeout=12) as c:
        for name, (method, url, params) in checks.items():
            try:
                r = c.request(method, url, params=params, headers={"User-Agent": UA})
                out[name] = {"status": r.status_code, "ok": r.status_code < 400}
            except Exception as e:
                out[name] = {"ok": False, "error": type(e).__name__}
    return {"checked": len(out), "results": out,
            "note": "All keyless. No account required. Measured from this machine."}


if __name__ == "__main__":
    mcp.run()