from fastmcp import FastMCP
from state import ApplicantState

mcp = FastMCP(name="Income Stability Evaluation Server")

@mcp.tool()
def assess_income_stability(applicant: ApplicantState) -> dict:
    income_stability_score = ((1 if applicant.employment_status == "employed" or applicant.employment_status == "self-employed" else 0) * 0.6 +
                       min(applicant.employment_years, 10) / 10 * 0.4) * 100
    return {"income_stability_score": round(income_stability_score, 2)}

if __name__ == "__main__":
    mcp.run()