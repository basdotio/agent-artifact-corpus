#!/usr/bin/env python3
"""Noor Governance MCP Server - FastMCP (SDK 2.x compatible)."""

import json
import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from noor_lawful_screener import screen_task, get_screener_status
from noor_approval_gate import run_approval_gate, approve, deny, get_pending, get_status

mcp = FastMCP("noor-governance")

BUDGET_LIMITS = {
    "default": 50.0,
    "construction-bid-coordinator": 100.0,
    "grant-specialist": 200.0,
}

IDENTITY_REGISTRY = Path(__file__).parent / "_meta" / "agent_identities.json"


def load_identities():
    if IDENTITY_REGISTRY.exists():
        return json.loads(IDENTITY_REGISTRY.read_text())
    return {}


def save_identities(identities):
    IDENTITY_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    IDENTITY_REGISTRY.write_text(json.dumps(identities, indent=2))


@mcp.tool()
def lawful_check(description: str, agent_id: str) -> dict:
    """Screen a task for unlawful-adjacent elements.

    Returns tier (CLEAR/FLAGGED/BLOCKED), categories, reasoning, and disclaimer.
    """
    tier, result = screen_task(description)
    return {
        "tier": tier,
        "categories": result.get("categories", []),
        "reasoning": result.get("reasoning", ""),
        "task_hash": result.get("task_hash", ""),
        "disclaimer": result.get("disclaimer", ""),
        "screener_status": get_screener_status(),
    }


@mcp.tool()
def request_approval(action: str, agent_id: str, reason: str) -> dict:
    """Request human approval for a risky action.

    Returns an approval_id. The action stays pending until a human approves or denies.
    """
    result = run_approval_gate(action, agent_id)
    return result


@mcp.tool()
def budget_enforce(agent_id: str, amount: float) -> dict:
    """Check if an agent spending amount exceeds its monthly limit."""
    limit = BUDGET_LIMITS.get(agent_id, BUDGET_LIMITS["default"])
    return {
        "agent_id": agent_id,
        "limit": limit,
        "requested": amount,
        "allowed": amount <= limit,
    }


@mcp.tool()
def identity_register(agent_id: str, role: str = "") -> dict:
    """Register or retrieve an agent persistent identity."""
    identities = load_identities()
    if role and agent_id not in identities:
        from datetime import datetime, timezone
        identities[agent_id] = {"role": role, "registered": datetime.now(timezone.utc).isoformat()}
        save_identities(identities)
    return {
        "agent_id": agent_id,
        "identity": identities.get(agent_id, {"role": "unregistered"}),
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
