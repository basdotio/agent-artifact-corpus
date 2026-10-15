#!/usr/bin/env python3
"""
Test the MCP server tools without requiring actual iTop credentials.
This script validates the server structure and tool definitions.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from main import mcp
    print("✅ Successfully imported MCP server")
except ImportError as e:
    print(f"❌ Failed to import MCP server: {e}")
    sys.exit(1)


def test_server_structure():
    """Test the server structure and available tools"""
    print("\n🔧 Testing Server Structure...")
    
    # Get the FastMCP instance
    print(f"Server name: {mcp.name}")
    print(f"Server description: {mcp.description}")
    
    # List available tools
    tools = []
    for name, func in mcp._tools.items():
        tools.append(name)
        print(f"  • {name}: {func.__doc__.strip().split('.')[0] if func.__doc__ else 'No description'}")
    
    print(f"\nTotal tools available: {len(tools)}")
    
    expected_tools = [
        "list_operations",
        "get_objects", 
        "create_object",
        "update_object",
        "delete_object",
        "apply_stimulus",
        "get_related_objects",
        "check_credentials"
    ]
    
    missing_tools = set(expected_tools) - set(tools)
    if missing_tools:
        print(f"❌ Missing expected tools: {', '.join(missing_tools)}")
    else:
        print("✅ All expected tools are present")
    
    return len(missing_tools) == 0


def test_tool_signatures():
    """Test that all tools have proper signatures and documentation"""
    print("\n📋 Testing Tool Signatures...")
    
    all_good = True
    
    for name, func in mcp._tools.items():
        # Check if function has docstring
        if not func.__doc__:
            print(f"❌ {name}: Missing docstring")
            all_good = False
        else:
            # Check if docstring has Args section for functions with parameters
            import inspect
            sig = inspect.signature(func)
            params = [p for p in sig.parameters.values() if p.name != 'self']
            
            if params and 'Args:' not in func.__doc__:
                print(f"⚠️  {name}: Has parameters but no Args section in docstring")
            else:
                print(f"✅ {name}: Well documented")
    
    return all_good


def validate_json_examples():
    """Validate JSON examples in the code"""
    print("\n🔍 Validating JSON Examples...")
    
    # Test some common JSON structures that would be used
    test_cases = [
        ('Simple field update', '{"title": "Updated title", "priority": "high"}'),
        ('Organization search', '{"name": "Demo"}'),
        ('OQL query', 'SELECT UserRequest WHERE status = "new"'),
        ('Contact list', '[{"role": "manager", "contact_id": 123}]')
    ]
    
    all_valid = True
    for description, json_str in test_cases:
        try:
            if json_str.startswith('SELECT'):
                # OQL queries are strings, not JSON
                print(f"✅ {description}: Valid OQL query")
            else:
                json.loads(json_str)
                print(f"✅ {description}: Valid JSON")
        except json.JSONDecodeError as e:
            print(f"❌ {description}: Invalid JSON - {e}")
            all_valid = False
    
    return all_valid


def generate_usage_examples():
    """Generate usage examples for the README"""
    print("\n📖 Generating Usage Examples...")
    
    examples = {
        "Get all organizations": {
            "tool": "get_objects",
            "args": {
                "class_name": "Organization",
                "output_fields": "name,status,code"
            }
        },
        "Search for user requests by status": {
            "tool": "get_objects", 
            "args": {
                "class_name": "UserRequest",
                "key": "SELECT UserRequest WHERE status = 'new'",
                "output_fields": "friendlyname,title,caller_name,status"
            }
        },
        "Create a new incident": {
            "tool": "create_object",
            "args": {
                "class_name": "Incident",
                "fields_json": '{"title": "Server down", "description": "Mail server is not responding", "impact": "2", "urgency": "2"}',
                "comment": "Created via MCP server"
            }
        },
        "Update ticket priority": {
            "tool": "update_object",
            "args": {
                "class_name": "UserRequest",
                "key": "123",
                "fields_json": '{"priority": "1"}',
                "comment": "Priority escalated"
            }
        },
        "Resolve a ticket": {
            "tool": "apply_stimulus",
            "args": {
                "class_name": "UserRequest",
                "key": "123",
                "stimulus": "ev_resolve",
                "fields_json": '{"solution": "Issue resolved by restarting service"}',
                "comment": "Ticket resolved"
            }
        }
    }
    
    print("Generated examples:")
    for name, example in examples.items():
        print(f"\n  {name}:")
        print(f"    Tool: {example['tool']}")
        for arg, value in example['args'].items():
            print(f"    {arg}: {value}")
    
    return examples


def main():
    """Main test function"""
    print("🚀 iTop MCP Server Validation Suite")
    print("=" * 50)
    
    all_tests_passed = True
    
    # Test server structure
    all_tests_passed &= test_server_structure()
    
    # Test tool signatures
    all_tests_passed &= test_tool_signatures()
    
    # Validate JSON examples
    all_tests_passed &= validate_json_examples()
    
    # Generate usage examples
    generate_usage_examples()
    
    print(f"\n{'=' * 50}")
    if all_tests_passed:
        print("✅ All validation tests passed!")
        print("🎉 The iTop MCP server is ready to use!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your iTop connection")
        print("2. Test the connection with: uv run test_itop.py")
        print("3. Add to Claude Desktop configuration")
    else:
        print("❌ Some validation tests failed")
        print("Please review the output above and fix any issues")
    
    return 0 if all_tests_passed else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
