"""Dashboard CRUD tools for Grafana MCP server."""

from typing import Any

from .base import grafana_tool, get_current_client, handle_grafana_errors
from ..security.validators import SecurityValidator


@grafana_tool
def create_dashboard(cluster: str, dashboard_json: dict, *, folder_uid: str = "") -> dict[str, Any]:
    """Create a new Grafana dashboard with protection labels.
    
    Args:
        cluster: Target cluster name.
        dashboard_json: Dashboard configuration as JSON/dict.
        folder_uid: Optional folder UID where dashboard should be created.
        
    Returns:
        Created dashboard information including UID and URL.
        
    Raises:
        ValueError: If cluster is invalid, folder access denied, or dashboard already exists.
    """
    # Prepare dashboard with security requirements
    prepared_dashboard = SecurityValidator.prepare_dashboard_for_creation(dashboard_json, folder_uid)

    # Get the current client
    client = get_current_client()
    
    # Check if dashboard with this UID already exists
    if "uid" in prepared_dashboard and prepared_dashboard["uid"]:
        try:
            existing = client.get_dashboard(prepared_dashboard["uid"])
            if existing:
                raise ValueError(f"Dashboard with UID '{prepared_dashboard['uid']}' already exists")
        except Exception:
            # Dashboard doesn't exist, which is what we want
            pass

    # Create the dashboard
    result = client.create_dashboard(prepared_dashboard, folder_uid)
    return result


@grafana_tool
def read_dashboard(cluster: str, dashboard_uid: str) -> dict[str, Any]:
    """Read a Grafana dashboard by UID.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard.
        
    Returns:
        Dashboard configuration and metadata.
        
    Raises:
        ValueError: If cluster is invalid or dashboard not found.
    """
    client = get_current_client()
    result = client.get_dashboard(dashboard_uid)
    dashboard = result.get("dashboard", {})
    SecurityValidator.validate_dashboard_for_read(dashboard)
    return result


@grafana_tool
def update_dashboard(cluster: str, dashboard_uid: str, dashboard_json: dict) -> dict[str, Any]:
    """Update an existing Grafana dashboard.
    
    Only dashboards with required protection labels can be updated.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard to update.
        dashboard_json: Updated dashboard configuration.
        
    Returns:
        Updated dashboard information.
        
    Raises:
        ValueError: If cluster is invalid, dashboard not found, or missing protection labels.
    """
    client = get_current_client()
    # Get existing dashboard to validate labels
    existing = client.get_dashboard(dashboard_uid)
    existing_dashboard = existing.get("dashboard", {})
    existing_meta = existing.get("meta", {})

    # Validate that existing dashboard has protection tags
    SecurityValidator.validate_dashboard_for_write(existing_dashboard, "update")

    # Prepare updated dashboard
    updated_dashboard = dashboard_json.copy()
    updated_dashboard["uid"] = dashboard_uid

    # Get existing folder to preserve it
    existing_folder_uid = existing_meta.get("folderUid", "")

    # Ensure protection tags are maintained
    prepared_dashboard = SecurityValidator.prepare_dashboard_for_update(updated_dashboard, existing_folder_uid)

    # Update the dashboard (preserve existing folder)
    result = client.update_dashboard(prepared_dashboard, existing_folder_uid)
    return result


@grafana_tool
def delete_dashboard(cluster: str, dashboard_uid: str) -> dict[str, Any]:
    """Delete a Grafana dashboard.
    
    Only dashboards with required protection labels can be deleted.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard to delete.
        
    Returns:
        Deletion confirmation.
        
    Raises:
        ValueError: If cluster is invalid, dashboard not found, or missing protection labels.
    """
    client = get_current_client()
    # Get existing dashboard to validate labels
    existing = client.get_dashboard(dashboard_uid)
    existing_dashboard = existing.get("dashboard", {})

    # Validate that dashboard has protection tags
    SecurityValidator.validate_dashboard_for_write(existing_dashboard, "delete")

    # Delete the dashboard
    result = client.delete_dashboard(dashboard_uid)
    return result


