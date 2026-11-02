---
name: parallel-research
description: Deep research on any topic using parallel sub-agent execution. Breaks question into 3-5 angles, researches all simultaneously, synthesizes into a structured report saved to disk. Turns 30-min serial research into 5 minutes.
argument-hint: [research question or topic to investigate]
allowed-tools: Read, Write, Bash, WebSearch, WebFetch
---

# Parallel Research — Multi-Angle Research Synthesizer

## Why This Exists
Serial research (search → read → search → read) is slow. The right pattern: decompose the question into independent angles, run them all at once, synthesize. This skill implements that pattern with structured output and a saved report.

## Trigger
Use when: "research X", "find everything about Y", "investigate Z", "what do I need to know about [topic]", "deep dive on [subject]", or any research task that would take more than one search query.

Invoked as: `/parallel-research [topic or question]`

---

## Process

### Step 1: Parse the Research Question

From `$ARGUMENTS`, identify:
- The core question or topic
- Any constraints (e.g., "focus on pricing", "only recent news", "for a technical audience")
- The desired output format (if mentioned)
- Domain/industry context

If the question is very broad (e.g., "AI agents"), narrow it: "What specifically do you want to know? e.g., market landscape, technical architecture, business use cases, or all of the above?"

---

### Step 2: Decompose into Research Angles

Break the topic into **3-5 focused, non-overlapping sub-questions**. Each angle should be independently answerable and together they should cover the full picture.

**Decomposition patterns by topic type:**

*Market/business topic* (e.g., "AI agent market"):
1. Market size, growth rate, and key players
2. Current pricing models and revenue benchmarks
3. Technology differentiation (what separates winners from losers)
4. Recent news, funding rounds, and notable launches (last 90 days)
5. Competitor weaknesses and market gaps

*Technical topic* (e.g., "vector databases"):
1. How it works — core architecture and algorithms
2. Comparison of leading options (feature matrix)
3. Performance benchmarks and scaling limits
4. Integration patterns with common stacks
5. Community activity, maturity, and adoption signals

*Person/company topic* (e.g., "Anthropic"):
1. Background, founding story, and key people
2. Products, pricing, and current offerings
3. Funding history and financial health
4. Recent news and strategic moves
5. Competitive positioning and differentiation

*Skill/how-to topic* (e.g., "running a Telegram bot"):
1. Official docs and setup walkthrough
2. Common gotchas and failure modes
3. Real-world implementations and open source examples
4. Cost and scaling considerations
5. Best libraries/frameworks with tradeoffs

---

### Step 3: Execute Parallel Research

For each angle, conduct focused research:

**Research execution (do all angles in sequence, taking notes as you go):**

For each angle:
1. Run 1-3 targeted WebSearch queries specific to that angle
2. For the most promising result, use WebFetch to read the full page
3. Extract the key facts, numbers, quotes, and insights
4. Note the source URL and date
5. Flag any contradictions or gaps found

**Search query crafting tips:**
- Add the current year to avoid stale results: `"topic" 2026`
- Use site-specific searches for authoritative sources: `site:techcrunch.com AI agents 2026`
- For pricing/benchmarks: add "pricing" or "benchmark" or "comparison"
- For recent news: add "news" or sort results by date

**While researching each angle, track:**
- 3-5 key facts or data points
- 1-2 most credible sources
- Any surprising or counterintuitive findings
- Any gaps (things you couldn't find or verify)

---

### Step 4: Synthesize the Report

After all angles are researched, write a structured markdown report.

**Report structure:**
```markdown
# Research Report: [Topic]
Generated: [date]
Question: [original research question from $ARGUMENTS]

---

## Executive Summary
[3-5 sentences covering the most important things to know. Lead with the most actionable insight.]

---

## Findings by Angle

### [Angle 1 Title]
[3-5 bullet points. Each bullet = one concrete fact, number, or finding. Cite source inline: [Source Name](URL)]

### [Angle 2 Title]
[same format]

### [Angle 3 Title]
[same format]

[...continue for each angle...]

---

## Contradictions & Gaps
- [Thing A says X, but Thing B says Y — which is current?]
- [Could not verify: ...]
- [Missing data: ...]

---

## Recommended Next Steps
1. [Most important action based on findings]
2. [Second action]
3. [Optional: deeper research needed on X]

---

## Sources
- [Source 1](URL) — [what it covers]
- [Source 2](URL) — [what it covers]
[...all sources used across all angles...]
```

---

### Step 5: Save the Report

Determine output path:
- If inside a project directory: save to `./research/research-[topic-slug]-[YYYY-MM-DD].md`
- If no project context: save to current working directory as `research-[topic-slug]-[YYYY-MM-DD].md`
- Create `research/` directory if it doesn't exist

**Topic slug rules:** lowercase, hyphens, no special chars, max 40 chars. Example: "AI agent frameworks" → "ai-agent-frameworks"

---

### Step 6: Send to Kevin via Telegram

After saving, send the Executive Summary + file path to Kevin via Telegram.

```bash
# Read bot token from config
BOT_TOKEN=$(node -e "console.log(require('C:/Users/kevdo/.clawd-cc/config.json').telegramBotToken)")

# Send summary message
curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
  -d "chat_id=8062428674" \
  --data-urlencode "text=Research complete: [Topic]

[Executive Summary — first 2-3 sentences]

Full report: [file path]
Angles covered: [X]
Sources: [Y]"
```

If the Telegram send fails (token not available, network issue), skip silently — the report file is the primary deliverable.

---

### Step 7: Print Final Output

```
Research complete.

Topic: [topic]
Angles researched: [X]
Sources consulted: [Y]
Report saved: [path]

Executive Summary:
[paste summary here]

Key findings:
• [Finding 1]
• [Finding 2]
• [Finding 3]

[Telegram notification sent / skipped]
```

---

## Error Handling

- **Topic too broad** ("research everything about AI"): Narrow to a specific question or ask Kevin to pick one of: market landscape / technical deep dive / business use cases
- **Search returns no useful results**: Try rephrasing with different terms, add year, try site-specific searches
- **Paywalled content**: Note the paywall in gaps section, find alternative sources
- **Contradictory findings**: Report both in the Contradictions section — don't pick a side without strong evidence
- **Rate limited on WebSearch**: Spread queries with short pauses, reduce to 2 queries per angle
- **Output file already exists**: Append a `-v2` suffix rather than overwriting

## Performance Notes
- Total research time: typically 3-8 minutes for 4 angles
- Quality improves with specific, focused questions
- For time-sensitive topics, add "site:reuters.com OR site:techcrunch.com OR site:bloomberg.com" to prioritize fresh authoritative sources