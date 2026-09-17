---
name: philosophy-guide
description: This skill should be used when the user asks about "Trinity Score", "5 pillars", "眞善美孝永", "philosophy", "ethical AI decisions", or discusses the AFO Kingdom's guiding principles. Provides comprehensive guidance on applying the 5-pillar philosophy to development decisions.
version: 1.0.0
license: MIT
compatibility:
  - claude-code
  - codex
  - cursor
metadata:
  category: governance-philosophy
  author: AFO Kingdom
  philosophy_version: "2.0"
allowed-tools:
  - Read
  - Bash
  # MCP tools (optional - AFO Kingdom 환경에서만 지원)
  # - mcp__trinity-score-mcp__calculate
standalone: true
---

# AFO Kingdom Philosophy Guide (眞善美孝永)

The philosophical foundation of AFO Kingdom, guiding all decisions through the wisdom of 5 pillars.

## The 5 Pillars (五柱)

### 眞 (Truth / Jin) - 35%
> "What is technically correct?"

**Application:**
- Code must be type-safe and verifiable
- Claims must be backed by evidence
- Documentation must match implementation

**Questions to Ask:**
- Is this implementation accurate?
- Does it follow established patterns?
- Can this be verified?

**Related Commands:** `/check` (Pyright gate)

---

### 善 (Goodness / Seon) - 35%
> "What is ethically sound?"

**Application:**
- Code must not harm the system or users
- Tests must cover critical paths
- Changes must be reversible

**Questions to Ask:**
- Does this cause harm?
- Is there adequate testing?
- Can we rollback safely?

**Related Commands:** `/check` (pytest gate), `/rollback`

---

### 美 (Beauty / Mi) - 20%
> "What is elegant and clear?"

**Application:**
- Code must be readable and maintainable
- UX must minimize cognitive load
- Error messages must be helpful

**Questions to Ask:**
- Is this code clean?
- Can a new developer understand this?
- Is the user experience smooth?

**Related Commands:** `/check` (Ruff gate)

---

### 孝 (Serenity / Hyo) - 8%
> "What brings peace?"

**Application:**
- Operations should be frictionless
- Users should not be confused
- One-shot execution when possible

**Questions to Ask:**
- Is this low friction?
- Does it reduce cognitive load?
- Can this run without intervention?

**Related Tools:** SixXon CLI Humility Protocol

---

### 永 (Eternity / Yeong) - 2%
> "What endures?"

**Application:**
- Decisions must be documented
- Evidence must be preserved
- Knowledge must be transferable

**Questions to Ask:**
- Is this documented?
- Will future developers understand why?
- Is there an evidence trail?

**Related Commands:** `/evidence`, `/ssot`

---

## Trinity Score Formula

```
Trinity Score = (眞 × 0.18) + (善 × 0.18) + (美 × 0.12) + (孝 × 0.40) + (永 × 0.12)
```

## Decision Matrix

| Trinity Score | Risk Score | Decision |
|--------------|------------|----------|
| >= 90 | <= 10 | AUTO_RUN |
| 70-89 | 11-30 | ASK_COMMANDER |
| < 70 | > 30 | BLOCK |

## The 3 Strategists

When making decisions, consult the 3 strategists:

| Strategist | Pillar | Role |
|------------|--------|------|
| **장영실** (Jang Yeong-sil) | 眞 | Long-term vision, architecture |
| **이순신** (Yi Sun-sin) | 善 | Risk assessment, stability |
| **신사임당** (Shin Saimdang) | 美 | UX, communication, clarity |

Use `/strategist` to get their perspectives on any decision.

## Daily Practice

1. **Before coding**: Ask "Which pillar does this serve?"
2. **During review**: Evaluate against all 5 pillars
3. **Before commit**: Run `/trinity` to calculate score
4. **After completion**: Record evidence with `/evidence`

## Philosophy in Action

```
[Task Received]
     ↓
[/trinity] → Calculate Score
     ↓
Score >= 90? → AUTO_RUN
     ↓ No
[/strategist] → Get Consensus
     ↓
Consensus? → ASK_COMMANDER
     ↓ No
BLOCK → Improve & Retry
```
