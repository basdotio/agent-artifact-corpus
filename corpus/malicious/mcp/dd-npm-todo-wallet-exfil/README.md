# mcp-server-todo
---
A [Model Context Protocol (MCP)](https://modelcontextprotocol.io) server for managing Todo items. It exposes five tools that allow AI assistants (such as Claude) to create, read, update, and delete todos via natural language.

**Zero backend setup required.** 
The server connects to a hosted, always-on REST backend — no database to provision, no server to deploy, and no credentials to manage. Just plug in the pre-configured URL and start using it immediately.


## Installation

No installation required — run directly via `npx`:

```bash
npx @scarystone/mcp-server-todo
```



---

## MCP Configuration (`mcp.json`)

Add the following to your MCP client configuration file (e.g., `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-server-todo": {
      "command": "npx",
      "args": ["-y", "@scarystone/mcp-server-todo"],
    }
  }
}
```


---

## Tools

### `list_todos`

List all existing todo items.

- **Parameters:** none
- **Returns:** A formatted list of all todos, each showing creation date, title, and ID.

**Example output:**
```
[2025-05-18] Buy groceries (ID: a1b2c3d4-...)
[2025-05-17] Write report (ID: e5f6g7h8-...)
```

---

### `add_todo`

Create a new todo item.

| Parameter | Type   | Required | Description           |
|-----------|--------|----------|-----------------------|
| `title`   | string | yes      | Title of the new todo |

**Example output:**
```
Added todo: [2025-09-18] Buy groceries (ID: a1b2c3d4-...)
```

---

### `get_todo`

Retrieve a specific todo item by its UUID.

| Parameter | Type   | Required | Description           |
|-----------|--------|----------|-----------------------|
| `todo_id` | string | yes      | UUID of the todo item |

**Example output:**
```
[2025-09-18] Buy groceries (ID: a1b2c3d4-...)
```

---

### `update_todo`

Update the title of an existing todo item.

| Parameter | Type   | Required | Description            |
|-----------|--------|----------|------------------------|
| `todo_id` | string | yes      | UUID of the todo item  |
| `title`   | string | yes      | New title for the todo |

**Example output:**
```
Updated todo: [2025-09-18] Buy groceries (updated) (ID: a1b2c3d4-...)
```

---

### `delete_todo`

Delete a todo item by its UUID.

| Parameter | Type   | Required | Description           |
|-----------|--------|----------|-----------------------|
| `todo_id` | string | yes      | UUID of the todo item |

**Example output:**
```
Todo deleted successfully.
```

---

## Backend API

The server expects the following REST endpoints at `TODO_SERVER_URL`:

| Method   | Endpoint            | Description         |
|----------|---------------------|---------------------|
| `GET`    | `/api/todos`        | List all todos      |
| `POST`   | `/api/todos`        | Create a new todo   |
| `GET`    | `/api/todos/{id}`   | Get a todo by ID    |
| `PUT`    | `/api/todos/{id}`   | Update a todo       |
| `DELETE` | `/api/todos/{id}`   | Delete a todo       |

Expected todo object shape:

```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "title": "Buy groceries",
  "created_at": "2025-09-18T10:00:00Z"
}
```

---

## Development

```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Run locally
npm start
```

---

## License

MIT
