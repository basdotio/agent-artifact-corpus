from fastmcp import FastMCP, Context
from fastmcp.server.lifespan import lifespan

from garage61.client import (
    Garage61Client,
    load_static_data,
)


@lifespan
async def app_lifespan(_server: FastMCP):
    client = None
    try:
        client = Garage61Client.from_env()
        await load_static_data(client)
        yield {"g61_client": client}
    finally:
        if client:
            await client.close()


mcp = FastMCP("garage61-race-engineer", lifespan=app_lifespan)


@mcp.tool()
async def list_tracks(ctx: Context) -> dict:
    """Returns available tracks so the agent can resolve a track name to a track_id."""
    client: Garage61Client = ctx.lifespan_context["g61_client"]
    return {
        "tracks": [
            {"track_id": t.track_id, "name": t.name, "variant": t.variant}
            for t in await client.get_tracks(use_cache=True)
        ]
    }


@mcp.tool()
async def list_cars(ctx: Context) -> dict:
    """Returns available cars so the agent can resolve a car name to a car_id."""
    client: Garage61Client = ctx.lifespan_context["g61_client"]
    return {
        "cars": [
            {"car_id": c.car_id, "name": c.name}
            for c in await client.get_cars(use_cache=True)
        ]
    }


if __name__ == "__main__":
    mcp.run()
