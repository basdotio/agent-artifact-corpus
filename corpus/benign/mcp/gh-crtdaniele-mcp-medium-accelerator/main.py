from mcp.server.fastmcp import FastMCP
import httpx
from bs4 import BeautifulSoup
import os
from tinydb import TinyDB, Query
from datetime import datetime

mcp = FastMCP("mcp-medium-accelerator")

home_dir = os.path.expanduser("~")
data_dir = os.path.join(home_dir, "mcp-medium-accelerator_data")
os.makedirs(data_dir, exist_ok=True)

db_path = os.path.join(data_dir, "summaries.json")
db = TinyDB(db_path)
summaries_table = db.table("summaries")

@mcp.tool(
    description="Extracts article links from a Medium archive URL. Returns a list of article links.",
    name="extract_article_links",
)
def extract_article_links(archive_url: str, limit: int = 10) -> list[str]:
    response = httpx.get(archive_url)
    soup = BeautifulSoup(response.text, "html.parser")
    links = []

    for div in soup.find_all("article", attrs={"data-testid": "post-preview"}):
        for inner_div in div.find_all("div"):
            if inner_div.has_attr("data-href"):
                div_with_data_href = inner_div["data-href"]
                break
        if div_with_data_href:
            href = div_with_data_href
            if href not in links:
                links.append(href)
            if len(links) >= limit:
                break

    return links

@mcp.tool(
    description="Saves a summary of an article with its title, URL, and tags. Returns a status message.",
    name="save_summary",
)
def save_summary(title: str, url: str, summary: str, tags: list[str] = []):
    entry = {
        "title": title,
        "url": url,
        "summary": summary,
        "tags": tags,
        "saved_at": datetime.utcnow().isoformat()
    }

    Article = Query()
    if summaries_table.contains(Article.url == url):
        return {"status": "already_saved"}

    summaries_table.insert(entry)
    return {"status": "ok"}

@mcp.tool(
    description="Lists all saved summaries. Returns a list of summaries.",
    name="list_summaries",
)
def list_summaries():
    return summaries_table.all()

@mcp.tool(
    description="Extracts the text content from a saved article summary. Ask if the user want to save it with save_summary.",
    name="extract_article_text",
)
def extract_article_text(url: str):
    response = httpx.get(url)
    soup = BeautifulSoup(response.text, "html.parser")
    article = soup.find("article")
    return article.get_text() if article else ""