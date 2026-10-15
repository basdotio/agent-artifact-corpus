from mcp.server.fastmcp import FastMCP
import argparse
from linkup import LinkupClient
from qdrant_client import AsyncQdrantClient, QdrantClient
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core import Settings, VectorStoreIndex
from llama_index.core.query_engine.transform_query_engine import TransformQueryEngine
from llama_index.core.indices.query.query_transform import HyDEQueryTransform
from llama_index.llms.groq import Groq
from dotenv import load_dotenv
from os import environ as ENV

load_dotenv()

embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
llm = Groq(model="llama-3.3-70b-versatile", api_key=ENV["groq_api_key"])

Settings.llm = llm
Settings.embed_model = embed_model
Settings.chunk_size = 2000
Settings.chunk_overlap = 50
mcp = FastMCP(name="MCP")
linkup_client = LinkupClient(api_key=ENV["linkup_api_key"])
client = QdrantClient("http://localhost:6333")
aclient = AsyncQdrantClient("http://localhost:6333")
vector_store = QdrantVectorStore(collection_name="ts_docs", client=client, aclient=aclient, enable_hybrid=True, fastembed_sparse_model="Qdrant/bm25")
vector_index = VectorStoreIndex.from_vector_store(vector_store=vector_store)
query_engine = vector_index.as_query_engine()
hyde_transform = HyDEQueryTransform()
hyde_qe = TransformQueryEngine(query_engine=query_engine, query_transform=hyde_transform)

@mcp.tool(name="deepsearch_tool", description="Useful to search for precise information in the depths of the web when you need to answer advanced and/or complicated questions by the user about Typescript (especially debugging and errors).")
async def deepsearch(query: str) -> str:
    response = linkup_client.search(
        query=query,
        depth="deep",
        output_type="sourcedAnswer",
    )
    answer = response.answer
    sources = response.sources
    bibliography = [f"- [{source.name}]({source.url})" for source in sources]
    sb = "\n".join(bibliography)
    return f"<details>\n\t<summary><b>Sources</b></summary>\n\n{sb}\n\n</details>\n\n{answer}"

@mcp.tool(name="documentation_search_tool", description="Useful to search for specific information within a database containing TypeScript documentation.")
async def docs_search(query: str) -> str:
    response = await hyde_qe.aquery(query)
    return response.response

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"]
    )
    args = parser.parse_args()
    mcp.run(args.server_type)