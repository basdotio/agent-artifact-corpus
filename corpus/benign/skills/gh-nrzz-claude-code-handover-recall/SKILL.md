---
name: recall
description: Find what was said or decided about a topic in any past session of this project, with dates. Use when the user asks "what did we decide about X", "did we try X before", or when the handover does not cover something the current task needs.
argument-hint: [topic words]
allowed-tools: Bash(node:*) Read Grep
---

Search the past sessions of this project for: $ARGUMENTS

1. Run `node "${CLAUDE_SKILL_DIR}/../../claude-code-handover/scripts/recall.mjs" $ARGUMENTS` from the project folder. If the script or Node is missing, search instead with Grep (case-insensitive) for the words in `${CLAUDE_SKILL_DIR}/../../projects/<this folder's key>/*.jsonl`, where the key is the folder path with every character that is not a letter or digit replaced by "-", and read only the matching lines' text parts.
2. Also check DECISIONS.md and HANDOVER.md in the project folder; the script already includes them.
3. Answer in this shape: what was decided or found, when, in which session, and whether a later entry changed it. Quote short phrases, not whole turns.
4. If the answer is a decision that DECISIONS.md does not hold yet, append it there as a dated line so the next recall is instant.
