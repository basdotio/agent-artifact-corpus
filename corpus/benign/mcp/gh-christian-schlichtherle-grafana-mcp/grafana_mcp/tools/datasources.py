"""Datasource tools for Grafana MCP server."""

from typing import Any

from .base import grafana_tool, get_current_client


@grafana_tool
def list_datasources(cluster: str) -> list[dict[str, Any]]:
    """List all datasources in a Grafana cluster.
    
    Args:
        cluster: Target cluster name.
        
    Returns:
        List of datasources with name, type, UID, and other metadata.
        
    Raises:
        ValueError: If cluster is invalid.
    """
    client = get_current_client()
    datasources = client.list_datasources()

    # Return simplified datasource information
    result = []
    for ds in datasources:
        result.append({
            "uid": ds.get("uid", ""),
            "name": ds.get("name", ""),
            "type": ds.get("type", ""),
            "url": ds.get("url", ""),
            "isDefault": ds.get("isDefault", False),
            "access": ds.get("access", ""),
            "readOnly": ds.get("readOnly", False)
        })

    return result
