# Advanced RAG Techniques

## Overview

This document covers sophisticated RAG patterns including agents, query engines, multi-agent systems, and advanced architectural patterns for production deployments.

## Agents

### Agent Definition

An agent is **"a specific system that uses an LLM, memory, and tools, to handle inputs from outside users."** This contrasts with "agentic" systems, which represent a broader class incorporating LLM decision-making.

### Agent Loop Cycle

Standard agent execution follows this sequence:

1. Retrieves latest message and chat history
2. Sends tool schemas and conversation context to LLM API
3. LLM responds with either direct answer or tool invocation list
4. Each tool executes independently
5. Results append to chat history
6. Process repeats until completion

### Agent Types

#### FunctionAgent

Primary implementation leveraging provider-native function/tool calling.

```python
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.llms.openai import OpenAI

def multiply(a: float, b: float) -> float:
    """Useful for multiplying two numbers."""
    return a * b

agent = FunctionAgent(
    tools=[multiply],
    llm=OpenAI(model="gpt-4o-mini"),
    system_prompt="You are a helpful assistant..."
)

response = await agent.run("What is 5 times 7?")
```

#### ReActAgent

Uses reasoning-act prompting strategy:

```python
from llama_index.core.agent import ReActAgent

agent = ReActAgent.from_tools(
    tools=[query_tool, calculator_tool],
    llm=llm,
    verbose=True
)
```

#### CodeActAgent

Generates and executes code for tool interactions:

```python
from llama_index.core.agent import CodeActAgent

agent = CodeActAgent.from_tools(
    tools=[python_tool],
    llm=llm
)
```

### Tool Integration

#### Function-based Tools

Simplest approach using Python functions with docstrings:

```python
def search_documents(query: str) -> str:
    """Search document database for relevant information.

    Args:
        query: The search query string
    """
    results = vector_index.query(query)
    return str(results)
```

#### QueryEngineTool

Wrap query engines as tools:

```python
from llama_index.core.tools import QueryEngineTool, ToolMetadata

query_tool = QueryEngineTool(
    query_engine=vector_query_engine,
    metadata=ToolMetadata(
        name="document_search",
        description="Searches technical documentation for answers"
    )
)

agent = ReActAgent.from_tools([query_tool], llm=llm)
```

#### FunctionTool

Enhanced configuration for custom functions:

```python
from llama_index.core.tools import FunctionTool

def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 72°F"

weather_tool = FunctionTool.from_defaults(
    fn=get_weather,
    name="weather",
    description="Get current weather for a city"
)
```

### Memory Management

#### Default Memory

All agents use `ChatMemoryBuffer` by default:

```python
from llama_index.core.memory import ChatMemoryBuffer

memory = ChatMemoryBuffer.from_defaults(token_limit=40000)
response = await agent.run(
    "What did we discuss earlier?",
    memory=memory
)
```

#### Persistent Memory

```python
class PersistentMemory(ChatMemoryBuffer):
    def __init__(self, storage_path, **kwargs):
        super().__init__(**kwargs)
        self.storage_path = storage_path

    def save(self):
        with open(self.storage_path, 'w') as f:
            json.dump(self.get_all(), f)

    def load(self):
        with open(self.storage_path, 'r') as f:
            messages = json.load(f)
            self.put_messages(messages)
```

### Multi-Modal Capabilities

Process images alongside text:

```python
from llama_index.core.llms import ChatMessage, ImageBlock, TextBlock

msg = ChatMessage(
    role="user",
    blocks=[
        TextBlock(text="Analyze this image:"),
        ImageBlock(path="./screenshot.png"),
    ],
)

response = await agent.run(msg)
```

## Query Engines

### Query Engine Basics

A query engine is a **"generic interface that allows you to ask questions over your data."**

#### Basic Usage

```python
query_engine = index.as_query_engine()
response = query_engine.query("Who is Paul Graham?")
```

#### Streaming Responses

```python
query_engine = index.as_query_engine(streaming=True)
streaming_response = query_engine.query("Who is Paul Graham?")
streaming_response.print_response_stream()
```

### Advanced Query Engine Patterns

#### RouterQueryEngine

Route queries to specialized handlers:

