---
name: search-codebase
description: >-
  Searches and indexes codebases using natural language queries via hybrid
  keyword and semantic search. Use when the user wants to find files in a
  project, understand code structure, locate implementations, or discover
  related files. Triggers on queries like "find the authentication logic",
  "where is the database connection handled", or "search this codebase for
  error handling".
compatibility: Requires the filesift Python package (pip install filesift). Python 3.12+.
metadata:
  author: roshunsunder
  version: "1.0.1"
allowed-tools: Bash(filesift:*)
---

# Searching Codebases with FileSift

FileSift indexes codebases and enables natural language search via hybrid keyword (BM25) + semantic (FAISS embeddings) search, merged with Reciprocal Rank Fusion.

## When to use this skill

Use FileSift when the target is a **concept or behaviour**, not a known identifier.

**Reach for FileSift when:**
- You're in the exploration phase of a task and need to orient yourself in an unfamiliar codebase
- The user asks a question that requires understanding *what* code does ("how is auth handled?", "where does billing happen?", "what validates user input?")
- You need to find an implementation but don't know what it's called — you'd have to guess grep patterns
- You're looking for the files most relevant to a concept that could be expressed many ways (`retry`, `backoff`, `exponential_sleep`, `with_retries` …)
- You've read one relevant file and want to find its collaborators by semantic proximity

**Prefer grep / glob instead when:**
- You already know the exact function name, class name, or string to search for
- You're tracing a known call chain or import path
- The search is purely structural (file extensions, directory layout, naming conventions)
- The codebase is small enough that a directory listing gives you the full picture

The rule of thumb: if you'd have to *guess* the right grep pattern, FileSift will outperform it. If you already *know* the exact token, grep is faster.

## Step 0 — Verify FileSift is installed

**Do this before anything else, every time this skill is invoked for the first time in a session.**

```bash
filesift --version
```

If the command is found, proceed to [Quick start](#quick-start).

If it isn't found, install it. FileSift requires **Python 3.12+** and is published on PyPI. The right install command depends on how the user manages Python packages. Always ask the user before running any installation commands.

| Environment | Install command |
|---|---|
| pip (default) | `pip install filesift` |
| uv (tool) | `uv tool install filesift` |
| uv (project) | `uv add filesift` |
| pipx | `pipx install filesift` |
| poetry | `poetry add filesift` |
| pdm | `pdm add filesift` |
| conda / mamba | `pip install filesift` (inside the active conda env) |

After installing, confirm with `filesift --version` before proceeding.

## Quick start

### 1. Check if an index exists

```bash
ls <project-root>/.filesift/
```

If `.filesift/` exists, skip to step 3.

### 2. Index the codebase

```bash
filesift index <project-root>
```

- Fast indexing (keyword/structural) completes in seconds
- Semantic indexing (embeddings) runs in the background and may take 1-3 minutes for large codebases
- You can search immediately with keyword-only results while semantic indexing completes

### 3. Search

```bash
filesift find "<natural language query>" --path <project-root>
```

Use conceptual descriptions, not code syntax:
- "user authentication and session management"
- "database connection pooling"
- "error handling and retry logic"
- "API rate limiting middleware"

Results are ranked by relevance score (0-1). Read the top results to understand the actual implementation.

**Iterating on results**

A single search is rarely enough for complex questions. If the top results don't contain what you're looking for, don't stop — reframe and search again. Treat FileSift like a conversation: each result gives you vocabulary (function names, module names, patterns) you can feed into the next query. Common iteration strategies:

- Results are in the right area but too broad → narrow with a more specific verb or concept (`"parse JWT claims"` instead of `"authentication"`)
- Results miss the mark entirely → try a synonym or a different layer of abstraction (`"token refresh"` instead of `"login"`)
- You found one relevant file but need its collaborators → query for what that file *calls* (`"session store write"`, `"user lookup by id"`)
- A concept spans multiple files → run separate focused queries for each sub-concern and union the results yourself

Only conclude that something doesn't exist in the codebase after at least 2–3 differently-framed queries come up empty.

**Formulating effective queries**

The semantic index embeds raw source code. The embedding model (jina-embeddings-v2-base-code) was trained on 150M+ natural language / code pairs, so it bridges intent-based queries directly to code. Despite this, query quality directly determines result quality — the model encodes each query into a single dense vector, so a vague or overloaded query produces a vague result.

**Core rule:** Translate the user's request into a short (3–7 word) description of what the target code *does*, as a developer would phrase it in a docstring. Do not paste the user's question verbatim.

Guidelines:
- **Strip question framing** — Remove "how does", "where is", "I need to understand", "code that handles". These words don't appear in code.
- **Lead with an action verb** — "parse", "validate", "authenticate", "retry", "transform" match function names and docstrings.
- **One concept per query** — For multi-part user requests, run separate focused queries rather than one long combined query. A single long query dilutes the embedding signal.
- **Use developer vocabulary** — Think: what would a developer name this function, or write in its docstring?

| User request | Bad query | Good queries |
|---|---|---|
| "How does the app handle user login and JWT tokens?" | `"how app handles user login and JWT token management"` | `"user authentication"` + `"JWT token validation"` |
| "I want to understand how database errors are caught and retried" | `"catching retrying database errors logic"` | `"database error handling"` |
| "Where is the config loaded from at startup?" | `"config loading parsing startup initialization"` | `"configuration loading"` |
| "How does payment processing work, including webhooks?" | `"payment processing webhooks implementation"` | `"payment processing"` + `"webhook handler"` |

### 4. Re-index after significant changes

```bash
filesift index <project-root> --reindex
```

Use `--reindex` to force a full rebuild. Without it, only changed files are re-indexed.

## Tips

- **Default path**: If the project root is the current working directory, `--path` can be omitted
- **More results**: Default is 5 results. Change with `filesift config set search.MAX_RESULTS 20`
- **Multiple projects**: Each project gets its own `.filesift/` directory; index each separately

## Advanced usage

See [references/ADVANCED.md](references/ADVANCED.md) for daemon management, configuration tuning, and troubleshooting.
