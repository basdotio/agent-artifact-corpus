---
name: on-page-seo
description: "Optimizes individual web pages for search rankings through content and entity strategy. Covers the 8 On-Page Tablets (URL, titles, headers, keywords, LSI, images, outbound links, internal linking), Entity SEO (Knowledge Graph, entity homes, topical authority, siloing), and E-E-A-T framework. Use when optimizing page content for specific keywords, building entity authority, or auditing on-page SEO elements. Trigger phrases: 'on-page SEO', 'title tag', 'meta description', 'H1', 'keyword density', 'content optimization', 'E-E-A-T', 'entity SEO'. NOT for technical issues (use technical-seo), link building (use link-building), AI search (use ai-ready), or structured data implementation (use schema-markup)."
---

# On-Page SEO

**When to use this skill:**

- Optimizing page content for specific target keywords
- Building entity authority and Knowledge Graph presence
- Auditing on-page SEO elements (titles, headers, internal links)
- Improving topical authority through content siloing
- Applying E-E-A-T framework to content

**When NOT to use:**

- Technical SEO issues (crawl errors, page speed, robots.txt) → use `technical-seo`
- Link building and outreach → use `link-building`
- AI search / GEO optimization → use `ai-ready`
- Structured data / JSON-LD implementation → use `schema-markup`
- Image optimization (formats, compression, lazy loading) → use `image-seo`

---

## Quick Router

| User says...                                               | Go to...                     |
| ---------------------------------------------------------- | ---------------------------- |
| "optimize page", "on-page SEO", "title tag", "keywords"   | Phase 1: On-Page SEO         |
| "Knowledge Graph", "entity", "schema types", "siloing"    | Phase 2: Entity SEO          |
| "E-E-A-T", "author credentials", "trustworthiness"        | Phase 3: E-E-A-T Framework   |
| "technical SEO", "speed", "Core Web Vitals"               | → Use `technical-seo` skill  |
| "backlinks", "link building", "outreach"                  | → Use `link-building` skill  |
| "JSON-LD", "structured data", "rich results"              | → Use `schema-markup` skill  |
| "AI search", "ChatGPT", "Perplexity", "GEO"               | → Use `ai-ready` skill       |

---

## Core Framework: Four Pillars of SEO

```
1. RELEVANCE → Does your content match search intent?
2. CRAWLABILITY → Can search engines find and index your content?
3. ENGAGEMENT → Do users interact positively with your content?
4. AUTHORITY → Do other sites vouch for your content?
```

**Success = All four pillars working together**

---

## Phase 1: On-Page SEO (8 Tablets)

**Source:** Will Coombe "3 Months to No.1"

### Tablet 1: URL Structure

- **Rule:** Max 5 words, include primary keyword
- **Structure:** `domain.com/category/keyword-phrase`
- **Checklist:**
  - [ ] URL contains primary keyword
  - [ ] Max one subdirectory from root
  - [ ] No special characters or numbers
  - [ ] Hyphens between words (not underscores)

**Example:** `healthyliving.com/best-vegetarian-diet` ✓

### Tablet 2: Title Tags

- **Rule:** Unique title per page, keyword at start
- **Format:** `Primary Keyword | Secondary | Brand`
- **Length:** 50-60 characters
- **Checklist:**
  - [ ] Primary keyword in first 3 words
  - [ ] Unique across entire site
  - [ ] Compelling for CTR (not just keywords)

**Example:** `Vegetarian Diet Plan | Complete Guide | HealthyLiving`

### Tablet 3: Header Structure (H1-H6)

- **Rule:** One H1 per page with primary keyword
- **Structure:**
  ```
  H1: Primary keyword (only one)
  H2: Main sections (include LSI keywords)
  H3: Subsections
  H4+: Details
  ```
- **Checklist:**
  - [ ] Exactly one H1 tag
  - [ ] H1 matches/relates to title tag
  - [ ] Logical hierarchy (no skipping levels)
  - [ ] H2s contain secondary keywords

### Tablet 4: Keyword Density

- **Rule:** 1-2% density for primary keyword
- **Placement priority:**
  1. First 100 words
  2. Last 100 words
  3. At least one H2
  4. Naturally throughout
- **Warning:** Over-optimization penalty at >3%

### Tablet 5: LSI Keywords (Latent Semantic Indexing)

- **Rule:** Include related terms to establish topical authority
- **How to find:**
  - Google "related searches" at bottom of SERP
  - Google autocomplete suggestions
  - People Also Ask boxes
  - Tools: LSIGraph, Clearscope, SurferSEO
- **Checklist:**
  - [ ] 5-10 LSI terms per 1000 words
  - [ ] Used naturally in context
  - [ ] Included in H2/H3 where relevant

### Tablet 6: Images & Alt Tags

