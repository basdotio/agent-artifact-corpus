---
name: artifacts
description: Create and manage repo-local work artifacts for a user “task request” by generating `.artifacts/artifacts/{request_id}/` with `plan.md`, `todo.md`, and `walkthrough.md`, then indexing completed work into ChromaDB stored at `.artifacts/chroma_db/` for 7-day recall. Use when the user wants (1) a tracked/confirm-before-execute workflow, (2) a minimal final answer that links to a walkthrough, or (3) to ask “what did we do before with the artifacts skill?” and you should answer by querying the ChromaDB artifacts index.
---

# Artifacts

## Workflow

Goal: leave a durable, linkable trace of work in `.artifacts/artifacts/{request_id}/`, and answer future questions by querying the `.artifacts/` ChromaDB index (retained for 7 days).

### 0) Bootstrap the required environment under `.artifacts/` (always)

1. Create `.artifacts/.venv/` and install `chromadb` there:
   - `python3 "$CODEX_HOME/skills/artifacts/scripts/artifacts_bootstrap_env.py"`
2. After bootstrap, run all other commands using `.artifacts/.venv/bin/python` (required).

### 1) Initialize artifacts (always)

1. Run the initializer script (from repo root or anywhere inside the repo):
   - `.artifacts/.venv/bin/python "$CODEX_HOME/skills/artifacts/scripts/artifacts_init.py" --request "<user request>"`
2. The script prints paths for:
   - `.artifacts/artifacts/{request_id}/plan.md`
   - `.artifacts/artifacts/{request_id}/todo.md`
   - `.artifacts/artifacts/{request_id}/walkthrough.md`
3. Reply to the user with:
   - The `plan.md` + `todo.md` paths
   - A single confirmation question: “이대로 진행할까?”
4. Do not start implementation until the user explicitly confirms.

### 2) Execute work (after user confirmation)

1. Update `.artifacts/artifacts/{request_id}/todo.md` by checking items as they complete.
2. Do the requested work in the repo (code changes / analysis / commands).
3. Write `.artifacts/artifacts/{request_id}/walkthrough.md` as the detailed record (plan snapshot, steps, commands, files, validation). Ensure it is sufficient for a reviewer to reconstruct the work without the chat.

### 3) Index + retention (end of task)

1. Run indexing (this also prunes anything older than 7 days, both index + folders):
   - `.artifacts/.venv/bin/python "$CODEX_HOME/skills/artifacts/scripts/artifacts_index.py"`
2. The index is stored at `.artifacts/chroma_db/` (repo-local, derived).
3. If `.artifacts/chroma_db/` is missing or chromadb is not installed, initialize by running the indexer once with a Python environment located under `.artifacts/` (required).

### 4) Answering “what did we do before?” (query mode)

1. Query the artifacts index:
   - `.artifacts/.venv/bin/python "$CODEX_HOME/skills/artifacts/scripts/artifacts_query.py" "<question>"`
2. Use the returned results as the basis for your answer.
3. In your reply, include the `todo.md` + `walkthrough.md` paths for the most relevant result(s).

## Output rules (important)

When responding after work is done, keep the answer minimal:

1. Include clickable paths to:
   - `.artifacts/artifacts/{request_id}/todo.md`
   - `.artifacts/artifacts/{request_id}/walkthrough.md`
2. Keep prose to 1–3 short sentences: what instruction you received + what you did.
3. Do not paste the walkthrough into the chat; the walkthrough is the source of detail.

## Reference

- File format + retention details: `references/artifacts_format.md`
