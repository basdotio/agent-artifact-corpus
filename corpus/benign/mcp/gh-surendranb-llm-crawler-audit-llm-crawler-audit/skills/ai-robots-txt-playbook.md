# AI Search & LLM Crawler robots.txt Playbook

A comprehensive guide to configuring RFC 9309 compliant `robots.txt` directives for AI search engines, answer bots, and model training crawlers.

---

## 1. The Modern AI Crawler Landscape

AI crawlers fall into two distinct operational categories:
1. **AI Search & Retrieval Bots**: Power live web grounding, RAG (Retrieval-Augmented Generation), citations, and real-time user queries in ChatGPT Search, Claude, Perplexity, and Apple Intelligence.
2. **Model Training & Corpus Crawlers**: Scrape large-scale web corpora for foundational model pre-training and fine-tuning.

### The 9 Critical AI User-Agents

| User-Agent | Operator | Primary Role | Business Impact |
|---|---|---|---|
| `GPTBot` | OpenAI | Corpus training & ChatGPT Search indexing | High citation & training footprint |
| `ChatGPT-User` | OpenAI | Live user-directed browsing & real-time search | Direct citations & click-through referrals |
| `ClaudeBot` | Anthropic | Web crawling for Claude products | Direct citation & answers in Claude |
| `anthropic-ai` | Anthropic | Legacy/training crawler identifier | Anthropic model training |
| `PerplexityBot` | Perplexity AI | Real-time search indexer | Perplexity search citations & source cards |
| `Applebot-Extended` | Apple | Apple Intelligence training & Siri answers | Apple ecosystem visibility |
| `Bytespider` | ByteDance | TikTok / Douyin AI search & LLM training | High crawl velocity |
| `Google-Extended` | Google | Gemini & Vertex AI training (separate from Googlebot) | Google AI training opt-out control |
| `CCBot` | Common Crawl | Open web dataset for open-weights models | Training data for Llama, Mistral, etc. |

---

## 2. Standard Archetypes & Configurations

### Archetype A: Maximum AI Search & Citation Readiness (Recommended)
Allow all AI search engines and training crawlers to index content, link to `llms.txt`, and discover sitemaps.

```txt
User-agent: *
Allow: /

# Explicit AI Search & Answer Agents
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

User-agent: Applebot-Extended
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: CCBot
Allow: /

# Machine-readable discovery
Sitemap: https://example.com/sitemap.xml
# LLMs: https://example.com/llms.txt
```

### Archetype B: Search & Citation Only (Block Model Training)
Permit real-time search indexers to cite your domain in AI chat interfaces, while blocking bulk corpus training scrapers.

```txt
User-agent: *
Allow: /

# Allow Search & Retrieval Crawlers (Citations & Traffic)
User-agent: ChatGPT-User
Allow: /

User-agent: ClaudeBot
Allow: /

User-agent: PerplexityBot
Allow: /

# Block Corpus Training Crawlers
User-agent: Google-Extended
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: Bytespider
Disallow: /

Sitemap: https://example.com/sitemap.xml
```

### Archetype C: Total AI Opt-Out
Completely disallow all known AI crawlers from fetching any content.

```txt
User-agent: GPTBot
Disallow: /

User-agent: ChatGPT-User
Disallow: /

User-agent: ClaudeBot
Disallow: /

User-agent: anthropic-ai
Disallow: /

User-agent: PerplexityBot
Disallow: /

User-agent: Applebot-Extended
Disallow: /

User-agent: Bytespider
Disallow: /

User-agent: Google-Extended
Disallow: /

User-agent: CCBot
Disallow: /

User-agent: *
Allow: /
```

---

## 3. RFC 9309 Rules & Common Pitfalls

1. **Precedence (Section 2.2.1)**:
   - Specific user-agent groups override the generic `User-agent: *` group completely.
   - If you declare `User-agent: GPTBot` with `Allow: /blog/`, it will NOT inherit rules from `User-agent: *`. You must explicitly specify all rules for that agent.
2. **Longest Match Rule (Section 2.2.2)**:
   - When multiple rules match a path, the rule with the longest path prefix takes precedence.
   - In case of a tie between `Allow:` and `Disallow:` of equal length, `Allow:` wins.
3. **Empty Disallow**:
   - `Disallow:` with no value is explicitly recognized by RFC 9309 as "allow everything".
4. **Crawl-Delay Hazards**:
   - Setting `Crawl-delay: 30` or higher often causes AI search indexers to drop real-time pages from fresh indexes. Keep delay <= 2 or omit.
