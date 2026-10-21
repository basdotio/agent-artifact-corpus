"""Run with python -m mcp_server.server. Approval operations are deliberately absent."""
from mcp.server.fastmcp import FastMCP
from mcp_server.service import ProcurementService

mcp = FastMCP("Health Commodity Tender Workbench")
service = ProcurementService()


@mcp.tool()
def register_case(request: dict) -> dict:
    """Inventory a closed tender and explicitly synthetic bids, preserving source hashes."""
    return service.register_case(request)


@mcp.tool()
def compile_evaluation_plan(case_id: str, model: str = "", feedback: str = "") -> dict:
    """Create a sourced draft plan. A named human must lock it before bid evaluation.
    feedback: the validator's rejection of a previous attempt, passed back to the local model to correct."""
    return service.compile_evaluation_plan(case_id, model, feedback)


@mcp.tool()
def search_award_history(ocid: str = "", query: str = "", buyer: str = "", limit: int = 10, case_id: str = "") -> dict:
    """Search published Kenya OCDS award history by exact OCID or title keywords (optionally filtered by buyer).
    Returns contract-level awards with data-quality flags and a file/line/JSON-pointer citation for each value.
    With case_id, saves the result to the case as a cited annex and compares the declared closing date with the
    published one. Never produces a unit-price benchmark or a finding against a supplier."""
    return service.search_award_history(ocid=ocid, query=query, buyer=buyer, limit=limit, case_id=case_id)


@mcp.tool()
def evaluate_bid_pack(case_id: str, locked_plan_id: str, live_sources: bool = False) -> dict:
    """Evaluate synthetic bid evidence using only the current human-locked plan."""
    return service.evaluate_bid_pack(case_id, locked_plan_id, live_sources)


@mcp.tool()
def draft_evaluation_file(case_id: str) -> dict:
    """Create a cited unsigned review package; export requires a separate human approval."""
    return service.draft_evaluation_file(case_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
