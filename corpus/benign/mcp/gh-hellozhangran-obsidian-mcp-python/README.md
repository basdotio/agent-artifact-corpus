# obsidian-mcp-python

## notice
Actually, this is a small demo project designed to help you understand MCP. It enables you to quickly get to know and set up a real MCP service. 
- If you're a developer, you can look at the Tutorial.md
- If you're an ordinary user who just wants to have a try, please refer to the "Usage" section.

## Usage
1. clone this repo to your local pc
2. install uv tool in your local pc
3. copy bellow json config into you MCP Client (Cursor/Windsurf/Claude Desktop)

```json
{
  "mcpServers": {
    "obsidian-mcp-python": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/of/your/project/file/obsidian-mcp-python",
        "run",
        "main.py"
      ],
      "env": {
        "OBSIDIAN_PATH": "/path/of/your/obsidian/vault"
      }
    }
  }
}
```

