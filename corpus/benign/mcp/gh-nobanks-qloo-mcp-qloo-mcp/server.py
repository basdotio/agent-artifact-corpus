"""MCP server exposing the Qloo Taste AI API as agent tools."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Awaitable, Callable

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool
from pydantic import BaseModel, ValidationError

from .client import QlooAPIError, QlooClient
from .schemas import (
    GetDemographicsInput,
    GetInsightsInput,
    GetTasteAnalysisInput,
    ListAudiencesInput,
    SearchEntitiesInput,
    SearchTagsInput,
    TasteMatchInput,
)
from .taste_match import run_taste_match

APP_NAME = "qloo-mcp"

server = Server(APP_NAME)


def _get_client() -> QlooClient:
    """Build a Qloo client from the current environment."""
    return QlooClient()


def _dump(payload: Any) -> list[TextContent]:
    return [TextContent(type="text", text=json.dumps(payload, indent=2))]


def _error(kind: str, message: str, status_code: int | None = None) -> list[TextContent]:
    payload: dict[str, Any] = {"error": kind, "message": message}
    if status_code is not None:
        payload["status_code"] = status_code
    return _dump(payload)


async def _run_search_entities(client: QlooClient, inp: SearchEntitiesInput) -> dict[str, Any]:
    return await client.search_entities(inp)


async def _run_search_tags(client: QlooClient, inp: SearchTagsInput) -> dict[str, Any]:
    return await client.search_tags(inp)


async def _run_list_audiences(client: QlooClient, inp: ListAudiencesInput) -> dict[str, Any]:
    return await client.list_audiences(inp)


async def _run_get_insights(client: QlooClient, inp: GetInsightsInput) -> dict[str, Any]:
    return await client.get_insights(inp)


async def _run_get_demographics(client: QlooClient, inp: GetDemographicsInput) -> dict[str, Any]:
    return await client.get_demographics(inp)


async def _run_get_taste_analysis(client: QlooClient, inp: GetTasteAnalysisInput) -> dict[str, Any]:
    return await client.get_taste_analysis(inp)


async def _run_taste_match(client: QlooClient, inp: TasteMatchInput) -> dict[str, Any]:
    return await run_taste_match(client, inp)


_TOOL_SPECS: list[tuple[str, str, type[BaseModel], Callable[[QlooClient, Any], Awaitable[dict[str, Any]]]]] = [
    (
        "search_entities",
        "Look up Qloo entity IDs by name across artists, books, brands, destinations, movies, people, places, podcasts, TV shows and video games.",
        SearchEntitiesInput,
        _run_search_entities,
    ),
    (
        "search_tags",
        "Look up Qloo tag IDs (genres, cuisines, keywords, styles) by partial name.",
        SearchTagsInput,
        _run_search_tags,
    ),
    (
        "list_audiences",
        "List Qloo audience segments, optionally filtered by audience type URN.",
        ListAudiencesInput,
        _run_list_audiences,
    ),
    (
        "get_insights",
        "Taste-based recommendations: entities of one type ranked by affinity to the given entity, tag, demographic and location signals.",
        GetInsightsInput,
        _run_get_insights,
    ),
    (
        "get_demographics",
        "Age and gender affinity breakdown for the audience of given entities or tags.",
        GetDemographicsInput,
        _run_get_demographics,
    ),
    (
        "get_taste_analysis",
        "Tags that best describe the taste of an audience, entity set, or location.",
        GetTasteAnalysisInput,
        _run_get_taste_analysis,
    ),
    (
        "taste_match",
        "Composite agent tool: given an artwork or song description from an independent artist, resolves influences and keywords to Qloo IDs and returns the audiences, places, artists, brands and taste tags whose taste overlaps the work.",
        TasteMatchInput,
        _run_taste_match,
    ),
]

_TOOL_INDEX: dict[str, tuple[type[BaseModel], Callable[[QlooClient, Any], Awaitable[dict[str, Any]]]]] = {
    name: (model, handler) for name, _description, model, handler in _TOOL_SPECS
}


@server.list_tools()
async def list_tools() -> list[Tool]:
    """Return the tool catalog exposed to MCP clients."""
    return [
        Tool(
            name=name,
            description=description,
            inputSchema=model.model_json_schema(),
        )
        for name, description, model, _handler in _TOOL_SPECS
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Validate arguments, call Qloo, and return structured JSON text content."""
    spec = _TOOL_INDEX.get(name)
    if spec is None:
        return _error("unknown_tool", f"Unknown tool: {name}")

    model, handler = spec

    try:
        validated = model.model_validate(arguments or {})
    except ValidationError as exc:
        return _error("invalid_input", str(exc))

    try:
        client = _get_client()
    except ValueError:
        return _error("missing_api_key", "Set QLOO_API_KEY")

    try:
        result = await handler(client, validated)
    except QlooAPIError as exc:
        return _error("qloo_api_error", exc.message, exc.status_code)

    return _dump(result)


async def main() -> None:
    """Run the MCP server over stdio."""
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main_sync() -> None:
    """Synchronous entry point."""
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
