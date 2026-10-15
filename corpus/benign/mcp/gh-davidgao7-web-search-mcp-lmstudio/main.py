# local_search_server.py

from mcp.server.fastmcp import FastMCP
from duckduckgo_search import DDGS
import requests
from bs4 import BeautifulSoup

mcp = FastMCP(
    "Local Web Search",
    "A local server that searches DuckDuckGo and fetches page content."
)

@mcp.tool()
def web_search(
    query: str,
    num_results: int = 10,
    region: str = "us-en",
    safesearch: str = "off",
    timelimit: str | None = None
) -> str:
    """
    Performs a web search using DuckDuckGo with customizable settings.

    - query: The search term.
    - num_results: Number of results to return.
    - region: 'us-en', 'uk-en', 'de-de', etc.
    - safesearch: 'on', 'moderate', 'off'.
    - timelimit: 'd' (day), 'w' (week), 'm' (month), 'y' (year).
    """
    print(f"Received search query: '{query}' with settings: region={region}, safesearch={safesearch}, timelimit={timelimit}")
    try:
        # --- MODIFIED LINE ---
        with DDGS() as ddgs:
            results = list(ddgs.text(
                keywords=query,
                region=region,
                safesearch=safesearch,
                timelimit=timelimit,
                max_results=num_results
            ))

        if not results:
            return "No results found for that query."

        formatted_results = ""
        for i, result in enumerate(results, 1):
            formatted_results += f"Result {i}:\n"
            formatted_results += f"  Title: {result['title']}\n"
            formatted_results += f"  URL: {result['href']}\n"
            formatted_results += f"  Snippet: {result['body']}\n\n"

        print("Search successful. Returning formatted results.")
        return formatted_results.strip()

    except Exception as e:
        print(f"An error occurred during search: {e}")
        return f"Error: Could not perform the search. Details: {e}"

# ... (The rest of the file remains unchanged) ...
@mcp.tool()
def get_page_content(url: str) -> str:
    # ... (no changes here) ...
    print(f"Fetching content from URL: {url}")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        for script_or_style in soup(["script", "style"]):
            script_or_style.decompose()

        text = soup.get_text()
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)

        print("Successfully fetched and parsed page content.")
        return text[:4000] + "... (truncated)" if len(text) > 4000 else text

    except requests.RequestException as e:
        print(f"An error occurred while fetching the URL: {e}")
        return f"Error: Could not fetch the URL. Details: {e}"

if __name__ == "__main__":
    mcp.run()
