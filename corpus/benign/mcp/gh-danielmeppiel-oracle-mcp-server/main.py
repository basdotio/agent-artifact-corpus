from mcp.server.fastmcp import FastMCP, Context
import json
import os
import sys
from typing import Dict, List, AsyncIterator, Optional
import time
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
import uuid  # retained for potential future use elsewhere
import oracledb

from db_context import DatabaseContext
from db_context.utils import wrap_untrusted
from db_context.schema.formatter import format_sql_query_result

# Load environment variables from .env file
load_dotenv()

ORACLE_CONNECTION_STRING = os.getenv('ORACLE_CONNECTION_STRING')
TARGET_SCHEMA = os.getenv('TARGET_SCHEMA')  # Optional schema override
CACHE_DIR = os.getenv('CACHE_DIR', '.cache')
USE_THICK_MODE = os.getenv('THICK_MODE', '').lower() in ('true', '1', 'yes')  # Convert string to boolean
READ_ONLY_MODE = os.getenv('READ_ONLY_MODE', 'true').lower() not in ('false', '0', 'no')
ORACLE_CLIENT_LIB_DIR = os.getenv('ORACLE_CLIENT_LIB_DIR', None)

@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DatabaseContext]:
    """Manage application lifecycle and ensure DatabaseContext is properly initialized"""
    print("App Lifespan initialising", file=sys.stderr)
    connection_string = ORACLE_CONNECTION_STRING
    if not connection_string:
        raise ValueError("ORACLE_CONNECTION_STRING environment variable is required. Set it in .env file or environment.")
    
    cache_dir = Path(CACHE_DIR)
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    db_context = DatabaseContext(
        connection_string=connection_string,
        cache_path=cache_dir / 'schema_cache.json',
        target_schema=TARGET_SCHEMA,
        use_thick_mode=USE_THICK_MODE,  # Pass the thick mode setting
        lib_dir=ORACLE_CLIENT_LIB_DIR,
        read_only=READ_ONLY_MODE
    )
    
    try:
        # Initialize cache on startup
        print("Initialising database cache...", file=sys.stderr)
        await db_context.initialize()
        print("Cache ready!", file=sys.stderr)
        yield db_context
    finally:
        # Ensure proper cleanup of database resources
        print("Closing database connections...", file=sys.stderr)
        await db_context.close()
        print("Database connections closed", file=sys.stderr)

# Initialize FastMCP server
mcp = FastMCP("oracle", lifespan=app_lifespan)
print("FastMCP server initialized", file=sys.stderr)

@mcp.tool()
async def get_table_schema(table_name: str, ctx: Context) -> str:
    """Single-table columns + FK relationships (lazy loads & caches).

    Use: Inspect one table's structure before writing queries / building joins.
    Compose: Pair with get_table_constraints + get_table_indexes for a full profile.
    Avoid: Looping across many tables for ranking (prefer get_related_tables + constraints/indexes directly).

    Args:
        table_name: Exact table name (case-insensitive).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    table_info = await db_context.get_schema_info(table_name)
    
    if not table_info:
        return f"Table '{table_name}' not found in the schema."
    
    # Delegate formatting to the TableInfo model
    return table_info.format_schema()

@mcp.tool()
async def rebuild_schema_cache(ctx: Context) -> str:
    """Rebuild the full schema index (expensive – invalidates caches).

    Use: After DDL changes that add/drop/rename many tables.
    Compose: Run once before bulk analytics if structure changed.
    Avoid: Inside loops or routine per-request flows.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    try:
        await db_context.rebuild_cache()
        cache_size = len(db_context.schema_manager.cache.all_table_names) if db_context.schema_manager.cache else 0
        return f"Schema cache rebuilt successfully. Indexed {cache_size} tables."
    except Exception as e:
        return f"Failed to rebuild schema cache: {str(e)}"

