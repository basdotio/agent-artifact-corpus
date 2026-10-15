# File-Access MCP Server (FastMCP)

## 1. What this repository is

A production-ready **Model Context Protocol (MCP) server** in **Python** that turns any local
directory of text files into a first-class **document store for LLMs and AI agents**. Built on
**FastMCP 2.x** (the standalone [`fastmcp`](https://gofastmcp.com) package, 4.x line) over the
official `mcp` SDK transports, it speaks **JSON-RPC 2.0** on both **stdio** and **streamable
HTTP** (`/mcp`), with browser-ready **CORS** for the MCP Inspector and direct-connect clients.

The nine exposed MCP tools cover the full document lifecycle —

`search_documents` · `list_all_documents` · `glob` · `get_document` · `get_document_length` ·
`get_document_partial` · `edit_document` · `create_document` · `delete_document` — with
character-precise offsets, case-insensitive regex-safe substring search, glob patterns
(`**/*.txt`), **structured output** alongside plain text, **permission flags**
(`--allow-edit/--allow-create/--allow-delete`), **symlink escape containment**, non-UTF-8
filtering, and **atomic crash-safe writes** (temp file + rename). The tool descriptions carry an
explicit **batch-write policy** so agent LLMs always write in small offset-addressed batches
instead of whole files — protecting against **output token limit** failures.

**Keywords:** MCP server · Model Context Protocol · FastMCP · LLM · AI agent tooling · document
management · file access control · stdio transport · streamable HTTP · SSE-free resumable
streaming · JSON-RPC · structured content · CORS · Python 3 · e2e tested.

## 2. Getting started

### Prerequisites

- **Python 3.10+** (developed and tested on 3.14)
- A directory of UTF-8 text documents you want the agent to work with

```bash
# 1. Set up
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 2. Point the server at your documents (stdio mode — for most MCP clients)
python main.py /path/to/your/docs --allow-edit --allow-create --allow-delete

#    …or in read-only mode (no flags = read tools only)
python main.py /path/to/your/docs
```

```bash
# 2'. Alternative: streamable HTTP mode (for browser/remote clients, URL http://HOST:PORT/mcp)
python main.py --host 127.0.0.1 --port 8888 /path/to/your/docs
```

### Register with a client

- **stdio** (Claude Desktop, Cursor, VS Code, any MCP client):
  ```json
  {
    "file-access": {
      "command": "python",
      "args": ["main.py", "/path/to/your/docs", "--allow-edit", "--allow-create", "--allow-delete"]
    }
  }
  ```
- **HTTP**: connect to `http://127.0.0.1:8888/mcp` (MCP Inspector: *Direct Connect*).

### Verify

```bash
python testing.py          # spawns real stdio + HTTP servers and must print ALL TESTS PASSED
```

### Tell your agent to use it

Paste a prompt like this to your agent once the server is registered:

> You have the **file-access** MCP tools for all document work.
> Never create or overwrite files by other means.
>
> - **Find**: use `list_all_documents` / `glob` to locate files, `search_documents` for
>   content, then `get_document_partial(rel_path, offset, length)` to read the relevant span
>   (check `get_document_length` first when unsure of the size).
> - **Write — always in batches**: `create_document` only with a small first chunk, then grow
>   the file with successive `edit_document` calls using `to_replace=""` and
>   `offset` = the `new length` reported by the previous call. Keep every
>   `to_replace`/`replace_with` pair small (a few lines) — never put a whole file in one call.
> - **Delete**: only when explicitly asked, via `delete_document`.
>
> If a write tool reports "not enabled", stop and tell me — do not work around it.

## 3. Walkthrough: how this FastMCP server is built

An in-depth tour of `main.py` — the anatomy of a FastMCP server that turns
ordinary Python functions into tools an agent can call.

### The three layers

`main.py` follows a three-layer shape that keeps the MCP details out of your
real logic:

```
┌─────────────────────────────────────────────────────────────────┐
│ 3. TRANSPORT        main() → mcp.run(transport="stdio")         │
│                        or serve_http() → mcp.http_app() + uvicorn│
├─────────────────────────────────────────────────────────────────┤
│ 2. TOOL LAYER       build_server()  @mcp.tool() wrappers        │
│                        docstrings/annotations → MCP contract     │
│                        DocumentError → ToolError                │
├─────────────────────────────────────────────────────────────────┤
│ 1. DOMAIN           class DocumentStore                         │
│                        pure Python, no MCP imports, testable     │
└─────────────────────────────────────────────────────────────────┘
```

### Layer 1 — the domain: plain Python, zero MCP imports

`DocumentStore` (the first ~250 lines) is a self-contained class: path
containment (`resolve()`), lazy UTF-8 document iteration
(`iter_documents()`), search/list/glob, partial reads, atomic edits
(`tempfile.mkstemp` + `os.replace`), and permission gating (`_require`).
It raises its own `DocumentError`. Nothing in this layer knows an LLM
exists — this is what makes the logic unit-testable and reusable.

### Layer 2 — the tool layer: one decorator turns a function into an MCP tool

The minimal skeleton of the whole mechanism in `build_server()`:

```python
from fastmcp import FastMCP, ToolError

mcp = FastMCP("file-access", instructions="...what this server can do...")

@mcp.tool()                                   # ← this is the entire registration
def get_document_length(rel_path: str) -> int:
    """Return the length of the document at rel_path in characters (not bytes)."""
    return store.length(rel_path)
```

FastMCP derives **everything the agent sees** from the Python function:

| FastMCP reads from the function       | Becomes in the MCP protocol (what the agent's LLM sees) |
| --- | --- |
| function name                        | tool name (`get_document_length`) |
| **docstring**                        | tool `description` — the LLM's only documentation, so write it *for an LLM* |
| **parameter names, `str`/`int`/`bool`/`list[...]` annotations, defaults** | the JSON-Schema `inputSchema` (e.g. `max_results: int = 20` → optional param) |
| **return annotation** (`str`, `list[str]`, `list[dict]`, `int`) | the structured-output shape; the agent gets `structured_content` *and* a text rendering |
| exceptions                          | error results: raise `ToolError(msg)` → the client sees a clean one-line `isError` message; other exceptions → `Error calling tool ...` |

Three practical details from this codebase worth copying into your own server:

1. **The docstring is your product feature.** The `edit_document`/
   `create_document` docstrings end with an "ALWAYS WRITE IN BATCHES" policy —
   that is how you *steer agent behavior at the protocol level*, e.g.
   preventing a model from ever emitting a whole file in one call and hitting
   its output token limit. Anything you want the agent to always do, say in a
   docstring.
2. **Convert domain errors to `ToolError`** in the thin wrapper (here the
   `_call` helper), so the agent gets `editing is not enabled on this server
   (start file-access with --allow-edit)` instead of a Python traceback.
3. **Declare the tool hints.** Each `@mcp.tool(annotations=…)` sets all four MCP
   hints explicitly so a host always knows what it's about to do: `read_only_hint`
   (`true` for the six read tools), `destructive_hint` (`true` for
   `edit_document`/`delete_document`), `idempotent_hint`, and `open_world_hint`
   (`false` — this server only touches the local tree). The MCP spec treats these
   as *hints, not guarantees*, but setting them honestly lets a cautious client
   confirm before a destructive call.

The **server instructions** (`instructions=` in the `FastMCP(...)` call, built
by `describe_capabilities()`) are advertised at MCP `initialize` time — use
them for capability state (which write flags are on) and global policy, the
docstrings for per-tool usage.

### Layer 3 — the transport: one line per wire protocol

```python
mcp.run(transport="stdio", show_banner=False)      # clients launch this process for you
app = mcp.http_app()                               # …or serve it: ASGI app at /mcp
app.add_middleware(CORSMiddleware, ...)            # browser clients (Inspector) need CORS
uvicorn.run(app, host=host, port=port)
```

In fastmcp 4.x the `host`/`port` belong to the *runner* (uvicorn /
`mcp.run(...)`), not to the `FastMCP(...)` constructor. Note `mcp.run` is a
blocking call — it *is* the server's main loop.

### Recipe: adding your own tool to a FastMCP server

1. Implement the behavior in the domain layer (pure Python, own exception type).
2. In `build_server()`: `@mcp.tool()` above a wrapper that calls it.
3. Name the tool verb+noun (`rename_document`), annotate all parameters with
   concrete types (lists of dicts/str/int for structured results) and give
   sensible defaults.
4. Write the docstring *for an LLM*: exact meaning of each arg, units
   (characters, not bytes!), error conditions, and any behavior you want forced
   (e.g. the batch-write policy).
5. Wrap domain errors in `ToolError`, then extend the test suite with the
   same "advertised → works → refused/error" checks the other tools have in
   `testing.py`.
