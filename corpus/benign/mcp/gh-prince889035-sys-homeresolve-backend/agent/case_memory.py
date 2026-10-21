"""Read-only saved workflow memory. Not MCP, and never an approval capability."""

from typing import Any
from jsonschema import Draft202012Validator
from backend.agent.models import AgentError, Conversation, PurchaseResult, WarrantyResult
from backend.repair_service import RepairService

HISTORY_TOOL = {"name": "get_repair_history", "description":
    "Use ONLY for a user question about PREVIOUS/SAVED repairs, decisions, cases or their original evidence. "
    "Not for a newly reported fault or a current warranty check: those require purchase and warranty MCP tools. "
    "For a named appliance find it first, then supply its selected ID. No writes or bookings.",
    "input_schema": {"type": "object", "properties": {"appliance_id": {"type": "string", "minLength": 1, "maxLength": 80}},
                     "additionalProperties": False}}


def validate_history(arguments: dict[str, Any]) -> None:
    if not Draft202012Validator(HISTORY_TOOL["input_schema"]).is_valid(arguments):
        raise AgentError("Invalid saved-history arguments. Household context cannot be supplied by the model.")


def read_history(repairs: RepairService, state: Conversation, arguments: dict[str, Any]) -> dict[str, Any]:
    validate_history(arguments)
    appliance_id = arguments.get("appliance_id")
    if appliance_id and (not state.selected or state.selected["id"] != appliance_id):
        raise AgentError("Identify the appliance through MCP before filtering saved history.")
    proposals = repairs.list_repair_proposals(state.household_id)
    if appliance_id:
        proposals = [p for p in proposals if p["appliance_id"] == appliance_id]
    cases = {c["proposal_id"]: c for c in repairs.list_repair_cases(state.household_id)}
    records = []
    for p in proposals[-10:]:
        case = cases.get(p["proposal_id"])
        records.append({"proposal_id": p["proposal_id"], "appliance_id": p["appliance_id"], "decision": p["status"],
                        "case_id": case["case_id"] if case else None, "case_status": case["status"] if case else None,
                        "updated_at": p["updated_at"],
                        "warranty": WarrantyResult.model_validate(p["warranty_evaluation_snapshot"]).model_dump(),
                        "purchase": PurchaseResult.model_validate(p["purchase_evidence_snapshot"]).model_dump(),
                        "events": [{"event_type": e["event_type"], "event_timestamp": e["event_timestamp"]}
                                   for e in repairs.get_audit_history(state.household_id, p["proposal_id"])]})
    return {"source": "local_sqlite_saved_workflow", "records": records, "total_matches": len(proposals), "limited_to": 10}


def render_history(history: dict[str, Any], proposal_id: str | None) -> str:
    records = history["records"]
    if not records:
        return "There are no saved repair proposals or cases for this selection in your demo household. Temporary chat is not saved case history."
    if proposal_id:
        records = [r for r in records if r["proposal_id"] == proposal_id]
        if not records:
            raise AgentError("Model selected a proposal outside the retrieved household history.")
    if len(records) > 1 or (history["total_matches"] > 10 and not proposal_id):
        choices = "; ".join(f"{r['proposal_id']} ({r['appliance_id']}, {r['decision']})" for r in records)
        return "Which saved proposal do you mean? Choose a proposal ID: " + choices
    record = records[0]
    warranty = record["warranty"]
    lines = [f"Saved proposal {record['proposal_id']} for {record['appliance_id']}: {record['decision']}."]
    if record["case_id"]:
        lines.append(f"Local case {record['case_id']} is {record['case_status']}. No external service has been booked.")
    else:
        lines.append("No repair case was created for this proposal.")
    lines.append(f"Saved warranty assessment: {warranty['status']} on {warranty['evaluation_date']}; this is the original snapshot, not a new coverage check.")
    lines.append("Sources: " + (", ".join(warranty["source_refs"]) or "none available; warranty evidence is insufficient"))
    lines.append("Audit: " + ", ".join(e["event_type"] for e in record["events"]))
    lines.append("Saved workflow persists in SQLite; conversation history is temporary. No warranty claim approval or free service is established.")
    return "\n".join(lines)