@grafana_tool
def search(
        cluster: str,
        *,
        query: str = "",
        tags: list = [],
        starred: bool = False,
        folder_uids: list = [],
        dashboard_uids: list = [],
        dashboard_ids: list = [],
        type: str = "",
        limit: int = 1000,
        page: int = 1
) -> list[dict[str, Any]]:
    """Search for dashboards and folders with comprehensive filtering options.
    
    Args:
        cluster: Target cluster name.
        query: Search query string for titles.
        tags: List of tags to filter by.
        starred: Filter only starred items.
        folder_uids: List of folder UIDs to search within.
        dashboard_uids: List of specific dashboard UIDs to return.
        dashboard_ids: List of specific dashboard IDs to return.
        type: Filter by type ("dash-db" for dashboards, "dash-folder" for folders, "" for all).
        limit: Maximum number of results (max 5000, default 1000).
        page: Page number for pagination.
        
    Returns:
        List of matching dashboards and folders.
        
    Raises:
        ValueError: If cluster is invalid or parameters are invalid.
    """
    client = get_current_client()
    # Validate limit
    if limit > 5000:
        limit = 5000
    if limit < 1:
        limit = 1000

    # Validate page
    if page < 1:
        page = 1

    result = client.search_dashboards(
        query=query,
        tags=tags if tags else None,
        starred=starred if starred else None,
        folder_uids=folder_uids if folder_uids else None,
        dashboard_uids=dashboard_uids if dashboard_uids else None,
        dashboard_ids=dashboard_ids if dashboard_ids else None,
        type_filter=type,
        limit=limit,
        page=page
    )
    
    # Filter results based on read access tags
    filtered_results = []
    for item in result:
        if item.get("type") == "dash-db":  # Dashboard
            try:
                # Fetch full dashboard to validate tags
                dashboard_result = client.get_dashboard(item["uid"])
                dashboard = dashboard_result.get("dashboard", {})
                SecurityValidator.validate_dashboard_for_read(dashboard)
                filtered_results.append(item)
            except ValueError:
                # Unauthorized - exclude from results
                continue
        else:  # Folder or other
            filtered_results.append(item)
    
    return filtered_results




