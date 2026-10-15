"""Example user tool - add your own tools here!"""

from tools.base import tool


@tool(
    name="hello_world",
    description="A simple hello world tool for demonstration",
    schema={
        "type": "object",
        "properties": {"name": {"type": "string", "description": "Name to greet"}},
        "required": ["name"],
    },
)
def hello_world(name: str) -> str:
    """Greet someone by name."""
    return f"Hello, {name}! Welcome to the DiamCP MCP server."


@tool(
    name="reverse_text",
    description="Reverse a string of text",
    schema={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to reverse"}},
        "required": ["text"],
    },
)
def reverse_text(text: str) -> str:
    """Reverse the input text."""
    return text[::-1]
