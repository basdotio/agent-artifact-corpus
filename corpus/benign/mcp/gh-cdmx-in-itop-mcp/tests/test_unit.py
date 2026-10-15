"""
Unit Tests for iTop MCP Server

These tests can run without a live iTop instance by mocking API responses.
"""

import asyncio
import json
import os
import sys
from unittest.mock import AsyncMock, patch, MagicMock
import pytest

# Add the main module to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import (
    ITopClient,
    _format_support_tickets_output,
    _format_field_value,
    SUPPORT_TICKET_FIELDS
)


class TestITopClient:
    """Unit tests for ITopClient class."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = ITopClient("https://example.com/itop", "user", "pass", "1.4")
        assert client.base_url == "https://example.com/itop"
        assert client.username == "user"
        assert client.password == "pass"
        assert client.version == "1.4"
        assert client.rest_url == "https://example.com/itop/webservices/rest.php"
    
    def test_url_normalization(self):
        """Test URL normalization."""
        client = ITopClient("https://example.com/itop/", "user", "pass")
        assert client.base_url == "https://example.com/itop"
        assert not client.base_url.endswith("/")
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_success(self, mock_client):
        """Test successful API request."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {"code": 0, "message": "OK"}
        mock_response.raise_for_status.return_value = None
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        client = ITopClient("https://example.com/itop", "user", "pass")
        result = await client.make_request({"operation": "list_operations"})
        
        assert result["code"] == 0
        assert result["message"] == "OK"
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_http_error(self, mock_client):
        """Test HTTP error handling."""
        import httpx
        
        mock_client_instance = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        http_error = httpx.HTTPStatusError("404", request=MagicMock(), response=mock_response)
        mock_client_instance.post.side_effect = http_error
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        client = ITopClient("https://example.com/itop", "user", "pass")
        
        with pytest.raises(ValueError, match="HTTP error 404"):
            await client.make_request({"operation": "test"})
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient')
    async def test_make_request_connection_error(self, mock_client):
        """Test connection error handling."""
        import httpx
        
        mock_client_instance = AsyncMock()
        mock_client_instance.post.side_effect = httpx.RequestError("Connection failed")
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        client = ITopClient("https://example.com/itop", "user", "pass")
        
        with pytest.raises(ConnectionError, match="Request failed"):
            await client.make_request({"operation": "test"})


class TestFormattingFunctions:
    """Unit tests for formatting functions."""
    
    def test_format_field_value(self):
        """Test field value formatting."""
        # Test None value
        assert _format_field_value(None) == "None"
        
        # Test regular string
        assert _format_field_value("test") == "test"
        
        # Test HTML removal
        html_value = "<p>This is <strong>bold</strong> text</p>"
        result = _format_field_value(html_value)
        assert "<" not in result
        assert ">" not in result
        assert "This is bold text" in result
        
        # Test newline replacement
        multiline = "Line 1\nLine 2\rLine 3"
        result = _format_field_value(multiline)
        assert "\n" not in result
        assert "\r" not in result
        assert "Line 1 Line 2 Line 3" in result
    
    def test_format_support_tickets_table(self):
        """Test support tickets table formatting."""
        mock_objects = {
            "ticket1": {
                "code": 0,
                "fields": {
                    "ref": "R-000001",
                    "title": "Test ticket 1",
                    "status": "new",
                    "sla_tto_passed": "1",
                    "sla_ttr_passed": "0",
                    "start_date": "2024-01-01",
                    "close_date": ""
                }
            },
            "ticket2": {
                "code": 0,
                "fields": {
                    "ref": "R-000002",
                    "title": "Test ticket 2",
                    "status": "resolved",
                    "sla_tto_passed": "1",
                    "sla_ttr_passed": "1",
                    "start_date": "2024-01-02",
                    "close_date": "2024-01-03"
                }
            }
        }
        
        result = _format_support_tickets_output(mock_objects, "UserRequest", "table", True)
        
        assert "Found 2 UserRequest tickets" in result
        assert "R-000001" in result
        assert "R-000002" in result
        assert "✓" in result  # SLA passed
        assert "✗" in result  # SLA failed
        assert "|" in result  # Table formatting
    
    def test_format_support_tickets_summary(self):
        """Test support tickets summary formatting."""
        mock_objects = {
            "ticket1": {
                "code": 0,
                "fields": {
                    "status": "new",
                    "sla_tto_passed": "1",
                    "sla_ttr_passed": "0"
                }
            },
            "ticket2": {
                "code": 0,
                "fields": {
                    "status": "new",
                    "sla_tto_passed": "0",
                    "sla_ttr_passed": "0"
                }
            },
            "ticket3": {
                "code": 0,
                "fields": {
                    "status": "resolved",
                    "sla_tto_passed": "1",
                    "sla_ttr_passed": "1"
                }
            }
        }
        
        result = _format_support_tickets_output(mock_objects, "UserRequest", "summary", True)
        
        assert "📊 **Summary**" in result
        assert "Total tickets: 3" in result
        assert "SLA breached: 2" in result  # 2 tickets have SLA breaches
        assert "new: 2" in result
        assert "resolved: 1" in result
    
    def test_format_support_tickets_detailed(self):
        """Test support tickets detailed formatting."""
        mock_objects = {
            "ticket1": {
                "code": 0,
                "fields": {
                    "ref": "R-000001",
                    "title": "Test ticket",
                    "status": "new",
                    "sla_tto_passed": "1",
                    "sla_ttr_passed": "0",
                    "start_date": "2024-01-01",
                    "caller_name": "John Doe",
                    "agent_name": "Jane Smith",
                    "org_name": "ACME Corp"
                }
            }
        }
        
        result = _format_support_tickets_output(mock_objects, "UserRequest", "detailed", True)
        
        assert "🎫 **R-000001**" in result
        assert "Title: Test ticket" in result
        assert "Status: new" in result
        assert "SLA TTO: ✓ On Time" in result
        assert "SLA TTR: ✗ Breached" in result
        assert "Caller: John Doe" in result
        assert "Agent: Jane Smith" in result
        assert "Organization: ACME Corp" in result


