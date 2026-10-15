"""
WikiPeatia MCP Server -- Ray Peat bioenergetic health wiki + full corpus search.

Data sources (all public, no API key required):
  1. MediaWiki API (https://wikipeatia.org/w/api.php) -- wiki pages, categories,
     Library namespace (Ray Peat's books / newsletters / canonical texts).
  2. WikiPeatia Search API (https://search.wikipeatia.org/api/*) -- hybrid search
     (full-text + semantic embeddings + LLM Q&A) over the entire Ray Peat corpus:
     articles, books, interviews, newsletters, forum posts, email Q&A, wiki pages.
     ~7,000 documents / ~220,000 text chunks.
  3. raypeat.com -- Ray Peat's original articles (fetched on demand).

Read-only. Unofficial community project; the data belongs to the respective sources.
"""
from __future__ import annotations

__version__ = "1.0.0"

import os
import re
from typing import Any
from urllib.parse import quote

import httpx
from fastmcp import FastMCP

mcp = FastMCP("wikipeatia")

# -- Wiki (MediaWiki) ---------------------------------------------------
API_BASE = "https://wikipeatia.org/w/api.php"
TIMEOUT = float(os.getenv("WIKIPEATIA_TIMEOUT", "30"))
DEEP_TIMEOUT = float(os.getenv("WIKIPEATIA_DEEP_TIMEOUT", "120"))

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# -- Search API ----------------------------------------------------------
SEARCH_BASE = "https://search.wikipeatia.org"


def _api(params: dict[str, Any]) -> dict[str, Any]:
    """Call the MediaWiki API with params, return JSON."""
    with httpx.Client(timeout=TIMEOUT, headers=HEADERS) as client:
        r = client.get(API_BASE, params={**params, "format": "json"})
        r.raise_for_status()
        return r.json()


def _search_api(path: str, params: dict[str, Any] | None = None,
                timeout: float | None = None) -> dict[str, Any]:
    """Call the search.wikipeatia.org API."""
    with httpx.Client(timeout=timeout or TIMEOUT, headers=HEADERS) as client:
        r = client.get(f"{SEARCH_BASE}{path}", params=params or {})
        r.raise_for_status()
        return r.json()


# ===========================================
# Wiki: search
# ===========================================

@mcp.tool
def wiki_search(query: str, limit: int = 10) -> dict[str, Any]:
    """Search wiki pages by title or content (MediaWiki search).

    Note: this is the wiki's built-in search; multi-word queries may return
    zero hits. For the full corpus (interviews, books, ...) use corpus_search.

    Args:
        query: Search term (e.g. 'thyroid', 'PUFA', 'aspirin')
        limit: Max results (default 10)
    """
    data = _api({
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": min(limit, 50),
        "srprop": "snippet|titlesnippet",
    })
    results = []
    for r in data.get("query", {}).get("search", []):
        results.append({
            "title": r["title"],
            "pageid": r["pageid"],
            "snippet": _strip_html(r.get("snippet", "")),
            "url": f"https://wikipeatia.org/wiki/{quote(r['title'].replace(' ', '_'))}",
        })
    return {
        "query": query,
        "total_hits": data.get("query", {}).get("searchinfo", {}).get("totalhits", 0),
        "results": results,
    }


