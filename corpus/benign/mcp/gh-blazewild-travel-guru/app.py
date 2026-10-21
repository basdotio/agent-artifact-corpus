import asyncio
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# Load tools
from tools.exa_tools import search_and_contents, find_similar_and_contents
from tools.firecrawl import scrape_with_firecrawl
from tools.pdf_rag import search_pdf_docs
from tools.combined import run_combined_search

# Init MCP Server
load_dotenv()
mcp = FastMCP(name="multimodal_agent", version="1.0", description="Multi-tool AI Agent using Exa, Firecrawl, Pinecone, and Gemini")

# Register tools
mcp.tool()(search_and_contents)
mcp.tool()(find_similar_and_contents)
mcp.tool()(scrape_with_firecrawl)
mcp.tool()(search_pdf_docs)
mcp.tool()(run_combined_search)

# Run server
if __name__ == "__main__":
    asyncio.run(mcp.run_async())
