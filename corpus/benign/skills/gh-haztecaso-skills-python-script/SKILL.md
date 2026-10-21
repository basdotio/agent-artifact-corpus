---
name: python-script
description: Use when writing or developing python scripts — deciding script vs uv project, structuring code, picking dependencies, or verifying with ruff/ty. Covers PEP 723 inline metadata + uv shebang for self-contained scripts, and uv project setup for larger cases.
---

# Python script development

## Scope

Use python when task needs structured data handling, HTTP/API calls, parsing, or non-trivial logic beyond what shell pipes/coreutils handle cleanly. Not for simple file ops or command pipelines — that's bash's job.

- **Self-contained script** (default): fits in one file, no internal module structure, run once or a handful of times. Use PEP 723 inline deps + uv shebang, see below.
- **uv project (`pyproject.toml`)**: task grows past one file — multiple modules, tests, reusable library code, CLI with subcommands, packaging, or deps needing a lockfile. Use `uv init`.

Rule of thumb: tempted to split into multiple files or add `tests/`? It's a project, not a script.

**Never decide autonomously to start as, or migrate to, a uv project.** Always confirm with user first, even when task clearly grew past single-file scope.

## General rules

**Iterative development**: for quick checks (e.g. inspecting a response format, testing a snippet), use direct command execution (bash, python one-liners) instead of writing the script upfront. For the script itself, iterate: implement a basic version, run it, and use the actual output/results to guide the next implementation step, rather than trying to get it complete in one pass.

**Comments and docstrings**: comments should rarely be needed. Prefer readable code — good naming, clear structure, well-known patterns — over explaining it with comments. Only comment non-obvious WHY (hidden constraint, workaround, surprising behavior). Docstrings follow Google style, and are not always necessary — add them when a function's purpose/params/return aren't already clear from its signature and name.

**Naming conventions**: follow PEP 8 — `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_SNAKE_CASE` for module-level constants, leading underscore for internal/private helpers.

**Splitting into functions**: split when logic is reused, when a block does one clearly nameable thing worth isolating, or when it helps testability/readability. For a short linear script, keep it flat — don't split just to split.

**`if __name__ == "__main__":`**: always use this guard for the script's entry point, even in single-file scripts. Keeps top-level code importable/testable and avoids side effects on import.

**When to ask the user**: don't guess silently on decisions with real tradeoffs. Ask or confirm before proceeding when facing:
- Script vs uv project (already covered above, always confirm).
- Scope ambiguity: unclear whether a feature/edge case is actually needed.
- Anything touching production systems, external services with side effects, or irreversible actions.

For everything else — naming, internal structure, minor style choices — just decide and move on.

## Patterns

- **Type hints**: use extensively, including modern syntax (`X | None`, `list[str]`, `TypedDict`, `Protocol`, generics) whenever it clarifies intent. Skip only when it adds noise without value.
- **Structured data — dataclasses vs TypedDict vs pydantic**:
  - `dataclasses`: internal data with behavior (methods), no need for runtime validation, no external input parsing.
  - `TypedDict`: shape for plain dicts (e.g. JSON-like structures), no validation needed, lightest weight.
  - `pydantic`: validating external input (API responses, CLI args, config files), need for coercion/serialization, or nested validation rules.
- **Config and secrets**:
  - Simple case: `.env` file + `python-dotenv` for secrets/config values.
  - When config grows (many fields, nested structure, validation needed): switch to `pydantic-settings`, which supports `.env` file loading natively.
- **Dry-run flag**: any destructive script (deletes, overwrites, external side effects) must support a `--dry-run` flag that shows what would happen without doing it.
- **Error handling**: fail fast on unrecoverable errors. Error messages must be explicit and actionable (what failed, why, what to do). Use `sys.exit(1)` for unrecoverable failures, don't swallow exceptions silently.
- **Asyncio**: use when parallelizing I/O-bound work makes sense (multiple HTTP calls, concurrent file/network operations). Don't introduce it for purely sequential or CPU-bound scripts.
- **Logging** — stdlib `logging` vs `rich` vs `loguru`:
  - stdlib `logging`: default choice, no extra dependency, fine for most scripts.
  - `rich` (`RichHandler`): when the script already uses `rich` for output, want colored/formatted log lines matching the rest of the terminal output.
  - `loguru`: when you want a simpler API than stdlib logging with less setup (no manual handler/formatter config), for scripts with non-trivial logging needs (multiple sinks, structured logging).