@grafana_tool
def inspect_dashboard(cluster: str, dashboard_uid: str) -> dict[str, Any]:
    """Inspect a Grafana dashboard structure and provide detailed analysis.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard to inspect.
        
    Returns:
        Detailed inspection report including panels, datasources, variables, and metadata.
        
    Raises:
        ValueError: If cluster is invalid or dashboard not found.
    """
    client = get_current_client()
    
    # Get dashboard data
    dashboard_result = client.get_dashboard(dashboard_uid)
    dashboard = dashboard_result.get("dashboard", {})
    meta = dashboard_result.get("meta", {})
    
    if not dashboard:
        raise ValueError(f"Dashboard with UID '{dashboard_uid}' not found")
    
    # Validate read access
    SecurityValidator.validate_dashboard_for_read(dashboard)
    
    # Get available datasources for validation
    try:
        datasources = client.list_datasources()
        datasource_map = {ds.get("uid"): ds for ds in datasources}
        datasource_names = {ds.get("uid"): ds.get("name", "Unknown") for ds in datasources}
    except Exception:
        datasources = []
        datasource_map = {}
        datasource_names = {}
    
    # Extract basic dashboard info
    inspection_result = {
        "dashboard": {
            "uid": dashboard.get("uid"),
            "title": dashboard.get("title"),
            "description": dashboard.get("description", ""),
            "tags": dashboard.get("tags", []),
            "version": dashboard.get("version"),
            "created": meta.get("created"),
            "updated": meta.get("updated"),
            "folder_uid": meta.get("folderUid", ""),
            "folder_title": meta.get("folderTitle", ""),
            "editable": dashboard.get("editable", True),
            "refresh": dashboard.get("refresh", "")
        },
        "time_settings": {
            "from": dashboard.get("time", {}).get("from", ""),
            "to": dashboard.get("time", {}).get("to", ""),
            "timezone": dashboard.get("timezone", "browser")
        },
        "variables": [],
        "panels": [],
        "datasources_used": {},
        "validation_issues": []
    }
    
    # Extract template variables
    templating = dashboard.get("templating", {})
    if templating and "list" in templating:
        for var in templating["list"]:
            var_info = {
                "name": var.get("name"),
                "type": var.get("type"),
                "label": var.get("label", ""),
                "datasource": var.get("datasource"),
                "query": var.get("query", ""),
                "multi": var.get("multi", False),
                "includeAll": var.get("includeAll", False),
                "current": var.get("current", {})
            }
            inspection_result["variables"].append(var_info)
    
    # Extract panel information
    panels = dashboard.get("panels", [])
    for panel in panels:
        panel_info = {
            "id": panel.get("id"),
            "title": panel.get("title", ""),
            "type": panel.get("type", ""),
            "description": panel.get("description", ""),
            "gridPos": panel.get("gridPos", {}),
            "datasource": None,
            "queries": [],
            "field_config": panel.get("fieldConfig", {}),
            "options": panel.get("options", {}),
            "transformations": panel.get("transformations", [])
        }
        
        # Extract datasource info
        panel_datasource = panel.get("datasource")
        if panel_datasource:
            if isinstance(panel_datasource, dict):
                ds_uid = panel_datasource.get("uid")
                panel_info["datasource"] = {
                    "uid": ds_uid,
                    "type": panel_datasource.get("type"),
                    "name": datasource_names.get(ds_uid, "Unknown")
                }
                if ds_uid:
                    inspection_result["datasources_used"][ds_uid] = datasource_names.get(ds_uid, "Unknown")
            else:
                panel_info["datasource"] = str(panel_datasource)
        
        # Extract queries
        targets = panel.get("targets", [])
        for target in targets:
            query_info = {
                "refId": target.get("refId"),
                "datasource": target.get("datasource"),
                "hide": target.get("hide", False),
                "query_type": target.get("queryType", ""),
                "expr": target.get("expr", ""),
                "rawSql": target.get("rawSql", ""),
                "query": target.get("query", ""),
                "builder": target.get("builder", {}),
                "format": target.get("format", ""),
                "intervalMs": target.get("intervalMs"),
                "maxDataPoints": target.get("maxDataPoints")
            }
            
            # Extract key fields based on datasource type
            for key in ["sql", "table", "database", "interval", "step"]:
                if key in target:
                    query_info[key] = target[key]
            
            panel_info["queries"].append(query_info)
        
        inspection_result["panels"].append(panel_info)
    
    # Validate datasource references
    for panel in inspection_result["panels"]:
        if panel["datasource"] and isinstance(panel["datasource"], dict):
            ds_uid = panel["datasource"]["uid"]
            if ds_uid and ds_uid not in datasource_map:
                inspection_result["validation_issues"].append({
                    "type": "missing_datasource",
                    "panel_id": panel["id"],
                    "panel_title": panel["title"],
                    "datasource_uid": ds_uid,
                    "message": f"Panel '{panel['title']}' references missing datasource UID: {ds_uid}"
                })
    
    # Check for overlapping panels
    grid_positions = {}
    for panel in inspection_result["panels"]:
        grid_pos = panel["gridPos"]
        if grid_pos:
            x, y = grid_pos.get("x", 0), grid_pos.get("y", 0)
            w, h = grid_pos.get("w", 12), grid_pos.get("h", 8)
            
            # Simple overlap detection
            for existing_pos, existing_panel in grid_positions.items():
                ex_x, ex_y, ex_w, ex_h = existing_pos
                if (x < ex_x + ex_w and x + w > ex_x and y < ex_y + ex_h and y + h > ex_y):
                    inspection_result["validation_issues"].append({
                        "type": "overlapping_panels",
                        "panel_id": panel["id"],
                        "panel_title": panel["title"],
                        "conflicting_panel": existing_panel["title"],
                        "message": f"Panel '{panel['title']}' overlaps with '{existing_panel['title']}'"
                    })
            
            grid_positions[(x, y, w, h)] = panel
    
    # Summary statistics
    inspection_result["summary"] = {
        "total_panels": len(inspection_result["panels"]),
        "total_variables": len(inspection_result["variables"]),
        "unique_datasources": len(inspection_result["datasources_used"]),
        "validation_issues": len(inspection_result["validation_issues"]),
        "panel_types": list(set(p["type"] for p in inspection_result["panels"])),
        "variable_types": list(set(v["type"] for v in inspection_result["variables"]))
    }
    
    return inspection_result


