#!/usr/bin/env bash
# Research Sources Reference — BMAD Planning & Orchestrator
# Source-type strategy guide for market, competitive, technical, and domain research.
# Usage: bash ${CLAUDE_PLUGIN_ROOT}/skills/bmad-research/scripts/research-sources.sh [type]
#   type: market | competitive | technical | domain | all (default: all)

set -euo pipefail

FILTER="${1:-all}"

show_section() {
  local tag="$1"
  [[ "$FILTER" == "all" || "$FILTER" == "$tag" ]]
}

cat <<'HEADER'
Research Sources Guide — BMAD Planning & Orchestrator
======================================================
HEADER

# ─────────────────────────────────────────────────────────────
if show_section "market"; then
cat <<'EOF'

=============================================================================
MARKET RESEARCH SOURCES
=============================================================================

Industry Reports & Analysis:
- Gartner, Forrester, IDC (technology markets)
- IBISWorld (industry statistics)
- Statista (market data and statistics)
- CB Insights (venture and emerging markets)
- PitchBook (private markets and M&A)

Market Size & Growth:
- Grand View Research
- MarketsandMarkets
- Allied Market Research
- Fortune Business Insights

Government & Official Statistics:
- U.S. Census Bureau / Bureau of Labor Statistics
- SEC EDGAR (public company filings, 10-K, 10-Q)
- Patent databases (USPTO, WIPO) — signals innovation trends
- Eurostat / OECD (international markets)

Financial Data:
- Yahoo Finance / Google Finance
- Annual reports (investor relations pages)
- Quarterly earnings call transcripts
- Form 10-K / 20-F filings on SEC EDGAR

Recommended Search Queries:
  "[market] market size [year] billion"
  "[market] CAGR forecast [year range]"
  "[market] market share report site:statista.com OR site:grandviewresearch.com"
  "[market] industry trends [year]"

EOF
fi

# ─────────────────────────────────────────────────────────────
if show_section "competitive"; then
cat <<'EOF'

=============================================================================
COMPETITIVE RESEARCH SOURCES
=============================================================================

Company Information:
- Company websites (About, Pricing, Careers, Press pages)
- LinkedIn company pages (employee count, growth signals)
- Crunchbase (funding rounds, investors, team size)
- Product Hunt (launch dates, initial reception)

Product Analysis:
- G2, Capterra, TrustRadius (verified user reviews)
- Product documentation and help centers
- YouTube product demos and tutorials
- GitHub repositories (for developer tools: stars, issues, activity)
- App Store / Google Play (mobile products: ratings, reviews)

Social Media & Community Sentiment:
- Reddit (user discussions, complaints, comparisons)
- Hacker News (technical community reactions)
- Quora (common questions, comparisons, use-case discussions)
- Twitter/X (company announcements, user complaints)
- Discord/Slack communities (power-user insights)

News & Press:
- TechCrunch, VentureBeat, The Information (funding/launches)
- Industry-specific publications
- Company press releases (newsroom pages)
- Podcast interviews with founders (signal strategy)

Pricing Intelligence:
- Direct pricing pages (check Wayback Machine for history)
- Review sites often document pricing tiers
- Job postings reveal tech stack and team composition

Recommended Search Queries:
  "[competitor] reviews site:g2.com OR site:capterra.com"
  "[competitor] pricing [year]"
  "[competitor] vs [competitor] comparison"
  "[competitor] funding crunchbase"
  "alternatives to [competitor]"

EOF
fi

# ─────────────────────────────────────────────────────────────
if show_section "technical"; then
cat <<'EOF'

=============================================================================
TECHNICAL RESEARCH SOURCES
=============================================================================

Official Documentation:
- Framework/library official docs (always prefer over tutorials)
- MDN Web Docs (web platform APIs)
- AWS Docs, Google Cloud Docs, Azure Learn
- ReadTheDocs, GitBook hosted docs

Package Registries & Health Signals:
- npm / PyPI / Maven / crates.io (download trends, version cadence)
- GitHub (stars, forks, open issues, last commit, contributor count)
- Libraries.io (dependency graphs, deprecation signals)

Community & Adoption:
- Stack Overflow (question volume = adoption proxy; common errors)
- Dev.to, Medium (tutorials indicate adoption curve)
- Hacker News "Ask HN" (candid practitioner opinions)
- Reddit r/programming and language-specific subreddits

