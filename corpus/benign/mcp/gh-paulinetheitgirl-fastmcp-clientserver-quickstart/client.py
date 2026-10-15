# python client.py
import os
import asyncio
import logging
import re
from dotenv import load_dotenv
from fastmcp import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
load_dotenv(override=False)
MCP_SERVER_HOST = os.getenv("MCP_SERVER_HOST")
MCP_SERVER_PORT = os.getenv("MCP_SERVER_PORT")
mcp_client = Client(f"http://{MCP_SERVER_HOST}:{MCP_SERVER_PORT}/mcp", cache=True)

async def call_tool(tool_name: str):
    async with mcp_client:
        result = await mcp_client.call_tool(tool_name)
        print(result.data)

async def main():
    tool_names = set()
    async with mcp_client:
        all_tools = await mcp_client.list_tools()
        print("Available tools")
        for tool in all_tools:
            tool_names.add(tool.name)
            print(f"{tool.name}: {tool.description}")
            logger.debug(tool.input_schema)

        selected_tool = ""
        while (not selected_tool in tool_names):
            # Simple guardrail. See https://www.digitalocean.com/resources/articles/what-are-llm-guardrails
            # Rule-based filtering: List of blocked words/phrases
            blocked_patterns = [r"ignore all previous instructions", r"bypass security"]
            # Apply regex checks to detect harmful queries
            for pattern in blocked_patterns:
                if re.search(pattern, selected_tool, re.IGNORECASE):
                    raise ValueError("Blocked: Your input violates policy.")

            if (selected_tool or "").lower() == "exit":
                return # using "break" would make the flow go to the call_tool() below
            else:
                selected_tool = input("Call which tool? (Type exit to end) ")

        await call_tool(selected_tool)

asyncio.run(main())