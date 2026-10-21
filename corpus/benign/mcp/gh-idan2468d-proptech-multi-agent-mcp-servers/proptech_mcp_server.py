from typing import Any, Callable
from app.bll.agents.tools.financial_math import (
    calculate_israeli_purchase_tax,
    calculate_mortgage_schedule,
    compute_roi_metrics,
)
from app.dal.external.market_api_client import ExternalMarketAPIClient

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore
except ImportError:

    class FastMCP:  # type: ignore
        """Lightweight FastMCP-compatible server adapter when mcp package is not installed."""

        def __init__(self, name: str) -> None:
            self.name = name
            self.tools_registry: dict[str, Callable[..., Any]] = {}

        def tool(self, name: str | None = None) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                tool_name = name or func.__name__
                self.tools_registry[tool_name] = func
                return func

            return decorator

        def run(self) -> None:
            pass


mcp = FastMCP("PropTech-RealEstate-Analyzer-MCP")


@mcp.tool()
def mcp_calculate_mortgage(
    principal_ils: float,
    annual_rate_pct: float = 4.85,
    years: int = 25,
    method: str = "spitzer",
) -> dict[str, Any]:
    """Calculate deterministic Israeli mortgage schedule (Spitzer or Equal Principal)."""
    chosen_method = "equal_principal" if method == "equal_principal" else "spitzer"
    return calculate_mortgage_schedule(
        principal=principal_ils,
        annual_rate_pct=annual_rate_pct,
        years=years,
        method=chosen_method,  # type: ignore[arg-type]
    )


@mcp.tool()
def mcp_calculate_purchase_tax(
    property_price_ils: float,
    is_single_home: bool = False,
) -> dict[str, float]:
    """Calculate Israeli Purchase Tax (Mas Rechisha) brackets deterministically."""
    tax = calculate_israeli_purchase_tax(
        property_price_ils=property_price_ils,
        is_single_home=is_single_home,
    )
    return {
        "property_price_ils": property_price_ils,
        "purchase_tax_ils": tax,
        "effective_tax_rate_pct": round((tax / property_price_ils) * 100.0, 2),
    }


@mcp.tool()
def mcp_compute_property_roi(
    property_price_ils: float,
    equity_ils: float,
    monthly_rent_ils: float,
    annual_expenses_ils: float = 6000.0,
    monthly_mortgage_ils: float = 4500.0,
    appreciation_rate_pct: float = 3.0,
    is_single_home: bool = False,
) -> dict[str, float]:
    """Compute Gross Yield, Net Cap Rate, Cash-on-Cash, and 10-Yr IRR deterministically."""
    tax = calculate_israeli_purchase_tax(property_price_ils, is_single_home)
    return compute_roi_metrics(
        property_price_ils=property_price_ils,
        equity_ils=equity_ils,
        monthly_rent_ils=monthly_rent_ils,
        annual_expenses_ils=annual_expenses_ils,
        monthly_mortgage_ils=monthly_mortgage_ils,
        appreciation_rate_pct=appreciation_rate_pct,
        purchase_tax_ils=tax,
    )


@mcp.tool()
async def mcp_query_city_comps(city: str, area_sqm: float = 90.0) -> dict[str, Any]:
    """Query comparable real estate transactions and rent benchmarks for an Israeli city."""
    client = ExternalMarketAPIClient()
    return await client.fetch_city_market_data(city=city, area_sqm=area_sqm)


if __name__ == "__main__":
    mcp.run()
