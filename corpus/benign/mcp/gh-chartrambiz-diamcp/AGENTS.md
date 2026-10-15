# Agent Tools - diaMCP

This file documents capabilities for AI agents using the diaMCP server.

## Creating New Tools

You can create your own tools dynamically using the `create_tool` function. When you discover an API or need a capability that doesn't exist, you can bootstrap a new tool.

### The create_tool Tool

**Parameters:**
- `name` - Tool name (lowercase, underscores, starts with letter)
- `description` - What the tool does
- `schema` - JSON schema for parameters (as JSON string)
- `code` - Python function body (MUST follow the template below)
- `requirements` - Optional. Any new Python package dependencies (e.g., `yfinance>=1.2.0`)

### ⚠️ STRICT RULES FOR CODE PARAMETER

The `code` parameter MUST follow this exact template:

```python
# 1. Imports FIRST (before anything else)
import requests
import json

# 2. Then the function with @tool decorator
def my_tool(param1: str, param2: int = 10) -> str:
    """
    Brief description of what this tool does.
    
    Args:
        param1: Description of first parameter
        param2: Description of second parameter (default: 10)
    
    Returns:
        Description of what is returned
    """
    try:
        # Your code here
        return "success"
    except Exception as e:
        return f"Error: {str(e)}"
```

**CRITICAL RULES:**
1. **ALL imports MUST be at the very top** - before the `@tool` decorator
2. **The function name MUST match the tool name**
3. **The `@tool` decorator and function definition MUST be together** - decorator on line above function
4. **Schema must have proper bracket matching** - verify all `{}` and `[]` are closed

### Example: Creating a Simple Tool

Suppose the user mentions a weather API at `api.weather.com` with endpoint `/current?city=X`. You could create a tool:

```
create_tool(
    name="get_weather",
    description="Get current weather for a city from the weather API",
    schema='''{
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"}
        },
        "required": ["city"]
    }''',
    code='''import httpx

def get_weather(city: str) -> str:
    """
    Get current weather for a city from the weather API.
    
    Args:
        city: The city name to get weather for
    
    Returns:
        JSON weather data or error message
    """
    try:
        response = httpx.get(f"https://api.weather.com/current?city={city}", timeout=10)
        return response.json()
    except Exception as e:
        return f"Error: {e}"
''',
    requirements="httpx>=0.27.0"
)
```

**Important**: If you specify `requirements`, you **MUST tell the user**:
1. Add the package(s) to `requirements.txt`
2. Run `./restart.sh` to rebuild the container with the new dependency

### Example: Tool with Multiple Parameters

```
create_tool(
    name="calculate_tip",
    description="Calculate tip amount for a bill",
    schema='''{
        "type": "object",
        "properties": {
            "amount": {"type": "number", "description": "Bill amount"},
            "percentage": {"type": "number", "description": "Tip percentage", "default": 15}
        },
        "required": ["amount"]
    }''',
    code='''def calculate_tip(amount: float, percentage: float = 15) -> str:
    tip = amount * (percentage / 100)
    total = amount + tip
    return f"Tip: ${tip:.2f}, Total: ${total:.2f}"
'''
)
```

### Example: Tool that Returns Structured Data

```
create_tool(
    name="fetch_github_info",
    description="Get GitHub repository information",
    schema='''{
        "type": "object",
        "properties": {
            "owner": {"type": "string", "description": "Repository owner"},
            "repo": {"type": "string", "description": "Repository name"}
        },
        "required": ["owner", "repo"]
    }''',
    code='''def fetch_github_info(owner: str, repo: str) -> str:
    import httpx
    import json
    try:
        response = httpx.get(f"https://api.github.com/repos/{owner}/{repo}", timeout=10)
        data = response.json()
        return json.dumps({
            "name": data.get("name"),
            "stars": data.get("stargazers_count"),
            "language": data.get("language"),
            "description": data.get("description")
        }, indent=2)
    except Exception as e:
        return f"Error: {e}"
'''
)
```

### After Creating a Tool

