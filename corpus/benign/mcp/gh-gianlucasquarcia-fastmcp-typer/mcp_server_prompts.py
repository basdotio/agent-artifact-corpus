from fastmcp import FastMCP

mcp = FastMCP("Prompts")


@mcp.prompt(
    title="Weather Briefing",
    description="Prepare a concise weather briefing for geographic coordinates.",
    tags={"weather", "forecast", "briefing"},
)
def weather_briefing(latitude: float, longitude: float) -> str:
    """Prepare a concise weather briefing for a location."""
    return (
        f"Provide a concise weather briefing for latitude {latitude} and "
        f"longitude {longitude}. First call the `open_meteo_current_forecast` "
        f"tool with latitude={latitude} and longitude={longitude} to obtain "
        "current data, then summarize the current temperature and wind speed."
    )
