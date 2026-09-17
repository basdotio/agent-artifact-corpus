---
name: auto-evolution
description: "Memory-driven self-evolution layer for Agent Skills. Captures usage patterns, learns from errors, and automatically generates reusable knowledge. Use when you want your agent to learn from experience, track skill effectiveness, or generate improvement suggestions."
---

# Auto-Evolution: Memory-Driven Self-Evolution for Agent Skills

Transform your agent from a static assistant into a **learning system** that evolves with every interaction.

## What Makes This Different

```
Traditional Skills:  User → Agent → Output (static)

Auto-Evolution:      User → Agent → Output
                              ↓
                        [Capture] → [Memory] → [Learn] → [Evolve]
                              ↓
                     Agent gets smarter over time
```

## Quick Start

### 1. Enable Hooks

Add to your `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Read|Write|Edit|Bash", "hooks": [{"type": "command", "command": "bash .claude/skills/evolution/hooks/capture.sh \"$TOOL_NAME\" \"$TOOL_INPUT\""}]}],
    "PostToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "bash .claude/skills/evolution/hooks/capture.sh post-bash \"$TOOL_OUTPUT\" \"$EXIT_CODE\""}]}],
    "Stop": [{"matcher": "", "hooks": [{"type": "command", "command": "bash .claude/skills/evolution/hooks/reflect.sh"}]}]
  }
}
```

### 2. Work Normally

Just use Claude Code as you always do. The system silently captures:
- Which skills you use
- Commands that succeed or fail
- Patterns that repeat

### 3. See Your Evolution

At session end, open `reports/dashboard.html` for a visual summary.

---

## Core Concepts

### Three-Layer Memory System

| Layer | Purpose | Retention | Example |
|-------|---------|-----------|---------|
| **Episodic** | Raw events | 7 days | "Used layout.md at 14:32" |
| **Semantic** | Patterns | 30 days | "TypeScript errors often follow X" |
| **Procedural** | How-to knowledge | Permanent | Ready-to-use skill drafts |

### The Evolution Loop

```
┌─────────────────────────────────────────────────────────┐
│                                                          │
│   ┌──────────┐     ┌──────────┐     ┌──────────┐        │
│   │  Capture │ ──▶ │  Analyze │ ──▶ │  Evolve  │        │
│   │  Events  │     │  Patterns│     │  Skills  │        │
│   └──────────┘     └──────────┘     └──────────┘        │
│        ▲                                   │            │
│        │           ┌──────────┐           │            │
│        └────────── │  Memory  │ ◀─────────┘            │
│                    │  System  │                         │
│                    └──────────┘                         │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

---

## Commands

### `/retrospective` - Session Review

Ask Claude to generate a session retrospective:

```
User: /retrospective
```

Produces:
- Skills used with frequency counts
- Errors encountered and resolutions
- Patterns detected
- Improvement suggestions

### `/evolve` - Promote Knowledge

When you discover a reusable pattern:

```
User: This error handling approach is useful. /evolve it to a skill.
```

Claude will:
1. Extract the pattern
2. Create a skill draft in `community/`
3. Add validation criteria

### `/dashboard` - Visual Report

```
User: /dashboard
```

Opens the visual evolution dashboard showing:
- Session statistics
- Memory state
- Skill effectiveness heatmap
- Improvement opportunities

---

## Configuration

Edit `config.json`:

```json
{
  "memory": {
    "episodic_ttl_days": 7,
    "semantic_ttl_days": 30,
    "pattern_threshold": 3
  },
  "capture": {
    "ignore_exit_codes": [1],
    "ignore_patterns": ["grep|rg|test"],
    "force_patterns": ["error|fatal|panic"]
  },
  "evolution": {
    "auto_draft": true,
    "require_validation": true,
    "min_occurrences": 3
  }
}
```

---

## File Structure

```
evolution/
├── SKILL.md           # This file
├── config.json        # All settings
├── memory/
│   ├── episodes.jsonl # Raw events (append-only)
│   ├── patterns.json  # Detected patterns
│   └── drafts/        # Skill candidates
├── hooks/
│   ├── lib.sh         # Shared utilities
│   ├── capture.sh     # Event capture
│   └── reflect.sh     # Session reflection
├── reports/
│   ├── dashboard.html # Visual dashboard
│   └── sessions/      # Session reports
├── templates/
│   └── skill.md       # Skill template
└── community/
    └── README.md      # Contribution guide
```

---

## Quality Gates

Skills evolve through stages:

```
[Detected] ──▶ [Draft] ──▶ [Validated] ──▶ [Promoted]
    │             │            │              │
    │             │            │              └─ Becomes official skill
    │             │            └─ Verified to work
    │             └─ Structured documentation
    └─ Pattern appears 3+ times
```

---

## Integration

Works with any skills library. Just copy `evolution/` to your `.claude/skills/` directory.

For advanced integration, see [ARCHITECTURE.md](ARCHITECTURE.md).
