"""Statutory retrieval, search, publication, and reference domain sub-server."""

from __future__ import annotations

import logging
from typing import Any

from fastmcp import FastMCP
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ArgTransformConfig, ToolTransformConfig
from mcp.types import ToolAnnotations

from taxcode_mcp.db import db
from taxcode_mcp.errors import tool_error

logger = logging.getLogger(__name__)

ANNOTATION_READ_ONLY = ToolAnnotations(
    read_only_hint=True,
    destructive_hint=False,
    idempotent_hint=True,
    open_world_hint=False,
)

statutes_server = FastMCP(
    "taxcode-statutes",
    instructions="Authoritative statutory search, citation retrieval, and circulars.",
)

statutes_server.add_transform(
    ToolTransform(
        {
            "search_tax_code": ToolTransformConfig(
                arguments={
                    "client_id": ArgTransformConfig(hide=True, default="taxcode-client-default")
                }
            )
        }
    )
)


@statutes_server.tool(
    name="lookup_statute",
    description=(
        "Retrieve exact statutory language, temporal version, and metadata by "
        "citation or section code."
    ),
    annotations=ANNOTATION_READ_ONLY,
    tags={"statutes", "read_only"},
)
async def lookup_statute(
    citation_or_section: str,
    jurisdiction: str | None = None,
    tax_year: int | None = None,
    lang: str = "en",
) -> dict[str, Any]:
    """Find a statute by exact citation or section code in DuckDB."""
    try:
        result = db.lookup_statute(
            citation_or_section=citation_or_section,
            jurisdiction=jurisdiction,
            tax_year=tax_year,
            lang=lang,
        )
        if result is None:
            msg = f"Statute matching '{citation_or_section}'"
            if tax_year:
                msg += f" for tax year {tax_year}"
            if jurisdiction:
                msg += f" in jurisdiction '{jurisdiction}'"
            return {
                "status": "not_found",
                "query": citation_or_section,
                "tax_year": tax_year,
                "jurisdiction": jurisdiction,
                "message": f"{msg} not found in indexed corpora.",
            }
        return {"status": "success", "data": result}
    except Exception as exc:
        failure = tool_error(exc)
    raise failure from None


@statutes_server.tool(
    name="search_tax_code",
    description=(
        "Keyword and concept search across Federal and State statutory corpora, "
        "ordered by tax year descending."
    ),
    annotations=ANNOTATION_READ_ONLY,
    tags={"statutes", "search", "read_only"},
)
async def search_tax_code(
    query: str,
    jurisdiction: str | None = None,
    corpus: str | None = None,
    tax_year: int | None = None,
    limit: int = 5,
    client_id: str = "taxcode-client-default",
) -> dict[str, Any]:
    """Search statutes by keywords or concepts in DuckDB."""
    try:
        matches = db.search_statutes(
            query=query,
            jurisdiction=jurisdiction,
            corpus=corpus,
            tax_year=tax_year,
            limit=limit,
        )
        return {
            "status": "success",
            "query": query,
            "tax_year": tax_year,
            "jurisdiction": jurisdiction,
            "count": len(matches),
            "results": matches,
            "client_id": client_id,
        }
    except Exception as exc:
        failure = tool_error(exc)
    raise failure from None


@statutes_server.tool(
    name="list_publications",
    description="List administrative circulars, tax guidance publications, and bulletins.",
    annotations=ANNOTATION_READ_ONLY,
    tags={"statutes", "publications", "read_only"},
)
async def list_publications(
    category: str | None = None,
    since_date: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """List administrative publications from DuckDB."""
    try:
        pubs = db.list_publications(category=category, since_date=since_date, limit=limit)
        return {"status": "success", "count": len(pubs), "publications": pubs}
    except Exception as exc:
        failure = tool_error(exc)
    raise failure from None


@statutes_server.resource("taxcode://statutes/{jurisdiction}/{section}")
async def get_statute_resource(jurisdiction: str, section: str) -> str:
    """Fetch statutory text as a resource by jurisdiction and section."""
    res = db.lookup_statute(citation_or_section=section, jurisdiction=jurisdiction)
    if not res:
        return f"Statute '{section}' in jurisdiction '{jurisdiction}' not found."
    return (
        f"{res['citation']} - {res['title']}\n"
        f"Jurisdiction: {res['jurisdiction']} ({res['corpus']})\n"
        f"Effective Year: {res['effective_year']}\n\n"
        f"{res['operative_text']}"
    )
