from state import ApplicantState
from fastmcp import FastMCP
import random, requests

mcp = FastMCP(name="Fraud Risk Evaluation Server")

@mcp.tool()
def evaluate_fraud_risk(applicant: ApplicantState) -> dict:
    geo_resp = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": applicant.location, "format": "json"},
        headers={"User-Agent": "credit-agent"}
    ).json()
    geo_trust = 1 if geo_resp else 0.5
    velocity = random.uniform(0, 1)
    fraud_score = (1 - geo_trust) * 0.4 + velocity * 0.6

    return {"fraud_risk_score": round(fraud_score * 100, 2)}

if __name__ == "__main__":
    mcp.run()