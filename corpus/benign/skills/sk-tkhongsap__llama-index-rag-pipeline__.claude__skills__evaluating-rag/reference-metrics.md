# RAG Evaluation Metrics and Methods

## Overview

To improve the performance of an LLM app (RAG, agents), you must have a way to measure it. LlamaIndex provides comprehensive evaluation modules to assess both retrieval quality and response generation.

## Core Evaluation Metrics

### Retrieval Evaluation Metrics

#### 1. Hit Rate

**Definition**: The fraction of queries where the correct answer is found within the top-k retrieved documents.

**Formula**: `Hit Rate = (Queries with relevant doc in top-k) / Total queries`

**Interpretation**:
- 1.0 = Perfect retrieval (all queries found relevant docs)
- 0.5 = Half of queries found relevant docs
- Higher is better

**Example**:
```python
# If 90 out of 100 queries found relevant docs in top-5
hit_rate = 90 / 100 = 0.90
```

**Use case**: Primary metric for retrieval accuracy.

#### 2. Mean Reciprocal Rank (MRR)

**Definition**: The average of the reciprocals of ranks across all queries for the highest-placed relevant document.

**Formula**: `MRR = (1/N) * Σ(1/rank_i)`

**Interpretation**:
- 1.0 = Perfect ranking (relevant doc always rank 1)
- 0.5 = Relevant doc typically at rank 2
- Degrades as position worsens
- Higher is better

**Example**:
```python
# Query 1: Relevant doc at position 1 → 1/1 = 1.0
# Query 2: Relevant doc at position 2 → 1/2 = 0.5
# Query 3: Relevant doc at position 1 → 1/1 = 1.0
# MRR = (1.0 + 0.5 + 1.0) / 3 = 0.833
```

**Use case**: Measures ranking quality—where relevant docs appear in results.

### Response Evaluation Metrics

#### 3. Correctness

**Definition**: Compares generated answers against reference answers using query context.

**Implementation**:
```python
from llama_index.core.evaluation import CorrectnessEvaluator

evaluator = CorrectnessEvaluator(service_context=service_context)
result = evaluator.evaluate(
    query="What is the capital of France?",
    response="Paris",
    reference="Paris is the capital of France"
)
```

**Use case**: Validate factual accuracy of responses.

#### 4. Faithfulness

**Definition**: Determines if responses accurately reflect retrieved context without hallucination.

**Implementation**:
```python
from llama_index.core.evaluation import FaithfulnessEvaluator

evaluator = FaithfulnessEvaluator(service_context=service_context)
result = evaluator.evaluate_response(response=response)
```

**Use case**: Detect hallucinations and ensure grounding in sources.

#### 5. Semantic Similarity

**Definition**: Measures whether predicted and reference answers align conceptually.

**Implementation**:
```python
from llama_index.core.evaluation import SemanticSimilarityEvaluator

evaluator = SemanticSimilarityEvaluator(service_context=service_context)
result = evaluator.evaluate(
    response="Paris",
    reference="The capital is Paris"
)
```

**Use case**: Assess answer quality when exact matches aren't required.

#### 6. Context Relevancy

**Definition**: Validates whether retrieved sources align with the query.

**Use case**: Ensure retrieval quality before response generation.

#### 7. Answer Relevancy

**Definition**: Assesses if generated responses directly address the query.

**Use case**: Detect off-topic or incomplete answers.

#### 8. Guideline Adherence

**Definition**: Ensures outputs follow specific behavioral guidelines.

**Use case**: Compliance, safety, brand voice requirements.

## Evaluation Implementation Patterns

### Retrieval Evaluation Workflow

#### Step 1: Generate Evaluation Dataset

```python
from llama_index.core.evaluation import generate_question_context_pairs
from llama_index.llms.anthropic import Anthropic

llm = Anthropic(api_key="YOUR_KEY")
qa_dataset = generate_question_context_pairs(
    nodes,
    llm=llm,
    num_questions_per_chunk=2
)
```

**Note**: Uses LLM to generate synthetic (question, context) pairs from corpus.

