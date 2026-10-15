"""
Desktop Routes
==============
API endpoints for Power BI Desktop connectivity.
"""

import logging
from flask import Blueprint, jsonify, request

from src.connectors.desktop import PowerBIDesktopConnector
from ..services.state import app_state

logger = logging.getLogger("powerbi-v3-webui")
desktop_bp = Blueprint('desktop', __name__)


@desktop_bp.route('/discover')
def discover():
    """Discover running Power BI Desktop instances."""
    try:
        if app_state.desktop_connector is None:
            app_state.desktop_connector = PowerBIDesktopConnector()

        if not app_state.desktop_connector.is_available():
            return jsonify({
                "response": "❌ Desktop connectivity unavailable. Install: pip install psutil pythonnet",
                "instances": [],
                "count": 0
            })

        instances = app_state.desktop_connector.discover_instances()

        if not instances:
            return jsonify({
                "response": "❌ No Power BI Desktop instances found. Please open a .pbix file.",
                "instances": [],
                "count": 0
            })

        response = f"✅ Found {len(instances)} Power BI Desktop instance(s):\n\n"
        for i, inst in enumerate(instances, 1):
            response += f"  {i}. Port: {inst['port']} | Model: {inst['model_name']}\n"

        return jsonify({
            "response": response,
            "instances": instances,
            "count": len(instances)
        })

    except Exception as e:
        return jsonify({
            "response": f"❌ Error: {str(e)}",
            "instances": [],
            "count": 0
        })


@desktop_bp.route('/connect')
def connect():
    """Connect to the first available Power BI Desktop instance."""
    try:
        if app_state.desktop_connector is None:
            app_state.desktop_connector = PowerBIDesktopConnector()

        success = app_state.desktop_connector.connect()

        if success:
            return jsonify({
                "response": f"✅ Connected to Power BI Desktop!\n\n" +
                           f"Model: {app_state.desktop_connector.current_model_name}\n" +
                           f"Port: {app_state.desktop_connector.current_port}"
            })
        else:
            return jsonify({
                "response": "❌ Failed to connect. Is Power BI Desktop running with a .pbix open?"
            })

    except Exception as e:
        return jsonify({"response": f"❌ Error: {str(e)}"})


@desktop_bp.route('/connect_instance', methods=['POST'])
def connect_instance():
    """Connect to a specific Power BI Desktop instance by port."""
    try:
        data = request.get_json() or {}
        port = data.get('port')

        if not port:
            return jsonify({"response": "❌ No port specified"})

        port = int(port)

        if app_state.desktop_connector is None:
            app_state.desktop_connector = PowerBIDesktopConnector()

        success = app_state.desktop_connector.connect(port=port)

        if success:
            return jsonify({
                "response": f"✅ Connected to Power BI Desktop!\n\n" +
                           f"Model: {app_state.desktop_connector.current_model_name}\n" +
                           f"Port: {app_state.desktop_connector.current_port}"
            })
        else:
            return jsonify({
                "response": f"❌ Failed to connect to port {port}. Is the instance still running?"
            })

    except ValueError:
        return jsonify({"response": "❌ Invalid port number"})
    except Exception as e:
        return jsonify({"response": f"❌ Error: {str(e)}"})


@desktop_bp.route('/schema')
def get_schema():
    """Get the schema of the connected Power BI model."""
    try:
        if not app_state.is_desktop_connected:
            return jsonify({"response": "❌ Not connected. Click 'Connect to Power BI' first."})

        # Use comprehensive schema with all INFO views
        schema = app_state.desktop_connector.get_comprehensive_schema()
        app_state.model_schema = schema

        tables = schema.get('tables', [])
        table_schemas = schema.get('table_schemas', [])
        measures = schema.get('measures', [])
        relationships = schema.get('relationships', [])

        response = f"📊 **Schema for: {schema.get('model_name', 'Unknown')}**\n\n"

        # Tables with columns
        response += f"**Tables ({len(tables)}):**\n"
        for ts in table_schemas[:15]:
            table_name = ts.get('name', '')
            columns = ts.get('columns', [])
            response += f"  • `'{table_name}'`\n"
            if columns:
                cols_preview = ', '.join(columns[:8])
                if len(columns) > 8:
                    cols_preview += f", ... +{len(columns)-8} more"
                response += f"    Columns: {cols_preview}\n"

        if len(tables) > 15:
            response += f"  ... and {len(tables) - 15} more tables\n"

        # Measures
        response += f"\n**Measures ({len(measures)}):**\n"
        for m in measures[:15]:
            response += f"  • [{m.get('name')}]\n"
        if len(measures) > 15:
            response += f"  ... and {len(measures) - 15} more\n"

        # Relationships
        response += f"\n**Relationships ({len(relationships)}):**\n"
        for r in relationships[:10]:
            response += f"  • '{r.get('from_table')}'[{r.get('from_column')}] → '{r.get('to_table')}'[{r.get('to_column')}]\n"
        if len(relationships) > 10:
            response += f"  ... and {len(relationships) - 10} more\n"

        return jsonify({
            "response": response,
            "schema": {
                "tables": tables,
                "columns": len(schema.get('columns', [])),
                "measures": len(measures),
                "relationships": len(relationships)
            }
        })

    except Exception as e:
        logger.error(f"Schema error: {e}", exc_info=True)
        return jsonify({"response": f"❌ Error: {str(e)}"})


@desktop_bp.route('/tables')
def get_tables():
    """List all tables in the connected model."""
    try:
        if not app_state.is_desktop_connected:
            return jsonify({"response": "❌ Not connected. Click 'Connect to Power BI' first."})

        tables = app_state.desktop_connector.list_tables()

        response = f"📁 Tables ({len(tables)}):\n\n"
        for t in tables:
            response += f"  • {t['name']}\n"

        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"response": f"❌ Error: {str(e)}"})


@desktop_bp.route('/measures')
def get_measures():
    """List all measures in the connected model."""
    try:
        if not app_state.is_desktop_connected:
            return jsonify({"response": "❌ Not connected. Click 'Connect to Power BI' first."})

        measures = app_state.desktop_connector.list_measures()

        response = f"📐 Measures ({len(measures)}):\n\n"
        for m in measures:
            expr = m.get('expression', '')
            if len(expr) > 50:
                expr = expr[:50] + "..."
            response += f"  • {m['name']}\n    = {expr}\n"

        return jsonify({"response": response})

    except Exception as e:
        return jsonify({"response": f"❌ Error: {str(e)}"})


@desktop_bp.route('/execute_dax', methods=['POST'])
def execute_dax():
    """Execute a DAX query against the connected model."""
    try:
        if not app_state.is_desktop_connected:
            return jsonify({"success": False, "error": "Not connected to Power BI Desktop"})

        data = request.get_json() or {}
        dax_query = data.get('query', '').strip()

        if not dax_query:
            return jsonify({"success": False, "error": "No query provided"})

        result = app_state.desktop_connector.execute_dax(dax_query)

        return jsonify({
            "success": True,
            "result": result
        })

    except Exception as e:
        logger.error(f"DAX execution error: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)})
