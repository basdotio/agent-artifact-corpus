import datetime
import json

from fastmcp import FastMCP

mcp = FastMCP("Resources")


@mcp.resource(
    "resource://greeting",
    name="Greeting",
    title="Greeting message",
    description="Return a greeting after the configured simulated delay.",
    mime_type="text/plain",
    tags={"demo", "greeting"},
)
def get_greeting() -> str:
    """Provides a simple greeting message."""
    return "Hello from FastMCP Resources!"


@mcp.resource(
    "resource://config",
    name="Application configuration",
    title="Application configuration",
    description="Read the current application theme, version, and enabled features.",
    mime_type="application/json",
    tags={"demo", "config"},
)
def get_config() -> str:
    """Provides application configuration as JSON."""
    return json.dumps(
        {
            "theme": "dark",
            "version": "1.2.0",
            "features": ["tools", "resources"],
        }
    )


@mcp.resource(
    "resource://time",
    name="Current UTC time",
    title="Current UTC time",
    description="Return the current UTC time.",
    mime_type="text/plain",
    tags={"demo", "time"},
)
def get_current_time() -> str:
    """Provides the current UTC time."""
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    return f"RESOURCE: The current UTC time is {now}."


@mcp.resource(
    "resource://gps_position",
    name="Current GPS Position",
    title="Current GPS position",
    description="Return the current GPS position of the server.",
    mime_type="application/json",
    tags={"demo", "gps", "position"},
)
def get_current_gps_position() -> dict:
    """
    Get the current GPS position of the server.

    Returns:
        dict: A dictionary containing the latitude and longitude of the server's current GPS position.
    """
    # For demonstration purposes, we return a fixed GPS position.
    # In a real implementation, you would retrieve the actual GPS position from a GPS device or service.
    return {"latitude": 37.7749, "longitude": -122.4194}  # Example: San Francisco, CA
