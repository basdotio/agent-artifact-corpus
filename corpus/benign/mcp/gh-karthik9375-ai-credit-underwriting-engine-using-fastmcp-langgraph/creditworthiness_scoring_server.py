from fastmcp import FastMCP
from state import ApplicantState

mcp = FastMCP(name="Creditworthiness Scoring Server")

@mcp.tool()
def estimate_creditworthiness(applicant: ApplicantState) -> dict:
    debt_to_income_ratio = applicant.total_debt / max(applicant.annual_income, 1.0)
    
    creditworthiness_score = (
        (applicant.credit_score / 850) * 0.4 +
        max(0.0, 1 - debt_to_income_ratio) * 0.3 +
        (min(applicant.credit_history_length, 30) / 30) * 0.2 +
        (1 if ((applicant.employment_status == "employed" or applicant.employment_status == "self-employed") and applicant.employment_years >= 2) else 0) * 0.1
    ) * 100

    if applicant.age < 25:
        creditworthiness_score *= 0.95
    elif applicant.age > 65:
        creditworthiness_score *= 0.97

    return {"creditworthiness_score": round(creditworthiness_score, 2)}

if __name__ == "__main__":
    mcp.run()
    