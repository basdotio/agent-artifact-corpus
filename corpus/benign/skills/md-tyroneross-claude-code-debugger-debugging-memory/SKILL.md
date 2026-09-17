---
name: debugging-memory
description: This skill should be used when the user asks to "debug this", "fix this bug", "why is this failing", "investigate error", "getting an error", "exception thrown", "crash", "not working", "what's causing this", "root cause", "diagnose this issue", or describes any software bug or error. Also activates when spawning subagents for debugging tasks, using Task tool for bug investigation, or coordinating multiple agents on a debugging problem. Provides memory-first debugging workflow that checks past incidents before investigating.
version: 1.5.0
user-invocable: false
---

# Debugging Memory Workflow

This skill integrates the claude-code-debugger memory system into debugging workflows. The core principle: **never solve the same bug twice**.

## Memory-First Approach

Before investigating any bug, always check the debugging memory using the debugger `search` MCP tool:

```
Use the debugger search tool with the symptom description.
```

The search returns a **verdict** with matching incidents and patterns.

**Verdict-based decision tree:**

1. **KNOWN_FIX**: Apply the documented fix directly, adapting for current context
2. **LIKELY_MATCH**: Review the past incident, use it as a starting point
3. **WEAK_SIGNAL**: Consider loosely related incidents, but investigate fresh
4. **NO_MATCH**: Proceed with standard debugging, document the solution afterward

## Progressive Depth Retrieval

Results are returned as compact summaries. Drill into matches on demand:

1. **Initial search**: Use the debugger `search` MCP tool — returns verdict + compact matches
2. **Drill down**: Use the debugger `detail` MCP tool with the ID to load full incident/pattern data
3. **Outcome tracking**: Use the debugger `outcome` MCP tool to record whether the fix worked, failed, or was modified

## Visibility

When this skill activates, always announce it to the user:

1. **Before searching**: Output "Checking debugging memory for similar issues..."
2. **After search**: Report result briefly:
   - Found match: "Found X matching incident(s) from past debugging sessions"
   - No match: "No matching incidents in debugging memory - starting fresh investigation"

This ensures users know the debugger is active and working.

## Structured Debugging Process

When no past solution applies, follow this systematic approach.

### Deep Investigation Mode

For non-trivial issues, load the `debug-loop` skill instead of the basic steps below. The trigger is the **verdict category** from memory search, not a numeric confidence score:

- **`KNOWN_FIX`** → apply the fix directly, skip the loop
- **`LIKELY_MATCH`** → enter debug loop (past incidents exist but need verification against current context)
- **`WEAK_SIGNAL`** → enter debug loop (loosely related, needs fresh investigation)
- **`NO_MATCH`** → enter debug loop (no prior knowledge, full investigation needed)

Also enter the debug loop when:
- The initial diagnosis feels superficial (treating a symptom as the cause)
- A previous fix attempt didn't hold — the bug came back
- The user explicitly asks for root cause analysis or deep investigation
- Multiple symptoms suggest a shared underlying cause

The debug loop provides: causal tree investigation, hypothesis testing, iterative fix-verify-score cycles (up to 5x), fix critique before declaring done, and transparent ✅/⚠️/❓ reporting.

### Basic Steps (for simple, clear-cut issues)

For straightforward bugs where the cause is immediately apparent, use these steps directly:

### 1. Reproduce

Establish a reliable reproduction path:
- Identify exact steps to trigger the bug
- Note any environmental factors (OS, dependencies, state)
- Create a minimal reproduction if possible

### 2. Isolate

Narrow down the problem space:
- Binary search through recent changes
- Disable components to find the culprit
- Check logs and error messages for clues

### 3. Diagnose

Find the root cause:
- Trace the execution path
- Examine state at failure point
- Identify the specific code causing the issue

### 4. Fix

Implement the solution:
- Make minimal, targeted changes
- Avoid side effects
- Consider edge cases

### 5. Verify

Confirm the fix works:
- Test the original reproduction steps
- Run related tests
- Check for regressions

## Incident Documentation

After fixing a bug, use the debugger `store` MCP tool to document it for future retrieval.

