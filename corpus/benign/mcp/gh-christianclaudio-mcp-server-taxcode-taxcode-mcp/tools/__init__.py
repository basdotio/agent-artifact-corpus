"""Modular domain tools and sub-servers for FastMCP 4 Server Composition."""

from __future__ import annotations

from taxcode_mcp.tools.compliance import (
    SUPPORTED_STATE_JURISDICTIONS,
    calculate_built_in_gain_sourcing,
    compliance_server,
    cross_border_tax_analysis,
    evaluate_georgia_residency,
    evaluate_pr_bona_fide_residency,
    evaluate_state_residency,
)
from taxcode_mcp.tools.statutes import (
    get_statute_resource,
    list_publications,
    lookup_statute,
    search_tax_code,
    statutes_server,
)
from taxcode_mcp.tools.system import (
    get_capabilities,
    get_health_status,
    system_server,
)

__all__ = [
    "SUPPORTED_STATE_JURISDICTIONS",
    "calculate_built_in_gain_sourcing",
    "compliance_server",
    "cross_border_tax_analysis",
    "evaluate_georgia_residency",
    "evaluate_pr_bona_fide_residency",
    "evaluate_state_residency",
    "get_capabilities",
    "get_health_status",
    "get_statute_resource",
    "list_publications",
    "lookup_statute",
    "search_tax_code",
    "statutes_server",
    "system_server",
]
