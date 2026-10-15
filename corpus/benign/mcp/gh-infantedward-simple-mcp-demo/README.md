# Simple MCP Demo

This repo shows a minimal Model Context Protocol setup with:

- `math_tools.py`: plain Python math functions decorated as MCP tools
- `server.py`: a FastMCP server that registers those tools
- `client_fastmcp.py`: a client built with FastMCP
- `client_manual.py`: a client built manually with `requests`
- `web_app.py`: a tiny web app that proxies browser actions to the MCP server
- `static/`: the HTML, JS, and CSS for the interactive frontend

The point of the demo is to show how little code is needed to expose Python functions through MCP.

## Project structure

```text
.
├── client_fastmcp.py
├── client_manual.py
├── math_tools.py
├── pyproject.toml
├── README.md
├── static
│   ├── app.js
│   ├── index.html
│   └── styles.css
└── server.py
└── web_app.py
```

## Why this is useful

With MCP, the server exposes tools in a standard way:

1. A client initializes a session.
2. The client asks for the list of tools.
3. The client calls a tool by name with JSON arguments.
4. The server validates inputs, runs the Python function, and returns the result.

FastMCP hides most of the ceremony. In this demo, the tool definitions are just normal functions with a decorator.

## Install

```bash
uv sync
```

## The tool file

The tools live in `math_tools.py` and use FastMCP's standalone decorator:

```python
from fastmcp.tools import tool

@tool
def add(a: float, b: float) -> float:
    return a + b
```

That marks the function as an MCP tool. The server later imports the function and registers it with `mcp.add_tool(...)`.

## Run the server over HTTP

This is useful for seeing the MCP protocol over JSON-RPC and for the manual `requests` client:

```bash
uv run python server.py --transport http --host 127.0.0.1 --port 8000
```

The MCP endpoint will be:

```text
http://127.0.0.1:8000/mcp
```

## FastMCP client example

This client imports the `mcp` server instance directly and uses FastMCP's in-memory client path, which the FastMCP docs recommend for local testing:

```bash
uv run python client_fastmcp.py
```

It will:

1. connect to the server
2. list the available tools
3. call `multiply`

## Manual MCP client example

Start the HTTP server first:

```bash
uv run python server.py --transport http
```

Then run the manual client:

```bash
uv run python client_manual.py
```

This script shows the core protocol flow explicitly:

1. send `initialize`
2. send `notifications/initialized`
3. send `tools/list`
4. send `tools/call`

It also handles the `Mcp-Session-Id` and `MCP-Protocol-Version` headers required for the HTTP session flow.

## Interactive HTML frontend

If you want a browser UI without mixing HTML concerns into the MCP files, use the small web layer:

1. start the MCP server
2. start the web app
3. open the browser

Terminal 1:

```bash
uv run python server.py --transport http --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
uv run uvicorn web_app:app --reload --host 127.0.0.1 --port 3000
```

Then open:

```text
http://127.0.0.1:3000
```

The browser does not speak MCP directly. Instead:

1. the page calls `/api/tools` and `/api/call`
2. `web_app.py` manages the MCP HTTP session
3. `web_app.py` forwards JSON-RPC requests to the MCP server
4. the frontend renders the returned tool metadata and results

## What each file demonstrates

### `math_tools.py`

The simplest possible authoring model: decorate normal functions.

### `server.py`

The server owns transport and registration. It imports the decorated functions and exposes them through one `FastMCP` instance.

### `client_fastmcp.py`

The ergonomic client path. You work with `Client`, `list_tools()`, and `call_tool()` instead of raw JSON-RPC.

### `client_manual.py`

The lower-level path. You can see the actual MCP lifecycle and tool-calling messages directly.

### `web_app.py` and `static/`

The UI path. This keeps the MCP server and clients clean while giving you an interactive browser demo.

## Sources used for this demo

- FastMCP tools docs: <https://gofastmcp.com/v2/servers/tools>
- FastMCP client docs: <https://gofastmcp.com/v2/clients/client>
- FastMCP running server docs: <https://gofastmcp.com/v2/deployment/running-server>
- MCP lifecycle: <https://modelcontextprotocol.io/specification/latest/basic/lifecycle>
- MCP transports: <https://modelcontextprotocol.io/specification/2025-06-18/basic/transports>
