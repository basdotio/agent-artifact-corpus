---
name: performance-optimization
description: Optimize API performance, database queries, caching, and profiling. Use when improving system performance to meet <500ms p95 target.
license: Apache-2.0
compatibility: Python 3.10+, FastAPI, SQLAlchemy
metadata:
  author: paracle-core-team
  version: "1.0.0"
  category: automation
  level: advanced
  display_name: "Performance Optimization"
  tags:
    - performance
    - profiling
    - caching
    - optimization
  capabilities:
    - performance_profiling
    - query_optimization
    - caching_strategies
allowed-tools: Read Write Bash(python:*)
---

# Performance Optimization Skill

## When to use this skill

Use when:

- API responses exceed 500ms p95
- Database queries are slow
- Memory usage is high
- Need to implement caching
- Profiling performance bottlenecks

## Performance Targets

| Metric   | Target | Critical |
| -------- | ------ | -------- |
| API p95  | <500ms | <1s      |
| API p99  | <1s    | <2s      |
| DB Query | <50ms  | <200ms   |
| Memory   | <512MB | <1GB     |
| CPU      | <50%   | <80%     |

## Profiling

```python
# Profile API endpoint
import cProfile
import pstats

def profile_endpoint():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run endpoint
    result = await my_endpoint()

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumulative')
    stats.print_stats(20)  # Top 20 slow functions
```

## Database Optimization

```python
# Bad: N+1 queries
agents = await session.execute(select(Agent))
for agent in agents:
    tools = await session.execute(
        select(Tool).where(Tool.agent_id == agent.id)
    )  # Query per agent!

# Good: Eager loading
from sqlalchemy.orm import selectinload

agents = await session.execute(
    select(Agent).options(selectinload(Agent.tools))
)  # Single query with join

# Add indexes
class Agent(Base):
    __tablename__ = "agents"

    name = Column(String, index=True)  # Index for lookups
    created_at = Column(DateTime, index=True)  # Index for sorting
```

## Caching Strategies

```python
from functools import lru_cache
from redis import Redis
import pickle

# In-memory cache (simple)
@lru_cache(maxsize=128)
def get_agent_spec(agent_id: str) -> AgentSpec:
    return load_spec_from_disk(agent_id)

# Redis cache (distributed)
redis_client = Redis(host='localhost', port=6379)

async def get_agent_cached(agent_id: str) -> Agent:
    # Check cache
    cached = redis_client.get(f"agent:{agent_id}")
    if cached:
        return pickle.loads(cached)

    # Fetch from DB
    agent = await fetch_agent_from_db(agent_id)

    # Cache for 5 minutes
    redis_client.setex(
        f"agent:{agent_id}",
        300,
        pickle.dumps(agent),
    )
    return agent

# Cache invalidation
async def update_agent(agent_id: str, updates: dict):
    agent = await update_agent_in_db(agent_id, updates)
    # Invalidate cache
    redis_client.delete(f"agent:{agent_id}")
    return agent
```

## Async Optimization

```python
# Bad: Sequential
async def process_agents_slow(agent_ids: list[str]):
    results = []
    for agent_id in agent_ids:
        result = await process_agent(agent_id)  # Wait for each
        results.append(result)
    return results

# Good: Concurrent
import asyncio

async def process_agents_fast(agent_ids: list[str]):
    tasks = [process_agent(agent_id) for agent_id in agent_ids]
    results = await asyncio.gather(*tasks)  # All at once
    return results

# With error handling
async def process_agents_safe(agent_ids: list[str]):
    tasks = [process_agent(agent_id) for agent_id in agent_ids]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Handle failures
    successes = [r for r in results if not isinstance(r, Exception)]
    failures = [r for r in results if isinstance(r, Exception)]

    return {"successes": successes, "failures": failures}
```

## API Response Optimization

```python
from fastapi import FastAPI
from starlette.middleware.gzip import GZipMiddleware

app = FastAPI()

# Enable compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Use response models to exclude unnecessary fields
from pydantic import BaseModel

class AgentListResponse(BaseModel):
    id: str
    name: str
    # Exclude: system_prompt, full_config, etc.

@app.get("/agents", response_model=list[AgentListResponse])
async def list_agents():
    # Only fetch needed fields
    agents = await session.execute(
        select(Agent.id, Agent.name)  # Not select(Agent)
    )
    return agents

# Use streaming for large responses
from fastapi.responses import StreamingResponse

@app.get("/agents/export")
async def export_agents():
    async def generate():
        agents = await stream_agents_from_db()
        async for agent in agents:
            yield agent.json() + "\\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")
```

## Monitoring

```python
# Add timing middleware
import time
from fastapi import Request

@app.middleware("http")
async def add_timing_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    # Log slow requests
    if process_time > 0.5:
        logger.warning(
            f"Slow request: {request.url.path} took {process_time:.2f}s"
        )

    return response
```

## Best Practices

1. **Profile before optimizing** - Measure first
2. **Use async for I/O** - Network, disk, DB
3. **Cache expensive operations** - Specs, configs
4. **Add database indexes** - For common queries
5. **Monitor in production** - Track p95/p99
6. **Use connection pooling** - DB, Redis, HTTP

## Resources

- FastAPI Performance: https://fastapi.tiangolo.com/advanced/performance/
- SQLAlchemy Optimization: `content/docs/performance-guide.md`
- Monitoring: `packages/paracle_core/logging/metrics.py`