#### Step 2: Filter Dataset

```python
from llama_index.core.evaluation import EmbeddingQAFinetuneDataset

def filter_qa_dataset(qa_dataset):
    """Remove invalid entries"""
    queries_to_remove = {
        k for k, v in qa_dataset.queries.items()
        if 'Here are 2' in v or 'Here are two' in v
    }

    filtered_queries = {
        k: v for k, v in qa_dataset.queries.items()
        if k not in queries_to_remove
    }

    return EmbeddingQAFinetuneDataset(
        queries=filtered_queries,
        corpus=qa_dataset.corpus,
        relevant_docs=qa_dataset.relevant_docs
    )
```

#### Step 3: Run Evaluation

```python
from llama_index.core.evaluation import RetrieverEvaluator

retriever_evaluator = RetrieverEvaluator.from_metric_names(
    ["mrr", "hit_rate"],
    retriever=retriever
)

eval_results = await retriever_evaluator.aevaluate_dataset(qa_dataset)

print(f"Hit Rate: {eval_results['hit_rate']}")
print(f"MRR: {eval_results['mrr']}")
```

### Response Evaluation Workflow

```python
from llama_index.core.evaluation import (
    FaithfulnessEvaluator,
    RelevancyEvaluator
)

# Initialize evaluators
faithfulness_evaluator = FaithfulnessEvaluator()
relevancy_evaluator = RelevancyEvaluator()

# Generate response
response = query_engine.query("What is machine learning?")

# Evaluate faithfulness
faithfulness_result = faithfulness_evaluator.evaluate_response(
    response=response
)
print(f"Faithfulness: {faithfulness_result.passing}")

# Evaluate relevancy
relevancy_result = relevancy_evaluator.evaluate_response(
    query="What is machine learning?",
    response=response
)
print(f"Relevancy: {relevancy_result.passing}")
```

## Custom Retriever Evaluation

```python
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle
from typing import List

class CustomRetriever(BaseRetriever):
    """Combines vector search with optional reranking"""

    def __init__(self, vector_retriever, reranker=None):
        self._vector_retriever = vector_retriever
        self._reranker = reranker

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
        retrieved_nodes = self._vector_retriever.retrieve(query_bundle)

        if self._reranker:
            retrieved_nodes = self._reranker.postprocess_nodes(
                retrieved_nodes,
                query_bundle
            )

        return retrieved_nodes

# Evaluate custom retriever
retriever_evaluator = RetrieverEvaluator.from_metric_names(
    ["mrr", "hit_rate"],
    retriever=CustomRetriever(vector_retriever, reranker)
)
```

## Comparative Evaluation

### Compare Embedding Models

```python
embedding_models = [
    ("OpenAI", OpenAIEmbedding()),
    ("JinaAI", JinaEmbedding(model="jina-embeddings-v2-base-en")),
    ("BGE-Base", HuggingFaceEmbedding(model_name="BAAI/bge-base-en-v1.5")),
]

results = {}
for name, embed_model in embedding_models:
    index = VectorStoreIndex.from_documents(
        documents,
        embed_model=embed_model
    )
    retriever = index.as_retriever(similarity_top_k=10)
    evaluator = RetrieverEvaluator.from_metric_names(
        ["mrr", "hit_rate"],
        retriever=retriever
    )
    eval_result = await evaluator.aevaluate_dataset(qa_dataset)
    results[name] = eval_result

# Compare results
for name, result in results.items():
    print(f"{name}: Hit Rate={result['hit_rate']:.3f}, MRR={result['mrr']:.3f}")
```

### Compare Retrieval Strategies

```python
strategies = {
    "vector": vector_retriever,
    "bm25": bm25_retriever,
    "hybrid": hybrid_retriever,
    "metadata": metadata_retriever,
}

for strategy_name, retriever in strategies.items():
    evaluator = RetrieverEvaluator.from_metric_names(
        ["mrr", "hit_rate"],
        retriever=retriever
    )
    results = await evaluator.aevaluate_dataset(qa_dataset)
    print(f"{strategy_name}: {results}")
```

