"""Configuration management for Grafana MCP server."""

from os import getenv
from typing import Any


def check_truthy(value: Any, message: str) -> Any:
    """Check if the value is truthy."""
    if not value:
        raise ValueError(message)
    return value


def parse_key_value_pairs(pairs: str) -> dict[str, str]:
    """Parse space-separated key=value pairs."""
    return {
        k: v for k, v in (e.split("=", 1) for e in pairs.split()) if k and v
    }


class GrafanaConfig:
    """Configuration for the Grafana MCP server."""

    def __init__(self):
        self._clusters = check_truthy(
            parse_key_value_pairs(getenv("GRAFANA_CLUSTER_URLS", "localhost=http://localhost:3000")),
            "GRAFANA_CLUSTER_URLS must not be empty")
        self._root_folder = check_truthy(getenv("GRAFANA_ROOT_FOLDER", "/"), "GRAFANA_ROOT_FOLDER must not be empty")
        self._read_access_tags = set(getenv("GRAFANA_READ_ACCESS_TAGS", "").split())
        self._write_access_tags = check_truthy(
            set(getenv("GRAFANA_WRITE_ACCESS_TAGS", "MCP").split()),
            "GRAFANA_WRITE_ACCESS_TAGS must not be empty")
        self._api_tokens = parse_key_value_pairs(getenv("GRAFANA_API_TOKENS", ""))
        
        # Validate that read access tags are a subset of write access tags
        if not self._read_access_tags.issubset(self._write_access_tags):
            read_only_tags = self._read_access_tags - self._write_access_tags
            raise ValueError(
                f"GRAFANA_READ_ACCESS_TAGS must be a subset of GRAFANA_WRITE_ACCESS_TAGS. "
                f"Tags in read but not in write: {sorted(read_only_tags)}. "
                f"Either remove these tags from GRAFANA_READ_ACCESS_TAGS or add them to GRAFANA_WRITE_ACCESS_TAGS."
            )

    @property
    def clusters(self) -> dict[str, str]:
        """Get all configured clusters."""
        return self._clusters.copy()

    @property
    def read_access_tags(self) -> set[str]:
        """Get read access protection tags."""
        return self._read_access_tags.copy()
    
    @property
    def write_access_tags(self) -> set[str]:
        """Get write access protection tags."""
        return self._write_access_tags.copy()

    @property
    def root_folder(self) -> str:
        """Get root folder restriction."""
        return self._root_folder

    def get_cluster_url(self, cluster: str) -> str:
        """Get URL for specified cluster."""
        if cluster not in self._clusters:
            raise ValueError(f"Unknown cluster: {cluster}")
        return self._clusters[cluster]

    def get_cluster_token(self, cluster: str) -> str:
        """Get API token for specified cluster.
        
        Returns empty string for unauthenticated clusters.
        """
        return self._api_tokens.get(cluster, "")

    def validate_cluster(self, cluster: str) -> None:
        """Validate that a cluster exists."""
        if cluster not in self._clusters:
            available = ", ".join(self._clusters.keys())
            raise ValueError(f"Unknown cluster '{cluster}'. Available clusters: {available}")


config = GrafanaConfig()