1. The tool file is written to `/workspace/tools/`
2. **IMPORTANT**: User must restart MCP server for the tool to be loaded:
   ```bash
   cd ~/diamcp && ./restart.sh
   ```
3. Tool becomes available to both you and the user

### When to Restart the Server

The MCP server only loads tools and dependencies at startup. You **MUST** instruct the user to restart (`./restart.sh`) after:

- **Creating a new tool** - New tool files in `workspace/tools/` need to be loaded
- **Modifying an existing tool** - Changes won't take effect until restart
- **Adding new dependencies** - If a tool requires a new Python package, the container must be rebuilt and restarted
- **Removing a tool** - Must restart to unregister it

The server will NOT automatically detect or reload changes.

### Adding New Dependencies

If a new tool requires a Python package not in `requirements.txt`:

1. Add the package to `requirements.txt` (e.g., `yfinance>=1.2.0`)
2. Instruct user to run `./restart.sh` which will rebuild the Docker container with the new dependency
3. The tool will then be available after restart

**Important**: Simply restarting the container without rebuilding will NOT install new dependencies. The `./restart.sh` script handles both the rebuild and restart.

### Tool Schema Reference

**Parameter Types:**
- `string` - Text
- `number` - Floating point
- `integer` - Whole number
- `boolean` - true/false
- `array` - List of items
- `object` - Nested object

**Schema Properties:**
- `description` - Human-readable description
- `type` - Data type
- `required` - Required parameters array
- `default` - Default value for optional parameters
- `enum` - Allowed values array

### Best Practices for Tool Creation

1. **Descriptive names** - Use `snake_case`, descriptive names like `fetch_github_info` not `gh`
2. **Clear descriptions** - Explain what the tool returns and any notable behavior
3. **Error handling** - Always wrap API calls in try/except and return error messages
4. **Timeout** - Always set timeouts on external requests (10-30 seconds)
5. **Simple returns** - Return strings for simple results, JSON strings for structured data

### Example: Creating Multiple Related Tools

If a user describes a todo API with endpoints `/todos` (GET list, POST create, DELETE id):

```
create_tool(
    name="get_todos",
    description="Get all todos from the API",
    schema='{"type": "object", "properties": {}, "required": []}',
    code='''def get_todos() -> str:
    import httpx
    try:
        response = httpx.get("https://api.example.com/todos", timeout=10)
        return response.json()
    except Exception as e:
        return f"Error: {e}"
'''
)

create_tool(
    name="add_todo",
    description="Add a new todo item",
    schema='''{
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Todo title"},
            "completed": {"type": "boolean", "description": "Is completed", "default": false}
        },
        "required": ["title"]
    }''',
    code='''def add_todo(title: str, completed: bool = False) -> str:
    import httpx
    try:
        response = httpx.post("https://api.example.com/todos", json={"title": title, "completed": completed}, timeout=10)
        return f"Created: {response.json()}"
    except Exception as e:
        return f"Error: {e}"
'''
)
```

## Available Tools

You have access to these built-in tools:
- File operations: `read_file`, `write_file`, `list_directory`, `search_files`, `grep`, `file_info`, `delete_file`, `create_directory`
- Web: `web_search`, `web_fetch`, `download_file`
- Git: `git_clone`, `git_pull`
- System: `run_command`, `python_eval`, `run_python_script`, `get_system_info`, `get_time`, `calculate`, `count_lines`
- Security: `manage_blacklist`, `manage_approved`, `get_dangerous_patterns`
- Meta: `create_tool`

## Workspace

Tools are stored in `/workspace/tools/` inside the Docker container. This directory is mounted from `~/diamcp/workspace/tools/` on the host. Files there persist across restarts and are auto-loaded at server startup.

**Note**: The server only loads tools when it starts. If the server is already running, changes to tool files won't take effect until you restart.

## Quick Reference

```python
create_tool(
    name="tool_name",
    description="What it does",
    schema='{"type": "object", "properties": {"param": {"type": "string"}}, "required": ["param"]}',
    code='''def tool_name(param: str) -> str:
        return f"Result: {param}"
'''
)
```

**Remember**: After creating/modifying tools or adding dependencies, tell the user to run `./restart.sh`
