import os

import requests
from dotenv import load_dotenv
from fastmcp import FastMCP

load_dotenv()

API_KEY = os.getenv("ALPHAVANTAGE_API_KEY")

mcp = FastMCP("Stock OHLC MCP")


@mcp.tool()
def get_ohlc(symbol: str, limit: int = 10) -> dict:
    """
    Get daily OHLCV data for a stock.

    Examples:
        AAPL
        MSFT
        RELIANCE.BSE
        TCS.BSE
        INFY.BSE
    """

    if not API_KEY:
        return {
            "error": "ALPHAVANTAGE_API_KEY is not configured."
        }

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol.upper(),
            "outputsize": "compact",
            "apikey": API_KEY,
        },
        timeout=20,
    )

    response.raise_for_status()

    data = response.json()

    if "Error Message" in data:
        return {"error": data["Error Message"]}

    if "Note" in data:
        return {"error": data["Note"]}

    time_series = data.get("Time Series (Daily)")

    if not time_series:
        return {
            "error": "No OHLC data returned.",
            "response": data,
        }

    limit = max(1, min(limit, 100))

    rows = []

    for date, values in list(time_series.items())[:limit]:
        rows.append(
            {
                "date": date,
                "open": float(values["1. open"]),
                "high": float(values["2. high"]),
                "low": float(values["3. low"]),
                "close": float(values["4. close"]),
                "volume": int(values["5. volume"]),
            }
        )

    return {
        "symbol": symbol.upper(),
        "frequency": "daily",
        "count": len(rows),
        "data": rows,
    }


if __name__ == "__main__":
    mcp.run()