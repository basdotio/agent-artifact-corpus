from typing import Optional
import asyncio
from mcp.server.fastmcp import FastMCP
from databricks_formatter import format_query_results
from databricks_sdk_utils import (
    get_uc_table_details,
    get_uc_catalog_details,
    get_uc_schema_details,
    execute_databricks_sql,
    get_uc_all_catalogs_summary
)


mcp = FastMCP("databricks")

@mcp.tool()
async def execute_sql_query(sql: str) -> str:
    """
    Executes a given SQL query against the Databricks SQL warehouse and returns the formatted results.
    
    Use this tool when you need to run specific SQL queries, such as SELECT, SHOW, or other DQL statements.
    This is ideal for targeted data retrieval or for queries that are too complex for the structured description tools.
    The results are returned in a human-readable, Markdown-like table format.

    Args:
        sql: The complete SQL query string to execute.
    """
    try:
        sdk_result = await asyncio.to_thread(execute_databricks_sql, sql_query=sql)
        
        status = sdk_result.get("status")
        if status == "failed":
            error_message = sdk_result.get("error", "Unknown query execution error.")
            details = sdk_result.get("details", "No additional details provided.")
            return f"SQL Query Failed: {error_message}\nDetails: {details}"
        elif status == "error":
            error_message = sdk_result.get("error", "Unknown error during SQL execution.")
            details = sdk_result.get("details", "No additional details provided.")
            return f"Error during SQL Execution: {error_message}\nDetails: {details}"
        elif status == "success":
            return format_query_results(sdk_result)
        else:
            # Should not happen if execute_databricks_sql always returns a known status
            return f"Received an unexpected status from query execution: {status}. Result: {sdk_result}"
            
    except Exception as e:
        return f"An unexpected error occurred while executing SQL query: {str(e)}"


@mcp.tool()
async def describe_uc_table(full_table_name: str, include_lineage: Optional[bool] = False) -> str:
    """
    Provides a detailed description of a specific Unity Catalog table.
    
    Use this tool to understand the structure (columns, data types, partitioning) of a single table.
    This is essential before constructing SQL queries against the table.
    
    Optionally, it can include comprehensive lineage information that goes beyond traditional 
    table-to-table dependencies:

    **Table Lineage:**
    - Upstream tables (tables this table reads from)
    - Downstream tables (tables that read from this table)
    
    **Notebook & Job Lineage:**
    - Notebooks that read from this table, including:
      * Notebook name and workspace path
      * Associated Databricks job information (job name, ID, task details)
    - Notebooks that write to this table with the same detailed context
    
    **Use Cases:**
    - Data impact analysis: understand what breaks if you modify this table
    - Code discovery: find notebooks that process this data for further analysis
    - Debugging: trace data flow issues by examining both table dependencies and processing code
    - Documentation: understand the complete data ecosystem around a table

    The lineage information allows LLMs and tools to subsequently fetch the actual notebook 
    code content for deeper analysis of data transformations and business logic.

    The output is formatted in Markdown.

    Args:
        full_table_name: The fully qualified three-part name of the table (e.g., `catalog.schema.table`).
        include_lineage: Set to True to fetch and include comprehensive lineage (tables, notebooks, jobs). 
                         Defaults to False. May take longer to retrieve but provides rich context for 
                         understanding data dependencies and enabling code exploration.
    """
    try:
        details_markdown = await asyncio.to_thread(
            get_uc_table_details,
            full_table_name=full_table_name,
            include_lineage=include_lineage
        )
        return details_markdown
    except ImportError as e:
        return f"Error initializing Databricks SDK utilities: {str(e)}. Please ensure DATABRICKS_HOST and DATABRICKS_TOKEN are set."
    except Exception as e:
        return f"Error getting detailed table description for '{full_table_name}': {str(e)}"

@mcp.tool()
async def describe_uc_catalog(catalog_name: str) -> str:
    """
    Provides a summary of a specific Unity Catalog, listing all its schemas with their names and descriptions.
    
    Use this tool when you know the catalog name and need to discover the schemas within it.
    This is often a precursor to describing a specific schema or table.
    The output is formatted in Markdown.

    Args:
        catalog_name: The name of the Unity Catalog to describe (e.g., `prod`, `dev`, `system`).
    """
    try:
        summary_markdown = await asyncio.to_thread(
            get_uc_catalog_details,
            catalog_name=catalog_name
        )
        return summary_markdown
    except ImportError as e:
        return f"Error initializing Databricks SDK utilities: {str(e)}. Please ensure DATABRICKS_HOST and DATABRICKS_TOKEN are set."
    except Exception as e:
        return f"Error getting catalog summary for '{catalog_name}': {str(e)}"

@mcp.tool()
async def describe_uc_schema(catalog_name: str, schema_name: str, include_columns: Optional[bool] = False) -> str:
    """
    Provides detailed information about a specific schema within a Unity Catalog.
    
    Use this tool to understand the contents of a schema, primarily its tables.
    Optionally, it can list all tables within the schema and their column details.
    Set `include_columns=True` to get column information, which is crucial for query construction but makes the output longer.
    If `include_columns=False`, only table names and descriptions are shown, useful for a quicker overview.
    The output is formatted in Markdown.

    Args:
        catalog_name: The name of the catalog containing the schema.
        schema_name: The name of the schema to describe.
        include_columns: If True, lists tables with their columns. Defaults to False for a briefer summary.
    """
    try:
        details_markdown = await asyncio.to_thread(
            get_uc_schema_details,
            catalog_name=catalog_name,
            schema_name=schema_name,
            include_columns=include_columns
        )
        return details_markdown
    except ImportError as e:
        return f"Error initializing Databricks SDK utilities: {str(e)}. Please ensure DATABRICKS_HOST and DATABRICKS_TOKEN are set."
    except Exception as e:
        return f"Error getting detailed schema description for '{catalog_name}.{schema_name}': {str(e)}"

@mcp.tool()
async def list_uc_catalogs() -> str:
    """
    Lists all available Unity Catalogs with their names, descriptions, and types.
    
    Use this tool as a starting point to discover available data sources when you don't know specific catalog names.
    It provides a high-level overview of all accessible catalogs in the workspace.
    The output is formatted in Markdown.
    """
    try:
        summary_markdown = await asyncio.to_thread(get_uc_all_catalogs_summary)
        return summary_markdown
    except ImportError as e:
        return f"Error initializing Databricks SDK utilities: {str(e)}. Please ensure DATABRICKS_HOST and DATABRICKS_TOKEN are set."
    except Exception as e:
        return f"Error listing catalogs: {str(e)}"

if __name__ == "__main__":
    mcp.run(transport='stdio')