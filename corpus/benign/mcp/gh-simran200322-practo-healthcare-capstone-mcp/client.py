"""MCP Client invoking check_appointment_status tool across standard protocol."""
import sys
import asyncio
import json
from pathlib import Path

# Add directory of this script to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))
# Add project root to sys.path
sys.path.insert(1, str(Path(__file__).resolve().parent.parent))

from server import mcp as server_instance
from fastmcp import Client


async def run_mcp_client(target_record_ids=None):
    """Connect to MCP server via FastMCP Client and invoke tool for >= 2 records."""
    if target_record_ids is None:
        target_record_ids = ["APP-0001", "APP-0002", "APP-0005"]

    print("=" * 75)
    print("PRACTO HEALTHCARE CAPSTONE - FASTMCP CLIENT DEMONSTRATION (Task 14)")
    print("=" * 75)
    print(f"Connecting to FastMCP Server instance: '{server_instance.name}'...")
    print(f"Target Record IDs to query: {target_record_ids}")
    print("-" * 75)

    results = []

    # Using FastMCP Client protocol session
    async with Client(server_instance) as client:
        # List available tools to verify protocol discovery
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        print(f"Discovered MCP Tools on Server: {tool_names}")
        print("-" * 75)

        for record_id in target_record_ids:
            print(f"\n[MCP Protocol Call] Tool: 'check_appointment_status' | Argument: record_id='{record_id}'")
            # Invoke tool over standard MCP protocol
            mcp_response = await client.call_tool("check_appointment_status", {"record_id": record_id})
            
            # Extract content text from MCP response object
            response_payload = mcp_response.content if hasattr(mcp_response, "content") else mcp_response
            print(f"Standardized MCP Response Object:")
            print(f"  Type   : {type(mcp_response).__name__}")
            print(f"  Content: {response_payload}")

            results.append({
                "record_id": record_id,
                "response": str(response_payload)
            })

    print("\n" + "=" * 75)
    print("SUCCESS: FastMCP Tool successfully executed for multiple record IDs!")
    print("=" * 75)
    return results


def main():
    asyncio.run(run_mcp_client())


if __name__ == "__main__":
    main()
