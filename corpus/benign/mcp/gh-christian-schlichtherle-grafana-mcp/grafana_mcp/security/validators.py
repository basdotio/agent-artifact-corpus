"""Security validation and enforcement for Grafana operations."""

import uuid
from typing import Any

from ..config import config


class SecurityValidator:
    """Validates and enforces security restrictions for dashboard operations."""

    @staticmethod
    def validate_dashboard_tags(dashboard: dict[str, Any]) -> bool:
        """Check if dashboard has all required protection tags."""
        dashboard_tags = set(dashboard.get("tags", []))
        required_tags = config.write_access_tags
        return required_tags.issubset(dashboard_tags)

    @staticmethod
    def add_protection_tags(dashboard: dict[str, Any]) -> dict[str, Any]:
        """Add protection tags to dashboard."""
        dashboard_copy = dashboard.copy()
        existing_tags = dashboard_copy.get("tags", [])
        if not isinstance(existing_tags, list):
            existing_tags = []

        tags_set = set(existing_tags)
        tags_set.update(config.write_access_tags)
        dashboard_copy["tags"] = list(tags_set)
        return dashboard_copy

    @staticmethod
    def validate_folder_access(folder_uid: str = "") -> bool:
        """Validate that operations are allowed in the specified folder."""
        folder_restriction = config.root_folder

        if folder_restriction == "/":
            return True

        if not folder_uid:
            return folder_restriction == "/"

        return True

    @staticmethod
    def generate_dashboard_uid() -> str:
        """Generate a unique dashboard UID."""
        # Generate a UUID and take first 10 characters (Grafana UID format)
        return uuid.uuid4().hex[:10]

    @staticmethod
    def prepare_dashboard_for_creation(dashboard: dict[str, Any], folder_uid: str = "") -> dict[str, Any]:
        """Prepare dashboard for creation with security requirements."""
        # Validate folder access
        if not SecurityValidator.validate_folder_access(folder_uid):
            raise ValueError(f"Access denied to folder. Operations restricted to: {config.folder}")

        # Add protection tags
        dashboard_with_tags = SecurityValidator.add_protection_tags(dashboard)

        # Generate UID if not present
        if "uid" not in dashboard_with_tags or not dashboard_with_tags["uid"]:
            dashboard_with_tags["uid"] = SecurityValidator.generate_dashboard_uid()

        # Ensure version is not set for new dashboards
        dashboard_with_tags.pop("version", None)

        return dashboard_with_tags

    @staticmethod
    def validate_dashboard_for_read(dashboard: dict[str, Any]) -> None:
        """Validate dashboard can be read based on protection tags."""
        read_tags = config.read_access_tags
        if not read_tags:
            return
        
        dashboard_tags = set(dashboard.get("tags", []))
        if not read_tags.issubset(dashboard_tags):
            raise ValueError("Dashboard not found")

    @staticmethod
    def validate_dashboard_for_write(dashboard: dict[str, Any], operation: str) -> None:
        """Validate dashboard can be modified (updated or deleted)."""
        if not SecurityValidator.validate_dashboard_tags(dashboard):
            required_tags = ", ".join(sorted(config.write_access_tags))
            raise ValueError(
                f"Cannot {operation} dashboard: missing required tags {required_tags}. "
                f"This dashboard was not created by this MCP server or has been modified."
            )

    @staticmethod
    def prepare_dashboard_for_update(dashboard: dict[str, Any], folder_uid: str = "") -> dict[str, Any]:
        """Prepare dashboard for update with security requirements."""
        # Validate folder access
        if not SecurityValidator.validate_folder_access(folder_uid):
            raise ValueError(f"Access denied to folder. Operations restricted to: {config.folder}")

        # Ensure protection tags are maintained
        dashboard_with_tags = SecurityValidator.add_protection_tags(dashboard)

        # Let Grafana handle version management automatically
        dashboard_with_tags.pop("version", None)

        return dashboard_with_tags

    @staticmethod
    def copy_dashboard_for_creation(
            source_dashboard: dict[str, Any],
            new_title: str,
            folder_uid: str = "",
            target_uid: str = ""
    ) -> dict[str, Any]:
        """Prepare a dashboard copy for creation."""
        # Start with the source dashboard
        new_dashboard = source_dashboard.copy()

        # Remove fields that shouldn't be copied
        fields_to_remove = ["id", "version", "url"]
        
        for field in fields_to_remove:
            new_dashboard.pop(field, None)

        # Set new title
        new_dashboard["title"] = new_title

        # Handle UID assignment
        if target_uid:
            # Explicit target UID provided
            new_dashboard["uid"] = target_uid
        else:
            # No target UID: remove existing UID and let prepare_dashboard_for_creation generate one
            new_dashboard.pop("uid", None)

        # Add protection tags and validate folder access
        return SecurityValidator.prepare_dashboard_for_creation(new_dashboard, folder_uid)
