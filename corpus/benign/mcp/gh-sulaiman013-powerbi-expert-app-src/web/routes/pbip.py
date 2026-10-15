"""
PBIP Routes
===========
API endpoints for PBIP (Power BI Project) file operations.
"""

import logging
from flask import Blueprint, jsonify, request

from src.connectors.pbip import PowerBIPBIPConnector
from ..services.state import app_state

logger = logging.getLogger("powerbi-v3-webui")
pbip_bp = Blueprint('pbip', __name__)


@pbip_bp.route('/pbip_load', methods=['POST'])
def pbip_load():
    """Load a PBIP project from a directory path."""
    try:
        data = request.get_json() or {}
        path = data.get('path', '').strip()

        if not path:
            return jsonify({
                "success": False,
                "message": "No path provided"
            })

        if app_state.pbip_connector is None:
            app_state.pbip_connector = PowerBIPBIPConnector(auto_backup=True)

        success = app_state.pbip_connector.load_project(path)

        if not success:
            return jsonify({
                "success": False,
                "message": f"Could not find a valid PBIP project at: {path}"
            })

        app_state.pbip_loaded = True
        project_info = app_state.pbip_connector.get_project_info()

        return jsonify({
            "success": True,
            "message": "PBIP project loaded successfully",
            "project_info": project_info
        })

    except Exception as e:
        logger.error(f"PBIP load error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })


@pbip_bp.route('/pbip_rename', methods=['POST'])
def pbip_rename():
    """Rename a table in the loaded PBIP project."""
    try:
        if not app_state.is_pbip_loaded:
            return jsonify({
                "success": False,
                "message": "No PBIP project loaded. Call /api/pbip_load first."
            })

        data = request.get_json() or {}
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()

        if not old_name or not new_name:
            return jsonify({
                "success": False,
                "message": "Both old_name and new_name are required"
            })

        result = app_state.pbip_connector.rename_table_in_files(old_name, new_name)

        if result.success:
            return jsonify({
                "success": True,
                "message": f"Renamed '{old_name}' to '{new_name}'",
                "files_modified": result.files_modified,
                "references_updated": result.references_updated
            })
        else:
            return jsonify({
                "success": False,
                "message": f"Rename failed: {result.error}",
                "files_modified": result.files_modified,
                "references_updated": result.references_updated
            })

    except Exception as e:
        logger.error(f"PBIP rename error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })


@pbip_bp.route('/pbip_batch_rename', methods=['POST'])
def pbip_batch_rename():
    """Batch rename tables, columns, or measures in the loaded PBIP project."""
    try:
        if not app_state.is_pbip_loaded:
            return jsonify({
                "success": False,
                "message": "No PBIP project loaded. Call /api/pbip_load first."
            })

        data = request.get_json() or {}
        renames = data.get('renames', [])

        if not renames:
            return jsonify({
                "success": False,
                "message": "No renames provided. Expected list of {old_name, new_name, type}"
            })

        # Separate renames by type
        table_renames = []
        column_renames = []
        measure_renames = []

        for r in renames:
            rename_type = r.get('type', 'table')
            if rename_type == 'column':
                # Map frontend 'table' to backend 'table_name'
                column_renames.append({
                    'table_name': r.get('table'),
                    'old_name': r.get('old_name'),
                    'new_name': r.get('new_name')
                })
            elif rename_type == 'measure':
                measure_renames.append({
                    'old_name': r.get('old_name'),
                    'new_name': r.get('new_name')
                })
            else:  # table (default)
                table_renames.append({
                    'old_name': r.get('old_name'),
                    'new_name': r.get('new_name')
                })

        # Execute renames by type and collect results
        all_results = []
        all_files = set()
        total_refs = 0
        messages = []

        if table_renames:
            result = app_state.pbip_connector.batch_rename_tables(table_renames)
            if result.details:
                all_results.extend(result.details.get("individual_results", []))
            all_files.update(result.files_modified)
            total_refs += result.references_updated
            messages.append(f"{len(table_renames)} table(s)")

        if column_renames:
            result = app_state.pbip_connector.batch_rename_columns(column_renames)
            if result.details:
                all_results.extend(result.details.get("individual_results", []))
            all_files.update(result.files_modified)
            total_refs += result.references_updated
            messages.append(f"{len(column_renames)} column(s)")

        if measure_renames:
            result = app_state.pbip_connector.batch_rename_measures(measure_renames)
            if result.details:
                all_results.extend(result.details.get("individual_results", []))
            all_files.update(result.files_modified)
            total_refs += result.references_updated
            messages.append(f"{len(measure_renames)} measure(s)")

        return jsonify({
            "success": True,
            "message": f"Renamed {', '.join(messages)}. Updated {total_refs} references in {len(all_files)} file(s).",
            "files_modified": list(all_files),
            "references_updated": total_refs,
            "results": all_results
        })

    except Exception as e:
        logger.error(f"PBIP batch rename error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })


@pbip_bp.route('/pbip_info')
def pbip_info():
    """Get information about the currently loaded PBIP project."""
    if not app_state.is_pbip_loaded:
        return jsonify({
            "loaded": False,
            "message": "No PBIP project loaded"
        })

    project_info = app_state.pbip_connector.get_project_info()

    return jsonify({
        "loaded": True,
        "project_info": project_info
    })


@pbip_bp.route('/pbip_schema', methods=['POST'])
def pbip_schema():
    """Get model schema (tables, columns, measures) from PBIP project."""
    try:
        data = request.get_json() or {}
        path = data.get('path', '').strip()

        # If path provided, load/reload the project
        if path:
            if app_state.pbip_connector is None:
                app_state.pbip_connector = PowerBIPBIPConnector(auto_backup=True)

            success = app_state.pbip_connector.load_project(path)
            if not success:
                return jsonify({
                    "success": False,
                    "message": f"Could not find a valid PBIP project at: {path}"
                })
            app_state.pbip_loaded = True

        # Check if project is loaded
        if not app_state.is_pbip_loaded:
            return jsonify({
                "success": False,
                "message": "No PBIP project loaded. Provide a path or call /api/pbip_load first."
            })

        # Get schema
        schema = app_state.pbip_connector.get_model_schema()

        return jsonify({
            "success": True,
            "schema": schema
        })

    except Exception as e:
        logger.error(f"PBIP schema error: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })
