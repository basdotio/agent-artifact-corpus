---
name: claude-research
description: Use Claude Code CLI for advanced web research, codebase analysis, and complex queries that exceed your own capabilities.
---

# Claude Code Research

You have access to Claude Code (`claude`) via the bash tool. Claude Code is
a powerful AI assistant with web search, file reading, code search, and
multi-step reasoning capabilities. Use it when a query exceeds what you
can do with your own tools.

## When to Use This

- **Web research** — current events, documentation, API references, comparisons
- **Deep codebase analysis** — understanding unfamiliar repos, tracing call chains
- **Complex reasoning** — questions requiring multiple tool calls chained together
- **Second opinion** — validating your own analysis or getting an alternative approach

Do NOT use this for tasks you can do directly (reading a file you already
know the path to, simple grep, etc). Reserve it for queries where Claude
Code's tool-use loop adds real value.

## Invocation

Always use `-p` (print mode) for non-interactive execution:

```bash
claude -p "your query here"
```

For complex queries that require multiple tool calls:

```bash
claude -p --timeout 120 "your query here"
```

## Patterns

### Web Research

```bash
claude -p "what are the current best practices for PostgreSQL connection pooling in serverless environments?"
```

```bash
claude -p --timeout 60 "find the official documentation for Discord.js v14 slash command permissions and summarize the key API methods"
```

### Codebase Analysis (run from repo root)

```bash
cd /path/to/repo && claude -p "how does the authentication middleware work? trace the full request flow from entry point to database query"
```

```bash
cd /path/to/repo && claude -p "what would break if I changed the User.email column from varchar to citext? check all queries, indexes, and application code"
```

### Structured Output

When you need machine-parseable results:

```bash
claude -p "list all REST endpoints in this project as a JSON array with fields: method, path, handler_file, auth_required"
```

### Comparative Analysis

```bash
claude -p --timeout 120 "compare the error handling in src/api/v1/ vs src/api/v2/ — what patterns changed and are there any regressions?"
```

## Important Constraints

- **Stateless** — each invocation starts fresh with no memory of previous calls.
  Include all necessary context in the prompt.
- **Timeout** — default 30s. Use `--timeout 120` for complex multi-step queries.
- **Working directory matters** — for codebase queries, ensure you're in the
  right repo. Claude Code reads CLAUDE.md and uses git context from cwd.
- **No stdin for large payloads** — keep prompts under ~4000 chars. If you need
  to pass large context, write it to a temp file and reference the path.
- **Cost awareness** — each invocation runs a full agent loop. Don't use it in
  tight loops or for trivial lookups.

## Composing Results

Claude Code returns markdown text. You can use the output directly in your
own responses or parse it for structured data. When chaining multiple
queries, extract the key findings from each and synthesize them yourself
rather than asking Claude Code to remember previous results.