The store tool accepts:
- **symptom** (required): User-facing description of the bug
- **root_cause** (required): Technical explanation of why the bug occurred
- **fix** (required): What was done to fix it
- **category**: Root cause category (logic, config, dependency, performance, react-hooks)
- **tags**: Search keywords for future retrieval
- **files_changed**: List of files that were modified
- **file**: Primary file where the bug was located

### Manual Incident Storage (Alternative)

Claude Code can also directly write incident files to `.claude/memory/incidents/` using the Write tool.

**Step 1: Generate incident ID**
```
INC_YYYYMMDD_HHMMSS_xxxx
```
Where `xxxx` is 4 random alphanumeric characters. Example: `INC_20241231_143052_a7b2`

**Step 2: Write JSON file**
```bash
.claude/memory/incidents/INC_20241231_143052_a7b2.json
```

**Minimal incident structure:**
```json
{
  "incident_id": "INC_20241231_143052_a7b2",
  "timestamp": 1735654252000,
  "symptom": "User-facing description of the bug",
  "root_cause": {
    "description": "Technical explanation of why the bug occurred",
    "file": "path/to/problematic/file.ts",
    "category": "logic|config|dependency|performance|react-hooks",
    "confidence": 0.85
  },
  "fix": {
    "approach": "What was done to fix it",
    "changes": [
      {
        "file": "path/to/file.ts",
        "lines_changed": 10,
        "change_type": "modify|add|delete",
        "summary": "Brief description of change"
      }
    ]
  },
  "verification": {
    "status": "verified|unverified",
    "regression_tests_passed": true,
    "success_criteria_met": true
  },
  "tags": ["relevant", "keywords", "for", "search"],
  "files_changed": ["list/of/all/files.ts"],
  "quality_score": 0.75
}
```

**Step 3: Ensure directory exists**
Before writing, create the directory if needed:
```bash
mkdir -p .claude/memory/incidents
```

### Quality Indicators

The memory system scores incidents on:
- Root cause analysis depth (30%)
- Fix documentation completeness (30%)
- Verification status (20%)
- Tags and metadata (20%)

Target 75%+ quality score for effective future retrieval.

### Tagging Strategy

Apply descriptive tags for better searchability:
- Technology: `react`, `typescript`, `api`, `database`
- Category: `logic`, `config`, `dependency`, `performance`
- Symptom type: `crash`, `render`, `timeout`, `validation`

## Using Past Solutions

When the memory system finds a match:

1. **Review the past incident** - Understand the original context
2. **Assess applicability** - Consider differences in current situation
3. **Adapt the fix** - Modify as needed for current codebase
4. **Verify thoroughly** - The same symptom may have different causes

## Pattern Recognition

The memory system automatically extracts patterns when 3+ similar incidents exist. Patterns represent reusable solutions with higher reliability than individual incidents.

When a pattern matches:
- Trust the solution template (90%+ confidence)
- Apply the recommended approach
- Note any caveats mentioned

## MCP Tools Quick Reference

| Tool | Purpose |
|------|---------|
| `search` | Search memory for similar bugs (returns verdict) |
| `store` | Store a new debugging incident |
| `detail` | Get full details of an incident or pattern |
| `status` | Show memory statistics |
| `list` | List recent incidents |
| `patterns` | List known fix patterns |
| `outcome` | Record whether a fix worked |

## Parallel Domain Assessment

For complex issues that may span multiple areas (database, frontend, API, performance), use parallel assessment to diagnose all domains simultaneously.

### When to Use Parallel Assessment

- Symptom is vague or unclear ("app broken", "something wrong")
- Multiple domains may be involved ("search is slow and returns wrong results")
- Post-deploy regression with unknown scope
- Complex issues affecting multiple layers

### Domain Assessors

Four specialized assessor agents are available:

| Assessor | Expertise |
|----------|-----------|
| `database-assessor` | Prisma, PostgreSQL, queries, migrations, connection issues |
| `frontend-assessor` | React, hooks, rendering, state, hydration, SSR |
| `api-assessor` | Endpoints, REST/GraphQL, auth, middleware, CORS |
| `performance-assessor` | Latency, memory, CPU, bottlenecks, optimization |

### Parallel Execution

Launch assessors **in parallel** using the Task tool:

```
For: "search is slow and returns wrong results"

Launch simultaneously:
- database-assessor (query performance)
- api-assessor (endpoint correctness)
- performance-assessor (latency analysis)
```

