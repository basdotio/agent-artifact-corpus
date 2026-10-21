from typing import Any
from app.bll.agents.urban_renewal_gis_agent import (
    CITY_GIS_RENEWAL_DB,
    UrbanRenewalGISAgent,
    UrbanRenewalGISContext,
)
from mcp_servers.proptech_mcp_server import FastMCP

mcp = FastMCP("PropTech-Geospatial-GIS-MCP")


@mcp.tool()
async def mcp_get_urban_renewal_and_transit_gis(
    city: str,
    address: str,
    area_sqm: float = 95.0,
) -> dict[str, Any]:
    """Retrieve TAMA 38 / Pinui-Binui urban renewal feasibility, Light Rail distance, and Walkability score."""
    agent = UrbanRenewalGISAgent()
    res = await agent.run(
        UrbanRenewalGISContext(
            city=city,
            address=address,
            area_sqm=area_sqm,
        )
    )
    return res.model_dump()


@mcp.tool()
def mcp_list_supported_gis_cities() -> list[str]:
    """List Israeli cities with high-resolution GIS & TAMA 38 benchmark layers."""
    return list(CITY_GIS_RENEWAL_DB.keys())


if __name__ == "__main__":
    mcp.run()
