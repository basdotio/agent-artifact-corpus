---
name: lumberjack
description: Query the Forest knowledge base for project context and capture learnings. MUST USE when user asks "what do we know about", "capture this", "save this learning", "project context", or when you need prior decisions. Do NOT answer from memory - actually run forest commands.
allowed-tools: Bash, Read
context: fork
---

# Lumberjack - Forest Knowledge Base Integration

**IMPORTANT**: This skill requires ACTUALLY RUNNING forest commands. Do not answer questions about "what we know" from static docs or memory - query the live knowledge base.

Jack is Forest's dedicated companion. This skill is a portable subset of Jack's workflows, usable from any project directory.

## Required Action

When this skill triggers, you MUST run:
```bash
forest search "<relevant query>"
```

Then report what Forest found, not what you already know from CLAUDE.md.

## Project Tagging

Always tag notes with the current project:
```bash
PROJECT_TAG="#project/$(basename "$PWD")"
```

## Core Workflows

### 1. Search for Context (REQUIRED for "what do we know" questions)

**Always run this command** - do not skip it:

```bash
forest search "scoring algorithm"
forest search "API authentication pattern"
forest search "database migration"
```

After searching, read the top results with `forest read <id>` to get full content.

### 2. Capture Learnings

When you discover something useful during development:

```bash
echo "The scoring algorithm uses dual scores: semantic (embedding cosine similarity) and tag (IDF-weighted Jaccard). Edges are kept if either score exceeds its threshold." | forest capture --title "Dual score algorithm" --stdin --tags "#project/$(basename "$PWD"),#pattern/scoring"
```

Capture when:
- You discover a non-obvious pattern or convention
- You understand why a decision was made
- You encounter a gotcha or edge case
- You learn something that would help future work

### 3. Bug Reports (High Value Captures)

When you fix a bug, capture it with reproduction steps and code references:

```bash
cat <<'EOF' | forest capture --title "Bug: <one-line symptom>" --stdin --tags "#project/$(basename "$PWD"),#bug/<area>"
BUG: <one-line symptom>

REPRO:
1. <step one>
2. <step two>
3. <observe: error/unexpected behavior>

FIX: <file:line> - <what was changed>

NOTES: <why this happened, edge case that triggered it>
EOF
```

To promote a bug to a GitHub issue on Forest:

```bash
gh issue create --repo bwl/forest --label bug --title "Bug: <symptom>" --body "<details>"
```

### 4. Feature Requests

When you notice a missing capability in Forest:

```bash
cat <<'EOF' | forest capture --title "Feature: <one-line description>" --stdin --tags "#project/forest,#feature/<area>"
FEATURE: <one-line description>

USE CASE: <why this matters>
CURRENT WORKAROUND: <how you work around it today>
PROPOSED: <what the solution could look like>
EOF
```

To promote to a GitHub issue:

```bash
gh issue create --repo bwl/forest --label enhancement --title "Feature: <description>" --body "<details>"
```

### 5. Self-Correction Feedback

When the user corrects you (wrong command, missed context, bad capture), log it:

```bash
echo "WRONG: <what I did wrong>
CORRECT: <what I should have done>
LESSON: <generalized takeaway>" | forest capture --title "Feedback: <short summary>" --stdin --tags "#skill/lumberjack,#feedback/correction"
```

This helps track skill effectiveness over time. Query with:
```bash
forest search "#feedback/correction"
```

**Tag conventions:**
- `#project/<name>` - Always add for filtering by project
- `#bug/*` - Bug fixes (e.g., `#bug/scoring`, `#bug/api`)
- `#feature/*` - Feature requests (e.g., `#feature/export`, `#feature/search`)
- `#pattern/*` - Recurring patterns (e.g., `#pattern/error-handling`)
- `#decision/*` - Architectural decisions (e.g., `#decision/database-choice`)
- `#gotcha/*` - Surprising behaviors (e.g., `#gotcha/async-timing`)
- `#skill/lumberjack` - Meta: notes about the skill
- `#feedback/correction` - Meta: times the user corrected Claude

### 6. Explore Connections

Browse related concepts in the knowledge graph:

```bash
forest explore                      # Interactive exploration
forest explore --search "auth"      # Start from matching nodes
forest explore @                    # Start from last captured note
```

### 7. Link Related Concepts

Connect related ideas with bridge tags:

```bash
forest link <ref1> <ref2>
```

Use when two notes are conceptually related but weren't automatically linked.

### 8. Read Specific Notes

Deep-dive into a specific note:

```bash
forest read <ref>      # By short ID, e.g., "7fa7"
forest read @          # Last captured note
forest search --mode metadata --tags "#auth"   # Find by tag, then forest read <id>
```

## Best Practices

### Note Quality

Good captures are:
- **Specific**: "The retry logic uses exponential backoff with jitter" not "handles retries"
- **Contextual**: Include why, not just what
- **Searchable**: Use terms someone would search for

### When to Search vs Capture

**Search first** when:
- Starting a new task
- Confused about existing code
- Looking for examples

**Capture** when:
- You just figured something out
- You found a non-obvious pattern
- Future-you would want to know this

## Quick Reference

| Action | Command |
|--------|---------|
| Search | `forest search "query"` |
| Capture | `echo "..." \| forest capture --title "..." --stdin --tags "#project/$(basename "$PWD"),#pattern/<topic>"` |
| Bug report | `cat <<'EOF' \| forest capture --title "Bug: ..." --stdin --tags "#project/$(basename "$PWD"),#bug/<area>"` |
| Feature req | `cat <<'EOF' \| forest capture --title "Feature: ..." --stdin --tags "#project/forest,#feature/<area>"` |
| File issue | `gh issue create --repo bwl/forest --label bug --title "..." --body "..."` |
| Explore | `forest explore` |
| Link | `forest link <ref1> <ref2>` |
| Read | `forest read <ref>` |
| Stats | `forest stats` |

## Skill Effectiveness Tracking

To evaluate how well this skill is performing:

```bash
# See all skill-related captures
forest search "#skill/lumberjack"

# See correction feedback (where Claude made mistakes)
forest search "#feedback/correction"

# See bug reports captured
forest search "#bug"

# Tag statistics (shows capture frequency by tag)
forest tags stats
```

**Periodic review checklist:**
1. Are searches returning relevant results?
2. Are captures specific enough to be useful later?
3. Are bug reports complete (repro steps + code refs)?
4. What patterns appear in correction feedback?