@mcp.tool
def wiki_get_page(title: str, format: str = "wikitext") -> dict[str, Any]:
    """Get the raw content of a wiki page.

    Args:
        title: Page title (e.g. 'Thyroid', 'PUFA', 'Ray_Peat',
               'Library:Thyroid' -- Library namespace is accepted too)
        format: 'wikitext' (raw wiki markup) or 'html' (rendered HTML)
    """
    if format == "html":
        data = _api({
            "action": "parse",
            "page": title,
            "prop": "text",
            "disablelimitreport": "1",
        })
        parsed = data.get("parse", {})
        return {
            "title": parsed.get("title", title),
            "pageid": parsed.get("pageid"),
            "format": "html",
            "text": parsed.get("text", {}).get("*", ""),
            "url": f"https://wikipeatia.org/wiki/{quote(title.replace(' ', '_'))}",
        }
    else:
        data = _api({
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": title,
        })
        pages = data.get("query", {}).get("pages", {})
        for pid, page in pages.items():
            if pid == "-1":
                return {"error": f"Page not found: {title}", "title": title}
            revs = page.get("revisions", [{}])
            return {
                "title": page["title"],
                "pageid": page["pageid"],
                "format": "wikitext",
                "text": revs[0].get("slots", {}).get("main", {}).get("*", ""),
                "url": f"https://wikipeatia.org/wiki/{quote(page['title'].replace(' ', '_'))}",
            }
        return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_get_page_summary(title: str) -> dict[str, Any]:
    """Get the first paragraph (intro extract) of a wiki page. Fast overview.

    Args:
        title: Page title
    """
    data = _api({
        "action": "query",
        "prop": "extracts",
        "exintro": "1",
        "explaintext": "1",
        "exlimit": "1",
        "titles": title,
    })
    pages = _pages_dict(data)
    for pid, page in pages.items():
        if pid == "-1":
            return {"error": f"Page not found: {title}", "title": title}
        return {
            "title": page["title"],
            "pageid": page["pageid"],
            "summary": page.get("extract", ""),
            "url": f"https://wikipeatia.org/wiki/{quote(page['title'].replace(' ', '_'))}",
        }
    return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_read(title: str, section: int = 0) -> dict[str, Any]:
    """Read a wiki page as plain text. With a section number, only that section.

    Args:
        title: Page title (e.g. 'Thyroid', 'PUFA', 'Library:Thyroid')
        section: 0 = whole page, N = only section N (list sections with
                 wiki_get_page_sections)
    """
    params: dict[str, Any] = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "exsectionformat": "wiki",
        "titles": title,
    }
    if section > 0:
        params["exsection"] = str(section)

    data = _api(params)
    pages = _pages_dict(data)
    for pid, page in pages.items():
        if pid == "-1":
            return {"error": f"Page not found: {title}", "title": title}
        text = page.get("extract", "")
        return {
            "title": page["title"],
            "pageid": page["pageid"],
            "section": section if section > 0 else "all",
            "text": text,
            "length_chars": len(text),
            "url": f"https://wikipeatia.org/wiki/{quote(page['title'].replace(' ', '_'))}",
        }
    return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_suggest(query: str) -> dict[str, Any]:
    """Autocomplete wiki page titles while typing.

    Args:
        query: Partial search term (e.g. 'thyr', 'asp')
    """
    import urllib.request as _ur
    url = f"https://wikipeatia.org/w/api.php?action=opensearch&search={quote(query)}&limit=10&format=json"
    r = _ur.urlopen(_ur.Request(url, headers=HEADERS))
    import json as _json
    data = _json.loads(r.read())
    # OpenSearch returns [query, [titles], [descriptions], [urls]]
    suggestions = []
    if len(data) >= 2:
        for i, title in enumerate(data[1]):
            item = {"title": title}
            if len(data) > 2 and i < len(data[2]):
                item["description"] = data[2][i]
            if len(data) > 3 and i < len(data[3]):
                item["url"] = data[3][i]
            suggestions.append(item)
    return {"query": query, "suggestions": suggestions}


# ===========================================
# Wiki: categories, index, discovery
# ===========================================

@mcp.tool
def wiki_list_categories(limit: int = 50) -> dict[str, Any]:
    """List all categories on the wiki."""
    data = _api({
        "action": "query",
        "list": "allcategories",
        "aclimit": min(limit, 500),
        "acprop": "size",
    })
    cats = []
    for c in data.get("query", {}).get("allcategories", []):
        cats.append({
            "category": c["*"],
            "pages": c.get("size", 0),
        })
    return {"total": len(cats), "categories": cats}


@mcp.tool
def wiki_get_category_members(category: str, limit: int = 50) -> dict[str, Any]:
    """List all pages in a category.

    Args:
        category: Category name (e.g. 'Hormones', 'Vitamins', 'Substances')
        limit: Max results
    """
    data = _api({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": min(limit, 500),
        "cmtype": "page",
    })
    members = []
    for m in data.get("query", {}).get("categorymembers", []):
        members.append({
            "title": m["title"],
            "pageid": m["pageid"],
            "url": f"https://wikipeatia.org/wiki/{quote(m['title'].replace(' ', '_'))}",
        })
    return {
        "category": category,
        "total": len(members),
        "members": members,
    }


