"""
InfoStore and Repository service for SAP BusinessObjects 4.3 SP5.
Handles hierarchical folder structures, corporate categories, and folder CRUD operations.
"""

from typing import Any, Dict, List, Optional

from core.client import BOEClient
from core.exceptions import BOEError


class InfostoreService:
    """Service to navigate and manage repository folders, InfoStore objects, and categories."""

    def __init__(self, client: BOEClient):
        self.client = client

    def get_folders(self, folder_id: str, recursive: bool = True, folder_list: Optional[List[str]] = None) -> List[str]:
        """
        Recursively retrieves all subfolder IDs starting from a parent folder ID.
        """
        if folder_list is None:
            folder_list = []

        url = f"{self.client.bip_url}/infostore/{folder_id}/children?type=Folder&page=1&pagesize=10000"
        try:
            resp = self.client.get(url)
            if isinstance(resp, dict) and "entries" in resp:
                for entry in resp["entries"]:
                    child_id = str(entry["id"])
                    folder_list.append(child_id)
                    if recursive:
                        self.get_folders(child_id, recursive=True, folder_list=folder_list)
        except Exception:
            # If folder has no children or error, return accumulated list
            pass
        return folder_list

    def get_folder_details(self, folder_id: str) -> Dict[str, Any]:
        """
        Retrieves metadata of a specific repository folder (name, CUID, parent ID, description).
        """
        url = f"{self.client.query_url}/cmsquery?page=1&pagesize=10"
        payload = {
            "query": f"SELECT SI_ID, SI_NAME, SI_CUID, SI_PARENTID, SI_DESCRIPTION FROM CI_INFOOBJECTS WHERE SI_ID = {folder_id} AND SI_KIND = 'Folder'"
        }
        resp = self.client.post(url, json_data=payload)
        if isinstance(resp, dict) and resp.get("entries"):
            entry = resp["entries"][0]
            return {
                "id": str(entry.get("SI_ID", folder_id)),
                "name": str(entry.get("SI_NAME", "")),
                "cuid": str(entry.get("SI_CUID", "")),
                "parent_id": str(entry.get("SI_PARENTID", "")),
                "description": str(entry.get("SI_DESCRIPTION", "")),
            }
        raise BOEError(f"Folder ID {folder_id} not found in InfoStore.")

    def create_folder(self, name: str, parent_folder_id: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Creates a new folder under the specified parent folder ID.
        """
        url = f"{self.client.bip_url}/infostore/{parent_folder_id}/children"
        payload = {"entry": {"name": name, "description": description or "", "type": "Folder"}}
        resp = self.client.post(url, json_data=payload)
        return resp

    def delete_folder(self, folder_id: str) -> bool:
        """
        Permanently deletes a folder from the InfoStore repository.
        """
        url = f"{self.client.bip_url}/infostore/{folder_id}"
        self.client.delete(url)
        return True

    def get_webi_docs(self, folder_id: str) -> List[str]:
        """
        Retrieves all Web Intelligence document IDs situated inside a folder.
        """
        url = f"{self.client.bip_url}/infostore/{folder_id}/children?type=Webi&page=1&pagesize=10000"
        resp = self.client.get(url)
        webi_list: List[str] = []
        if isinstance(resp, dict) and "entries" in resp:
            for entry in resp["entries"]:
                webi_list.append(str(entry["id"]))
        return webi_list

    def get_categories(self) -> List[Dict[str, str]]:
        """
        Lists all Corporate Categories defined in the BI platform.
        """
        url = f"{self.client.query_url}/cmsquery?page=1&pagesize=1000"
        payload = {
            "query": "SELECT SI_ID, SI_NAME, SI_CUID FROM CI_INFOOBJECTS WHERE SI_KIND = 'Category' ORDER BY SI_NAME"
        }
        resp = self.client.post(url, json_data=payload)
        categories: List[Dict[str, str]] = []
        if isinstance(resp, dict) and resp.get("entries"):
            for entry in resp["entries"]:
                categories.append(
                    {
                        "id": str(entry.get("SI_ID", "")),
                        "name": str(entry.get("SI_NAME", "")),
                        "cuid": str(entry.get("SI_CUID", "")),
                    }
                )
        return categories
