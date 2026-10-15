#!/usr/bin/env python3
"""Basic tests for MCP server functionality"""

import pytest
from pathlib import Path
import sys

# Add parent src directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

def test_imports():
    """Test that basic imports work"""
    try:
        from models import MCPServer, OperationType, RegistrySource, ServerCategory
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import models: {e}")

def test_enum_values():
    """Test that enum values are correct"""
    from models import ServerCategory, OperationType, RegistrySource
    
    # Test ServerCategory
    assert ServerCategory.DATABASE == "database"
    assert ServerCategory.FILE_SYSTEM == "file_system"
    assert ServerCategory.API_INTEGRATION == "api_integration"
    
    # Test OperationType
    assert OperationType.READ == "read"
    assert OperationType.WRITE == "write"
    assert OperationType.QUERY == "query"
    
    # Test RegistrySource
    assert RegistrySource.GITHUB == "github"
    assert RegistrySource.MCP_SO == "mcp.so"

def test_mcp_server_model():
    """Test MCPServer model creation"""
    from models import MCPServer, ServerCategory, OperationType, RegistrySource
    
    server = MCPServer(
        id="test-1",
        name="Test Server",
        description="A test server",
        categories=[ServerCategory.DATABASE],
        operations=[OperationType.READ, OperationType.WRITE],
        registry_source=RegistrySource.GITHUB,
    )
    
    assert server.id == "test-1"
    assert server.name == "Test Server"
    assert server.description == "A test server"
    assert ServerCategory.DATABASE in server.categories
    assert OperationType.READ in server.operations
    assert OperationType.WRITE in server.operations
    assert server.registry_source == RegistrySource.GITHUB

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 