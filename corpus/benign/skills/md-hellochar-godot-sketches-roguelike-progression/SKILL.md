---
name: roguelike-progression-eval
description: Critically evaluate run-based game progression mechanics and provide actionable recommendations. Use when analyzing roguelike, roguelite, deckbuilder, or run-based game projects for progression system quality, build diversity, reward pacing, synergy design, or player agency. Triggers on requests to review, audit, critique, or improve progression mechanics in game projects.
---

# Roguelike Progression Evaluation

Evaluate run-based game progression systems against proven design principles. Produce specific, actionable recommendations.

## Evaluation Process

### 1. Gather Project Context

Identify and read relevant project files:
- Game design documents (GDD, progression docs)
- Item/card/ability definitions (JSON, YAML, ScriptableObjects, Resources)
- Synergy/combo configuration files
- Reward distribution logic
- Run structure definitions (floors, acts, biomes)
- Meta-progression systems

Ask clarifying questions if project structure is unclear:
- "Where are item/card definitions stored?"
- "Is there a design doc covering progression?"
- "What's the target run length?"

### 2. Analyze Against Core Dimensions

Evaluate each dimension. Score 1-5 (1=critical issues, 5=excellent). Provide specific evidence.

#### A. Power Acquisition Mechanisms

**What to look for:**
- Variety of acquisition sources (combat rewards, shops, events, bosses)
- Clear build-defining moments vs incremental upgrades
- Item/card pool size appropriate to run length (aim for 3-5x what player collects)

**Red flags:**
- Single acquisition channel dominates
- No "exciting" rare drops that transform runs
- Pool too small (repetitive) or too large (no identity)

**Benchmark:** Slay the Spire offers cards after every combat + 170 relics from varied sources.

#### B. Synergy Architecture

**What to look for:**
- Multiple viable build archetypes (minimum 3-4 per character/class)
- Synergies discoverable through play, not requiring wiki
- Both designed combos and emergent interactions
- Tags/keywords that hint at combinations

**Red flags:**
- One dominant strategy obsoletes alternatives
- Synergies require specific 3+ item combinations (too narrow)
- No way to identify synergistic items before acquiring

**Benchmark:** Balatro's Joker ordering creates emergent synergies; Enter the Gungeon has 350 named synergies with visual indicators.

#### C. Decision Quality

**What to look for:**
- Meaningful choices every 1-3 minutes
- Early choices echo through entire run
- Skip/remove options as valuable as acquire options
- Information available to make informed decisions

**Red flags:**
- "Always take X" or "never take Y" dominant strategies
- Early game decisions irrelevant to late game
- Choices presented without context for evaluation
- Optimal play is obvious

**Benchmark:** Slay the Spire's Act 1 card choices define entire run archetype.

#### D. Pacing & Reward Cadence

**What to look for:**
- Target run length 20-45 minutes
- Power milestones every 10-15 minutes
- Difficulty curve that tests builds without trivializing late game
- Build comes "online" in mid-game, not final moments

**Red flags:**
- Early game feels like waiting for real game to start
- Late game either trivial (overpowered) or hopeless (undergeared)
- Long stretches without meaningful decisions
- Runs drag past 60 minutes regularly

**Benchmark:** Hades distributes boons across 36-42 chambers with bosses at 12/24/36/final.

#### E. Agency vs Randomness Balance

**What to look for:**
- Pre-action luck (random options, player chooses) over post-action luck (commit then roll)
- Pity mechanics prevent extended bad luck streaks
- Skill is primary determinant of success
- RNG creates variety, not outcomes

**Red flags:**
- Critical resources entirely luck-dependent
- No influence over what options appear
- "Dead runs" obvious early but must be played out
- Optimal play still loses to bad RNG frequently

**Benchmark:** Hades presents 3 boon options—RNG selects pool, player chooses.

#### F. Meta-Progression Design

**What to look for:**
- Unlocks expand options horizontally (new strategies) not vertically (raw power)
- Serves as extended tutorial, gating complexity not power
- Core game winnable from early meta-state
- Reasonable unlock pace (not hundreds of hours to full roster)

**Red flags:**
- Early runs feel deliberately crippled
- Grinding required before "real game" accessible
- Power unlocks make skill irrelevant
- Unlocks don't change how game plays

**Benchmark:** Slay the Spire unlocks add cards to pool but don't increase base power.

#### G. Technical Flexibility

**What to look for:**
- Item stats in data files (JSON/YAML/ScriptableObjects), not hardcoded
- Synergy rules configurable without code changes
- Tag-based systems for extensibility
- Clear separation of balance numbers from logic

**Red flags:**
- Adding new item requires code changes
- Balance tweaks require recompilation
- No tooling for designers to iterate
- Synergies hardcoded as special cases

**Benchmark:** Data-driven design enabling weekly balance patches.

### 3. Generate Recommendations

For each dimension scoring ≤3, provide:

1. **Specific Problem**: What's wrong, with evidence from project files
2. **Impact**: How this hurts player experience
3. **Solution**: Concrete fix with implementation guidance
4. **Priority**: Critical / High / Medium / Low
5. **Reference**: Example from successful game if applicable

Prioritize recommendations by:
1. Critical: Breaks core loop or causes player abandonment
2. High: Significantly reduces replayability or satisfaction
3. Medium: Noticeable quality-of-life improvement
4. Low: Polish and refinement

### 4. Output Format

```markdown
# Progression Evaluation: [Game Name]

## Executive Summary
[2-3 sentences on overall progression health and top priorities]

## Scores

| Dimension | Score | Status |
|-----------|-------|--------|
| Power Acquisition | X/5 | 🔴/🟡/🟢 |
| Synergy Architecture | X/5 | 🔴/🟡/🟢 |
| Decision Quality | X/5 | 🔴/🟡/🟢 |
| Pacing & Cadence | X/5 | 🔴/🟡/🟢 |
| Agency vs Randomness | X/5 | 🔴/🟡/🟢 |
| Meta-Progression | X/5 | 🔴/🟡/🟢 |
| Technical Flexibility | X/5 | 🔴/🟡/🟢 |

## Critical Findings
[Issues scoring 1-2]

## Detailed Analysis
[Section per dimension with evidence and recommendations]

## Prioritized Recommendations
[Numbered list with priority tags]

## Quick Wins
[Changes implementable in <1 day with high impact]
```

## Psychological Principles Reference

When analyzing, consider these proven engagement drivers:

- **Variable Rewards**: Dopamine peaks at ~50% reward probability. Uncertainty drives anticipation.
- **Flow State**: Challenge must match skill. Brief over/underpowered moments acceptable if average is balanced.
- **IKEA Effect**: Players value builds they assembled over "meta" builds they copied.
- **Loss Aversion**: Losses feel 2x as intense as gains. Permadeath stakes must feel earned.
- **Mastery Loop**: Player skill improvement should be primary success driver, not accumulated power.

## Common Archetypes to Check

Verify project supports multiple viable approaches:

- **Glass Cannon**: High damage, low survivability
- **Tank/Control**: Survivability focus, slower kills
- **Synergy Engine**: Weak individually, powerful combinations
- **Scaling Build**: Weak early, exponential late power
- **Consistency Build**: Reliable but capped ceiling
- **High-Roll Build**: Variance-dependent, huge highs and lows
