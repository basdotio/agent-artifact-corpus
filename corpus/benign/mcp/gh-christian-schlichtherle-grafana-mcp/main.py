"""Main entry point for Grafana MCP server."""

from mcp.server.fastmcp import FastMCP

from grafana_mcp.tools import clusters, dashboards, datasources, folders

# Create the MCP server
mcp = FastMCP("Grafana")

tools_to_register = [
    # Cluster management tools
    clusters.list_clusters,
    clusters.check_cluster_health,
    
    # Dashboard tools
    dashboards.create_dashboard,
    dashboards.read_dashboard,
    dashboards.update_dashboard,
    dashboards.delete_dashboard,
    dashboards.search,
    dashboards.copy_dashboard,
    
    # Dashboard testing and validation tools
    dashboards.inspect_dashboard,
    dashboards.validate_dashboard,
    dashboards.snapshot_dashboard,
    dashboards.test_panel_render,
    dashboards.compare_dashboards,
    
    # Folder management tools
    folders.list_folders,
    folders.get_folder,
    folders.create_folder,
    folders.update_folder,
    folders.delete_folder,
    
    # Datasource tools
    datasources.list_datasources,
]

for tool in tools_to_register:
    mcp.tool()(tool)
