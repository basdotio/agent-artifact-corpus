---
name: bmad-research
description: |
  Conducts market, competitive, domain, and technical research using live web sources,
  producing a cited research-report.md to inform BMAD planning decisions.

  Use when the user says:
  - "research [topic/market/technology]"
  - "competitive analysis" or "who are the competitors"
  - "market size" or "market landscape"
  - "technical research" or "evaluate [technology/framework]"
  - "domain research" or "industry analysis"
  - "what does the market look like"
  - "find out about [technology/space]"
  - "I need research before we plan"
  - "gather information on [topic]"

  Supports three modes: Create (new research), Update (refresh existing report with new
  sources), Validate (cross-check claims in an existing report against live sources).
  Output lands in bmad-output/ as a cited research-report.md ready for downstream
  planning skills (business-analyst, product-manager, system-architect).
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebSearch, WebFetch, TodoWrite
---

# BMAD Research

Conducts structured, cited research across three modes to feed BMAD planning workflows.
Output is a research-report.md in bmad-output/, ready for handoff to planning skills.

---

## Step 0 — Clarify Intent

Before searching, confirm:

1. **Mode** — Create / Update / Validate (default: Create)
2. **Research type** — Market | Competitive | Technical | Domain (may combine)
3. **Topic** — What is being researched?
4. **Output destination** — Default: `bmad-output/research-report.md`

If project-context.md exists, read it first (`bmad-output/project-context.md`) for
scope constraints.

---

## Step 1 — Plan the Research

Use the source-type strategy guide to pick sources by research type:

```
${CLAUDE_PLUGIN_ROOT}/skills/bmad-research/scripts/research-sources.sh
```

Run it (Bash) to print the guide, then sketch a query plan:
- 3–5 targeted WebSearch queries per research type
- Specific URLs to WebFetch (industry reports, competitor sites, docs)
- Triangulation goal: each key claim backed by 2+ independent sources

Track progress with TodoWrite.

---

## Step 2 — Execute Research

### Market Research
- Search: market size, TAM/SAM/SOM, growth CAGR, key trends, growth drivers
- Sources: Statista, Grand View Research, CB Insights, SEC filings, industry reports
- Quantify everything possible: dollar values, percentages, time frames

### Competitive Research
- Search: top competitors, feature comparisons, pricing, user reviews, funding
- Sources: G2/Capterra (reviews), Crunchbase (funding/size), company IR pages,
  product documentation, Reddit/HN community sentiment
- Build a feature comparison matrix

### Technical Research
- Search: framework benchmarks, adoption rates, community health, known trade-offs
- Sources: Official docs, GitHub stars/issues, npm/PyPI stats, State of JS/CSS,
  ThoughtWorks Radar, Stack Overflow surveys
- Evaluate: maturity, ecosystem, licensing, long-term viability

### Domain Research
- Search: regulatory landscape, industry standards, key players, domain glossary
- Sources: Government databases, standards bodies, academic papers (Google Scholar,
  arXiv), trade publications

**Citation discipline**: for every factual claim, record source URL + access date.
When a claim cannot be verified across 2+ sources, mark it `[UNVERIFIED]`.

---

## Step 3 — Update Mode

If mode is Update, read the existing report first. Then:
1. Identify sections with stale data (>6 months old, or marked `[UNVERIFIED]`)
2. Re-run targeted searches for those sections only
3. Append a "Last Updated" entry per section
4. Increment the report version

---

## Step 4 — Validate Mode

If mode is Validate:
1. Extract all quantitative claims from the existing report
2. Spot-check each claim with a fresh WebSearch
3. Mark each claim: `[VERIFIED]`, `[CONTRADICTED source: …]`, or `[UNVERIFIED]`
4. Append a "Validation Summary" section noting overall confidence

---

## Step 5 — Write the Report

Use the template:

```
${CLAUDE_PLUGIN_ROOT}/skills/bmad-research/templates/research-report.template.md
```

Fill all sections. Sections irrelevant to the research type may be omitted (mark as
N/A). Write the completed report to:

```
bmad-output/research-report.md   # or a user-specified path
```

**Required sections regardless of mode:**
- Executive Summary with key findings and bottom line
- Research Scope (in/out of scope, time frame)
- Methodology (sources used, tools, limitations)
- Gaps & Opportunities
- Recommendations (planning actions, not implementation actions)
- Full source bibliography (Appendix B) with URLs and access dates

---

## Step 6 — Handoff

After writing the report, tell the user:
- The output path
- The 3 most important findings in plain language
- Which BMAD planning skill should consume this report next:
  - Market/Competitive → business-analyst or product-manager
  - Technical → system-architect
  - Domain → business-analyst

Record the research decision in `bmad-output/decision-log.md`:
```
## Research: [Topic] — [Date]
- Mode: [Create/Update/Validate]
- Types: [Market/Competitive/Technical/Domain]
- Key finding: [one sentence]
- Report: bmad-output/research-report.md
- Next skill: [skill name]
```

---

## Subagent Strategy

For broad research covering multiple types simultaneously, fan out parallel agents:

**Agent 1 — Market Agent**
```
Read project-context.md, then conduct market research on [topic]:
TAM/SAM/SOM, growth rates, key trends. Write findings to
bmad-output/research-scratch/market.md with full citations.
```

**Agent 2 — Competitive Agent**
```
Read project-context.md, then research top 3-5 competitors for [topic]:
features, pricing, strengths/weaknesses, user sentiment. Write findings to
bmad-output/research-scratch/competitive.md with full citations.
```

**Agent 3 — Technical/Domain Agent**
```
Read project-context.md, then research technical landscape for [topic]:
technology options, ecosystem health, standards. Write findings to
bmad-output/research-scratch/technical.md with full citations.
```

After all agents complete, synthesize scratch files into the final report using the
template. Delete scratch files after synthesis.

---

> ---
> Part of the **BMAD Planning & Orchestrator** plugin — a Claude Code harness for the **BMAD Method** by the **BMAD Code Organization** (https://github.com/bmad-code-org/BMAD-METHOD). Implements the spirit of `bmad-market/domain/technical-research`. All methodology credit belongs to the BMAD Code Organization.
