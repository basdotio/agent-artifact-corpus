---
name: go-temporal
description: Expert guidance for building workflows and activities with Temporal in Go. Use when working with Temporal SDK, designing durable workflows, handling retries, implementing saga patterns, or debugging Temporal applications.
---

This skill guides creation of production-ready Temporal applications following Go idioms and best practices. Build durable, fault-tolerant workflows with proper error handling, observability, and testing.

## Core Mental Model

Temporal separates **what** happens from **when** it happens:

- **Workflows**: Deterministic orchestrators that survive failures. They coordinate, make decisions, and maintain state. Think of them as reliable state machines that never lose progress.
- **Activities**: Unreliable operations (I/O, APIs, databases) wrapped with automatic retries. They do the actual work but may fail transiently.
- **Workers**: Stateless executors polling task queues. Scale horizontally by adding more workers.

**Key insight**: Workflows replay from history on restart. Any non-deterministic operation (time, random, I/O) breaks replay. Use `workflow.*` APIs for determinism.

## Design Principles

### Workflow Design

- **Single Responsibility**: One workflow per business process. Decompose complex processes into parent/child workflows.
- **Idempotent by Default**: Design for replay. Workflow code runs multiple times but must produce the same result.
- **Prefer Small State**: Keep workflow inputs/outputs under 2MB. Reference external storage for large data.
- **Explicit Over Implicit**: Configure retry policies, timeouts, and task queues explicitly. Never rely on defaults in production.

### Activity Design

- **Idempotency is Essential**: Activities may retry. Use idempotency keys from `activity.GetInfo(ctx)` for external calls.
- **Heartbeat Long Operations**: Any activity running >1 minute needs heartbeating. Store progress in heartbeat details for resumption.
- **Fail Fast, Retry Smart**: Return non-retryable errors for validation failures. Let transient errors retry automatically.
- **Local Activities for Speed**: Use for sub-second operations (validation, transforms) that don't need durability.

### Error Philosophy

- **Retryable**: Network timeouts, rate limits, temporary unavailability. Wrap with `fmt.Errorf()`.
- **Non-Retryable**: Validation errors, not found, permission denied. Use `temporal.NewNonRetryableApplicationError()`.
- **Structured Details**: Attach error details for workflow-side decision making.

## Determinism Rules

Workflows must produce identical results on replay. Prohibited operations:

| Prohibited | Use Instead |
|------------|-------------|
| `time.Now()` | `workflow.Now(ctx)` |
| `time.Sleep()` | `workflow.Sleep(ctx, duration)` |
| `rand.*` | `workflow.SideEffect()` |
| `go func(){}` | `workflow.Go()` |
| `chan` | `workflow.Channel` |
| `sync.Mutex` | `workflow.Mutex` |
| Network/file I/O | Activities |
| Global mutable state | Workflow-local state |

## Project Organization

```
myapp/
├── cmd/worker/main.go     # Worker entrypoint  
├── internal/
│   ├── workflows/         # Workflow definitions
│   ├── activities/        # Activity implementations (group related ones in structs)
│   └── shared/            # Types, constants, task queue names
```

Group related activities in structs for dependency injection and cleaner registration. Reference methods in workflows via nil pointer for type safety.

## Reference Guides

Detailed patterns and examples for specific topics:

- **[Workflow Patterns](references/workflows.md)**: Child workflows, continue-as-new, versioning, sagas, parallel execution, cancellation
- **[Activity Patterns](references/activities.md)**: Heartbeats, local activities, async completion, idempotency patterns  
- **[Testing](references/testing.md)**: Unit testing, mocking, time manipulation, integration tests
- **[Observability](references/observability.md)**: OpenTelemetry tracing, context propagation, metrics, logging

## Common Pitfalls

1. **Non-deterministic workflow code**: Using standard library time/random/goroutines instead of workflow APIs
2. **Missing retry policies**: Always configure explicit retry policies for activities
3. **Unbounded history**: Use continue-as-new for workflows processing >10K events
4. **Large payloads**: Keep inputs/outputs <2MB; use external storage with references
5. **Silent activity failures**: Heartbeat long activities; check `ctx.Err()` for cancellation
6. **Versioning mistakes**: Use `workflow.GetVersion()` for code changes; never modify existing workflow logic without versioning