@grafana_tool
def validate_dashboard(cluster: str, dashboard_uid: str) -> dict[str, Any]:
    """Validate a Grafana dashboard against schema and best practices.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard to validate.
        
    Returns:
        Validation report with pass/fail status and detailed issues.
        
    Raises:
        ValueError: If cluster is invalid or dashboard not found.
    """
    client = get_current_client()
    
    # Get dashboard data
    dashboard_result = client.get_dashboard(dashboard_uid)
    dashboard = dashboard_result.get("dashboard", {})
    meta = dashboard_result.get("meta", {})
    
    if not dashboard:
        raise ValueError(f"Dashboard with UID '{dashboard_uid}' not found")
    
    # Validate read access
    SecurityValidator.validate_dashboard_for_read(dashboard)
    
    validation_result = {
        "dashboard_uid": dashboard_uid,
        "dashboard_title": dashboard.get("title", ""),
        "validation_status": "PASS",
        "issues": [],
        "warnings": [],
        "info": [],
        "summary": {}
    }
    
    def add_issue(level: str, category: str, message: str, panel_id: str = None):
        """Helper to add validation issues."""
        issue = {
            "level": level,
            "category": category,
            "message": message
        }
        if panel_id:
            issue["panel_id"] = panel_id
        
        if level == "ERROR":
            validation_result["issues"].append(issue)
            validation_result["validation_status"] = "FAIL"
        elif level == "WARNING":
            validation_result["warnings"].append(issue)
        else:
            validation_result["info"].append(issue)
    
    # Schema validation
    required_fields = ["uid", "title", "panels"]
    for field in required_fields:
        if field not in dashboard or not dashboard[field]:
            add_issue("ERROR", "schema", f"Required field '{field}' is missing or empty")
    
    # Validate UID format
    uid = dashboard.get("uid")
    if uid and (len(uid) < 1 or len(uid) > 40):
        add_issue("ERROR", "schema", f"Dashboard UID '{uid}' length must be between 1 and 40 characters")
    
    # Validate title
    title = dashboard.get("title", "")
    if not title:
        add_issue("ERROR", "schema", "Dashboard title is required")
    elif len(title) > 255:
        add_issue("WARNING", "schema", f"Dashboard title is very long ({len(title)} characters)")
    
    # Validate time settings
    time_settings = dashboard.get("time", {})
    if not time_settings.get("from") or not time_settings.get("to"):
        add_issue("WARNING", "time", "Time range (from/to) should be specified")
    
    # Validate panels
    panels = dashboard.get("panels", [])
    if not panels:
        add_issue("WARNING", "content", "Dashboard has no panels")
    
    panel_ids = set()
    grid_positions = {}
    
    for panel in panels:
        panel_id = panel.get("id")
        panel_title = panel.get("title", f"Panel {panel_id}")
        
        # Validate panel ID
        if panel_id is None:
            add_issue("ERROR", "panel", f"Panel '{panel_title}' is missing ID")
        elif panel_id in panel_ids:
            add_issue("ERROR", "panel", f"Duplicate panel ID: {panel_id}")
        else:
            panel_ids.add(panel_id)
        
        # Validate panel type
        panel_type = panel.get("type")
        if not panel_type:
            add_issue("ERROR", "panel", f"Panel '{panel_title}' is missing type", str(panel_id))
        
        # Validate grid position
        grid_pos = panel.get("gridPos", {})
        if not grid_pos:
            add_issue("WARNING", "layout", f"Panel '{panel_title}' has no grid position", str(panel_id))
        else:
            x, y = grid_pos.get("x", 0), grid_pos.get("y", 0)
            w, h = grid_pos.get("w", 12), grid_pos.get("h", 8)
            
            # Validate grid values
            if w <= 0 or w > 24:
                add_issue("ERROR", "layout", f"Panel '{panel_title}' has invalid width: {w}", str(panel_id))
            if h <= 0:
                add_issue("ERROR", "layout", f"Panel '{panel_title}' has invalid height: {h}", str(panel_id))
            if x < 0 or x >= 24:
                add_issue("ERROR", "layout", f"Panel '{panel_title}' has invalid x position: {x}", str(panel_id))
            if y < 0:
                add_issue("ERROR", "layout", f"Panel '{panel_title}' has invalid y position: {y}", str(panel_id))
            
            # Check for overlapping panels
            for existing_pos, existing_panel in grid_positions.items():
                ex_x, ex_y, ex_w, ex_h = existing_pos
                if (x < ex_x + ex_w and x + w > ex_x and y < ex_y + ex_h and y + h > ex_y):
                    add_issue("ERROR", "layout", 
                             f"Panel '{panel_title}' overlaps with '{existing_panel}'", str(panel_id))
            
            grid_positions[(x, y, w, h)] = panel_title
        
        # Validate datasource
        datasource = panel.get("datasource")
        if not datasource:
            add_issue("WARNING", "datasource", f"Panel '{panel_title}' has no datasource", str(panel_id))
        
        # Validate queries
        targets = panel.get("targets", [])
        if not targets:
            add_issue("WARNING", "query", f"Panel '{panel_title}' has no queries", str(panel_id))
        else:
            ref_ids = set()
            for target in targets:
                ref_id = target.get("refId")
                if not ref_id:
                    add_issue("ERROR", "query", f"Query in panel '{panel_title}' is missing refId", str(panel_id))
                elif ref_id in ref_ids:
                    add_issue("ERROR", "query", f"Duplicate refId '{ref_id}' in panel '{panel_title}'", str(panel_id))
                else:
                    ref_ids.add(ref_id)
    
    # Validate template variables
    templating = dashboard.get("templating", {})
    if templating and "list" in templating:
        var_names = set()
        for var in templating["list"]:
            var_name = var.get("name")
            if not var_name:
                add_issue("ERROR", "variable", "Template variable is missing name")
            elif var_name in var_names:
                add_issue("ERROR", "variable", f"Duplicate variable name: {var_name}")
            else:
                var_names.add(var_name)
            
            # Validate variable type
            var_type = var.get("type")
            valid_types = {"query", "custom", "constant", "datasource", "interval", "textbox", "adhoc"}
            if var_type not in valid_types:
                add_issue("WARNING", "variable", f"Variable '{var_name}' has unknown type: {var_type}")
    
    # Best practices validation
    if len(panels) > 30:
        add_issue("INFO", "performance", f"Dashboard has many panels ({len(panels)}). Consider splitting into multiple dashboards.")
    
    # Check refresh rate
    refresh = dashboard.get("refresh")
    if refresh:
        if refresh in {"5s", "10s"}:
            add_issue("WARNING", "performance", f"Very frequent refresh rate ({refresh}) may impact performance")
    
    # Validate annotations
    annotations = dashboard.get("annotations", {})
    if annotations and "list" in annotations:
        for annotation in annotations["list"]:
            if not annotation.get("datasource"):
                add_issue("WARNING", "annotation", "Annotation is missing datasource")
    
    # Summary
    validation_result["summary"] = {
        "total_panels": len(panels),
        "total_variables": len(templating.get("list", [])) if templating else 0,
        "total_issues": len(validation_result["issues"]),
        "total_warnings": len(validation_result["warnings"]),
        "total_info": len(validation_result["info"]),
        "validation_status": validation_result["validation_status"]
    }
    
    return validation_result


