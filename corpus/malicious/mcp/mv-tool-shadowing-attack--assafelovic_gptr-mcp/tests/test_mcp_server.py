#!/usr/bin/env python3
"""
Test script for GPT Researcher MCP Server

This script validates the MCP server functionality including:
- SSE connection establishment
- Session management
- MCP protocol initialization
- Tool discovery and execution
"""

import asyncio
import json
import time
import httpx
import sseclient
from typing import Dict, Any, Optional

class MCPServerTester:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
    
    async def connect_sse(self) -> bool:
        """Connect to SSE endpoint and get session ID"""
        print("🔌 Connecting to SSE endpoint...")
        try:
            response = await self.client.get(f"{self.base_url}/sse")
            if response.status_code == 200:
                # Parse the first event to get session ID
                content = response.text
                lines = content.split('\n')
                for line in lines:
                    if line.startswith('data: /messages/?session_id='):
                        self.session_id = line.split('session_id=')[1]
                        print(f"✅ Connected! Session ID: {self.session_id}")
                        return True
            return False
        except Exception as e:
            print(f"❌ SSE connection failed: {e}")
            return False
    
    def get_session_id_from_sse(self) -> Optional[str]:
        """Get session ID by making a simple request to SSE endpoint"""
        try:
            with httpx.stream("GET", f"{self.base_url}/sse") as response:
                for line in response.iter_lines():
                    if line.startswith('data: /messages/?session_id='):
                        session_id = line.split('session_id=')[1].strip()
                        print(f"✅ Got session ID: {session_id}")
                        return session_id
        except Exception as e:
            print(f"❌ Failed to get session ID: {e}")
            return None
    
    async def send_mcp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send MCP message to the server"""
        if not self.session_id:
            print("❌ No session ID available")
            return {}
        
        url = f"{self.base_url}/messages/?session_id={self.session_id}"
        try:
            response = await self.client.post(
                url,
                json=message,
                headers={"Content-Type": "application/json"}
            )
            
            # SSE transport returns 202 Accepted for valid requests
            if response.status_code in [200, 202]:
                try:
                    return response.json()
                except:
                    return {"status": "accepted", "text": response.text}
            else:
                return {"error": f"HTTP {response.status_code}", "text": response.text}
        except Exception as e:
            return {"error": str(e)}
    
    async def initialize_mcp(self) -> bool:
        """Initialize MCP connection"""
        print("🚀 Initializing MCP connection...")
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        result = await self.send_mcp_message(init_message)
        # SSE transport returns 202 Accepted, which means the message was received
        if "error" not in result or result.get("status") == "accepted":
            print("✅ MCP initialized successfully")
            return True
        else:
            print(f"❌ MCP initialization failed: {result}")
            return False
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools"""
        print("🔧 Listing available tools...")
        list_tools_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        result = await self.send_mcp_message(list_tools_message)
        print(f"📋 Tools result: {result}")
        return result
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool"""
        print(f"⚡ Calling tool: {tool_name}")
        call_tool_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        result = await self.send_mcp_message(call_tool_message)
        print(f"📊 Tool result: {result}")
        return result
    
    async def run_comprehensive_test(self):
        """Run comprehensive test suite"""
        print("=" * 50)
        print("🧪 GPT Researcher MCP Server Test Suite")
        print("=" * 50)
        
        # Step 1: Get session ID
        self.session_id = self.get_session_id_from_sse()
        if not self.session_id:
            print("❌ Failed to get session ID")
            return False
        
        # Step 2: Initialize MCP
        if not await self.initialize_mcp():
            return False
        
        # Step 3: List tools
        await self.list_tools()
        
        # Step 4: Test quick_search tool
        print("\n🔍 Testing quick_search tool...")
        await self.call_tool("quick_search", {"query": "latest AI developments"})
        
        print("\n✅ Test suite completed!")
        return True


async def main():
    print("Starting MCP Server Tests...")
    
    # Check if server is running
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/")
            if response.status_code != 404:  # 404 is expected for root
                print("❌ Server doesn't seem to be running on port 8000")
                return
    except:
        print("❌ Cannot connect to server on port 8000")
        print("💡 Make sure to start the server with: python server.py")
        return
    
    async with MCPServerTester() as tester:
        await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main()) 