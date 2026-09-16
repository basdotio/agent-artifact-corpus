# learn-ingest — Claude Code Skill

A guided intake skill for [Claude Code](https://claude.ai/code) that turns any learning material into structured vault notes + actionable outputs.

## What it does

Point it at a course lesson, podcast transcript, article, or Google Drive folder and it walks you through:

- **A — Insights** — key ideas, frameworks, and practical "so what"
- **B — Implement** — extracts steps and wires into a GSD project or phase
- **C — Content mining** — frameworks, quotes, and 5 post/article angles
- **D — Conversation mining** — hooks, talking points, contrarian angles for social/DMs
- **E — Skill extraction** — identifies if the lesson could become a Claude skill
- **F — Teach me** — Socratic back-and-forth to actually retain dense material
- **G — Just archive** — saves to vault, nothing else
- **H — Scan vault** — searches existing vault content by topic without ingesting anything new

## Installation

1. Copy `SKILL.md` into your Claude Code skills directory:
   ```
   ~/.claude/skills/learn-ingest/SKILL.md
   ```
2. Update the vault path in `SKILL.md` to match your own Obsidian or notes folder
3. Invoke with `/learn-ingest` in any Claude Code session

## Requirements

- [Claude Code](https://claude.ai/code) CLI
- Google Drive MCP (optional — for ingesting directly from Drive folders)
- An Obsidian vault or any local notes folder

## Vault structure

```
~/Your Vault/Courses/<Community>/<Course Name>/<lesson-slug>.md
~/Your Vault/Courses/<Community>/<Course Name>/Mining/<lesson-slug>-content-mining.md
```

## Usage

```
/learn-ingest
```

Then follow the guided prompts — material type, community/source, and action selection.

---

Built with [Claude Code](https://claude.ai/code). Part of the [Clawdia](https://github.com/Clawdia-Wonderlabs) skill library.