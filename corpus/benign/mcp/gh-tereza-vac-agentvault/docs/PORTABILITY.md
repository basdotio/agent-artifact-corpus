# Portability — take your brain anywhere

AgentVault is designed so **your knowledge is not locked to this repo, Postgres, or one vendor**.

## Source of truth = Markdown

Everything important lives under `NOTES_DIR` (default `./notes`):

- Plain `.md` files
- Optional Obsidian-style `[[wikilinks]]`
- Category = top-level folder
- Optional vault config: `NOTES_DIR/.agentvault.json`

Postgres + pgvector store **embeddings and search metadata only**. If you delete the database, you lose search speed — not the notes. Run `./av index` again to rebuild.

## Export / backup

**Recommended: git**

```bash
cd "$NOTES_DIR"
git init   # if not already
git add -A && git commit -m "brain snapshot"
# push to a private remote, e.g. agent-hq-brain
```

**One-shot archive**

```bash
tar -czf agentvault-notes-$(date +%Y%m%d).tar.gz -C "$(dirname "$NOTES_DIR")" "$(basename "$NOTES_DIR")"
```

On Agent HQ the daily copy is `gdrive:AgentHQ/Backup/brain/` (`backup_brain.sh`).

Do **not** treat the Docker `pgdata` volume as your backup of meaning — only as disposable index state.

## Import into other tools

| Target | How |
|---|---|
| **Obsidian** | Open `NOTES_DIR` as a vault |
| **Another RAG / MCP brain** | Point it at the same Markdown tree (or copy files) |
| **Notion** | Manual or scripted promote of selected notes only — not a full mirror |
| **Plain grep / editors** | Always works; no AgentVault required |

## What is *not* portable

- Embedding vectors and chunk rows in Postgres
- Model cache (e.g. Hugging Face / Torch downloads)
- Local web UI state in browser `localStorage` (`agentvault-state-v1`)

All of the above are regenerable or cosmetic.

## Agents

Agents should:

1. **Write** new knowledge as Markdown into `NOTES_DIR` (or via the web/CLI helpers).
2. **Read** via `./av search "…"` / MCP `vault_search` (and `vault_get` for full notes).
3. Never assume the DB exists on another machine — only the notes tree travels.

CLI-friendly agents (Codex, shell tools) do not need MCP: calling `./av search` is enough.

## Agent HQ layout (later)

On the VPS you can set:

```bash
NOTES_DIR=/home/agent/brain   # or a dedicated AgentVault notes clone
```

Keep films / bookmarks / tips as Markdown there. `brain_note.py` can keep writing the same tree until bots call `./av` directly.

## Notion split (locked)

- **AgentVault** — agent memory, tips, films, bookmarks, journal (portable MD).
- **Notion** — human projects (AI Academy, curricula, shared pages).
- **Drive / document index** — scanned files stay outside the vault unless you deliberately add a short summary note.
