
# Expense-Tracker MCP Server

An **MCP (Model Context Protocol) server** built with [FastMCP](https://github.com/jlowin/fastmcp) to help you track and analyze personal expenses.  
This server is meant to be used with **MCP-compatible clients** such as **Claude Desktop**, and provides structured tools and resources for expense management.

---

## 🧾 Overview

The Expense-Tracker MCP server allows MCP clients to:

-  **Add new expenses** (with date, amount, category, subcategory, and notes)  
-  **List expenses** within a given date range  
-  **Summarize spending** by category in a given period  
-  **Access predefined categories** from a JSON resource  

All expense data is stored in a local **SQLite database** (`expenses.db`). Categories can be managed through the `categories.json` file.  

---

## 📂 Project Structure

```
.
├── categories.json # Predefined expense categories
├── expenses.db # SQLite database (auto-created on first run)
├── main_exp.py # Main MCP server
├── demo.py # Optional demo / quick test script
├── pyproject.toml # Project metadata & dependencies
├── uv.lock # Lock file for uv dependencies
└── README.md # You are here
```

---

## 🚀 Features

- **Add Expenses** → Save expenses with categories, subcategories, and notes  
- **List Expenses** → Retrieve expenses between start and end dates  
- **Summarize** → Aggregate expenses by category (optionally filter by one category)  
- **Dynamic Categories** → Categories are loaded live from `categories.json` so you can edit without restarting  
- **FastMCP-powered** → Simple, declarative tools with zero boilerplate  

---

## 🛠 Setup & Run

### 1. Clone the Repository
```bash
git clone https://github.com/AbhaySingh71/Expense-tracker-mcp-server.git
cd Expense-tracker-mcp-server
```

### 2. Install Dependencies with uv
```bash
uv sync
```

### 3. Run the MCP Server
```bash
uv run main_exp.py
```

The server will start and wait for an MCP client (like Claude Desktop) to connect.

---

## 🖥 Using with Claude (MCP Client)

Open your Claude Desktop configuration file (`claude_desktop_config.json`).

Add the Expense-Tracker MCP server under `"mcpServers"`. Example:

```json
{
  "mcpServers": {
    "expense-tracker": {
      "command": "uv",
      "args": ["run", "main_exp.py"],
      "cwd": "C:/Users/abhay/Desktop/Expense-tracker-mcp"
    }
  }
}
```

Restart Claude Desktop.  
You can now ask Claude things like:

- “Add an expense of ₹200 for Food on 2025-09-28.”  
- “List all my expenses between 2025-09-01 and 2025-09-28.”  
- “Summarize my expenses by category for September 2025.”  

---

## 🔍 Debugging with MCP Inspector

You can also use MCP Inspector to test this server outside of Claude.

Example:

```bash
npx @modelcontextprotocol/inspector uv run main_exp.py
```

This will launch the inspector UI in your browser, where you can try tools (`add_expense`, `list_expenses`, `summarize`) and check the resource (`expense://categories`) interactively.

---

## 📬 Contributing

Pull requests and feature suggestions are welcome.  
Follow the MCP design philosophy: modularity, clarity, and extensibility.

---

## 🛡 License

Released under the MIT License.
 
