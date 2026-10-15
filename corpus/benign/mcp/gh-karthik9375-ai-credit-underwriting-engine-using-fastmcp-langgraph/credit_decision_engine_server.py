from fastmcp import FastMCP
from state import CreditState

mcp = FastMCP(name="Credit Decision Engine Server")

@mcp.tool()
def make_decision(credit_state: CreditState) -> dict:
    aggregate_score = (credit_state.creditworthiness_score * 0.4 +
                       (100 - credit_state.fraud_risk_score) * 0.3 +
                       credit_state.income_stability_score * 0.2 +
                       (credit_state.market_conditions_score or 0) * 0.1)
    
    decision = "APPROVED" if aggregate_score >= 70 else "SUBJECT TO HUMAN REVIEW" if aggregate_score >= 50 else "REJECTED"
    return {"decision": decision}

if __name__ == "__main__":
    mcp.run()