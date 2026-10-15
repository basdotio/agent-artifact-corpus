---
name: mac-disk-cleanup
description: >-
  Frees disk space on macOS safely (mode B): audits usage, auto-cleans
  regenerable caches (Xcode DerivedData, Homebrew, npm, Docker prune of
  unused data), and asks before risky deletes (simulators, volumes, old
  projects). Use when the user asks to liberar espacio, free disk space,
  clean Mac storage, clear caches, Xcode DerivedData, Docker disk usage,
  brew cleanup, npm cache, or the disk is almost full.
---

# Mac Disk Cleanup (mode B)

Portable **Agent Skill** (`SKILL.md`) for any coding agent with shell access (Claude Code, Codex, Cursor, Gemini CLI, OpenCode, etc.).

Safe-by-default macOS cleanup focused on **Xcode, Docker, Homebrew, and npm**.

Resolve script paths relative to this skill directory (where `SKILL.md` lives).

## Policy (mode B)

| Tier | Action | Examples |
|------|--------|----------|
| **Safe** | Audit → report sizes → clean **without** asking (then report freed GB) | Xcode DerivedData, Homebrew cache, `npm cache clean --force`, `docker system prune` (no volumes) |
| **Risky** | Audit → propose with size + impact → **wait for explicit yes** | Delete Simulator runtimes, `docker system prune --volumes`, remove unused Xcode, wipe Archives |
| **Never** | Do not touch | `~/Documents`, Photos libraries, Keychains, SSH keys, `.env`, active project source (unless user names a path) |

Always start with an **audit**, never with deletes.

Respond to the user in **their language** (Spanish if they wrote in Spanish). Keep skill internals and script comments in English.

## Workflow

Copy and track:

```
Cleanup Progress:
- [ ] 1. Baseline free space
- [ ] 2. Audit (Xcode / Docker / Homebrew / npm)
- [ ] 3. Clean Safe tier
- [ ] 4. Propose Risky tier (sizes + one-line risk)
- [ ] 5. On approval only: run Risky items
- [ ] 6. Final free-space delta
```

### 1. Baseline

```bash
df -h /
```

Record Available before any cleanup.

### 2. Audit

Prefer the bundled script (from the skill directory):

```bash
bash scripts/audit.sh
```

If the script is missing, run the equivalent commands in [reference.md](reference.md).

### 3. Clean Safe tier

```bash
bash scripts/clean-safe.sh
```

Or follow Safe commands in [reference.md](reference.md). Skip any tool that is not installed; do not install tools just to clean.

### 4–5. Risky tier

Present a short table: item | size | risk | exact command.  
Run **only** items the user approved (by name or number). Never batch-approve implied consent from “limpia todo” for Risky items—clarify first.

### 6. Report

```bash
df -h /
```

Report: before → after → approximate freed space. List what was cleaned vs skipped.

## Output template

```markdown
## Disco / Disk
- Libre antes / Free before: …
- Libre después / Free after: …
- Liberado / Freed: ~…

## Safe (hecho / done)
- …

## Risky (pendiente de OK / awaiting OK)
| # | Ítem | Tamaño | Riesgo | Comando |
|---|------|--------|--------|---------|
| 1 | … | … | … | … |
```

## Hard rules

1. No `sudo rm -rf` on system paths.
2. No deleting user Documents/Desktop/Downloads wholesale.
3. Docker: Safe = `docker system prune -f` (unused containers/networks/images). Volumes need explicit OK.
4. Xcode: Safe = DerivedData + device support caches listed as Safe in reference. Simulator runtimes = Risky.
5. If free space is critical (<5 GB), prioritize Safe cleanup first, then ask about the largest Risky item only.

## Additional resources

- Command catalog and paths: [reference.md](reference.md)
