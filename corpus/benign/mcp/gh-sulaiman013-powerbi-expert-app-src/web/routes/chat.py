"""
Chat Routes
===========
API endpoints for the AI chat functionality.
"""

import asyncio
import json
import uuid
import logging
from flask import Blueprint, jsonify, request

from src.llm.base_provider import LLMRequest
from src.connectors.pbip import PowerBIPBIPConnector
from ..services.state import app_state
from ..services.dax_utils import extract_dax_query, fix_table_names_in_dax, is_data_question
from ..services.pbip_service import PBIPService

logger = logging.getLogger("powerbi-v3-webui")
chat_bp = Blueprint('chat', __name__)


def _build_schema_context() -> tuple:
    """
    Build schema context from connected Power BI model.

    Returns:
        Tuple of (schema_context_string, data_source_type, inactive_relationships_list)
    """
    schema_context = ""
    data_source = "none"
    inactive_rels = []

    # Priority: Cloud connection > Desktop connection
    if app_state.cloud_connected and app_state.cloud_model_schema:
        data_source = "cloud"
        table_schemas = app_state.cloud_model_schema.get('table_schemas', [])
        measures = app_state.cloud_model_schema.get('measures', [])
        relationships = app_state.cloud_model_schema.get('relationships', [])

        schema_context = f"\n\nConnected Power BI Service Model (via XMLA):"
        schema_context += f"\n- Dataset: {app_state.cloud_model_schema.get('dataset_name', 'Unknown')}"
        schema_context += f"\n- Workspace: {app_state.cloud_model_schema.get('workspace_name', 'Unknown')}"

        schema_context += f"\n\nTABLES AND COLUMNS (use these EXACT names):"
        for ts in table_schemas[:12]:
            table_name = ts.get('name', '')
            columns = ts.get('columns', [])
            if columns:
                schema_context += f"\n• '{table_name}': [{'], ['.join(columns[:20])}]"

        # Include measures for cloud - same as desktop
        if measures:
            schema_context += f"\n\nMEASURES (use with square brackets):"
            measure_names = [m.get('name', '') for m in measures[:15]]
            schema_context += f"\n[{'], ['.join(measure_names)}]"

        # Include relationship info for cloud
        if relationships:
            rel_context, inactive_rels = _build_relationship_context(relationships)
            schema_context += rel_context

    elif app_state.model_schema:
        data_source = "desktop"
        table_schemas = app_state.model_schema.get('table_schemas', [])
        measures = app_state.model_schema.get('measures', [])
        relationships = app_state.model_schema.get('relationships', [])

        schema_context = f"\n\nConnected Power BI Desktop Model:"
        schema_context += f"\n\nTABLES AND COLUMNS (use these EXACT names):"

        for ts in table_schemas[:12]:
            table_name = ts.get('name', '')
            columns = ts.get('columns', [])
            if columns:
                schema_context += f"\n• '{table_name}': [{'], ['.join(columns[:20])}]"

        if measures:
            schema_context += f"\n\nMEASURES (use with square brackets):"
            measure_names = [m.get('name', '') for m in measures[:15]]
            schema_context += f"\n[{'], ['.join(measure_names)}]"

        if relationships:
            rel_context, inactive_rels = _build_relationship_context(relationships)
            schema_context += rel_context

    return schema_context, data_source, inactive_rels


def _build_relationship_context(relationships: list) -> tuple:
    """
    Build detailed relationship context including active/inactive status.

    This is critical for the LLM to know when to use USERELATIONSHIP().

    Returns:
        Tuple of (context_string, list_of_inactive_relationships)
    """
    if not relationships:
        return "", []

    # Debug: log the raw relationships data
    logger.info(f"[RELATIONSHIP DEBUG] Total relationships: {len(relationships)}")
    for i, r in enumerate(relationships[:3]):
        logger.info(f"[RELATIONSHIP DEBUG] Sample {i}: {r}")

    context = "\n\nMODEL RELATIONSHIPS:"

    # Separate active and inactive relationships
    active_rels = []
    inactive_rels = []

    for r in relationships:
        is_active = r.get('is_active', True)
        # Debug: log the is_active value and its type
        logger.info(f"[RELATIONSHIP DEBUG] is_active value: {is_active}, type: {type(is_active)}")
        # Handle string 'True'/'False' from DAX query results
        if isinstance(is_active, str):
            is_active = is_active.lower() == 'true'

        rel_info = {
            'from_table': r.get('from_table', ''),
            'from_column': r.get('from_column', ''),
            'to_table': r.get('to_table', ''),
            'to_column': r.get('to_column', '')
        }

        if is_active:
            active_rels.append(rel_info)
        else:
            inactive_rels.append(rel_info)

    # Document active relationships
    if active_rels:
        context += "\n\nACTIVE RELATIONSHIPS (automatically used in queries):"
        for r in active_rels[:10]:
            context += f"\n• '{r['from_table']}'[{r['from_column']}] → '{r['to_table']}'[{r['to_column']}]"

    # Document inactive relationships with USERELATIONSHIP guidance
    if inactive_rels:
        context += "\n\n🚨 INACTIVE RELATIONSHIPS - CRITICAL! YOU MUST USE USERELATIONSHIP():"
        for r in inactive_rels[:10]:
            context += f"\n• '{r['from_table']}'[{r['from_column']}] → '{r['to_table']}'[{r['to_column']}] [INACTIVE]"
            context += f"\n  REQUIRED: USERELATIONSHIP('{r['from_table']}'[{r['from_column']}], '{r['to_table']}'[{r['to_column']}])"

    return context, inactive_rels


