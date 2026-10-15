# Signal Checklist

Full detail behind Step 3 of SKILL.md. Work through every applicable section
for every page you crawled, not just the homepage — but only report a
sub-total once per site, calling out page-specific exceptions as evidence.

---

## 1. SEO — traditional search engines

### On-page technical
- **Title tag**: present, 50–60 characters, contains the page's primary
  topic, not duplicated across pages you crawled.
- **Meta description**: present, 150–160 characters, includes a reason to
  click, not duplicated.
- **Heading hierarchy**: exactly one H1, logical H2/H3 nesting, no heading
  stuffing (repeating keywords across headings unnaturally).
- **URL structure**: readable, no excess parameters or session IDs, reflects
  the page's topic.
- **Canonical tag**: present, points to the correct self- or cross-domain
  target (check for accidental cross-domain canonicals — a common CMS bug).
- **Hreflang** (only if the site appears to target more than one
  language/region): present and reciprocal.
- **Robots meta / X-Robots-Tag**: page is indexable; check specifically for
  an accidental sitewide `noindex` left over from staging.
- **Viewport meta**: present (baseline mobile signal).
- **Image alt text**: present and descriptive on content images (decorative
  images can reasonably skip it).
- **Internal linking**: descriptive anchor text, no orphaned key pages
  (pages that exist in the sitemap but that nothing links to).
- **Open Graph / Twitter Card**: `og:title`, `og:description`, `og:image`
  present and sensible for how the page would appear when shared.

### Content quality
- **Depth**: ~500+ words for standard pages, 1,200+ for pillar/cornerstone
  content — but judge by whether the topic is actually covered, not word
  count alone.
- **Topical focus**: one clear primary topic per page, related terms present
  naturally (not stuffed).
- **Freshness signals**: publish/update dates visible where relevant (blog,
  news, pricing).
- **Scannability**: subheadings, short paragraphs, lists where they'd help.
- **Duplicate/thin content**: flag pages that are near-copies of each other
  or that add no real content beyond a template.

### Structured data
- **Schema markup present**: JSON-LD preferred; note types found
  (`Organization`, `LocalBusiness`, `Article`, `Product`, `FAQPage`,
  `HowTo`, `BreadcrumbList`, `Review`, etc.).
- **Validity**: does the JSON-LD parse and include the required properties
  for its type? Note obvious errors (e.g., `FAQPage` with no `mainEntity`).

### Site-level technical
- **HTTPS**: enforced sitewide, no mixed-content indicators in the HTML.
- **robots.txt**: doesn't accidentally block important paths; has a
  `Sitemap:` line.
- **sitemap.xml**: exists, is well-formed, roughly matches what you found by
  crawling.
- **404/error handling**: if you hit a broken internal link during the
  crawl, note it — broken links are both a UX and crawl-budget issue.

---

## 2. GEO — generative / AI answer engines

AI answer engines synthesize responses from multiple sources and choose what
to cite. They reward clarity, verifiable facts, and machine-legible
structure over persuasive copy.

### E-E-A-T (Experience, Expertise, Authoritativeness, Trustworthiness)
- **Author identity**: named authors with visible credentials on
  content-driven pages.
- **About page**: explains who runs the site and why they're credible on
  the topic.
- **Contact information**: real phone/address/email, not just a form.
- **Third-party trust signals**: testimonials, certifications, press
  mentions, case studies — visible, not just claimed.
- **Organization schema**: brand entity declared with name, logo, URL, and
  `sameAs` links to verified social/professional profiles.

### Content built for AI synthesis
- **Factual density**: specific numbers, dates, and claims an engine could
  extract and cite, rather than only qualitative marketing language.
- **Claim stated up front**: the page's core answer/argument is stated
  plainly near the top, not buried after three paragraphs of preamble.
- **Source citation**: content references credible external sources where
  relevant, rather than asserting claims with no backing.
- **Comprehensiveness**: the topic is actually resolved on the page, not
  left as a teaser toward a sales call.
- **Entity consistency**: the brand/person/place is named the same way
  throughout the site (helps an AI system build a consistent entity graph
  instead of treating variants as different things).
- **Retrieval-friendly structure**: content is broken into self-contained
  sections — a heading followed by a complete, extractable answer — rather
  than one long undifferentiated block. This is what lets an AI system pull
  out and cite a specific passage instead of skipping the page.

### AI-crawler access — check this explicitly, it's easy to miss
Parse `robots.txt` for `User-agent` blocks targeting known AI crawlers, and
report whether each is allowed or disallowed:

- `GPTBot` (OpenAI)
- `ChatGPT-User` (OpenAI, on-demand browsing)
- `ClaudeBot` / `anthropic-ai` (Anthropic)
- `PerplexityBot` (Perplexity)
- `Google-Extended` (Google's Gemini/AI Overviews training toggle, separate
  from `Googlebot`)
- `CCBot` (Common Crawl — many models train on this)
- `Amazonbot`
- `Applebot-Extended`

A site can score well everywhere else and still be structurally excluded
from AI answers if any of these are disallowed. Treat a block here as a
**high-priority, low-effort** fix — call it out by name in the roadmap, not
buried in a table.

### llms.txt
Check `{domain}/llms.txt`. This is an emerging (not yet universal)
convention where a site offers a curated Markdown map of its key content for
AI agents. Its absence is not a real deduction for most sites yet — note it
as an "ahead of the curve" opportunity, not a deficiency.

---

## 3. AEO — featured snippets, People Also Ask, voice assistants

### Snippet eligibility
- **Direct-answer paragraphs**: the core question is answered in ~40–60
  words directly under a question-phrased heading.
- **Definition pattern**: the page defines its subject in a clear "X is…"
  sentence somewhere prominent.
- **List content**: numbered steps or bullet lists that could become a list
  snippet.
- **Table content**: comparison tables that could become a table snippet.

### Structured answer formats
- **FAQ schema**: present and correctly structured (`FAQPage` with paired
  `Question`/`acceptedAnswer`).
- **HowTo schema**: present for step-by-step content, with ordered `step`
  entries.
- **Question-phrased headings**: H2/H3s written as natural questions ("How
  does X work?", "What does Y cost?").
- **SpeakableSpecification**: present for sections meant to be read aloud by
  voice assistants (rare — note as an opportunity if content would clearly
  benefit, not a default expectation).

### Voice / conversational readiness
- **Conversational phrasing**: content reads naturally if read aloud, not
  just optimized for skimming.
- **Long-tail question coverage**: the page anticipates specific who/what/
  when/where/why/how phrasings a person would actually ask.
- **Local signals** (only if the business is location-based): NAP (Name,
  Address, Phone) consistent with what's in the schema, `LocalBusiness`
  schema present, city/region named naturally in content.

---

## What you cannot verify from an HTML fetch — say so, name the tool

| Signal | Why you can't check it here | What to point the user to |
|---|---|---|
| Core Web Vitals (LCP, INP, CLS) | Requires real browser rendering/timing | pagespeed.web.dev |
| Actual render performance / JS-heavy content | Static fetch may miss client-rendered content | Browser dev tools, or ask if the site is server-rendered |
| Backlink profile / domain authority | Requires an external index Claude doesn't have | Ahrefs, Moz, Semrush |
| Real indexing status | Requires Search Console access | Google Search Console |
| Actual AI-engine citation frequency | Requires querying each engine over time | Manual spot-checks in ChatGPT Search / Perplexity, or a GEO-monitoring tool |

Never estimate a number for these — name the row, name the tool, move on.
