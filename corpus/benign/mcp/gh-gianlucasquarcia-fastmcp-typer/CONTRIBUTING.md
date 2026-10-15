# Contributing

Thanks for helping improve this FastMCP server template.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
cp .env.template .env   # adjust values as needed; never commit .env
```

## Project structure

- `mcp_server.py` only mounts the sub-servers. Add tools, resources and prompts to `mcp_server_tools.py`, `mcp_server_resources.py` and `mcp_server_prompts.py`.
- `mcp_server_cli.py` is the Typer CLI; `settings.py` holds environment-backed configuration.
- `clients/` contains example clients; `tests/` contains the tests.

See `README.md` for details.

## Conventions

- Every tool sets `title`, `description`, `tags` and `annotations` (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- Use type hints and Google-style docstrings; docstrings become MCP descriptions.
- New settings go in both `settings.py` and `.env.template`, and are documented in `README.md`.
- Add dependencies with `uv add <package>` so `pyproject.toml` and `uv.lock` stay in sync.
- Tests must not use the network; mock external APIs.

## Before opening a pull request

```bash
uv run ruff check
uv run ruff format
uv run python -m pytest
uv run tox          # full Python 3.10-3.14 matrix
```

- Coverage must stay at 100% (enforced in `pyproject.toml`).
- Update `README.md` when you change tools, resources, settings or layout.
- Keep commits focused, with clear messages.

## Releasing

Maintainers publish a release by pushing a version tag; the `Release` workflow creates the GitHub release with generated notes:

```bash
git tag v1.0.0
git push origin v1.0.0   # push the tag explicitly; --follow-tags skips lightweight tags
```

## GitHub Copilot

Repository guidance for Copilot lives in `.github/copilot-instructions.md`, `.github/instructions/` and `.github/prompts/`. Keep those files in sync with this document when conventions change.
