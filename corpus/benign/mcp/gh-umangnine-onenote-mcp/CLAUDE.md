# OneNote MCP Server — Project Guidelines

Refer to [AGENTS.md](file:///D:/www/onenote-mcp/AGENTS.md) for full project architecture, tool reference, and code conventions.

## Quick Summary
- **User**: [**Umang Kathiyara**](https://github.com/umangnine) (`@umangnine`)
- **Server**: FastMCP local OneNote server ([server.py](file:///D:/www/onenote-mcp/server.py))
- **Environment**: Python 3.12+ with `uv` (`uv sync` / `uv run server.py`)
- **Diagnostics**: `powershell -ExecutionPolicy Bypass -File .\scripts\test_connection.ps1`
- **Formatting Rule**: Minimum 12pt font size, multi-`<one:OE>` structure, nested `<one:OEChildren>` lists, STA PowerShell execution.
