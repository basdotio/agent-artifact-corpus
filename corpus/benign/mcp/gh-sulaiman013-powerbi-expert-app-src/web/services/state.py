"""
Application State Management
============================
Centralized state management for the Power BI MCP Server web application.
Replaces global variables with a proper state container.
"""

from typing import Optional, Any, Dict
from dataclasses import dataclass, field


@dataclass
class CloudConnectionInfo:
    """Information about the Power BI Service connection."""
    workspace_id: str = ""
    workspace_name: str = ""
    dataset_id: str = ""
    dataset_name: str = ""


class AppState:
    """
    Singleton state container for the application.

    Manages connections to:
    - Power BI Desktop (local)
    - Power BI Service (cloud)
    - LLM providers (Ollama, Azure)
    - PBIP projects
    """

    _instance: Optional['AppState'] = None

    def __new__(cls) -> 'AppState':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """Initialize all state variables."""
        # Power BI Desktop connection
        self.desktop_connector: Optional[Any] = None

        # Power BI Service (cloud) connection
        self.rest_connector: Optional[Any] = None
        self.xmla_connector: Optional[Any] = None
        self.cloud_connected: bool = False
        self.cloud_connection_info: Optional[CloudConnectionInfo] = None
        self.cloud_model_schema: Optional[Dict] = None

        # LLM Provider
        self.llm_provider: Optional[Any] = None
        self.current_provider_type: str = "ollama"  # "ollama", "azure", or "azure-claude"

        # Model schema (from local desktop)
        self.model_schema: Optional[Dict] = None

        # PBIP project
        self.pbip_connector: Optional[Any] = None
        self.pbip_loaded: bool = False

    def reset(self) -> None:
        """Reset all state to initial values."""
        self._initialize()

    @property
    def is_desktop_connected(self) -> bool:
        """Check if connected to Power BI Desktop."""
        return (self.desktop_connector is not None and
                self.desktop_connector.current_port is not None)

    @property
    def is_cloud_connected(self) -> bool:
        """Check if connected to Power BI Service."""
        return self.cloud_connected

    @property
    def is_llm_configured(self) -> bool:
        """Check if an LLM provider is configured."""
        return self.llm_provider is not None

    @property
    def is_pbip_loaded(self) -> bool:
        """Check if a PBIP project is loaded."""
        return self.pbip_loaded and self.pbip_connector is not None


# Global singleton instance
app_state = AppState()
