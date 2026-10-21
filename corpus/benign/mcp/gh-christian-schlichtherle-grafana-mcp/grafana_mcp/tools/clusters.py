"""Cluster management tools for Grafana MCP server."""

from typing import Any

from .base import grafana_tool, get_current_client
from ..config import config


def list_clusters() -> list[str]:
    """List all configured Grafana cluster names.
    
    Returns:
        Sorted list of cluster names.
    """
    return sorted(config.clusters.keys())


@grafana_tool
def check_cluster_health(cluster: str) -> dict[str, Any]:
    """Check the health and connectivity of a Grafana cluster.
    
    Args:
        cluster: Target cluster name to check.
        
    Returns:
        Dictionary containing health status, version info, and connectivity details.
        
    Raises:
        ValueError: If cluster is invalid or unreachable.
    """
    client = get_current_client()
    
    try:
        # Get health status
        health_info = client.health_check()
        
        # Try to get additional cluster info
        try:
            # Get datasources to verify API functionality
            datasources = client.list_datasources()
            datasource_count = len(datasources)
        except Exception:
            datasource_count = "unavailable"
        
        return {
            "cluster": cluster,
            "status": "healthy",
            "health_info": health_info,
            "datasource_count": datasource_count,
            "connectivity": "ok"
        }
    except Exception as e:
        return {
            "cluster": cluster,
            "status": "unhealthy", 
            "connectivity": "failed",
            "error": str(e)
        }