@mcp.tool
def wiki_list_all_pages(prefix: str = "", limit: int = 50) -> dict[str, Any]:
    """List all wiki pages alphabetically, optionally filtered by prefix.

    Args:
        prefix: Page-title prefix (e.g. 'Roadmap' to list Roadmap pages)
        limit: Max results
    """
    params: dict[str, Any] = {
        "action": "query",
        "list": "allpages",
        "aplimit": min(limit, 500),
    }
    if prefix:
        params["apprefix"] = prefix

    data = _api(params)
    pages = []
    for p in data.get("query", {}).get("allpages", []):
        pages.append({
            "title": p["title"],
            "pageid": p["pageid"],
            "url": f"https://wikipeatia.org/wiki/{quote(p['title'].replace(' ', '_'))}",
        })
    return {
        "prefix": prefix or "(all)",
        "total": len(pages),
        "pages": pages,
    }


@mcp.tool
def wiki_list_library(limit: int = 50) -> dict[str, Any]:
    """List all pages in the Library namespace ('Library:<title>').

    Ray Peat's books / newsletters / canonical texts live here.
    Read one with wiki_read('Library:01 Radiation And Growth', ...).

    Args:
        limit: Max results
    """
    data = _api({
        "action": "query",
        "list": "allpages",
        "aplimit": min(limit, 500),
        "apnamespace": "3000",
    })
    pages = []
    for p in data.get("query", {}).get("allpages", []):
        pages.append({
            "title": p["title"],
            "pageid": p["pageid"],
            "url": f"https://wikipeatia.org/wiki/{quote(p['title'].replace(' ', '_'))}",
        })
    return {"total": len(pages), "pages": pages}


# ===========================================
# Wiki: page meta / links / changes
# ===========================================

@mcp.tool
def wiki_get_page_categories(title: str) -> dict[str, Any]:
    """Show which categories a page belongs to.

    Args:
        title: Page title
    """
    data = _api({
        "action": "query",
        "prop": "categories",
        "cllimit": "max",
        "titles": title,
    })
    pages = _pages_dict(data)
    for pid, page in pages.items():
        if pid == "-1":
            return {"error": f"Page not found: {title}"}
        cats = []
        for c in page.get("categories", []):
            name = c["title"].replace("Category:", "")
            cats.append(name)
        return {
            "title": page["title"],
            "pageid": page["pageid"],
            "categories": cats,
            "url": f"https://wikipeatia.org/wiki/{quote(page['title'].replace(' ', '_'))}",
        }
    return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_get_page_links(title: str, limit: int = 50) -> dict[str, Any]:
    """List the wiki links contained in a page (related-topic discovery).

    Args:
        title: Page title
        limit: Max links
    """
    data = _api({
        "action": "query",
        "prop": "links",
        "pllimit": min(limit, 500),
        "titles": title,
    })
    pages = _pages_dict(data)
    for pid, page in pages.items():
        if pid == "-1":
            return {"error": f"Page not found: {title}"}
        links = [l["title"] for l in page.get("links", [])]
        return {
            "title": page["title"],
            "total": len(links),
            "links": links,
        }
    return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_get_backlinks(title: str, limit: int = 50) -> dict[str, Any]:
    """Which pages link to this page? (reverse link map)

    Args:
        title: Page title
        limit: Max results
    """
    data = _api({
        "action": "query",
        "list": "backlinks",
        "bltitle": title,
        "bllimit": min(limit, 500),
    })
    backlinks = []
    for b in data.get("query", {}).get("backlinks", []):
        backlinks.append({
            "title": b["title"],
            "pageid": b["pageid"],
            "url": f"https://wikipeatia.org/wiki/{quote(b['title'].replace(' ', '_'))}",
        })
    return {
        "title": title,
        "total": len(backlinks),
        "backlinks": backlinks,
    }


