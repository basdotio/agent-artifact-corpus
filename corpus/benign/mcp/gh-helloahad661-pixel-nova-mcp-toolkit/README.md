# nova-mcp-toolkit

Local MCP tool servers that give a coding assistant real capabilities:

| Server | What it exposes |
|---|---|
| `mcp_nova_web` | Web fetch and search over stdio |
| `mcp_nova_sqlite` | Safe SQLite queries |
| `mcp_public_apis` | Free public APIs, no keys needed |
| `mcp_security_monitor` | Data-leak and malware checks |
| `mcp_system_server` | System info and diagnostics |

```bash
pip install mcp
```

Point any MCP host (e.g. OpenCode, Claude Code) at these files over stdio.
Each server is one file with no other dependencies.

Part of [Nova](https://github.com/helloahad661-pixel/Nova), my macOS assistant system — `system_agent_real` looks after this piece.
