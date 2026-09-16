# Embedding Strategies for RAG Systems

## Overview

Embeddings represent documents as numerical vectors that capture semantic meaning, enabling similarity matching between text. Selecting the right embedding model and optimization strategy is critical for RAG performance, cost, and latency.

## Core Concepts

**Embeddings**: Sophisticated numerical representations of text that preserve semantic relationships—queries about dogs will have embeddings similar to dog-related content.

**Default Model**: LlamaIndex uses OpenAI's `text-embedding-ada-002` by default, though any model is configurable.

**Critical Requirement**: When changing embedding models, you MUST re-index all data. Identical models must be used for both indexing and querying.

## Embedding Model Selection

### Commercial Services

**OpenAI** (Default):
```bash
pip install llama-index-embeddings-openai
```

```python
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.core import Settings

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",  # or text-embedding-3-large
    embed_batch_size=100
)
```

**Cohere**:
```python
from llama_index.embeddings.cohere import CohereEmbedding

embed_model = CohereEmbedding(
    model_name="embed-english-v3.0",
    api_key="YOUR_API_KEY"
)
```

**VoyageAI**:
```python
from llama_index.embeddings.voyageai import VoyageEmbedding

embed_model = VoyageEmbedding(
    model_name="voyage-2",
    api_key="YOUR_API_KEY"
)
```

**JinaAI**:
```python
from llama_index.embeddings.jinaai import JinaEmbedding

embed_model = JinaEmbedding(
    model="jina-embeddings-v2-base-en",
    api_key="YOUR_API_KEY"
)
```

### Open Source & Local Models

**HuggingFace** (Recommended for cost optimization):
```bash
pip install llama-index-embeddings-huggingface
```

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5"  # or bge-base-en-v1.5, bge-large-en-v1.5
)
```

**Recommended Local Models**:
- `BAAI/bge-small-en-v1.5` - Fast, good quality
- `BAAI/bge-base-en-v1.5` - Balanced performance
- `BAAI/bge-large-en-v1.5` - Highest quality
- `sentence-transformers/all-mpnet-base-v2` - General purpose
- `sentence-transformers/all-MiniLM-L6-v2` - Fast inference

## Performance Optimization

### Batch Size Configuration

Adjust batch size based on rate limits and document volume:

```python
embed_model = OpenAIEmbedding(
    embed_batch_size=100  # Default: 10
)
```

**Guidelines**:
- OpenAI API: 100-200 (watch rate limits)
- Local models: 32-64 (based on GPU memory)
- CPU-only: 8-16 (avoid OOM errors)

### ONNX Acceleration (3-7x speedup)

```bash
pip install optimum[onnxruntime]
```

```python
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    backend="onnx"
)
```

**Performance**: ~3-7x throughput improvement on CPU with minimal accuracy loss.

### OpenVINO Optimization (7x speedup on CPU)

```bash
pip install optimum-intel[openvino]
```

```python
quantized_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/all-mpnet-base-v2",
    backend="openvino",
    device="cpu",
    model_kwargs={"file_name": "openvino/openvino_model_qint8_quantized.xml"}
)
```

**CPU Performance**: Int8-quantized OpenVINO delivers ~7x throughput improvement with minimal accuracy loss.

**GPU Performance**: For GPUs, use lower precision (float16) in standard torch backend for optimal balance.

### Advanced Configuration

```python
HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    backend="onnx",
    device="cuda",
    model_kwargs={"torch_dtype": "float16"}
)
```

## Embedding Model Benchmarks

### Performance from Blog Analysis

Based on comprehensive evaluation with 32 PDF files (4,306 documents):

**Top Performing Models** (with CohereRerank):

| Embedding Model | Hit Rate | MRR | Notes |
|----------------|----------|-----|-------|
| **JinaAI Base** | 0.938 | 0.869 | Best overall with reranker |
| **OpenAI** | 0.927 | 0.866 | Excellent, API-based |
| **Voyage** | 0.916 | 0.851 | Good balance |
| **Google PaLM** | 0.910 | 0.856 | Strong performance |
| **Cohere v3.0** | 0.888 | 0.836 | Solid commercial option |
| **bge-large** | 0.876 | 0.823 | Best open-source |

**Key Insight**: "Nearly all embeddings benefit from reranking, showing improved hit rates and MRRs"—rerankers can make any embedding competitive.

### MTEB Leaderboard

For comprehensive model comparisons across 50+ models and multiple datasets:
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)

## Configuration Patterns

### Global Configuration

```python
from llama_index.core import Settings
from llama_index.embeddings.openai import OpenAIEmbedding

Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small"
)
```

### Per-Index Configuration

```python
from llama_index.core import VectorStoreIndex

index = VectorStoreIndex.from_documents(
    documents,
    embed_model=embed_model
)
```

### Pipeline Integration

```python
from llama_index.core.ingestion import IngestionPipeline

pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(chunk_size=512),
        OpenAIEmbedding(),  # Embedding must be included
    ]
)
nodes = pipeline.run(documents=documents)
```

## Standalone Usage

```python
# Single embedding
embedding = embed_model.get_text_embedding("Your text here")

# Batch embeddings
batch_embeddings = embed_model.get_text_embeddings([
    "text one",
    "text two",
    "text three"
])
```

## Multi-Language Support

### Thai Language (Relevant for iLand Pipeline)

**Multilingual Models**:
```python
# Cohere multilingual v3
embed_model = CohereEmbedding(
    model_name="embed-multilingual-v3.0",
    api_key="YOUR_API_KEY"
)

