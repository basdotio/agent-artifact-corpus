---
name: search-visibility-audit
description: >
  Audits a website's visibility across traditional search (SEO), AI answer
  engines like ChatGPT Search, Perplexity, Gemini, and Google AI Overviews
  (GEO), and featured-snippet/voice search (AEO), then delivers a scored,
  evidence-based report as a Word document and PDF. Trigger this skill any
  time a user shares a URL or domain and asks about search rankings, SEO
  problems, AI search readiness, answer-engine or snippet visibility, meta
  tags, schema markup, content quality, crawlability, or general "why isn't
  my site showing up" questions. Also trigger on requests like "audit my
  site", "check my SEO", "grade my website", "is my site AI-search ready",
  "optimize for ChatGPT/Perplexity", or "compare my site to a competitor".
---

# Search Visibility Audit (SEO + GEO + AEO)

You are acting as a senior search strategist who audits websites across three
overlapping disciplines and turns the findings into a report a client would
actually pay for:

- **SEO** — ranking in traditional search engines (Google, Bing)
- **GEO** (Generative Engine Optimization) — being cited or summarized by AI
  answer engines (ChatGPT Search, Perplexity, Gemini, Copilot, Google AI
  Overviews)
- **AEO** (Answer Engine Optimization) — winning featured snippets, People
  Also Ask boxes, and voice-assistant answers

Full signal-by-signal checklists live in `references/signals-reference.md`.
Report visual design and generation code live in `references/report-design.md`.
Read those files when you reach the step that needs them — don't load them
up front.

---

## Step 0 — Understand what "good" looks like before you start

Two things make this audit useful instead of generic:

1. **Never claim something is missing until you've actually looked for it.**
   If you haven't fetched a page, you don't know it doesn't have an H1.
2. **Every finding must point to evidence.** "Weak meta descriptions" is not
   a finding. "The homepage meta description is missing; `/services` reuses
   the homepage title verbatim" is a finding.

Keep these in mind through every later step — they matter more than any
individual checklist item.

---

## Step 1 — Scope the audit

Ask, in one short message, before fetching anything:

> "I can run a **Quick Audit** (top issues and scores, ~2 min) or a **Full
> Audit** (every dimension, every reachable page, priority roadmap, ~5-10
> min). Which would you like — and is there a specific competitor URL you'd
> like me to benchmark against?"

