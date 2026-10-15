from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import httpx
import json
import os
from bs4 import BeautifulSoup
load_dotenv()

mcp = FastMCP("n8n-Assistant")

USER_AGENT = "n8n-assistant/1.0"
SERPER_URL="https://google.serper.dev/search"

n8n_urls = {
    "docs": "docs.n8n.io",
    "workflows": "n8n.io/workflows",
    "community": "community.n8n.io"
}

async def search_web(query: str) -> dict | None:
    payload = json.dumps({"q": query, "num": 5})

    headers = {
        "X-API-KEY": os.getenv("SERPER_API_KEY"),
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                SERPER_URL, headers=headers, data=payload, timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.TimeoutException:
            return {"organic": []}
        except Exception as e:
            return {"organic": [], "error": str(e)}
  
async def fetch_url(url: str):
  async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=30.0)
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Remove navigation, menus, headers, footers
            for nav in soup.find_all(['nav', 'header', 'footer', 'aside']):
                nav.decompose()
            
            # Remove script and style elements
            for script in soup.find_all(['script', 'style']):
                script.decompose()
                
            # Get main content if it exists
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup
            
            # Extract text and clean it
            text = main_content.get_text(separator=' ', strip=True)
            
            # Remove excessive whitespace
            import re
            text = re.sub(r'\s+', ' ', text)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            
            # Limit length to save tokens (optional, adjust as needed)
            max_length = 4000
            if len(text) > max_length:
                text = text[:max_length] + "... (content truncated)"
                
            return text
        except httpx.TimeoutException:
            return "Timeout error"
        except Exception as e:
            return f"Error fetching content: {str(e)}"

@mcp.tool()  
async def get_n8n_info(query: str, resource_type: str):
  """
  Search the latest n8n resources for a given query.
  
  Args:
    query: The query to search for (e.g. "HTTP Request node")
    resource_type: The resource type to search in (docs, workflows, community)
      - docs: General n8n documentation
      - workflows: Example workflows (will search for "n8n example {query}")
      - community: Community forums for issues and questions

  Returns:
    Text from the n8n resources
  """
  if resource_type not in n8n_urls:
    raise ValueError(f"Resource type {resource_type} not supported. Use 'docs', 'workflows', or 'community'")
  
  search_query = query
  if resource_type == "workflows":
    search_query = f"n8n example {query}"
  
  query = f"site:{n8n_urls[resource_type]} {search_query}"
  results = await search_web(query)
  
  if not results or "organic" not in results or len(results["organic"]) == 0:
    return f"No results found for '{search_query}' in {resource_type}"
  
  # Get content from the top results
  content_list = []
  for i, result in enumerate(results["organic"]):
    if "link" not in result:
      continue
      
    source_url = result["link"]
    title = result.get("title", "No title")
    content = await fetch_url(source_url)
    
    if content and not content.startswith("Error") and not content.startswith("Timeout"):
      content_list.append({
        "title": title,
        "url": source_url,
        "content": content
      })
  
  if not content_list:
    return f"Retrieved results for '{search_query}' in {resource_type}, but couldn't extract meaningful content"
  
  # Format the results
  formatted_results = ""
  for i, item in enumerate(content_list):
    formatted_results += f"\n\n--- RESULT {i+1}: {item['title']} ---\nSource: {item['url']}\n\n{item['content']}"
  
  return formatted_results


if __name__ == "__main__":
    mcp.run(transport="stdio")