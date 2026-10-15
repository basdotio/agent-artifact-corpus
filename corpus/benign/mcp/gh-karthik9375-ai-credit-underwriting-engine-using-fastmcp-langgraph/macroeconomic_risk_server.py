import os, requests
from fastmcp import FastMCP
from state import ApplicantState
from dotenv import load_dotenv

load_dotenv()

FRED_API_KEY = os.getenv("FRED_API_KEY")
FRED_SEARCH_URL = "https://api.stlouisfed.org/fred/series/search"
FRED_OBS_URL = "https://api.stlouisfed.org/fred/series/observations"

mcp = FastMCP(name="Macroeconomic Risk Evaluation Server")

def fetch_latest_series_value(series_id: str) -> float:
    data = requests.get(FRED_OBS_URL, params={"series_id": series_id, "api_key": FRED_API_KEY, "file_type": "json"}).json()
    observations = data.get("observations", [])
    for obs in reversed(observations):
        try:
            return float(obs["value"])
        except ValueError:
            continue
    return 0.0

def search_fred_series(country: str, keyword: str) -> str:
    data = requests.get(FRED_SEARCH_URL, params={"search_text": f"{country} {keyword}", "api_key": FRED_API_KEY, "file_type": "json"}).json()
    series_list = data.get("seriess", [])
    return series_list[0]["id"] if series_list else ""

@mcp.tool()
def fetch_macro_risk(applicant: ApplicantState) -> dict:
    country = applicant.location
    inflation = fetch_latest_series_value(search_fred_series(country, "inflation"))
    unemployment = fetch_latest_series_value(search_fred_series(country, "unemployment"))
    interest_rate = fetch_latest_series_value(search_fred_series(country, "interest rate"))
    norm_inflation = min(inflation / 10, 1.0)
    norm_unemployment = min(unemployment / 25, 1.0)
    norm_interest = min(interest_rate / 20, 1.0)
    macro_score = ((1 - norm_interest) * 0.4 + (1 - norm_unemployment) * 0.3 + (1 - norm_inflation) * 0.3) * 100
    return {"market_conditions_score": round(macro_score, 2)}

if __name__ == "__main__":
    mcp.run()