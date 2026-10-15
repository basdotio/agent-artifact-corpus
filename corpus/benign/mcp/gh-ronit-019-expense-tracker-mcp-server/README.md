# Expense Tracker MCP Server

[![M8ven Score](https://m8ven.ai/badge/mcp/ronit-019-expense-tracker-mcp-server-1j8nio?v=5ca349b20275f3c87de29ec57daa9bb2)](https://m8ven.ai/mcp/ronit-019-expense-tracker-mcp-server-1j8nio?s=readme)

A simple personal Expense Tracker built as an **MCP (Model Context Protocol) server** using **FastMCP** and **SQLite**.

The server allows an MCP client such as Claude to manage expenses and budgets using natural language through MCP tools, access financial information through resources, and use predefined financial-analysis prompts.

The project focuses on understanding how **MCP tools, resources, prompts, database operations, CRUD design, and remote MCP transports** work together.

---

## Features

### Expense Management

A single `manage_expenses` tool handles all expense CRUD operations:

- Create expense
- Read/list expenses
- Update expense
- Delete expense

The tool uses an enum-based `CRUDAction`:

```text
CREATE
READ
UPDATE
DELETE
```

### Budget Management

A single `manage_budgets` tool handles all budget CRUD operations:

- Create budget
- Read/list budgets
- Update budget
- Delete budget

### Financial Analysis

- Budget vs Expense
- Financial Health Score

### Receipt / Image Workflow

The server can be used with Claude's image capabilities for receipt and bill workflows.

For example, a user can upload a restaurant or shopping receipt to Claude and ask it to add the expense.

The flow is:

```text
Receipt / Bill Image
        ↓
Claude interprets the image
        ↓
Claude extracts the expense information
        ↓
MCP manage_expenses tool
        ↓
SQLite
```

The image understanding is handled by the MCP client/LLM. The server is responsible for receiving the structured expense information and storing it.

### Tool Annotations:

- Explicit read-only, destructive, idempotency, and open-world hints for MCP tools.

---

## Large Expense List Optimization

The `READ` operation in `manage_expenses` includes a simple payload optimization.

If the query returns:

```text
≤ 50 expenses
```

the server returns the expenses directly as JSON.

If the query returns:

```text
> 50 expenses
```

the server:

1. Generates a CSV file
2. Stores it in the server's export directory
3. Calculates a compact summary
4. Returns the file URI, record count, and summary instead of sending every record directly to the LLM

Flow:

```text
manage_expenses(READ)
        │
        ▼
   Query SQLite
        │
        ▼
   Count records
     /       \
   ≤ 50      > 50
    │          │
    ▼          ▼
  JSON       CSV Export
               │
               ▼
        Compact Summary
```

This helps avoid unnecessarily sending large datasets into the LLM context.

---

## MCP Tools

The server uses **10 functional tools**:

| Tool | Description |
|---|---|
| `manage_expenses` | Create, read, update, and delete expenses |
| `manage_budgets` | Create, read, update, and delete budgets |
| `budget_vs_expense` | Compare budget against expenses |
| `financial_health_score` | Calculate a simple financial health score |

The two CRUD tools replace eight separate CRUD tools.

Originally:

```text
create_expense
list_expenses
update_expense
delete_expense

create_budget
list_budgets
update_budget
delete_budget
```

were separate tools.

They are now consolidated into:

```text
manage_expenses
manage_budgets
```

This reduces the MCP tool surface while keeping the same CRUD functionality.

### Tool Schema Benchmark

A simple benchmark of the MCP tool schemas produced:

```text
Separate CRUD tools
--------------------
Estimated schema tokens: 1,070

Consolidated CRUD tools
-----------------------
Estimated schema tokens: 601

Reduction
---------
Tool surface: 75%
Estimated schema context: 43.8%
```

The consolidation reduces the amount of tool-schema information that needs to be provided to the LLM while preserving the same CRUD operations.

---

## MCP Resources

The server provides the following resources:

### `expense://summary`

Provides a simple financial summary:

```text
Total Budget
Total Expenses
Remaining
```

### `expense://categories`

Provides the available expense categories:

```text
Food
Travel
Bills
Shopping
Entertainment
Health
Education
Other
```

### Expense CSV Exports

When more than 50 expenses are returned from a READ operation, the server creates an export using:

```text
expense://exports/{filename}
```

---

## MCP Prompts

### `financial_review`

Provides instructions for reviewing the user's financial situation using the available expense and budget information.

The review includes:

- Total spending
- Budget usage
- Highest spending categories
- Overspending
- Simple suggestions

### `budget_advice`

Provides instructions for analyzing budgets and expenses and suggesting practical budget improvements.

---

## Tech Stack

- Python
- FastMCP
- MCP
- SQLite
- aiosqlite
- Claude
- CSV

---

## Project Structure

```text
Expense-Tracker/
│
├── main.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── exports/
│   └── generated expense CSV files
│
└── expenses.db
    └── Created automatically when the server runs
```

`expenses.db` and generated export files should be ignored by Git.

---

## How It Works

```text
                 MCP Client
                  (Claude)
                     │
                     │ MCP
                     ▼
              FastMCP Server
                     │
        ┌────────────┼────────────┐
        │            │            │
      Tools       Resources     Prompts
        │            │            │
        └────────────┼────────────┘
                     │
                     ▼
                  SQLite
                     │
                     ▼
               expenses.db
```

For a large expense query:

```text
Claude
  │
  ▼
manage_expenses(READ)
  │
  ▼
SQLite
  │
  ▼
More than 50?
  │
  ├── No ──► JSON response
  │
  └── Yes
       │
       ▼
    Generate CSV
       │
       ▼
  Compact summary + URI
```

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repository-url>
cd Expense-Tracker
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

**Windows:**

```cmd
.venv\Scripts\activate
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the server

```bash
python main.py
```

The default local transport is `stdio`.

The SQLite database is automatically created when the server starts.

---

## Using Claude

The server can be connected to an MCP client such as Claude.

Once connected, you can interact with it using natural language.

Examples:

```text
Add an expense of ₹500 for dinner in Food.
```

```text
Show me all my expenses.
```

```text
Update expense 3 and change the amount to ₹750.
```

```text
Delete expense 3.
```

```text
Create a Food budget of ₹5000 for October 2026.
```

```text
Show my budgets.
```

```text
Compare my Food budget with my Food expenses.
```

```text
Give me my financial health score.
```

For receipt workflows:

```text
[Upload receipt image]

Add this expense to my expense tracker.
```

Claude can interpret the uploaded receipt and call the appropriate MCP expense tool with the extracted information.

---

## Local and Remote Server

The same `main.py` supports both local and remote MCP usage.

### Local

The local server uses `stdio`:

```text
Claude
  │
  │ stdio
  ▼
main.py
  │
  ▼
SQLite
```

Run:

```bash
python main.py
```

### Remote

The server can also run remotely using **Streamable HTTP**.

Set:

```text
MCP_TRANSPORT=streamable-http
```

and provide the required port.

The server then runs using:

```text
MCP Client
    │
    │ Streamable HTTP
    ▼
Remote FastMCP Server
    │
    ▼
SQLite
```

The same tools, resources, and prompts are available in both modes.

---

## Database

The project uses SQLite to keep the implementation simple.

No separate database server is required.

On the first run, the application creates:

```text
expenses.db
```

with two tables:

```text
expenses
budgets
```

### Expenses

```text
id
title
amount
category
date
description
```

### Budgets

```text
id
category
amount
month
```

For a larger multi-user application, SQLite could be replaced with PostgreSQL.

---

## Testing Large Expense Lists

A temporary development tool named:

```text
seed_test_expenses
```

can create test expenses for testing the large-payload behavior.

For example, you can ask Claude:

```text
Create 65 test expenses for testing the large expense export feature.
```

This allows the `manage_expenses(READ)` operation to cross the 50-record threshold and test the CSV export behavior.

The tool is intended for development/testing and should be removed before the final production deployment.

---

## Why SQLite?

SQLite was chosen because this is a small MCP project.

It makes the server easy to:

- Run locally
- Understand
- Test
- Deploy
- Extend

For a larger application with multiple users and concurrent database access, PostgreSQL would be a better choice.

---

## Design Decisions

### Why consolidate CRUD tools?

Instead of exposing eight separate CRUD tools, the server uses:

```text
manage_expenses
manage_budgets
```

with:

```text
CREATE
READ
UPDATE
DELETE
```

This keeps the MCP tool surface smaller while retaining the same functionality.

### Why export large result sets?

Returning hundreds of expense records directly to an LLM can unnecessarily increase context usage.

The server therefore uses a simple threshold:

```text
≤ 50 records → JSON

> 50 records → CSV + summary
```

This keeps normal queries simple while avoiding unnecessarily large tool responses.

### Why keep the implementation simple?

The project is primarily intended to demonstrate and understand:

- MCP tools
- MCP resources
- MCP prompts
- FastMCP
- CRUD operations
- Async SQLite operations
- LLM tool calling
- Remote MCP transports
- Large-payload handling

It intentionally avoids unnecessary production-level abstractions.

---

## Testing

Run the automated tests with:

```bash
pytest -v
```

The test suite covers expense CRUD operations, required-field validation, and the large-result CSV export threshold.

---

## License

This project is licensed under the MIT License.
See the [LICENSE](LICENSE) file for details.