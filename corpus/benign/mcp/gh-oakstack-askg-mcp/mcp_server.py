#!/usr/bin/env python3
"""Official MCP Server Implementation for ASKG

This module provides a proper MCP server implementation using the official
MCP library that follows the Model Context Protocol specification.
"""

import asyncio
import json
import logging

# Import from the parent askg package
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from neo4j import GraphDatabase
from pydantic import BaseModel, Field

sys.path.append(str(Path(__file__).parent.parent / "src"))

from models import MCPServer, OperationType, RegistrySource, ServerCategory

# MCP imports
try:
    from mcp.server import Server
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        CallToolRequest,
        CallToolResult,
        Data,
        EmbeddedResource,
        Error,
        Image,
        ImageContent,
        ListToolsRequest,
        ListToolsResult,
        LoggingLevel,
        Prompt,
        Resource,
        Result,
        Text,
        TextContent,
        Tool,
    )
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    # Create stubs for when MCP is not available
    class Server:
        def __init__(self):
            pass

    class Tool:
        def __init__(self, name, description, inputSchema):
            self.name = name
            self.description = description
            self.inputSchema = inputSchema

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ServerSearchRequest(BaseModel):
    """Request model for server search"""

    prompt: str = Field(..., description="Search prompt describing the desired MCP servers")
    limit: int = Field(default=20, description="Maximum number of servers to return")
    min_confidence: float = Field(default=0.5, description="Minimum confidence score for results")


class ServerSearchResult(BaseModel):
    """Result model for server search"""

    servers: list[MCPServer] = Field(..., description="List of matching MCP servers")
    total_found: int = Field(..., description="Total number of servers found")
    search_metadata: dict[str, Any] = Field(default_factory=dict, description="Search metadata")


