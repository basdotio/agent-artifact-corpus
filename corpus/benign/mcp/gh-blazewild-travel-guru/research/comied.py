import os
import sys
import asyncio
import logging

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# existing modules for web search & dynamic RAG
import search
import rag

# Pinecone + LangChain for PDF RAG
import pinecone
from src.helpers import load_hugging_face_embedding
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import PromptTemplate

# Google Gemini for LLM final answer
from google.generativeai import configure, GenerativeModel

# setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# load environment variables
load_dotenv()
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENV     = os.getenv("PINECONE_API_ENV")    # e.g. "us-east-1-aws"
GEMINI_API_KEY   = os.getenv("GEMINI_API_KEY")

# initialize MCP
mcp = FastMCP(
    name="web_and_pdf_rag",
    version="1.0.0",
    description=(
        "1) Live web-search + dynamic RAG, 2) Firecrawl raw fetch, "
        "3) PDF-based RAG (Pinecone), 4) Combined final LLM answer"
    )
)

# ----------------------------------------------------------------------------
# 1) Live Web Search + In-Memory RAG
# ----------------------------------------------------------------------------
@mcp.tool()
async def search_web_tool(query: str) -> str:
    """
    Search the web via Exa + Firecrawl, build an in-memory FAISS RAG, and return combined results.
    """
    logger.info(f"[WebTool] Searching for: {query}")
    formatted_results, raw_results = await search.search_web(query)
    if not raw_results:
        return "No live web results."

    urls = [res.url for res in raw_results if hasattr(res, 'url')]
    if not urls:
        return "No URLs found in the results."

    # build dynamic RAG
    vectorstore = await rag.create_rag(urls)
    rag_results = await rag.search_rag(query, vectorstore)

    output = formatted_results + "\n\n=== RAG Over Web ===\n"
    output += "\n---\n".join(doc.page_content for doc in rag_results)
    return output

# ----------------------------------------------------------------------------
# 2) Raw URL Content via Firecrawl
# ----------------------------------------------------------------------------
@mcp.tool()
async def get_web_content_tool(url: str) -> str:
    """
    Scrape the given URL via Firecrawl and return raw text.
    """
    logger.info(f"[GetContent] URL: {url}")
    try:
        documents = await asyncio.wait_for(search.get_web_content(url), timeout=FIRECRAWL_TIMEOUT)
        if documents:
            return "\n\n".join(doc.page_content for doc in documents)
        return "Unable to retrieve content from the URL."
    except asyncio.TimeoutError:
        return "Request timed out. Please try again later."
    except Exception as e:
        return f"An error occurred: {str(e)}"

# ----------------------------------------------------------------------------
# 3) PDF-Based RAG via Pinecone
# ----------------------------------------------------------------------------
@mcp.tool()
async def search_documents_tool(query: str) -> str:
    """
    Retrieve top-k chunks from existing Pinecone index and return the PDF context.
    """
    logger.info(f"[DocTool] Querying PDF RAG: {query}")
    # init Pinecone client
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENV)

    # load embeddings + vectorstore
    embeddings = load_hugging_face_embedding()
    index_name = "travel-guru"
    docsearch = PineconeVectorStore.from_existing_index(
        index_name=index_name,
        embedding=embeddings
    )

    # retrieve top-3
    retriever = docsearch.as_retriever(search_kwargs={"k": 3})
    docs = retriever.get_relevant_documents(query)
    if not docs:
        return "No relevant PDF documents found."

    # format PDF context
    return "\n\n---\n\n".join(d.page_content for d in docs)

# ----------------------------------------------------------------------------
# 4) Combined Tool: Web + PDF RAG -> Final LLM Answer
# ----------------------------------------------------------------------------
@mcp.tool()
async def combined_search_tool(query: str) -> str:
    """
    Runs web RAG & PDF RAG, combines contexts, and calls Google Gemini for a final answer.
    """
    logger.info(f"[Combined] Query: {query}")

    # 1) gather web RAG
    web_ctx = await search_web_tool(query)

    # 2) gather PDF RAG
    pdf_ctx = await search_documents_tool(query)

    # 3) combine and prompt
    combined_context = (
        "=== Web RAG Context ===\n" + web_ctx +
        "\n\n=== PDF RAG Context ===\n" + pdf_ctx
    )
    prompt = (
        "You are Trekking Guru. Using the retrieved information, answer the question:\n"
        f"{combined_context}\n\nQuestion: {query}\nAnswer in 3-5 sentences."
    )

    # call Google Gemini
    configure(api_key=GEMINI_API_KEY)
    model = GenerativeModel("gemini-2.0-flash")
    response = model.generate(prompt=prompt)
    return response.candidates[0].output

# ----------------------------------------------------------------------------
# KEEP existing helper functions and main with try/except as-is
# ----------------------------------------------------------------------------

# ... (create_rag, create_rag_from_documents, search_web_internal,
# format_search_results, get_web_content, main) with their original try/except blocks ...

if __name__ == "__main__":
    asyncio.run(main())
