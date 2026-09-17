---
name: observability
description: Analyzes distributed systems using Prometheus (PromQL), Loki (LogQL), and Tempo (TraceQL). Constructs efficient queries for metrics, logs, and traces. Interprets results with token-efficient structured output. Use when debugging performance issues, investigating errors, analyzing latency, or correlating observability signals across metrics, logs, and traces.
---

# Observability Analysis

Query construction and analysis for Prometheus, Loki, and Tempo.

## Core Principles

Start with all available metrics then drill down to logs and traces for context.

**Progressive Query Construction**
- Start simple → Add filters → Add operations → Optimize
- Test incrementally to validate each step
- Adjust based on data characteristics

**Multi-Signal Correlation**
- **Metrics** → Identify anomaly (what/when/how much)
- **Traces** → Map request flow (where/which services)
- **Logs** → Extract details (why/error messages)
- Use `trace_id`, `service.name`, timestamp for correlation

**Token-Efficient Results**
```
## Finding: [One-sentence summary]

**Evidence**: [Specific values/metrics]
**Impact**: [User/business effect]
**Cause**: [Root issue if identified]
**Action**: [Next step]
```

Target: <500 tokens for complete analysis

## Query Patterns

**Common starting points** (adapt based on context):

```promql
# Metrics: Error rate, latency percentiles, traffic patterns
sum(rate(http_requests_total{status=~"5.."}[5m])) / sum(rate(http_requests_total[5m]))
histogram_quantile(0.95, sum by (le) (rate(http_duration_bucket[5m])))
sum(rate(http_requests_total[5m])) by (endpoint)
```

```logql
# Logs: Error details, slow operations
{job="service"} |= "error" | json
{job="service"} | json | unwrap duration_ms | duration_ms > threshold
```

```traceql
# Traces: Error traces, slow requests, request flow
{status=error && service.name="service"}
{duration > threshold && service.name="service"}
{kind="server" && service.name="service"}
```

## Query Construction Guidelines

**Labels**: Use specific labels, avoid high cardinality aggregations
**Time ranges**: Match analysis needs (5m for rate, adjust as needed)
**Aggregations**: Filter first, then aggregate for efficiency

## Result Interpretation

**Extract key information**:
- Magnitude: Absolute values and comparisons
- Trend: Direction and velocity of change
- Scope: Affected components/users
- Timing: When changes occurred

**Quantify impact**: Convert metrics to business/user impact
**Prioritize**: Focus on severity, scope, and trend

## Reference Documentation

Consult references for detailed syntax, patterns, and workflows:

- **references/promql.md** - PromQL functions, RED/USE methods, optimization patterns
- **references/logql.md** - LogQL parsers, aggregations, pipeline optimization
- **references/traceql.md** - TraceQL span filtering, structural queries, performance analysis
- **references/semantic-conventions.md** - OpenTelemetry attribute standards and naming
- **references/analysis-patterns.md** - Token-efficient templates, output formats, examples
- **references/troubleshooting.md** - Investigation workflows, scenario-specific patterns

**When to use references**:
- Need specific syntax or advanced query patterns
- Unfamiliar with query language features
- Complex troubleshooting scenarios
- Semantic convention lookups

## Behavior

**DO**:
- Construct queries progressively and test incrementally
- Quantify findings with specific numbers and comparisons
- Present insights in structured, token-efficient format
- Focus on actionable, high-impact information
- Lead with conclusions

**DON'T**:
- Over-explain investigation process or basic concepts
- Include unnecessary query variations
- Generate instrumentation code or alert rules
- Overwhelm with excessive findings (prioritize top issues)

## Success Criteria

Effective analysis provides:
- Concise findings (<500 tokens for complete analysis)
- Specific evidence (numbers, comparisons, trends)
- Clear impact assessment
- Actionable next steps
- Structured presentation