@grafana_tool
def snapshot_dashboard(
    cluster: str,
    dashboard_uid: str,
    *,
    snapshot_name: str = "",
    expires_hours: int = 24,
    time_from: str = "now-6h",
    time_to: str = "now"
) -> dict[str, Any]:
    """Create a dashboard snapshot with current data for inspection and testing.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard to snapshot.
        snapshot_name: Optional name for the snapshot.
        expires_hours: Hours until snapshot expires (default 24, 0 = never expires).
        time_from: Time range start (e.g., "now-6h", "2023-01-01T00:00:00Z").
        time_to: Time range end (e.g., "now", "2023-01-01T23:59:59Z").
        
    Returns:
        Snapshot information including key and URL for viewing.
        
    Raises:
        ValueError: If cluster is invalid or dashboard not found.
    """
    client = get_current_client()
    
    # Get dashboard data
    dashboard_result = client.get_dashboard(dashboard_uid)
    dashboard = dashboard_result.get("dashboard", {})
    
    if not dashboard:
        raise ValueError(f"Dashboard with UID '{dashboard_uid}' not found")
    
    # Validate read access
    SecurityValidator.validate_dashboard_for_read(dashboard)
    
    # Prepare dashboard for snapshot
    snapshot_dashboard = dashboard.copy()
    
    # Override time range if specified
    if time_from != "now-6h" or time_to != "now":
        snapshot_dashboard["time"] = {
            "from": time_from,
            "to": time_to
        }
    
    # Generate snapshot name if not provided
    if not snapshot_name:
        dashboard_title = dashboard.get("title", "Dashboard")
        snapshot_name = f"{dashboard_title} - Snapshot"
    
    # Calculate expiry (convert hours to seconds)
    expires_seconds = expires_hours * 3600 if expires_hours > 0 else 0
    
    # Create snapshot
    try:
        snapshot_result = client.create_snapshot(
            dashboard_json=snapshot_dashboard,
            name=snapshot_name,
            expires=expires_seconds
        )
        
        # Add additional metadata to result
        snapshot_result["dashboard_uid"] = dashboard_uid
        snapshot_result["dashboard_title"] = dashboard.get("title", "")
        snapshot_result["time_range"] = {
            "from": time_from,
            "to": time_to
        }
        snapshot_result["expires_hours"] = expires_hours
        
        return snapshot_result
        
    except Exception as e:
        raise ValueError(f"Failed to create snapshot: {str(e)}")


