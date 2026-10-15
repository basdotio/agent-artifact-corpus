# Dead Simple MCP Server Template

A minimal Model Context Protocol (MCP) server template. Clone this to build your own MCP server.

## What's Included

- `server.py` - A basic MCP server with one example tool
- `requirements.txt` - Python dependencies
- This README

## Quick Start

### 1. Clone or Fork This Repo

```bash
git clone https://github.com/YOUR-USERNAME/mcp-template.git
cd mcp-template
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Test the Server

```bash
python server.py
```

The server runs and waits for input from Claude Desktop.

### 4. Add to Claude Desktop

Edit your Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

Add this configuration:

```json
{
  "mcpServers": {
    "simple-server": {
      "command": "python",
      "args": ["/absolute/path/to/mcp-template/server.py"]
    }
  }
}
```

Replace `/absolute/path/to/mcp-template/` with the actual path.

### 5. Restart Claude Desktop

Quit and restart Claude Desktop. Your MCP server will now be available.

## How to Modify

### Add Your Own Tools

Edit `server.py` and add new tools in the `list_tools()` function:

```python
@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="your_tool_name",
            description="What your tool does",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param1"]
            }
        )
    ]
```

### Handle Tool Calls

Add your logic in the `call_tool()` function:

```python
@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "your_tool_name":
        # Your logic here
        result = do_something(arguments.get("param1"))
        return [TextContent(type="text", text=result)]
```

### Connect to APIs or Databases

Import what you need and call it from your tool handlers:

```python
import requests

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "fetch_data":
        response = requests.get("https://api.example.com/data")
        return [TextContent(type="text", text=response.text)]
```

## Resources

- [MCP Documentation](https://modelcontextprotocol.io)
- [Anthropic MCP Course](https://anthropic.skilljar.com/introduction-to-model-context-protocol)
- [awesome-mcp-servers](https://github.com/punkpeye/awesome-mcp-servers) - More examples

## License

MIT - Use this however you want.