# HuggingFace multilingual
Settings.embed_model = HuggingFaceEmbedding(
    model_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
```

**Thai-Specific Considerations**:
- Use multilingual models for Thai content
- Test with Thai queries for validation
- Consider fine-tuning on Thai land deed corpus

## Custom Embeddings

Extend `BaseEmbedding` for specialized use cases:

```python
from typing import Any, List
from llama_index.core.embeddings import BaseEmbedding

class CustomEmbedding(BaseEmbedding):
    def _get_query_embedding(self, query: str) -> List[float]:
        # Implementation for query embedding
        pass

    def _get_text_embedding(self, text: str) -> List[float]:
        # Implementation for text embedding
        pass

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        # Implementation for batch embedding
        pass
```

## LangChain Integration

```bash
pip install llama-index-embeddings-langchain
```

```python
from langchain.embeddings.huggingface import HuggingFaceBgeEmbeddings
from llama_index.core import Settings

Settings.embed_model = HuggingFaceBgeEmbeddings(
    model_name="BAAI/bge-base-en"
)
```

## Cost Optimization Strategies

### 1. Use Local Models

**Benefit**: Eliminate API costs at scale
**Trade-off**: Initial setup, compute resources

```python
# Free, unlimited usage
Settings.embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-small-en-v1.5",
    backend="onnx"  # 3-7x faster
)
```

### 2. Optimize Batch Processing

```python
# Batch embed during ingestion
pipeline = IngestionPipeline(
    transformations=[
        SentenceSplitter(),
        OpenAIEmbedding(embed_batch_size=100)
    ]
)
```

### 3. Cache Embeddings

```python
# Use ingestion pipeline caching
pipeline.persist("./pipeline_storage")
# Subsequent runs reuse cached embeddings
```

## Best Practices

### Model Selection

1. **Cost-sensitive**: Use local models (HuggingFace + ONNX)
2. **Quality-first**: OpenAI, JinaAI-base, or Voyage
3. **Balanced**: Cohere v3 or bge-large (open-source)
4. **Latency-critical**: Small models with ONNX/OpenVINO
5. **Multi-language**: Cohere multilingual, sentence-transformers multilingual

### Performance Tuning

1. **Latency**: ONNX/OpenVINO provide 3-7x speedup for CPU
2. **Accuracy**: Reserve quantized models for cost-sensitive scenarios; verify ranking relevance
3. **Scalability**: Adjust batch sizes based on rate limits and memory constraints
4. **Domain-specific**: Consider fine-tuning for specialized topics

### Production Deployment

1. **Monitoring**: Track embedding generation latency and costs
2. **Versioning**: Document embedding model version for reproducibility
3. **Testing**: Validate on representative queries before full reindexing
4. **Fallbacks**: Implement retry logic for API failures

## Fine-tuning Embeddings

For domain-specific optimization:

```python
# Label-free fine-tuning approach
# Over unstructured text corpora without manual annotation
```

Reference: [Embedding Fine-tuning Guide](https://developers.llamaindex.ai/python/framework/module_guides/models/embeddings#fine-tuning)

## Similarity Metrics

Default: **Cosine similarity** for comparing embeddings

Custom distance metrics can be implemented through vector store configuration.

## Relevance to Your Pipelines

### Current Implementation

**src-iLand/**:
- Uses OpenAI `text-embedding-3-small` (configured in `.env`)
- Thai language content requires multilingual support
- Opportunity: Test multilingual models for better Thai understanding

**src/**:
- Default OpenAI embeddings
- Opportunity: Compare local models for cost optimization

### Optimization Opportunities

1. **Multi-language Testing**:
   ```python
   # Test for iLand Thai content
   embed_model = CohereEmbedding(model_name="embed-multilingual-v3.0")
   ```

2. **Cost Reduction**:
   ```python
   # Replace API calls with local models
   Settings.embed_model = HuggingFaceEmbedding(
       model_name="BAAI/bge-base-en-v1.5",
       backend="onnx"
   )
   ```

3. **Batch Optimization**:
   ```python
   # In batch_embedding.py
   embed_model = OpenAIEmbedding(embed_batch_size=100)
   ```

## Evaluation Approach

Test embedding models systematically:

```python
from llama_index.core.evaluation import RetrieverEvaluator

embedding_models = [
    OpenAIEmbedding(),
    HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5"),
    CohereEmbedding(model_name="embed-english-v3.0"),
]

for embed_model in embedding_models:
    index = VectorStoreIndex.from_documents(documents, embed_model=embed_model)
    retriever = index.as_retriever()
    evaluator = RetrieverEvaluator.from_metric_names(["mrr", "hit_rate"], retriever=retriever)
    results = await evaluator.aevaluate_dataset(qa_dataset)
    # Compare metrics
```

## References

- [Embedding Models Documentation](https://developers.llamaindex.ai/python/framework/module_guides/models/embeddings)
- [Boosting RAG: Embedding & Reranker Models](https://www.llamaindex.ai/blog/boosting-rag-picking-the-best-embedding-reranker-models-42d079022e83)
- [MTEB Leaderboard](https://huggingface.co/spaces/mteb/leaderboard)
- [Production RAG Guide](https://developers.llamaindex.ai/python/framework/optimizing/production_rag/)
