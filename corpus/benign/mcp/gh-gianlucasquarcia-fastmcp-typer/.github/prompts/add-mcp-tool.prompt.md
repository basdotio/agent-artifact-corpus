---
description: Add a new MCP tool with tests and docs
---

Add a new MCP tool named `${input:toolName}` that does: `${input:purpose}`.

1. Implement it in `mcp_server_tools.py` following the existing tools: `@mcp.tool` with title, description, tags, and all four annotations; type hints; Google-style docstring.
2. Add any new configuration to `settings.py` and `.env.template`.
3. Add pytest tests in `tests/test_mcp_server.py` (mock any network calls), keeping 100% coverage.
4. Update `README.md` (features and layout).
5. Run `uv run ruff check`, `uv run ruff format`, and `uv run pytest`; fix any failures.
