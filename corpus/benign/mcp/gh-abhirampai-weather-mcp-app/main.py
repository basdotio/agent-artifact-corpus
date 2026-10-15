"""Application entry point for the Weather MCP server."""

from fastmcp import FastMCP

from src.dashboard import build_dashboard
from src.services.weather_service import WeatherService
from src.tools import register_tools

mcp = FastMCP("Weather MCP")
weather = WeatherService()
get_weather = register_tools(mcp, weather)


@mcp.tool(app=True)
def weather_dashboard(
    location: str,
    forecast_days: int = 5,
    temperature_unit: str = "celsius",
):
    """Show an interactive weather dashboard with location and unit controls."""
    return build_dashboard(get_weather, location, forecast_days, temperature_unit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
