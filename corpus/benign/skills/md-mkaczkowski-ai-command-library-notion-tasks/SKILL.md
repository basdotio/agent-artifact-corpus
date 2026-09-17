---
name: notion-tasks
description: Manage tasks in Notion. List, create, update tasks. Use for any Notion task-related operations.
---

# Notion Tasks Management

Manage tasks in a Notion database using the Notion MCP server.

## Prerequisites

Requires the Notion MCP server to be configured. Add to your MCP settings:

```json
{
  "mcpServers": {
    "notion": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.notion.com/mcp"]
    }
  }
}
```

## Configuration

Before using this skill, configure your task database:

1. **Database URL**: Your Notion database URL
2. **Data Source ID**: The collection ID (get from fetching the database)

Example configuration (add to your project's skill copy):

```
Database URL: https://www.notion.so/{database_id}
Data Source ID: collection://{data_source_id}
```

## Database Schema

Recommended schema for task tracking:

| Property     | Type         | Options/Description            |
| ------------ | ------------ | ------------------------------ |
| Task name    | title        | Task title (required)          |
| Status       | status       | Not started, In progress, Done |
| Priority     | select       | High, Medium, Low              |
| Effort level | select       | Small, Medium, Large           |
| Description  | text         | Short summary                  |
| Task type    | multi_select | Bug, Feature request, Polish   |
| PR           | url          | GitHub PR link                 |
| Assignee     | person       | Who's responsible              |
| Due date     | date         | Deadline                       |

**Note**: Multi-select options may include emojis (e.g., `🐞 Bug`, `💬 Feature request`, `💅 Polish`). Always use the exact option names from your database schema.

## Available Operations

### 1. List Tasks

Search and filter tasks in the database:

```
mcp__notion__notion-search
- query: "search term"
- data_source_url: "collection://{data_source_id}"
```

**Note**: Search doesn't filter by Status. Fetch individual pages to check properties.

### 2. Fetch Task Details

Get full task content and properties:

```
mcp__notion__notion-fetch
- id: {page_id_or_url}
```

### 3. Create a Task

```
mcp__notion__notion-create-pages
- parent: { "data_source_id": "{data_source_id}" }
- pages: [{
    "properties": {
      "Task name": "Task title",
      "Status": "Not started",
      "Priority": "High",
      "Description": "Task description"
    },
    "content": "## Task Description\n..."
  }]
```

### 4. Update Task Properties

```
mcp__notion__notion-update-page
- data: {
    "page_id": "{page_id}",
    "command": "update_properties",
    "properties": {
      "Status": "In progress",
      "PR": "https://github.com/..."
    }
  }
```

### 5. Update Task Content

**Replace all content:**

```
mcp__notion__notion-update-page
- data: {
    "page_id": "{page_id}",
    "command": "replace_content",
    "new_str": "## New content\n..."
  }
```

**Insert after specific text:**

```
mcp__notion__notion-update-page
- data: {
    "page_id": "{page_id}",
    "command": "insert_content_after",
    "selection_with_ellipsis": "## Section...end text",
    "new_str": "\n## New Section\nContent here"
  }
```

**Critical**: Always fetch the page first before using `insert_content_after` or `replace_content_range`.

## Markdown Content Support

Notion supports these markdown elements:

- **Bold**, _italic_, `code`, ~~strikethrough~~
- Headers: `#`, `##`, `###`
- Lists: `-`, `1.`
- Checkboxes: `- [ ]`, `- [x]`
- Blockquotes: `>`
- Code blocks: ` ```language `
- Tables: `| col1 | col2 |`
- Dividers: `---`
- Links: `[text](url)`

## Workflow Examples

### Get all "Not started" tasks

1. Search data source for tasks
2. Fetch each result
3. Filter where Status === "Not started"

### Move task to "In progress" with PR link

1. Fetch task to confirm current state
2. Update properties: Status + PR

### Create task from GitHub issue

1. Create page in data source
2. Set Task name, Status, Priority, Task type
3. Add content with issue description

## Limitations

- **No status filtering in search** - must fetch individual pages
- **No bulk updates** - update one page at a time
- **Content sync timing** - always re-fetch before content edits
- **Page icons** - cannot be set via MCP (set manually in Notion UI)

## Tool Reference

| Tool                                  | Purpose                        |
| ------------------------------------- | ------------------------------ |
| `mcp__notion__notion-search`          | Search pages/databases         |
| `mcp__notion__notion-fetch`           | Get page/database details      |
| `mcp__notion__notion-create-pages`    | Create new pages               |
| `mcp__notion__notion-update-page`     | Update page properties/content |
| `mcp__notion__notion-create-database` | Create new database            |
| `mcp__notion__notion-update-database` | Update database schema         |
