---
name: langfuse-data-retrieval
description: This skill should be used when the user asks to "get langfuse traces", "fetch trace data", "retrieve last traces", "show me the trace", "debug a trace", "analyze trace ID", "what happened in trace", or needs to pull Langfuse observability data for debugging or analysis. Provides surgical trace retrieval with multiple output modes to avoid overwhelming context.
---

# Langfuse Data Retrieval

Surgical extraction of Langfuse traces with output modes that filter to what matters. Outputs formatted markdown optimized for LLM consumption.

## When to Use

- Debugging a specific trace or recent workflow runs
- Understanding what inputs/outputs flowed through a pipeline
- Investigating tool calls and their results
- Quick overview of recent trace activity

## Output Modes

| Mode | What It Shows | Use When |
|------|---------------|----------|
| `io` | Node inputs/outputs + tool calls | **Default** - Core debugging |
| `minimal` | Trace ID, name, timestamp, status | Quick listing |
| `prompts` | LLM prompts and responses only | Prompt quality analysis |
| `flow` | Node names, order, timing | Performance investigation |
| `full` | Everything (costs, tokens, metadata) | Deep investigation |

The `io` mode is the default and recommended mode - it shows the substance of what happened without metrics bloat.

## Retrieval Methods

### Single Trace by ID

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id abc123def456
```

### Last N Traces

```bash
# Last 1 trace (default)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py --last 1

# Last 3 traces
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py --last 3
```

### Filtered Retrieval

```bash
# By metadata field (e.g., project_id, environment, user_id)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 2 --filter-field project_id --filter-value myproject

# By tags
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 5 --tags production api-v2

# Custom time range
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 10 --days 3
```

**Metadata filtering options:**
- `--filter-field NAME` - Any metadata field to filter by
- `--filter-value VALUE` - Value to match for the filter field

### Score-Based Filtering

Filter traces by scores for optimization workflows:

```bash
# Find low-scoring traces (score <= 7.0)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 20 --max-score 7.0 --mode minimal

# Find high-quality traces for golden sets (score >= 9.0)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 10 --min-score 9.0 --mode minimal

# Filter by specific score name
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 10 --min-score 8.0 --score-name custom_quality_score

# Combined: failing traces for a specific project
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 30 --filter-field project_id --filter-value myproject --max-score 7.0 --mode minimal
```

**Score filtering options:**
- `--min-score FLOAT` - Include traces with score >= value
- `--max-score FLOAT` - Include traces with score <= value
- `--score-name NAME` - Score name to filter by (default: `quality_score`)

**Note:** Score filtering is client-side, so the tool fetches more traces initially to ensure it can return enough matching results. Traces without the specified score are excluded.

## Mode Examples

### io Mode (Default)

Shows node inputs/outputs and tool calls without metrics:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id abc123 --mode io
```

Output includes:
- Each node's input and output
- Tool/function calls with their inputs and results
- Error messages and status
- No: token counts, costs, latencies, verbose metadata

### prompts Mode

Focus on LLM interactions only:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 1 --mode prompts
```

### flow Mode

Understand execution order and timing:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 1 --mode flow
```

### minimal Mode

Quick overview without observation details:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 10 --mode minimal
```

## Credential Configuration

Credentials are loaded automatically from multiple sources (in priority order):

1. **Environment variables** (if not placeholders)
2. **Project `.env` file** (current directory)
3. **User config `~/.langfuse.env`**

### Option 1: User Config (Recommended)

Create `~/.langfuse.env` for global access across all projects:

```bash
# ~/.langfuse.env
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-key-here
LANGFUSE_HOST=https://cloud.langfuse.com  # Optional
```

### Option 2: Project `.env`

Add to your project's `.env` file for project-specific credentials:

```bash
# .env
LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
LANGFUSE_SECRET_KEY=sk-lf-your-key-here
```

### Option 3: Environment Variables

Export in your shell or add to `.zshrc`/`.bashrc`:

```bash
export LANGFUSE_PUBLIC_KEY=pk-lf-your-key-here
export LANGFUSE_SECRET_KEY=sk-lf-your-key-here
```

### Test Connection

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/langfuse_client.py
```

**Note:** Placeholder values like `your_public_key` or `YOUR_SECRET_KEY` are automatically detected and skipped.

## Common Workflows

### Debug a Failing Trace

1. Get the trace ID from Langfuse dashboard or logs
2. Retrieve with io mode to see full flow:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id <id> --mode io
```

### Review Recent Activity

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 5 --mode minimal
```

### Compare Before/After

```bash
# Get traces before change
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id <before_id> --mode io

# Get traces after change
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id <after_id> --mode io
```

### Investigate Specific Workflow

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 1 --filter-field workflow_name --filter-value checkout --mode io
```

Look for span observations to see which operations were performed and their outputs.

### Find Traces Pending Annotation

Use the **annotation-manager** skill for annotation queue workflows:

```bash
# Find traces missing human review (last 7 days)
python3 ${CLAUDE_PLUGIN_ROOT}/skills/annotation-manager/helpers/annotation_manager.py \
  pending --score-name "human_review" --days 7 --limit 20

# Find traces missing quality scores for a specific trace type
python3 ${CLAUDE_PLUGIN_ROOT}/skills/annotation-manager/helpers/annotation_manager.py \
  pending --score-name "quality" --trace-name "chat-completion" --days 3
```

Once you identify traces needing review, use this skill's retrieval to inspect them:

```bash
# Get full details of a trace pending annotation
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id <pending_trace_id> --mode io
```

**Tip:** For high-volume annotation queues, consider increasing the timeout by running the annotation-manager helper with longer wait times, or process in smaller batches.

### Curate Regression Dataset

Identify failing traces for dataset curation:

```bash
# Step 1: Find failing traces
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --last 20 --max-score 7.0 --mode minimal

# Step 2: Investigate specific failing trace
python3 ${CLAUDE_PLUGIN_ROOT}/skills/data-retrieval/helpers/trace_retriever.py \
  --trace-id <failing_trace_id> --mode io

# Step 3: Use the trace IDs with dataset-management skill to create regression tests
```

## Output Format

The retriever outputs formatted markdown to stdout with:

- Trace header (ID, name, timestamp)
- Observations in execution order (flat list)
- Mode-appropriate field selection
- Truncation of very long values (>2000 chars)
- Clear section separators

## Troubleshooting

**No traces found:**
- Check time range with `--days`
- Verify filter field/value or tags exist in your traces
- Confirm Langfuse credentials are correct

**Connection errors:**
- Test with `python3 helpers/langfuse_client.py`
- Verify environment variables are set
- Check LANGFUSE_HOST if using self-hosted

**Too much output:**
- Use `--mode minimal` for overview
- Use `--mode prompts` to focus on LLM calls
- Reduce `--last N` count
