from firecrawl import FirecrawlApp
from langchain.tools import tool
import os
from dotenv import load_dotenv

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

firecrawl = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

@tool
def scrape_with_firecrawl(url:str) -> str:
    """Use this to scrape a website with firecrawl"""
    try:
        scrape_status = firecrawl.scrape_url(url, formats=["markdown", "html"])
        return scrape_status
    except Exception as e:
        return f"Error scraping website: {e}"

@tool
def crawl_with_firecrawl(url:str) -> str:
    """Use this to crawl a website with firecrawl"""
    try:
        crawl_status = firecrawl.crawl_url(url, formats=["markdown", "html"])
        return crawl_status
    except Exception as e:
        return f"Error crawling website: {e}"

@tool
def map_with_firecrawl(url:str) -> str:
    """Use this to map a website with firecrawl"""
    try:
        map_status = firecrawl.map_url(url, formats=["markdown", "html"])
        return map_status
    except Exception as e:
        return f"Error mapping website: {e}"

