"""Exposure-control policy resolution and native visibility enforcement.

Pure resolution of the six filter settings into a per-surface policy, plus
the scoped ``FastMCP.enable`` / ``disable`` calls that make the policy take
effect. No backend I/O; no discovery audit (see ``exposure_audit``).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, cast

from fastmcp import FastMCP

if TYPE_CHECKING:
    from mcp_call_orchestrator_proxy.config import ProxySettings

BACKEND_STATUS_TOOL_NAME = "backend_status"


class Surface(StrEnum):
    """Client-facing surface governed by exposure control."""

    TOOL = "tool"
    RESOURCE = "resource"
    PROMPT = "prompt"


class PolicyMode(StrEnum):
    """Resolved mode for one surface after allow-beats-deny."""

    UNSET = "unset"
    ALLOW = "allow"
    DENY = "deny"


@dataclass(frozen=True, slots=True)
class ResolvedPolicy:
    """Policy in effect for one surface."""

    mode: PolicyMode
    names: frozenset[str]


@dataclass(frozen=True, slots=True)
class ExposureResolution:
    """All three surfaces plus ready-to-log startup warnings."""

    policies: Mapping[Surface, ResolvedPolicy]
    warnings: tuple[str, ...]


# Exposure surface → fastmcp components= sets (resource covers templates too).
SURFACE_COMPONENTS: Mapping[Surface, frozenset[str]] = {
    Surface.TOOL: frozenset({"tool"}),
    Surface.RESOURCE: frozenset({"resource", "template"}),
    Surface.PROMPT: frozenset({"prompt"}),
}


def resolve_policies(settings: ProxySettings) -> ExposureResolution:
    """Turn the six filter fields into one resolved policy per surface.

    Pure: no I/O, no logging. Never raises for filter content. When both
    allow and deny are set for a surface, allow wins and a warning string is
    produced for the composition root to log.
    """
    pairs: tuple[
        tuple[Surface, tuple[str, ...] | None, tuple[str, ...] | None], ...
    ] = (
        (Surface.TOOL, settings.tool_allow, settings.tool_deny),
        (Surface.RESOURCE, settings.resource_allow, settings.resource_deny),
        (Surface.PROMPT, settings.prompt_allow, settings.prompt_deny),
    )

    policies: dict[Surface, ResolvedPolicy] = {}
    warnings: list[str] = []

    for surface, allow, deny in pairs:
        if allow is not None and deny is not None:
            policies[surface] = ResolvedPolicy(
                mode=PolicyMode.ALLOW, names=frozenset(allow)
            )
            warnings.append(
                f"exposure: {surface.value} deny-list discarded because "
                "allow-list is set; allow-list decides"
            )
        elif allow is not None:
            policies[surface] = ResolvedPolicy(
                mode=PolicyMode.ALLOW, names=frozenset(allow)
            )
        elif deny is not None:
            policies[surface] = ResolvedPolicy(
                mode=PolicyMode.DENY, names=frozenset(deny)
            )
        else:
            policies[surface] = ResolvedPolicy(mode=PolicyMode.UNSET, names=frozenset())

    tool_pol = policies[Surface.TOOL]
    excluded = (
        tool_pol.mode == PolicyMode.ALLOW
        and BACKEND_STATUS_TOOL_NAME not in tool_pol.names
    ) or (
        tool_pol.mode == PolicyMode.DENY and BACKEND_STATUS_TOOL_NAME in tool_pol.names
    )
    if excluded:
        warnings.append(
            "exposure: tool filter excludes 'backend_status'; clients cannot "
            "use the built-in backend health-check tool"
        )

    return ExposureResolution(policies=policies, warnings=tuple(warnings))


def apply_exposure_policy(mcp: FastMCP, resolution: ExposureResolution) -> None:
    """Apply resolved policies via scoped ``disable`` / ``enable`` (never only=True).

    Transforms are evaluated lazily at list/lookup time, so this may run before
    or after ``backend_status`` is registered; the composition root still
    registers first for readability.
    """
    for surface, policy in resolution.policies.items():
        if policy.mode == PolicyMode.UNSET:
            continue
        # fastmcp types components as set[Literal[...]]; our frozenset[str] is
        # the same runtime values (tool/resource/template/prompt).
        components = cast(Any, set(SURFACE_COMPONENTS[surface]))
        if policy.mode == PolicyMode.ALLOW:
            # Scoped blank of this surface only, then re-enable named items.
            # Never use only=True: it appends an unscoped match_all disable.
            mcp.disable(components=components)
            mcp.enable(names=set(policy.names), components=components)
        else:  # DENY
            mcp.disable(names=set(policy.names), components=components)
