"""MCP RAG + Agent server for VS Code + Copilot Chat."""
import sys
import logging
from typing import Optional
from fastmcp import FastMCP

from db import (
    init_db, insert_document, insert_embedding,
    search_similar, get_stats, chunk_text,
    save_message, get_history, create_session,
)
from llm_client import get_embedding, rag_query, chat_completion
from agent_executor import create_and_run_agent

# Log to stderr — stdout is reserved for MCP protocol under stdio transport
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr,
)
logger = logging.getLogger("MCP-RAG-Server")

mcp = FastMCP(
    "AI_Tutor_RAG",
    instructions="RAG + Agent creation server. Use ingest_documents "
                 "to load knowledge, then search_knowledge or ask_with_rag.",
)

init_db()


# ========== Tools ==========

@mcp.tool()
def ingest_documents(documents: list[dict]) -> dict:
    """Import documents with automatic chunking."""
    imported = 0
    errors = []
    total_chunks = 0

    for doc in documents:
        try:
            content = doc.get("content", "").strip()
            if not content:
                continue

            source = doc.get("source", "manual")
            metadata = doc.get("metadata", {})

            chunks = chunk_text(content)
            total_chunks += len(chunks)

            for i, chunk in enumerate(chunks):
                chunk_metadata = {**metadata, "chunk_index": i, "total_chunks": len(chunks)}
                doc_id = insert_document(
                    content=chunk,
                    source=source,
                    metadata=chunk_metadata,
                )
                insert_embedding(doc_id, get_embedding(chunk))
                imported += 1

        except Exception as e:
            errors.append(str(e))
            logger.error(f"Failed to ingest: {e}")

    return {
        "imported": imported,
        "total_chunks": total_chunks,
        "errors": errors,
        "total_attempted": len(documents),
    }


@mcp.tool()
def search_knowledge(query: str, top_k: int = 5,
                     source_filter: Optional[str] = None) -> dict:
    """Semantic search with optional source filter."""
    results = search_similar(
        get_embedding(query),
        top_k=top_k,
        source_filter=source_filter,
    )
    return {
        "query": query,
        "filter": source_filter,
        "results_count": len(results),
        "results": results,
    }


@mcp.tool()
def ask_with_rag(question: str, top_k: int = 5,
                 source_filter: Optional[str] = None) -> dict:
    """RAG Q&A with optional source filter."""
    docs = search_similar(
        get_embedding(question),
        top_k=top_k,
        source_filter=source_filter,
    )
    if not docs:
        return {
            "question": question,
            "answer": "No relevant info found. Use ingest_documents first.",
            "sources": [],
        }
    answer = rag_query(question, docs)
    return {
        "question": question,
        "answer": answer,
        "filter": source_filter,
        "sources": [
            {"id": d["id"], "source": d["source"], "similarity": d["similarity"]}
            for d in docs
        ],
    }


@mcp.tool()
def create_agent(agent_name: str, system_prompt: str, task: str,
                 session_id: Optional[str] = None,
                 model: Optional[str] = None) -> dict:
    """
    Create an agent with optional conversation memory.

    Args:
        agent_name: Identifier for the agent.
        system_prompt: System prompt defining the agent's role.
        task: The concrete task to perform.
        session_id: Pass to continue an existing conversation, or omit to start new.
        model: Optional model override.
    """
    logger.info(f"Creating agent: {agent_name}")

    # If no session handling needed, still support it:
    sid = create_session(session_id)
    history = get_history(sid)

    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": task})

    save_message(sid, "user", task)

    try:
        result = chat_completion(messages, temperature=0.7)
        save_message(sid, "assistant", result)
        return {
            "agent_name": agent_name,
            "session_id": sid,
            "status": "success",
            "result": result,
            "history_length": len(history),
        }
    except Exception as e:
        return {
            "agent_name": agent_name,
            "session_id": sid,
            "status": "error",
            "error": str(e),
        }


# ========== Resources ==========

@mcp.resource("knowledge://stats")
def knowledge_stats() -> dict:
    """Knowledge base statistics."""
    return get_stats()


@mcp.resource("knowledge://config")
def knowledge_config() -> dict:
    """Current server configuration."""
    import os
    return {
        "chat_model": os.getenv("OPENROUTER_MODEL"),
        "embedding_model": os.getenv("EMBEDDING_MODEL"),
        "embedding_base_url": os.getenv("EMBEDDING_BASE_URL"),
        "vector_db": "PostgreSQL + pgvector",
        "rag_enabled": True,
        "agent_creation_enabled": True,
    }


# ========== Prompts ==========

@mcp.prompt()
def explain_concept(concept: str) -> str:
    """Generate a prompt for explaining a concept."""
    return f"Explain '{concept}' in simple terms, assuming I'm new to MCP and AI agents."


if __name__ == "__main__":
    mcp.run()