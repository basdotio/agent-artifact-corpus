# Install instructions for mcp-notes-server (AI-installer edition)

These instructions are written so an AI installer (e.g. Cline) can set up
this server from scratch with no human input.

## What this server is

A minimal, free and open-source Model Context Protocol (MCP) server in
Python. It gives an MCP-compatible AI assistant a persistent notebook with
three tools — `create_note`, `list_notes`, `search_notes` — stored in a plain
local JSON file. Built with the official `mcp` Python SDK (FastMCP style).
No database, no cloud, no accounts, no network calls.

## Prerequisites

- Python 3.10 or newer (`python3 --version` must print 3.10+)
- `pip` (any recent version)
- `git`

## Step 1 — Clone the repo

```bash
git clone https://github.com/bradraylucas-eng/mcp-notes-server.git
cd mcp-notes-server
```

## Step 2 — Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` contains exactly one line: `mcp>=1.6.0,<2`.

- This installs the official Model Context Protocol Python SDK, v1.x.
- The `<2` upper pin is REQUIRED, not cosmetic: SDK 2.x renamed
  `FastMCP` (it became `MCPServer`) and this server's code targets the v1
  API. Installing `mcp>=2` will make `server.py` fail at import time.
- The SDK pulls its own transitive dependencies; no other packages are
  needed.

## Step 3 — Verify the install works

Run the repo's own smoke test (no MCP host needed; it stubs the SDK if it
is missing, and uses the real one when present):

```bash
python tests/smoke_test.py
```

Expected: exit code 0 and `6/6 checks passed`.

Run the end-to-end MCP protocol test (requires the real SDK from Step 2;
it launches `server.py` over stdio and calls all three tools):

```bash
python tests/mcp_e2e_test.py
```

Expected: the printed tool list `['create_note', 'list_notes', 'search_notes']`
and the line `E2E MCP PROTOCOL TEST: PASS`.

## Step 4 — Run the server

```bash
python server.py
```

The server speaks MCP over **stdio** and stays attached to the terminal
until the host closes it. It creates `notes.json` in its own folder on the
first note — that file is the entire database.

## Step 5 — Connect an MCP host

The same stdio command/args pattern works for Claude Desktop, Cline, and
most MCP hosts. Copy the config example from
`examples/claude_desktop_config.example.json`:

```json
{
  "mcpServers": {
    "notes-server": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-notes-server/server.py"]
    }
  }
}
```

Replace `/absolute/path/to/mcp-notes-server/server.py` with the real
absolute path from Step 1. (A host-agnostic variant is at
`examples/mcp-client-config.generic.json`.)

A packaged one-click bundle (`.mcpb`, installable by MCP hosts that
support bundle import) is attached to the v1.0.0 release:
https://github.com/bradraylucas-eng/mcp-notes-server/releases/tag/v1.0.0

## Step 6 — Try it

Ask your assistant: *"Create a note titled 'Shopping list' with milk, eggs,
and coffee."* Then ask: *"Search my notes for eggs."* The note persists in
`notes.json` next to `server.py`.

## Troubleshooting

- `ModuleNotFoundError: No module named 'mcp'` — redo Step 2
  (`pip install -r requirements.txt`).
- `ImportError` mentioning `FastMCP` — your environment resolved SDK 2.x;
  pin with `pip install "mcp>=1.6.0,<2"`.
- `python` launches the wrong interpreter (older than 3.10) — use
  `python3` explicitly, or set the MCP host's `command` to the venv's
  Python.

## Source of truth

Repository: https://github.com/bradraylucas-eng/mcp-notes-server
(MIT license). This install file mirrors the manual steps in README.md.
