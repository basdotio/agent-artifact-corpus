"""Model-independent safety policy, tool orchestration, and local proposal bridge."""

import asyncio
import json
import re
from datetime import date
from typing import Any

from backend.agent.mcp_client import MCPClient
from backend.agent.models import AgentError, AgentReply, Conversation, ResponsePlan, ToolCall, redact
from backend.agent.providers import Provider
from backend.agent.case_memory import HISTORY_TOOL, read_history, render_history, validate_history
from backend.repair_service import RepairService

LIMIT_NOTICE = "Active dates do not establish fault coverage, claim acceptance, free repair or a booking."


class Agent:
    def __init__(self, client: MCPClient, provider: Provider, repairs: RepairService, *,
                 evaluation_date: str = "2026-10-17", max_rounds: int = 6, max_tools: int = 8) -> None:
        try:
            if date.fromisoformat(evaluation_date).isoformat() != evaluation_date:
                raise ValueError
        except (ValueError, TypeError):
            raise AgentError("Evaluation date must be YYYY-MM-DD.") from None
        if not 1 <= max_rounds <= 8 or not 1 <= max_tools <= 12:
            raise AgentError("Agent iteration limits are outside supported bounds.")
        self.client, self.provider, self.repairs = client, provider, repairs
        self.evaluation_date, self.max_rounds, self.max_tools = evaluation_date, max_rounds, max_tools

    async def _execute(self, state: Conversation, call: ToolCall) -> dict[str, Any]:
        if call.name == HISTORY_TOOL["name"]:
            state.saved_history = read_history(self.repairs, state, call.arguments)
            return state.saved_history
        self.client.validate_call(call.name, call.arguments)
        args = dict(call.arguments)
        if call.name == "find_appliance":
            query = args.get("query", "").strip().casefold()
            request = state.recent_messages[-1].casefold() if state.recent_messages else ""
            normalized = re.sub(r"\bwasher\b", "washing machine", request)
            normalized = re.sub(r"\bfridge\b", "refrigerator", normalized)
            followup = bool(re.search(r"evidence|warranty|receipt|that|coverage|proof|prepare", request))
            selected_query = state.selected and query == state.selected["id"].casefold() and followup
            if query != state.household_id.casefold() and query not in request and query not in normalized and not selected_query:
                raise AgentError("Search query was not grounded in your request. Please specify the appliance type or ID.")
        else:
            if state.selected is None or args.get("appliance_id") != state.selected["id"]:
                raise AgentError("Select one appliance from MCP discovery before checking its evidence.")
            if call.name == "evaluate_warranty":
                if args.get("evaluation_date") not in (None, self.evaluation_date):
                    raise AgentError("Model attempted to change the configured evaluation date.")
                args["evaluation_date"] = self.evaluation_date
        result = await self.client.call(call.name, args)
        if call.name == "find_appliance":
            matches = [item for item in result["matches"] if item["household"] == state.household_id]
            state.candidates = matches
            state.selected = matches[0] if len(matches) == 1 else None
            state.evidence.clear()
            state.clarification = None if len(matches) == 1 else ("multiple" if matches else "missing")
            result = {**result, "matches": matches, "count": len(matches)}
        else:
            state.evidence[call.name] = result
        return result

    @staticmethod
    def _clarify(state: Conversation) -> str:
        if state.candidates:
            choices = "; ".join(f"{item['id']} ({item['model']}, serial {item['serial']})" for item in state.candidates)
            return f"Which appliance should I check? Choose an ID: {choices}"
        return "No single registered appliance was identified. Please specify an appliance type, ID, model or serial."

    def _grounded(self, state: Conversation, plan: ResponsePlan) -> str:
        if plan.action == "history":
            if state.saved_history is None:
                raise AgentError("Saved history was not retrieved; no case conclusion was presented.")
            if plan.proposal_id and plan.proposal_id.casefold() not in state.recent_messages[-1].casefold():
                raise AgentError("Please explicitly select the saved proposal ID before narrowing history.")
            return render_history(state.saved_history, plan.proposal_id)
        if plan.action == "unsupported":
            return "I can check registered appliance evidence and warranty dates, and help prepare a pending repair proposal. Please name an appliance."
        if plan.action == "clarify" or state.selected is None:
            state.phase = "clarifying"
            return self._clarify(state)
        purchase = state.evidence.get("get_purchase_evidence")
        warranty = state.evidence.get("evaluate_warranty")
        if not purchase or not warranty:
            raise AgentError("No complete MCP evidence is available; a warranty conclusion cannot be made.")
        refs = purchase["source_refs"] + purchase["warranty_evidence"]["source_refs"]
        if (plan.appliance_id != state.selected["id"] or plan.warranty_status != warranty["status"]
                or plan.source_refs != warranty["source_refs"] or set(refs) != set(warranty["source_refs"])):
            raise AgentError("Model response did not match the MCP evidence; no conclusion was presented.")
        if warranty["status"] != "unknown" and (
                purchase["evidence_status"] != "verified_demo" or purchase["warranty_evidence"]["evidence_status"] != "verified_demo"
                or purchase["purchase_date"] != warranty["period_start"]
                or purchase["warranty_evidence"]["start_date"] != warranty["period_start"]
                or purchase["warranty_evidence"]["end_date"] != warranty["period_end"]):
            raise AgentError("Purchase and warranty evidence disagree; no coverage conclusion was presented.")
        item = state.selected
        coverage = {"active": "Active date-based warranty period", "expired": "Expired warranty period",
                    "unknown": "Unknown / insufficient warranty evidence"}[warranty["status"]]
        lines = [f"Appliance: {item['name']} [{item['id']}], {item['brand']} {item['model']}, serial {item['serial']}.",
                 f"Purchase evidence: {purchase['evidence_status']}; date: {purchase['purchase_date'] or 'missing'}.",
                 f"Warranty: {coverage} as of {warranty['evaluation_date']}."]
        if warranty["period_start"] and warranty["period_end"]:
            lines.append(f"Recorded period: {warranty['period_start']} through {warranty['period_end']} (inclusive).")
        lines.append("Sources: " + (", ".join(warranty["source_refs"]) or "none available"))
        lines.append("Missing information: " + (", ".join(purchase["missing_information"]) or "none recorded in demo evidence"))
        lines.extend([LIMIT_NOTICE, "Next: use /prepare <issue description> to save a pending local proposal for human review."])
        return "\n".join(lines)

    async def respond(self, state: Conversation, user_message: str) -> AgentReply:
        if state.busy:
            return AgentReply("This conversation already has an operation in progress.", status="error")
        if not isinstance(user_message, str) or not user_message.strip() or len(user_message) > 2000:
            return AgentReply("Enter a non-empty request of at most 2000 characters.", status="error")
        state.busy, state.phase = True, "reading"
        trace: list[str] = []
        local_trace: list[str] = []
        # No stale findings may be used after a failed/new turn.
        state.evidence.clear()
        state.saved_history = None
        state.execution_trace.clear()
        user_message = redact(user_message.strip())
        state.recent_messages.append(user_message)
        results: list[dict[str, Any]] = []
        try:
            tools = [*await self.client.discover(), HISTORY_TOOL]
            context = state.context(user_message, results, self.evaluation_date)
            messages = [{"role": "user", "content": json.dumps({"backend_context": context,
                          "untrusted_user_request": user_message})}]
            used_ids = set()
            for _ in range(self.max_rounds):
                if len(json.dumps(messages)) > 32000:
                    raise AgentError("Conversation exceeded the bounded model context; start a shorter request.")
                state.phase = "interpreting"
                turn = await asyncio.wait_for(self.provider.complete(messages, tools, context),
                                              timeout=getattr(self.provider, "completion_timeout", getattr(self.provider, "timeout", 29)) + 1)
                if turn.final is not None and not turn.calls:
                    text = self._grounded(state, turn.final)
                    if state.phase != "clarifying":
                        state.phase = "ready"
                    return AgentReply(redact(text), trace, local_tools=local_trace)
                if not turn.calls or turn.final is not None or len(trace) + len(local_trace) + len(turn.calls) > self.max_tools:
                    raise AgentError("Model tool-call limit or response contract was exceeded.")
                for call in turn.calls:
                    if call.name == HISTORY_TOOL["name"]:
                        validate_history(call.arguments)
                    else:
                        self.client.validate_call(call.name, call.arguments)
                    if call.call_id in used_ids:
                        raise AgentError("Model reused a tool-call ID.")
                    used_ids.add(call.call_id)
                    state.execution_trace.append({"event": "provider_tool_call", "provider": type(self.provider).__name__,
                                                  "call_id": call.call_id, "name": call.name})
                messages.append({"role": "assistant", "content": [
                    {"type": "tool_use", "id": call.call_id, "name": call.name, "input": call.arguments}
                    for call in turn.calls]})
                outputs = []
                for call in turn.calls:
                    state.phase = "reading"
                    result = await self._execute(state, call)
                    local = call.name == HISTORY_TOOL["name"]
                    (local_trace if local else trace).append(call.name)
                    state.execution_trace.append({"event": "executed_local_read" if local else "executed_mcp_http",
                                                  "call_id": call.call_id, "name": call.name})
                    results.append({"name": call.name, "result": result})
                    outputs.append({"type": "tool_result", "tool_use_id": call.call_id,
                                    "content": json.dumps({"untrusted_tool_data": result})})
                    if call.name == "find_appliance" and state.selected is None:
                        state.phase = "clarifying"
                        return AgentReply(self._clarify(state), trace, local_tools=local_trace)
                messages.append({"role": "user", "content": outputs})
                context = state.context(user_message, results, self.evaluation_date)
            raise AgentError("Model iteration limit reached; no proposal or approval was executed.")
        except asyncio.CancelledError:
            state.phase = "error"
            state.evidence.clear()
            state.saved_history = None
            raise
        except AgentError as exc:
            state.phase = "error"
            state.evidence.clear()
            return AgentReply(redact(str(exc)), trace, "error", local_trace)
        except Exception:
            state.phase = "error"
            state.evidence.clear()
            return AgentReply("Agent/provider unavailable or timed out. No proposal or approval was executed; retry or use demo mode.", trace, "error", local_trace)
        finally:
            state.busy = False

    async def prepare_proposal(self, state: Conversation, issue: str) -> dict[str, Any]:
        """Trusted local command only. This operation is NOT a model tool."""
        if state.busy or state.phase == "error" or not state.selected or state.clarification:
            raise AgentError("Identify one appliance successfully before preparing a proposal.")
        if not isinstance(issue, str) or not issue.strip() or len(issue) > 2000:
            raise AgentError("Describe the issue in 1–2000 characters.")
        state.busy = True
        try:
            await self.client.discover()
            for name in ("get_purchase_evidence", "evaluate_warranty"):
                await self._execute(state, ToolCall(call_id=f"prepare-{name}", name=name,
                                                    arguments={"appliance_id": state.selected["id"]}))
            # The service revalidates canonical catalog evidence and owns every SQLite write.
            proposal = self.repairs.prepare_repair_proposal(
                state.household_id, state.selected["id"], redact(issue.strip()),
                f"agent-{state.conversation_id}-{state.selected['id']}", self.evaluation_date)
            if proposal["status"] != "pending":
                raise AgentError("This conversation already has a decided proposal for this appliance. Start a new conversation for another proposal.")
            state.pending_proposal_id, state.phase = proposal["proposal_id"], "pending_review"
            return proposal
        except BaseException:
            state.evidence.clear()
            state.phase = "error"
            raise
        finally:
            state.busy = False
