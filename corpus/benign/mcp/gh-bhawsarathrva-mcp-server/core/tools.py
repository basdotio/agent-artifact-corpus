import json
from typing import Optional, Literal, List
from mcp.types import CallToolResult, Tool, TextContent
from mcp_client import MCPClient
from anthropic.types import Message, ToolResultBlockParam


class ToolManager:
    @classmethod
    async def get_all_tools(cls, clients: dict[str, MCPClient]) -> list[Tool]:
        """Gets all tools from the provided clients."""
        tools = []
        for client in clients.values():
            tool_models = await client.list_tools()
            tools += [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.inputSchema,
                }
                for t in tool_models
            ]
        return tools

    @classmethod
    async def _find_client_with_tool(
        cls, clients: list[MCPClient], tool_name: str
    ) -> Optional[MCPClient]:
        """Finds the first client that has the specified tool."""
        for client in clients:
            tools = await client.list_tools()
            tool = next((t for t in tools if t.name == tool_name), None)
            if tool:
                return client
        return None

    @classmethod
    def _build_tool_result_part(
        cls,
        tool_use_id: str,
        text: str,
        status: Literal["success"] | Literal["error"],
    ) -> ToolResultBlockParam:
        """Builds a tool result part dictionary."""
        return {
            "tool_use_id": tool_use_id,
            "type": "tool_result",
            "content": text,
            "is_error": status == "error",
        }

    @classmethod
    async def execute_tool_requests(
        cls, clients: dict[str, MCPClient], message
    ) -> List[dict]:
        """Executes a list of tool requests against the provided clients."""
        tool_calls = []

        # Support Ollama ChatResponse
        if hasattr(message, 'message') and getattr(message.message, 'tool_calls', None):
            for tc in message.message.tool_calls:
                tool_calls.append({
                    "name": tc.function.name,
                    "input": tc.function.arguments,
                })
        # Support OpenAI/Groq response
        elif hasattr(message, 'choices') and message.choices[0].message.tool_calls:
            for tc in message.choices[0].message.tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    args = json.loads(args)
                tool_calls.append({
                    "name": tc.function.name,
                    "input": args,
                })
        # Support Anthropic message
        elif hasattr(message, 'content'):
            for block in message.content:
                if getattr(block, 'type', None) == 'tool_use':
                    tool_calls.append({
                        "name": block.name,
                        "input": block.input,
                    })

        tool_result_blocks = []
        for call in tool_calls:
            tool_name = call["name"]
            tool_input = call["input"]

            client = await cls._find_client_with_tool(
                list(clients.values()), tool_name
            )

            if not client:
                tool_result_blocks.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": "Could not find that tool",
                })
                continue

            try:
                tool_output: CallToolResult | None = await client.call_tool(
                    tool_name, tool_input
                )
                items = []
                if tool_output:
                    items = tool_output.content
                content_list = [
                    item.text for item in items if isinstance(item, TextContent)
                ]
                content_json = json.dumps(content_list)
                tool_result_blocks.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": content_json,
                })
            except Exception as e:
                error_message = f"Error executing tool '{tool_name}': {e}"
                print(error_message)
                tool_result_blocks.append({
                    "role": "tool",
                    "name": tool_name,
                    "content": json.dumps({"error": error_message}),
                })
        return tool_result_blocks
