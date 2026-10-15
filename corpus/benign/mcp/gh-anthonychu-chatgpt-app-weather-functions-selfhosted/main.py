import fastmcp
from fastmcp import FastMCP
from fastmcp.tools.tool import ToolResult
from pathlib import Path
import requests

fastmcp.settings.stateless_http = True

mcp = FastMCP("My MCP Server")

# Add the weather widget HTML file as a resource for ChatGPT
@mcp.resource("ui://widget/current-weather.html", mime_type="text/html+skybridge")
def get_weather_widget() -> str:
    """Interactive HTML widget to display current weather data in ChatGPT."""
    widget_path = Path(__file__).parent / "current_weather_widget.html"
    return widget_path.read_text()

@mcp.tool(
    annotations={
        "title": "Get Current Weather",
        "readOnlyHint": True,
        "openWorldHint": True,
    },
    meta={
        "openai/outputTemplate": "ui://widget/current-weather.html",
        "openai/toolInvocation/invoking": "Fetching weather data",
        "openai/toolInvocation/invoked": "Weather data retrieved"
    },
)
def get_current_weather(latitude: float, longitude: float) -> ToolResult:
    """Get current weather for a given latitude and longitude using Open-Meteo API."""
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current_weather=true"
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        
        current_weather = data.get("current_weather", {})
        temperature = current_weather.get("temperature")
        windspeed = current_weather.get("windspeed")
        winddirection = current_weather.get("winddirection")
        weathercode = current_weather.get("weathercode")
        
        content_text = f"Current weather at ({latitude}, {longitude}): {temperature}°C, Wind: {windspeed} km/h from {winddirection}°, Weather code: {weathercode}"
        
        return ToolResult(
            content=content_text,
            structured_content=data
        )
    except requests.RequestException as e:
        error_msg = f"Error fetching weather data: {str(e)}"
        return ToolResult(
            content=error_msg,
            structured_content={"error": str(e)}
        )



if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
