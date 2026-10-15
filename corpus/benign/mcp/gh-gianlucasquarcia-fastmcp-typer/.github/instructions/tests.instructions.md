---
applyTo: "tests/**/*.py"
---

# Test guidelines
- Use pytest with plain `test_*` functions; name tests after behavior (`test_sort_numbers_returns_ascending_order`).
- Call tool/resource functions directly, or via the FastMCP server for end-to-end checks; use `typer.testing.CliRunner` for CLI commands.
- Never hit the network: mock `requests` / external APIs and Ollama.
- Keep 100% coverage (see `pyproject.toml`); cover error paths and edge cases.
- Run with `uv run pytest`.
