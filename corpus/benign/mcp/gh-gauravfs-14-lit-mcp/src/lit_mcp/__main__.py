from mcp.server.fastmcp import FastMCP

from .prompts import latest_info_prompt, related_topics_prompt, author_spotlight_prompt
from .utils import find_arxiv_publications, find_dblp_publications

mcp = FastMCP("lit-mcp")

@mcp.tool(
    name="arxiv_search",
    description="Search for papers on arXiv."
)
def arxiv_search(query: str, max_results: int = 10) -> list[dict]:
    """Search for papers on arXiv.
    Args:
        query: The query to search for.
        max_results: The maximum number of results to return. Defaults to 10.

    Returns:
        A list of dictionaries with the following keys: title, authors, published, summary, entry_id, pdf_url, categories, doi.
    """
    return find_arxiv_publications(query, max_results)

@mcp.tool(
    name="dblp_search",
    description="Search DBLP database for computer science papers."
)
def dblp_search(query: str, max_results: int = 10) -> list[dict]:
    """Search DBLP database for computer science papers.
    Args:
        query: The query to search for.
        max_results: The maximum number of results to return. Defaults to 10.

    Returns:
        A list of dictionaries with the following keys: title, authors, venue, volume, number, pages, publisher, year, type, access, key, doi, ee, url.
    """
    return find_dblp_publications(query, max_results)

@mcp.prompt(
    name="latest_info",
    description="Generate a well-structured and readable summary of the most recent innovations, trends, and papers in a given research field."
)
def latest_info(topic: str) -> str:
    """
    Generate a detailed, accessible overview of the latest innovations, research breakthroughs,
    and emerging trends in the given field using sources such as arXiv and DBLP.
    """
    return latest_info_prompt(topic)

@mcp.prompt(
    name="related_topics",
    description="Discover related and emerging research areas connected to a given topic."
)
def related_topics(topic: str) -> str:
    return related_topics_prompt(topic)

@mcp.prompt(
    name="author_spotlight",
    description="Identify leading authors, labs, and research groups advancing innovation in the field."
)
def author_spotlight(topic: str) -> str:
    return author_spotlight_prompt(topic)

def main():
    """Entry point for the MCP server when run as a script."""
    mcp.run()

if __name__ == "__main__":
    main()
