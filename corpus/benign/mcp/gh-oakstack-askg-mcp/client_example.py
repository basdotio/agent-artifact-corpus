#!/usr/bin/env python3
"""Client Example for ASKG MCP Server

This example demonstrates how to use the ASKG MCP server to search for MCP servers
in the knowledge graph database.
"""

import asyncio
import json
import logging

# Import from the parent askg package
import sys
from pathlib import Path
from typing import Any, Dict

sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_server import ASKGMCPServer, ServerSearchRequest

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def search_example():
    """Example of searching for MCP servers"""
    # Initialize the ASKG MCP server
    with ASKGMCPServer(".config.yaml", "local") as server:

        # Example search queries
        search_queries = [
            "Find database servers for SQL operations",
            "Show me file system servers for reading and writing files",
            "I need API integration servers for REST APIs",
            "Find AI and machine learning servers",
            "Show me development tools and utilities",
            "I want servers for data processing and ETL",
            "Find authentication and security servers",
            "Show me monitoring and logging servers",
        ]

        for query in search_queries:
            print(f"\n{'='*60}")
            print(f"Search Query: {query}")
            print(f"{'='*60}")

            try:
                # Create search request
                request = ServerSearchRequest(
                    prompt=query,
                    limit=5,
                    min_confidence=0.3,
                )

                # Perform search
                result = await server.search_servers(request)

                # Display results
                print(f"Found {result.total_found} servers:")
                print()

                for i, mcp_server in enumerate(result.servers, 1):
                    print(f"{i}. {mcp_server.name}")
                    if mcp_server.description:
                        print(f"   Description: {mcp_server.description}")
                    if mcp_server.author:
                        print(f"   Author: {mcp_server.author}")
                    if mcp_server.categories:
                        categories = ", ".join([cat.value for cat in mcp_server.categories])
                        print(f"   Categories: {categories}")
                    if mcp_server.operations:
                        operations = ", ".join([op.value for op in mcp_server.operations])
                        print(f"   Operations: {operations}")
                    if mcp_server.repository:
                        print(f"   Repository: {mcp_server.repository}")
                    if mcp_server.raw_metadata and "search_score" in mcp_server.raw_metadata:
                        score = mcp_server.raw_metadata["search_score"]
                        print(f"   Relevance Score: {score:.2f}")
                    print()

                # Show search metadata
                print("Search Metadata:")
                metadata = result.search_metadata
                print(f"  - Extracted Categories: {metadata.get('search_terms', {}).get('categories', [])}")
                print(f"  - Extracted Operations: {metadata.get('search_terms', {}).get('operations', [])}")
                print(f"  - Search Strategy: {metadata.get('search_strategy', 'unknown')}")
                print(f"  - Neo4j Instance: {metadata.get('instance', 'unknown')}")

            except Exception as e:
                print(f"Error searching for servers: {e}")
                logger.error(f"Search error: {e}")


async def interactive_search():
    """Interactive search interface"""
    print("ASKG MCP Server - Interactive Search")
    print("Type 'quit' to exit")
    print()

    with ASKGMCPServer(".config.yaml", "local") as server:

        while True:
            try:
                # Get user input
                query = input("Enter search prompt: ").strip()

                if query.lower() in ["quit", "exit", "q"]:
                    break

                if not query:
                    continue

                # Get optional parameters
                try:
                    limit_input = input("Limit (default 10): ").strip()
                    limit = int(limit_input) if limit_input else 10
                except ValueError:
                    limit = 10

                try:
                    confidence_input = input("Min confidence (default 0.5): ").strip()
                    min_confidence = float(confidence_input) if confidence_input else 0.5
                except ValueError:
                    min_confidence = 0.5

                # Create search request
                request = ServerSearchRequest(
                    prompt=query,
                    limit=limit,
                    min_confidence=min_confidence,
                )

                # Perform search
                result = await server.search_servers(request)

                # Display results
                print(f"\nFound {result.total_found} servers:")
                print("-" * 40)

                for i, mcp_server in enumerate(result.servers, 1):
                    print(f"{i}. {mcp_server.name}")
                    if mcp_server.description:
                        print(f"   {mcp_server.description}")
                    if mcp_server.categories:
                        categories = ", ".join([cat.value for cat in mcp_server.categories])
                        print(f"   Categories: {categories}")
                    if mcp_server.raw_metadata and "search_score" in mcp_server.raw_metadata:
                        score = mcp_server.raw_metadata["search_score"]
                        print(f"   Score: {score:.2f}")
                    print()

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Error: {e}")
                logger.error(f"Interactive search error: {e}")


def test_connection():
    """Test the connection to Neo4j"""
    try:
        with ASKGMCPServer(".config.yaml", "local") as server:
            print("✅ Successfully connected to Neo4j")

            # Test a simple query
            with server.driver.session() as session:
                result = session.run("MATCH (s:Server) RETURN COUNT(s) as count")
                count = result.single()["count"]
                print(f"✅ Found {count} servers in the database")

    except Exception as e:
        print(f"❌ Connection failed: {e}")
        logger.error(f"Connection test failed: {e}")


async def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="ASKG MCP Server Client Example")
    parser.add_argument("--mode", choices=["example", "interactive", "test"],
                       default="example", help="Run mode")

    args = parser.parse_args()

    if args.mode == "test":
        test_connection()
    elif args.mode == "interactive":
        await interactive_search()
    else:
        await search_example()


if __name__ == "__main__":
    asyncio.run(main())