- **Context managers**: use for anything with acquire/release semantics — file handles, network/db connections, temp dirs, locks. Prefer stdlib context managers (`open`, `tempfile.TemporaryDirectory`) or write a small `@contextmanager` for custom cleanup, over manual try/finally.
- **Retry/backoff**: for simple cases (one or two retries, fixed delay) a plain loop with try/except is enough. For anything more (exponential backoff, jitter, conditional retry on specific exceptions), use `tenacity` instead of hand-rolling it.

## Common packages and dependencies

Prefer zero dependencies when the task can be solved with stdlib alone (`pathlib`, `argparse`, `dataclasses`, `json`, `urllib`). Only reach for a package when it meaningfully simplifies the task.

- **`pathlib`** (stdlib): always prefer over `os.path` for filesystem paths.
- **`httpx`**: use when you need async HTTP, HTTP/2, or richer client features. For simple synchronous requests, plain `requests` is enough.
- **`click`**: for CLIs beyond trivial `argparse` usage (subcommands, option groups, shell completion).
- **`polars`**: prefer over `pandas` for data-heavy one-offs — faster, more ergonomic API.
- **`pydantic`**: validating/parsing external or structured data (see Patterns above).
- **TUI/output**:
  - `rich`: formatted terminal output, tables, progress bars, syntax highlighting — default choice for nicer CLI output.
  - `tqdm`: simple progress bars when `rich` is overkill.
  - `textual`: full TUI apps — only when an interactive terminal UI is actually justified by the task, not for basic output.
- **`fastapi`**: prefer over `flask` for any script that exposes an HTTP API — modern, typed, async-native.
- **`beautifulsoup4`**: HTML parsing/scraping.
- **`sqlmodel`**: when a script needs a database layer with typed models (combines SQLAlchemy + pydantic).
- **`loguru`**: simpler logging setup than stdlib, for scripts with non-trivial logging needs (see Patterns above).
- **`tenacity`**: retry/backoff beyond a simple loop (see Patterns above).

## Verification

- Prefer running one-off utilities via `uvx` instead of installing them (e.g. `uvx ruff check`).
- Before considering a script done, run in order:
  1. `ruff check`
  2. `ruff format`
  3. `ty check`
- If the script has a `--dry-run` mode, run it before the real execution.

## Security

- Never hardcode secrets (API keys, tokens, passwords) in the script. Load them from environment variables or a `.env` file, kept out of version control.
- Before running a script that touches production systems or external services with side effects, confirm with the user first — don't decide autonomously that it's safe to run.
- Never `eval`/`exec` on external or untrusted input.
- Subprocess: avoid `shell=True` with unsanitized input (command injection risk); prefer passing args as a list.
- Validate/sanitize file paths built from external input to avoid path traversal.
- Avoid `pickle` (or other insecure deserialization) on untrusted data; prefer `json`.
- HTTP clients: keep TLS verification on; don't disable it (`verify=False`) without explicit justification.
- Set restrictive permissions (`chmod 600`) on generated files containing secrets/config.
- Don't log secrets, tokens, or PII, even accidentally (e.g. logging full request/response objects).
- Pin dependency versions, and double-check package names before adding them (typosquatting risk).

## Self contained scripts

The PEP 723 `dependencies` block is optional. If the script can be implemented with stdlib only, omit it — don't add empty or unnecessary dependency declarations.

You will use uv shebang and PEP 723 inline metadata format to specify
dependencies. You can use the following as an example to start from when
implementing new scripts:

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx>=0.27.0",
#   "rich>=13.0.0",
# ]
# ///

import httpx
from rich import print

response = httpx.get("https://api.github.com")
print(f"[green]Status: {response.status_code}[/green]")
```

To make the script executable you can use chmod.

```python
chmod +x script.py
./script.py
```
