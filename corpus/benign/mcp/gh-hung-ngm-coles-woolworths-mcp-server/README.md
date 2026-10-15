# Coles and Woolworths MCP Server

An experimental Model Context Protocol (MCP) server implementation that allows AI assistants to search for product information from Australia's major supermarkets: Coles and Woolworths. This server exposes product search functionality through the MCP protocol, making it easy for AI assistants to retrieve product pricing and details.

<a href="https://glama.ai/mcp/servers/@hung-ngm/coles-woolworths-mcp-server">
  <img width="380" height="200" src="https://glama.ai/mcp/servers/@hung-ngm/coles-woolworths-mcp-server/badge" alt="coles-woolworths MCP server" />
</a>

## Demo

### Use with Claude Desktop

https://github.com/user-attachments/assets/0af3b07a-578a-4112-acfe-e7a7eee31161

## Features

- **Product Search**: Search for products at both Coles and Woolworths supermarkets
- **Price Comparison**: Get pricing information from both retailers in a consistent format
- **Store Selection**: Search specific Coles stores using store IDs
- **Result Limiting**: Control how many products are returned in search results

## Quick Start for Claude Desktop, Cursor, and other clients

1. Clone this repository
```bash
git clone https://github.com/hung-ngm/coles-woolworths-mcp-server.git
```

2. Navigate to the project directory
```bash
cd coles-woolies-mcp
```

3. Install the [prerequisites](#prerequisites)

4. Configure your MCP client to use this server (see [Integrating with MCP Clients](#integrating-with-mcp-clients))

## Installation

### Prerequisites

1. Python 3.8 or higher
2. The `uv` package manager

### Installing uv

uv is a fast Python package installer and resolver. To install:

#### macOS/Linux:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows:
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### Setup

1. Clone the repository and navigate to the project directory
2. Use `uv` to install dependencies:

```bash
# Install dependencies
uv pip install fastmcp requests python-dotenv
```

## Configuration

The server uses the following environment variables:

- `COLES_API_KEY`: API key for accessing the Coles API (required for Coles product searches)

You can set these variables in a `.env` file in the project directory.

## Running the Server

To run the Coles and Woolworths MCP server directly using `uv`:

```bash
uv run main.py
```

By default, the server runs with stdio transport for MCP client integration.

## Integrating with MCP Clients

### Claude Desktop Configuration

To use the Coles and Woolworths MCP server with Claude Desktop:

1. Locate your Claude Desktop configuration file (usually `claude_desktop_config.json`)
2. Add the following configuration to the `mcpServers` section:

```json
{
  "mcpServers": {
    "coles-woolies-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "--with",
        "requests",
        "--with", 
        "python-dotenv",
        "fastmcp",
        "run",
        "/full/path/to/coles-woolies-mcp/main.py"
      ]
    }
  }
}
```

Replace `/full/path/to/coles-woolies-mcp/main.py` with the absolute path to your main.py file.

3. Restart Claude Desktop for the changes to take effect

### Cursor IDE Configuration

To integrate with Cursor IDE:

1. Open your Cursor configuration file
2. Add the following to the `mcpServers` section:

```json
{
  "mcpServers": {
    "coles-woolies-mcp": {
      "command": "uv",
      "args": [
        "run",
        "--with",
        "fastmcp",
        "--with",
        "requests",
        "--with", 
        "python-dotenv",
        "fastmcp",
        "run",
        "/full/path/to/coles-woolies-mcp/main.py"
      ]
    }
  }
}
```

## Available Tools

The Coles and Woolworths MCP server exposes the following tools:

- `get_coles_products`: Search for products at Coles supermarkets with optional store selection
- `get_woolworths_products`: Search for products at Woolworths supermarkets

### Example Usage in Claude

You can use the tools in Claude like this:

```
Could you check the price of Cadbury chocolate at both Coles and Woolworths?
```

Claude will then use the appropriate tools to search for the products and return the results.

## Requirements

- Python 3.8 or higher
- fastmcp package
- requests package
- python-dotenv package
- MCP-compatible client (Claude Desktop, Cursor, etc.)