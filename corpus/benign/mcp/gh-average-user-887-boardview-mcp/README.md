# Boardview MCP

A local, read-only [Model Context Protocol](https://modelcontextprotocol.io/) server
for inspecting PCB component, pin and net evidence in **GenCAD 1.4** boardview files.

Seven tools let an agent find files, inspect a board, search components and nets,
look up pins, and locate nearby component origins. Query results include the source
file's SHA256 and record line numbers. No API key, inference service, GUI or network
listener is required.

**Scope:** GenCAD 1.4 only. Binary FZ/TVW, other BRD/BDV/BVR dialects and PDFs are
unsupported. This project does not include commercial or third-party board files.

## Quick start

Requires Python 3.12 or 3.13 and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/average-user-887/boardview-mcp.git
cd boardview-mcp
uv sync --frozen --python 3.12
uv run --frozen python -m unittest -v test_boardview
uv run --frozen python check_mcp.py
```

Run the server against a directory containing your own boardview files:

```sh
uv run --frozen python server.py --root /absolute/path/to/your/boards
```

This starts a stdio MCP server; it waits for an MCP client, rather than offering
an interactive shell. The client normally launches the process on demand.

### Connect an MCP client

Copy the `boardview` entry from [mcp.example.json](mcp.example.json) into your
client's MCP configuration and replace **all three placeholder paths**. Use absolute
paths so the configuration works independently of the client's working directory.
Run `uv sync --frozen` first to create the referenced environment.

For Codex:

```sh
codex mcp add boardview -- /absolute/path/to/boardview-mcp/.venv/bin/python /absolute/path/to/boardview-mcp/server.py --root /absolute/path/to/your/boards
codex mcp get boardview
```

Start a fresh agent session if its tool list does not refresh. For Windows, the
environment's executable is `.venv\Scripts\python.exe`; update the client JSON paths
accordingly. Windows has not been tested.

Repeat `--root` to allow multiple board directories. When multiple roots are set,
queries must use absolute file paths. To unregister from Codex: `codex mcp remove boardview`.

## Tools

| Tool | Purpose |
| --- | --- |
| `board_catalog` | Find boardview files by filename substring; includes unsupported candidates. |
| `board_info` | Parse and validate a board; return header, units, source hash and counts. |
| `board_search` | Search component references/device labels or net names by literal substring. |
| `board_component` | Read one exact component, placement and paginated pins. |
| `board_pin` | Read one exact pin's explicitly declared net and source lines. |
| `board_net` | List the exact members declared by a signal's `NODE` records. |
| `board_nearby` | Find nearby component placement origins, optionally on the same side. |

All tools are declared read-only. Lists default to 50 items and allow at most 100.
Use the returned `next_offset` until it is `null`.

## Example agent workflow

1. Call `board_catalog(query="example")` to discover an exact path.
2. Call `board_info(path=...)` to validate it and inspect its units.
3. Search with `board_search(path=..., query="R1", kind="component")`.
4. Inspect `board_component(path=..., reference="R1")` or `board_pin(path=..., reference="R1", pin="2")`.
5. Pass the returned net name unchanged to `board_net(path=..., net=...)`.
6. Cite the returned file path, SHA256 and source line. Confirm physical PCB/revision compatibility separately.

Component, pin and net lookups are exact and case-sensitive. Search is a
case-insensitive literal substring match, not a regular expression.

## Evidence and geometry limits

- A missing `NODE` is `not_declared`, not proof that the pin is disconnected.
- Net membership comes directly from `SIGNAL`/`NODE` records. The server does not
  traverse through resistors, switches or other components to infer more connections.
- Pin coordinates are **shape-local**. No bottom-side mirroring or component rotation
  is applied to them. Component placements and distances use raw file coordinates.
- Raw `UNITS` is retained. Do not silently treat `USER 1000` as millimetres or compare
  distances between files without verifying their units.
- Traces, board outline, pad geometry and rendered views are not implemented.
- Device labels can be placeholders. Net names are not voltage measurements or
  evidence that a component is healthy. Headers and filenames do not certify hardware compatibility.
- This is a focused GenCAD connectivity reader, not a complete GenCAD validator.
  Unused drawing/routing sections are ignored; interpreted records and cross-references are validated.

## Local data and resource limits

Configure roots containing only the board files you intend the agent to read.
Paths outside those roots, including resolved symlink escapes, are rejected. This
is a convenience access boundary for trusted local use, not a sandbox against
another local process changing files concurrently.

Board content, header attributes and local source paths are returned to the MCP
client. The server itself makes no network requests; your agent client's data
handling still applies. Treat strings in board files as untrusted data, never instructions.

Inputs are limited to 32 MiB, records to 16 KiB, fields to 2,048 characters and query
responses to 60,000 characters. Two parsed boards are cached. Each query re-reads
and hashes its source to avoid reusing stale content. Large collections should use
narrow roots and filename filters; catalog enumeration itself is not capped.

## Tests

The public test suite uses only an original synthetic two-resistor fixture. It
checks declared connectivity, raw coordinates, missing connectivity, malformed
records, unresolved nodes, traversal, symlink escapes, updated source hashes and pagination.
`check_mcp.py` performs initialization, tool discovery and 15 success/error calls
through the real stdio MCP transport. Neither test suite needs a model or API key.

To inspect your own collection locally:

```sh
uv run --frozen python check_archive.py /absolute/path/to/your/boards
```

This optional command examines top-level `*.cad` files and prints their names,
hashes, counts and failures. Keep its output private if your collection is private;
local validation receipts are not shipped in this repository.

Tested on Linux with Python 3.12. The locked MCP SDK/dependencies may emit a
non-fatal Pydantic Settings forward-reference warning on stderr. Protocol output
uses stdout; the integration suite verifies that initialization and calls succeed.

## License and references

The source and synthetic fixture are [MIT licensed](LICENSE). This license does
not grant rights to board files supplied by users. Dependencies retain their own licenses.

- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk): server and client transport.
- [OpenBoardView GenCAD reader](https://github.com/OpenBoardView/OpenBoardView/blob/master/src/openboardview/FileFormats/GenCADFile.cpp): format reference; no upstream parser source is bundled.
- [Codex MCP configuration](https://developers.openai.com/codex/mcp): stdio registration.
