---
description: Add a new MCP resource with tests and docs
---

Add a new MCP resource at URI `${input:uri}` that provides: `${input:purpose}`.

1. Implement it in `mcp_server_resources.py` following the existing resources.
2. Add pytest tests in `tests/test_mcp_server.py`, keeping 100% coverage.
3. Update `README.md`.
4. Run `uv run ruff check`, `uv run ruff format`, and `uv run pytest`; fix any failures.
