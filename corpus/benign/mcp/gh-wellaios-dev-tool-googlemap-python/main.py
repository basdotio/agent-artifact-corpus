from dotenv import load_dotenv

# Load environment variables from a .env file
load_dotenv()

from fastmcp import FastMCP
from starlette.middleware import Middleware
from wellaios.google_map import find_on_google_map

# Import custom authentication middleware and token generation/matching utility
from wellaios.authenticate import (
    AuthenticationMiddleware,
)

import uvicorn

# Initialize FastMCP application with a specific name for this demo
mcp = FastMCP("wellaios-demo")

# This special token indicates to WELLAIOS that user authorization is required
REQUEST_AUTH_TOKEN = "[AUTH]"


@mcp.tool()
async def find_on_map(query: str) -> str:
    """
    Uses the Google Places API to find locations based on a specific text query.

    Args:
        query: The search term to find locations. This query should include a specific location
               (e.g., "Italian restaurant in Paris", "Museum in Tokyo"). Queries like "near me"
               may not yield intended results on a server without location context.

    Returns:
        A JSON string containing information about the found places, including their display name,
        formatted address, and Google Maps link. Returns "Error in calling the tool" if the API call fails.
    """
    return find_on_google_map(query)


if __name__ == "__main__":
    # Define the list of custom middleware to be applied to the HTTP application.
    custom_middleware = [Middleware(AuthenticationMiddleware)]
    # Create the FastMCP HTTP application instance, applying the configured middleware
    http_app = mcp.http_app(middleware=custom_middleware)
    # Run the Uvicorn server, making the application accessible on all network interfaces
    # at port 30000.
    uvicorn.run(http_app, host="0.0.0.0", port=30000)