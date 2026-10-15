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
def compile_evaluation_plan(case_id: str, model: str = "") -> dict:
    """Create a sourced draft plan. A named human must lock it before bid evaluation."""
    return service.compile_evaluation_plan(case_id, model)


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
