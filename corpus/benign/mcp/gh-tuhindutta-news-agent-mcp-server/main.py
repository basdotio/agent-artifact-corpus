import os
import json
from fastmcp import FastMCP
from endpoint import EndPoint
from news_api import NewsAPI
from website_scraper import WebsiteScraper
from urllib.parse import urlparse
from dotenv import load_dotenv
load_dotenv()


NEWSDATA_API_KEY = os.getenv("NEWSDATA_API_KEY")
FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

if not NEWSDATA_API_KEY:
    raise RuntimeError("NEWSDATA_API_KEY not set")

if not FIRECRAWL_API_KEY:
    raise RuntimeError("FIRECRAWL_API_KEY not set")

ep = EndPoint(NEWSDATA_API_KEY)
news = NewsAPI(ep)

scraper = WebsiteScraper(FIRECRAWL_API_KEY)


mcp = FastMCP(
    name="NewsAndWebsiteDataFetcher",
    instructions="""
        This server provides current news.
        Call get_latest_news(topic:str) to get the latest news on the topic.
        Call get_website_data(url:str) to get text content from the URL.
    """
)


@mcp.tool()
def get_latest_news(topic:str) -> str:
    """It takes topic string and returns a list of news article dictionaries."""
    try:
        data = '\n'.join([json.dumps(i.model_dump()) for i in news.get_latest_news(topic)])
        return data
    except Exception as e:
        return f"error: {str(e)}"

@mcp.tool()
def scrape_website(url:str) -> str:
    """It takes URL string and returns string."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return "Invalid URL"
        return scraper.data(url)
    except Exception as e:
        return f"Error fetching website data: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000)

