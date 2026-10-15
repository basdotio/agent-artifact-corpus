#!/bin/bash
# Quick setup script to initialize the workspace with example tools

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Setting up Do It All MCP (diaMCP) workspace..."

mkdir -p "$SCRIPT_DIR/workspace/tools"

if [ ! -f "$SCRIPT_DIR/workspace/tools/__init__.py" ]; then
    touch "$SCRIPT_DIR/workspace/tools/__init__.py"
    echo "Created __init__.py in workspace/tools/"
fi

if [ ! -f "$SCRIPT_DIR/workspace/my_first_tool.py" ]; then
    cat > "$SCRIPT_DIR/workspace/my_first_tool.py" << 'EOF'
"""Example custom tool created during setup"""

from tools.base import tool


@tool(
    name="word_count",
    description="Count words, characters, and lines in text",
    schema={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to analyze"}
        },
        "required": ["text"]
    }
)
def word_count(text: str) -> str:
    """Count words, chars, and lines in text."""
    lines = text.count('\n') + 1
    words = len(text.split())
    chars = len(text)
    return f"Lines: {lines}, Words: {words}, Characters: {chars}"
EOF
    echo "Created example tool: workspace/my_first_tool.py"
fi

echo "Setup complete! Your workspace is ready at: $SCRIPT_DIR/workspace"
echo ""
echo "To run the MCP server:"
echo "  Docker: docker compose up --build"
echo "  Or:     pip install -r requirements.txt && python server.py"
