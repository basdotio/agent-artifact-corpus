# Expense Tracker MCP Server

A small [Model Context Protocol](https://modelcontextprotocol.io/) server built with [FastMCP](https://gofastmcp.com/). It stores expense entries in a local SQLite database and exposes tools for adding, listing, and summarizing expenses.

## Features

- Add expenses with a date, amount, category, subcategory, and note.
- List expenses within an inclusive date range.
- Summarize spending by category, optionally filtered to one category.
- Read the supported categories from the `expense://categories` resource.
- Persist data locally in `expenses.db`.

## Requirements

- Python 3.12 or newer
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- Claude Desktop, MCP Inspector, or another MCP-compatible client

## Setup

Clone the repository and install its dependencies:

```powershell
git clone https://github.com/sanyagupta31/expensetrackermcpserver.git
cd expensetrackermcpserver
uv sync
```

The database is created automatically the first time the server starts. It is intentionally ignored by Git because it contains local user data.

## Run the server

Run the server directly over the default stdio transport:

```powershell
uv run fastmcp run main.py
```

To develop and test the server with the MCP Inspector:

```powershell
uv run fastmcp dev inspector main.py
```

## Connect Claude Desktop

For the standard Claude Desktop installation, run:

```powershell
uv run fastmcp install claude-desktop main.py
```

For the Microsoft Store version of Claude Desktop on Windows, use its package configuration directory:

```powershell
uv run fastmcp install claude-desktop `
	--config-path "$env:LOCALAPPDATA\Packages\Claude_pzs8sxrjxfjjc\LocalCache\Roaming\Claude" `
	main.py
```

Restart Claude Desktop after installation. The server will appear as **ExpenseTracker**.

### Claude Desktop in action

The server is connected to Claude Desktop and can answer natural-language questions about stored expenses, including displaying a monthly expense table.

![Expense Tracker MCP server running in Claude Desktop](docs/claude-desktop-expense-table.png)

## Available MCP tools

### `add_expense`

Adds an expense to the local database.

Arguments: `date`, `amount`, `category`, `subcategory` (optional), and `note` (optional).

### `list_expenses`

Returns all expenses between `start_date` and `end_date`, inclusive.

### `summarize`

Returns totals grouped by category for a date range. Pass `category` to filter the summary.

## Project structure

```text
.
├── categories.json       # Supported categories and subcategories
├── main.py               # FastMCP server and SQLite operations
├── pyproject.toml        # Project metadata and dependencies
├── README.md
└── uv.lock               # Reproducible dependency lockfile
```

## Data and security

The server writes `expenses.db` next to `main.py`. This is a local demonstration project; add authentication, validation, backups, and a production database before exposing it to untrusted clients or networks.

## License

This project is licensed under the MIT License.
