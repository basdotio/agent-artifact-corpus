# Simple MCP Server

A minimal implementation of the Model Context Protocol (MCP) server using FastMCP. This example demonstrates how to create a simple MCP server that clients like Windsurf IDE and Claude can connect to.

## What is MCP?

The Model Context Protocol (MCP) is a standard that connects LLMs with external tools and data sources. MCP servers extend AI capabilities by providing access to specialized tools, external information, and services.

## Features

- Dual transport support (HTTP and stdio)
- Simple authentication middleware for HTTP transport
- Example tools implementation
- Compatible with MCP clients like Windsurf IDE and Claude

## Prerequisites

- Python 3.11+
- [FastMCP - https://github.com/jlowin/fastmcp](https://github.com/jlowin/fastmcp)
- [uv - https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/rjmoggach/simple-mcp-server.git
   cd simple-mcp-server
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

You can run the server in three different modes:

### Run with both transports (default)

```bash
python run_server.py
```

This will start the HTTP server on port 9876 and the stdio server simultaneously.

### HTTP transport only

```bash
python run_server.py --http-only
```

### stdio transport only

```bash
python run_server.py --stdio-only
```

## Available Tools

The server provides these example tools:

1. **hello_world** - A simple greeting tool
   - Parameters:
     - `name` (string, default: "World"): Name to greet
     - `delay` (integer, default: 0): Optional delay in seconds
   - Returns: A greeting message

2. **get_version** - Returns server version information
   - Returns: Version details including server name and API version

3. **system_info** - Returns basic system information
   - Returns: Python version and platform details

## Connecting to AI Systems

### Windsurf IDE Configuration

Add the following configuration to your Windsurf IDE settings:

```json
"simple-mcp": {
  "command": "npx",
  "args": [
    "mcp-remote", 
    "http://localhost:9876/", 
    "--allow-http", 
    "--header", 
    "Authorization: Bearer SIMPLE_MCP_SERVER"
  ]
}
```

### Claude Desktop Configuration

Add the following to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "simple-mcp": {
      "command": "uv",
      "args": [
        "run", 
        "--project", "/path/to/simple-mcp-server", 
        "python", "/path/to/simple-mcp-server/run_server.py", 
        "--stdio-only"
      ],
      "cwd": "/path/to/simple-mcp-server"
    }
  }
}
```

Replace `/path/to/simple-mcp-server` with the actual path to your project.

## Authentication

For HTTP transport, the server uses a simple token-based authentication:

- Token: `SIMPLE_MCP_SERVER` (defined in `run_server.py`)
- Header format: `Authorization: Bearer SIMPLE_MCP_SERVER`

## Extending the Server

To add your own tools, modify the `create_mcp_server()` function in `run_server.py`:

```python
@mcp.tool()
async def your_custom_tool(param1: str, param2: int = 0) -> dict:
    """Your custom tool description."""
    # Implementation here
    return {"result": "Your output"}
```

## License

[MIT License](LICENSE)
