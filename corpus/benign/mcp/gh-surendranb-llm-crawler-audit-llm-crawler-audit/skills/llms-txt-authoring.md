# /llms.txt and /llms-full.txt Standard Authoring Guide

A reference manual for implementing the `llms.txt` and `llms-full.txt` standards (defined by [llmstxt.org](https://llmstxt.org)) to expose structured, token-efficient knowledge to AI models and agentic runtimes.

---

## 1. Specification Overview

`/llms.txt` is a curated Markdown document placed in the website root that serves as an executive briefing and index for Large Language Models.

### Required & Recommended Structure

```markdown
# <Site or Project Name>

> <Brief summary (1-2 sentences) describing the core identity, mission, and scope.>

## <Section Title: e.g. Documentation, Core Guides, APIs>

- [<Resource Title>](<url>): <Description of the resource and when an LLM should inspect it.>
- [<Another Resource>](<url>): <Concise summary.>

## Optional

- [<Secondary Resource>](<url>): <Resources that provide extended context if token budget allows.>
```

### Key Formatting Rules
1. **First Line**: Must be an H1 heading (`# Name`).
2. **Summary Blockquote**: A blockquote starting with `> ` directly under the title.
3. **Structured Markdown Links**: Bullet items with `[Title](url): Description`.
4. **Sections**: Organized with H2 headers (`## Section Name`).
5. **No HTML/Scripts**: Pure clean Markdown only.

---

## 2. /llms-full.txt Specification

While `/llms.txt` is an index (< 10 KB), `/llms-full.txt` provides the complete, consolidated knowledge base in a single file:
- **Target Size**: Under 500 KB (~50,000 to 100,000 tokens) for optimal context window utilization and prompt caching.
- **Content**: All primary documentation pages stitched together with clear markdown dividers (`---`).
- **Strip Non-Essential Elements**: Omit navigation bars, cookie banners, tracking scripts, and UI chrome.

---

## 3. Site Integration & Discovery

### HTTP Header Discovery
Link to your `llms.txt` file from HTTP response headers:
```http
Link: <https://example.com/llms.txt>; rel="describedby"
```

### Robots.txt Discovery Comment
```txt
# LLMs: https://example.com/llms.txt
```

### HTML Head Discovery Tag
```html
<link rel="describedby" href="/llms.txt" type="text/markdown">
```

---

## 4. Verification Checklist

- [ ] `/llms.txt` is served with HTTP 200 at the domain root
- [ ] Returns `Content-Type: text/markdown` or `text/plain`
- [ ] Begins with a single `# ` H1 heading
- [ ] Contains a blockquote summary (`> `)
- [ ] Contains at least 3 curated markdown links with URLs and descriptions
- [ ] `/llms-full.txt` exists and is under 500 KB
