# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

FastMCP (v4) server exposing the Lexware Office (formerly lexoffice) public API to Claude. Current scope is invoice creation plus supporting lookups (`create_invoice`, `find_contacts`, `get_invoice`). API reference: https://developers.lexware.io/docs/

## Commands

Uses `uv`, Python 3.13.

```bash
uv sync                                   # install deps
uv run pytest                             # all tests (no API key needed)
uv run pytest tests/test_server.py::test_create_invoice_retries_on_rate_limit   # single test
LEXWARE_API_KEY=... uv run --with "fastmcp>=4" --with httpx main.py   # run server over stdio
```

No linter or formatter is configured.

## Architecture

Flat layout (no package, no `__init__.py`); pytest finds modules via `pythonpath = ["."]` in `pyproject.toml`.

- `models.py`: Pydantic input models (snake_case, LLM friendly) and `build_invoice_payload`, a pure function that maps them to the camelCase JSON body for `POST /v1/invoices`. The `InvoiceDraft` model is used directly as the `create_invoice` tool argument, so its `Field(description=...)` texts become the tool's input schema seen by Claude. Cross field rules from the Lexware docs (contact id vs. one time address, required fields per line item type, vat free types need tax rate 0, period shipping types need an end date) live in `model_validator`s here.
- `lexware.py`: `LexwareClient`, an async httpx wrapper. Throttles to Lexware's limit of 2 requests per second and retries only `429` (Lexware guarantees the call was not executed). Other errors, including 500/504, are deliberately not retried so a POST cannot create duplicate invoices. `describe_error` handles both Lexware error formats (legacy `IssueList` and the newer `message`/`details`).
- `main.py`: the FastMCP server. A lifespan creates one `LexwareClient` from env vars and tools read it via `ctx.lifespan_context["lexware"]`. Tools convert `LexwareError`/`httpx` errors into `ToolError` so Claude sees readable messages. `create_invoice` does a follow up `GET` for number and totals; if that GET fails it returns a warning instead of raising, because the invoice already exists.

## Domain conventions

- Lexware dates are sent as midnight `Europe/Berlin` in `yyyy-MM-ddTHH:mm:ss.SSSXXX` (see `to_lexware_datetime`).
- Unit prices are sent as `netAmount`, or `grossAmount` when `tax_type == "gross"`. Currency is always EUR.
- Invoices are drafts by default; `finalize=true` is irreversible (binding invoice number, no edit or delete via API). Server `INSTRUCTIONS` tell Claude to finalize only on explicit user request; keep that behaviour.
- Tool annotations use MCP SDK v2 snake_case names (`read_only_hint`, not `readOnlyHint`, which is deprecated).

## Testing

`tests/test_server.py` runs the real server in memory via `fastmcp.Client(main.mcp)`. The `lexware_api` fixture monkeypatches `main.create_lexware_client` to inject an `httpx.MockTransport` (`FakeLexware` queues responses per method and path) and zeroes the throttle and backoff constants in `lexware`. Use this pattern for new tools rather than mocking `LexwareClient` methods.

## Configuration

Env vars: `LEXWARE_API_KEY` (required; server fails at startup without it), `LEXWARE_BASE_URL` (default `https://api.lexware.io`), `LEXWARE_APP_URL` (default `https://app.lexware.de`, used for invoice deep links). Install into Claude Code with:

```bash
claude mcp add lexware --scope user -e LEXWARE_API_KEY=... -- uv run --with "fastmcp>=4" --with httpx /absolute/path/to/lexoffice_mcp/main.py
```
