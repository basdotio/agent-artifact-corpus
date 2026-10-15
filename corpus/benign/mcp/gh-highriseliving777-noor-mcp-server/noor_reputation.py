#!/usr/bin/env python3
"""
noor_reputation.py — Portable Covenant Score for any agent.

Scans all certificates issued to an agent and computes:
- Total certified tasks
- Average Covenant Score (weighted by recency)
- Violation count (FLAGGED tasks)
- Trust level (Emerging / Established / Trusted / Exemplary)
- Score trend (improving / stable / declining)

The Covenant Score follows the agent across platforms. Any marketplace can
query it. Any enterprise can verify it. The agent carries its track record
wherever it goes.

Covenant Score formula:
  Base: 1.0
  Per CLEAR task:    -0.00
  Per FLAGGED task:  -0.05
  Per BLOCKED task:  -0.50 (retired — never fires in practice)
  Weighted by recency (recent tasks count more)
  Clamped to [0.0, 1.0]
"""

import json
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional

# --- Configuration ---
BASE_DIR = Path(__file__).parent
META_DIR = BASE_DIR / "_meta"
CERTS_DIR = META_DIR / "certificates"

SCORE_PENALTIES = {
    "CLEAR": 0.0,
    "FLAGGED": 0.05,
    "BLOCKED": 0.50,
}

TRUST_LEVELS = [
    (0.95, "Exemplary"),
    (0.85, "Trusted"),
    (0.70, "Established"),
    (0.00, "Emerging"),
]

RECENCY_HALFLIFE_DAYS = 90  # Tasks older than 90 days count half as much

# --- Load certificates for an agent ---
def load_certificates_for_agent(agent_id: str) -> List[Dict]:
    """Load all certificates that reference this agent_id.

    Note: certificates are stored in _meta/certificates/NGC-*.json.
    We load the attestation reference, then look up the agent_id in the chain.
    For now, we look in each certificate's attestation metadata; if the
    agent_id is not stored directly in the cert, we skip it.
    """
    certs = []
    if not CERTS_DIR.exists():
        return certs

    for cert_file in CERTS_DIR.glob("NGC-*.json"):
        try:
            cert = json.loads(cert_file.read_text())
        except Exception:
            continue
        # Check if cert references this agent
        # (Attestation metadata may carry agent_id; we add a top-level field later)
        if cert.get("agent_id") == agent_id:
            certs.append(cert)
    return certs

# --- Score computation ---
def _recency_weight(issued_at: str) -> float:
    """Weight by recency. Recent tasks count more."""
    try:
        issued = datetime.fromisoformat(issued_at.replace("Z", "+00:00"))
    except Exception:
        return 1.0
    age_days = (datetime.now(timezone.utc) - issued).total_seconds() / 86400.0
    # Exponential decay with halflife
    return 0.5 ** (age_days / RECENCY_HALFLIFE_DAYS)

def _trust_level(score: float) -> str:
    for threshold, level in TRUST_LEVELS:
        if score >= threshold:
            return level
    return "Emerging"

def compute_reputation(agent_id: str) -> Dict:
    """Compute the Covenant Score and reputation summary for an agent."""
    certs = load_certificates_for_agent(agent_id)

    if not certs:
        return {
            "agent_id": agent_id,
            "total_certified_tasks": 0,
            "covenant_score": None,
            "trust_level": "Unverified",
            "violations": 0,
            "trend": "no_data",
            "first_certificate": None,
            "last_certificate": None,
        }

    # Sort by issue time (chronological)
    certs_sorted = sorted(certs, key=lambda c: c.get("issued_at", ""))

    # Compute weighted score
    total_weight = 0.0
    weighted_penalty = 0.0
    violations = 0

    for cert in certs_sorted:
        tier = cert.get("governance_result", {}).get("tier", "CLEAR")
        if tier == "FLAGGED":
            violations += 1
        penalty = SCORE_PENALTIES.get(tier, 0.0)
        weight = _recency_weight(cert.get("issued_at", ""))
        total_weight += weight
        weighted_penalty += penalty * weight

    if total_weight > 0:
        avg_penalty = weighted_penalty / total_weight
    else:
        avg_penalty = 0.0

    score = max(0.0, min(1.0, 1.0 - avg_penalty))

    # Trend: compare first-half vs second-half of certs
    if len(certs_sorted) < 4:
        trend = "insufficient_data"
    else:
        half = len(certs_sorted) // 2
        first_half = certs_sorted[:half]
        second_half = certs_sorted[half:]

        def half_score(half_certs):
            penalty_sum = sum(SCORE_PENALTIES.get(c.get("governance_result", {}).get("tier", "CLEAR"), 0.0) for c in half_certs)
            return 1.0 - (penalty_sum / max(len(half_certs), 1))

        first_score = half_score(first_half)
        second_score = half_score(second_half)
        diff = second_score - first_score
        if diff > 0.02:
            trend = "improving"
        elif diff < -0.02:
            trend = "declining"
        else:
            trend = "stable"

    return {
        "agent_id": agent_id,
        "total_certified_tasks": len(certs),
        "covenant_score": round(score, 4),
        "trust_level": _trust_level(score),
        "violations": violations,
        "trend": trend,
        "first_certificate": certs_sorted[0].get("certificate_id"),
        "last_certificate": certs_sorted[-1].get("certificate_id"),
        "first_issued": certs_sorted[0].get("issued_at"),
        "last_issued": certs_sorted[-1].get("issued_at"),
    }

# --- Public interface ---
def query_reputation(agent_id: str) -> Dict:
    """Public reputation query. Returns the Covenant Score and summary."""
    if not agent_id:
        return {"error": "agent_id required"}

    result = compute_reputation(agent_id)
    result["disclaimer"] = (
        "The Covenant Score is derived from the agent's certificate history. "
        "It is a track record, not a guarantee. Verify individual certificates at "
        "/api/verify/{certificate_id}."
    )
    result["reputation_layer_version"] = "1.0"
    return result

def get_reputation_status() -> Dict:
    """Status for health endpoints."""
    total_agents = 0
    if CERTS_DIR.exists():
        agent_set = set()
        for cert_file in CERTS_DIR.glob("NGC-*.json"):
            try:
                cert = json.loads(cert_file.read_text())
                if cert.get("agent_id"):
                    agent_set.add(cert["agent_id"])
            except Exception:
                continue
        total_agents = len(agent_set)

    return {
        "status": "active",
        "layer": "Portable Reputation",
        "total_agents_tracked": total_agents,
        "covenant_score_range": "0.0 (worst) to 1.0 (perfect)",
        "trust_levels": ["Emerging", "Established", "Trusted", "Exemplary"],
        "query_endpoint": "/api/reputation/{agent_id}",
    }

# --- Testing ---
if __name__ == "__main__":
    print("Testing noor_reputation.py")
    print("=" * 70)

    # Query a non-existent agent
    print("\n[1] Query unknown agent...")
    result = query_reputation("unknown-agent-123")
    print(json.dumps(result, indent=2))

    # Query the test-agent (from attestation test)
    print("\n[2] Query test-agent...")
    result = query_reputation("test-agent")
    print(json.dumps(result, indent=2))

    print("\n[3] Reputation layer status:")
    print(json.dumps(get_reputation_status(), indent=2))