Benchmarks & Comparisons:
- TechEmpower Framework Benchmarks (web framework performance)
- DB-Engines.com (database popularity rankings)
- State of JS / State of CSS / Stack Overflow Developer Survey
- ThoughtWorks Technology Radar (adopt / trial / assess / hold)

Academic & Research:
- Google Scholar (peer-reviewed papers)
- arXiv.org (pre-prints for AI/ML/CS)
- ACM Digital Library / IEEE Xplore (formal research)
- NIST (security standards, cryptography)

Licensing & Compliance:
- SPDX License List (license compatibility)
- FOSSA, Snyk (known vulnerabilities in packages)
- OSS Review Toolkit (license obligations)

Recommended Search Queries:
  "[technology] vs [technology] [year] performance"
  "[technology] production case study"
  "[technology] known issues OR limitations [year]"
  "[framework] benchmark site:techempower.com"
  "state of [technology] [year] survey"

EOF
fi

# ─────────────────────────────────────────────────────────────
if show_section "domain"; then
cat <<'EOF'

=============================================================================
DOMAIN / INDUSTRY RESEARCH SOURCES
=============================================================================

Regulatory & Standards:
- Relevant government agencies (FDA, FTC, FINRA, HIPAA.gov, GDPR.eu)
- Standards bodies (ISO, NIST, W3C, IEEE, IETF)
- Industry associations (trade groups publish compliance guides)
- Legal databases (Westlaw, LexisNexis — for regulatory landscape)

Industry Publications:
- Trade journals specific to the domain
- Professional association newsletters
- Government white papers and RFIs

Academic & Think Tanks:
- Google Scholar + arXiv (domain research)
- Brookings Institution, McKinsey Global Institute (industry reports)
- Domain-specific university research centers

User Behavior & Demographics:
- Pew Research Center (demographics, technology adoption)
- Nielsen Norman Group (UX and user behavior)
- Baymard Institute (e-commerce UX benchmarks)
- Google Trends (search interest over time)

Recommended Search Queries:
  "[domain] regulation [country] [year]"
  "[domain] compliance requirements"
  "[domain] industry association standards"
  "[domain] key players market leaders"
  "[domain] terminology glossary"

EOF
fi

# ─────────────────────────────────────────────────────────────
cat <<'EOF'

=============================================================================
RESEARCH WORKFLOW — STEP BY STEP
=============================================================================

Step 1: Define scope
  → What decisions will this research inform?
  → What questions must be answered?
  → Set a time-box (research is infinite without one)

Step 2: Map sources to questions
  → Assign source type(s) to each question (see sections above)
  → Draft 3–5 WebSearch queries per research type
  → Identify 2–4 specific URLs to WebFetch directly

Step 3: Gather — search broad, fetch specific
  → WebSearch for discovery and trends
  → WebFetch for specific reports, docs, pricing pages
  → Note source URL + access date for every data point

Step 4: Triangulate — verify claims across 2+ independent sources
  → Single-source claims → mark [UNVERIFIED]
  → Contradictions → document both with sources, flag for review

Step 5: Synthesize into research-report.md
  → Use the template at:
     ${CLAUDE_PLUGIN_ROOT}/skills/bmad-research/templates/research-report.template.md
  → Write to: bmad-output/research-report.md

=============================================================================
CITATION FORMAT
=============================================================================

Inline citation (use after every factual claim):
  [Source Name, Date](URL)

Bibliography entry (Appendix B):
  1. Source Name. "Page Title." URL. Accessed YYYY-MM-DD.

Confidence markers:
  [VERIFIED]    — supported by 2+ independent sources
  [UNVERIFIED]  — single source only, could not cross-check
  [CONTRADICTED source: URL] — contradicted by another source

=============================================================================
BEST PRACTICES
=============================================================================

 1. Secondary before primary — existing data first (faster, cheaper)
 2. Triangulate — 2+ sources for every key claim
 3. Check publish dates — prefer sources < 18 months old
 4. Consider source bias — who funded this report and why?
 5. Quantify — numbers beat adjectives ("large market" → "$4.2B TAM")
 6. Cite inline — don't wait until the end to record sources
 7. Look for gaps — what's NOT being said is often the opportunity
 8. Time-box — set a search limit per research type (e.g., 20 min)
 9. Focus on decisions — every finding should map to a planning choice
10. Date-stamp findings — markets and tech change quickly

=============================================================================

EOF
