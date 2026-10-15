import asyncio
from mcp.server.fastmcp import FastMCP
from agno.knowledge.text import TextKnowledgeBase
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.fastembed import FastEmbedEmbedder
from agno.document.chunking.markdown import MarkdownChunking

# Knowledge Base
knowledge_base = TextKnowledgeBase(
  path="doc/EIPs/EIPS",
  formats=[".md"],
  chunking_strategy=MarkdownChunking(chunk_size=5000, overlap=0),
  vector_db=LanceDb(
    uri="tmp/lancedb",
    table_name="EIPs",
    search_type=SearchType.vector,
    embedder=FastEmbedEmbedder(),
  ),
)

# Initialize MCP server
mcp = FastMCP("EIPs MCP Server")

# Tool to search Ethereum EIPs
@mcp.tool()
def search(query: str) -> str:
    """Search Ethereum EIPs by query string"""
    # Implementation to be added
    chunks = knowledge_base.search(query=query, num_documents=5)
    parts = []
    for chunk in chunks:
        parts.append("-" * 20 + chunk.name + "-" * 20)
        parts.append(chunk.content)
    return "\n".join(parts)    

# Run the server
if __name__ == "__main__":
    mcp.run()
    