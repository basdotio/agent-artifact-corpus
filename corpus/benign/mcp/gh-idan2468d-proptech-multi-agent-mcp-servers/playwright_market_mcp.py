from typing import Any
from mcp_servers.proptech_mcp_server import FastMCP

mcp = FastMCP("PropTech-Playwright-Market-Pulse-MCP")

CITY_PULSE_DATA: dict[str, dict[str, Any]] = {
    "תל אביב": {
        "active_listings_count": 412,
        "avg_days_on_market": 44,
        "recent_price_drops_pct": 14.5,
        "avg_seller_discount_pct": 3.2,
    },
    "חיפה": {
        "active_listings_count": 285,
        "avg_days_on_market": 58,
        "recent_price_drops_pct": 22.0,
        "avg_seller_discount_pct": 5.4,
    },
    "רמת גן": {
        "active_listings_count": 198,
        "avg_days_on_market": 49,
        "recent_price_drops_pct": 18.0,
        "avg_seller_discount_pct": 4.1,
    },
    "באר שבע": {
        "active_listings_count": 340,
        "avg_days_on_market": 67,
        "recent_price_drops_pct": 27.5,
        "avg_seller_discount_pct": 6.2,
    },
}


@mcp.tool()
def mcp_fetch_live_listings_market_pulse(city: str) -> dict[str, Any]:
    """Fetch active listings supply, average days-on-market (DOM), and price-drop frequency."""
    pulse = CITY_PULSE_DATA.get(
        city.strip(),
        {
            "active_listings_count": 180,
            "avg_days_on_market": 55,
            "recent_price_drops_pct": 19.0,
            "avg_seller_discount_pct": 4.5,
        },
    )
    return {"city": city.strip(), **pulse}


if __name__ == "__main__":
    mcp.run()
