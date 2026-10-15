"""The published worker shown by ordinary CLI and MCP commands."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .client import LeanWarpCloudError


def published_worker_resources(catalog: Mapping[str, Any]) -> dict[str, Any]:
    """Project one default; retain the raw catalog in LeanWarpCloud.resources()."""
    name = catalog.get("default_resource_profile", "standard")
    resources = catalog.get("resources")
    if not isinstance(name, str) or not isinstance(resources, list):
        raise _unavailable()
    selected = [row for row in resources if isinstance(row, dict) and row.get("name") == name]
    if len(selected) != 1:
        raise _unavailable()
    row = selected[0]
    usage_based = row.get("billing") == "elastic_consumption_v1"
    worker = {
        field: row[field]
        for field in (
            "cpu_request_cores",
            "cpu_limit_cores",
            "memory_request_mib",
            "memory_limit_mib",
            "customer_cpu_cores",
            "customer_memory_mib",
            "hold_microusd",
        )
        if field in row
    }
    worker["usage_based"] = usage_based
    quote = row.get("minimum_minute_microusd" if usage_based else "minute_microusd")
    if quote is not None:
        worker["starting_minute_microusd"] = quote
    result: dict[str, Any] = {"worker": worker}
    if "idle_seconds" in catalog:
        result["idle_seconds"] = catalog["idle_seconds"]
    return result


def _unavailable() -> LeanWarpCloudError:
    return LeanWarpCloudError(
        502,
        "worker_pricing_unavailable",
        "LeanWarp did not identify one published worker; retry resources later.",
    )
