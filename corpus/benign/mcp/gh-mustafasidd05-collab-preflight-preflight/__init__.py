"""
Preflight: FastMCP Verification Server for AI Coding Agents.

Powered by SerpApi live search intelligence to eliminate hallucinated,
deprecated, and outdated code assertions before they reach production.
"""

__version__ = "0.1.0"
__author__ = "Preflight Team"

from preflight.models import PreflightVerdict, EvidenceItem, VerifyClaimRequest, VerdictType

__all__ = [
    "PreflightVerdict",
    "EvidenceItem",
    "VerifyClaimRequest",
    "VerdictType",
    "__version__",
]

