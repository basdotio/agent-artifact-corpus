#!/usr/bin/env python3
"""Tests for the ASKG MCP Server

This module contains tests to verify the MCP server functionality.
"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent src directory to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

# Import from local module
from mcp_server import ASKGMCPServer, ServerSearchRequest, ServerSearchResult

from models import MCPServer, OperationType, RegistrySource, ServerCategory

def get_config_path():
    """Get the path to the config file"""
    config_path = Path(__file__).parent.parent / ".config.yaml"
    if not config_path.exists():
        # Try example config
        example_path = Path(__file__).parent.parent / ".config.example.yaml"
        if example_path.exists():
            return str(example_path)
    return str(config_path)


class TestASKGMCPServer:
    """Test cases for the ASKG MCP Server"""

    @pytest.fixture
    def mock_config(self):
        """Mock configuration"""
        return {
            "neo4j": {
                "local": {
                    "uri": "bolt://localhost:7687",
                    "user": "neo4j",
                    "password": "password",
                },
            },
        }

    @pytest.fixture
    def mock_neo4j_driver(self):
        """Mock Neo4j driver"""
        mock_driver = Mock()
        mock_session = Mock()
        mock_result = Mock()

        # Mock session context manager
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)

        # Mock driver session
        mock_driver.session.return_value = mock_session

        # Mock the test connection
        mock_session.run.return_value = Mock()

        return mock_driver, mock_session, mock_result

    @pytest.fixture
    def sample_server_data(self):
        """Sample server data from Neo4j"""
        return {
            "s": {
                "id": "test-server-1",
                "name": "Test Database Server",
                "description": "A test database server for SQL operations",
                "version": "1.0.0",
                "author": "Test Author",
                "license": "MIT",
                "homepage": "https://example.com",
                "repository": "https://github.com/test/db-server",
                "implementation_language": "Python",
                "installation_command": "pip install test-db-server",
                "categories": ["database"],
                "operations": ["read", "write", "query"],
                "data_types": ["sql", "json"],
                "registry_source": "github",
                "source_url": "https://github.com/test/db-server",
                "last_updated": "2024-01-01T00:00:00Z",
                "popularity_score": 85,
                "download_count": 1000,
            },
            "total_score": 7.5,
        }

    @patch("mcp_server.yaml.safe_load")
    @patch("mcp_server.GraphDatabase.driver")
    def test_init_success(self, mock_driver, mock_yaml_load, mock_config):
        """Test successful initialization"""
        mock_yaml_load.return_value = mock_config
        mock_driver_instance = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.run.return_value = Mock()
        mock_driver_instance.session.return_value = mock_session
        mock_driver.return_value = mock_driver_instance

        with ASKGMCPServer(get_config_path(), "local") as server:
            assert server.config == mock_config
            assert server.instance == "local"
            assert server.driver is not None

    @patch("mcp_server.yaml.safe_load")
    def test_init_config_file_not_found(self, mock_yaml_load):
        """Test initialization with missing config file"""
        mock_yaml_load.side_effect = FileNotFoundError("Config file not found")

        with pytest.raises(FileNotFoundError):
            ASKGMCPServer(get_config_path(), "local")

    @patch("mcp_server.yaml.safe_load")
    @patch("mcp_server.GraphDatabase.driver")
    def test_init_neo4j_connection_failure(self, mock_driver, mock_yaml_load, mock_config):
        """Test initialization with Neo4j connection failure"""
        mock_yaml_load.return_value = mock_config
        mock_driver_instance = Mock()
        mock_session = Mock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=None)
        mock_session.run.side_effect = Exception("Connection failed")
        mock_driver_instance.session.return_value = mock_session
        mock_driver.return_value = mock_driver_instance

        with pytest.raises(Exception, match="Connection failed"):
            ASKGMCPServer(get_config_path(), "local")

    def test_extract_search_terms_database(self):
        """Test search term extraction for database queries"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            terms = server._extract_search_terms("Find database servers for SQL operations")

            assert "database" in terms["categories"]
            assert "query" in terms["operations"]
            # Check for case-insensitive match
            assert any("sql" in keyword.lower() for keyword in terms["keywords"])

    def test_extract_search_terms_file_system(self):
        """Test search term extraction for file system queries"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            terms = server._extract_search_terms("Show me file system servers for reading and writing files")

            assert "file_system" in terms["categories"]
            assert "read" in terms["operations"]
            # The prompt contains "writing" which should match "write"
            assert "write" in terms["operations"]

    def test_extract_search_terms_api_integration(self):
        """Test search term extraction for API integration queries"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            terms = server._extract_search_terms("I need API integration servers for REST APIs")

            assert "api_integration" in terms["categories"]
            # Check for case-insensitive match
            assert any("rest" in keyword.lower() for keyword in terms["keywords"])

    def test_build_search_query(self):
        """Test Cypher query building"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            search_terms = {
                "categories": ["database"],
                "operations": ["read", "write"],
                "keywords": ["sql", "database"],
                "original_prompt": "Find database servers",
            }

            cypher, params = server._build_search_query(search_terms, 10, 0.5)

            assert "MATCH (s:Server)" in cypher
            assert "text_score" in cypher
            assert "category_score" in cypher
            assert "operation_score" in cypher
            assert params["prompt"] == "Find database servers"
            assert params["categories"] == ["database"]
            assert params["operations"] == ["read", "write"]
            assert params["limit"] == 10
            assert params["min_confidence"] == 0.5

    def test_convert_to_mcp_server_success(self, sample_server_data):
        """Test successful conversion of Neo4j record to MCPServer"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            mcp_server = server._convert_to_mcp_server(sample_server_data)

            assert mcp_server is not None
            assert mcp_server.id == "test-server-1"
            assert mcp_server.name == "Test Database Server"
            assert mcp_server.description == "A test database server for SQL operations"
            assert ServerCategory.DATABASE in mcp_server.categories
            assert OperationType.READ in mcp_server.operations
            assert OperationType.WRITE in mcp_server.operations
            assert OperationType.QUERY in mcp_server.operations
            assert mcp_server.raw_metadata["search_score"] == 7.5

    def test_convert_to_mcp_server_invalid_data(self):
        """Test conversion with invalid data"""
        with patch("mcp_server.yaml.safe_load"), patch("mcp_server.GraphDatabase.driver"):
            server = ASKGMCPServer(get_config_path(), "local")

            # Test with missing required fields
            invalid_data = {"s": {"name": "Test"}}  # Missing id

            mcp_server = server._convert_to_mcp_server(invalid_data)

            assert mcp_server is not None
            assert mcp_server.id == "unknown"  # Should use default
            assert mcp_server.name == "Test"

    @pytest.mark.asyncio
    async def test_search_servers_success(self, mock_config, mock_neo4j_driver, sample_server_data):
        """Test successful server search"""
        mock_driver, mock_session, mock_result = mock_neo4j_driver

        with patch("mcp_server.yaml.safe_load", return_value=mock_config), \
             patch("mcp_server.GraphDatabase.driver", return_value=mock_driver):

            # Mock the search result
            mock_session.run.return_value = [sample_server_data]

            server = ASKGMCPServer("../.config.yaml", "local")

            request = ServerSearchRequest(
                prompt="Find database servers",
                limit=5,
                min_confidence=0.5,
            )

            result = await server.search_servers(request)

            assert isinstance(result, ServerSearchResult)
            assert result.total_found == 1
            assert len(result.servers) == 1
            assert result.servers[0].name == "Test Database Server"
            assert "database" in result.search_metadata["search_terms"]["categories"]

    @pytest.mark.asyncio
    async def test_search_servers_no_results(self, mock_config, mock_neo4j_driver):
        """Test server search with no results"""
        mock_driver, mock_session, mock_result = mock_neo4j_driver

        with patch("mcp_server.yaml.safe_load", return_value=mock_config), \
             patch("mcp_server.GraphDatabase.driver", return_value=mock_driver):

            # Mock empty search result
            mock_session.run.return_value = []

            server = ASKGMCPServer(get_config_path(), "local")

            request = ServerSearchRequest(
                prompt="Find nonexistent servers",
                limit=5,
                min_confidence=0.5,
            )

            result = await server.search_servers(request)

            assert isinstance(result, ServerSearchResult)
            assert result.total_found == 0
            assert len(result.servers) == 0

    @pytest.mark.asyncio
    async def test_search_servers_exception(self, mock_config, mock_neo4j_driver):
        """Test server search with exception"""
        mock_driver, mock_session, mock_result = mock_neo4j_driver

        with patch("mcp_server.yaml.safe_load", return_value=mock_config), \
             patch("mcp_server.GraphDatabase.driver", return_value=mock_driver):

            # Mock successful connection but failed search
            mock_session.run.side_effect = [
                Mock(),  # First call for connection test
                Exception("Database error"),  # Second call for search
            ]

            server = ASKGMCPServer(get_config_path(), "local")

            request = ServerSearchRequest(
                prompt="Find database servers",
                limit=5,
                min_confidence=0.5,
            )

            with pytest.raises(Exception, match="Database error"):
                await server.search_servers(request)