### Compare with/without Reranking

```python
# Without reranking
retriever_no_rerank = index.as_retriever(similarity_top_k=5)

# With reranking
retriever_with_rerank = index.as_retriever(
    similarity_top_k=10,
    node_postprocessors=[CohereRerank(top_n=5)]
)

for name, retriever in [("No Rerank", retriever_no_rerank),
                        ("With Rerank", retriever_with_rerank)]:
    evaluator = RetrieverEvaluator.from_metric_names(
        ["mrr", "hit_rate"],
        retriever=retriever
    )
    results = await evaluator.aevaluate_dataset(qa_dataset)
    print(f"{name}: {results}")
```

## LabelledRagDataset

Structured evaluation datasets for community sharing:

```python
from llama_index.core.llama_dataset import LabelledRagDataset

# Create dataset
rag_dataset = LabelledRagDataset(
    examples=[
        {
            "query": "What is machine learning?",
            "reference_answer": "ML is...",
            "reference_contexts": ["context1", "context2"]
        }
    ]
)

# Save dataset
rag_dataset.save_json("evaluation_dataset.json")

# Load dataset
loaded_dataset = LabelledRagDataset.from_json("evaluation_dataset.json")
```

## External Evaluation Integrations

### UpTrain

```python
from uptrain import EvalLLM

eval_llm = EvalLLM(settings)
results = eval_llm.evaluate(
    data=data,
    checks=["context_relevance", "factual_accuracy"]
)
```

### Tonic Validate

Includes visualization UI for evaluation results.

### DeepEval

```python
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

metric = AnswerRelevancyMetric()
test_case = LLMTestCase(
    input="What is AI?",
    actual_output=response
)
metric.measure(test_case)
```

### Ragas

Specialized RAG evaluation framework.

### RAGChecker

Comprehensive RAG evaluation toolkit.

## Benchmarking Strategies

### Multi-Dimensional Assessment

```python
def comprehensive_evaluation(query_engine, test_queries):
    """Evaluate multiple dimensions"""
    evaluators = {
        "faithfulness": FaithfulnessEvaluator(),
        "relevancy": RelevancyEvaluator(),
        "correctness": CorrectnessEvaluator(),
    }

    results = {}
    for query, reference in test_queries:
        response = query_engine.query(query)
        results[query] = {}

        for name, evaluator in evaluators.items():
            eval_result = evaluator.evaluate(
                query=query,
                response=response,
                reference=reference
            )
            results[query][name] = eval_result.score

    return results
```

### A/B Testing Framework

```python
def ab_test_retrievers(retriever_a, retriever_b, qa_dataset):
    """Compare two retrievers"""
    evaluator = RetrieverEvaluator.from_metric_names(
        ["mrr", "hit_rate"],
        retriever=retriever_a
    )
    results_a = await evaluator.aevaluate_dataset(qa_dataset)

    evaluator.retriever = retriever_b
    results_b = await evaluator.aevaluate_dataset(qa_dataset)

    print("Retriever A:", results_a)
    print("Retriever B:", results_b)

    # Statistical significance testing
    improvement = (results_b['hit_rate'] - results_a['hit_rate']) / results_a['hit_rate']
    print(f"Improvement: {improvement * 100:.2f}%")
```

## Production Monitoring

### Continuous Evaluation

```python
import logging

class ProductionEvaluator:
    def __init__(self, evaluators):
        self.evaluators = evaluators
        self.metrics = []

    def evaluate_query(self, query, response, reference=None):
        """Evaluate single production query"""
        results = {}
        for name, evaluator in self.evaluators.items():
            try:
                result = evaluator.evaluate(
                    query=query,
                    response=response,
                    reference=reference
                )
                results[name] = result.score
            except Exception as e:
                logging.error(f"Evaluation failed for {name}: {e}")

        self.metrics.append(results)
        return results

    def get_metrics_summary(self):
        """Aggregate metrics over time"""
        import numpy as np
        summary = {}
        for metric_name in self.evaluators.keys():
            values = [m[metric_name] for m in self.metrics if metric_name in m]
            summary[metric_name] = {
                "mean": np.mean(values),
                "median": np.median(values),
                "std": np.std(values)
            }
        return summary
```