@grafana_tool
def test_panel_render(
    cluster: str,
    dashboard_uid: str,
    panel_id: int,
    *,
    width: int = 1000,
    height: int = 500,
    time_from: str = "now-6h",
    time_to: str = "now",
    save_to_file: str = ""
) -> dict[str, Any]:
    """Render a specific dashboard panel as PNG for visual validation.
    
    Args:
        cluster: Target cluster name.
        dashboard_uid: Unique identifier of the dashboard.
        panel_id: ID of the panel to render.
        width: Image width in pixels (max 3000).
        height: Image height in pixels (max 3000).
        time_from: Time range start (e.g., "now-6h").
        time_to: Time range end (e.g., "now").
        save_to_file: Optional file path to save the rendered image.
        
    Returns:
        Information about the rendered panel including size and optionally file path.
        
    Raises:
        ValueError: If cluster is invalid, dashboard not found, or render fails.
    """
    client = get_current_client()
    
    # Validate parameters
    if width > 3000:
        width = 3000
    if height > 3000:
        height = 3000
    if width < 100:
        width = 100
    if height < 100:
        height = 100
    
    # Verify dashboard exists and validate read access
    try:
        dashboard_result = client.get_dashboard(dashboard_uid)
        dashboard = dashboard_result.get("dashboard", {})
        if not dashboard:
            raise ValueError(f"Dashboard with UID '{dashboard_uid}' not found")
        SecurityValidator.validate_dashboard_for_read(dashboard)
    except Exception as e:
        raise ValueError(f"Failed to get dashboard: {str(e)}")
    
    # Find panel info
    panels = dashboard.get("panels", [])
    panel_info = None
    for panel in panels:
        if panel.get("id") == panel_id:
            panel_info = panel
            break
    
    if not panel_info:
        raise ValueError(f"Panel with ID {panel_id} not found in dashboard")
    
    try:
        # Render panel
        image_data = client.render_dashboard_panel(
            uid=dashboard_uid,
            panel_id=panel_id,
            width=width,
            height=height,
            from_time=time_from,
            to_time=time_to
        )
        
        result = {
            "dashboard_uid": dashboard_uid,
            "dashboard_title": dashboard.get("title", ""),
            "panel_id": panel_id,
            "panel_title": panel_info.get("title", ""),
            "panel_type": panel_info.get("type", ""),
            "dimensions": {
                "width": width,
                "height": height
            },
            "time_range": {
                "from": time_from,
                "to": time_to
            },
            "image_size_bytes": len(image_data)
        }
        
        # Save to file if requested
        if save_to_file:
            try:
                with open(save_to_file, "wb") as f:
                    f.write(image_data)
                result["saved_to"] = save_to_file
                result["message"] = f"Panel rendered and saved to {save_to_file}"
            except Exception as e:
                result["save_error"] = f"Failed to save file: {str(e)}"
                result["message"] = f"Panel rendered successfully but failed to save: {str(e)}"
        else:
            result["message"] = f"Panel rendered successfully ({len(image_data)} bytes)"
        
        return result
        
    except Exception as e:
        raise ValueError(f"Failed to render panel: {str(e)}")


