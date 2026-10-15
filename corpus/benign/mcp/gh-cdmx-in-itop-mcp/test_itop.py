#!/usr/bin/env python3
"""
Example usage script for the iTop MCP Server
This script demonstrates how to interact with the server programmatically.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from main import get_itop_client


async def test_itop_connection():
    """Test basic connection to iTop"""
    print("🔧 Testing iTop Connection...")
    
    try:
        client = get_itop_client()
        
        # Test credentials
        operation_data = {
            "operation": "core/check_credentials",
            "user": client.username,
            "password": client.password
        }
        
        result = await client._make_request(operation_data)
        
        if result.get("code") == 0 and result.get("authorized"):
            print("✅ Connection successful!")
            print(f"   Connected to: {client.base_url}")
            print(f"   User: {client.username}")
            print(f"   API Version: {client.version}")
            return True
        else:
            print("❌ Authentication failed")
            print(f"   Error: {result.get('message', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False


async def list_available_operations():
    """List all available operations"""
    print("\n📋 Available Operations...")
    
    try:
        client = get_itop_client()
        operation_data = {"operation": "list_operations"}
        result = await client._make_request(operation_data)
        
        if result.get("code") == 0:
            operations = result.get("operations", [])
            print(f"Found {len(operations)} operations:")
            for op in operations:
                verb = op.get("verb", "Unknown")
                description = op.get("description", "No description")
                print(f"  • {verb}: {description}")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error listing operations: {e}")


async def test_user_requests():
    """Test getting user requests"""
    print("\n🎫 Testing User Requests...")
    
    try:
        client = get_itop_client()
        
        # Get first 5 user requests
        operation_data = {
            "operation": "core/get",
            "class": "UserRequest",
            "key": "SELECT UserRequest",
            "output_fields": "id,friendlyname,title,status,caller_name",
            "limit": 5
        }
        
        result = await client._make_request(operation_data)
        
        if result.get("code") == 0:
            objects = result.get("objects", {})
            print(f"Found {len(objects)} user requests:")
            
            for obj_key, obj_data in objects.items():
                if obj_data.get("code") == 0:
                    fields = obj_data.get("fields", {})
                    title = fields.get("title", "No title")
                    status = fields.get("status", "Unknown")
                    caller = fields.get("caller_name", "Unknown")
                    print(f"  • {obj_key}: {title} (Status: {status}, Caller: {caller})")
                else:
                    print(f"  • Error with {obj_key}: {obj_data.get('message', 'Unknown error')}")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error getting user requests: {e}")


async def test_organizations():
    """Test getting organizations"""
    print("\n🏢 Testing Organizations...")
    
    try:
        client = get_itop_client()
        
        operation_data = {
            "operation": "core/get",
            "class": "Organization",
            "output_fields": "id,name,status",
            "limit": 10
        }
        
        result = await client._make_request(operation_data)
        
        if result.get("code") == 0:
            objects = result.get("objects", {})
            print(f"Found {len(objects)} organizations:")
            
            for obj_key, obj_data in objects.items():
                if obj_data.get("code") == 0:
                    fields = obj_data.get("fields", {})
                    name = fields.get("name", "No name")
                    status = fields.get("status", "Unknown")
                    print(f"  • {obj_key}: {name} (Status: {status})")
        else:
            print(f"❌ Error: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ Error getting organizations: {e}")


async def main():
    """Main test function"""
    print("🚀 iTop MCP Server Test Suite")
    print("=" * 40)
    
    # Check environment variables
    required_vars = ["ITOP_BASE_URL", "ITOP_USER", "ITOP_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease set these variables or copy .env.example to .env and configure it.")
        return
    
    # Run tests
    connection_ok = await test_itop_connection()
    
    if connection_ok:
        await list_available_operations()
        await test_user_requests()
        await test_organizations()
        print("\n✅ All tests completed!")
    else:
        print("\n❌ Connection failed - skipping other tests")


if __name__ == "__main__":
    asyncio.run(main())
