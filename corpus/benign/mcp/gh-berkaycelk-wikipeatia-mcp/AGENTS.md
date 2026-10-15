# AGENTS.md

Guidance for AI coding agents that install, use, or modify this repo.

## What this is

`wikipeatia-mcp` -- a single-file MCP (stdio) server exposing:

- the [WikiPeatia](https://wikipeatia.org) wiki (MediaWiki API),
- full-text / semantic / LLM search over the Ray Peat corpus (~7K documents) at search.wikipeatia.org,
- Ray Peat's original articles from [raypeat.com](https://raypeat.com).

Read-only, no API keys, 32 tools, stdio transport, deps: `fastmcp` + `httpx` only.

## Run & install

- From a clone: `uv run --with fastmcp --with httpx python server.py`
  (or `pip install -r requirements.txt && python server.py`)
- Without cloning (the exact command users register in MCP clients):
  `uvx --from git+https://github.com/BerkayCelk/wikipeatia-mcp wikipeatia-mcp`
- Client setup (Claude Desktop/Code, Cursor, Windsurf, Hermes): see README sections
  "Client setup" and "For AI agents (automated setup)".

## Test before committing

- Smoke test (spawns the server over stdio, makes a few live calls -- keep it gentle):
  `uv run --with fastmcp --with httpx python smoke_test.py`
- Packaging check: `uv build`
- Latest-FastMCP compatibility: `uv run --with "fastmcp>=4" --with httpx python smoke_test.py`

## Conventions

- Tool docstrings are English and LLM-facing: they are the interface users' assistants
  see, so keep them precise (args, scope filters, speed caveats).
- Keep dependencies minimal (`fastmcp`, `httpx`); stay read-only with respect to upstream
  services; never add API keys.
- When adding/removing/renaming tools, update in sync: README tool tables and counts
  ("32 tools"), `EXPECTED_TOOLS` in `smoke_test.py`, and the examples if the command changes.
- Be polite to the upstream public APIs: tests make only a handful of calls, no loops,
  and `corpus_deep_ask` is slow (~30-120 s) by design.
