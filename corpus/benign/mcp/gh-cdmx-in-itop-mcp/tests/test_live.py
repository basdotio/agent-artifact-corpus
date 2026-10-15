"""
Live Test Cases for iTop MCP Server

This module provides comprehensive test cases for the iTop MCP server.
Tests are designed to run against a real iTop instance when credentials are provided.
"""

import asyncio
import json
import os
import sys
from typing import Dict, Any, Optional
import pytest

# Add the main module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    get_itop_client,
    get_support_tickets,
    get_objects,
    list_operations,
    check_credentials,
    create_user_request,
    get_organizations,
    ITopClient,
    SUPPORT_TICKET_FIELDS
)


class TestITopMCP:
    """Main test class for iTop MCP functionality."""
    
    @pytest.fixture(scope="session")
    def itop_client(self):
        """Get iTop client for testing."""
        try:
            return get_itop_client()
        except ValueError as e:
            pytest.skip(f"iTop credentials not configured: {e}")
    
    @pytest.fixture(scope="session")
    def event_loop(self):
        """Create event loop for async tests."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()
    
    @pytest.mark.asyncio
    async def test_credentials_check(self, itop_client):
        """Test credential validation."""
        result = await check_credentials()
        assert "✅" in result or "valid" in result.lower()
        assert "error" not in result.lower()
    
    @pytest.mark.asyncio
    async def test_list_operations(self, itop_client):
        """Test listing iTop operations."""
        result = await list_operations()
        assert "Available iTop REST API operations" in result
        assert "core/get" in result or "get" in result
        assert "Error" not in result
    
    @pytest.mark.asyncio
    async def test_get_support_tickets_basic(self, itop_client):
        """Test basic support ticket retrieval."""
        result = await get_support_tickets()
        assert isinstance(result, str)
        assert "UserRequest" in result
        # Should not contain error messages
        assert "Error getting support tickets" not in result
    
    @pytest.mark.asyncio
    async def test_get_support_tickets_with_filters(self, itop_client):
        """Test support ticket retrieval with filters."""
        result = await get_support_tickets(
            ticket_type="UserRequest",
            status_filter="new",
            include_sla=True,
            limit=10,
            format_output="table"
        )
        assert isinstance(result, str)
        assert "UserRequest" in result
        assert "SLA" in result
    
    @pytest.mark.asyncio
    async def test_get_support_tickets_summary(self, itop_client):
        """Test support ticket summary format."""
        result = await get_support_tickets(
            format_output="summary",
            limit=5
        )
        assert isinstance(result, str)
        assert "Summary" in result
        assert "Total tickets" in result
    
    @pytest.mark.asyncio
    async def test_get_objects_basic(self, itop_client):
        """Test basic object retrieval."""
        result = await get_objects(
            class_name="UserRequest",
            limit=5
        )
        assert isinstance(result, str)
        assert "UserRequest" in result
        assert "Error getting objects" not in result
    
    @pytest.mark.asyncio
    async def test_get_objects_with_fields(self, itop_client):
        """Test object retrieval with specific fields."""
        result = await get_objects(
            class_name="UserRequest",
            output_fields="ref,title,status",
            limit=3,
            format_output="table"
        )
        assert isinstance(result, str)
        assert "ref" in result.lower() or "title" in result.lower()
    
    @pytest.mark.asyncio
    async def test_get_organizations(self, itop_client):
        """Test organization retrieval."""
        result = await get_organizations(limit=5)
        assert isinstance(result, str)
        assert "Organization" in result
        assert "Error getting organizations" not in result
    
    @pytest.mark.asyncio
    async def test_support_ticket_fields_configuration(self):
        """Test support ticket fields configuration."""
        assert "UserRequest" in SUPPORT_TICKET_FIELDS
        assert "Incident" in SUPPORT_TICKET_FIELDS
        
        ur_config = SUPPORT_TICKET_FIELDS["UserRequest"]
        assert "default_fields" in ur_config
        assert "sla_tto_passed" in ur_config["default_fields"]
        assert "sla_ttr_passed" in ur_config["default_fields"]
    
    @pytest.mark.asyncio
    async def test_client_initialization(self):
        """Test client initialization with environment variables."""
        # Test with missing credentials
        old_env = {}
        for key in ["ITOP_BASE_URL", "ITOP_USER", "ITOP_PASSWORD"]:
            old_env[key] = os.environ.get(key)
            if key in os.environ:
                del os.environ[key]
        
        try:
            with pytest.raises(ValueError, match="Missing required environment variables"):
                get_itop_client()
        finally:
            # Restore environment
            for key, value in old_env.items():
                if value is not None:
                    os.environ[key] = value
    
    @pytest.mark.asyncio
    async def test_error_handling(self, itop_client):
        """Test error handling for invalid requests."""
        # Test with invalid class name
        result = await get_objects(class_name="InvalidClass", limit=1)
        assert isinstance(result, str)
        # Should handle the error gracefully
        assert "Error" in result or "No InvalidClass objects found" in result
    
    @pytest.mark.asyncio
    async def test_performance_limits(self, itop_client):
        """Test performance with limit constraints."""
        # Test with large limit (should be capped)
        result = await get_objects(
            class_name="UserRequest",
            limit=1000  # Should be capped at 100
        )
        assert isinstance(result, str)
        # Should not fail due to excessive limit
        assert "Error getting objects" not in result


class TestITopClientDirect:
    """Direct tests for ITopClient class."""
    
    def test_client_url_normalization(self):
        """Test URL normalization in client."""
        # Test trailing slash removal
        client = ITopClient("https://example.com/itop/", "user", "pass")
        assert client.base_url == "https://example.com/itop"
        assert client.rest_url == "https://example.com/itop/webservices/rest.php"
    
    def test_client_properties(self):
        """Test client property initialization."""
        client = ITopClient("https://example.com/itop", "testuser", "testpass", "1.5")
        assert client.username == "testuser"
        assert client.password == "testpass"
        assert client.version == "1.5"


class TestIntegrationScenarios:
    """Integration test scenarios for real-world usage."""
    
    @pytest.mark.asyncio
    async def test_ticket_lifecycle_simulation(self, itop_client):
        """Test simulating a ticket lifecycle."""
        # 1. Get initial ticket count
        initial_result = await get_support_tickets(
            status_filter="new",
            format_output="summary",
            limit=1
        )
        assert isinstance(initial_result, str)
        
        # 2. Get organizations (for potential ticket creation)
        org_result = await get_organizations(limit=3)
        assert isinstance(org_result, str)
        
        # 3. Check various ticket statuses
        for status in ["new", "assigned", "resolved"]:
            status_result = await get_support_tickets(
                status_filter=status,
                format_output="summary",
                limit=5
            )
            assert isinstance(status_result, str)
            assert "Summary" in status_result
    
    @pytest.mark.asyncio
    async def test_comprehensive_reporting(self, itop_client):
        """Test comprehensive reporting functionality."""
        # Test different output formats
        formats = ["detailed", "summary", "table"]
        
        for format_type in formats:
            result = await get_support_tickets(
                format_output=format_type,
                limit=3
            )
            assert isinstance(result, str)
            assert len(result) > 0
            
            if format_type == "summary":
                assert "Summary" in result
            elif format_type == "table":
                assert "|" in result  # Table formatting
    
    @pytest.mark.asyncio
    async def test_sla_monitoring(self, itop_client):
        """Test SLA monitoring capabilities."""
        result = await get_support_tickets(
            include_sla=True,
            format_output="detailed",
            limit=10
        )
        assert isinstance(result, str)
        assert "SLA" in result
        # Should include SLA status indicators
        assert "✓" in result or "✗" in result or "On Time" in result or "Breached" in result


def run_live_tests():
    """Run live tests with proper environment setup."""
    # Check if we have the required environment variables
    required_vars = ["ITOP_BASE_URL", "ITOP_USER", "ITOP_PASSWORD"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    
    if missing_vars:
        print(f"⚠️  Missing environment variables: {', '.join(missing_vars)}")
        print("Live tests will be skipped. Set these variables to run against a real iTop instance.")
        return
    
    print("🚀 Running live tests against iTop instance...")
    print(f"📍 iTop URL: {os.environ.get('ITOP_BASE_URL')}")
    print(f"👤 User: {os.environ.get('ITOP_USER')}")
    
    # Run pytest with verbose output
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto",
        "-x"  # Stop on first failure
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("✅ All live tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")
        sys.exit(exit_code)


if __name__ == "__main__":
    # Run live tests when executed directly
    run_live_tests()