- **Rule:** Include alt text with primary keyword on first image.
- For comprehensive image optimization (formats, compression, lazy loading, visual search) → see `image-seo` skill.

### Tablet 7: Outbound Links

- **Rule:** Link to 1-2 authoritative external sources
- **Requirements:**
  - High authority sites (Wikipedia, .gov, .edu, industry leaders)
  - NOT direct competitors
  - Relevant to content topic
- **Checklist:**
  - [ ] 1-2 outbound links per article
  - [ ] Links to authoritative sources
  - [ ] Opens in new tab
  - [ ] Adds value for reader

### Tablet 8: Topic Relevance (Internal Linking)

- **Rule:** Create 3-4 supporting articles linking to main page
- **Strategy:**
  - Main page targets primary keyword
  - Supporting pages target related long-tail keywords
  - All supporting pages link to main page
- **Example:**
  - Main: "Vegetarian Diet"
  - Supporting: "10 Famous Vegetarians", "Weight Loss Tricks", "Vegetarian Recipes"
  - All link back to main page

---

## Technical SEO Quick-Check

Before publishing any page, verify these 5 essentials. For a full technical audit → see `technical-seo` skill.

- [ ] **LCP < 2.5s** — Largest Contentful Paint passes Core Web Vitals threshold
- [ ] **robots.txt valid** — Page is not accidentally blocked from crawling
- [ ] **Sitemap submitted** — Page is included in XML sitemap submitted to GSC
- [ ] **Canonical tags** — Self-referencing canonical set; no conflicting canonicals
- [ ] **HTTPS** — Page served over HTTPS, no mixed content warnings

---

## Phase 2: Entity SEO

**Source:** Dixon Jones "Entity SEO"

### Core Concept

**Shift from "strings" (keywords) to "things" (entities)**

Entity SEO helps Google understand WHO you are, WHAT you do, and HOW you relate to other entities in the Knowledge Graph.

### Knowledge Graph Fundamentals

**Semantic Triples:** Subject → Predicate → Object

- "Freddie Mercury" → "is member of" → "Queen"
- "Your Brand" → "provides" → "SEO Services"

**Deduction:** Google derives new facts from existing relationships

- If: "Freddie Mercury is in Queen" AND "Queen is a rock band"
- Then: "Freddie Mercury is a rock musician"

### Building Your Entity

**Step 1: Check if Google knows you**

```
Use Knowledge Graph Search API:
https://kgsearch.googleapis.com/v1/entities:search?query=YOUR_BRAND&key=API_KEY
```

If you have an ID (e.g., `kg:/m/012g06h`), use it in structured data.

**Step 2: Establish Entity Home**

- One authoritative page that defines your entity
- Usually your About page or homepage
- Contains comprehensive, consistent information

**Step 3: Trusted Seeds Strategy**

| Source | Impact | Difficulty |
|--------|--------|------------|
| Wikipedia | Very High | Very Hard |
| Wikidata | High | Medium |
| Industry directories | Medium | Easy |
| News mentions | Medium | Medium |
| Social profiles | Low | Easy |

**"Affiliation Strategy":** If you can't get your own Wikipedia page, get mentioned on pages of entities you're connected to (employers, partners, associations).

**Step 4: Digital Assets Creation**

- [ ] Publish book with ISBN
- [ ] Create YouTube channel (linked to brand)
- [ ] IMDB listing (if applicable)
- [ ] Podcast on major platforms
- [ ] LinkedIn company page
- [ ] Crunchbase profile (for startups)

### Structured Data for Entity SEO

For JSON-LD implementation → see `schema-markup` skill.

**Schema types by page** (reference — implement via `schema-markup`):

| Page Type | Schema |
|-----------|--------|
| Homepage | Organization, WebSite |
| About | Organization, Person |
| Product | Product, Offer |
| Article | Article, NewsArticle |
| FAQ | FAQPage |
| How-to | HowTo |
| Event | Event |
| Local Business | LocalBusiness |

### Internal Link Graph (Siloing)

**Structure content into topical clusters:**

```
Pillar Page (main topic)
├── Cluster 1: Subtopic A
│   ├── Article 1.1
│   ├── Article 1.2
│   └── Article 1.3
├── Cluster 2: Subtopic B
│   ├── Article 2.1
│   └── Article 2.2
```

**Rules:**

- All cluster articles link to pillar page
- Cluster articles interlink within cluster
- Pillar pages link to each other sparingly
- Use descriptive anchor text (not "click here")

### SEU Metric (Search Engine Understanding)

**Goal:** Maximize Google's ability to extract entities from your content.

**Checklist:**

- [ ] Clear, unambiguous language
- [ ] Entities explicitly named (not just pronouns)
- [ ] Relationships stated clearly
- [ ] Structured data matches content
- [ ] Consistent naming across site

---

## Phase 3: E-E-A-T Framework