@mcp.tool
def wiki_get_page_sections(title: str) -> dict[str, Any]:
    """List a page's section headings (table of contents).

    Args:
        title: Page title
    """
    data = _api({
        "action": "parse",
        "page": title,
        "prop": "sections",
    })
    parsed = data.get("parse", {})
    sections = []
    for s in parsed.get("sections", []):
        sections.append({
            "level": int(s.get("level", s.get("toclevel", 1))),
            "line": s["line"],
            "anchor": s.get("anchor", ""),
            "index": s.get("index", ""),
        })
    return {
        "title": parsed.get("title", title),
        "pageid": parsed.get("pageid"),
        "total_sections": len(sections),
        "sections": sections,
    }


@mcp.tool
def wiki_get_page_info(title: str) -> dict[str, Any]:
    """Page metadata: last edit, length, last revision id, URLs.

    Args:
        title: Page title
    """
    data = _api({
        "action": "query",
        "prop": "info",
        "inprop": "url|displaytitle|length",
        "titles": title,
    })
    pages = _pages_dict(data)
    for pid, page in pages.items():
        if pid == "-1":
            return {"error": f"Page not found: {title}"}
        return {
            "title": page["title"],
            "pageid": page["pageid"],
            "length_bytes": page.get("length"),
            "last_touched": page.get("touched"),
            "last_revision_id": page.get("lastrevid"),
            "content_model": page.get("contentmodel"),
            "page_language": page.get("pagelanguage"),
            "full_url": page.get("fullurl"),
            "canonical_url": page.get("canonicalurl"),
        }
    return {"error": f"Page not found: {title}"}


@mcp.tool
def wiki_get_random(count: int = 1) -> dict[str, Any]:
    """Get random wiki page(s). Great for exploration.

    Args:
        count: How many random pages (1-10)
    """
    data = _api({
        "action": "query",
        "list": "random",
        "rnlimit": min(count, 10),
        "rnnamespace": "0",  # main namespace
    })
    pages = []
    for r in data.get("query", {}).get("random", []):
        pages.append({
            "title": r["title"],
            "pageid": r["id"],
            "url": f"https://wikipeatia.org/wiki/{quote(r['title'].replace(' ', '_'))}",
        })
    return {"count": len(pages), "pages": pages}


@mcp.tool
def wiki_get_recent_changes(limit: int = 10) -> dict[str, Any]:
    """List recent edits on the wiki.

    Args:
        limit: Max results (1-50)
    """
    data = _api({
        "action": "query",
        "list": "recentchanges",
        "rclimit": min(limit, 50),
        "rcprop": "title|timestamp|user|comment|sizes",
        "rctype": "edit|new",
    })
    changes = []
    for r in data.get("query", {}).get("recentchanges", []):
        changes.append({
            "title": r["title"],
            "pageid": r["pageid"],
            "timestamp": r["timestamp"],
            "user": r.get("user", "?"),
            "comment": r.get("comment", ""),
            "old_size": r.get("oldlen", 0),
            "new_size": r.get("newlen", 0),
            "url": f"https://wikipeatia.org/wiki/{quote(r['title'].replace(' ', '_'))}",
        })
    return {"total": len(changes), "changes": changes}


@mcp.tool
def wiki_get_site_stats() -> dict[str, Any]:
    """Wiki statistics: pages, edits, users, files."""
    data = _api({
        "action": "query",
        "meta": "siteinfo",
        "siprop": "statistics|general",
    })
    stats = data.get("query", {}).get("statistics", {})
    general = data.get("query", {}).get("general", {})
    return {
        "sitename": general.get("sitename"),
        "generator": general.get("generator"),
        "total_pages": stats.get("pages"),
        "total_articles": stats.get("articles"),
        "total_edits": stats.get("edits"),
        "total_images": stats.get("images"),
        "total_users": stats.get("users"),
        "active_users": stats.get("activeusers"),
        "url": general.get("server"),
    }


# ===========================================
# Search API -- full corpus (articles, books,
# interviews, newsletters, forum, email Q&A)
# ===========================================

