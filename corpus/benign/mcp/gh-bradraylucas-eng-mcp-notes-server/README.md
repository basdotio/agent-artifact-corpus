# mcp-notes-server

A minimal, **free and open-source** [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server in Python that gives any MCP-compatible AI assistant a persistent notebook: create notes, list them, and search them — stored in a plain local JSON file you own.

Built with the official `mcp` Python SDK (FastMCP). No database, no cloud, no accounts. Your notes never leave your machine.

## Tools

| Tool | What it does |
|---|---|
| `create_note` | Create a note with a title (required, ≤120 chars) and body (≤10,000 chars). Returns the saved record with id and timestamps. |
| `list_notes` | List saved notes, newest first (configurable limit, 1–500). |
| `search_notes` | Case-insensitive keyword search across titles and bodies. |

## Quick start

```bash
git clone <this-repo-url>
cd mcp-notes-server
pip install -r requirements.txt
python server.py
```

The server speaks MCP over **stdio**. Connect it from any MCP host — see the config examples below and in [`examples/`](examples/).

### Claude Desktop

Add to your `claude_desktop_config.json` (see [`examples/claude_desktop_config.example.json`](examples/claude_desktop_config.example.json)):

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

### Generic MCP host

See [`examples/mcp-client-config.generic.json`](examples/mcp-client-config.generic.json) — the same stdio command/args pattern works for most hosts.

## Try it

1. Connect your MCP host and ask: *"Create a note titled 'Shopping list' with milk, eggs, and coffee."*
2. Ask: *"Search my notes for eggs."*
3. Open `notes.json` (created automatically next to `server.py`) to see the raw storage — it's just JSON.

## How it works

- Storage helpers load/save a single `notes.json` file; saves are atomic (write to temp file, then replace).
- Every tool validates its input (title required and length-capped, body length-capped, search query required).
- Tool functions are ordinary Python functions decorated with `@mcp.tool()` — the type annotations become the tool input schemas. The whole server is one readable file (~150 lines), meant to be copied and adapted.

Run the smoke test (no MCP host needed):

```bash
python tests/smoke_test.py
```

Verified end-to-end over the real MCP protocol (stdio, official SDK v1.x) — tools listed, note created, searched, and listed: see `tests/mcp_e2e_test.py` and run it yourself after `pip install -r requirements.txt`. Note the requirements pin `mcp<2`: the 2.x SDK renamed FastMCP, and this code targets the v1 API.

## Scope & safety

- **Local only.** This server reads/writes one JSON file in its own folder. It makes no network calls and has no delete tool — by design, as a starter pattern.
- Treat it as a learning/prototyping base, not a hardened production service: no authentication (stdio servers are launched by your host as your user), no concurrency locking beyond atomic file replacement.

## Get the full pack

This free server is one of three starters in the **MCP Server Starter Templates** pack — the full pack adds a read-only SQLite lookup server (with a tested SQL-injection guard: SELECT-only validation) and a web-summary server skeleton, plus client configs for all three, a testing checklist, and security notes for taking MCP servers toward production.

→ **MCP Server Starter Templates (and more AI agent tools: AgentProof testing kits, LLM/RAG eval kits, verified datasets for agents): [bradray2.gumroad.com](https://bradray2.gumroad.com)**

Free samples of the paid kits live in the companion repo, **ai-agent-tools-free-samples**.

## License

MIT — see [LICENSE](LICENSE). Use it, fork it, ship it.

Copyright (c) 2026 Brad Lucas.
