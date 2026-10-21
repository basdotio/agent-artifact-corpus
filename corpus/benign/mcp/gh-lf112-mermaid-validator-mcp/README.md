# Mermaid Validator MCP

[![MCP Badge](https://lobehub.com/badge/mcp/lf112-mermaid-validator-mcp)](https://lobehub.com/mcp/lf112-mermaid-validator-mcp)

A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server built with [Bun](https://bun.sh) and TypeScript that validates [Mermaid](https://mermaid.js.org) diagram syntax.

## Quick Start

This package is published on npm. You can run it directly with npx:

```bash
npx -y mermaid-validator-mcp
```

## MCP Client Configuration

Add the server to your MCP client (e.g. Claude Desktop) configuration:

### Using npx (recommended)

```json
{
  "mcpServers": {
    "mermaid-validator": {
      "command": "npx",
      "args": ["-y", "mermaid-validator-mcp"]
    }
  }
}
```

### Using local source

```json
{
  "mcpServers": {
    "mermaid-validator": {
      "command": "bun",
      "args": [
        "/path/to/mermaid-validator-mcp/index.ts"
      ]
    }
  }
}
```

Or if you have it installed globally:

```json
{
  "mcpServers": {
    "mermaid-validator": {
      "command": "mermaid-validator-mcp"
    }
  }
}
```

## Features

- **Single tool – `validate_mermaid`**: Pass any Mermaid diagram text and receive either a success response with the detected diagram type, or a detailed parse-error message.
- Supports all major Mermaid diagram types: flowchart, sequence, class, pie, gantt, state, ER, gitGraph, mindmap, timeline, and more.
- No dependency on `mermaid-cli` or any external rendering process.
- Uses JSDOM to provide the minimal DOM environment required by Mermaid.

## Requirements

- [Bun](https://bun.sh) ≥ 1.0

## Getting Started

```bash
# Install dependencies
bun install

# Start the MCP server (stdio mode)
bun start
```

## Tool: `validate_mermaid`

### Input

| Field     | Type   | Description                          |
|-----------|--------|--------------------------------------|
| `diagram` | string | The Mermaid diagram text to validate |

### Output (JSON text)

**Valid diagram**

```json
{ "valid": true, "diagramType": "flowchart-v2" }
```

**Invalid diagram**

```json
{
  "valid": false,
  "error": "Parse error on line 2:\n...TD\n  --> B\n-------^\nExpecting 'SEMI', ..."
}
```

## Development

```bash
# Run with auto-reload
bun dev

# Build
bun run build
```
