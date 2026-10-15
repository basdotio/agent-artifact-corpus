# Search Visibility Audit — SEO + GEO + AEO Skill for Claude

A Claude Skill that audits a website across three layers of modern search
visibility and hands back a scored, evidence-based report — not generic
best-practice advice, but findings tied to what's actually on the site.

- **SEO** — title tags, meta descriptions, heading structure, schema markup,
  internal linking, content depth, technical crawlability
- **GEO** (Generative Engine Optimization) — how well the site is set up to
  be read, understood, and cited by AI answer engines (ChatGPT Search,
  Perplexity, Gemini, Copilot, Google AI Overviews), including whether the
  site's `robots.txt` accidentally blocks AI crawlers like `GPTBot`,
  `ClaudeBot`, or `Google-Extended`
- **AEO** (Answer Engine Optimization) — featured snippet and voice-search
  readiness: FAQ/HowTo schema, question-phrased headings, direct-answer
  formatting

## What makes this useful beyond a checklist

- **Evidence, not templates.** Every finding cites the actual page and text
  it came from. Nothing is flagged as "missing" without first checking
  whether it exists somewhere else on the site.
- **AI-crawler access check.** A site can look great and still be invisible
  to AI search if its `robots.txt` blocks the bots that power it — this
  skill checks for that explicitly and flags it as a priority fix.
- **Honest about limits.** Things an HTML fetch genuinely can't verify
  (Core Web Vitals, backlink profile, real render performance) are named
  as such, with the right external tool pointed to instead of a guessed
  number.
- **Optional head-to-head comparison** against a competitor's URL, folded
  into the same report.
- **Prioritized roadmap**, not just a list of problems — issues are ranked
  by effort vs. impact, with "quick wins" called out separately.

## How to use it

Give Claude a URL and ask about search performance:

> "Audit acme.com for SEO"
> "Why isn't example.com showing up in ChatGPT search results?"
> "Run a full audit on my site vs. competitor.com"
> "Is my site ready for AI search?"

Claude will confirm Quick vs. Full audit, crawl the relevant pages, then
deliver a short scored summary in chat followed by a full Word document and
PDF report.

## Installation

Distributed as a skill folder for Claude (Claude.ai Skills, Claude Code, or
Claude Cowork, depending on what's available in your environment):

1. Download or clone this repository.
2. In Claude, go to wherever Skills are managed for your environment (e.g.
   Settings → Capabilities → Skills, or the Skills upload option in Cowork).
3. Add the `search-visibility-audit` folder (or a zip of it) as a skill.

## Repository structure

```
search-visibility-audit/
├── SKILL.md                          ← core workflow (read first)
├── README.md
└── references/
    ├── signals-reference.md          ← full SEO/GEO/AEO signal checklist
    └── report-design.md              ← report design system + generation code
```

`SKILL.md` stays short on purpose — it points to the two reference files
only when the relevant step is reached, so most of the detail doesn't take
up context until it's actually needed.

## Credits

Rebuilt and extended by **Alireza Bahador** from an earlier community SEO
audit skill concept, with an added AI-crawler access check, `llms.txt`
awareness, retrieval-friendly content structure signals, a competitor
comparison mode, and a corrected, environment-portable report generation
path.

## License

MIT — use, modify, and redistribute freely.