@grafana_tool
def compare_dashboards(
    cluster: str,
    dashboard_uid_a: str,
    dashboard_uid_b: str,
    *,
    compare_cluster_b: str = ""
) -> dict[str, Any]:
    """Compare two dashboards and show differences in structure and configuration.
    
    Args:
        cluster: Target cluster name for dashboard A.
        dashboard_uid_a: UID of the first dashboard to compare.
        dashboard_uid_b: UID of the second dashboard to compare.
        compare_cluster_b: Optional cluster for dashboard B (defaults to same cluster).
        
    Returns:
        Detailed comparison report showing differences between the dashboards.
        
    Raises:
        ValueError: If cluster is invalid or dashboards not found.
    """
    from ..config import config
    from ..client import create_client
    
    # Get dashboard A
    client_a = get_current_client()
    try:
        result_a = client_a.get_dashboard(dashboard_uid_a)
        dashboard_a = result_a.get("dashboard", {})
        meta_a = result_a.get("meta", {})
        SecurityValidator.validate_dashboard_for_read(dashboard_a)
    except Exception as e:
        raise ValueError(f"Failed to get dashboard A '{dashboard_uid_a}': {str(e)}")
    
    # Get dashboard B (may be from different cluster)
    if compare_cluster_b and compare_cluster_b != cluster:
        config.validate_cluster(compare_cluster_b)
        with create_client(compare_cluster_b) as client_b:
            try:
                result_b = client_b.get_dashboard(dashboard_uid_b)
                dashboard_b = result_b.get("dashboard", {})
                meta_b = result_b.get("meta", {})
                SecurityValidator.validate_dashboard_for_read(dashboard_b)
            except Exception as e:
                raise ValueError(f"Failed to get dashboard B '{dashboard_uid_b}' from cluster '{compare_cluster_b}': {str(e)}")
    else:
        try:
            result_b = client_a.get_dashboard(dashboard_uid_b)
            dashboard_b = result_b.get("dashboard", {})
            meta_b = result_b.get("meta", {})
            SecurityValidator.validate_dashboard_for_read(dashboard_b)
        except Exception as e:
            raise ValueError(f"Failed to get dashboard B '{dashboard_uid_b}': {str(e)}")
    
    comparison_result = {
        "dashboard_a": {
            "uid": dashboard_a.get("uid"),
            "title": dashboard_a.get("title"),
            "cluster": cluster,
            "version": dashboard_a.get("version"),
            "updated": meta_a.get("updated")
        },
        "dashboard_b": {
            "uid": dashboard_b.get("uid"),
            "title": dashboard_b.get("title"),
            "cluster": compare_cluster_b if compare_cluster_b else cluster,
            "version": dashboard_b.get("version"),
            "updated": meta_b.get("updated")
        },
        "differences": [],
        "summary": {}
    }
    
    def add_difference(category: str, field: str, value_a, value_b, description: str = ""):
        """Helper to add differences."""
        diff = {
            "category": category,
            "field": field,
            "value_a": value_a,
            "value_b": value_b,
            "description": description or f"Field '{field}' differs"
        }
        comparison_result["differences"].append(diff)
    
    # Compare basic properties
    basic_fields = ["title", "description", "tags", "editable", "refresh"]
    for field in basic_fields:
        val_a = dashboard_a.get(field)
        val_b = dashboard_b.get(field)
        if val_a != val_b:
            add_difference("basic", field, val_a, val_b)
    
    # Compare time settings
    time_a = dashboard_a.get("time", {})
    time_b = dashboard_b.get("time", {})
    for time_field in ["from", "to"]:
        if time_a.get(time_field) != time_b.get(time_field):
            add_difference("time", time_field, time_a.get(time_field), time_b.get(time_field))
    
    # Compare timezone
    tz_a = dashboard_a.get("timezone", "browser")
    tz_b = dashboard_b.get("timezone", "browser")
    if tz_a != tz_b:
        add_difference("time", "timezone", tz_a, tz_b)
    
    # Compare template variables
    vars_a = dashboard_a.get("templating", {}).get("list", [])
    vars_b = dashboard_b.get("templating", {}).get("list", [])
    
    vars_a_map = {var.get("name"): var for var in vars_a}
    vars_b_map = {var.get("name"): var for var in vars_b}
    
    # Variables only in A
    for var_name in vars_a_map:
        if var_name not in vars_b_map:
            add_difference("variables", f"variable_{var_name}", "present", "missing", 
                         f"Variable '{var_name}' exists only in dashboard A")
    
    # Variables only in B
    for var_name in vars_b_map:
        if var_name not in vars_a_map:
            add_difference("variables", f"variable_{var_name}", "missing", "present",
                         f"Variable '{var_name}' exists only in dashboard B")
    
    # Variables in both - compare properties
    for var_name in vars_a_map:
        if var_name in vars_b_map:
            var_a = vars_a_map[var_name]
            var_b = vars_b_map[var_name]
            for var_field in ["type", "query", "datasource", "multi", "includeAll"]:
                if var_a.get(var_field) != var_b.get(var_field):
                    add_difference("variables", f"variable_{var_name}_{var_field}",
                                 var_a.get(var_field), var_b.get(var_field),
                                 f"Variable '{var_name}' {var_field} differs")
    
    # Compare panels
    panels_a = dashboard_a.get("panels", [])
    panels_b = dashboard_b.get("panels", [])
    
    panels_a_map = {panel.get("id"): panel for panel in panels_a}
    panels_b_map = {panel.get("id"): panel for panel in panels_b}
    
    # Panels only in A
    for panel_id in panels_a_map:
        if panel_id not in panels_b_map:
            panel_title = panels_a_map[panel_id].get("title", f"Panel {panel_id}")
            add_difference("panels", f"panel_{panel_id}", "present", "missing",
                         f"Panel '{panel_title}' (ID: {panel_id}) exists only in dashboard A")
    
    # Panels only in B
    for panel_id in panels_b_map:
        if panel_id not in panels_a_map:
            panel_title = panels_b_map[panel_id].get("title", f"Panel {panel_id}")
            add_difference("panels", f"panel_{panel_id}", "missing", "present",
                         f"Panel '{panel_title}' (ID: {panel_id}) exists only in dashboard B")
    
    # Panels in both - compare properties
    for panel_id in panels_a_map:
        if panel_id in panels_b_map:
            panel_a = panels_a_map[panel_id]
            panel_b = panels_b_map[panel_id]
            panel_title = panel_a.get("title", f"Panel {panel_id}")
            
            # Compare basic panel properties
            for panel_field in ["title", "type", "description"]:
                if panel_a.get(panel_field) != panel_b.get(panel_field):
                    add_difference("panels", f"panel_{panel_id}_{panel_field}",
                                 panel_a.get(panel_field), panel_b.get(panel_field),
                                 f"Panel '{panel_title}' {panel_field} differs")
            
            # Compare grid position
            grid_a = panel_a.get("gridPos", {})
            grid_b = panel_b.get("gridPos", {})
            for grid_field in ["x", "y", "w", "h"]:
                if grid_a.get(grid_field) != grid_b.get(grid_field):
                    add_difference("layout", f"panel_{panel_id}_grid_{grid_field}",
                                 grid_a.get(grid_field), grid_b.get(grid_field),
                                 f"Panel '{panel_title}' grid position {grid_field} differs")
            
            # Compare datasource
            ds_a = panel_a.get("datasource")
            ds_b = panel_b.get("datasource")
            if ds_a != ds_b:
                add_difference("datasource", f"panel_{panel_id}_datasource", ds_a, ds_b,
                             f"Panel '{panel_title}' datasource differs")
            
            # Compare number of queries
            targets_a = panel_a.get("targets", [])
            targets_b = panel_b.get("targets", [])
            if len(targets_a) != len(targets_b):
                add_difference("queries", f"panel_{panel_id}_query_count",
                             len(targets_a), len(targets_b),
                             f"Panel '{panel_title}' has different number of queries")
    
    # Summary statistics
    comparison_result["summary"] = {
        "total_differences": len(comparison_result["differences"]),
        "categories": list(set(diff["category"] for diff in comparison_result["differences"])),
        "panels_a": len(panels_a),
        "panels_b": len(panels_b),
        "variables_a": len(vars_a),
        "variables_b": len(vars_b),
        "dashboards_identical": len(comparison_result["differences"]) == 0
    }
    
    return comparison_result


