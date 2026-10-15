# Wolfram MCP

A FastMCP server that provides Wolfram Language evaluation capabilities through the Model Context Protocol (MCP). This allows AI assistants and other MCP clients to execute Wolfram Language code and receive results.

## Features

- **Wolfram Language Integration**: Execute Wolfram Language expressions and receive results
- **Persistent Session**: Maintains a Wolfram Language session for efficient evaluation
- **Error Handling**: Comprehensive error handling for Wolfram Client exceptions
- **Session Management**: Tools to evaluate code and terminate sessions
- **MCP Compliance**: Full Model Context Protocol compliance for seamless integration

## Prerequisites

- Python 3.12 or higher
- Wolfram Engine (must be installed and accessible)
- Valid Wolfram Engine license

## Installation

1. Clone this repository:
```bash
git clone https://github.com/12458/wolfram-mcp.git
cd wolfram-mcp
```

2. Install dependencies using uv (recommended):
```bash
uv sync
```

Or using pip:
```bash
pip install -e .
```

## Usage

### Running the MCP Server

Start the Wolfram MCP server:

```bash
python main.py
```

The server runs on STDIO transport by default, making it compatible with MCP clients.

### Available Tools

#### `eval_wolfram(code: str) -> str`
Evaluates a Wolfram Language expression and returns the result as a string.

**Parameters:**
- `code` (str): The Wolfram Language expression to evaluate

**Returns:**
- `str`: The result of the evaluation or an error message

**Example:**
```python
result = eval_wolfram("2 + 2")
# Returns: "4"

result = eval_wolfram("Plot[Sin[x], {x, 0, 2 Pi}]")
# Returns: plot object representation
```

#### `terminate_session() -> str`
Terminates the Wolfram Language session and frees resources.

**Returns:**
- `str`: Confirmation message or error details

## Configuration

The server uses default MCP configuration. For custom configuration, modify the `main.py` file:

```python
# Custom MCP server configuration
eval_mcp = FastMCP("Wolfram REPL MCP", version="1.0.0")
```

## Error Handling

The server handles various error scenarios:

- **WolframClientException**: Wolfram Engine communication errors
- **General Exceptions**: Unexpected errors during evaluation
- **Session Management**: Errors during session termination

## Development

### Project Structure

```
wolfram/
├── main.py          # Main MCP server implementation
├── pyproject.toml   # Project configuration and dependencies
├── README.md        # This file
└── uv.lock          # Dependency lock file
```

### Adding New Tools

To add new Wolfram Language tools, create new functions with the `@eval_mcp.tool` decorator:

```python
@eval_mcp.tool
def new_wolfram_tool(param: str) -> str:
    """Description of the new tool."""
    try:
        # Your Wolfram Language code here
        expr = wlexpr(param)
        result = session.evaluate(expr)
        return repr(result)
    except Exception as e:
        return f"Error: {e}"
```

## License

Licensed under the [MIT License](https://github.com/12458/wolfram-mcp)