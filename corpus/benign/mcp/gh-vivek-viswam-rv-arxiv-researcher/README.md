# arxiv-researcher

An MCP server that lets an LLM search arXiv and pull down papers as PDFs.

It exposes two tools over the [Model Context Protocol](https://modelcontextprotocol.io): one to search arXiv by free-text query, and one to download a specific paper by its arXiv ID. Point Claude Desktop, Claude Code, Cursor, or any other MCP client at it and you can ask things like "find recent work on speculative decoding and download the top result".

## How it works

The server is about 60 lines of Python. There isn't much to it, by design.

- **[FastMCP](https://gofastmcp.com)** handles the protocol. Each tool is a plain function decorated with `@mcp.tool()`; FastMCP reads the signature and docstring to build the tool schema the client sees, and takes care of transport, serialisation, and error reporting.
- **[Pydantic](https://docs.pydantic.dev)** defines the return types (`models.py`). `Article`, `SearchResponse`, and `DownloadResponse` are `BaseModel` subclasses, so every response has a fixed, typed shape rather than an ad-hoc dict. FastMCP uses the same models to generate the output schema, which means the client knows exactly what fields to expect before it ever calls the tool.
- **[arxiv](https://github.com/lukasschwab/arxiv.py)** wraps the arXiv API. A single shared `arxiv.Client()` is reused across calls so the library's built-in rate limiting is respected.

## Tools

### `search`

| Parameter | Type  | Default | Description                              |
|-----------|-------|---------|------------------------------------------|
| `query`   | str   |         | Free-text query, passed straight to arXiv |
| `count`   | int   | `5`     | Maximum number of results                |

Results are sorted by relevance. Each entry includes the short arXiv ID (e.g. `2411.11095v3`), title, authors, abstract, publication date, and a direct PDF URL.

### `download_article`

| Parameter    | Type         | Default                          | Description                              |
|--------------|--------------|----------------------------------|------------------------------------------|
| `article_id` | str          |                                  | arXiv ID, with or without version suffix |
| `directory`  | str          | `DEFAULT_DOWNLOAD_PATH`          | Where to save the PDF                    |
| `filename`   | str \| None  | `<article_id>.pdf`               | Override the output filename             |

The directory is created if it doesn't exist. Raises a `ValueError` if the ID doesn't resolve to a paper.

## Setup

Requires Python 3.13 or newer and [uv](https://docs.astral.sh/uv/).

```sh
git clone https://github.com/vivek-viswam-rv/arxiv-researcher.git
cd arxiv-researcher
uv sync
```

Before running, open `constants.py` and set `DEFAULT_DOWNLOAD_PATH` to wherever you want PDFs to land. It ships with a hardcoded path that almost certainly isn't right for your machine. Use an absolute path; `~` is not expanded.

## Running

The server speaks stdio, which is what most MCP clients expect:

```sh
uv run main.py
```

For interactive testing, FastMCP bundles the MCP Inspector:

```sh
uv run fastmcp dev inspector main.py
```

## Connecting a client

FastMCP can write the client configuration for you:

```sh
uv run fastmcp install claude-desktop main.py
uv run fastmcp install claude-code main.py
uv run fastmcp install cursor main.py
```

Or add the server by hand. For Claude Desktop, that means adding an entry to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "arxiv-researcher": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/arxiv-researcher", "main.py"]
    }
  }
}
```

Restart the client and the `search` and `download_article` tools should show up.

## Project layout

```
main.py        FastMCP server and the two tool definitions
models.py      Pydantic response models
constants.py   Download path and default result count
```

## License

MIT. See [LICENSE](LICENSE).
