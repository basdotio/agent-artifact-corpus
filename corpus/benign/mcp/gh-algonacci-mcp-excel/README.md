# mcp-excel

MCP server to give client the ability to read Excel files

# Usage

For this MCP server to work, add the following configuration to your MCP config file:

```json
{
  "mcpServers": {
    "sql_access": {
      "command": "uv",
      "args": [
        "--directory",
        "%USERPROFILE%/Documents/GitHub/mcp-excel",
        "run",
        "python",
        "main.py"
      ]
    }
  }
}
```
