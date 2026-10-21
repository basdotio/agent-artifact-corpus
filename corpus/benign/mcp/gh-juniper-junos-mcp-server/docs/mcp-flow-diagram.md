# MCP Flow Diagram - Junos MCP Server

## Overview

This document illustrates the Model Context Protocol (MCP) architecture and the interaction flow between the user, MCP client (Claude Desktop), Anthropic's LLM, and the Junos MCP Server.

## Architecture Components

```mermaid
graph TB
    User[User]
    Client[MCP Client<br/>Claude Desktop/VSCode]
    LLM[Anthropic LLM<br/>Claude AI]
    MCP[Junos MCP Server<br/>FastMCP + PyEZ]
    Junos[Junos Network Devices]

    User -->|Natural language queries| Client
    Client <-->|API requests| LLM
    Client <-->|MCP Protocol| MCP
    MCP <-->|NETCONF/SSH| Junos

    style User fill:#e1f5ff
    style Client fill:#fff4e1
    style LLM fill:#ffe1f5
    style MCP fill:#e1ffe1
    style Junos fill:#f0f0f0
```

## Initialization Flow - Tool Discovery

```mermaid
sequenceDiagram
    participant User
    participant Client as MCP Client<br/>(Claude Desktop)
    participant MCP as Junos MCP Server
    participant Config as devices.json

    Note over User,Config: Startup & Initialization Phase

    User->>Client: Launch Claude Desktop
    Client->>Client: Read claude_desktop_config.json
    Note over Client: Finds MCP server configuration<br/>(command, args, transport type)

    Client->>MCP: Start MCP server process<br/>(stdio or streamable-http)
    MCP->>Config: Load device configuration
    Config-->>MCP: Return router credentials
    MCP->>MCP: Initialize FastMCP framework
    MCP->>MCP: Register 6 MCP tools:<br/>• execute_junos_command<br/>• get_junos_config<br/>• junos_config_diff<br/>• gather_device_facts<br/>• get_router_list<br/>• load_and_commit_config

    Client->>MCP: MCP Protocol: list_tools()
    MCP-->>Client: Return tool definitions<br/>(names, descriptions, parameters)

    Client->>Client: Store available tools in context

    Note over User,Config: Server Ready - Tools Discovered
    Client->>User: Ready to assist
```

## Runtime Flow - End-to-End Request

```mermaid
sequenceDiagram
    participant User
    participant Client as MCP Client<br/>(Claude Desktop)
    participant LLM as Anthropic LLM<br/>(Claude AI)
    participant MCP as Junos MCP Server
    participant Junos as Junos Device

    Note over User,Junos: Runtime Operation Phase

    User->>Client: "Show me the configuration<br/>of router-A"
    Client->>LLM: Send user query + available tools context

    Note over LLM: Analyze query<br/>Determine relevant tool:<br/>get_junos_config

    LLM-->>Client: Tool call decision:<br/>get_junos_config(router_name="router-A")

    Client->>MCP: MCP Protocol: call_tool()<br/>Tool: get_junos_config<br/>Args: {router_name: "router-A"}

    MCP->>MCP: prepare_connection_params()<br/>(lookup router-A credentials)
    MCP->>MCP: _run_junos_cli_command()<br/>Command: "show configuration | display inheritance no-comments"

    MCP->>Junos: NETCONF/SSH Connection<br/>(using PyEZ Device)
    Junos-->>MCP: Device configuration output
    MCP->>MCP: Close connection

    MCP-->>Client: MCP Protocol: tool result<br/>(configuration text)

    Client->>LLM: Send tool result

    Note over LLM: Process result<br/>Format response

    LLM-->>Client: Natural language response<br/>with configuration details

    Client->>User: Display formatted response
```

## Configuration Change Flow (Critical Path)

