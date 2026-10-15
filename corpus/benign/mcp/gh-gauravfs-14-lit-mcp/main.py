from mcp.server.fastmcp import FastMCP
from utils import search_arxiv

mcp = FastMCP("lit-mcp")

@mcp.tool()
def arxiv_search(query: str, max_results: int = 10) -> list[dict]:
    """Search for papers on arXiv.
    Args:
        query: The query to search for.
        max_results: The maximum number of results to return. Defaults to 10.

    Returns:
        A list of dictionaries with the following keys: title, authors, published, summary, entry_id, pdf_url, categories, doi.
    """
    results = search_arxiv(query, max_results)
    results_dict = []
    for result in results:
        result_dict = {
            'title': result.title.encode('utf-8').decode('utf-8'),
            'authors': [str(author) for author in result.authors],
            'published': result.published.isoformat() if result.published else None,
            'summary': result.summary.encode('utf-8').decode('utf-8'),
            'entry_id': result.entry_id,
            'pdf_url': result.pdf_url,
            'categories': result.categories,
            'doi': result.doi
        }
        results_dict.append(result_dict)
    return results_dict

def main():
    """Entry point for the MCP server when run as a script."""
    mcp.run()

if __name__ == "__main__":
    main()