@mcp.tool()
async def get_tables_schema(table_names: List[str], ctx: Context) -> str:
    """Batch version of get_table_schema for a small explicit list.

    Use: You already have a short candidate set (< ~25) and need detail.
    Compose: Combine results with constraints / indexes per table if deeper profiling needed.
    Avoid: Broad discovery (use search_tables_schema first).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    results = []
    
    for table_name in table_names:
        table_info = await db_context.get_schema_info(table_name)
        if not table_info:
            results.append(f"\nTable '{table_name}' not found in the schema.")
            continue
        
        # Delegate formatting to the TableInfo model
        results.append(table_info.format_schema())
    
    return "\n".join(results)

@mcp.tool()
async def search_tables_schema(search_term: str, ctx: Context) -> str:
    """Find tables by name fragments (multi-term OR) + show their schemas.

    Use: Initial discovery when exact table names unknown.
    Compose: Feed resulting names into deeper profiling (constraints/indexes/dependents).
    Avoid: Acting as a full table list (results capped at 20; filtered).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    # Split search term by commas and whitespace and remove empty strings
    search_terms = [term.strip() for term in search_term.replace(',', ' ').split()]
    search_terms = [term for term in search_terms if term]
    
    if not search_terms:
        return "No valid search terms provided"
    
    # Track all matching tables without duplicates
    matching_tables = set()
    
    # Search for each term
    for term in search_terms:
        tables = await db_context.search_tables(term, limit=20)
        matching_tables.update(tables)
    
    # Convert back to list and limit to 20 results
    matching_tables = list(matching_tables)
    total_matches = len(matching_tables)
    limited_tables = matching_tables[:20]
    
    if not matching_tables:
        return f"No tables found matching any of these terms: {', '.join(search_terms)}"
    
    if total_matches > 20:
        results = [f"Found {total_matches} tables matching terms ({', '.join(search_terms)}). Returning the first 20 for performance reasons:"]
    else:
        results = [f"Found {total_matches} tables matching terms ({', '.join(search_terms)}):"]
    
    matching_tables = limited_tables
    
    # Now load the schema for each matching table
    for table_name in matching_tables:
        table_info = await db_context.get_schema_info(table_name)
        if not table_info:
            continue
        
        # Delegate formatting to the TableInfo model
        results.append(table_info.format_schema())
    
    return "\n".join(results)

