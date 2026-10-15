from fastmcp import FastMCP
from state import ApplicantState

mcp = FastMCP(name="Credit Application Intake Server")

@mcp.tool()
def normalize_application(applicant: ApplicantState) -> dict:
    debt_to_income_ratio = applicant.total_debt / max(applicant.annual_income, 1.0)
    
    return {
        **applicant.model_dump(),
        "debt_to_income_ratio": debt_to_income_ratio
    }
    
if __name__ == "__main__":
    mcp.run()