def _apply_filters(params: dict[str, Any], doc_type: str = "", author: str = "",
                   series: str = "", ray_only: bool | None = None,
                   include_extended: bool = True) -> dict[str, Any]:
    """Add shared corpora filters to a params dict."""
    if doc_type:
        params["doc_type"] = doc_type
    if series:
        params["series"] = series
    authors = [a.strip() for a in author.split(",") if a.strip()]
    if authors:
        params["author"] = authors if len(authors) > 1 else authors[0]
    if ray_only is not None:
        params["ray_only"] = "true" if ray_only else "false"
    if include_extended:
        params["include_extended"] = "true"
    return params


@mcp.tool
def corpus_health() -> dict[str, Any]:
    """Status and stats of the corpus search infrastructure.

    Returns:
        mode (hybrid), semantic_live (embedding search online),
        chunk_count, doc_count
    """
    return _search_api("/api/health")


@mcp.tool
def corpus_search(query: str, limit: int = 10, doc_type: str = "",
                  author: str = "", series: str = "",
                  ray_only: bool | None = None,
                  include_extended: bool = True) -> dict[str, Any]:
    """Full-text search across the entire Ray Peat corpus.

    Covers articles, books (Library), interviews (audio transcripts),
    newsletters, forum posts, email Q&A and wiki pages. Results include
    excerpt, doc_id, doc_type, author, series, source_url, audio_url and
    timestamps (for interviews).

    Args:
        query: Search terms (e.g. 'PUFA detoxification', 'cortisol', 'milk protein')
        limit: Max results (max 50)
        doc_type: Optional type filter: article, book, interview, newsletter,
                  forum_thread, email_qa, blog_post, wiki_article, lecture,
                  thesis, patent... (see corpus_list_doc_types)
        author: Optional author filter, comma-separated for several
                (e.g. 'Ray Peat' or 'Ray Peat,Georgi Dinkov (Haidut)').
                See corpus_list_authors for exact names.
        series: Optional series/collection filter (e.g. 'Ask the Herb Doctor',
                'Generative Energy'). See corpus_list_series.
        ray_only: Optional scope: true = Ray Peat's own materials only;
                  false = whole corpus (all authors); omit for the server
                  default scope (Ray Peat-focused).
        include_extended: true = include extra fields (audio_url, timestamps...)
    """
    params: dict[str, Any] = {"q": query, "limit": min(limit, 50)}
    _apply_filters(params, doc_type, author, series, ray_only, include_extended)
    data = _search_api("/api/search", params)
    data["query"] = query
    return data


@mcp.tool
def corpus_semantic_search(query: str, limit: int = 10, doc_type: str = "",
                           author: str = "", series: str = "",
                           ray_only: bool | None = None,
                           include_extended: bool = True) -> dict[str, Any]:
    """Semantic (embedding) search over the corpus.

    Finds passages close in meaning even without exact keyword matches;
    also returns glossary_terms (synonyms/concepts found for the query).

    Args:
        query: Natural-language query (e.g. 'cortisol metabolism', 'stress effects')
        limit: Max results (max 50)
        doc_type / author / series / ray_only: same filters as corpus_search
        include_extended: true = include extra fields
    """
    params: dict[str, Any] = {"q": query, "limit": min(limit, 50)}
    _apply_filters(params, doc_type, author, series, ray_only, include_extended)
    data = _search_api("/api/semantic", params, timeout=DEEP_TIMEOUT)
    data["query"] = query
    return data


@mcp.tool
def corpus_ask(question: str) -> dict[str, Any]:
    """Quick LLM-grounded answer over the corpus (fast, roughly 2-10 s).

    Returns a short synthesized answer with a confidence value and the
    cited chunks. For deep multi-source research with [S1][S2] citations,
    use corpus_deep_ask instead.

    Args:
        question: Natural-language question (e.g. 'What does Ray Peat say about aspirin?')
    """
    data = _search_api("/api/ask", {"q": question}, timeout=DEEP_TIMEOUT)
    data["question"] = question
    return data


@mcp.tool
def corpus_deep_ask(question: str) -> dict[str, Any]:
    """Deep, LLM-assisted question answering over the entire corpus.

    Synthesizes across all ~220K chunks; the answer carries [S1], [S2]...
    source markers. Open the underlying documents with corpus_get_doc(doc_id).

    Note: this endpoint is slow (30-120 s). Ask one question at a time.

    Args:
        question: e.g. 'How does PUFA detoxification work?',
                  'What causes hypothyroidism according to Ray Peat?'
    """
    data = _search_api("/api/ask/deep", {"q": question}, timeout=DEEP_TIMEOUT)
    data["question"] = question
    return data


