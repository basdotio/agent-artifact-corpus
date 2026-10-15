#!/usr/bin/env python3
"""Simple import test for MCP server dependencies"""

import sys
from pathlib import Path

def test_imports():
    """Test all required imports"""
    print("Testing imports...")
    
    # Test basic dependencies
    try:
        import yaml
        print("✅ yaml imported successfully")
    except ImportError as e:
        print(f"❌ yaml import failed: {e}")
        return False
    
    try:
        import neo4j
        print("✅ neo4j imported successfully")
    except ImportError as e:
        print(f"❌ neo4j import failed: {e}")
        return False
    
    try:
        import pydantic
        print("✅ pydantic imported successfully")
    except ImportError as e:
        print(f"❌ pydantic import failed: {e}")
        return False
    
    try:
        import aiohttp
        print("✅ aiohttp imported successfully")
    except ImportError as e:
        print(f"❌ aiohttp import failed: {e}")
        return False
    
    # Test MCP imports
    try:
        from mcp.server import Server
        print("✅ MCP server imported successfully")
    except ImportError as e:
        print(f"⚠️  MCP server import failed (optional): {e}")
    
    # Test local imports
    try:
        # Add parent src directory to path
        sys.path.append(str(Path(__file__).parent.parent / "src"))
        from models import MCPServer, OperationType, RegistrySource, ServerCategory
        print("✅ models imported successfully")
    except ImportError as e:
        print(f"❌ models import failed: {e}")
        return False
    
    try:
        from mcp_server import ASKGMCPServer, ServerSearchRequest, ServerSearchResult
        print("✅ mcp_server imported successfully")
    except ImportError as e:
        print(f"❌ mcp_server import failed: {e}")
        return False
    
    print("✅ All required imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1) 