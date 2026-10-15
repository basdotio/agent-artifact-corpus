#!/usr/bin/env python3
"""MCP Server for ASKG (Agent-Server Knowledge Graph)

This MCP server provides semantic search capabilities for MCP servers
stored in the Neo4j knowledge graph database.
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

from models import MCPServer, MCPTool, OperationType, RegistrySource, ServerCategory
from text2cypher import create_text2cypher_converter

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


def get_mock_servers(prompt: str) -> list[MCPServer]:
    """Return mock MCP servers for testing"""
    mock_servers = [
        MCPServer(
            id="mock_github_anthropic_claude-desktop",
            name="claude-desktop",
            description="Claude Desktop is a desktop application that brings Claude's capabilities to your computer. It includes MCP server integration for enhanced functionality.",
            version="1.0.0",
            author="anthropic",
            license="MIT",
            homepage="https://claude.ai/desktop",
            repository="https://github.com/anthropics/claude-desktop",
            implementation_language="TypeScript",
            installation_command="npm install -g @anthropic-ai/claude-desktop",
            categories=[ServerCategory.COMMUNICATION, ServerCategory.DEVELOPMENT_TOOLS],
            operations=[OperationType.READ, OperationType.WRITE, OperationType.EXECUTE],
            data_types=["text", "image", "file"],
            registry_source=RegistrySource.GITHUB,
            source_url="https://github.com/anthropics/claude-desktop",
            last_updated=None,
            popularity_score=1500,
            download_count=50000,
            raw_metadata={"mock": True, "search_score": 0.95},
        ),
        MCPServer(
            id="mock_github_modelcontextprotocol_mcp-server-sqlite",
            name="mcp-server-sqlite",
            description="An MCP server that provides SQLite database access. Allows Claude to read from and write to SQLite databases through the Model Context Protocol.",
            version="0.1.0",
            author="modelcontextprotocol",
            license="MIT",
            homepage="https://github.com/modelcontextprotocol/mcp-server-sqlite",
            repository="https://github.com/modelcontextprotocol/mcp-server-sqlite",
            implementation_language="Python",
            installation_command="pip install mcp-server-sqlite",
            categories=[ServerCategory.DATABASE, ServerCategory.DATA_PROCESSING],
            operations=[OperationType.READ, OperationType.WRITE, OperationType.QUERY],
            data_types=["sql", "table", "json"],
            registry_source=RegistrySource.GITHUB,
            source_url="https://github.com/modelcontextprotocol/mcp-server-sqlite",
            last_updated=None,
            popularity_score=800,
            download_count=15000,
            raw_metadata={"mock": True, "search_score": 0.88},
        ),
        MCPServer(
            id="mock_github_modelcontextprotocol_mcp-server-filesystem",
            name="mcp-server-filesystem",
            description="An MCP server that provides filesystem access. Allows Claude to read, write, and manage files on the local filesystem through the Model Context Protocol.",
            version="0.2.0",
            author="modelcontextprotocol",
            license="MIT",
            homepage="https://github.com/modelcontextprotocol/mcp-server-filesystem",
            repository="https://github.com/modelcontextprotocol/mcp-server-filesystem",
            implementation_language="Python",
            installation_command="pip install mcp-server-filesystem",
            categories=[ServerCategory.FILE_SYSTEM, ServerCategory.DEVELOPMENT_TOOLS],
            operations=[OperationType.READ, OperationType.WRITE, OperationType.EXECUTE],
            data_types=["file", "directory", "text", "binary"],
            registry_source=RegistrySource.GITHUB,
            source_url="https://github.com/modelcontextprotocol/mcp-server-filesystem",
            last_updated=None,
            popularity_score=1200,
            download_count=25000,
            raw_metadata={"mock": True, "search_score": 0.92},
        ),
    ]

    # Filter servers based on prompt (simple keyword matching)
    prompt_lower = prompt.lower()
    filtered_servers = []

    for server in mock_servers:
        score = 0.0

        # Check name
        if prompt_lower in server.name.lower():
            score += 3.0

        # Check description
        if server.description and prompt_lower in server.description.lower():
            score += 2.0

        # Check categories
        for category in server.categories:
            if prompt_lower in category.value.lower():
                score += 1.5

        # Check operations
        for operation in server.operations:
            if prompt_lower in operation.value.lower():
                score += 1.0

        # Check implementation language
        if server.implementation_language and prompt_lower in server.implementation_language.lower():
            score += 0.5

        # Add server if it has any relevance
        if score > 0:
            server.raw_metadata["search_score"] = score
            filtered_servers.append(server)

    # If no specific matches, return all servers
    if not filtered_servers:
        return mock_servers

    # Sort by relevance score and return top results
    filtered_servers.sort(key=lambda x: x.raw_metadata.get("search_score", 0), reverse=True)
    return filtered_servers[:3]


class ASKGMCPServer:
    """MCP Server for ASKG semantic search"""

    def __init__(self, config_path: str = ".config.yaml", instance: str = None):
        """Initialize the MCP server with Neo4j connection"""
        self.config_path = config_path
        self.instance = instance
        self.driver = None
        self.text2cypher = create_text2cypher_converter()
        self._load_config()
        self._auto_select_instance()
        self._connect_to_neo4j()

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
                "search_strategy": "llm_enhanced_semantic" if self.text2cypher else "keyword_based_semantic",
                "query_conversion": "text2cypher_llm" if self.text2cypher else "keyword_extraction",
                "mock_data": len([s for s in mcp_servers if s.raw_metadata.get("mock", False)]) > 0,
            }

            return ServerSearchResult(
                servers=mcp_servers,
                total_found=len(mcp_servers),
                search_metadata=search_metadata,
            )

        except Exception as e:
            logger.error(f"Error during server search: {e}")
            logger.info("Falling back to mock data due to error")

            # Fallback to mock data
            mcp_servers = get_mock_servers(request.prompt)

            search_metadata = {
                "prompt": request.prompt,
                "instance": self.instance,
                "search_strategy": "mock_fallback",
                "query_conversion": "none_due_to_error",
                "error": str(e),
                "mock_data": True,
            }

            return ServerSearchResult(
                servers=mcp_servers,
                total_found=len(mcp_servers),
                search_metadata=search_metadata,
            )

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
            "read": ["read", "get", "fetch", "retrieve"],
            "write": ["write", "save", "store", "create", "update"],
            "execute": ["execute", "run", "call", "invoke"],
            "query": ["query", "search", "find", "filter"],
            "transform": ["transform", "convert", "process", "analyze"],
            "monitor": ["monitor", "watch", "observe", "track"],
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
        # Use text2cypher converter if available, otherwise fallback to keyword-based search
        if self.text2cypher:
            try:
                # Convert the original prompt to Cypher using LLM
                cypher_result = self.text2cypher.convert_to_cypher(
                    search_terms["original_prompt"], 
                    limit, 
                    min_confidence
                )
                cypher_query = cypher_result["cypher"]
                params = cypher_result["parameters"]
                
                logger.info(f"Using LLM-generated Cypher query: {cypher_query}")
                logger.info(f"Query parameters: {params}")
                
                # Test the query to see if it returns results
                with self.driver.session() as session:
                    test_result = session.run(cypher_query, params)
                    test_records = [dict(record) for record in test_result]
                    
                    # If no results, fall back to keyword search
                    if not test_records:
                        logger.info("LLM query returned no results, falling back to keyword search")
                        fallback_result = self.text2cypher._fallback_query(
                            search_terms["original_prompt"], 
                            limit, 
                            min_confidence
                        )
                        cypher_query = fallback_result["cypher"]
                        params = fallback_result["parameters"]
                        logger.info(f"Using fallback query: {cypher_query}")
                        logger.info(f"Fallback parameters: {params}")
                    else:
                        logger.info(f"LLM query returned {len(test_records)} results")
                
            except Exception as e:
                logger.warning(f"Text2Cypher conversion failed, falling back to keyword search: {e}")
                fallback_result = self.text2cypher._fallback_query(
                    search_terms["original_prompt"], 
                    limit, 
                    min_confidence
                )
                cypher_query = fallback_result["cypher"]
                params = fallback_result["parameters"]
        else:
            # Fallback to keyword-based search
            cypher_query, params = self._build_search_query(search_terms, limit, min_confidence)

        with self.driver.session() as session:
            result = session.run(cypher_query, params)
            return [dict(record) for record in result]

    def _build_search_query(self, search_terms: dict[str, Any], limit: int, min_confidence: float) -> tuple:
        """Build a Cypher query for semantic search
        """
        # Base query with tools
        cypher = """
        MATCH (s:Server)
        OPTIONAL MATCH (s)-[:HAS_TOOL]->(t:Tool)
        WITH s, COLLECT(t) as tools,
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
             
        WITH s, tools, (text_score + category_score + operation_score + popularity_bonus) as total_score
        
        WHERE total_score >= $min_confidence
        
        RETURN s, tools, total_score
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
            tools_data = server_record.get("tools", [])
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

            # Convert tools data to MCPTool objects
            tools = []
            if tools_data:
                for tool_data in tools_data:
                    if tool_data:  # Skip None values
                        tools.append(MCPTool(
                            name=tool_data.get("name", "Unknown Tool"),
                            description=tool_data.get("description"),
                            parameters=tool_data.get("parameters"),
                        ))

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
                homepage=str(server_data.get("homepage")) if server_data.get("homepage") else None,
                repository=str(server_data.get("repository")) if server_data.get("repository") else None,
                implementation_language=server_data.get("implementation_language"),
                installation_command=server_data.get("installation_command"),
                tools=tools,  # Add tools to the server
                categories=categories,
                operations=operations,
                data_types=server_data.get("data_types", []),
                registry_source=registry_source,
                source_url=str(server_data.get("source_url")) if server_data.get("source_url") else None,
                last_updated=server_data.get("last_updated"),
                popularity_score=server_data.get("popularity_score"),
                download_count=server_data.get("download_count"),
                raw_metadata={"search_score": score},
            )

        except Exception as e:
            logger.error(f"Error converting server record: {e}")
            return None