```python
from llama_index.core.query_engine import RouterQueryEngine
from llama_index.core.selectors import LLMSingleSelector
from llama_index.core.tools import QueryEngineTool

summary_tool = QueryEngineTool.from_defaults(
    query_engine=summary_query_engine,
    description="Useful for summarization questions"
)

vector_tool = QueryEngineTool.from_defaults(
    query_engine=vector_query_engine,
    description="Useful for factual questions"
)

query_engine = RouterQueryEngine(
    selector=LLMSingleSelector.from_defaults(),
    query_engine_tools=[summary_tool, vector_tool]
)
```

#### SubQuestionQueryEngine

Decompose complex queries into sub-questions:

```python
from llama_index.core.query_engine import SubQuestionQueryEngine

query_engine_tools = [
    QueryEngineTool(
        query_engine=essay_engine,
        metadata=ToolMetadata(
            name="essays",
            description="Paul Graham essays collection"
        )
    ),
    QueryEngineTool(
        query_engine=articles_engine,
        metadata=ToolMetadata(
            name="articles",
            description="Technical articles"
        )
    )
]

query_engine = SubQuestionQueryEngine.from_defaults(
    query_engine_tools=query_engine_tools,
    use_async=True
)
```

**How it works**:
1. Breaks complex query into sub-questions
2. Routes each to appropriate query engine
3. Executes in parallel (if `use_async=True`)
4. Synthesizes comprehensive answer

**Use cases**: Multi-source analysis, comparative questions, comprehensive research

#### Joint QA-Summary Engine

Combine question answering with summarization:

```python
from llama_index.core.query_engine import (
    SubQuestionQueryEngine,
    RouterQueryEngine
)

# Combine multiple capabilities
hybrid_engine = RouterQueryEngine(
    selector=selector,
    query_engine_tools=[
        qa_tool,
        summary_tool,
        comparison_tool
    ]
)
```

### Custom Query Engine

```python
from llama_index.core.query_engine import CustomQueryEngine
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.response_synthesizers import BaseSynthesizer

class MyQueryEngine(CustomQueryEngine):
    retriever: BaseRetriever
    response_synthesizer: BaseSynthesizer

    def custom_query(self, query_str: str):
        nodes = self.retriever.retrieve(query_str)
        response = self.response_synthesizer.synthesize(query_str, nodes)
        return response
```

## Multi-Agent Systems

### Coordination Pattern

```python
from llama_index.core.agent.workflow import AgentWorkflow

# Define specialized agents
research_agent = FunctionAgent(
    tools=[search_tool, summarize_tool],
    system_prompt="You are a research specialist"
)

analysis_agent = FunctionAgent(
    tools=[analyze_tool, visualize_tool],
    system_prompt="You are a data analyst"
)

# Orchestrate agents
multi_agent = AgentWorkflow(
    agents=[research_agent, analysis_agent]
)

response = await multi_agent.run("Research and analyze market trends")
```

### Agent Handoff

Agents coordinate by handing off control:

```python
class CoordinatorAgent:
    def __init__(self, specialist_agents):
        self.specialists = specialist_agents

    async def delegate(self, task, task_type):
        """Route task to appropriate specialist"""
        if task_type == "research":
            return await self.specialists['research'].run(task)
        elif task_type == "analysis":
            return await self.specialists['analysis'].run(task)
```

### Hierarchical Multi-Agent

```python
# Manager agent
manager = FunctionAgent(
    tools=[delegate_to_research, delegate_to_analysis],
    system_prompt="You are a project manager. Delegate tasks to specialists."
)

# Worker agents
research_agent = FunctionAgent(tools=[search_tool])
analysis_agent = FunctionAgent(tools=[analyze_tool])

# Hierarchical execution
response = await manager.run("Complete comprehensive market analysis")
```

## Response Synthesis Patterns

### Response Modes

**create_and_refine**: Builds answer sequentially, refining with each chunk

**tree_summarize**: Builds tree of summaries bottom-up

**simple_summarize**: Concatenates all chunks, single LLM call

**compact**: Similar to simple but handles context overflow

```python
from llama_index.core.response_synthesizers import ResponseMode

query_engine = index.as_query_engine(
    response_mode=ResponseMode.TREE_SUMMARIZE
)
```

### Custom Response Synthesizer

