# FastMCP Demo Server

A beginner-friendly **Model Context Protocol (MCP) server** built with [FastMCP](https://github.com/modelcontextprotocol/python-sdk). This project demonstrates how to create custom MCP tools and connect them to AI clients such as Claude Desktop.

## 🚀 Features

This server currently provides two simple MCP tools:

* `add` — Adds two numbers
* `multiply` — Multiplies two numbers

The project is designed as a simple starting point for learning how MCP servers work.

## 🧠 How It Works

The basic architecture is:

```text
User
  ↓
AI Client (Claude Desktop)
  ↓
MCP Protocol
  ↓
FastMCP Server
  ↓
Custom Tools
  ↓
Python Functions
```

For example, when Claude needs to calculate `10 + 20`, it can call the `add` MCP tool:

```text
Claude
  ↓
add(10, 20)
  ↓
FastMCP Server
  ↓
Python function
  ↓
30
```

## 📁 Project Structure

```text
fastmcp-demo-server/
│
├── main.py
├── README.md
├── LICENSE
├── pyproject.toml
├── uv.lock
├── .python-version
└── .gitignore
```

## 🛠️ Tools

### 1. add

Adds two numbers.

```python
add(a, b)
```

Example:

```text
add(10, 20)
→ 30
```

### 2. multiply

Multiplies two numbers.

```python
multiply(a, b)
```

Example:

```text
multiply(10, 20)
→ 200
```

## ⚙️ Requirements

* Python
* [uv](https://docs.astral.sh/uv/)
* FastMCP
* An MCP-compatible client such as Claude Desktop

## 📦 Installation

Clone the repository:

```bash
git clone https://github.com/safayet9009/fastmcp-demo-server.git
```

Go to the project directory:

```bash
cd fastmcp-demo-server
```

Install the project dependencies:

```bash
uv sync
```

## ▶️ Run the Server

Run the MCP server with:

```bash
uv run fastmcp run main.py:mcp
```

The server uses **stdio transport**, so it can communicate directly with MCP clients such as Claude Desktop.

## 🔍 Test with FastMCP Inspector

You can also inspect and test the server using FastMCP's development tools:

```bash
uv run fastmcp dev inspector main.py:mcp
```

This allows you to explore the available MCP tools and test them interactively.

## 🤖 Connect with Claude Desktop

Add the following configuration to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "Demo Server": {
      "command": "/home/shafayet/.local/bin/uv",
      "args": [
        "run",
        "--directory",
        "/home/shafayet/Desktop/fastmcp-demo-server",
        "fastmcp",
        "run",
        "main.py:mcp"
      ],
      "env": {},
      "transport": "stdio"
    }
  }
}
```

> **Note:** Update the paths according to your own system.

After adding the configuration, restart Claude Desktop.

Claude should then be able to discover the available tools:

```text
add
multiply
```

You can test it by asking Claude:

```text
Use the add tool to calculate 25 + 75.
```

or:

```text
Use the multiply tool to calculate 12 × 8.
```

## 🎯 Learning Goals

This project helps demonstrate:

* What an MCP server is
* How FastMCP works
* How to create MCP tools
* How MCP clients discover and call tools
* How Python functions can become MCP tools
* How to connect a custom MCP server with Claude Desktop
* How `stdio` transport works

## 🔮 Future Improvements

Possible future additions include:

* Weather tool
* Calculator tool
* Web search tool
* Database tools
* File management tools
* API integration
* Custom AI-powered tools
* Resources and prompts
* Authentication
* More advanced MCP workflows

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## 👨‍💻 Author

**Safayet Hossain**

GitHub: [@safayet9009](https://github.com/safayet9009)

---

⭐ If you find this project useful for learning MCP, consider giving it a star!
