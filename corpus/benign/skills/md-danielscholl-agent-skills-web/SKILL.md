---
name: web
description: "Search the web using Brave Search API and fetch page content with HTML-to-markdown conversion. Use when user needs current information, online documentation, or specific URL content beyond knowledge cutoff."
version: 1.0.0
brief_description: "Web search and page fetching with Brave API"
triggers:
  keywords: [web, search, internet, online, fetch, url, webpage, website, current, recent, latest, news, documentation, brave]
  verbs: [search, fetch, get, find, lookup, retrieve]
  patterns:
    - "https?://"
    - "www\\."
    - "search.*for"
    - "look.*up"
    - "find.*information"
    - "current.*(?:news|info|data)"
    - "recent.*(?:news|info|data)"
allowed-tools: Bash, WebFetch, WebSearch
---

# web

## 🎯 Triggers
**When user wants to:**
- Search the internet
- Get current/recent information
- Fetch content from a URL
- Access online documentation

**Skip when:**
- Answer is within knowledge cutoff
- Local file operation

## Scripts

### search
**What:** Search the web using Brave Search API
**Pattern:** User wants to search → `script_run web search --query "USER_QUERY" --json`
**Example:** "Search for python tutorials" → `script_run web search --query "python tutorials" --json`

### fetch
**What:** Fetch and convert web page to markdown
**Pattern:** User provides URL → `script_run web fetch --url "USER_URL" --json`
**Example:** "Get https://example.com" → `script_run web fetch --url "https://example.com" --json`

## Quick Reference
```
User: "Search for X"          → script_run web search --query "X" --json
User: "Fetch https://..."     → script_run web fetch --url "https://..." --json
User: "Find recent news on X" → script_run web search --query "X news" --json
```

## Requires
- `BRAVE_API_KEY` environment variable for search
