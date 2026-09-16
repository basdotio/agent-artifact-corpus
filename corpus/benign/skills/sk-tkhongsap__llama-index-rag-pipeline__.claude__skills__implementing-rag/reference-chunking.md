# Chunking Strategies for RAG Systems

## Overview

Chunking is the process of breaking down documents into smaller, manageable pieces (nodes) for embedding and retrieval. Optimal chunk size and overlap are critical for RAG performance - smaller chunks provide precision while larger chunks offer more context.

## Key Concepts

**Chunk Size**: Maximum size per node (measured in tokens or characters)
**Chunk Overlap**: Number of overlapping tokens/characters between consecutive chunks
**Node**: A specific chunk of the parent document with inherited metadata

## Default Settings

LlamaIndex defaults:
- **Chunk size**: 1024 tokens
- **Chunk overlap**: 20 tokens

## Trade-offs

- **Smaller chunks** → More precise embeddings, risk of missing broader context
- **Larger chunks** → More general embeddings, risk of noise and detail dilution

**Best practice**: When halving chunk size, consider doubling `similarity_top_k` to maintain retrieval coverage.

## Node Parser Types

### 1. SentenceSplitter

Respects sentence boundaries while chunking, ideal for narrative text.

```python
from llama_index.core.node_parser import SentenceSplitter

node_parser = SentenceSplitter(
    chunk_size=1024,
    chunk_overlap=20
)
nodes = node_parser.get_nodes_from_documents(
    documents,
    show_progress=False
)
```

### 2. TokenTextSplitter

Provides precise token-based control, suitable for strict LLM token limits.

```python
from llama_index.core.node_parser import TokenTextSplitter

text_splitter = TokenTextSplitter(
    separator=" ",
    chunk_size=512,
    chunk_overlap=128
)
```

## Implementation Patterns

### Global Configuration

Apply chunk settings across all indices:

```python
from llama_index.core import Settings
from llama_index.core.node_parser import SentenceSplitter

Settings.chunk_size = 512
Settings.chunk_overlap = 50

# OR
Settings.text_splitter = SentenceSplitter(
    chunk_size=512,
    chunk_overlap=50
)
```

### Per-Index Configuration

Configure chunking for specific indices:

```python
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("./data").load_data()

index = VectorStoreIndex.from_documents(
    documents,
    transformations=[SentenceSplitter(chunk_size=512, chunk_overlap=50)]
)

query_engine = index.as_query_engine(similarity_top_k=4)
```

### Pipeline Integration

Integrate node parsers into transformation workflows:

```python
from llama_index.core.ingestion import IngestionPipeline

pipeline = IngestionPipeline(
    transformations=[
        TokenTextSplitter(chunk_size=512, chunk_overlap=128),
        # Additional transformations...
    ]
)
nodes = pipeline.run(documents=documents)
```

### Standalone Usage

Use node parsers independently without creating an index:

```python
from llama_index.core import Document

node_parser = SentenceSplitter(chunk_size=1024, chunk_overlap=20)
nodes = node_parser.get_nodes_from_documents(
    [Document(text="long text")],
    show_progress=False
)
```

## Advanced Chunking Patterns

### Sentence-Window Retrieval

Embed individual sentences for fine-grained retrieval while linking to surrounding context for synthesis:

```python
from llama_index.core.node_parser import SentenceWindowNodeParser

# This pattern addresses "lost in the middle" problem
node_parser = SentenceWindowNodeParser.from_defaults(
    window_size=3,  # sentences before/after
    window_metadata_key="window",
)
```

Used with `MetadataReplacementPostProcessor` for chunk decoupling.

### Hierarchical Chunking

Create parent-child relationships for recursive retrieval:

```python
# Parent chunks for high-level retrieval
parent_splitter = SentenceSplitter(chunk_size=2048, chunk_overlap=100)

# Child chunks for detailed retrieval
child_splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
```

## Configuration Parameters

| Parameter | Purpose | Typical Values |
|-----------|---------|----------------|
| `chunk_size` | Maximum node size | 256-2048 tokens |
| `chunk_overlap` | Context preservation | 10-20% of chunk_size |
| `separator` | Splitting delimiter | " " (space), "\n\n" (paragraphs) |
| `show_progress` | Display processing status | True/False |

## Optimization Guidelines

### For Your Use Cases

**iLand Thai Land Deeds (src-iLand/)**:
- Current: 1024 chunk size (good for legal documents)
- Consider: Testing 512 with increased top_k for better precision on specific deed attributes

**Main Pipeline (src/)**:
- Current: Varies by script
- Recommendation: Standardize chunk size across retrieval strategies for fair comparison

### Chunk Size Selection

1. **Domain considerations**:
   - Legal/Technical docs: 512-1024 (preserve clause boundaries)
   - Narrative content: 1024-2048 (maintain story flow)
   - Q&A pairs: 256-512 (focused responses)

2. **Query complexity**:
   - Simple factual queries: Smaller chunks (256-512)
   - Complex analytical queries: Larger chunks (1024-2048)

3. **Embedding model limits**:
   - Ensure chunk_size < model's max context window
   - OpenAI text-embedding-3-small: 8191 tokens max

### Overlap Optimization

- **Minimal context loss**: 50-100 tokens overlap
- **Computational efficiency**: 10-20 tokens overlap
- **High redundancy**: 20% of chunk_size

## Metadata Preservation

All document attributes automatically cascade to child nodes:
- Custom metadata fields
- Text templates
- Formatting information
- Relationships to parent documents

```python
from llama_index.core import Document

document = Document(
    text="content",
    metadata={"author": "LlamaIndex", "category": "technical"}
)
nodes = node_parser.get_nodes_from_documents([document])
# Each node inherits metadata from parent
```

## Evaluation Approach

Test chunk sizes systematically using evaluation metrics:

```python
# Test configuration
chunk_sizes = [256, 512, 1024, 2048]
top_k_values = [2, 4, 8, 16]

for chunk_size in chunk_sizes:
    for top_k in top_k_values:
        Settings.chunk_size = chunk_size
        # Run evaluation...
        # Measure hit_rate, MRR, latency
```

Reference: [Evaluating the Ideal Chunk Size for RAG](https://blog.llamaindex.ai/evaluating-the-ideal-chunk-size-for-a-rag-system-using-llamaindex-6207e5d3fec5)

## Relevance to Your Pipelines

### Current Implementation Analysis

**src-iLand/data_processing/doc_to_md_converter.py**:
- Converts Thai land deeds to markdown
- Current chunking happens during embedding phase
- Consider: Pre-chunking during conversion for better control

**src/02_prep_doc_for_embedding.py**:
- Prepares documents for embedding
- Opportunity: Implement configurable chunking strategy

### Integration Points

1. **data_processing → docs_embedding**: Configure chunking before embedding generation
2. **Retrieval strategies**: Ensure consistent chunking across all 7 retrieval methods
3. **Evaluation**: Compare chunk size impact on hit_rate and MRR

## References

- [Basic RAG Optimization Strategies](https://developers.llamaindex.ai/python/framework/optimizing/basic_strategies/basic_strategies/)
- [Node Parser Documentation](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers)
- [Production RAG Guide](https://developers.llamaindex.ai/python/framework/optimizing/production_rag/)
- [Building RAG from Scratch](https://developers.llamaindex.ai/python/framework/optimizing/building_rag_from_scratch/)
