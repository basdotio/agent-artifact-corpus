# FastMCP Server template
![Python](https://img.shields.io/badge/python-3.10%20--%203.14-blue.svg)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://docs.astral.sh/uv/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

A small FastMCP server example with a Typer CLI wrapper, HTTP and stdio client examples, and a bridge for local Ollama models.

## Features

- Exposes a `long_running_greet` MCP tool that simulates a slow async task
- Exposes a `time` MCP tool that returns the current UTC time
- Exposes an `open_meteo_current_forecast` MCP tool that fetches live weather data from the Open-Meteo API
- Adds titles, tags, and MCP annotations to tools so clients can identify capabilities and
  read-only, idempotency, destructive, and external-service hints
- Includes a Typer CLI for starting the server with stdio or HTTP transport
- Uses environment-based settings for the default port, transport, and simulated task delay
- Includes HTTP, stdio, and Ollama-bridging client examples

## Project layout

- `mcp_server.py` — assembles the FastMCP server by mounting the tools and resources sub-servers
- `mcp_server_tools.py` — MCP tool definitions (`long_running_greet`, `sort_numbers`, `open_meteo_current_forecast`)
- `mcp_server_resources.py` — MCP resource definitions (greeting, config, time, GPS position)
- `mcp_server_cli.py` — Typer CLI entry point (`run`, `list-tools` commands)
- `settings.py` — environment-backed configuration
- `clients/mcp_http_client.py` — HTTP MCP client that connects to a running server
- `clients/mcp_stdio_client.py` — stdio client that spawns the server as a subprocess
- `clients/ollama_mcp_client.py` — bridges a local Ollama model to this MCP server's tools over stdio
- `clients/ollama_mcp_http_client.py` — same Ollama bridge, but over streamable-http against an already-running server
- `tests/test_mcp_server.py` — tests for tool behavior and CLI commands
- `.env.template` — template for local environment configuration
- `CONTRIBUTING.md` — contributor guide
- `SECURITY.md` — security policy and vulnerability reporting
- `.github/copilot-instructions.md` — repository-wide GitHub Copilot instructions
- `.github/instructions/*.instructions.md` — path-scoped Copilot instructions (tests, server, clients)
- `.github/prompts/*.prompt.md` — reusable Copilot prompts (`/add-mcp-tool`, `/add-mcp-resource`, `/review-changes`)

## Setup

Install dependencies with [uv](https://docs.astral.sh/uv/):

```bash
uv sync
```

Copy the environment template and adjust values as needed:

```bash
cp .env.template .env
```

The project metadata in `pyproject.toml` declares the dependencies:

- `fastmcp`
- `typer`
- `pytest`
- `requests`
- `ollama`

## Configuration

Settings are read from environment variables. On startup, `settings.py` loads the
repository-local `.env` file when present; explicitly set environment variables take
precedence (see `settings.py` and `.env.template`):

- `MCP_SERVER_DEFAULT_PORT` (default: `8000`)
- `MCP_SERVER_DEFAULT_TRANSPORT` (default: `stdio`)
- `LONG_RUNNING_TASK_FAKE_DELAY` (default: `5`) — seconds `long_running_greet` sleeps to simulate a slow task
- `HTTP_REQUEST_TIMEOUT` (default: `10`) — seconds to wait for Open-Meteo requests
- `HTTP_REQUEST_TLS_VERIFY` (default: `true`) — whether to verify HTTPS certificates

## Using uv

Run the server:

```bash
uv run mcp_server.py run
uv run mcp_server.py run --transport streamable-http --port 8000
```

Run a client:

```bash
uv run clients/mcp_http_client.py
uv run clients/mcp_stdio_client.py
uv run clients/ollama_mcp_client.py "What time is it?"
uv run clients/ollama_mcp_http_client.py "What time is it?"
```

Run tests:

```bash
uv run coverage run -m pytest -v
uv run coverage report
```

Run the full test suite (pytest and `test.py`) across Python 3.10–3.14 with [tox](https://tox.wiki/) (requires those interpreters to be installed and discoverable, e.g. via `py -0p`):

```bash
uv run tox
uv run tox -e py312  # run a single environment
```

Add a new dependency (updates `pyproject.toml` and `uv.lock`):

```bash
uv add <package>
```

## Run the server

Run in stdio mode (default):

```bash
uv run mcp_server.py run
```

Run in HTTP mode:

```bash
uv run mcp_server.py run --transport streamable-http --port 8000
```

The CLI defaults (`transport`, `port`) come from `settings.py`, which reads `MCP_SERVER_DEFAULT_TRANSPORT` and `MCP_SERVER_DEFAULT_PORT` from the environment.

## Run with Docker

Build the image:

```bash
docker build -t fastmcp-typer .
```

Run it (the image defaults to `streamable-http` transport on port 8000, bound to all interfaces via `FASTMCP_HOST=0.0.0.0`):

```bash
docker run --rm -p 8000:8000 fastmcp-typer
```

The server will be reachable at `http://localhost:8000/mcp`. Override settings with `-e`, e.g. `-e MCP_SERVER_DEFAULT_PORT=9000 -p 9000:9000`.

## List registered tools

```bash
uv run mcp_server.py list-tools
```

This calls the Typer `list_tools` command and prints the name, description, parameters, and output schema of each registered MCP tool.

## Start the HTTP client

Start the server in HTTP mode first:

```bash
uv run mcp_server.py run --transport streamable-http --port 8000
```

Then run the client:

```bash
uv run clients/mcp_http_client.py
```

The client connects to `http://localhost:8000/mcp` and calls the `time` and `long_running_greet` tools.

## Start the stdio client

This client launches the server as a subprocess and communicates with it over stdin/stdout — no separately running server is needed:

```bash
uv run clients/mcp_stdio_client.py
```

The script starts `mcp_server.py run` using the current Python interpreter and calls the `time` tool over stdio transport.

## Connect a local Ollama model

Two variants of the same bridge are provided, depending on which MCP transport you want to use. Both:

1. Connect to the MCP server and list its tools
2. Convert the tool definitions into the `tools` schema Ollama's chat API expects
3. Send your prompt to the model
4. If the model responds with a tool call, forward it to the MCP server via `call_tool`, feed the result back to the model, and repeat until the model returns a final answer

Prerequisites for both:

```bash
ollama serve
ollama pull llama3.1   # any tool-calling capable model
```

### stdio variant

`clients/ollama_mcp_client.py` starts `mcp_server.py` as a stdio subprocess itself (same pattern as `mcp_stdio_client.py`), so no server needs to be running beforehand:

```bash
uv run clients/ollama_mcp_client.py "What time is it?"
```

### HTTP variant

`clients/ollama_mcp_http_client.py` connects to an already-running server over streamable-http (same pattern as `mcp_http_client.py`). Start the server first:

```bash
uv run mcp_server.py run --transport streamable-http --port 8000
```

Then, in another terminal:

```bash
uv run clients/ollama_mcp_http_client.py "What time is it?"
```

It connects to `http://localhost:8000/mcp` by default (see `SERVER_URL` at the top of the file).

Both scripts expose the target model as the `LOCAL_OLLAMA_MODEL` constant at the top of the file (defaults to `llama3.1`).

The HTTP Ollama bridge also discovers MCP resources and resource templates. Because Ollama
supports function tools rather than native MCP resources, it presents a read-only
`read_mcp_resource(uri)` function to the model and forwards each requested URI through
MCP's `resources/read` operation.

## Run tests

```bash
uv run coverage run -m pytest -v
uv run coverage report
```

## FastMCP CLI

`fastmcp` also ships its own CLI (installed as part of the `fastmcp` dependency), which can inspect and run the server object directly without going through the project's Typer wrapper. Reference the server as `mcp_server.py:mcp` (module file plus the exported `FastMCP` instance).

Inspect the server (tools, prompts, resources, versions):

```bash
uv run fastmcp inspect mcp_server.py:mcp
```

Run the server directly with the FastMCP CLI:

```bash
uv run fastmcp run mcp_server.py:mcp --transport stdio
uv run fastmcp run mcp_server.py:mcp --transport http --port 8000
```

Display FastMCP version and environment info:

```bash
uv run fastmcp version
```

See `uv run fastmcp --help` for the full command list, including `call`, `dev`, and `install`.

## Notes

- `stdio` is used for local process-to-process MCP communication.
- `streamable-http` is used for HTTP-based MCP transport.
- The async tool (`long_running_greet`) works without wrapping `mcp.run()` in `asyncio.run(...)`.
- `open_meteo_current_forecast` calls the public Open-Meteo API and requires network access.
