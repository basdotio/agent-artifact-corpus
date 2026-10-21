"""HTTP client for Grafana API operations."""

from typing import Any

import httpx

from .config import config


class GrafanaClient:
    """HTTP client for Grafana API operations."""

    def __init__(self, cluster: str):
        """Initialize client for specified cluster."""
        config.validate_cluster(cluster)
        self.cluster = cluster
        self.base_url = config.get_cluster_url(cluster)
        self.token = config.get_cluster_token(cluster)

        # Remove trailing slash from base URL
        self.base_url = self.base_url.removesuffix("/")

        # Set up headers
        headers = {
            "Content-Type": "application/json"
        }

        # Only add Authorization header if token is present
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        # Set up the HTTP client
        self.client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=30.0
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    # Dashboard operations

    def get_dashboard(self, uid: str) -> dict[str, Any]:
        """Get dashboard by UID."""
        response = self.client.get(f"/api/dashboards/uid/{uid}")
        response.raise_for_status()
        return response.json()

    def create_dashboard(self, dashboard_json: dict[str, Any], folder_uid: str = "") -> dict[str, Any]:
        """Create a new dashboard."""
        payload = {
            "dashboard": dashboard_json,
            "overwrite": False,
            "message": "Created via Grafana MCP"
        }

        if folder_uid:
            payload["folderUid"] = folder_uid

        response = self.client.post("/api/dashboards/db", json=payload)
        response.raise_for_status()
        return response.json()

    def update_dashboard(self, dashboard_json: dict[str, Any], folder_uid: str = "") -> dict[str, Any]:
        """Update an existing dashboard."""
        payload = {
            "dashboard": dashboard_json,
            "overwrite": True,
            "message": "Updated via Grafana MCP"
        }

        if folder_uid:
            payload["folderUid"] = folder_uid

        response = self.client.post("/api/dashboards/db", json=payload)
        response.raise_for_status()
        return response.json()

    def delete_dashboard(self, uid: str) -> dict[str, Any]:
        """Delete dashboard by UID."""
        response = self.client.delete(f"/api/dashboards/uid/{uid}")
        response.raise_for_status()
        return response.json()

    def search_dashboards(
            self,
            query: str = "",
            tags: list[str] = None,
            starred: bool | None = None,
            folder_uids: list[str] = None,
            dashboard_uids: list[str] = None,
            dashboard_ids: list[int] = None,
            type_filter: str = "",
            limit: int = 1000,
            page: int = 1
    ) -> list[dict[str, Any]]:
        """Search for dashboards."""
        params = {}

        if query:
            params["query"] = query

        if tags:
            params["tag"] = tags

        if starred is not None:
            params["starred"] = str(starred).lower()

        if folder_uids:
            params["folderUIDs"] = folder_uids

        if dashboard_uids:
            params["dashboardUIDs"] = dashboard_uids

        if dashboard_ids:
            params["dashboardIds"] = dashboard_ids

        if type_filter:
            params["type"] = type_filter

        params["limit"] = limit
        params["page"] = page

        response = self.client.get("/api/search", params=params)
        response.raise_for_status()
        return response.json()

    def get_dashboard_tags(self) -> list[dict[str, Any]]:
        """Get all dashboard tags."""
        response = self.client.get("/api/dashboards/tags")
        response.raise_for_status()
        return response.json()

    # Datasource operations

    def list_datasources(self) -> list[dict[str, Any]]:
        """List all datasources."""
        response = self.client.get("/api/datasources")
        response.raise_for_status()
        return response.json()

    def get_datasource(self, uid: str) -> dict[str, Any]:
        """Get datasource by UID."""
        response = self.client.get(f"/api/datasources/uid/{uid}")
        response.raise_for_status()
        return response.json()

    # Folder operations

    def list_folders(self, parent_uid: str = "") -> list[dict[str, Any]]:
        """List all folders, optionally under a parent folder."""
        params = {}
        if parent_uid:
            params["parent"] = parent_uid

        response = self.client.get("/api/folders", params=params)
        response.raise_for_status()
        return response.json()

    def get_folder(self, uid: str) -> dict[str, Any]:
        """Get folder by UID."""
        response = self.client.get(f"/api/folders/{uid}")
        response.raise_for_status()
        return response.json()

    def create_folder(self, title: str, parent_uid: str = "") -> dict[str, Any]:
        """Create a new folder."""
        payload = {
            "title": title
        }

        if parent_uid:
            payload["parentUid"] = parent_uid

        response = self.client.post("/api/folders", json=payload)
        response.raise_for_status()
        return response.json()

    def update_folder(self, uid: str, title: str, parent_uid: str = "") -> dict[str, Any]:
        """Update an existing folder."""
        payload = {
            "title": title,
            "uid": uid
        }

        if parent_uid:
            payload["parentUid"] = parent_uid

        response = self.client.put(f"/api/folders/{uid}", json=payload)
        response.raise_for_status()
        return response.json()

    def delete_folder(self, uid: str, force_delete_rules: bool = False) -> dict[str, Any]:
        """Delete a folder."""
        params = {}
        if force_delete_rules:
            params["forceDeleteRules"] = "true"

        response = self.client.delete(f"/api/folders/{uid}", params=params)
        response.raise_for_status()
        return response.json()

    # Snapshot operations

    def create_snapshot(self, dashboard_json: dict[str, Any], name: str = "", expires: int = 0) -> dict[str, Any]:
        """Create a dashboard snapshot."""
        payload = {
            "dashboard": dashboard_json,
            "name": name,
            "expires": expires
        }

        response = self.client.post("/api/snapshots", json=payload)
        response.raise_for_status()
        return response.json()

    def get_snapshot(self, key: str) -> dict[str, Any]:
        """Get snapshot by key."""
        response = self.client.get(f"/api/snapshots/{key}")
        response.raise_for_status()
        return response.json()

    def list_snapshots(self) -> list[dict[str, Any]]:
        """List all snapshots."""
        response = self.client.get("/api/dashboard/snapshots")
        response.raise_for_status()
        return response.json()

    def delete_snapshot(self, key: str) -> dict[str, Any]:
        """Delete snapshot by key."""
        response = self.client.delete(f"/api/snapshots/{key}")
        response.raise_for_status()
        return response.json()

    # Render operations

    def render_dashboard_panel(
        self,
        uid: str,
        panel_id: int,
        width: int = 1000,
        height: int = 500,
        from_time: str = "now-6h",
        to_time: str = "now"
    ) -> bytes:
        """Render a specific panel as PNG."""
        params = {
            "panelId": panel_id,
            "width": width,
            "height": height,
            "from": from_time,
            "to": to_time
        }

        response = self.client.get(f"/render/d-solo/{uid}/", params=params)
        response.raise_for_status()
        return response.content

    # Health check

    def health_check(self) -> dict[str, Any]:
        """Check cluster health."""
        response = self.client.get("/api/health")
        response.raise_for_status()
        return response.json()


def create_client(cluster: str) -> GrafanaClient:
    """Create a Grafana client for the specified cluster."""
    return GrafanaClient(cluster)