@handle_grafana_errors
def copy_dashboard(
        source_cluster: str,
        source_uid: str,
        new_title: str,
        *,
        target_cluster: str = "",
        folder_uid: str = "",
        target_uid: str = ""
) -> dict[str, Any]:
    """Copy an existing dashboard, creating or updating the target with protection labels.
    
    If a dashboard with the target UID already exists, it will be updated/overwritten 
    provided the security prerequisites are met (matching protection labels).
    
    Args:
        source_cluster: Source cluster name where the dashboard exists.
        source_uid: UID of the dashboard to copy.
        new_title: Title for the new dashboard.
        target_cluster: Target cluster name where dashboard should be created. If empty, uses source_cluster.
        folder_uid: Optional folder UID where new dashboard should be created.
        target_uid: Optional target UID for the new dashboard. If not provided:
                    - Same cluster: generates new UID automatically
                    - Cross-cluster: preserves source UID
        
    Returns:
        Created or updated dashboard information.
        
    Raises:
        ValueError: If cluster is invalid, source dashboard not found, folder access denied,
                   or target dashboard exists but lacks required protection labels.
    """
    from ..config import config
    from ..client import create_client
    
    # Validate clusters
    config.validate_cluster(source_cluster)
    target_cluster_name = target_cluster if target_cluster else source_cluster
    config.validate_cluster(target_cluster_name)
    
    # Determine if this is a cross-cluster copy
    is_cross_cluster = target_cluster_name != source_cluster
    
    # Get source dashboard from source cluster
    with create_client(source_cluster) as source_client:
        source_result = source_client.get_dashboard(source_uid)
        source_dashboard = source_result.get("dashboard", {})

        if not source_dashboard:
            raise ValueError(f"Source dashboard with UID '{source_uid}' not found")

        # If no folder specified, inherit from source dashboard
        target_folder_uid = folder_uid
        if not target_folder_uid:
            source_meta = source_result.get("meta", {})
            target_folder_uid = source_meta.get("folderUid", "")

    # Determine target UID logic
    if target_uid:
        # Explicit target UID provided
        use_target_uid = target_uid
    elif is_cross_cluster:
        # Cross-cluster copy: preserve source UID by default
        use_target_uid = source_uid
    else:
        # Same cluster copy: generate new UID
        use_target_uid = ""

    # Prepare dashboard for copying
    new_dashboard = SecurityValidator.copy_dashboard_for_creation(
        source_dashboard, new_title, target_folder_uid, use_target_uid
    )

    # Create or update dashboard on target cluster
    with create_client(target_cluster_name) as target_client:
        # Check if target dashboard already exists
        target_dashboard_uid = new_dashboard.get("uid")
        existing_dashboard = None
        
        if target_dashboard_uid:
            try:
                existing_result = target_client.get_dashboard(target_dashboard_uid)
                existing_dashboard = existing_result.get("dashboard", {})
            except Exception:
                # Dashboard doesn't exist, proceed with creation
                pass
        
        if existing_dashboard:
            # Dashboard exists - validate security tags and update
            SecurityValidator.validate_dashboard_for_write(existing_dashboard, "update")
            
            # Ensure protection tags are maintained
            prepared_dashboard = SecurityValidator.prepare_dashboard_for_update(new_dashboard, target_folder_uid)
            result = target_client.update_dashboard(prepared_dashboard, target_folder_uid)
        else:
            # Dashboard doesn't exist - create new
            result = target_client.create_dashboard(new_dashboard, target_folder_uid)
        
        return result