def _handle_pbip_chat_request(user_message: str):
    """Handle PBIP file editing requests via chat."""
    try:
        parsed = PBIPService.parse_request(user_message)

        # If no path and no project loaded, ask for path
        if not parsed.path and not app_state.is_pbip_loaded:
            return jsonify({
                "response": "📁 **PBIP Project Not Loaded**\n\n" +
                           "Please provide the path to your PBIP project folder. For example:\n\n" +
                           "```\nI need to edit the PBIP at C:\\Users\\YourName\\Projects\\MyReport\\powerbi\n\n" +
                           "Rename tables:\n1. _Measures to DAX Measures\n2. Dim Date to DateTable\n```"
            })

        # Load project if path provided
        if parsed.path:
            if app_state.pbip_connector is None:
                app_state.pbip_connector = PowerBIPBIPConnector(auto_backup=True)

            success = app_state.pbip_connector.load_project(parsed.path)
            if not success:
                return jsonify({
                    "response": f"❌ **Failed to load PBIP project**\n\n" +
                               f"Could not find a valid PBIP project at:\n`{parsed.path}`\n\n" +
                               "Make sure the path contains a `.pbip` file or `.SemanticModel` folder."
                })

            app_state.pbip_loaded = True
            project_info = app_state.pbip_connector.get_project_info()

            # If no renames, just show project info
            if not parsed.renames:
                return jsonify({
                    "response": f"✅ **PBIP Project Loaded**\n\n" +
                               f"**Project:** {project_info.get('pbip_file', 'Unknown')}\n" +
                               f"**Report Format:** {project_info.get('report_format', 'Unknown')}\n" +
                               f"**TMDL Files:** {project_info.get('tmdl_file_count', 0)}\n" +
                               f"**Visual Files:** {project_info.get('visual_json_count', 0)}\n\n" +
                               "Now you can ask me to rename tables, columns, or measures. For example:\n" +
                               "- Rename table _Measures to DAX Measures\n" +
                               "- Rename column CustomerID to Customer ID in table Dim Customer"
                })

        # Check if project is loaded for renames
        if not app_state.is_pbip_loaded:
            return jsonify({
                "response": "❌ **No PBIP project loaded**\n\n" +
                           "Please include the PBIP project path in your message first."
            })

        # Process renames
        if parsed.renames:
            results = []
            for rename in parsed.renames:
                result = app_state.pbip_connector.rename_table_in_files(
                    rename.old_name, rename.new_name
                )
                results.append({
                    'old': rename.old_name,
                    'new': rename.new_name,
                    'success': result.success,
                    'refs': result.references_updated,
                    'files': len(result.files_modified),
                    'files_modified': result.files_modified
                })

            response = PBIPService.format_rename_result(results)
            return jsonify({"response": response})

        return jsonify({
            "response": "❓ Could not understand the PBIP operation. Please specify what you want to rename."
        })

    except Exception as e:
        logger.error(f"PBIP chat error: {e}", exc_info=True)
        return jsonify({"response": f"❌ Error: {str(e)}"})


