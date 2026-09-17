---
name: ADK Tools
description: This skill should be used when the user asks about "adding a tool", "FunctionTool", "creating tools", "MCP integration", "OpenAPI tools", "built-in tools", "google_search tool", "code_execution tool", "long-running tools", "async tools", "third-party tools", "LangChain tools", "computer use", or needs guidance on extending agent capabilities with custom functions, API integrations, or external tool frameworks.
version: 3.0.0
---

# ADK Tools

Guide for extending agent capabilities with tools. Covers custom functions, API integrations, and external frameworks.

## When to Use

- Adding custom Python functions as tools
- Integrating external APIs
- Connecting MCP servers
- Using built-in ADK tools
- Handling long-running operations
- Computer use capabilities
- LangChain/LlamaIndex tool integration

## When NOT to Use

- Initial project setup → Use `@adk-core` instead
- Creating agents → Use `@adk-core` instead
- Multi-agent coordination → Use `@adk-orchestration` instead
- Security policies → Use `@adk-production` instead

## Key Concepts

**FunctionTool** wraps Python functions into agent-callable tools. Docstrings become tool descriptions, type hints define parameters.

**Built-in Tools** like `google_search` and `code_execution` are pre-configured and ready to use via tool name.

**MCP Integration** connects Model Context Protocol servers as tool sources. Configure in `adk.yaml` or via `.mcp.json`.

**OpenAPI Tools** auto-generate from API specifications. ADK creates typed tools from your OpenAPI schemas.

**Long-Running Tools** use async patterns or callbacks for operations that exceed typical timeouts.

**Computer Use Tools** provide screen, keyboard, and mouse control for desktop automation tasks.

**Third-Party Frameworks** like LangChain and LlamaIndex expose their tool ecosystems to ADK agents.

## Implementation Pattern

```python
from adk.tools import FunctionTool
from adk import LlmAgent

def calculate_area(length: float, width: float) -> float:
    """Calculate rectangle area."""
    return length * width

area_tool = FunctionTool(calculate_area)
agent = LlmAgent(tools=[area_tool])
```

## References

Detailed guides with code examples:
- `references/tools-function.md` - Custom Python tools
- `references/tools-builtin.md` - Pre-configured tools
- `references/tools-mcp.md` - MCP server integration
- `references/tools-openapi.md` - OpenAPI schemas
- `references/tools-async.md` - Long-running operations
- `references/tools-computer-use.md` - Desktop automation
- `references/tools-third-party.md` - LangChain/LlamaIndex