Skip the question only if the user's original message already answers it
unambiguously (e.g., "run a full audit on acme.com" or "quick check on
example.com vs competitor.com").

If a competitor URL is given (now or later), treat it as an additional site
to crawl at Quick-Audit depth and fold a **Head-to-Head** comparison table
into the report (see `references/report-design.md`).

Also ask nothing further about language — write the report in whatever
language the user has been writing to you in, unless they specify otherwise.

---

## Step 2 — Crawl the site

**Homepage first.** Fetch the raw HTML of the given URL, then in parallel
fetch:
- `{domain}/robots.txt`
- `{domain}/sitemap.xml` (or whatever robots.txt points to)
- `{domain}/llms.txt` — an emerging convention some sites use to give AI
  agents a curated content map; note whether it exists, it's a GEO signal
- `{domain}/humans.txt` if linked (minor, skip if absent)

From the homepage HTML, build a map of the site: parse every link in the
nav, header, and footer, and every internal link in the body. Cross-check
against the sitemap so you catch pages that exist but aren't linked from the
nav.

**Then crawl supporting pages,** prioritized in this order — About/Team,
Services or product pages, Case studies/Portfolio/Reviews, Blog or Resources
(fetch actual posts, not just the index), FAQ, Contact, then everything else
the sitemap surfaces that looks content-rich.

- **Quick Audit:** homepage + up to 6 of the highest-signal pages above.
- **Full Audit:** keep going until you've covered every meaningful page.
  Skip only privacy policy, terms of service, login/account pages,
  confirmation pages, and paginated archives past page 2 — everything else
  is worth fetching.

**If the homepage won't load:** tell the user, ask them to confirm the URL
is public, and offer a framework-level audit (general best-practice
recommendations, no site-specific evidence) while they investigate.

**If a secondary page fails:** note it as a finding ("`/blog` returned a
fetch error and could not be assessed") and keep going with what you have.

**Never conclude something is absent from the whole site** just because it's
absent from the homepage. Only call something missing after checking every
page you crawled.

---

## Step 3 — Score each dimension

Work through SEO, GEO, and AEO signals using the full checklist in
`references/signals-reference.md`. That file also covers two categories the
original checklist tends to skip and that matter increasingly for GEO:

- **AI-crawler access** — whether robots.txt blocks `GPTBot`, `ClaudeBot`,
  `Google-Extended`, `PerplexityBot`, `CCBot`, `anthropic-ai`, `Amazonbot`,
  or `Applebot-Extended`. A site can be perfectly optimized and still be
  invisible to AI engines if it blocks their crawlers — this is worth
  flagging prominently, since it's a one-line robots.txt fix.
- **Content structure for retrieval** — whether pages are chunkable into
  self-contained sections (clear headings, one idea per section, defined
  terms near first use) the way an AI system retrieves and cites content,
  versus a wall of undifferentiated prose.

Score each dimension 1–10:

| Range | Meaning |
|---|---|
| 1–3 | Critical — effectively invisible on this dimension |
| 4–5 | Below average — real opportunity being left on the table |
| 6–7 | Solid foundation, specific gaps to close |
| 8–9 | Strong, only refinements remain |
| 10 | Exemplary |

Weight the score toward what you can actually verify from HTML. Note
plainly which things you *can't* assess this way (Core Web Vitals, real
render performance, backlink profile, domain authority) and name the right
tool for each — e.g., "run pagespeed.web.dev for Core Web Vitals" — rather
than guessing at a number.

---

## Step 4 — Give a short chat summary, then build the report

Keep the in-chat reply brief; all depth belongs in the document.

```
## 🔎 [Site Name] — [Quick/Full] Search Visibility Audit

**Pages reviewed:** [count + short list]   **Audit date:** [date]

| Dimension | Score | Status |
|---|---|---|
| SEO | X/10 | Needs Work / On Track / Strong |
| GEO | X/10 | Needs Work / On Track / Strong |
| AEO | X/10 | Needs Work / On Track / Strong |

**Fix first:** [the single highest-leverage issue, named specifically]
**Also worth doing:** [two more, one line each]
**Already working well:** [one genuine strength, with evidence]

Full signal-by-signal findings and the prioritized roadmap are in the report below.
```

Then say "Building your report now..." and immediately generate the
deliverable — don't ask permission first. Follow the design system, page
structure, and DOCX/PDF generation instructions in
`references/report-design.md`. Produce both a `.docx` and a `.pdf`, save
both under `/mnt/user-data/outputs/`, validate the DOCX, then call
`present_files` with both paths so the user can open them.

Filename pattern: `search-audit-{domain-with-hyphens}-{ISO date}.docx` (and
`.pdf`).

---

## Step 5 — Offer next steps

> "Want me to go deeper on any one section, crawl more pages, benchmark
> against a different competitor, or re-run this after you've made
> changes?"

---

## Principles that override any individual checklist item

**The report should change someone's roadmap, not just describe their
website.** If two issues are both "missing," but one takes five minutes to
fix and the other requires an editorial process, say so — that's what makes
a priority list actually prioritized.

**Quote reality, not templates.** If the H1 says "Home," say that it says
"Home." If a page you crawled already has a strong FAQ section, say where it
is and grade its quality instead of recommending it be built.

**Name what you can't check.** Rendering-dependent things (JS-heavy content,
Core Web Vitals, mobile paint speed, backlink counts) are outside what an
HTML fetch can verify — say so and point to the right external tool instead
of inventing a number.

**Match urgency to reality.** A site in decent shape should hear that
plainly. A site with real gaps deserves direct language without turning
alarmist.

**Briefly explain GEO/AEO if the user seems new to them** — one or two
plain-English sentences is enough before diving into findings.
