# !/usr/bin/env python3

"""
Simple test to verify the MCP server works by testing the core functionality
"""

import asyncio
from mcp_server import handle_list_tools, handle_call_tool


async def test_server_functions():
    """Test the server handler functions directly"""

    print("=== Testing MCP Server Functions ===")

    # Test list_tools
    print("\n1. Testing list_tools...")
    try:
        tools = await handle_list_tools()
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool.name}: {tool.description}")
    except Exception as e:
        print(f"Error listing tools: {e}")
        return

    # Test call_tool - Official transcript first
    print("\n2. Testing call_tool (official transcript)...")
    try:
        result = await handle_call_tool(
            name="get_youtube_transcript",
            arguments={
                "query": "What is an API? by MuleSoft",
                "force_whisper": False
            }
        )
        print("Tool call successful!")
        print(f"Response type: {type(result)}")
        print(f"Response content preview: {str(result[0].text)[:200]}...")

    except Exception as e:
        print(f"Error calling tool: {e}")

    # Test call_tool - Force Whisper
    print("\n3. Testing call_tool (force whisper)...")
    print("WARNING: This will download audio and use Whisper - may take several minutes!")
    user_input = input("Do you want to test force_whisper? (y/N): ")

    if user_input.lower().startswith('y'):
        try:
            result = await handle_call_tool(
                name="get_youtube_transcript",
                arguments={
                    "query": "What is an API? by MuleSoft",
                    "force_whisper": True
                }
            )
            print("Whisper tool call successful!")
            print(f"Response type: {type(result)}")
            print(f"Response content preview: {str(result[0].text)[:200]}...")

        except Exception as e:
            print(f"Error calling tool with Whisper: {e}")
    else:
        print("Skipping Whisper test.")


if __name__ == "__main__":
    asyncio.run(test_server_functions())