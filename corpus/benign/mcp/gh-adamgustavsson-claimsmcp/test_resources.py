#!/usr/bin/env python3
"""Test script to verify the resources implementation."""

import asyncio
import json
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

async def test_resources():
    """Test the claim extraction resources."""
    
    # Server parameters
    server_params = StdioServerParameters(
        command="python3",
        args=[str(Path(__file__).parent / "claimify_server.py")]
    )
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()
            
            print("=== Testing Claim Extraction Tool ===")
            
            # Call the extract_claims tool
            test_text = "Apple Inc. was founded in 1976 by Steve Jobs. The company released the iPhone in 2007."
            result = await session.call_tool(
                "extract_claims",
                arguments={
                    "text_to_process": test_text,
                    "question": "What is the history of Apple?"
                }
            )
            
            print(f"\nExtracted claims:")
            for content in result.content:
                if hasattr(content, 'text'):
                    claims = json.loads(content.text)
                    for claim in claims:
                        print(f"  - {claim}")
            
            # Wait a moment for the resource to be stored
            await asyncio.sleep(0.5)
            
            print("\n=== Testing Resources ===")
            
            # List resources
            resources = await session.list_resources()
            print(f"\nAvailable resources: {len(resources.resources)}")
            for resource in resources.resources:
                print(f"  - {resource.name}: {resource.description}")
                print(f"    URI: {resource.uri}")
            
            # Read the first resource if available
            if resources.resources:
                first_resource = resources.resources[0]
                print(f"\n=== Reading resource: {first_resource.uri} ===")
                
                resource_content = await session.read_resource(first_resource.uri)
                for content in resource_content.contents:
                    if hasattr(content, 'text'):
                        data = json.loads(content.text)
                        print(json.dumps(data, indent=2))

if __name__ == "__main__":
    asyncio.run(test_resources())
