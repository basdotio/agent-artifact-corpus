---
name: memory-recall
description: Search and recall memories. Auto-triggered when a topic relates to past discussions or the user asks about previous context.
---

# Memory Recall

Search and retrieve relevant memories from the memory files.

## When to Use

This skill is auto-triggered by the Engram hook instructions. Use it when:

- The current topic might relate to past discussions
- The user references something from a previous conversation
- You're uncertain about context that may have been discussed before
- The user asks "do you remember..." or similar queries

Do NOT guess or assume — search memory files first, then respond with confidence.

## Workflow

### 1. Read Configuration

Read `.claude/memory-settings.json` to get the configured file names.

### 2. Extract Search Keywords

From the current conversation context, identify:
- Key topics, names, technologies, or concepts
- Time references ("last week", "when we discussed X")
- Specific terms the user mentioned

### 3. Search in Parallel

Execute searches across all three files simultaneously:

#### Preferences File
- Read the full file (it's small, designed to be loaded entirely)
- Extract relevant sections

#### Conversations File
- Use Grep to search for keywords
- Results are in reverse chronological order (newest first)
- Look for matching `### YYYY-MM-DD` entries and their content

#### Long-Term Memory File
- Use Grep to search for keywords
- Check across all subsections (milestones, decisions, lessons, etc.)

### 4. Synthesize Results

Combine findings from all files into a coherent response:
- Prioritize the most relevant and recent information
- Cross-reference between files (e.g., a preference change might relate to a conversation)
- Present information naturally — don't list "found in file X"

### 5. Response Style

Integrate recalled memories naturally into your response. Examples:

**Good**: "Based on our previous discussion, you decided to use PostgreSQL for this project. You also mentioned preferring connection pooling via PgBouncer."

**Bad**: "I searched memory_conversations.md and found an entry from 2025-01-15 that mentions PostgreSQL. I also found in memory_longterm.md under Architecture Decisions..."

The user should feel like you genuinely remember, not like you're reading from a database.
