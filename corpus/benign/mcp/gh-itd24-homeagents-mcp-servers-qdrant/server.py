"""
Qdrant Memory MCP Server

Exposes four tools over MCP streamable-http (mounted at /mcp by default):
  - memory_store(content, domain, source=None, tags=None)
  - memory_search(query, domain=None, top_k=5)
  - memory_delete(point_id)
  - memory_stats(domain=None)

Single Qdrant collection ("memory" by default), domain-tagged via payload
filtering. Embeddings come from a local TEI service
(BAAI/bge-m3, 1024-dim, CPU-only, zero API cost).
"""

import os
import time
import uuid
from typing import Optional

import httpx
from fastmcp import FastMCP
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)
from starlette.responses import JSONResponse

QDRANT_URL = os.environ.get("QDRANT_URL", "http://qdrant:6333")
EMBEDDINGS_URL = os.environ.get("EMBEDDINGS_URL", "http://embeddings:80")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "memory")
VECTOR_SIZE = 1024 # matches BAAI/bge-m3

client = QdrantClient(url=QDRANT_URL)
mcp = FastMCP("qdrant-memory")


def ensure_collection() -> None:
    """Create the shared collection if it doesn't exist yet. Safe to call
    repeatedly - this is what makes a fresh machine self-heal even if the
    one-off create_collection.py step gets skipped."""
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )


async def embed(text: str) -> list[float]:
    """Call the local TEI embeddings service. TEI's /embed endpoint takes a
    batch of strings and returns a list of vectors - we always send one."""
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        resp = await http_client.post(f"{EMBEDDINGS_URL}/embed", json={"inputs": text})
        resp.raise_for_status()
        vectors = resp.json()
        return vectors[0]


def domain_filter(domain: Optional[str]) -> Optional[Filter]:
    if not domain:
        return None
    return Filter(must=[FieldCondition(key="domain", match=MatchValue(value=domain))])


@mcp.tool()
async def memory_store(
    content: str,
    domain: str,
    source: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> dict:
    """Store a piece of memory in Qdrant, tagged with a domain
    (e.g. dev, finance, jobs, content, general). Embeds `content` locally
    via TEI and upserts a point. Returns the new point id."""
    ensure_collection()
    vector = await embed(content)
    point_id = str(uuid.uuid4())
    payload = {
        "domain": domain,
        "content": content,
        "source": source,
        "tags": tags or [],
        "timestamp": time.time(),
    }
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=point_id, vector=vector, payload=payload)],
    )
    return {"id": point_id, "domain": domain}


@mcp.tool()
async def memory_search(query: str, domain: Optional[str] = None, top_k: int = 5) -> list[dict]:
    """Semantic search over stored memory. Pass `domain` to scope the search
    to one profile's memory; omit it to deliberately search across all
    domains (e.g. a general assistant recalling a finance fact)."""
    ensure_collection()
    vector = await embed(query)
    results = client.query_points(
        collection_name=COLLECTION_NAME,
        query=vector,
        query_filter=domain_filter(domain),
        limit=top_k,
    )
    return [
        {
            "id": p.id,
            "score": p.score,
            "content": p.payload.get("content"),
            "domain": p.payload.get("domain"),
            "source": p.payload.get("source"),
            "tags": p.payload.get("tags"),
            "timestamp": p.payload.get("timestamp"),
        }
        for p in results.points
    ]


@mcp.tool()
def memory_delete(point_id: str) -> dict:
    """Delete a single memory point by its id."""
    client.delete(collection_name=COLLECTION_NAME, points_selector=[point_id])
    return {"deleted": point_id}


@mcp.tool()
def memory_stats(domain: Optional[str] = None) -> dict:
    """Count stored points, optionally scoped to one domain. Omit `domain`
    for a total across all domains."""
    ensure_collection()
    count = client.count(
        collection_name=COLLECTION_NAME,
        count_filter=domain_filter(domain),
        exact=True,
    )
    return {"domain": domain or "all", "count": count.count}


@mcp.custom_route("/health", methods=["GET"])
async def health(_request):
    """Plain HTTP health check - separate from the /mcp protocol endpoint,
    for docker healthchecks and smoke tests."""
    try:
        client.get_collections()
        return JSONResponse({"status": "ok"})
    except Exception as exc:  # noqa: BLE001 - health check, report any failure
        return JSONResponse({"status": "error", "detail": str(exc)}, status_code=503)


if __name__ == "__main__":
    ensure_collection()
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8765)
