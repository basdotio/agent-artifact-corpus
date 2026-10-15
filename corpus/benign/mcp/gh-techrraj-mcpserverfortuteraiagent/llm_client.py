"""Free LLM wrapper using OpenRouter (OpenAI-compatible)."""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# --- Chat client (OpenRouter) ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=120.0,
)

CHAT_MODEL = os.getenv("OPENROUTER_MODEL", "openrouter/free")

# --- Embedding client (also OpenRouter, no OpenAI key needed) ---
_embed_client = OpenAI(
    base_url=os.getenv("EMBEDDING_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("OPENROUTER_API_KEY"),
    timeout=120.0,
)

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "nvidia/nemotron-3-embed-1b:free")


def get_embedding(text: str) -> list[float]:
    """Return the vector embedding for a piece of text."""
    response = _embed_client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=text,
    )
    return response.data[0].embedding


def chat_completion(messages: list[dict],
                    temperature: float = 0.7,
                    max_tokens: int = 2000) -> str:
    """Call chat completion via OpenRouter."""
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        extra_headers={
            "HTTP-Referer": "http://localhost",
            "X-OpenRouter-Title": "MCP RAG Agent",
        },
    )
    return response.choices[0].message.content


def rag_query(question: str, context_docs: list[dict]) -> str:
    """Generate an answer grounded in retrieved context."""
    context = "\n\n".join(
        f"[Source: {d['source']}]\n{d['content']}" for d in context_docs
    )
    messages = [
        {"role": "system",
         "content": "You are a knowledge assistant. Answer using ONLY the "
                    "provided reference material. If insufficient, say so."},
        {"role": "user",
         "content": f"Reference:\n{context}\n\nQuestion: {question}"},
    ]
    return chat_completion(messages, temperature=0.3)