@chat_bp.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint for AI-powered Power BI assistance."""
    try:
        data = request.json
        user_message = data.get('message', '')

        # Check for PBIP file editing requests first (doesn't require AI)
        if PBIPService.is_pbip_request(user_message):
            return _handle_pbip_chat_request(user_message)

        # Check if provider is configured
        if not app_state.is_llm_configured:
            return jsonify({
                "response": "⚙️ No AI provider configured.\n\nClick the **Settings** button (gear icon) to configure:\n- **Azure AI Foundry** (fast, cloud-based)\n- **Ollama** (local, requires GPU for speed)"
            })

        # Build context with schema if available
        schema_context, data_source, inactive_rels = _build_schema_context()

        # Check if Power BI is connected and user wants data
        pbi_connected = app_state.is_desktop_connected or app_state.is_cloud_connected
        wants_data = is_data_question(user_message)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        # If user wants actual data and PBI is connected, use two-step process
        if pbi_connected and wants_data:
            result, total_latency = _handle_data_query(
                user_message, schema_context, data_source, inactive_rels, loop
            )
        else:
            result, total_latency = _handle_code_generation(
                user_message, schema_context, loop
            )

        # Add provider info
        if app_state.current_provider_type == "azure-claude":
            provider_label = "Azure Claude"
        elif app_state.current_provider_type == "azure":
            provider_label = "Azure OpenAI"
        else:
            provider_label = "Ollama (local)"
        result += f"\n\n---\n_Generated by {provider_label} ({total_latency:.0f}ms)_"

        return jsonify({"response": result})

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        return jsonify({"response": f"❌ Error: {str(e)}"})


def _handle_data_query(user_message: str, schema_context: str, data_source: str, inactive_rels: list, loop) -> tuple:
    """Handle data query requests - generates and executes DAX."""

    # Build MANDATORY USERELATIONSHIP section if there are inactive relationships
    mandatory_userel_section = ""
    if inactive_rels:
        mandatory_userel_section = """
🚨🚨🚨 MANDATORY - READ THIS FIRST! 🚨🚨🚨
THIS MODEL HAS INACTIVE RELATIONSHIPS!
You MUST use USERELATIONSHIP() in your query or data will be NULL/blank!

The following relationships are INACTIVE and require USERELATIONSHIP():
"""
        for r in inactive_rels:
            mandatory_userel_section += f"""
• '{r['from_table']}'[{r['from_column']}] → '{r['to_table']}'[{r['to_column']}]
  YOU MUST INCLUDE: USERELATIONSHIP('{r['from_table']}'[{r['from_column']}], '{r['to_table']}'[{r['to_column']}])
"""
        mandatory_userel_section += """
If your query involves ANY of these tables, wrap your aggregations in CALCULATE with USERELATIONSHIP!
🚨🚨🚨 END MANDATORY SECTION 🚨🚨🚨
"""

    dax_system_prompt = f"""You are a Power BI DAX expert. The user wants actual data from their Power BI model.
{mandatory_userel_section}
Generate an executable DAX query wrapped in EVALUATE to answer their question.
The query MUST start with EVALUATE (optionally preceded by DEFINE for measures).

Available schema:
{schema_context}

CRITICAL - TABLE AND COLUMN NAMING RULES:
- Use the EXACT table and column names from the schema above - DO NOT modify them
- Table names with spaces MUST be wrapped in single quotes: 'Fact Financials', 'Dim Account'
- Column references use square brackets: 'Fact Financials'[Amount]
- DO NOT replace spaces with underscores - use the exact names as shown
- DO NOT assume table names - only use tables listed in the schema

⚠️ INACTIVE RELATIONSHIPS - CRITICAL:
- If the schema shows INACTIVE RELATIONSHIPS, you MUST use USERELATIONSHIP() to activate them
- USERELATIONSHIP goes INSIDE CALCULATE() as a filter argument
- Syntax: CALCULATE(expression, USERELATIONSHIP('FromTable'[FromColumn], 'ToTable'[ToColumn]))
- Without USERELATIONSHIP, inactive relationship columns will return NULL/blank values
- Example:
  CALCULATE(
      SUM('Fact Financials'[amount]),
      USERELATIONSHIP('Fact Financials'[entity_key], 'Dim Entity'[entity_key])
  )

SUMMARIZE SYNTAX - CRITICAL:
- SUMMARIZE(table, groupByColumn1, groupByColumn2, ..., "OutputName1", Expression1, "OutputName2", Expression2, ...)
- Grouping columns come FIRST without quotes: 'Table'[Column]
- Aggregated outputs come AFTER with a name in quotes: "Name", [Measure]
- WRONG: SUMMARIZE(table, "Name", 'Table'[Column]) - this will ERROR
- RIGHT: SUMMARIZE(table, 'Table'[Column], "Total", [Measure])

