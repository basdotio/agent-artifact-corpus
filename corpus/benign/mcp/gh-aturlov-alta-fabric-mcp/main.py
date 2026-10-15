"""Fabric MCP Server - Model Context Protocol server for Microsoft Fabric

This MCP server provides AI assistants (like GitHub Copilot) with tools to interact with 
Microsoft Fabric workspaces, lakehouses, and data through REST APIs and SQL endpoints.

Available Tools:
- list_workspaces: Discover all accessible Fabric workspaces
- list_lakehouses: List lakehouses within a specific workspace  
- get_lakehouse_tables: Enumerate all tables in a lakehouse (supports schema-enabled lakehouses)
- get_table_schema: Retrieve detailed column metadata from tables
- get_table_sample_data: Sample data from tables for exploration and understanding
- execute_custom_sql_query: Run custom SQL queries for analytics and reporting
- sign_out: Clear cached authentication tokens (interactive auth only)

Authentication: Supports both interactive (device code flow) and service principal auth
Backend: Uses FastMCP for stdio transport to VS Code
Requirements: See README.md for setup instructions

Usage: Configure in VS Code via mcp.json to enable automatic Copilot integration
"""

from typing import Any
from fastmcp import FastMCP

from fabric_mcp_service import FabricMCPService

# Initialize FastMCP server
mcp = FastMCP("Fabric MCP Server")

# Initialize service layer that contains all business logic
service = FabricMCPService()


# ============================================================================
# MCP Tools - Fabric Workspace and Lakehouse Operations
# ============================================================================

@mcp.tool()
async def list_workspaces() -> dict[str, Any]:
    """List all Fabric workspaces the user has access to.
    
    This is the first tool to call when exploring Fabric. Returns workspace IDs needed
    for all other discovery and query tools.
    
    Use this when:
    - Starting exploration of available Fabric resources
    - Need to find a specific workspace ID
    - Want to see all available workspaces
    
    Returns:
        dict: {"workspaces": [{"id": str, "name": str}, ...]}
    """
    return await service.list_workspaces()


@mcp.tool()
async def list_lakehouses(workspace_id: str) -> dict[str, Any]:
    """List all lakehouses in a workspace.
    
    Call this after list_workspaces() to find lakehouses. Returns lakehouse IDs needed
    for table discovery and queries.
    
    Use this when:
    - Finding which lakehouses exist in a workspace
    - Need a lakehouse ID for data exploration
    - Exploring data storage locations
    
    Args:
        workspace_id: Workspace ID (from list_workspaces)
    
    Returns:
        dict: {"lakehouses": [{"id": str, "name": str}, ...]}
    """
    return await service.list_lakehouses(workspace_id)


@mcp.tool()
async def get_lakehouse_tables(workspace_id: str, lakehouse_id: str) -> dict[str, Any]:
    """List all tables in a lakehouse (supports schema-enabled lakehouses).
    
    Returns all tables with schema prefixes (e.g., "silver.customers") for use in
    other tools. SQL-based discovery works reliably with complex schemas.
    
    Use this when:
    - Discovering available tables for analysis
    - Understanding lakehouse structure
    - Getting table names to use with get_table_schema() or get_table_sample_data()

    Args:
        workspace_id: Workspace ID
        lakehouse_id: Lakehouse ID (from list_lakehouses)
    
    Returns:
        dict: {
            "tables": [
                {"schema": str, "name": str, "type": str, "full_name": str},
                ...
            ]
        }
    Note: Use the "full_name" field (e.g., "silver.customers") with other tools.
    """
    return await service.get_lakehouse_tables(workspace_id, lakehouse_id)


# ============================================================================
# MCP Tools - SQL Query Operations
# ============================================================================

@mcp.tool()
async def get_table_schema(workspace_id: str, lakehouse_id: str, table_name: str) -> dict[str, Any]:
    """Get column definitions (names, types, nullability) for a table.
    
    Use this to understand table structure before writing queries or sampling data.
    Returns complete metadata needed to write correct SQL.
    
    Use this when:
    - Understanding table structure before queries
    - Checking column names and data types
    - Verifying nullability or precision requirements
    - Planning SQL joins or filters
    
    Args:
        workspace_id: Workspace ID
        lakehouse_id: Lakehouse ID
        table_name: Table name (use full_name from get_lakehouse_tables, e.g., "silver.customers")
    
    Returns:
        dict with "table_name" and "columns" array:
        - Each column has: name, data_type, is_nullable, precision, scale, position
        Example: {"name": "customer_id", "data_type": "INT", "is_nullable": False, ...}
    """
    return await service.get_table_schema(workspace_id, lakehouse_id, table_name)


@mcp.tool()
async def get_table_sample_data(
    workspace_id: str,
    lakehouse_id: str,
    table_name: str,
    limit: int = 10
) -> dict[str, Any]:
    """Peek at data in a table (sample rows) to understand content and format.
    
    Returns first N rows showing actual values, data quality, and content patterns.
    Faster than full queries for quick exploration.
    
    Use this when:
    - Exploring table content before writing queries
    - Checking data quality and formats
    - Seeing real values to understand field meanings
    - Verifying table is populated before complex analysis
    
    Args:
        workspace_id: Workspace ID
        lakehouse_id: Lakehouse ID
        table_name: Table name (use full_name from get_lakehouse_tables, e.g., "silver.customers")
        limit: Rows to return (default: 10). Increase for larger samples.
    
    Returns:
        dict with "table_name", "sample_rows" array, and "row_count"
    """
    return await service.get_table_sample_data(workspace_id, lakehouse_id, table_name, limit)


@mcp.tool()
async def execute_custom_sql_query(
    workspace_id: str,
    lakehouse_id: str,
    query: str
) -> dict[str, Any]:
    """Execute any SQL query for analysis, aggregation, and reporting.
    
    Supports SELECT with JOINs, GROUP BY, WHERE, aggregations, and calculated fields.
    Use after understanding tables with get_lakehouse_tables and get_table_schema.
    
    Use this when:
    - Running analytical queries (e.g., revenue by category)
    - Joining multiple tables
    - Aggregating data (SUM, COUNT, GROUP BY)
    - Filtering and transforming data
    - Complex business logic queries
    
    Args:
        workspace_id: Workspace ID
        lakehouse_id: Lakehouse ID
        query: SQL query (T-SQL dialect, e.g., "SELECT TOP 100 * FROM [schema].[table]")
    
    Returns:
        dict with "success", "query", "row_count", and "results" array
        Example success: {"success": True, "row_count": 42, "results": [{...}, ...]}
        Example error: {"success": False, "error": "[error message]"}
    """
    return await service.execute_custom_sql_query(workspace_id, lakehouse_id, query)


# ============================================================================
# MCP Tools - Authentication Management
# ============================================================================

@mcp.tool()
async def sign_out() -> dict[str, str]:
    """Sign out and clear cached authentication tokens.
    
    Use this to force re-authentication (interactive auth) or when switching users.
    Only affects interactive authentication mode (device code flow).
    
    Use this when:
    - Switching to a different user account
    - Fixing authentication issues
    - Testing multi-user scenarios
    - Debugging permission errors
    
    Returns:
        dict: {"status": "success" or "not_applicable", "message": str}
    """
    return service.sign_out()


# ============================================================================
# Entry Point
# ============================================================================

if __name__ == "__main__":
    mcp.run()
