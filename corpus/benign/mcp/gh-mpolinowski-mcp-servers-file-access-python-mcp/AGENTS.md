# AGENTS.md — working in this repository

This repository is **docmgr**: a local document directory exposed as MCP tools, built on the
standalone **FastMCP** package (`fastmcp`, 4.x line) on top of the `mcp` SDK transports.
It is a single-file server (`main.py`) plus one e2e suite (`testing.py`).
Read this guide before changing anything.

## Repository layout

| File | Purpose |
| --- | --- |
| `main.py` | The entire MCP server: `DocumentStore` (domain logic) + `build_server` (tool layer) + CLI/transport. Entry: `python main.py <dir> [flags]`. |
| `testing.py` | End-to-end suite. Spawns the **real** server over stdio and streamable HTTP and drives it with a real MCP client against throwaway fixtures. |
| `requirements.txt` | `fastmcp>=4,<5`, `uvicorn`, `starlette`; test-only: `mcp>=2`, `httpx`. |
| `main.py.bak`, `testing.py.bak` | Pre-rewrite originals. **Do not** edit, reference, or delete them. |
| `README.md` | User-facing documentation (overview + getting started + agent prompt). |

## Commands

```bash
python3 main.py /path/to/docs [--allow-edit --allow-create --allow-delete]   # run (stdio)
python3 main.py --host 127.0.0.1 --port 8888 /path/to/docs                   # run (HTTP, /mcp)
python3 testing.py                                                           # full e2e; must end with "ALL TESTS PASSED"
python3 -m py_compile main.py                                                # quick syntax check
```

- Environment facts (current host): Python 3.14, `fastmcp 4.0.3`, `mcp 2.1.1`.
- **mcp is 2.x**: `mcp.server.fastmcp` does not exist there. If a change needs the `mcp`
  import, remember that client models use snake_case attributes (`is_error`,
  `structured_content`).
- Tests create fixtures in an OS temp dir and clean up after themselves; they bind a random
  free port on 127.0.0.1. No external services, no network beyond localhost.

## Tool contract — semantics are pinned by tests

Nine tools, all names/parameters below are load-bearing (asserted in `testing.py`):

| Tool | Params | Notes |
| --- | --- | --- |
| `search_documents` | `query`, `max_results=20`, `case_sensitive=False` | Exact substring (regex-escaped), at most one hit per document, ordered by `rel_path`, stops early at `max_results`. Returns `{rel_path, snippet, snippet_offset, offset}` with 50-char context each side. |
| `list_all_documents` | — | All served docs, hidden included, non-UTF-8 excluded, sorted. |
| `glob` | `path_str` | Relative wildcard patterns; matches intersected with the served set. |
| `get_document` | `rel_path` | Full text. |
| `get_document_length` | `rel_path` | **Characters**, not bytes. |
| `get_document_partial` | `rel_path, offset, length` | Offset/range errors must fail, not clamp. |
| `edit_document` | `rel_path, to_replace, replace_with, offset` | `to_replace` must start exactly at `offset`; empty `to_replace` inserts. Returns a message containing the **`new length`**. |
| `create_document` | `rel_path, text` | Creates parents; must fail on existing path. |
| `delete_document` | `rel_path` | File only (never a directory). |

Every tool also declares the four MCP **tool hints** (`read_only_hint`,
`destructive_hint`, `idempotent_hint`, `open_world_hint`) via
`@mcp.tool(annotations=_)`. Per the MCP spec these are *hints, not guarantees*;
a client may use them to warn the user before invoking. Set all four explicitly
on each tool to match its real behaviour — read tools are `read_only/
idempotent/non-destructive`, `edit_document` and `delete_document` are
destructive, `create_document` is additive — and keep `open_world_hint=False`
(this server only touches the local tree). These are metadata, so they don't
change tool names/params and `testing.py` doesn't assert them, but keep them in
sync if you add or change a tool's semantics.

Hard invariants — breaking any of these breaks the security/correctness model:

1. **Containment**: reject absolute paths, `..` parts, anything resolving outside the root, and
   symlinks that escape it. Non-UTF-8 files and directories are invisible to list/glob/search.
2. **Permission gating**: writes require `--allow-{edit,create,delete}` (or `--allow-all`);
   refusals must say the word **"not enabled"** and name the flag; the server *instructions*
   advertise all three flags with their enabled/disabled state (tests count the word
   `"enabled"`).
3. **Batch-write policy in tool docstrings**: keep the "ALWAYS WRITE IN BATCHES" paragraphs in
   `edit_document`/`create_document` — they are the LLM-facing contract that prevents
   output-token-limit failures.
4. **Lazy single-read iteration**: `iter_documents()` yields `(rel_path, content)` after one
   `read` per file, sorted by `rel_path`; search stops early. Don't re-introduce double reading.
5. **Atomic writes**: temp file in the same directory + `os.replace`; failures unlink the temp.
6. **Transport hygiene**: stdio stdout is reserved for the protocol (logs to stderr,
   `show_banner=False`); HTTP serves at `/mcp` with `access-control-expose-headers` covering
   `mcp-session-id` (browser clients need it) — both are asserted in `testing.py`.
7. **Error surfaces**: raise `DocumentError` in `DocumentStore`; the tool layer converts it to
   `fastmcp.exceptions.ToolError` (clean client-visible text, no traceback).

## How to change things safely

- **Order**: change `DocumentStore` (domain) first, then the tool wrapper, then update
  `testing.py` expectations only when the *contract* intentionally changes.
- **Always** end with `python3 testing.py` printing `ALL TESTS PASSED` before reporting done;
  that suite covers read-only, per-flag permissions, `--allow-all`, and HTTP+CORS.
- Keep it dependency-frugal: stdlib + `fastmcp` (+ `uvicorn`/`starlette` for HTTP) only.
- Tool docstrings are LLM-facing documentation: keep them precise (offsets are **characters**
  into the decoded content) and preserve the batch-write guidance.
- Python style: 3.10+ typing, no dataclasses/pydantic needed; modules are self-contained.
- If you extend the tool set, update in sync: `build_server`, the tool table in this file,
  the agent prompt paragraph in `README.md`, and one scenario check in `testing.py`.
