# System Info MCP Server

A Model Context Protocol (MCP) server that exposes system monitoring and process management tools.

This project provides AI agents with safe access to system information such as CPU usage, memory usage, running processes, and controlled process termination with validation safeguards.

## 🚀 Features

- ✅ Retrieve system information (CPU, RAM, Disk, Network, Uptime)

- ✅ List running processes

- ✅ Detect high resource usage processes

- ✅ Safe process termination with validation

- ✅ MCP tools integration

- ✅ Security checks preventing termination of critical system processes

## 🧱 Project Structure
```text
system-info/
│
├── main.py                     # MCP server entry point
├── services/
│   └── system_info_service.py # System monitoring logic
├── models/
│   ├── system_info.py
│   └── process_info.py
├── validation.py              # Safety validation rules
├── tests.py                   # Unit tests
└── README.md
```
## ⚙️ Requirements

Python 3.10+

psutil

MCP FastMCP

Install dependencies:

pip install psutil

pip install mcp

## ▶️ Running the MCP Server

Start the server:

python main.py

The MCP server will start and expose registered tools to compatible MCP clients.

## 🧠 Available MCP Tools
### system_info_tool

Returns system information including:

OS details

CPU usage

RAM usage

Disk usage

Network statistics

Uptime

### resource_usage_tool

Detects processes consuming excessive resources and returns only those safe to terminate.

### list_processes_tool

Returns a list of currently running processes.


### terminate_process_tool

Safely terminates a process after validation and user confirmation.

Parameters:

pid — Process ID

confirmed — must be true to execute termination

Safety protections include:

Prevents killing system-critical processes

Prevents terminating PID 0/1

Prevents self-termination

## 🔐 Safety Model

Before terminating a process:

Process information is collected.

Validation rules are applied.

Critical OS processes are blocked.

User confirmation is required.

## 🧪 Running Tests

Run unit tests:

```json
python -m unittest utils.tests
```

Tests use mocking to avoid interacting with real system processes.

## 🔌 Adding This MCP Server to an MCP Client

Example configuration (Claude Desktop / MCP-compatible client):

```json
{
  "mcpServers": {
    "system-info": {
      "command": "python",
      "args": ["PATH_TO_PROJECT/main.py"]
    }
  }
}
```

Replace:

PATH_TO_PROJECT

with the absolute path to your project folder.

Example (Windows):

C:\\Users\\your-user\\Desktop\\system-info\\main.py
🧩 How MCP Integration Works

This project uses:

mcp = FastMCP("system-info-mcp-server")

Each tool is registered using:

@mcp.tool()

When the server runs, MCP automatically exposes these tools to AI agents.

## 🛡️ Security Notes

Never expose this server publicly without authentication.

Process termination is restricted but still powerful.

Intended for local development or controlled environments.

## 📄 License

MIT License

