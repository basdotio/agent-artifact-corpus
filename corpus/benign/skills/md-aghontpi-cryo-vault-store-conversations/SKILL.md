---
name: Cryo Vault CLI Interaction & Log Ingestion
description: Use this skill when asked to add/ingest new logs, or when asked to check history, search past chat logs, or retrieve previous conversations from the Cryo Vault database.
---

# Cryo Vault CLI

This skill allows you to interact with the Cryo Vault database using its native command-line interface. You can ingest logs, search conversations, and view statistics directly from the terminal.

## Setup

First, ensure the binary is built:

```bash
cargo build --release
```

The binary will be located at `target/release/cryo` (or `target/release/cryo-vault-mcp` for the MCP server, but this skill focuses on the main CLI).

**Alias for convenience:**
```bash
alias cryo="./target/release/cryo"
```

## Environment Variables

- `CRYO_DB_PATH`: Path to the database directory. Defaults to `~/.cryo`.
- `RUST_LOG`: Control logging verbosity (e.g., `error`, `warn`, `info`, `debug`, `trace`). Default is `warn`.

## Commands

### 1. Ingest Data (`add`)

Ingest chat logs from a file or standard input.

**Usage:**
```bash
cryo add [OPTIONS] [FILE]
```

**Arguments:**
- `FILE`: Path to the input file. Use `-` for stdin (default).

**Options:**
- `--stream`: Treat input as streaming output (one JSON object per line).

**Supported Formats:**
- **Single Session:** A `ChatSessionInput` JSON object.
- **List of Sessions:** An array `[ ... ]` of `ChatSessionInput` objects.
- **ChatGPT Export:** A JSON exported from ChatGPT (list of conversations).

**Examples:**
```bash
# Import a single file
cryo add my_chat_logs.json

# Import from stdin
cat logs.json | cryo add -

# Import streaming newline-delimited JSON
tail -f live_logs.jsonl | cryo add --stream -
```

### 2. Search (`search`)

Search the archive for conversations matching a query.

**Usage:**
```bash
cryo search [OPTIONS] <QUERY>
```

**Arguments:**
- `QUERY`: The search term (regex supported).

**Options:**
- `--after <DATE>`: Filter by date (YYYY-MM-DD or Unix timestamp).
- `--before <DATE>`: Filter by date (YYYY-MM-DD or Unix timestamp).
- `--json`: Output results as raw JSON.

**Examples:**
```bash
# Simple search
cryo search "rust optimization"

# Search with date range
cryo search "database" --after 2023-01-01 --before 2024-01-01

# Output JSON for processing
cryo search "error" --json | jq .
```

### 3. View Session (`show`)

Show full details of a specific session by ID.

**Usage:**
```bash
cryo show <SESSION_ID>
```

**Example:**
```bash
cryo show 550e8400-e29b-41d4-a716-446655440000
```

### 4. Browse Sessions

View the first (oldest) or last (newest) sessions.

**Usage:**
```bash
# Show last N sessions (default 10)
cryo last [COUNT]

# Show first N sessions (default 10)
cryo first [COUNT]
```

**Example:**
```bash
cryo last 5
```

### 5. Statistics (`stats`)

View database statistics, including total sessions, messages, disk usage, and time range.

**Usage:**
```bash
cryo stats
```

### 6. Maintenance (`reindex`)

Rebuild the search index from the raw data files. Useful if the index becomes corrupted or you manually moved data files.

**Usage:**
```bash
cryo reindex
```
