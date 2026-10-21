# masterfabric-academy MCP

<p align="center">
  <img src="./assets/masterfabric-academy-logo.png" alt="MasterFabric Academy" width="88" />
  <br /><br />
  <strong>MCP Interactive Learning</strong><br />
  Flow &amp; Project Planning
</p>

<p align="center">
  <img src="./assets/mcp-interactive-learning-banner.png" alt="MCP Interactive Learning — Flow & Project Planning" width="100%" />
</p>

> [!IMPORTANT]
> **Interactive learning & project planning** — Use this MCP to drive day-by-day teaching and phase-aligned project plans. Prefer official `days/` lessons over improvising a syllabus. Start with [EXAMPLES.md](./EXAMPLES.md).

Local Model Context Protocol server for the [MasterFabric 100-Day](../README.md) education repo.

Agents connect here to teach as an **instructor / staff engineer** stack and walk learners through official day-by-day curricula under `days/`.

| | |
| ---: | --- |
| **Examples (English)** | **[EXAMPLES.md](./EXAMPLES.md)** — copy-paste chats & smoke tests |
| **Teaching skill** | [skills/masterfabric-academy/SKILL.md](./skills/masterfabric-academy/SKILL.md) |
| **Cursor config** | [`.cursor/mcp.json`](../.cursor/mcp.json) |
| **Go Day 1** | [`days/go/1.md`](../days/go/1.md) |
| **Go roadmap** | [`days/go/go_roadmap.md`](../days/go/go_roadmap.md) |

---

## Quick test (deep links)

Want to verify the MCP in under two minutes?

1. [Install dependencies](#setup)
2. [Confirm Cursor wiring](#cursor-config)
3. Open **[EXAMPLES.md → Smoke test checklist](./EXAMPLES.md#smoke-test-checklist)**
4. Paste the **[one-shot prompt](./EXAMPLES.md#e--one-shot-copy-paste-prompt)** or start with **[Go Day 1](./EXAMPLES.md#a--start-go-from-day-1)**

| Fast path | Link |
| --- | --- |
| Start Go Day 1 chat | [Example A](./EXAMPLES.md#a--start-go-from-day-1) |
| Resume mid-track | [Example B](./EXAMPLES.md#b--resume-go-mid-track) |
| Roadmap / phases | [Example C](./EXAMPLES.md#c--roadmap--phase-planning) |
| Personas + skill load | [Example D](./EXAMPLES.md#d--load-personas--skill-then-teach) |
| Copy-paste one-shot | [Example E](./EXAMPLES.md#e--one-shot-copy-paste-prompt) |
| Expected reply shape | [Example F](./EXAMPLES.md#f--expected-agent-reply-shape) |
| Tool cheat sheet | [Tools in EXAMPLES](./EXAMPLES.md#tool-cheat-sheet) |
| All tracks swap table | [More tracks](./EXAMPLES.md#more-tracks-swap-track) |

---

## What it provides

| Capability | MCP tool |
| --- | --- |
| Mentor personas (instructor, staff eng, security, delivery) | `get_mentor_persona` |
| Day-by-day academy skill | `get_academy_skill` |
| Track catalog | `list_tracks` |
| Roadmap + phase blocks | `get_roadmap` |
| Official day lesson | `get_day_lesson` |
| Session bootstrap (persona + skill + day) | `start_learning_session` |
| Cadence / tomorrow plan | `guide_next_steps` |
| List persona summaries | `list_personas` |
| List day files on disk | `list_days` |

Single skill (source of teaching workflow):

[`mcp/skills/masterfabric-academy/SKILL.md`](./skills/masterfabric-academy/SKILL.md)

Persona implementation:

[`mcp/lib/persona.ts`](./lib/persona.ts)

---

## Setup

```bash
cd mcp
npm install
```

## Run

```bash
npm start
# or
npx tsx mcp.ts
```

Stdio only — hosts spawn this process and speak JSON-RPC on stdin/stdout. Log with `console.error` only.

---

## Cursor config

Project file: [`.cursor/mcp.json`](../.cursor/mcp.json)

```json
{
  "mcpServers": {
    "masterfabric-academy": {
      "command": "npx",
      "args": ["tsx", "mcp/mcp.ts"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

After enabling the server:

1. Paste a prompt from **[EXAMPLES.md](./EXAMPLES.md)**
2. Or call `start_learning_session` with `track=go`, `day=1`, and your goal
3. Teach from the returned brief (do not invent alternate days)
4. Call `guide_next_steps` when the day is done

---

## Mentor persona flow

Default stack (composed by `start_learning_session` / `get_mentor_persona`):

| ID | Role |
| --- | --- |
| `lead-instructor` | Day-by-day teaching from official lessons |
| `staff-engineer` | High-traffic, maintainable engineering standards |
| `security-coach` | Secure defaults and threat-aware habits |
| `delivery-manager` | Cadence, milestones, definition of done |

Priority when advice conflicts: **safety → curriculum day → production quality → delivery tempo**.

See the full English walkthrough: **[EXAMPLES.md → Example D](./EXAMPLES.md#d--load-personas--skill-then-teach)**.

---

## Layout

```
mcp/
  README.md              # This file
  EXAMPLES.md            # English chat examples & smoke tests
  assets/
    masterfabric-academy-logo.png
    mcp-interactive-learning-banner.png
  mcp.ts                 # MCP server entry
  lib/
    curriculum.ts        # Track/day/roadmap readers
    persona.ts           # Mentor personas
  skills/
    masterfabric-academy/
      SKILL.md           # Day-by-day teaching skill
  package.json
  tsconfig.json
```

---

## Related

| Doc | Link |
| --- | --- |
| Chat examples (English) | [EXAMPLES.md](./EXAMPLES.md) |
| Academy skill | [SKILL.md](./skills/masterfabric-academy/SKILL.md) |
| Trainee paths | [LEARNING_PATHS.md](../trainee/LEARNING_PATHS.md) |
| Intern workflow | [pr_and_commit_guide.md](../interns/pr_and_commit_guide.md) |
| Repository overview | [Root README](../README.md) |