@mcp.tool()
async def get_database_vendor_info(ctx: Context) -> str:
    """Database/edition + version + active schema context.

    Use: Capability gating, logging environment.
    Compose: Call once early; reuse info client-side.
    Avoid: Polling repeatedly (metadata rarely changes per session).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        db_info = await db_context.get_database_info()
        
        if not db_info:
            return "Could not retrieve database vendor information."
        
        result = [f"Database Vendor: {db_info.get('vendor', 'Unknown')}"]
        result.append(f"Version: {db_info.get('version', 'Unknown')}")
        if "schema" in db_info:
            result.append(f"Schema: {db_info['schema']}")
        
        if "additional_info" in db_info and db_info["additional_info"]:
            result.append("\nAdditional Version Information:")
            for info in db_info["additional_info"]:
                result.append(f"- {info}")
                
        if "error" in db_info:
            result.append(f"\nError: {db_info['error']}")
            
        return "\n".join(result)
    except Exception as e:
        return f"Error retrieving database vendor information: {str(e)}"

@mcp.tool()
async def search_columns(search_term: str, ctx: Context) -> str:
    """Find columns (substring match) and list hosting tables (limit 50).

    Use: Discover where a data attribute lives (e.g. customer_id).
    Compose: Narrow candidate tables before calling per-table tools.
    Avoid: Full structural profiling (use get_table_schema + constraints instead).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        matching_columns = await db_context.search_columns(search_term, limit=50)
        
        if not matching_columns:
            return f"No columns found matching '{search_term}'"
        
        results = [f"Found columns matching '{search_term}' in {len(matching_columns)} tables:"]
        
        for table_name, columns in matching_columns.items():
            results.append(f"\nTable: {table_name}")
            results.append("Matching columns:")
            for col in columns:
                nullable = "NULL" if col["nullable"] else "NOT NULL"
                results.append(f"  - {col['name']}: {col['type']} {nullable}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error searching columns: {str(e)}"

@mcp.tool()
async def get_pl_sql_objects(object_type: str, name_pattern: Optional[str], ctx: Context) -> str:
    """List PL/SQL objects (procedures/functions/packages/etc) by type/pattern.

    Use: Inventory logic surface / candidate impact analysis.
    Compose: Follow with get_object_source or get_dependent_objects.
    Avoid: Counting table dependencies (use get_dependent_objects on the table).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        objects = await db_context.get_pl_sql_objects(object_type.upper(), name_pattern)
        
        if not objects:
            pattern_msg = f" matching '{name_pattern}'" if name_pattern else ""
            return f"No {object_type.upper()} objects found{pattern_msg}"
        
        results = [f"Found {len(objects)} {object_type.upper()} objects:"]
        
        for obj in objects:
            results.append(f"\n{obj['type']}: {obj['name']}")
            if 'owner' in obj:
                results.append(f"Owner: {obj['owner']}")
            if 'status' in obj:
                results.append(f"Status: {obj['status']}")
            if 'created' in obj:
                results.append(f"Created: {obj['created']}")
            if 'last_modified' in obj:
                results.append(f"Last Modified: {obj['last_modified']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving PL/SQL objects: {str(e)}"

@mcp.tool()
async def get_object_source(object_type: str, object_name: str, ctx: Context) -> str:
    """Retrieve full DDL/source text for a single PL/SQL object.

    Use: Deep dive / debugging after identifying object via get_pl_sql_objects.
    Compose: Pair with dependency info for refactor planning.
    Avoid: Bulk enumeration (fetch only what you need).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        source = await db_context.get_object_source(object_type.upper(), object_name.upper())
        
        if not source:
            return wrap_untrusted(f"No source found for {object_type} {object_name}")
        
        return wrap_untrusted(f"Source for {object_type} {object_name}:\n\n{source}")
    except Exception as e:
        return wrap_untrusted(f"Error retrieving object source: {str(e)}")

@mcp.tool()
async def get_table_constraints(table_name: str, ctx: Context) -> str:
    """List PK / FK / UNIQUE / CHECK constraints for one table (cached TTL).

    Use: Relationship + integrity analysis; ranking features (FK counts, PK presence).
    Compose: With get_related_tables (quick FK direction) + get_table_indexes.
    Avoid: Manually parsing schema text for constraints elsewhere.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        constraints = await db_context.get_table_constraints(table_name)
        
        if not constraints:
            return f"No constraints found for table '{table_name}'"
        
        results = [f"Constraints for table '{table_name}':"]
        
        for constraint in constraints:
            constraint_type = constraint.get('type', 'UNKNOWN')
            name = constraint.get('name', 'UNNAMED')
            
            results.append(f"\n{constraint_type} Constraint: {name}")
            
            if 'columns' in constraint:
                results.append(f"Columns: {', '.join(constraint['columns'])}")
                
            if constraint_type == 'FOREIGN KEY' and 'references' in constraint:
                ref = constraint['references']
                results.append(f"References: {ref['table']}({', '.join(ref['columns'])})")
                
            if 'condition' in constraint:
                results.append(f"Condition: {constraint['condition']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving constraints: {str(e)}"

@mcp.tool()
async def get_table_indexes(table_name: str, ctx: Context) -> str:
    """Enumerate indexes (name, columns, uniqueness, status) for a table.

    Use: Performance hints + structural importance (index density, unique keys).
    Compose: With get_table_constraints (PK/UK) + get_dependent_objects.
    Avoid: Calling just to re-learn column order (columns via get_table_schema).
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        indexes = await db_context.get_table_indexes(table_name)
        
        if not indexes:
            return f"No indexes found for table '{table_name}'"
        
        results = [f"Indexes for table '{table_name}':"]
        
        for idx in indexes:
            idx_type = "UNIQUE " if idx.get('unique', False) else ""
            results.append(f"\n{idx_type}Index: {idx['name']}")
            results.append(f"Columns: {', '.join(idx['columns'])}")
            
            if 'tablespace' in idx:
                results.append(f"Tablespace: {idx['tablespace']}")
                
            if 'status' in idx:
                results.append(f"Status: {idx['status']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving indexes: {str(e)}"

@mcp.tool()
async def get_dependent_objects(object_name: str, ctx: Context) -> str:
    """List objects (views / PL/SQL / triggers) depending on a table/object.

    Use: Impact analysis & centrality (importance scoring dimension).
    Compose: Combine counts with FK + index metrics for ranking.
    Avoid: Running on every table blindly—filter candidates first.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        dependencies = await db_context.get_dependent_objects(object_name.upper())
        
        if not dependencies:
            return f"No objects found that depend on '{object_name}'"
        
        results = [f"Objects that depend on '{object_name}':"]
        
        for dep in dependencies:
            results.append(f"\n{dep['type']}: {dep['name']}")
            if 'owner' in dep:
                results.append(f"Owner: {dep['owner']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving dependencies: {str(e)}"

@mcp.tool()
async def get_user_defined_types(type_pattern: Optional[str], ctx: Context) -> str:
    """List user-defined types (+ attributes for OBJECT types).

    Use: Understand custom data modeling / complexity hotspots.
    Compose: Only include in importance scoring if type coupling matters.
    Avoid: Treating as a substitute for table relationship analysis.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        types = await db_context.get_user_defined_types(type_pattern)
        
        if not types:
            pattern_msg = f" matching '{type_pattern}'" if type_pattern else ""
            return f"No user-defined types found{pattern_msg}"
        
        results = [f"User-defined types:"]
        
        for typ in types:
            results.append(f"\nType: {typ['name']}")
            results.append(f"Type category: {typ['type_category']}")
            if 'owner' in typ:
                results.append(f"Owner: {typ['owner']}")
            if 'attributes' in typ and typ['attributes']:
                results.append("Attributes:")
                for attr in typ['attributes']:
                    results.append(f"  - {attr['name']}: {attr['type']}")
        
        return "\n".join(results)
    except Exception as e:
        return f"Error retrieving user-defined types: {str(e)}"

@mcp.tool()
async def get_related_tables(table_name: str, ctx: Context) -> str:
    """FK in/out adjacency for one table (incoming + outgoing lists, cached TTL).

    Use: Quick centrality signals (in-degree/out-degree) for ranking & join design.
    Compose: With get_table_constraints (details) + get_dependent_objects (broader usage).
    Avoid: Deriving FK direction manually from constraints output.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        related = await db_context.get_related_tables(table_name)
        
        if not related['referenced_tables'] and not related['referencing_tables']:
            return f"No related tables found for '{table_name}'"
        
        results = [f"Tables related to '{table_name}':"]
        
        if related['referenced_tables']:
            results.append("\nTables referenced by this table (outgoing foreign keys):")
            for table in related['referenced_tables']:
                results.append(f"  - {table}")
        
        if related['referencing_tables']:
            results.append("\nTables that reference this table (incoming foreign keys):")
            for table in related['referencing_tables']:
                results.append(f"  - {table}")
        
        return "\n".join(results)
        
    except Exception as e:
        return f"Error getting related tables: {str(e)}"

@mcp.tool()
async def run_sql_query(sql: str, ctx: Context, max_rows: int = 100) -> str:
    """Generic read-only SELECT executor (formatted output).

    Use: Ad hoc data inspection or metrics not exposed by other tools.
    Compose: Supplement structured metadata tools (e.g. row counts) sparingly.
    Avoid: Rebuilding metadata graphs already available via dedicated tools.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    
    try:
        result = await db_context.run_sql_query(sql, max_rows=max_rows)
        if not result.get("rows"):
            # Write or empty read response
            if "message" in result:
                return wrap_untrusted(result["message"])  # keep consistency
            return wrap_untrusted("Query executed successfully, but returned no rows.")
        formatted_result = format_sql_query_result(result)
        return wrap_untrusted(formatted_result)
    except PermissionError as e:
        return wrap_untrusted(f"Permission error: {e}")
    except oracledb.Error as e:
        return wrap_untrusted(f"Database error: {e}")
    except Exception as e:
        return wrap_untrusted(f"Unexpected error executing query: {e}")

@mcp.tool()
async def explain_query_plan(sql: str, ctx: Context) -> str:
    """Obtain an execution plan for a SELECT/CTE.

    Read-only mode note: The underlying Oracle mechanism uses PLAN_TABLE and
    cleanup (DELETE) statements; on locked-down or strictly read-only accounts
    this may fail. If so, a structured error is returned instead of a plan.

    Use: Pre-flight cost / access path inspection before running large queries.
    Avoid: High frequency calls in loops.
    """
    db_context: DatabaseContext = ctx.request_context.lifespan_context
    try:
        plan = await db_context.explain_query_plan(sql)
        # Standardize error wrapping
        if plan.get("error"):
            return wrap_untrusted(f"Explain plan unavailable: {plan['error']}")
        if not plan.get("execution_plan"):
            return wrap_untrusted("No execution plan rows returned.")
        lines = ["Execution Plan:"] + [f"  {step}" for step in plan["execution_plan"]]
        if plan.get("optimization_suggestions"):
            lines.append("\nSuggestions:")
            for s in plan["optimization_suggestions"]:
                lines.append(f"  - {s}")
        return wrap_untrusted("\n".join(lines))
    except PermissionError as e:
        return wrap_untrusted(f"Permission error: {e}")
    except oracledb.Error as e:
        return wrap_untrusted(f"Database error obtaining plan: {e}")
    except Exception as e:
        return wrap_untrusted(f"Unexpected error obtaining plan: {e}")

if __name__ == "__main__":
    mcp.run()
