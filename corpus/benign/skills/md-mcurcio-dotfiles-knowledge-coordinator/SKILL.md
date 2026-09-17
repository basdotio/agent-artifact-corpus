---
name: knowledge-coordinator
description: Coordinates knowledge capture across personal (Obsidian) and public (Jira, Confluence) bases. Triages new information and delegates to the Obsidian knowledge agent or the public knowledge agent. Use when the user says "update all my knowledge bases", "sync to Jira and Obsidian", "disseminate this", "capture everywhere", or when new information should be written to multiple systems to keep them aligned.
---

# Knowledge Coordinator

You coordinate knowledge capture so **Obsidian**, **Jira**, and **Confluence** stay aligned. You take in new information, triage it, and delegate to the right specialist agent(s). You do not perform the writes yourself—you invoke subagents with clear payloads.

## 1. When This Skill Applies

| Trigger | Action |
|---------|--------|
| "Update all my knowledge bases", "sync knowledge", "capture everywhere" | Triage and invoke one or both agents |
| "Put this in Obsidian and create a Jira ticket" | Invoke both agents with the same info |
| "Disseminate this to the team" / "document this publicly" | Invoke public-knowledge-agent only |
| "Add to my notes and organize my vault" | Invoke obsidian-knowledge-agent only |
| User provides a batch of learnings or decisions to capture | Triage each (or the set) and delegate |

When the user only wants Obsidian (e.g. "add to my notes") or only Jira (e.g. "create a ticket"), use the **obsidian-knowledge-loop** skill or **smart-jira-tickets** skill directly instead of the coordinator. Use the coordinator when **multiple systems** or **explicit alignment** is requested.

## 2. Triage: Personal vs Public

| Destination | Content type | Agent to invoke |
|-------------|--------------|-----------------|
| **Personal** | Private notes, TODOs, personal learnings, how-I-work, drafts | **obsidian-knowledge-agent** |
| **Public** | Team/org work: tickets, decisions, runbooks, Confluence docs | **public-knowledge-agent** |
| **Both** | Decision that affects both (e.g. "we decided X" → note for you, ticket or Confluence for team) | Invoke **both** with the same summary and context |

If unclear, ask once: "Should this live in your personal notes (Obsidian), in Jira/Confluence for the team, or both?"

## 3. Delegation Flow

1. **Summarize** the information to capture in 2–4 sentences (or bullets). Include: what happened, key decision/finding, and any references (code, tickets, people).

2. **Choose** agent(s):
   - Personal only → invoke **obsidian-knowledge-agent**
   - Public only → invoke **public-knowledge-agent**
   - Both → invoke **obsidian-knowledge-agent** first, then **public-knowledge-agent** (or in parallel if the UI allows), with the same summary

3. **Invoke** with a clear, self-contained prompt. Example:
   - "Capture this to Obsidian: [summary]. Optional: organize related notes under Knowledge/ and add tag #cursor. If there are TODOs, add them to my TODOs system."
   - "Capture this to Jira/Confluence: [summary]. Search for existing related issues/pages first. Create or update as appropriate; prefer commenting on existing issues over creating duplicates."

4. **Confirm** with the user what was delegated and what each agent did (after they run).

## 4. Keeping Bases Aligned

When the user asks to **align** or **sync** knowledge:

- **Same content, multiple places:** Send the same summary to each relevant agent. Mention "this should match what we put in [other system]" so agents can use consistent wording.
- **Cross-links:** Ask the Obsidian agent to add a link to the Jira issue or Confluence page in the note (once the public agent returns keys/URLs). Ask the public agent to reference the decision or doc in ticket/Confluence.
- **Periodic sync:** If the user says "make sure my notes and Jira are aligned on project X", invoke both agents with context: "Review project X; update Obsidian and Jira/Confluence so they reflect the same decisions and status."

## 5. Subagent Reference

| Agent | Name to invoke | Use for |
|-------|----------------|---------|
| Obsidian / personal | **obsidian-knowledge-agent** | Vault updates, organizing notes, TODOs, personal learnings |
| Jira / Confluence / public | **public-knowledge-agent** | Jira issues, Confluence pages, team-facing documentation |

Invoke by asking the user (or the system) to run the subagent with the payload you prepared. Example: "Use the **obsidian-knowledge-agent** subagent with the following: [payload]."

## 6. "Scheduled" check (optional)

A rule **knowledge-check-rule.mdc** (in this skill folder) makes the agent offer to update knowledge bases at conversation start and at break points. To enable: copy it into the project's `.cursor/rules/`. See [reference.md](reference.md) for details.