@mcp.tool
def corpus_suggest(query: str) -> dict[str, Any]:
    """Corpus autocomplete: term and document (doc_id) suggestions.

    Args:
        query: Partial query (e.g. 'thyr', 'aspir')
    """
    return _search_api("/api/suggest", {"q": query})


@mcp.tool
def corpus_get_doc(doc_id: str, max_chars_per_chunk: int = 3000) -> dict[str, Any]:
    """Fetch a document's full content (chunk by chunk).

    Interview chunks carry speaker and timestamp_start fields; use
    audio_url / source_url to reach the audio source.

    Args:
        doc_id: Document id (e.g. 'wikiwiki-thyroid',
                'rw-articles-lactate-vs-co2-...', 'email:Thyroid')
                -- from corpus_search / corpus_suggest results.
        max_chars_per_chunk: Max characters returned per chunk
                             (0 = no limit; can be huge)
    """
    data = _search_api(f"/api/doc/{quote(doc_id)}")
    chunks = data.get("chunks", [])
    if max_chars_per_chunk > 0:
        total_chars = 0
        trimmed = 0
        for c in chunks:
            total_chars += len(c.get("text", ""))
            if len(c.get("text", "")) > max_chars_per_chunk:
                c["text"] = c["text"][:max_chars_per_chunk] + "\n...[truncated]"
                trimmed += 1
        data["full_text_chars"] = total_chars
        data["trimmed_chunks"] = trimmed
    return data


@mcp.tool
def corpus_list_doc_types() -> dict[str, Any]:
    """Document types and counts in the corpus (article, book, interview, ...).

    Usable as the doc_type filter in corpus_search.
    """
    return _search_api("/api/doc-types")


@mcp.tool
def corpus_list_authors(extended_only: bool = True) -> dict[str, Any]:
    """Authors in the corpus and their document counts.

    Args:
        extended_only: true = detailed version with the full list
    """
    params = {}
    if extended_only:
        params["extended_only"] = "true"
    return _search_api("/api/authors", params)


@mcp.tool
def corpus_list_series() -> dict[str, Any]:
    """Series / collections in the corpus (e.g. 'One Radio Network',
    'Ray Peat Newsletter', 'Ask the Herb Doctor').

    Matches the 'series' field in corpus_search results; usable as a filter.
    """
    return _search_api("/api/series")


@mcp.tool
def corpus_library(series: str = "", limit: int = 50,
                   extended: bool = False) -> dict[str, Any]:
    """Browse the corpus library (metadata list). For content use corpus_get_doc.

    Args:
        series: Optional series filter (e.g. 'Ask the Herb Doctor')
        limit: Max results
        extended: include extended entries
    """
    params: dict[str, Any] = {"limit": min(limit, 500)}
    if series:
        params["series"] = series
    if extended:
        params["extended"] = "true"
    return _search_api("/api/library", params)


@mcp.tool
def corpus_topics() -> dict[str, Any]:
    """List the corpus's topic tags (e.g. 'thyroid', 'pufa', 'cortisol').

    Useful to see what themes the corpus is organized around.
    """
    data = _search_api("/api/topics")
    if isinstance(data, list):
        return {"total": len(data), "topics": data}
    return data


# ===========================================
# Ray Peat original articles (raypeat.com)
# ===========================================

RAYPEAT_BASE = "https://raypeat.com"
RAYPEAT_HEADERS = {
    "User-Agent": "RayPeatMCP/1.0",
    "Accept": "text/html",
}


def _scrape(url: str) -> str:
    """Scrape a raypeat.com page and return text content."""
    import urllib.request as _ur
    r = _ur.urlopen(_ur.Request(url, headers={**HEADERS, "Accept": "text/html"}))
    html = r.read().decode("utf-8", errors="replace")

    # Remove scripts, styles, nav
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=re.DOTALL | re.IGNORECASE)

    # Simple tag stripping
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'</p>', '\n\n', text)
    text = re.sub(r'</h\d>', '\n\n', text)
    text = re.sub(r'</li>', '\n', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'&nbsp;', ' ', text)
    text = re.sub(r'&amp;', '&', text)
    text = re.sub(r'&lt;', '<', text)
    text = re.sub(r'&gt;', '>', text)
    text = re.sub(r'&quot;', '"', text)

    # Collapse whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    return text.strip()


