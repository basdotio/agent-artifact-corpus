"""MCP server: lets any MCP client (Claude Desktop, Claude Code, IDEs, custom agents) search the legal
collection, read articles and produce citations.

    legal-mcp                                   # stdio (for Claude Desktop / Claude Code)
    legal-mcp --transport streamable-http       # HTTP on :8000/mcp
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Annotated, Literal

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import BaseModel, Field

from .library import ArticleNotFound, LegalLibrary

log = logging.getLogger("legal_mcp")
READ_ONLY = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)

INSTRUCTIONS = """Search and cite the laws of the (fictional) Republic of Norland.
Workflow: call search_legislation with the user's question, read the most relevant results with
get_article, and cite every legal statement with the citation string the tools return.
If nothing relevant is found, say so instead of guessing."""


class SearchHit(BaseModel):
    id: str = Field(description="Article id, e.g. 'RT-2'; pass it to get_article or cite_article")
    citation: str
    snippet: str = Field(description="Best-matching passage, query terms in **bold**")
    score: float


class SearchResult(BaseModel):
    query: str
    results: list[SearchHit]


class Article(BaseModel):
    id: str
    citation: str
    act: str
    article: int
    year: int
    heading: str
    text: str
    previous_article: str | None
    next_article: str | None


class ActInfo(BaseModel):
    code: str
    name: str
    year: int
    articles: int


def create_server(library: LegalLibrary | None = None, host: str = "127.0.0.1", port: int = 8000) -> FastMCP:
    lib = library or LegalLibrary()
    mcp = FastMCP("norland-legal", instructions=INSTRUCTIONS, host=host, port=port)

    @mcp.tool(annotations=READ_ONLY)
    def search_legislation(
        query: Annotated[str, Field(min_length=2, max_length=500, description="Question or keywords, in plain language")],
        k: Annotated[int, Field(ge=1, le=20, description="Number of articles to return")] = 5,
        act_codes: Annotated[list[str] | None, Field(description="Limit to acts, e.g. ['RT'] (see list_acts)")] = None,
        year_from: Annotated[int | None, Field(description="Only acts adopted in or after this year")] = None,
        year_to: Annotated[int | None, Field(description="Only acts adopted in or before this year")] = None,
        mode: Literal["hybrid", "bm25", "dense"] = "hybrid",
    ) -> SearchResult:
        """Find the legal articles most relevant to a question, using hybrid keyword + semantic search."""
        try:
            hits = lib.search(query, k, act_codes, year_from, year_to, mode)
        except ArticleNotFound as e:
            raise ToolError(str(e.args[0])) from e
        log.info("search %r -> %s", query, [h["id"] for h in hits])
        return SearchResult(query=query, results=[SearchHit(**h) for h in hits])

    @mcp.tool(annotations=READ_ONLY)
    def get_article(article_id: Annotated[str, Field(description="Article id such as 'DP-6'")]) -> Article:
        """Return the full text of one article, with its citation and neighbouring article ids."""
        try:
            d = lib.article(article_id)
        except ArticleNotFound as e:
            raise ToolError(str(e.args[0])) from e
        m = d.metadata
        siblings = [x.id for x in lib.act_articles(m["act_code"])]
        i = siblings.index(d.id)
        return Article(id=d.id, citation=lib.cite(d.id), act=m["act"], article=m["article"], year=m["year"],
                       heading=d.title.split(": ", 1)[-1], text=d.text,
                       previous_article=siblings[i - 1] if i > 0 else None,
                       next_article=siblings[i + 1] if i + 1 < len(siblings) else None)

    @mcp.tool(annotations=READ_ONLY)
    def list_acts() -> list[ActInfo]:
        """List the acts in the collection with their codes (usable as filters), years and article counts."""
        return [ActInfo(code=a.code, name=a.name, year=a.year, articles=a.articles) for a in lib.acts.values()]

    @mcp.tool(annotations=READ_ONLY)
    def cite_article(article_id: str, style: Literal["full", "short"] = "full") -> str:
        """Format a citation, e.g. full: 'Residential Tenancy Act (2017), Article 2 (Security deposit)'; short: 'RTA 2017, art. 2'."""
        try:
            return lib.cite(article_id, style)
        except ArticleNotFound as e:
            raise ToolError(str(e.args[0])) from e

    @mcp.resource("legal://acts/{code}", mime_type="text/markdown")
    def act_text(code: str) -> str:
        """The full text of an act as Markdown."""
        arts = lib.act_articles(code)
        act = lib.acts[code.upper()]
        body = "\n\n".join(f"## Article {d.metadata['article']}: {d.title.split(': ', 1)[-1]}\n\n{d.text}" for d in arts)
        return f"# {act.name} ({act.year})\n\n{body}"

    @mcp.prompt()
    def answer_with_citations(question: str) -> str:
        """Answer a legal question using the tools, citing every statement."""
        return (f"Answer this question about Norland law: {question}\n\n"
                "1. Call search_legislation with the question.\n"
                "2. Read the top results with get_article.\n"
                "3. Answer in plain language, citing each statement with the article's citation.\n"
                "4. If the articles don't answer it, say so. Remind the user this is not legal advice.")

    return mcp


def main() -> None:
    p = argparse.ArgumentParser(description="Norland legal MCP server")
    p.add_argument("--transport", default="stdio", choices=["stdio", "streamable-http"])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    a = p.parse_args()
    # stdout carries the MCP protocol over stdio, so logs must go to stderr
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(asctime)s %(name)s %(message)s")
    create_server(host=a.host, port=a.port).run(transport=a.transport)


if __name__ == "__main__":
    main()
