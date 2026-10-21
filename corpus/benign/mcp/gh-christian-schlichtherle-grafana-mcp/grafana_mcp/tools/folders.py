"""Folder management tools for Grafana MCP server."""

from typing import Any

from .base import grafana_tool, get_current_client
from ..security.validators import SecurityValidator


@grafana_tool
def list_folders(cluster: str, *, parent_uid: str = "") -> list[dict[str, Any]]:
    """List folders in a Grafana cluster, optionally under a parent folder.
    
    Args:
        cluster: Target cluster name.
        parent_uid: Optional parent folder UID to list subfolders.
        
    Returns:
        List of folders with metadata including hierarchy information.
        
    Raises:
        ValueError: If cluster is invalid.
    """
    client = get_current_client()
    
    # Validate folder access
    if not SecurityValidator.validate_folder_access(parent_uid):
        raise ValueError(f"Access denied to folder. Operations restricted to root folder boundary.")
    
    folders = client.list_folders(parent_uid=parent_uid)

    # Return simplified folder information
    result = []
    for folder in folders:
        result.append({
            "uid": folder.get("uid", ""),
            "id": folder.get("id", 0),
            "title": folder.get("title", ""),
            "url": folder.get("url", ""),
            "hasAcl": folder.get("hasAcl", False),
            "canSave": folder.get("canSave", False),
            "canEdit": folder.get("canEdit", False),
            "canAdmin": folder.get("canAdmin", False),
            "created": folder.get("created", ""),
            "updated": folder.get("updated", ""),
            "version": folder.get("version", 0),
            "parents": folder.get("parents", [])  # Hierarchy information
        })

    return result


@grafana_tool
def get_folder(cluster: str, folder_uid: str) -> dict[str, Any]:
    """Get detailed information about a specific folder.
    
    Args:
        cluster: Target cluster name.
        folder_uid: Unique identifier of the folder.
        
    Returns:
        Detailed folder information including hierarchy and permissions.
        
    Raises:
        ValueError: If cluster is invalid or folder not found.
    """
    client = get_current_client()
    
    # Validate folder access
    if not SecurityValidator.validate_folder_access(folder_uid):
        raise ValueError(f"Access denied to folder. Operations restricted to root folder boundary.")
    
    folder = client.get_folder(folder_uid)
    return folder


@grafana_tool
def create_folder(cluster: str, title: str, *, parent_uid: str = "") -> dict[str, Any]:
    """Create a new folder in Grafana.
    
    Args:
        cluster: Target cluster name.
        title: Title for the new folder.
        parent_uid: Optional parent folder UID to create subfolder.
        
    Returns:
        Created folder information including UID and URL.
        
    Raises:
        ValueError: If cluster is invalid or folder creation fails.
    """
    client = get_current_client()
    
    # Validate folder access
    if not SecurityValidator.validate_folder_access(parent_uid):
        raise ValueError(f"Access denied to folder. Operations restricted to root folder boundary.")
    
    result = client.create_folder(title=title, parent_uid=parent_uid)
    return result


@grafana_tool
def update_folder(
        cluster: str,
        folder_uid: str,
        title: str,
        *,
        parent_uid: str = ""
) -> dict[str, Any]:
    """Update an existing folder (rename or move to different parent).
    
    Args:
        cluster: Target cluster name.
        folder_uid: Unique identifier of the folder to update.
        title: New title for the folder.
        parent_uid: Optional new parent folder UID to move folder.
        
    Returns:
        Updated folder information.
        
    Raises:
        ValueError: If cluster is invalid, folder not found, or update fails.
    """
    client = get_current_client()
    
    # Validate folder access
    if not SecurityValidator.validate_folder_access(folder_uid):
        raise ValueError(f"Access denied to folder. Operations restricted to root folder boundary.")
    
    result = client.update_folder(uid=folder_uid, title=title, parent_uid=parent_uid)
    return result


@grafana_tool
def delete_folder(cluster: str, folder_uid: str, *, force_delete_rules: bool = False) -> dict[str, Any]:
    """Delete a folder from Grafana.
    
    Args:
        cluster: Target cluster name.
        folder_uid: Unique identifier of the folder to delete.
        force_delete_rules: Whether to force delete associated alert rules.
        
    Returns:
        Deletion confirmation.
        
    Raises:
        ValueError: If cluster is invalid, folder not found, or deletion fails.
    """
    client = get_current_client()
    
    # Validate folder access
    if not SecurityValidator.validate_folder_access(folder_uid):
        raise ValueError(f"Access denied to folder. Operations restricted to root folder boundary.")
    
    result = client.delete_folder(uid=folder_uid, force_delete_rules=force_delete_rules)
    return result