**Source:** The Art of SEO (4th Edition)

### Components

| Letter | Meaning               | Description                      |
| ------ | --------------------- | -------------------------------- |
| E      | **Experience**        | First-hand experience with topic |
| E      | **Expertise**         | Formal knowledge/credentials     |
| A      | **Authoritativeness** | Industry recognition             |
| T      | **Trustworthiness**   | Site reliability and honesty     |

### YMYL (Your Money Your Life)

**Extra scrutiny for topics affecting:**

- Health and safety
- Financial information
- Legal advice
- News and current events
- Shopping/transactions
- Groups of people

### E-E-A-T Implementation Checklist

**Experience:**

- [ ] Author has demonstrated experience (case studies, examples)
- [ ] First-person accounts where relevant
- [ ] "Tested and reviewed" content

**Expertise:**

- [ ] Author bios with credentials
- [ ] Qualifications stated clearly
- [ ] Expert contributors credited

**Authoritativeness:**

- [ ] Backlinks from authoritative sources
- [ ] Mentions in industry publications
- [ ] Awards and recognition displayed
- [ ] Association memberships shown

**Trustworthiness:**

- [ ] Clear contact information
- [ ] Physical address (if applicable)
- [ ] Privacy policy
- [ ] Terms of service
- [ ] HTTPS enabled
- [ ] References to authoritative sources
- [ ] Transparent editorial process
- [ ] Corrections policy

### Content Audit for E-E-A-T

1. **Remove thin content** (pages with little value)
2. **Add author information** to all articles
3. **Update outdated content** (especially YMYL)
4. **Add credentials** where relevant
5. **Link to authoritative sources**
6. **Remove or nofollow low-quality links**

---

## Complete On-Page Checklist

### Pre-Launch

- [ ] Keyword research completed
- [ ] Site architecture planned (siloing)
- [ ] Technical SEO baseline set (see `technical-seo`)
- [ ] Structured data implemented (see `schema-markup`)
- [ ] Core Web Vitals passing

### On-Page (Per Page)

- [ ] URL optimized (Tablet 1)
- [ ] Title tag optimized (Tablet 2)
- [ ] Headers structured (Tablet 3)
- [ ] Keyword density 1-2% (Tablet 4)
- [ ] LSI keywords included (Tablet 5)
- [ ] First image has alt text with primary keyword (Tablet 6)
- [ ] Outbound links added (Tablet 7)
- [ ] Internal links added (Tablet 8)

### Entity SEO

- [ ] Organization schema implemented (via `schema-markup`)
- [ ] Entity home page created
- [ ] Wikidata entry (if eligible)
- [ ] Consistent NAP across web
- [ ] sameAs links to social profiles

---

## Metrics & KPIs

### Traditional SEO

| Metric             | Tool               | Target                     |
| ------------------ | ------------------ | -------------------------- |
| Organic Traffic    | GA4                | ↑ Month over month         |
| Keyword Rankings   | Ahrefs/SEMrush     | Top 10 for target keywords |
| Click-Through Rate | GSC                | > Industry average         |
| Core Web Vitals    | PageSpeed Insights | All green                  |

---

## Common Mistakes

1. **Keyword stuffing** → Use 1-2% density, include LSI
2. **Ignoring technical SEO** → Fix crawl errors first (use `technical-seo`)
4. **Thin content** → Comprehensive > frequent
5. **Ignoring E-E-A-T** → Critical for YMYL topics
6. **Not tracking results** → Set up GSC + GA4 first
7. **Optimizing for rankings only** → Focus on conversions
9. **One-time optimization** → SEO is ongoing
10. **No internal linking** → Build topic clusters

---

## Related Skills

- **Keyword research:** `keyword-research`
- **Technical foundation:** `technical-seo`
- **Structured data:** `schema-markup`
- **Image optimization:** `image-seo`
- **Link building:** `link-building`
- **AI search:** `ai-ready`
- **Content writing:** `web-copy`
- **UX optimization:** `ux-optimization`
- **Full audit routing:** `seo-orchestrator`

---

## Resources

### Books Referenced

- "3 Months to No.1" - Will Coombe
- "Entity SEO" - Dixon Jones
- "Product-Led SEO" - Eli Schwartz
- "The Art of SEO" (4th Edition)

### Tools

- **Research:** Ahrefs, SEMrush, Moz
- **Tracking:** Google Search Console, GA4
- **Content:** Clearscope, SurferSEO, LSIGraph
- **Entity:** Knowledge Graph Search API, Wikidata

### Key Experts

- Jason Barnard (Entity SEO, Kalicube)
- Dixon Jones (Knowledge Graph)
- Eli Schwartz (Product-Led SEO)
- Rand Fishkin (General SEO strategy)

---

**Remember: On-page SEO is about making your content maximally clear to both humans and search engines. Relevance and authority compound over time.**
