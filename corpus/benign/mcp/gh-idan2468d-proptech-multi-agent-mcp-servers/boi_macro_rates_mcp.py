from typing import Any
from mcp_servers.proptech_mcp_server import FastMCP

mcp = FastMCP("PropTech-BOI-Macro-Rates-MCP")


@mcp.tool()
def mcp_get_boi_macro_rates() -> dict[str, Any]:
    """Return current Bank of Israel base rate, Prime rate, CPI inflation, and average mortgage track rates."""
    return {
        "boi_base_rate_pct": 4.50,
        "prime_rate_pct": 6.00,
        "cpi_annual_inflation_pct": 3.10,
        "construction_input_index_annual_pct": 2.85,
        "recommended_mortgage_tracks": {
            "kalatz_non_linked_fixed_pct": 4.85,
            "prime_minus_margin_pct": 5.35,
            "malatz_5yr_variable_non_linked_pct": 4.70,
        },
    }


if __name__ == "__main__":
    mcp.run()