class TestConfiguration:
    """Test configuration and constants."""
    
    def test_support_ticket_fields_config(self):
        """Test support ticket fields configuration."""
        assert isinstance(SUPPORT_TICKET_FIELDS, dict)
        assert "UserRequest" in SUPPORT_TICKET_FIELDS
        assert "Incident" in SUPPORT_TICKET_FIELDS
        
        # Test UserRequest configuration
        ur_config = SUPPORT_TICKET_FIELDS["UserRequest"]
        assert "default_fields" in ur_config
        assert "priority_fields" in ur_config
        assert "sla_fields" in ur_config
        assert "time_fields" in ur_config
        
        # Check SLA fields are included
        assert "sla_tto_passed" in ur_config["default_fields"]
        assert "sla_ttr_passed" in ur_config["default_fields"]
        
        # Test Incident configuration
        incident_config = SUPPORT_TICKET_FIELDS["Incident"]
        assert "priority" in incident_config["default_fields"]
        assert "impact" in incident_config["default_fields"]
        assert "urgency" in incident_config["default_fields"]


class TestAsyncMocking:
    """Test async function mocking for tools."""
    
    @pytest.mark.asyncio
    @patch('main.get_itop_client')
    async def test_get_support_tickets_mocked(self, mock_get_client):
        """Test get_support_tickets with mocked client."""
        from main import get_support_tickets
        
        # Mock client and response
        mock_client = AsyncMock()
        mock_response = {
            "code": 0,
            "objects": {
                "ticket1": {
                    "code": 0,
                    "fields": {
                        "ref": "R-000001",
                        "title": "Test ticket",
                        "status": "new",
                        "sla_tto_passed": "1",
                        "sla_ttr_passed": "1"
                    }
                }
            }
        }
        mock_client.make_request.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = await get_support_tickets()
        
        assert isinstance(result, str)
        assert "Found 1 UserRequest tickets" in result
        assert "R-000001" in result
        assert "Test ticket" in result
    
    @pytest.mark.asyncio
    @patch('main.get_itop_client')
    async def test_get_support_tickets_error(self, mock_get_client):
        """Test get_support_tickets error handling."""
        from main import get_support_tickets
        
        # Mock client to return error
        mock_client = AsyncMock()
        mock_response = {
            "code": 1,
            "message": "Authentication failed"
        }
        mock_client.make_request.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = await get_support_tickets()
        
        assert "Error: Authentication failed" in result
    
    @pytest.mark.asyncio
    @patch('main.get_itop_client')
    async def test_get_support_tickets_no_results(self, mock_get_client):
        """Test get_support_tickets with no results."""
        from main import get_support_tickets
        
        # Mock client to return empty results
        mock_client = AsyncMock()
        mock_response = {
            "code": 0,
            "objects": {}
        }
        mock_client.make_request.return_value = mock_response
        mock_get_client.return_value = mock_client
        
        result = await get_support_tickets(status_filter="nonexistent")
        
        assert "No UserRequest tickets found with status 'nonexistent'" in result


def run_unit_tests():
    """Run unit tests."""
    print("🧪 Running unit tests...")
    
    pytest_args = [
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ]
    
    exit_code = pytest.main(pytest_args)
    
    if exit_code == 0:
        print("✅ All unit tests passed!")
    else:
        print("❌ Some unit tests failed. Check output above.")
        sys.exit(exit_code)


if __name__ == "__main__":
    run_unit_tests()
