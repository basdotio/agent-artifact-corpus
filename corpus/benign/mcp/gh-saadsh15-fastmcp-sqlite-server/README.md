# FastMCP SQLite Server 🚀

A production-ready **Model Context Protocol (MCP)** server built with [FastMCP](https://github.com/jlowin/fastmcp) and [FastAPI](https://fastapi.tiangolo.com/), providing database management tools for AI assistants alongside a RESTful HTTP administration API and a modern web user signup portal.

---

## ✨ Features

- **🧠 Model Context Protocol (MCP) Integration**: Exposes standard MCP tools (`get_database_stats`, `inspect_database_schema`, `list_users`, `get_user_by_id`, `create_new_user`, `update_user`, `delete_user`, `run_readonly_sql`) for AI assistants (Cursor, Claude Desktop, Gemini, MCP Inspector).
- **🌐 RESTful HTTP API**: Custom HTTP routes under `/mcp/db/...` to query, create, update, delete, and inspect SQLite records directly using standard HTTP clients (curl, browser, frontend).
- **🎨 Modern Web UI**: Responsive sign-up page (`/auth/signup` and `/signup`) featuring Plus Jakarta Sans typography, live password strength indicator, show/hide password toggle, and asynchronous form submission.
- **🔒 Security & Safety**:
  - Passwords hashed before database persistence.
  - Guarded read-only SQL endpoint (`SELECT`, `PRAGMA`, `EXPLAIN` only) preventing unintended database modifications.
  - Parameterized queries via SQLAlchemy preventing SQL injection.
- **⚡ Dual Mode Execution**: Run as a unified FastAPI web server (with MCP mounted at `/mcp`) or as an independent standalone FastMCP server.

---

## 📁 Project Structure

```text
├── main.py                 # FastAPI application entrypoint with mounted routers & FastMCP
├── mcp_server.py           # FastMCP server with MCP tools and HTTP database management routes
├── user_signup.py          # User registration route and template server
├── get_user.py             # User query and pagination route
├── init_data.py            # Database initialization and mock data generator
├── templates/
│   └── signup.html         # Responsive, glassmorphic sign-up page UI
├── requirements.txt        # Python package dependencies
├── .env.example            # Sample environment variables template
└── .gitignore              # Ignored files (virtual environments, database, secrets)
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+
- [`uv`](https://github.com/astral-sh/uv) (recommended) or standard `pip`

### 2. Installation

Clone the repository and install dependencies:

```bash
git clone https://github.com/saadsh15/FastMCP_sqlite_server.git
cd FastMCP_sqlite_server

# Using uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# Or using standard pip
python -m venv env
source env/bin/activate
pip install -r requirements.txt
```

### 3. Initialize the Database (Optional)

To initialize the SQLite database (`arzonama.db`) and populate it with sample mock user records:

```bash
python init_data.py
```

---

## 🖥️ Running the Application

### Option A: Run Unified FastAPI Server (Default)

Runs the main FastAPI web application, mounting the web UI, REST API, and FastMCP server on port `8000`:

```bash
uv run fastapi dev
# or
uvicorn main:app --reload
```

Once running:
- **Web Sign-up Page**: [http://127.0.0.1:8000/auth/signup](http://127.0.0.1:8000/auth/signup) (or `/signup`)
- **FastAPI OpenAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **FastMCP HTTP Routes**: [http://127.0.0.1:8000/mcp/db/stats](http://127.0.0.1:8000/mcp/db/stats)
- **MCP Protocol Endpoint**: [http://127.0.0.1:8000/mcp/mcp](http://127.0.0.1:8000/mcp/mcp)

### Option B: Run FastMCP Standalone

Runs the FastMCP server independently on port `8001`:

```bash
python mcp_server.py
```

### Option C: Run FastMCP Dev Inspector

Use the FastMCP developer inspector UI:

```bash
fastmcp dev mcp_server.py
```

---

## 🛠️ MCP Tools Reference

When connecting an MCP-compatible client (such as Claude Desktop or Cursor), the following tools are available:

| Tool Name | Parameters | Description |
| :--- | :--- | :--- |
| `get_database_stats` | *None* | Returns database size, user counts, and latest signup. |
| `inspect_database_schema` | *None* | Introspects tables, columns, constraints, and indexes. |
| `list_users` | `limit`, `offset`, `search`, `is_premium` | Queries users with search and pagination filters. |
| `get_user_by_id` | `user_id` | Fetches details of a single user by ID. |
| `create_new_user` | `full_name`, `email`, `password`, `is_premium` | Inserts a new user with hashed password. |
| `update_user` | `user_id`, `full_name`?, `email`?, `is_premium`? | Updates user attributes. |
| `delete_user` | `user_id` | Deletes a user by ID. |
| `run_readonly_sql` | `sql_query` | Executes safe `SELECT` / `PRAGMA` SQL queries. |

---

## 📡 HTTP API Reference

All database management HTTP endpoints are available under `/mcp/db`:

### 1. Database Stats
- **`GET /mcp/db/stats`**
```bash
curl -s http://127.0.0.1:8000/mcp/db/stats
```
```json
{
  "database": "arzonama.db",
  "file_size_mb": 8.24,
  "total_users": 50000,
  "premium_users": 0,
  "standard_users": 50000,
  "newest_signup": "2026-10-07T17:22:31"
}
```

### 2. Schema Introspection
- **`GET /mcp/db/schema`**
```bash
curl -s http://127.0.0.1:8000/mcp/db/schema
```

### 3. List / Search Users
- **`GET /mcp/db/users?search=alice&limit=10&offset=0`**
```bash
curl -s "http://127.0.0.1:8000/mcp/db/users?search=alice&limit=2"
```

### 4. Create User
- **`POST /mcp/db/users`**
```bash
curl -X POST http://127.0.0.1:8000/mcp/db/users \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Alice Johnson",
    "email": "alice.johnson@example.com",
    "password": "SecurePassword123!",
    "is_premium": true
  }'
```

### 5. Update User
- **`PATCH /mcp/db/users/{id}`**
```bash
curl -X PATCH http://127.0.0.1:8000/mcp/db/users/1 \
  -H "Content-Type: application/json" \
  -d '{"is_premium": true}'
```

### 6. Delete User
- **`DELETE /mcp/db/users/{id}`**
```bash
curl -X DELETE http://127.0.0.1:8000/mcp/db/users/1
```

### 7. Run Read-Only SQL Query
- **`POST /mcp/db/query`**
```bash
curl -X POST http://127.0.0.1:8000/mcp/db/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT count(*) AS total FROM user WHERE is_premium = 1"}'
```

---

## 🔒 Security Notes

- SQLite database files (`*.db`) and secrets (`.env`) are excluded from version control via `.gitignore`.
- Password hashes are stored using SHA-256.
- The SQL query endpoint strictly forbids non-readonly queries (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`).

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
