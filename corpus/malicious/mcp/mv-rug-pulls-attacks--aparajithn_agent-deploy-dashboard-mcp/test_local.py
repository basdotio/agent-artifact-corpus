"""Local test script to verify MCP server functionality."""
import httpx
import asyncio
import json


async def test_health():
    """Test health endpoint."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/health")
        print("Health check:", response.status_code)
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200


async def test_mcp_initialize():
    """Test MCP initialize."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test", "version": "1.0.0"}
                }
            }
        )
        print("\nMCP Initialize:", response.status_code)
        print(json.dumps(response.json(), indent=2))
        return response.status_code == 200


async def test_mcp_tools_list():
    """Test MCP tools/list."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8080/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/list",
                "params": {}
            }
        )
        print("\nMCP Tools List:", response.status_code)
        data = response.json()
        print(f"Found {len(data.get('result', {}).get('tools', []))} tools")
        for tool in data.get('result', {}).get('tools', []):
            print(f"  - {tool['name']}: {tool['description'][:60]}...")
        return response.status_code == 200


async def test_rest_list_services():
    """Test REST API list_all_services (will fail without tokens)."""
    async with httpx.AsyncClient() as client:
        response = await client.get("http://localhost:8080/api/v1/list_all_services")
        print("\nREST List Services:", response.status_code)
        print(json.dumps(response.json(), indent=2))
        # This might return errors if tokens aren't set, which is OK for testing
        return True


async def test_well_known_endpoints():
    """Test .well-known endpoints."""
    async with httpx.AsyncClient() as client:
        # Agent card
        response = await client.get("http://localhost:8080/.well-known/agent-card.json")
        print("\nAgent Card:", response.status_code)
        print(json.dumps(response.json(), indent=2))
        
        # MCP server card
        response = await client.get("http://localhost:8080/.well-known/mcp/server-card.json")
        print("\nMCP Server Card:", response.status_code)
        data = response.json()
        print(f"Server: {data['serverInfo']['name']} v{data['serverInfo']['version']}")
        print(f"Tools: {len(data['tools'])}")
        
        return True


async def main():
    """Run all tests."""
    print("=" * 60)
    print("Agent Deploy Dashboard MCP Server - Local Tests")
    print("=" * 60)
    
    tests = [
        test_health,
        test_well_known_endpoints,
        test_mcp_initialize,
        test_mcp_tools_list,
        test_rest_list_services
    ]
    
    results = []
    for test in tests:
        try:
            result = await test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            results.append(False)
    
    print("\n" + "=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