```mermaid
sequenceDiagram
    participant User
    participant Client as MCP Client
    participant LLM as Anthropic LLM
    participant MCP as Junos MCP Server
    participant Junos as Junos Device

    Note over User,Junos: Configuration Change Operation (⚠️ Auto-commits!)

    User->>Client: "Add interface ge-0/0/1<br/>with IP 10.0.0.1/24"
    Client->>LLM: Send query + tools

    LLM-->>Client: Tool: load_and_commit_config()<br/>Args: {router_name, config, format}

    Client->>User: ⚠️ Show proposed changes<br/>(may prompt for confirmation)
    User->>Client: Confirm

    Client->>MCP: call_tool: load_and_commit_config

    MCP->>Junos: Connect via NETCONF
    MCP->>Junos: Load configuration candidate
    MCP->>Junos: Commit configuration<br/>⚠️ AUTOMATIC COMMIT
    Junos-->>MCP: Commit success/failure

    MCP-->>Client: Tool result (success/error)
    Client->>LLM: Send result
    LLM-->>Client: Formatted response
    Client->>User: "Configuration applied successfully"

    Note over User,Junos: Changes are LIVE on device
```

## Transport Types

### stdio Transport (Claude Desktop)

```mermaid
graph LR
    A[Claude Desktop] <-->|stdin/stdout<br/>JSON-RPC| B[MCP Server Process]
    B <-->|NETCONF| C[Junos Devices]

    style A fill:#fff4e1
    style B fill:#e1ffe1
    style C fill:#f0f0f0
```

**Configuration:**
```json
{
  "mcpServers": {
    "junos": {
      "command": "python3.11",
      "args": ["/path/to/jmcp.py", "-f", "/path/to/devices.json", "-t", "stdio"]
    }
  }
}
```

### streamable-http Transport (VSCode/Copilot)

```mermaid
graph LR
    A[VSCode] <-->|HTTP<br/>MCP Protocol| B[MCP Server<br/>Port 30030]
    B <-->|NETCONF| C[Junos Devices]

    style A fill:#fff4e1
    style B fill:#e1ffe1
    style C fill:#f0f0f0
```

**Configuration:**
```json
{
  "mcp": {
    "servers": {
      "junos": {
        "url": "http://127.0.0.1:30030/mcp"
      }
    }
  }
}
```

## Key Implementation Details

### Tool Discovery at Initialization

1. **MCP Client reads config**: Finds server command and transport type
2. **Server starts**: Loads `devices.json`, initializes FastMCP
3. **Tool registration**: All 6 tools decorated with `@mcp.tool()` are registered
4. **Client queries**: Sends `list_tools()` request via MCP protocol
5. **Server responds**: Returns tool schemas (name, description, parameter types)
6. **LLM context**: Tools are added to LLM's system context for future requests

### Runtime Tool Execution

1. **User query**: Natural language request to MCP client
2. **LLM analysis**: Determines which tool(s) to call with what parameters
3. **MCP protocol**: Client sends `call_tool()` request to server
4. **Authentication**: `prepare_connection_params()` handles password or SSH key auth
5. **Execution**: `_run_junos_cli_command()` executes via PyEZ
6. **Response**: Result flows back through MCP protocol to LLM to user

### Available Tools

| Tool | Purpose | Auto-Commit |
|------|---------|-------------|
| `execute_junos_command` | Run arbitrary CLI commands | No |
| `get_junos_config` | Retrieve device configuration | No |
| `junos_config_diff` | Compare config versions | No |
| `gather_device_facts` | Collect device information | No |
| `get_router_list` | List available routers | No |
| `load_and_commit_config` | Apply config changes | ⚠️ **YES** |

## Security Notes

- ⚠️ **Critical**: `load_and_commit_config` automatically commits changes to live devices
- SSH key authentication recommended over passwords
- All device credentials stored in `devices.json`
- MCP exposes network infrastructure to LLM - ensure corporate policy compliance
- Always review LLM-generated configurations before allowing execution
