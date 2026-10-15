"""
Cloud Routes
=============
API endpoints for Power BI Service (cloud) connectivity.
"""

import re
import logging
from flask import Blueprint, jsonify, request

from src.connectors.rest import PowerBIRestConnector
from src.connectors.xmla import PowerBIXmlaConnector
from ..services.state import app_state, CloudConnectionInfo

logger = logging.getLogger("powerbi-v3-webui")
cloud_bp = Blueprint('cloud', __name__)


def parse_powerbi_url(url: str) -> dict:
    """
    Parse a Power BI Service URL to extract workspace_id and dataset_id.

    Examples:
    - https://app.powerbi.com/groups/73c6b305-73d6-40b3-a2e8-d391285f6ef6/datasets/c5909392-a87a-47a1-83df-0096ef946225/details
    - https://app.powerbi.com/groups/{workspace_id}/datasets/{dataset_id}
    """
    pattern = r'groups/([a-f0-9-]+)/datasets/([a-f0-9-]+)'
    match = re.search(pattern, url, re.IGNORECASE)

    if match:
        return {
            'workspace_id': match.group(1),
            'dataset_id': match.group(2)
        }
    return None


@cloud_bp.route('/configure_pbi_service', methods=['POST'])
def configure_pbi_service():
    """Configure and connect to Power BI Service via XMLA."""
    logger.info("[CLOUD] === Power BI Service connection request received ===")
    try:
        data = request.json
        logger.info(f"[CLOUD] Received JSON data: {bool(data)}")

        tenant_id = data.get('tenant_id', '').strip()
        client_id = data.get('client_id', '').strip()
        client_secret = data.get('client_secret', '').strip()
        service_url = data.get('service_url', '').strip()

        logger.info(f"[CLOUD] Tenant ID: {tenant_id[:8]}...")
        logger.info(f"[CLOUD] Client ID: {client_id[:8]}...")
        logger.info(f"[CLOUD] Service URL: {service_url}")

        # Validate inputs
        if not all([tenant_id, client_id, client_secret, service_url]):
            logger.error("[CLOUD] Missing required fields")
            return jsonify({
                "success": False,
                "message": "All fields are required (Tenant ID, Client ID, Client Secret, Service URL)"
            })

        # Parse the Power BI URL
        url_parts = parse_powerbi_url(service_url)
        if not url_parts:
            logger.error("[CLOUD] Invalid Power BI URL format")
            return jsonify({
                "success": False,
                "message": "Invalid Power BI URL. Expected format: https://app.powerbi.com/groups/{workspace_id}/datasets/{dataset_id}/..."
            })

        workspace_id = url_parts['workspace_id']
        dataset_id = url_parts['dataset_id']

        logger.info(f"[CLOUD] Configuring Power BI Service connection...")
        logger.info(f"[CLOUD] Workspace ID: {workspace_id}")
        logger.info(f"[CLOUD] Dataset ID: {dataset_id}")

        # Step 1: Create REST connector and authenticate
        logger.info("[CLOUD] Step 1: Creating REST connector...")
        app_state.rest_connector = PowerBIRestConnector(tenant_id, client_id, client_secret)
        logger.info("[CLOUD] Step 1: Authenticating via REST API...")
        if not app_state.rest_connector.authenticate():
            logger.error("[CLOUD] Step 1 FAILED: REST API authentication failed")
            return jsonify({
                "success": False,
                "message": "REST API authentication failed. Check your Service Principal credentials."
            })
        logger.info("[CLOUD] Step 1 COMPLETE: REST API authentication successful")

        # Step 2: Get workspace name using REST API
        logger.info("[CLOUD] Step 2: Listing workspaces...")
        workspaces = app_state.rest_connector.list_workspaces()
        logger.info(f"[CLOUD] Step 2: Found {len(workspaces)} workspaces")
        workspace_name = None
        dataset_name = None

        for ws in workspaces:
            if ws['id'] == workspace_id:
                workspace_name = ws['name']
                logger.info(f"[CLOUD] Step 2: Found workspace '{workspace_name}', listing datasets...")
                datasets = app_state.rest_connector.list_datasets(workspace_id)
                logger.info(f"[CLOUD] Step 2: Found {len(datasets)} datasets")
                for ds in datasets:
                    if ds['id'] == dataset_id:
                        dataset_name = ds['name']
                        break
                break

        if not workspace_name:
            logger.error(f"[CLOUD] Step 2 FAILED: Workspace {workspace_id} not found")
            return jsonify({
                "success": False,
                "message": f"Workspace not found. The Service Principal may not have access to workspace {workspace_id}"
            })

        if not dataset_name:
            logger.error(f"[CLOUD] Step 2 FAILED: Dataset {dataset_id} not found")
            return jsonify({
                "success": False,
                "message": f"Dataset not found in workspace '{workspace_name}'. Check if the dataset ID is correct."
            })

        logger.info(f"[CLOUD] Step 2 COMPLETE: Found workspace: {workspace_name}")
        logger.info(f"[CLOUD] Step 2 COMPLETE: Found dataset: {dataset_name}")

        # Step 3: Create XMLA connector and connect
        logger.info("[CLOUD] Step 3: Creating XMLA connector...")
        app_state.xmla_connector = PowerBIXmlaConnector(tenant_id, client_id, client_secret)
        logger.info(f"[CLOUD] Step 3: Connecting to XMLA endpoint for '{dataset_name}'...")
        logger.info("[CLOUD] Step 3: (This may take 30-60 seconds...)")
        if not app_state.xmla_connector.connect(workspace_name, dataset_name):
            logger.error("[CLOUD] Step 3 FAILED: XMLA connection failed")
            return jsonify({
                "success": False,
                "message": f"XMLA connection failed to '{dataset_name}'. Ensure XMLA endpoint is enabled in Power BI tenant settings."
            })
        logger.info("[CLOUD] Step 3 COMPLETE: XMLA connection successful")

        # Step 4: Discover tables and build schema
        logger.info("[CLOUD] Step 4: Discovering tables...")
        tables = app_state.xmla_connector.discover_tables()
        logger.info(f"[CLOUD] Step 4: Found {len(tables)} tables")

        table_schemas = []
        columns = []
        for table in tables[:20]:
            schema = app_state.xmla_connector.get_table_schema(table['name'])
            table_columns = [col['name'] for col in schema.get('columns', [])]
            table_schemas.append({
                'name': table['name'],
                'columns': table_columns
            })
            # Also build columns list for compatibility
            for col in schema.get('columns', []):
                columns.append({
                    'table': table['name'],
                    'name': col['name'],
                    'data_type': col.get('type', '')
                })
        logger.info(f"[CLOUD] Step 4: Built schema for {len(table_schemas)} tables, {len(columns)} columns")

        # Step 5: Discover measures (same as desktop)
        logger.info("[CLOUD] Step 5: Discovering measures...")
        measures = app_state.xmla_connector.discover_measures()
        logger.info(f"[CLOUD] Step 5: Found {len(measures)} measures")

        # Step 6: Discover relationships (critical for USERELATIONSHIP support)
        logger.info("[CLOUD] Step 6: Discovering relationships...")
        relationships = app_state.xmla_connector.discover_relationships()
        logger.info(f"[CLOUD] Step 6: Found {len(relationships)} relationships")

        # Count inactive relationships for logging
        inactive_count = sum(1 for r in relationships if not r.get('is_active', True))
        if inactive_count > 0:
            logger.info(f"[CLOUD] Step 6: {inactive_count} INACTIVE relationships found (USERELATIONSHIP required)")

        logger.info(f"[CLOUD] Step 4-6 COMPLETE: Full schema discovery finished")

        app_state.cloud_model_schema = {
            'workspace_name': workspace_name,
            'dataset_name': dataset_name,
            'tables': [t['name'] for t in tables],
            'table_schemas': table_schemas,
            'columns': columns,
            'measures': measures,
            'relationships': relationships
        }

        app_state.cloud_connection_info = CloudConnectionInfo(
            workspace_id=workspace_id,
            workspace_name=workspace_name,
            dataset_id=dataset_id,
            dataset_name=dataset_name
        )

        app_state.cloud_connected = True

        details = f"• Workspace: {workspace_name}\n• Dataset: {dataset_name}\n• Tables: {len(tables)}"

        logger.info("[CLOUD] === Power BI Service connection SUCCESSFUL ===")
        return jsonify({
            "success": True,
            "message": f"Connected to '{dataset_name}' via XMLA",
            "details": details
        })

    except Exception as e:
        logger.error(f"[CLOUD] === Power BI Service config EXCEPTION: {e} ===", exc_info=True)
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })
