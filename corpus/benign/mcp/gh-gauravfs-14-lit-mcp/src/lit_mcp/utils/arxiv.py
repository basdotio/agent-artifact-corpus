import arxiv

def find_arxiv_publications(query: str, max_results: int = 10) -> list[dict]:
    """Search for papers on arXiv."""
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.Relevance,
        sort_order=arxiv.SortOrder.Descending,
    )
    results = list(search.results())
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