class ASKGMCPServer:
    """MCP Server for ASKG semantic search"""

    def __init__(self, config_path: str = ".config.yaml", instance: str = None):
        """Initialize the MCP server with Neo4j connection"""
        self.config_path = config_path
        self.instance = instance
        self.driver = None
        self._load_config()
        self._auto_select_instance()
        self._connect_to_neo4j()

    def _auto_select_instance(self):
        # If instance is explicitly set, use it
        if self.instance:
            return
        # Try remote first
        try:
            remote_config = self.config["neo4j"].get("remote")
            if remote_config:
                from neo4j import GraphDatabase
                driver = GraphDatabase.driver(
                    remote_config["uri"],
                    auth=(remote_config["user"], remote_config["password"]),
                )
                with driver.session() as session:
                    session.run("RETURN 1")
                self.instance = "remote"
                driver.close()
                logger.info("Auto-selected remote Neo4j instance.")
                return
        except Exception as e:
            logger.warning(f"Remote Neo4j not available: {e}")
        # Fallback to local
        self.instance = "local"
        logger.info("Falling back to local Neo4j instance.")

    def _load_config(self):
        """Load configuration from YAML file"""
        try:
            with open(self.config_path) as f:
                self.config = yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file {self.config_path} not found")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing configuration file: {e}")
            raise

    def _connect_to_neo4j(self):
        """Establish connection to Neo4j database"""
        try:
            neo4j_config = self.config["neo4j"][self.instance]
            self.driver = GraphDatabase.driver(
                neo4j_config["uri"],
                auth=(neo4j_config["user"], neo4j_config["password"]),
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"Connected to Neo4j instance: {self.instance}")
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def close(self):
        """Close Neo4j connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def search_servers(self, request: ServerSearchRequest) -> ServerSearchResult:
        """Search for MCP servers based on a semantic prompt
        
        This function performs a multi-faceted search:
        1. Text-based search on server names and descriptions
        2. Category-based search using semantic matching
        3. Operation-based search for functional capabilities
        4. Combined scoring and ranking
        """
        try:
            # Parse the prompt to extract search terms and intent
            search_terms = self._extract_search_terms(request.prompt)

            # Perform semantic search
            servers = await self._semantic_search(search_terms, request.limit, request.min_confidence)

            # Convert Neo4j records to MCPServer objects
            mcp_servers = []
            for server_record in servers:
                mcp_server = self._convert_to_mcp_server(server_record)
                if mcp_server:
                    mcp_servers.append(mcp_server)

            # If no servers found in database, do not use mock data
            if not mcp_servers:
                logger.info("No servers found in database, returning empty result (no mock data)")
                search_metadata = {
                    "search_terms": search_terms,
                    "prompt": request.prompt,
                    "instance": self.instance,
                    "search_strategy": "semantic_multi_faceted",
                    "mock_data": False,
                }
                return ServerSearchResult(
                    servers=[],
                    total_found=0,
                    search_metadata=search_metadata,
                )

            # Create search metadata
            search_metadata = {
                "search_terms": search_terms,
                "prompt": request.prompt,
                "instance": self.instance,
                "search_strategy": "semantic_multi_faceted",
            }

            return ServerSearchResult(
                servers=mcp_servers,
                total_found=len(mcp_servers),
                search_metadata=search_metadata,
            )

        except Exception as e:
            logger.error(f"Error during server search: {e}")
            raise

    def _extract_search_terms(self, prompt: str) -> dict[str, Any]:
        """Extract search terms and intent from the prompt
        
        This is a simple keyword extraction. In a production system,
        you might use NLP techniques or LLM-based intent extraction.
        """
        prompt_lower = prompt.lower()

        # Extract potential categories
        categories = []
        category_keywords = {
            "database": ["database", "db", "sql", "nosql", "query", "store"],
            "file_system": ["file", "filesystem", "fs", "storage", "read", "write"],
            "api_integration": ["api", "rest", "graphql", "http", "webhook"],
            "development_tools": ["dev", "development", "tool", "utility"],
            "data_processing": ["process", "transform", "analyze", "etl"],
            "cloud_services": ["cloud", "aws", "azure", "gcp", "s3"],
            "communication": ["chat", "message", "email", "notification"],
            "authentication": ["auth", "login", "oauth", "jwt", "security"],
            "monitoring": ["monitor", "log", "metric", "alert"],
            "search": ["search", "index", "elasticsearch", "lucene"],
            "ai_ml": ["ai", "ml", "machine learning", "model", "prediction"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                categories.append(category)

        # Extract potential operations
        operations = []
        operation_keywords = {
            "read": ["read", "reading", "get", "fetch", "retrieve"],
            "write": ["write", "writing", "save", "store", "create", "update"],
            "execute": ["execute", "executing", "run", "call", "invoke"],
            "query": ["query", "querying", "search", "find", "filter"],
            "transform": ["transform", "transforming", "convert", "process", "analyze"],
            "monitor": ["monitor", "monitoring", "watch", "observe", "track"],
        }

        for operation, keywords in operation_keywords.items():
            if any(keyword in prompt_lower for keyword in keywords):
                operations.append(operation)

        # Extract general search terms
        search_terms = prompt.split()

        return {
            "categories": categories,
            "operations": operations,
            "keywords": search_terms,
            "original_prompt": prompt,
        }

    async def _semantic_search(self, search_terms: dict[str, Any], limit: int, min_confidence: float) -> list[dict]:
        """Perform semantic search using multiple strategies
        """
        # Build the Cypher query based on search terms
        cypher_query, params = self._build_search_query(search_terms, limit, min_confidence)

        with self.driver.session() as session:
            result = session.run(cypher_query, params)
            return [dict(record) for record in result]

    def _build_search_query(self, search_terms: dict[str, Any], limit: int, min_confidence: float) -> tuple:
        """Build a Cypher query for semantic search
        """
        # Base query
        cypher = """
        MATCH (s:Server)
        WITH s,
             // Text relevance score
             CASE 
                 WHEN toLower(s.name) CONTAINS toLower($prompt) THEN 3.0
                 WHEN toLower(s.description) CONTAINS toLower($prompt) THEN 2.0
                 ELSE 0.0
             END as text_score,
             
             // Category relevance score
             CASE 
                 WHEN $categories IS NOT NULL AND ANY(cat IN $categories WHERE cat IN s.categories) 
                 THEN SIZE([cat IN $categories WHERE cat IN s.categories]) * 2.0
                 ELSE 0.0
             END as category_score,
             
             // Operation relevance score
             CASE 
                 WHEN $operations IS NOT NULL AND ANY(op IN $operations WHERE op IN s.operations)
                 THEN SIZE([op IN $operations WHERE op IN s.operations]) * 1.5
                 ELSE 0.0
             END as operation_score,
             
             // Popularity bonus
             COALESCE(s.popularity_score, 0) * 0.1 as popularity_bonus
             
        WITH s, (text_score + category_score + operation_score + popularity_bonus) as total_score
        
        WHERE total_score >= $min_confidence
        
        RETURN s, total_score
        ORDER BY total_score DESC
        LIMIT $limit
        """

        params = {
            "prompt": search_terms["original_prompt"],
            "categories": search_terms["categories"],
            "operations": search_terms["operations"],
            "min_confidence": min_confidence,
            "limit": limit,
        }

        return cypher, params

    def _convert_to_mcp_server(self, server_record: dict) -> MCPServer | None:
        """Convert Neo4j record to MCPServer object
        """
        try:
            server_data = server_record["s"]
            score = server_record.get("total_score", 0.0)

            # Convert string categories back to ServerCategory enums
            categories = []
            if server_data.get("categories"):
                for cat_str in server_data["categories"]:
                    try:
                        categories.append(ServerCategory(cat_str))
                    except ValueError:
                        categories.append(ServerCategory.OTHER)

            # Convert string operations back to OperationType enums
            operations = []
            if server_data.get("operations"):
                for op_str in server_data["operations"]:
                    try:
                        operations.append(OperationType(op_str))
                    except ValueError:
                        operations.append(OperationType.EXECUTE)

            # Convert registry source
            registry_source = RegistrySource.GITHUB  # Default to GITHUB
            if server_data.get("registry_source"):
                raw = server_data["registry_source"]
                mapping = {
                    "github": RegistrySource.GITHUB,
                    "glama": RegistrySource.GLAMA,
                    "mcp.so": RegistrySource.MCP_SO,
                    "mcpmarket.com": RegistrySource.MCP_MARKET,
                }
                registry_source = mapping.get(str(raw).lower(), RegistrySource.GITHUB)

            # Create MCPServer object
            return MCPServer(
                id=server_data.get("id", "unknown"),
                name=server_data.get("name", "Unknown Server"),
                description=server_data.get("description"),
                version=server_data.get("version"),
                author=server_data.get("author"),
                license=server_data.get("license"),
                homepage=server_data.get("homepage"),
                repository=server_data.get("repository"),
                implementation_language=server_data.get("implementation_language"),
                installation_command=server_data.get("installation_command"),
                categories=categories,
                operations=operations,
                data_types=server_data.get("data_types", []),
                registry_source=registry_source,
                source_url=server_data.get("source_url"),
                last_updated=server_data.get("last_updated"),
                popularity_score=server_data.get("popularity_score"),
                download_count=server_data.get("download_count"),
                raw_metadata={"search_score": score},
            )

        except Exception as e:
            logger.error(f"Error converting server record: {e}")
            return None


def create_mcp_server(config_path: str = ".config.yaml", instance: str = "local") -> Server:
    """Create and configure the MCP server"""
    if not MCP_AVAILABLE:
        raise ImportError("MCP library not available. Install with: pip install mcp")

    # Create the ASKG server instance
    askg_server = ASKGMCPServer(config_path, instance)

    # Create the MCP server
    server = Server("askg-mcp-server")

    @server.list_tools()
    async def handle_list_tools() -> ListToolsResult:
        """List available tools"""
        return ListToolsResult(
            tools=[
                Tool(
                    name="search_mcp_servers",
                    description="Search for MCP servers in the ASKG knowledge graph based on a semantic prompt",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prompt": {
                                "type": "string",
                                "description": "Search prompt describing the desired MCP servers",
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of servers to return",
                                "default": 10,
                            },
                            "min_confidence": {
                                "type": "number",
                                "description": "Minimum confidence score for results",
                                "default": 0.5,
                            },
                        },
                        "required": ["prompt"],
                    },
                ),
            ],
        )

    @server.call_tool()
    async def handle_call_tool(name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Handle tool calls"""
        if name == "search_mcp_servers":
            try:
                # Create search request
                search_request = ServerSearchRequest(**arguments)

                # Perform search
                result = await askg_server.search_servers(search_request)

                # Format the result as text content
                result_text = f"Found {result.total_found} MCP servers matching your query:\n\n"

                for i, server in enumerate(result.servers, 1):
                    result_text += f"{i}. **{server.name}**\n"
                    if server.description:
                        result_text += f"   Description: {server.description}\n"
                    if server.author:
                        result_text += f"   Author: {server.author}\n"
                    if server.categories:
                        categories_str = ", ".join([cat.value for cat in server.categories])
                        result_text += f"   Categories: {categories_str}\n"
                    if server.operations:
                        operations_str = ", ".join([op.value for op in server.operations])
                        result_text += f"   Operations: {operations_str}\n"
                    if server.repository:
                        result_text += f"   Repository: {server.repository}\n"
                    if server.raw_metadata and "search_score" in server.raw_metadata:
                        result_text += f"   Relevance Score: {server.raw_metadata['search_score']:.2f}\n"
                    result_text += "\n"

                # Add search metadata
                result_text += "**Search Metadata:**\n"
                result_text += f"- Search Terms: {result.search_metadata.get('search_terms', {})}\n"
                result_text += f"- Search Strategy: {result.search_metadata.get('search_strategy', 'unknown')}\n"
                result_text += f"- Neo4j Instance: {result.search_metadata.get('instance', 'unknown')}\n"

                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=Text(value=result_text),
                        ),
                    ],
                )

            except Exception as e:
                logger.error(f"Error in search_mcp_servers: {e}")
                return CallToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=Text(value=f"Error searching for MCP servers: {e!s}"),
                        ),
                    ],
                )
        else:
            return CallToolResult(
                content=[
                    TextContent(
                        type="text",
                        text=Text(value=f"Unknown tool: {name}"),
                    ),
                ],
            )

    return server


async def main():
    """Main entry point for the MCP server"""
    import argparse

    parser = argparse.ArgumentParser(description="ASKG MCP Server")
    parser.add_argument("--config", default=".config.yaml", help="Configuration file path")
    parser.add_argument("--instance", default="local", help="Neo4j instance to use")

    args = parser.parse_args()

    # Create the MCP server
    server = create_mcp_server(args.config, args.instance)

    # Run the server using stdio
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="askg-mcp-server",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities=None,
                ),
            ),
        )


if __name__ == "__main__":
    asyncio.run(main())