class TestServerSearchRequest:
    """Test cases for ServerSearchRequest"""

    def test_valid_request(self):
        """Test valid request creation"""
        request = ServerSearchRequest(
            prompt="Find database servers",
            limit=10,
            min_confidence=0.5,
        )

        assert request.prompt == "Find database servers"
        assert request.limit == 10
        assert request.min_confidence == 0.5

    def test_default_values(self):
        """Test default values"""
        request = ServerSearchRequest(prompt="Find servers")

        assert request.prompt == "Find servers"
        assert request.limit == 20  # default
        assert request.min_confidence == 0.5  # default

    def test_missing_prompt(self):
        """Test missing required prompt"""
        with pytest.raises(ValueError):
            ServerSearchRequest()


class TestServerSearchResult:
    """Test cases for ServerSearchResult"""

    def test_valid_result(self):
        """Test valid result creation"""
        servers = [
            MCPServer(
                id="test-1",
                name="Test Server 1",
                categories=[ServerCategory.DATABASE],
                operations=[OperationType.READ],
                registry_source=RegistrySource.GITHUB,
            ),
        ]

        result = ServerSearchResult(
            servers=servers,
            total_found=1,
            search_metadata={"test": "data"},
        )

        assert len(result.servers) == 1
        assert result.total_found == 1
        assert result.search_metadata["test"] == "data"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