IMPORTANT:
- Return ONLY the DAX query in a code block
- Use EVALUATE to make it executable
- Check for INACTIVE relationships in the schema and use USERELATIONSHIP when needed
- Prefer using existing measures when available (they're listed above)
- For simple totals, use: EVALUATE ROW("Total", [MeasureName])

Example - Using USERELATIONSHIP for inactive relationship:
```dax
EVALUATE
SUMMARIZECOLUMNS(
    'Dim Entity'[entity_name],
    "Revenue", CALCULATE(
        SUM('Fact Financials'[amount_usd]),
        'Dim Account'[fs_category] = "Revenue",
        USERELATIONSHIP('Fact Financials'[entity_key], 'Dim Entity'[entity_key])
    )
)
```

Example - Simple total using existing measure:
```dax
EVALUATE
ROW("Total Revenue", [Total Revenue])
```

Example - Grouped by dimension with measures:
```dax
EVALUATE
SUMMARIZE(
    'Fact Financials',
    'Dim Entity'[entity_name],
    "Revenue", [Total Revenue],
    "Profit", [Net Income]
)
```"""

    dax_request = LLMRequest(
        system_prompt=dax_system_prompt,
        user_prompt=user_message,
        request_id=str(uuid.uuid4()),
        temperature=0.1,
        max_tokens=1024
    )

    dax_response = loop.run_until_complete(app_state.llm_provider.generate(dax_request))
    dax_query = extract_dax_query(dax_response.content)

    if dax_query:
        # Fix table names with spaces
        schema_to_use = (app_state.cloud_model_schema if data_source == "cloud"
                        else app_state.model_schema)
        if schema_to_use:
            raw_tables = schema_to_use.get('tables', [])
            if raw_tables and isinstance(raw_tables[0], dict):
                table_names = [t.get('name', '') for t in raw_tables]
            else:
                table_names = raw_tables

            # Debug: log before/after fix
            logger.info(f"[DAX FIX] Original query: {dax_query[:200]}")
            logger.info(f"[DAX FIX] Table names with spaces: {[t for t in table_names if ' ' in t]}")

            dax_query = fix_table_names_in_dax(dax_query, table_names)

            logger.info(f"[DAX FIX] Fixed query: {dax_query[:200]}")

        try:
            # Execute the DAX query
            if data_source == "cloud" and app_state.xmla_connector:
                results = app_state.xmla_connector.execute_dax(dax_query)
                source_label = "Power BI Service (XMLA)"
            else:
                results = app_state.desktop_connector.execute_dax(dax_query, max_rows=100)
                source_label = "Power BI Desktop"

            # Ask AI to interpret the results
            interpret_prompt = f"""The user asked: "{user_message}"

Data source: {source_label}

I ran this DAX query:
```dax
{dax_query}
```

Results:
{json.dumps(results[:20], indent=2)}

Please provide a clear, conversational answer to the user's question based on these results.
Format numbers nicely (e.g., $1,234,567 or 1.2M). Be concise and direct."""

            interpret_request = LLMRequest(
                system_prompt="You are a helpful Power BI analyst. Answer questions based on query results. Be concise and format numbers nicely.",
                user_prompt=interpret_prompt,
                request_id=str(uuid.uuid4()),
                temperature=0.3,
                max_tokens=1024
            )

            interpret_response = loop.run_until_complete(
                app_state.llm_provider.generate(interpret_request)
            )

            result = interpret_response.content
            total_latency = dax_response.latency_ms + interpret_response.latency_ms

            result += f"\n\n<details><summary>📊 Query Details ({source_label})</summary>\n\n```dax\n{dax_query}\n```\n\nReturned {len(results)} row(s)\n</details>"

            return result, total_latency

        except Exception as dax_error:
            result = dax_response.content
            result += f"\n\n⚠️ *Could not auto-execute: {str(dax_error)}*"
            return result, dax_response.latency_ms
    else:
        return dax_response.content, dax_response.latency_ms


def _handle_code_generation(user_message: str, schema_context: str, loop) -> tuple:
    """Handle standard code generation requests."""
    system_prompt = """You are PowerBI-Expert, an elite AI specialized in Microsoft Power BI.

Generate clean, optimized DAX and Power Query code. Use best practices:
- Use VAR for intermediate calculations
- Use DIVIDE() instead of / for safe division
- Use CALCULATE() with proper filter context
- For Power Query, use proper let...in structure

CRITICAL - TABLE AND COLUMN NAMING:
- Use the EXACT table and column names from the schema - DO NOT modify them
- Table names with spaces MUST be wrapped in single quotes: 'Fact Financials', 'Dim Account'
- Column references use square brackets: 'Fact Financials'[Amount]
- DO NOT replace spaces with underscores - use the exact names as provided

⚠️ INACTIVE RELATIONSHIPS - CRITICAL:
- Check the schema for INACTIVE RELATIONSHIPS marked with [INACTIVE]
- For inactive relationships, you MUST use USERELATIONSHIP() inside CALCULATE()
- Syntax: CALCULATE(expression, USERELATIONSHIP('FromTable'[FromCol], 'ToTable'[ToCol]))
- Without USERELATIONSHIP, queries using inactive relationships return NULL values

Provide working code with brief explanations."""

    llm_request = LLMRequest(
        system_prompt=system_prompt,
        user_prompt=user_message + schema_context,
        request_id=str(uuid.uuid4()),
        temperature=0.1,
        max_tokens=2048
    )

    response = loop.run_until_complete(app_state.llm_provider.generate(llm_request))
    return response.content, response.latency_ms