# MCP Server Protocol Implementation
class MCPServerProtocol:
    """MCP Server Protocol implementation"""

    def __init__(self, askg_server: ASKGMCPServer):
        self.askg_server = askg_server

    async def handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Handle incoming MCP requests"""
        method = request.get("method")
        params = request.get("params", {})

        if method == "search_servers":
            search_request = ServerSearchRequest(**params)
            result = await self.askg_server.search_servers(search_request)
            return {
                "jsonrpc": "2.0",
                "id": request.get("id"),
                "result": result.model_dump(mode="json"),
            }
        return {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "error": {
                "code": -32601,
                "message": f"Method {method} not found",
            },
        }


def main():
    import argparse

    import aiohttp
    from aiohttp import web

    parser = argparse.ArgumentParser(description="ASKG MCP Server")
    parser.add_argument("--config", default=".config.yaml", help="Configuration file path")
    parser.add_argument("--instance", default="local", help="Neo4j instance to use")
    parser.add_argument("--port", type=int, default=8200, help="Server port")
    args = parser.parse_args()

    # Initialize the ASKG MCP server
    askg_server = ASKGMCPServer(args.config, args.instance)
    protocol = MCPServerProtocol(askg_server)

    async def handle_request(request):
        try:
            data = await request.json()
            response = await protocol.handle_request(data)
            return web.json_response(response)
        except Exception as e:
            logger.error(f"Error handling request: {e}")
            return web.json_response({
                "jsonrpc": "2.0",
                "id": data.get("id") if "data" in locals() else None,
                "error": {
                    "code": -32603,
                    "message": str(e),
                },
            })

    app = web.Application()
    app.router.add_post("/", handle_request)

    logger.info(f"Starting ASKG MCP server on port {args.port}")
    web.run_app(app, port=args.port)

if __name__ == "__main__":
    main()