@mcp.tool
def raypeat_list_articles() -> dict[str, Any]:
    """List all of Ray Peat's articles on raypeat.com.

    Returns:
        Article list with titles and URLs.
    """
    url = f"{RAYPEAT_BASE}/articles/"
    import urllib.request as _ur
    r = _ur.urlopen(_ur.Request(url, headers=RAYPEAT_HEADERS))
    html = r.read().decode("utf-8", errors="replace")

    # Extract all article links
    links = re.findall(
        r'<a\s+href="(/articles/[^"]+)"[^>]*>([^<]+)</a>',
        html, re.DOTALL
    )

    articles = []
    seen = set()
    for path, title in links:
        title = re.sub(r'\s+', ' ', title).strip()
        # Skip non-article links and duplicates
        if not title or len(title) < 5:
            continue
        if path in seen:
            continue
        seen.add(path)
        # Skip the article index itself and non-article paths
        if path in ("/articles/", "/articles/index.shtml"):
            continue
        articles.append({
            "title": title,
            "path": path,
            "url": f"{RAYPEAT_BASE}{path}",
        })

    return {
        "total": len(articles),
        "source": "raypeat.com/articles/",
        "articles": articles,
    }


@mcp.tool
def raypeat_read_article(path: str) -> dict[str, Any]:
    """Read one of Ray Peat's articles as full text.

    Args:
        path: Article path (e.g. '/articles/articles/glucose-sucrose-diabetes.shtml'
              or '/articles/articles/unsaturatedfats.shtml')

    Get the list first with raypeat_list_articles, then read by path.
    """
    if not path.startswith("/articles/"):
        return {"error": "Invalid path: must start with '/articles/'."}

    url = f"{RAYPEAT_BASE}{path}"
    text = _scrape(url)

    # Try to extract title from the file name
    title = path.rsplit("/", 1)[-1].replace(".shtml", "").replace(".html", "").replace("-", " ").title()

    return {
        "title": title,
        "path": path,
        "url": url,
        "text": text,
        "length_chars": len(text),
    }


@mcp.tool
def raypeat_search_articles(query: str) -> dict[str, Any]:
    """Keyword search across Ray Peat article titles.

    Args:
        query: Term to look for (e.g. 'thyroid', 'diabetes', 'progesterone')

    Note: for full-corpus search (other sources included) corpus_search is stronger.
    """
    # First get all articles
    import urllib.request as _ur

    list_url = f"{RAYPEAT_BASE}/articles/"
    r = _ur.urlopen(_ur.Request(list_url, headers=RAYPEAT_HEADERS))
    html = r.read().decode("utf-8", errors="replace")

    links = re.findall(
        r'<a\s+href="(/articles/[^"]+)"[^>]*>([^<]+)</a>',
        html, re.DOTALL
    )

    query_lower = query.lower()
    matches = []
    seen = set()

    for path, title in links:
        title_clean = re.sub(r'\s+', ' ', title).strip()
        if not title_clean or len(title_clean) < 5:
            continue
        if path in seen:
            continue
        seen.add(path)
        if path in ("/articles/", "/articles/index.shtml"):
            continue

        if query_lower in title_clean.lower():
            matches.append({
                "title": title_clean,
                "path": path,
                "url": f"{RAYPEAT_BASE}{path}",
            })

    return {
        "query": query,
        "total_matches": len(matches),
        "articles": matches,
    }


def _strip_html(text: str) -> str:
    """Strip HTML tags in a lightweight way."""
    return re.sub(r"<[^>]+>", "", text).strip()


def _pages_dict(data: dict[str, Any]) -> dict[str, Any]:
    """Extract the pages dict from a query result."""
    return data.get("query", {}).get("pages", {})


def main() -> None:
    """Run the server over stdio (how MCP clients launch it)."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