### Real-Time Monitoring

```python
from prometheus_client import Counter, Histogram

# Define metrics
retrieval_latency = Histogram(
    'rag_retrieval_latency_seconds',
    'Time spent in retrieval'
)
hit_rate_metric = Counter(
    'rag_hit_rate_total',
    'Total hit rate count'
)

# Track during queries
with retrieval_latency.time():
    results = retriever.retrieve(query)

if results:
    hit_rate_metric.inc()
```

## Best Practices

### 1. Generate Representative Datasets

- Cover diverse query types (factual, comparative, summarization)
- Include edge cases and failure modes
- Use domain-specific queries
- Maintain balance across difficulty levels

### 2. Evaluate Iteratively

```python
# Baseline
baseline_results = evaluate_retriever(baseline_retriever, qa_dataset)

# Iterate improvements
for improvement in improvements:
    apply_improvement(improvement)
    new_results = evaluate_retriever(retriever, qa_dataset)
    if new_results > baseline_results:
        baseline_results = new_results
    else:
        rollback_improvement(improvement)
```

### 3. Track Multiple Metrics

Don't rely on single metric—optimize for balanced performance:

```python
def balanced_score(eval_results):
    """Weighted combination of metrics"""
    return (
        0.4 * eval_results['hit_rate'] +
        0.3 * eval_results['mrr'] +
        0.2 * eval_results['faithfulness'] +
        0.1 * eval_results['relevancy']
    )
```

### 4. Test on Production Data

- Sample real user queries
- Maintain privacy (anonymize if needed)
- Track temporal trends

### 5. Automate Evaluation

```python
# CI/CD integration
def test_rag_performance():
    retriever = build_retriever()
    qa_dataset = load_qa_dataset()
    results = evaluate_retriever(retriever, qa_dataset)

    assert results['hit_rate'] >= 0.85, f"Hit rate too low: {results['hit_rate']}"
    assert results['mrr'] >= 0.75, f"MRR too low: {results['mrr']}"
```

## Relevance to Your Pipelines

### Current State

**src-iLand/**:
- ✅ Comprehensive retrieval strategies
- ⚠️ No systematic evaluation framework
- ⚠️ Manual testing only

**src/**:
- ✅ Multiple retrieval implementations
- ⚠️ No evaluation metrics tracked
- ⚠️ No comparative benchmarks

### Integration Opportunities

1. **Create Evaluation Dataset**:
   ```python
   # For iLand Thai land deeds
   qa_dataset = generate_question_context_pairs(
       nodes,
       llm=llm,
       num_questions_per_chunk=2
   )
   ```

2. **Compare 7 Strategies**:
   ```python
   strategies = ["vector", "bm25", "hybrid", "metadata",
                 "summary", "recursive", "planner"]
   for strategy in strategies:
       evaluate_strategy(strategy, qa_dataset)
   ```

3. **Track Metrics**:
   ```python
   # Add to retrieval CLI
   results = retriever.retrieve(query)
   hit_rate = calculate_hit_rate(results, ground_truth)
   logging.info(f"Hit Rate: {hit_rate}")
   ```

4. **A/B Testing**:
   ```python
   # Test with/without reranking
   ab_test_retrievers(
       retriever_no_rerank,
       retriever_with_rerank,
       qa_dataset
   )
   ```

## References

- [RAG Evaluation Documentation](https://developers.llamaindex.ai/python/framework/module_guides/evaluating)
- [Boosting RAG: Embedding & Reranker Models](https://www.llamaindex.ai/blog/boosting-rag-picking-the-best-embedding-reranker-models-42d079022e83)
- [Building RAG from Scratch](https://developers.llamaindex.ai/python/framework/optimizing/building_rag_from_scratch/)
