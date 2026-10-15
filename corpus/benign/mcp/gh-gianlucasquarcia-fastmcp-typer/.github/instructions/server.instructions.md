---
applyTo: "mcp_server*.py,settings.py"
---

# MCP server guidelines
- Define tools/resources/prompts in `mcp_server_tools.py`, `mcp_server_resources.py`, `mcp_server_prompts.py`; `mcp_server.py` only mounts them.
- Every `@mcp.tool` sets `title`, `description`, `tags`, and `annotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`); set `openWorldHint` true for external services.
- Use Google-style docstrings (Args/Returns) and full type hints.
- Use `async def` for I/O or waiting; read config from `settings`, never `os.environ` directly.
- New settings: add to `settings.py` and `.env.template`, and document in `README.md`.
