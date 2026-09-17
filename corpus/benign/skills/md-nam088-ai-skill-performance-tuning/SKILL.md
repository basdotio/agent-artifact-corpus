---
name: performance-tuning
description: Guidelines for optimizing Node.js application performance. Use when resolving latency issues, high CPU usage, or optimizing critical paths.
---

# Performance Tuning Skill

## When to use
- When the user complains about "slow" endpoints.
- When optimizing high-throughput features.
- When code involves heavy computation or large data processing.

## Tactics

### 1. Asynchronous Patterns
- **Promise.all**: Run independent async tasks in parallel.
  ```typescript
  // Fast
  const [user, posts] = await Promise.all([getUser(id), getPosts(id)]);
  
  // Slow
  const user = await getUser(id);
  const posts = await getPosts(id);
  ```

### 2. Database Optimization
- **Indexing**: Ensure WHERE, ORDER BY, and JOIN columns are indexed.
- **Select Fields**: Only select the columns you need (`select: { name: true }`).
- **N+1 Problem**: Use `.include()` or batch loaders (DataLoader) instead of looping queries.

### 3. Caching
- **Implementation**: Use Redis for expensive query results or computed data.
- **Strategy**: Cache-aside or Write-through depending on data freshness needs.

### 4. Node.js Specifics
- **Event Loop**: Don't block it. Use `setImmediate` or Worker Threads for CPU tasks.
- **JSON**: Serialization is expensive. Use `fast-json-stringify` (Fastify does this by default with schemas).

### 5. Memory Management
- **Streams**: Use streams for large file processing instead of buffering into memory.
- **Leaks**: Check for global listeners or uncleared intervals.
