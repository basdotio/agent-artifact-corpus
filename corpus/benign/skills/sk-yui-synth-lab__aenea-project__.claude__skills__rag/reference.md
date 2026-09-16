# RAG System Reference

## Key Files

| Component | Location |
|-----------|----------|
| Public API | [src/rag/index.ts](../../../src/rag/index.ts) |
| Embedder | [src/rag/embedder.ts](../../../src/rag/embedder.ts) |
| Vector DB | [src/rag/vectordb.ts](../../../src/rag/vectordb.ts) |
| Chunker | [src/rag/chunker.ts](../../../src/rag/chunker.ts) |
| Retriever | [src/rag/retriever.ts](../../../src/rag/retriever.ts) |
| Ingestion | [src/rag/ingest.ts](../../../src/rag/ingest.ts) |
| Types | [src/rag/types.ts](../../../src/rag/types.ts) |
| Config | [src/rag/config.ts](../../../src/rag/config.ts) |

## Directory Structure

```
knowledge/           # Knowledge base
├── sessions/        # Yui Protocol sessions
├── novels/          # Novels
├── dialogues/       # Exported dialogues
└── theory/          # Theory documents

data/vectordb/       # Vector database
└── aenea_vectors.db
```

## Technical Specs

| Aspect | Value |
|--------|-------|
| Vector DB | SQLite + cosine similarity |
| Embedding | Ollama `nomic-embed-text` (768 dim) |
| Chunking | `wakachigaki` (800 tokens, 100 overlap) |
| Feature Flag | `RAG_ENABLED=true` |

## Integration Points

| Stage | Usage |
|-------|-------|
| S0 | Search past explorations before generating questions |
| S1 | Retrieve knowledge for grounded agent thinking |
| Dialogue | Search past conversations for consistency |

## Environment Variables

See [.env.example](../../../.env.example) for full list:
- `RAG_ENABLED`
- `RAG_EMBEDDING_MODEL`
- `RAG_TOP_K`
- `RAG_SIMILARITY_THRESHOLD`
- `RAG_CHUNK_SIZE`
