"""triage-desk MCP server.

Six tools. Three act (register_patient, propose_priority, raise_recheck_flag);
three read. Every call is written to the audit table with inputs, outputs and
a timestamp, whether it succeeds or fails.

The clinician gate (record_clinician_decision) is deliberately NOT a tool on
this server, so no model connected to it can confirm its own proposal.

Run:  python -m triage_mcp.server        (stdio transport)
"""

from __future__ import annotations

import functools
import json
import os
from typing import Any, Optional

try:  # MCP Python SDK v2
    from mcp.server.mcpserver import MCPServer as Server
    from mcp.server.mcpserver.exceptions import ToolError
except ImportError:  # MCP Python SDK v1
    from mcp.server.fastmcp import FastMCP as Server
    from mcp.server.fastmcp.exceptions import ToolError

from . import desk, store

ACTOR = os.environ.get("TRIAGE_ACTOR", "agent")

mcp = Server(
    "triage-desk",
    instructions=(
        "Scores and sequences a triage queue on the South African Triage Scale (adult). "
        "It never diagnoses or prescribes. Every priority is a PENDING proposal until a "
        "named triage nurse confirms it. Cite evidence from the card for every discriminator."
    ),
)


def audited(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            out = fn(*args, **kwargs)
        except desk.DeskError as e:
            store.log(ACTOR, fn.__name__, kwargs, {"error": str(e)}, ok=False)
            raise ToolError(str(e)) from e
        except Exception as e:  # unexpected: log and surface, never swallow
            store.log(ACTOR, fn.__name__, kwargs, {"error": repr(e)}, ok=False)
            raise ToolError(f"internal error: {e!r}") from e
        store.log(ACTOR, fn.__name__, kwargs, out, ok=True)
        return out

    return wrapper


@mcp.tool()
@audited
def register_patient(card_json: str) -> dict:
    """Register an intake card. Pass card_json: the card file's text, copied exactly as read.

    The card holds patient_id, age_years, arrived_at, complaint, nurse_notes and vitals
    (rr, hr, sbp, temp, avpu A/V/C/P/U, mobility walking/with_help/immobile, trauma; optional
    glucose_mmol, ketonuria, spo2). Returns which scale applies, missing vitals and the next step.
    """
    try:
        card = json.loads(card_json)
    except (TypeError, ValueError) as e:
        raise desk.DeskError(f"card_json is not valid JSON: {e}") from e
    if not isinstance(card, dict):
        raise desk.DeskError("card_json must be a JSON object")
    return desk.register_patient(card=card)


@mcp.tool()
@audited
def compute_tews(patient_id: str) -> dict:
    """Triage Early Warning Score from the patient's latest recorded vitals, with a
    per-parameter breakdown and SATS rule ids. Uses stored vitals only."""
    return desk.compute_tews(patient_id=patient_id)


@mcp.tool()
@audited
def list_discriminators() -> dict:
    """SATS clinical discriminators the agent may cite, with their colour."""
    return desk.list_discriminators()


@mcp.tool()
@audited
def propose_priority(patient_id: str, rationale: str,
                     discriminators: Optional[list[dict[str, str]]] = None) -> dict:
    """Propose a SATS priority for nurse confirmation.

    discriminators: list of {"code": <code from list_discriminators>, "evidence_quote": <exact
    phrase copied from the card>}. Pass [] if none apply. The server computes the colour as the
    most urgent of the TEWS colour and the discriminators; you cannot set it. If any quote is not
    found on the card the whole proposal is rejected and nothing is stored.
    """
    return desk.propose_priority(patient_id=patient_id, discriminators=discriminators or [],
                                 rationale=rationale)


@mcp.tool()
@audited
def raise_recheck_flag(patient_id: str, kind: str, reason: str,
                       new_vitals: Optional[dict[str, Any]] = None) -> dict:
    """Ask the triage nurse for a second look. kind: missing_vitals | deterioration | nurse_review.

    With new_vitals from a re-check, the TEWS is recomputed; if it is more urgent than the
    confirmed colour a re-triage proposal is created, still pending nurse confirmation.
    """
    return desk.raise_recheck_flag(patient_id=patient_id, kind=kind, reason=reason,
                                   new_vitals=new_vitals)


@mcp.tool()
@audited
def get_queue() -> dict:
    """Current queue: confirmed patients ordered by colour then arrival, proposals awaiting
    the nurse, untriaged patients, open flags and target-time breaches."""
    return desk.get_queue()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
