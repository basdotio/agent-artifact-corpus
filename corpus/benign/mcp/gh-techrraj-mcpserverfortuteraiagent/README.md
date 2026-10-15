# MCP RAG + Agent Server for AI Tutor

A complete Model Context Protocol (MCP) server that combines:
- **RAG** (Retrieval-Augmented Generation) with PostgreSQL + pgvector
- **Free LLM** integration via OpenRouter
- **Dynamic agent creation** as an MCP tool
- **FastMCP** framework for building the server

## Features

### Tools
- `ingest_documents` — Import documents into the vector knowledge base
- `search_knowledge` — Semantic search using cosine similarity
- `ask_with_rag` — Full RAG pipeline (retrieve + LLM generation)
- `create_agent` — Dynamically create and run specialized AI agents

### Resources
- `knowledge://stats` — Knowledge base statistics
- `knowledge://config` — Current server configuration

### Prompts
- `explain_concept` — Generate explanation prompts for any concept

## Architecture


User → MCP Client (VS Code Copilot) → MCP Server → PostgreSQL+pgvector
→ OpenRouter LLM


## Setup

### 1. Start PostgreSQL + pgvector
```bash
docker run -d --name pgvector-demo \
  -e POSTGRES_USER=tutor \
  -e POSTGRES_PASSWORD=tutor123 \
  -e POSTGRES_DB=ai_tutor \
  -p 5432:5432 pgvector/pgvector:pg16

##2. Install dependencies

python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

3. Configure .env

DATABASE_URL=postgresql://tutor:tutor123@localhost:5432/ai_tutor
OPENROUTER_API_KEY=sk-or-v1-your-key
OPENAI_API_KEY=sk-your-openai-key
OPENROUTER_MODEL=openrouter/free
EMBEDDING_MODEL=nvidia/nemotron-3-embed-1b:free
EMBEDDING_BASE_URL=https://openrouter.ai/api/v1



4. Run the server

python server.py


Testing
Use MCP Inspector:
fastmcp dev inspector server.py

Tech Stack
FastMCP (MCP SDK for Python)

PostgreSQL 16 + pgvector

OpenAI Python SDK (via OpenRouter)

Python 3.11+

License
Apache 2.0
