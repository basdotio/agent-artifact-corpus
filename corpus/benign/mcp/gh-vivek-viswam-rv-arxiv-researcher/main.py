from pathlib import Path
from urllib.request import urlretrieve

import arxiv
from fastmcp import FastMCP

from constants import DEFAULT_DOWNLOAD_PATH, DEFAULT_RESULT_COUNT
from models import Article, DownloadResponse, SearchResponse

mcp = FastMCP()
arxiv_client = arxiv.Client()

@mcp.tool()
def search(query: str, count: int = DEFAULT_RESULT_COUNT) -> SearchResponse:
    """
    Search for arXiv articles matching the query and return the results as dict.
    """

    search_query = arxiv.Search(
        query=query,
        max_results=count,
        sort_by=arxiv.SortCriterion.Relevance
    )

    results = [
        Article(
            article_id=result.get_short_id(),
            title=result.title,
            authors=[author.name for author in result.authors],
            summary=result.summary,
            published=result.published.isoformat(),
            pdf_url=result.pdf_url,
        )
        for result in arxiv_client.results(search_query)
    ]

    return SearchResponse(results=results)


@mcp.tool()
def download_article(
    article_id: str,
    directory: str = DEFAULT_DOWNLOAD_PATH,
    filename: str | None = None,
) -> DownloadResponse:
    """Download an arXiv article PDF and return its saved path."""

    search_query = arxiv.Search(id_list=[article_id], max_results=1)
    result = next(arxiv_client.results(search_query), None)
    if result is None:
        raise ValueError(f"No arXiv article found for ID: {article_id}")

    output_directory = Path(directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    output_path = output_directory / (filename or f"{article_id}.pdf")
    path, _ = urlretrieve(result.pdf_url, str(output_path))

    return DownloadResponse(
        article_id=article_id,
        title=result.title,
        path=str(path),
        pdf_url=result.pdf_url,
    )

if __name__ == "__main__":
    mcp.run()