```python
from llama_index.core.response_synthesizers import BaseSynthesizer

class CustomSynthesizer(BaseSynthesizer):
    def synthesize(self, query_str, nodes, **kwargs):
        # Custom synthesis logic
        context = "\n\n".join([node.get_content() for node in nodes])
        prompt = f"Query: {query_str}\n\nContext:\n{context}\n\nAnswer:"
        response = llm.complete(prompt)
        return response
```

## Advanced Retrieval Patterns

### Fusion Retriever

Combines multiple retrievers with query rewriting:

```python
from llama_index.core.retrievers import QueryFusionRetriever

retriever = QueryFusionRetriever(
    [vector_retriever, bm25_retriever],
    similarity_top_k=5,
    num_queries=4,  # Generate query variations
    mode="reciprocal_rerank",
    use_async=True
)
```

**How it works**:
1. Generates multiple query variations
2. Retrieves with each variation across all retrievers
3. Fuses results using reciprocal rank
4. Returns top-k from fused results

### Auto Retriever

LLM automatically generates metadata filters:

```python
from llama_index.core.retrievers import VectorIndexAutoRetriever
from llama_index.core.vector_stores import MetadataInfo, VectorStoreInfo

vector_store_info = VectorStoreInfo(
    content_info="Technical documentation",
    metadata_info=[
        MetadataInfo(
            name="category",
            type="str",
            description="Document category (tutorial, reference, guide)"
        ),
        MetadataInfo(
            name="difficulty",
            type="str",
            description="Content difficulty (beginner, intermediate, advanced)"
        )
    ]
)

retriever = VectorIndexAutoRetriever(
    index,
    vector_store_info=vector_store_info
)

# LLM automatically generates appropriate filters
nodes = retriever.retrieve("Find beginner tutorials on Python")
```

### Knowledge Graph Retriever

Leverage graph relationships:

```python
from llama_index.core import KnowledgeGraphIndex

kg_index = KnowledgeGraphIndex.from_documents(documents)
kg_retriever = kg_index.as_retriever(
    include_text=True,
    retriever_mode="keyword"
)
```

## Prompt Engineering

### Custom Prompts

```python
from llama_index.core import PromptTemplate

qa_prompt_tmpl = """
Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query_str}
Answer: """

qa_prompt = PromptTemplate(qa_prompt_tmpl)

query_engine = index.as_query_engine(
    text_qa_template=qa_prompt
)
```

### Advanced Prompt Functions

```python
from llama_index.core.prompts import PromptTemplate

def custom_prompt_fn(query_str, **kwargs):
    """Dynamically inject few-shot examples"""
    examples = retrieve_similar_examples(query_str)
    examples_str = "\n".join(examples)

    return f"""
    Here are some examples:
    {examples_str}

    Now answer: {query_str}
    """

query_engine = index.as_query_engine(
    text_qa_template=PromptTemplate(custom_prompt_fn)
)
```

## Observability & Debugging

### Callback Instrumentation

```python
from llama_index.core.callbacks import CallbackManager, LlamaDebugHandler

llama_debug = LlamaDebugHandler(print_trace_on_end=True)
callback_manager = CallbackManager([llama_debug])
Settings.callback_manager = callback_manager

# Detailed execution traces
response = query_engine.query(query_str)
```

### Event Tracking

```python
from llama_index.core.callbacks import CBEventType, EventPayload

# Retrieve specific events
for i, (start_event, end_event) in enumerate(
    llama_debug.get_event_pairs(CBEventType.SUB_QUESTION)
):
    qa_pair = end_event.payload[EventPayload.SUB_QUESTION]
    print(f"Sub Question {i}: {qa_pair.sub_q.sub_question}")
    print(f"Answer: {qa_pair.answer}")
```

### Custom Callbacks

```python
from llama_index.core.callbacks.base import BaseCallbackHandler

class MetricsCallback(BaseCallbackHandler):
    def on_event_start(self, event_type, payload, **kwargs):
        if event_type == CBEventType.RETRIEVE:
            print(f"Retrieval started: {payload}")

    def on_event_end(self, event_type, payload, **kwargs):
        if event_type == CBEventType.RETRIEVE:
            print(f"Retrieval completed: {payload}")
```

## Workflow Orchestration

### Sequential Workflow

