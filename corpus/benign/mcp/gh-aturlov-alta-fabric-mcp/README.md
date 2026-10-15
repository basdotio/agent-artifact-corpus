# Fabric MCP Server

A Python-based Model Context Protocol (MCP) server for interacting with Microsoft Fabric APIs via GitHub Copilot in VS Code.

## Overview

This MCP server exposes tools that allow GitHub Copilot to:
- List Microsoft Fabric workspaces
- List lakehouses in a workspace
- (More tools can be added for pipelines, GraphQL queries, etc.)

## Prerequisites

- Python 3.12+
- Conda (recommended) or Python virtual environment
- ODBC Driver 17 (or 18) for SQL Server
- GitHub Copilot in VS Code
- (Optional) Microsoft Entra ID app registration for service principal authentication

## Setup

### 1. Create and activate conda environment

```bash
conda create -p ./env python=3.12 -y
conda activate ./env
```

### 2. Install dependencies

```bash
pip install fastmcp python-dotenv msal httpx pyodbc
pip freeze > requirements.txt
```

### 3. Configure authentication

The server supports two authentication modes:

#### Option 1: Interactive Authentication (Recommended for Individual Users)

**No configuration needed!** The server uses device code flow by default.

On first run, you'll see a prompt in the MCP server output with:
- A URL to visit (https://microsoft.com/devicelogin)
- A code to enter
- Instructions to sign in with your Microsoft account

Tokens are cached in `~/.fabric_mcp_token_cache.json` and will be refreshed automatically.

#### Option 2: Service Principal Authentication (For Automation)

Copy `.env.example` to `.env` and configure service principal credentials:

```bash
cp .env.example .env
```

Edit `.env`:
```
FABRIC_CLIENT_ID=your_client_id_here
FABRIC_CLIENT_SECRET=your_client_secret_here
FABRIC_TENANT_ID=your_tenant_id_here
```

The presence of `FABRIC_CLIENT_SECRET` triggers service principal authentication.

### 4. Run the MCP server

For stdio transport (recommended for VS Code):
```bash
python main.py
```

For development/testing with interactive mode:
```bash
fastmcp dev main:mcp
```

Or simply:
```bash
python main.py
```

## Available Tools

### `list_workspaces()`
Lists all Microsoft Fabric workspaces accessible to the authenticated user.

**Returns:**
```json
{
  "workspaces": [
    {"id": "workspace-id", "name": "Workspace Name"}
  ]
}
```

### `list_lakehouses(workspace_id: str)`
Lists all lakehouses in a specific workspace.

**Parameters:**
- `workspace_id` (str): The ID of the workspace

**Returns:**
```json
{
  "lakehouses": [
    {"id": "lakehouse-id", "name": "Lakehouse Name"}
  ]
}
```

### `get_lakehouse_tables(workspace_id: str, lakehouse_id: str)`
Get all tables in a lakehouse. Works with both schema-enabled and schema-less lakehouses using SQL-based discovery.

**Parameters:**
- `workspace_id` (str): The ID of the workspace
- `lakehouse_id` (str): The ID of the lakehouse

**Returns:**
```json
{
  "tables": [
    {
      "schema": "bronze",
      "name": "Customer",
      "type": "BASE TABLE",
      "full_name": "bronze.Customer"
    }
  ]
}
```

### `get_table_schema(workspace_id: str, lakehouse_id: str, table_name: str)`
Get detailed schema information for a table including column definitions.

**Parameters:**
- `workspace_id` (str): The ID of the workspace
- `lakehouse_id` (str): The ID of the lakehouse
- `table_name` (str): The name of the table

**Returns:**
```json
{
  "table_name": "Customer",
  "columns": [
    {
      "name": "CustomerID",
      "data_type": "int",
      "is_nullable": false,
      "position": 1
    }
  ]
}
```

### `get_table_sample_data(workspace_id: str, lakehouse_id: str, table_name: str, limit: int = 10)`
Get sample data from a table.

**Parameters:**
- `workspace_id` (str): The ID of the workspace
- `lakehouse_id` (str): The ID of the lakehouse
- `table_name` (str): The name of the table
- `limit` (int): Number of rows to return (default: 10)

**Returns:**
```json
{
  "table_name": "Customer",
  "sample_rows": [{"CustomerID": 1, "Name": "John"}],
  "row_count": 10
}
```

### `execute_custom_sql_query(workspace_id: str, lakehouse_id: str, query: str)`
Execute a custom SQL query against a lakehouse.

**Parameters:**
- `workspace_id` (str): The ID of the workspace
- `lakehouse_id` (str): The ID of the lakehouse
- `query` (str): The SQL query to execute

**Returns:**
```json
{
  "query": "SELECT * FROM bronze.Customer",
  "success": true,
  "row_count": 100,
  "results": [{"CustomerID": 1, "Name": "John"}]
}
```

### `sign_out()`
Sign out and clear cached authentication tokens (interactive auth only).

**Returns:**
```json
{
  "status": "success",
  "message": "Signed out successfully."
}
```

## Integration with GitHub Copilot

### Method 1: Using mcp.json (Recommended if you have MCP extension)

1. The `mcp.json` file in this directory is already configured
2. If you have the VS Code MCP extension installed, you should see "Run" buttons in the file
3. Click "Run" to start the server
4. The server will automatically integrate with GitHub Copilot

### Method 2: Manual VS Code Settings Configuration

1. Open VS Code Settings (JSON):
   - Press `Ctrl+Shift+P` (Windows) or `Cmd+Shift+P` (Mac)
   - Type "Preferences: Open User Settings (JSON)"
   - Press Enter

2. Add this configuration:
```json
{
  "github.copilot.chat.mcp.enabled": true,
  "github.copilot.chat.mcp.servers": {
    "fabric": {
      "command": "python",
      "args": ["main.py"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

3. Reload VS Code:
   - Press `Ctrl+Shift+P`
   - Type "Developer: Reload Window"
   - Press Enter

### Testing the Integration

Once configured, open GitHub Copilot Chat and ask questions like:
- "List all my Fabric workspaces"
- "Show me the lakehouses in workspace XYZ"
- "What Microsoft Fabric resources do I have access to?"

Copilot will automatically use your MCP tools to answer these questions.

## Development

### Testing tools locally

You can test the MCP server locally by running:

```bash
python main.py
```

Or use the FastMCP CLI for interactive testing:

```bash
fastmcp dev main:mcp
```

This will start an interactive session where you can call tools directly.

### Adding new tools

To add a new tool, use the `@mcp.tool()` decorator:

```python
@mcp.tool()
async def my_new_tool(param: str) -> dict:
    """
    Tool description for Copilot.
    
    Args:
        param: Parameter description
    
    Returns:
        dict: Response data
    """
    # Implementation
    return {"result": "data"}
```

## Security Notes

- Never commit `.env` file to version control
- Use service principal authentication with minimum required permissions
- Rotate secrets regularly
- Consider using Azure Key Vault for production deployments

## Troubleshooting

### Token acquisition fails
- Verify your app registration has correct API permissions
- Ensure admin consent is granted for application permissions
- Check that the service principal has necessary Fabric roles

### Tools not appearing in Copilot
- Verify the MCP server is properly configured in VS Code settings
- Check the VS Code output panel for MCP-related errors
- Restart VS Code after configuration changes

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
