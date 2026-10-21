from exa_py import Exa
from langchain_core.tools import tool
import os

exa = Exa(api_key=os.getenv("EXA_API_KEY"))

@tool
def search_and_contents(query: str):
    """Search for webpages based on the query and retrieve their contents."""
    response = exa.search_and_contents(
        query, use_autoprompt=True, num_results=5, text=True, highlights=True
    )
    # Format response as a string
    formatted_results = "\n".join([
        f"Title: {result.title}\nURL: {result.url}\nText: {result.text}\nHighlights: {result.highlights}"
        for result in response.results
    ])
    return formatted_results or "No results found."

@tool
def find_similar_and_contents(url: str):
    """Search for webpages similar to a given URL and retrieve their contents.
    The url passed in should be a URL returned from `search_and_contents`.
    """
    try:
        response = exa.find_similar_and_contents(url, num_results=5, text=True, highlights=True)
        # Format response as a string
        formatted_results = "\n".join([
            f"Title: {result.title}\nURL: {result.url}\nText: {result.text}\nHighlights: {result.highlights}"
            for result in response.results
        ])
        return formatted_results or "No similar results found."
    except Exception as e:
        return f"Error finding similar content: {str(e)}"