Each assessor returns a JSON assessment with:
- `confidence`: 0-1 score
- `probable_causes`: List of likely issues
- `recommended_actions`: Steps to fix
- `related_incidents`: Past memory matches

### Domain Detection Keywords

| Domain | Trigger Keywords |
|--------|-----------------|
| Database | query, schema, migration, prisma, sql, connection, constraint, index |
| Frontend | react, hook, useEffect, render, component, state, hydration, browser |
| API | endpoint, route, request, response, auth, 500, 404, cors, middleware |
| Performance | slow, latency, timeout, memory, leak, cpu, bottleneck, optimization |

### Result Aggregation

After parallel assessments complete:
1. Rank by confidence score (highest first)
2. Consider evidence count (more related incidents = higher priority)
3. Generate priority ranking of recommended actions
4. Present unified diagnosis with action sequence

## Trace Integration

The debugger can ingest traces from multiple sources to aid diagnosis:

### Supported Trace Sources

- **OpenTelemetry (OTLP)**: Distributed tracing spans
- **Sentry**: Error events and breadcrumbs
- **Langchain/LangSmith**: LLM operation traces
- **Browser**: Chrome DevTools, Playwright, console logs

### Using Traces for Debugging

When traces are available:
1. Correlate error traces with symptoms
2. Review performance spans for latency issues
3. Check LLM traces for AI-related bugs
4. Examine browser console for frontend errors

Traces are summarized to minimize token usage while preserving key diagnostic information.

## Token-Efficient Retrieval

The memory system uses tiered retrieval to minimize context size:

### Retrieval Tiers

| Tier | Token Usage | Content |
|------|-------------|---------|
| Summary | ~100 tokens | ID, symptom preview, category |
| Compact | ~200 tokens | Short keys, essential fields |
| Full | ~550 tokens | Complete incident details |

### Automatic Token Budgeting

Default budget: 2500 tokens
- Patterns: 30% (750 tokens)
- Incidents: 60% (1500 tokens)
- Metadata: 10% (250 tokens)

The system automatically selects the appropriate tier based on available budget.

## Subagent Integration

When debugging involves subagents (your own or from other plugins), follow these guidelines to ensure debugging memory is utilized.

### Automatic Behavior

**Before spawning debugging-related subagents:**
1. Search debugging memory first using the debugger `search` MCP tool
2. Pass relevant context to the subagent in its prompt
3. Include any matching incidents or patterns found

**Example subagent prompt with debugging context:**
```
Investigate the database timeout issue.

DEBUGGING MEMORY CONTEXT:
- Found 2 similar incidents: INC_20241215_db_timeout, INC_20241201_pool_exhaust
- Pattern PTN_connection_pool suggests checking pool size and idle timeout
- Previous fix: Increased pool size from 10 to 25 in DATABASE_URL

Start your investigation considering this prior knowledge.
```

### When Subagents Cannot Access Debugging Memory

**Inform the user** when debugging memory cannot be used with subagents:

1. **External MCP tools**: "Note: The debugging subagent is using external MCP tools that cannot access local debugging memory. I searched memory beforehand and found [X matching incidents / no matches]."

2. **Third-party agents**: "Note: This third-party debugging agent doesn't have access to your project's debugging memory. Consider searching debugging memory first to check for similar past issues."

3. **Sandboxed environments**: "Note: The subagent runs in a sandboxed environment without access to debugging memory. I've pre-loaded relevant context from [X] matching incidents."

### Coordinating Multiple Debugging Subagents

When using parallel assessment or multiple debugging subagents:

1. **Pre-query memory once** using the debugger `search` MCP tool before spawning agents
2. **Distribute context** - each agent gets relevant subset
3. **Aggregate findings** - collect new insights from all agents
4. **Store unified incident** - use the debugger `store` MCP tool to document the combined diagnosis

## Best Practices

1. **Always check memory first** - Use the `search` tool before investigating any bug
2. **Document every fix** - Use the `store` tool after resolving bugs
3. **Use descriptive symptoms** - Better matching requires good descriptions
4. **Include verification status** - Helps prioritize trusted solutions
5. **Record outcomes** - Use the `outcome` tool to improve future verdicts
6. **Pass context to subagents** - Don't let debugging knowledge stay siloed
7. **Inform users of limitations** - Be transparent when memory can't be accessed
