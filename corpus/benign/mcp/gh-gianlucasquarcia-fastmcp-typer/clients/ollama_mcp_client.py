"""Bridge between a local Ollama model and this project's FastMCP server.

Starts the MCP server as a stdio subprocess, exposes its tools to an Ollama
model via the standard OpenAI-style `tools` chat parameter, and executes any
tool calls the model requests by forwarding them to the MCP server.

Usage:
    uv run ollama_mcp_client.py "What time is it?"

Requires a running Ollama daemon (``ollama serve``) with a tool-calling
capable model already pulled, e.g. ``ollama pull llama3.1``.
"""

import asyncio
import sys
from pathlib import Path

import ollama
from mcp import Client, StdioServerParameters
from mcp_types import Tool as MCPTool

ROOT = Path(__file__).resolve().parent.parent
SERVER_PATH = ROOT / "mcp_server.py"
LOCAL_OLLAMA_MODEL = "llama3.1"  # Ollama model to use for tool calls


def to_ollama_tool(tool: MCPTool) -> dict:
    """Convert an MCP tool definition into the tool schema Ollama expects."""
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": tool.input_schema,
        },
    }


async def run(prompt: str) -> None:
    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SERVER_PATH), "run"],
        cwd=str(ROOT),
    )

    async with Client(server) as mcp_client:
        tools_result = await mcp_client.list_tools()
        ollama_tools = [to_ollama_tool(tool) for tool in tools_result.tools]

        messages = [{"role": "user", "content": prompt}]

        response = ollama.chat(
            model=LOCAL_OLLAMA_MODEL, messages=messages, tools=ollama_tools
        )
        messages.append(response.message)

        while response.message.tool_calls:
            for call in response.message.tool_calls:
                print(
                    f"-> calling tool '{call.function.name}' with {call.function.arguments}"
                )
                result = await mcp_client.call_tool(
                    call.function.name, dict(call.function.arguments)
                )
                messages.append(
                    {
                        "role": "tool",
                        "content": str(result.structured_content),
                        "tool_name": call.function.name,
                    }
                )

            response = ollama.chat(
                model=LOCAL_OLLAMA_MODEL, messages=messages, tools=ollama_tools
            )
            messages.append(response.message)

        print(response.message.content)


if __name__ == "__main__":
    user_prompt = " ".join(sys.argv[1:]) or "What time is it?"
    asyncio.run(run(user_prompt))
