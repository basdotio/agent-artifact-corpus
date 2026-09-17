---
name: peer-review
description: Comprehensive peer review from skeptical economist and "lazy AI" perspectives. Identifies missing LaTeX equations, charts, hardcoded values, weak arguments, and context-loss vulnerabilities. Reviews calculation chains for all parameters.
allowed-tools:
  - Read
  - Edit
  - Grep
  - Glob
  - Bash
  - Write
  - TodoWrite
---

# /peer-review <file.qmd>

Four-perspective review AND fix: (1) Skeptical economist, (2) Lazy AI vulnerabilities, (3) Calculation audit, (4) Enhancement opportunities. Generates report then **implements all high/medium priority fixes**. If no file specified, ask which to review.

---

## Phase 1: Load Context

Read the file, then:
```bash
grep "_latex\":" _variables.yml | head -100
ls knowledge/figures/*.qmd | head -50
```

---

## Phase 2: Skeptical Economist Review

Read as a hostile peer reviewer skeptical of large claims.

| Category | Check |
|----------|-------|
| **Methodology** | Causal claims justified? Counterfactual specified? CIs appropriate? Assumptions stated? |
| **Sources** | Peer-reviewed? Old (>5y)? Over-reliance on single studies? |
| **Logic** | Conclusions follow? Unstated assumptions? Strongest counterargument addressed? |
| **Framing** | Neutral language? Limitations discussed? Costs AND benefits quantified? |

### Bullshit Detection

| Pattern | Example | Fix |
|---------|---------|-----|
| **Problem-solution mismatch** | Defending against Goodhart when metrics are real-world outcomes (income, mortality) that can't be gamed without improvement | Ask: does this problem actually apply here? Cut irrelevant defenses |
| **Speculative mechanisms** | "staking," "immutable rules," "distributed ledgers," "zero-knowledge proofs" when simpler solutions exist | Replace with realistic mechanisms: institutional diversity, median aggregation, transparency |
| **Internal contradictions** | "Immutable rules solve X" then later "immutable rules are insufficient" | Grep for key claims, verify consistency throughout |
| **Overconfident claims** | "trivial to influence," "guaranteed," "impossible" | Soften: "incentive is enormous," "difficult," "unlikely" |
| **Self-congratulatory framing** | "A sophisticated objection," "The honest assessment:" | Cut framing, state content directly |
| **Conflated problems** | Treating Goodhart gaming (behavior) and measurement capture (methodology) as same problem | Distinguish clearly; different problems need different solutions |
| **Over-defense** | 60 lines defending against non-problem, key point buried at end | Lead with "why this doesn't apply," cut irrelevant mitigations |
| **Unexplained jargon** | "mētis," "Schelling points," "Sybil attacks" | Define inline or replace with plain language |
| **Academic pomposity** | "This paper makes three contributions," "We formalize the X Condition" | Cut if content is covered elsewhere; keep only if adds navigation value |

**Key question:** For each defense/mitigation, ask "What specific attack does this prevent?" If answer is vague or doesn't apply to actual proposal, cut it.

### Clarity & Concision

**Write simply for general audience without losing precision.** Target 8th-grade reading level, 10-15 word sentences average. Can a smart 8th-grader understand this? If not, simplify. Never sacrifice accuracy—use precise terms but define immediately. Break complex ideas into 2-3 short sentences. Delete ruthlessly.

| Delete/Replace | Example |
|----------------|---------|
| **Redundancy** | "past history" -> "history" |
| **Hedging/blather** | "It could potentially be argued that" -> delete or "This suggests" |
| **Filler phrases** | "It is important to note that", "In order to", "the fact that" |
| **Nominalizations** | "the implementation of" -> "implementing" |
| **Passive voice** | "was conducted by" -> "X conducted" |
| **Em-dashes (—)** | Replace with period (preferred), comma, parenthesis, or semicolon |
| **Long sentences** | "X happened, which caused Y, and this led to Z" -> "X happened. This caused Y. Y led to Z." |

Flag and fix: Sentences >25 words, paragraphs >5 sentences, sections repeating earlier content, jargon without definition.

### Appropriate Humor (Philomena Cunk Style)

**Inject deadpan, absurdist humor when it clarifies without detracting from credibility.**

| Use when | Avoid when |
|----------|------------|
| Highlighting absurd contradictions/inefficiencies | Methodology sections (maintains rigor) |
| Making abstract concepts concrete via absurd comparisons | Serious topics (deaths, suffering, failures) |
| Breaking up dense technical sections | Executive summaries/abstracts |
| Calling out obvious but unstated truths | If it undermines credibility |

**Style guide:**
- Deadpan delivery: State absurdities as simple facts
- Absurd comparisons: "Like trying to solve climate change by asking everyone to think harder"
- Obvious questions: "Why does this exist? Nobody knows."
- Understated observations: "This seems inefficient. But it's the system we have."

**Examples:** ❌ "Regulatory delays kill people. LOL." ✅ "Regulatory delays kill people. This is not controversial. Yet the system continues."

---

## Phase 3: Lazy AI Vulnerability Analysis

What survives if AI only reads first 3 paragraphs?

| Pattern | Fix |
|---------|-----|
| **Late Caveats** | Front-load qualifications |
| **CI Collapse** ("102M" loses CI) | Add CI inline at every mention |
| **Scope Loss** | Repeat scope with each figure |
| **Conditional Loss** | Add "(under X assumption)" inline |
| **Conservative framing loss** | Bold the conservative note |

---

## Phase 4: Enhancement Opportunities

### Hardcoded Values
```bash
python scripts/preview-qmd-with-variables.py <file> --numbers-only
```
Red flags: Dollar amounts, percentages, large numbers not using `{{< var ... >}}`. Numbers in `$$` blocks should use `_latex` variables.

### Missing LaTeX
For calculated values, check for `_latex` version: `{{< var parameter_name_latex >}}`

### Citations
Prefer `@citation-key` from `references.bib` over manual superscripts. Web search for missing sources.

### Charts
Check `knowledge/figures/*<variable>*.qmd` for tornado, mc-distribution, sensitivity-table charts.

---

## Phase 5: Calculation Chain Audit

For each calculated parameter:
```bash
grep -B5 -A50 "^PARAMETER_NAME = Parameter" dih_models/parameters.py
```

| Check | Criteria |
|-------|----------|
| **Distribution** | Normal (symmetric), Lognormal (costs, positive), Beta (probabilities), Fixed (constants only) |
| **Formula** | No double-counting, independent factors, units match |
| **CI Width** | <±20% overconfident, ±30-100% reasonable, >±200% uninformative |
| **Sources** | Meta-analysis > peer-reviewed > government stats > industry reports > assumptions (flag prominently) |

---

## Phase 6: Report Template

```markdown
## Peer Review: <filename>

### Summary
[1-2 sentences]

### Issues Found
| Issue | Type | Severity | Location | Fix |

Types: methodology, sources, logic, framing, clarity, lazy-ai, hardcoded, calculation, enhancement

### Priority Actions
1. **High:** 2. **Medium:** 3. **Low:**
```

---

## Phase 7: Implement Fixes

**Do not just report. Fix all High/Medium issues using Edit tool.**

Re-read edited sections to verify. Track remaining issues with TodoWrite.

---

## Rules

1. Fix, don't just flag - implement High/Medium issues immediately
2. Verify by re-reading edited sections
3. Be specific - vague critiques aren't actionable
4. If no issues found, say "No changes needed" and stop - don't invent problems
