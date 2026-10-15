"""Server-side per-tool PCA enforcement for FastMCP.

Verify a proof-carrying action on every ``tools/call`` before the tool runs. Built on the shared
``atlas_pca`` reference verifier (no crypto is reimplemented here).
"""
from .capability import (  # noqa: F401
    Capability,
    ToolCapability,
    capability_satisfies,
    parse_capability,
    resolve_required,
)
from .extract import PCA_META_KEY, extract_pcactn  # noqa: F401
from .middleware import (  # noqa: F401
    PCAAccessDenied,
    PCADecision,
    PCAMiddleware,
    PolicyHook,
    pca_guard,
    pca_tool,
)
from .registry import DEFAULT_REGISTRY, CapabilityRegistry  # noqa: F401
from .verifier import CoreVerifier, GrantResolver, Verifier  # noqa: F401

__all__ = [
    "Capability",
    "CapabilityRegistry",
    "CoreVerifier",
    "DEFAULT_REGISTRY",
    "GrantResolver",
    "PCAAccessDenied",
    "PCADecision",
    "PCAMiddleware",
    "PCA_META_KEY",
    "PolicyHook",
    "ToolCapability",
    "Verifier",
    "capability_satisfies",
    "extract_pcactn",
    "parse_capability",
    "pca_guard",
    "pca_tool",
    "resolve_required",
]
