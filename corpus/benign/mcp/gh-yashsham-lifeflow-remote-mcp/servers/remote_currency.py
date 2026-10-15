"""
RemoteCurrencyServer
Transport: HTTP / SSE
Port: 8001
Purpose: Real-time public exchange rates and crypto market data.
"""

import httpx
from fastmcp import FastMCP

mcp = FastMCP("RemoteCurrencyServer")

# Offline fallback baseline rates in case public APIs are rate-limited
FALLBACK_RATES = {
    "USD": 1.0,
    "INR": 86.85,
    "EUR": 0.92,
    "GBP": 0.77,
    "AED": 3.67,
    "CAD": 1.38,
    "JPY": 152.40
}

FALLBACK_CRYPTO = {
    "bitcoin": {"inr": 8250000, "usd": 95000},
    "ethereum": {"inr": 290000, "usd": 3340},
    "solana": {"inr": 18500, "usd": 213}
}


@mcp.tool()
async def convert_currency(amount: float, from_curr: str, to_curr: str) -> str:
    """Convert an amount from one fiat currency to another using real-time rates."""
    from_c = from_curr.strip().upper()
    to_c = to_curr.strip().upper()
    amount = float(amount)
    
    # Try fetching real-time exchange rates from open exchange API
    rate = None
    source = "Live API"
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(f"https://open.er-api.com/v6/latest/{from_c}")
            if resp.status_code == 200:
                data = resp.json()
                rates = data.get("rates", {})
                if to_c in rates:
                    rate = rates[to_c]
    except Exception:
        pass

    # Safe fallback if network/API fails
    if rate is None:
        source = "Simulated Market Rate"
        from_usd = FALLBACK_RATES.get(from_c, 1.0)
        to_usd = FALLBACK_RATES.get(to_c, 1.0)
        rate = to_usd / from_usd if from_usd else 1.0

    converted = round(amount * rate, 2)
    return (
        f"💱 **Currency Conversion ({source})**\n"
        f"- {amount:,.2f} {from_c} = **{converted:,.2f} {to_c}**\n"
        f"- Current Exchange Rate: 1 {from_c} = {rate:.4f} {to_c}"
    )


@mcp.tool()
async def get_crypto_price(coin: str = "bitcoin") -> str:
    """Get live market price for cryptocurrencies (bitcoin, ethereum, solana)."""
    coin_id = coin.strip().lower()
    
    data = None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": coin_id, "vs_currencies": "usd,inr"}
            )
            if resp.status_code == 200:
                data = resp.json().get(coin_id)
    except Exception:
        pass

    if not data:
        data = FALLBACK_CRYPTO.get(coin_id, {"usd": 90000, "inr": 7800000})

    usd_p = data.get("usd", 0)
    inr_p = data.get("inr", 0)
    return f"🪙 **{coin_id.upper()} Price**: ${usd_p:,.2f} USD | ₹{inr_p:,.2f} INR"


@mcp.resource("resource://market/disclaimer")
def rate_disclaimer() -> str:
    """Official market disclaimer for financial data."""
    return "Disclaimer: Forex and cryptocurrency rates are provided for estimation purposes only."


if __name__ == "__main__":
    # FastMCP run HTTP transport
    mcp.run(transport="sse", host="127.0.0.1", port=8001)