```python
async def rag_workflow(query: str):
    # Step 1: Retrieve
    nodes = retriever.retrieve(query)

    # Step 2: Rerank
    reranked_nodes = reranker.postprocess_nodes(nodes, query)

    # Step 3: Synthesize
    response = synthesizer.synthesize(query, reranked_nodes)

    # Step 4: Evaluate
    evaluation = evaluator.evaluate(query, response)

    return response, evaluation
```

### Parallel Workflow

```python
async def parallel_rag_workflow(query: str):
    # Parallel retrieval from multiple sources
    results = await asyncio.gather(
        vector_retriever.aretrieve(query),
        bm25_retriever.aretrieve(query),
        kg_retriever.aretrieve(query)
    )

    # Combine and rerank
    all_nodes = [node for result in results for node in result]
    reranked = reranker.postprocess_nodes(all_nodes, query)

    # Synthesize
    response = await synthesizer.asynthesize(query, reranked)
    return response
```

## Production Deployment Patterns

### API Server

```python
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class QueryRequest(BaseModel):
    query: str
    top_k: int = 5

@app.post("/query")
async def query_endpoint(request: QueryRequest):
    query_engine = index.as_query_engine(similarity_top_k=request.top_k)
    response = await query_engine.aquery(request.query)
    return {"response": str(response)}
```

### Streaming Server

```python
from fastapi.responses import StreamingResponse

@app.post("/query/stream")
async def query_stream(request: QueryRequest):
    query_engine = index.as_query_engine(streaming=True)
    response = query_engine.query(request.query)

    async def generate():
        for text in response.response_gen:
            yield text

    return StreamingResponse(generate(), media_type="text/plain")
```

### Batch Processing

```python
async def batch_query_processing(queries: List[str]):
    """Process multiple queries efficiently"""
    # Batch retrieval
    all_nodes = await asyncio.gather(*[
        retriever.aretrieve(query) for query in queries
    ])

    # Batch synthesis
    responses = await asyncio.gather(*[
        synthesizer.asynthesize(query, nodes)
        for query, nodes in zip(queries, all_nodes)
    ])

    return responses
```

## Relevance to Your Pipelines

### Current Implementation

**src/agentic_retriever/**:
- ✅ Agentic retrieval with LLM routing
- Opportunity: Expand to multi-agent architecture

**src/17_query_planning_agent.py**:
- ✅ Query planning implementation
- Opportunity: Add sub-question decomposition

**src-iLand/retrieval/router.py**:
- ✅ Two-stage routing (index + strategy)
- ✅ LLM-based strategy selection
- Opportunity: Convert to full agent with memory

### Integration Opportunities

1. **Convert Router to Agent**:
   ```python
   # Transform router into FunctionAgent
   agent = FunctionAgent(
       tools=[vector_tool, bm25_tool, hybrid_tool, metadata_tool],
       llm=llm,
       memory=ChatMemoryBuffer.from_defaults()
   )
   ```

2. **Multi-Agent iLand System**:
   ```python
   # Specialized agents
   deed_agent = FunctionAgent(tools=[deed_search_tool])
   legal_agent = FunctionAgent(tools=[legal_interpretation_tool])
   geo_agent = FunctionAgent(tools=[geographic_search_tool])

   # Coordinator
   coordinator = AgentWorkflow(agents=[deed_agent, legal_agent, geo_agent])
   ```

3. **Add Sub-Question Decomposition**:
   ```python
   # For complex queries
   query_engine = SubQuestionQueryEngine.from_defaults(
       query_engine_tools=retriever_tools,
       use_async=True
   )
   ```

4. **Streaming CLI**:
   ```python
   # Add streaming to retrieval CLI
   query_engine = index.as_query_engine(streaming=True)
   response = query_engine.query(user_query)
   for text in response.response_gen:
       print(text, end="", flush=True)
   ```

## References

- [Agent Documentation](https://developers.llamaindex.ai/python/framework/module_guides/deploying/agents)
- [Query Engine Documentation](https://developers.llamaindex.ai/python/framework/module_guides/deploying/query_engine)
- [Sub Question Query Engine](https://developers.llamaindex.ai/python/examples/query_engine/sub_question_query_engine)
- [Production RAG Guide](https://developers.llamaindex.ai/python/framework/optimizing/production_rag/)
- [Building RAG from Scratch](https://developers.llamaindex.ai/python/framework/optimizing/building_rag_from_scratch/)
