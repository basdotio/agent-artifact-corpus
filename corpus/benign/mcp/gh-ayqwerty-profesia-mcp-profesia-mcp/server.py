"""MCP server exposing profesia.sk job search (built on FastMCP).

Tools
-----
* ``search_jobs`` -- free-text search in a city with a km radius, returns a
  markdown table of matching offers.
* ``suggest_location`` -- resolve a city/region name to the concrete
  locations (with numeric ``region_id``) the search endpoint understands.
* ``read_job`` -- read one offer's full details (by its URL from
  ``search_jobs``) and return them as a markdown document.
"""

from __future__ import annotations

import json

from fastmcp import FastMCP

from .searcher import DEFAULT_RADIUS_KM, MAX_RADIUS_KM, Profesia

mcp = FastMCP(
    name="profesia-mcp",
    version="0.2.2",
    instructions=(
        "Search jobs on profesia.sk (Slovak job board). Usually pass keyword "
        "plus a Slovak city to search_jobs directly; it resolves the city "
        "automatically and reports which location it used. Only call "
        "suggest_location when a place name is ambiguous, then pass the exact "
        "name (or its region_id) back to search_jobs. Use read_job with an "
        "offer's URL (from search_jobs) to get its full details."
    ),
)


# One client per process: the HTTP session and the anti-bot token are reused
# across tool calls instead of being rebuilt on every request.
_client = Profesia()


def _resolve_region_id(client: Profesia, city: str) -> tuple[str, str]:
    """Resolve a place name to (region_id, resolved_name).

    Prefers an exact municipality match; otherwise returns the top
    suggestion. Raises ValueError if nothing matches.
    """
    suggestions = client.suggest_location(city)
    if not suggestions:
        raise ValueError(f"could not locate any place named {city!r}")

    lowered = city.strip().lower()
    for s in suggestions:
        if s.region_type == "municipality" and s.name.lower() == lowered:
            return s.region_id, s.name

    chosen = suggestions[0]
    return chosen.region_id, chosen.name


@mcp.tool(
    description=(
        "Resolve a place name into the locations profesia.sk understands. "
        "Returns a JSON array of {region_id, name, region_type}. Pass a "
        "place name to search_jobs.city, or a region_id from here to "
        "search_jobs.region_id, to pin the exact location."
    ),
    annotations={
        "title": "Suggest a location",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def suggest_location(city: str) -> str:
    suggestions = _client.suggest_location(city)
    payload = [s.asdict() for s in suggestions]
    return json.dumps(payload, ensure_ascii=False, indent=2)


@mcp.tool(
    description=(
        "Search profesia.sk jobs. Keyword accepts space or comma for OR "
        "matches. Location is optional: pass a Slovak place `city` "
        "(resolved automatically) or a `region_id` from suggest_location "
        "to pin the exact spot; omit both for a site-wide search. "
        "`radius_km` only applies with a location and snaps to "
        "0/10/20/30/60/100 (max 100). Returns a markdown table preceded by "
        "the total number of offers matching the search."
    ),
    annotations={
        "title": "Search job offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def search_jobs(
    keyword: str,
    city: str | None = None,
    region_id: str | None = None,
    radius_km: int = DEFAULT_RADIUS_KM,
    page: int = 1,
) -> str:
    if page < 1:
        raise ValueError("page must be a positive integer")
    if not 0 <= radius_km <= MAX_RADIUS_KM:
        raise ValueError(f"radius_km must be between 0 and {MAX_RADIUS_KM}")

    rid, where = region_id, None
    if city is not None:
        # A place name takes precedence over an explicit region_id.
        rid, where = _resolve_region_id(_client, city)
    elif rid is not None:
        where = f"region_id {rid}"

    offers, total = _client.search(
        keyword=keyword,
        region_id=rid,
        radius_km=radius_km,
        page=page,
    )

    if total is None:
        # No count rendered (typically zero results): the page itself is
        # all we know.
        count = f"Found {len(offers)} offer(s)"
        tail = f", page {page}.\n"
    else:
        count = (
            f"Found {total:,} offer(s) matching the search "
            f"(page {page} lists {len(offers)})"
        )
        tail = ".\n"

    if where is None:
        head = f"{count} for {keyword!r} (site-wide){tail}"
    else:
        head = f"{count} for {keyword!r} near {where}, radius={radius_km}km{tail}"
    return head + Profesia.to_markdown(offers)


@mcp.tool(
    description=(
        "Read full details of a single job offer from its URL (the URL "
        "column from search_jobs). Returns a markdown document: header "
        "fields (employer, location, employment type, salary, published "
        "date), badges, the full description/requirements text and the "
        "company info block."
    ),
    annotations={
        "title": "Read one job offer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
def read_job(url: str) -> str:
    return _client.get_offer(url).to_markdown()


def main() -> None:
    # The banner is printed to stdout; over stdio that stream is the JSON-RPC
    # channel, so a banner would corrupt it. Keep it disabled for server runs.
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
