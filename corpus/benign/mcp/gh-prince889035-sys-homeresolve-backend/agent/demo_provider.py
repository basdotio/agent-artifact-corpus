"""DEMO MODE — deterministic routing. This module does not perform LLM inference."""

import re
from typing import Any

from backend.agent.models import ModelTurn, ResponsePlan, ToolCall


class DemoProvider:
    async def complete(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]],
                       context: dict[str, Any]) -> ModelTurn:
        request = context["request"].casefold()
        results = context["turn_results"]

        def call(name: str, arguments: dict[str, Any]) -> ModelTurn:
            return ModelTurn(calls=[ToolCall(call_id=f"demo-{len(results)}", name=name, arguments=arguments)])

        history = bool(re.search(r"happened|previous|earlier|still open|decide|saved|supported", request))
        proposal = re.search(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", request)
        if history or proposal:
            aliases = [(r"washing machine|washer", "washing machine"), (r"fridge|refrigerator", "refrigerator"),
                       (r"microwave", "microwave")]
            queries = [query for pattern, query in aliases if re.search(pattern, request)]
            if not results and queries:
                return call("find_appliance", {"query": queries[0] if len(queries) == 1 else context["household_id"]})
            if not any(r["name"] == "get_repair_history" for r in results):
                return call("get_repair_history", {"appliance_id": context["selected"]["id"]} if queries and context["selected"] else {})
            return ModelTurn(final=ResponsePlan(action="history", proposal_id=proposal.group() if proposal else None))

        if not results:
            explicit_id = re.search(r"\b(?=[a-z0-9-]*\d)[a-z0-9]+(?:-[a-z0-9]+){1,3}\b", request)
            if explicit_id:
                return call("find_appliance", {"query": explicit_id.group()})
            aliases = [(r"washing machine|washer", "washing machine"), (r"refrigerator|fridge", "refrigerator"),
                       (r"microwave", "microwave"), (r"toaster", "toaster")]
            queries = [query for pattern, query in aliases if re.search(pattern, request)]
            # A supplied candidate ID/model/serial is a specific clarification selection.
            for item in context["candidates"]:
                if any(str(item[key]).casefold() in request for key in ("id", "model", "serial")):
                    return call("find_appliance", {"query": item["id"]})
            if len(queries) == 1:
                return call("find_appliance", {"query": queries[0]})
            if len(queries) > 1 or "two appliances" in request or "which one" in request:
                return call("find_appliance", {"query": context["household_id"]})
            if context["selected"] and re.search(r"evidence|warranty|receipt|that|coverage|proof|prepare", request):
                return call("get_purchase_evidence", {"appliance_id": context["selected"]["id"]})
            return ModelTurn(final=ResponsePlan(action="unsupported"))
        if context["selected"] is None:
            return ModelTurn(final=ResponsePlan(action="clarify"))
        names = {item["name"] for item in results}
        identifier = context["selected"]["id"]
        if "get_purchase_evidence" not in names:
            return call("get_purchase_evidence", {"appliance_id": identifier})
        if "evaluate_warranty" not in names:
            return call("evaluate_warranty", {"appliance_id": identifier, "evaluation_date": context["evaluation_date"]})
        warranty = context["evidence"]["evaluate_warranty"]
        return ModelTurn(final=ResponsePlan(action="prepare" if "prepare" in request else "report",
                                            appliance_id=identifier, warranty_status=warranty["status"],
                                            source_refs=warranty["source_refs"]))
