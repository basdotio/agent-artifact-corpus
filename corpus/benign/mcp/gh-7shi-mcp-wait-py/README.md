# mcp-wait-py MCP Server

A Model Context Protocol server

This is a Python-based MCP server that implements waiting for a specified number of seconds.

## Features

### Tools

- `wait_seconds` - Wait for a specified number of seconds

## Installation

To use with Claude Desktop, add the server config:

- On MacOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- On Windows: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "mcp-wait-py": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/mcp-wait/py",
        "run",
        "server.py"
      ]
    }
  }
}
```

### Debugging

Since MCP servers communicate over stdio, debugging can be challenging. We recommend using the [MCP Inspector](https://github.com/modelcontextprotocol/inspector), which is available as a package script:

```bash
npx @modelcontextprotocol/inspector uv run server.py
```

The Inspector will provide a URL to access debugging tools in your browser.
