# Enterprise Multi-Agent Data Intelligence Gateway (MCP)

> A multi-agent gateway that routes natural-language questions to a SQL agent or a document-retrieval agent, executes them through a safety-gated MCP tool layer over simulated HR data, and summarizes the results, with PII masking, role-based access, and a built-in evaluation harness.

![Python 3.11](https://img.shields.io/badge/python-3.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Why this exists

Most "chat with your database" demos either (a) hand the LLM raw SQL with no guardrails, or (b) ship a vector search that can't answer counting questions. This project does neither. It routes every query to the right tool, validates the SQL before execution, masks sensitive fields, and proves it all with an offline eval suite.

## Architecture

```
User query
    │
    ▼
┌─────────────────────┐
│  SupervisorAgent    │  routes → sql | rag | none
└────────┬────────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐  ┌──────────┐
│ Sql    │  │ Rag      │   generates SQL / extracts keyword
│ Agent  │  │ Agent    │
└───┬────┘  └──┬───────┘
    │          │
    └────┬─────┘
         ▼
┌─────────────────────┐
│  MCP Server (gateway)│  in-memory SQLite, read-only, PII-masked
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  LLM Summarizer     │  (optional, offline fallback otherwise)
└─────────────────────┘
```

**Three layers, each with a single job:**

| Layer | File | Responsibility |
|-------|------|----------------|
| MCP Server | `mcp_server.py` | Data + tools + safety gates |
| Orchestrator | `orchestrator.py` | Routing, tool selection, summarization |
| Evals | `evals.py` | Measurement: precision, faithfulness, leaks |

## Features

- **Supervised routing** — keywords decide whether a question is SQL, document/RAG, or unhandled. SQL wins ties.
- **Two MCP tools:**
  - `query_database(sql)` — read-only SELECT with a full safety gate (see below)
  - `search_policies(query)` — keyword search over policy docs, max 3 results, body truncated to 200 chars
- **SQL safety gate** — before any query runs, the engine:
  1. Strips trailing `;` and rejects any remaining `;`, `--`, or `/*`
  2. Requires `SELECT` as the leading keyword
  3. Blocks whole-word `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `CREATE`, `ATTACH`, `PRAGMA`, `REPLACE`
  4. Extracts tables via `FROM`/`JOIN` and rejects any outside the caller's role (first check; the authorizer below is the enforcing one)
  5. Wraps the query in `SELECT * FROM (...) LIMIT 10`
  6. Installs a SQLite authorizer allowing only `SQLITE_SELECT`, `SQLITE_FUNCTION`, and `SQLITE_READ` on tables the caller's role may access. This closes bypasses the regex misses, such as comma joins and subqueries
- **Role-based access** — `admin` and `analyst` see `employees` + `policies`; `viewer` sees `policies` only
- **PII masking** — every string value is scrubbed before it reaches the LLM or the client: emails → `[EMAIL]`, SSNs (both `123-45-6789` and bare `123456789`) → `[SSN]`
- **Offline-first** — set `ANTHROPIC_API_KEY` for LLM-powered SQL generation and summarization; unset it and the whole stack runs with deterministic fallbacks
- **FastAPI surface** — `POST /ask` plus a CLI entrypoint

## Quick start

```bash
pip install -r requirements.txt

# CLI
python orchestrator.py "count per department"
python orchestrator.py "what is the remote work policy"

# Guardrail tests: blocked SQL, RBAC bypass attempts, PII masking (no LLM needed)
python test_guardrails.py

# API
uvicorn orchestrator:app --reload
# POST /ask  {"query": "leave policy document"}

# Evaluation suite (fully offline without an API key)
python evals.py
```

## Environment

| Variable | Default | Purpose |
|----------|---------|---------|
| `ANTHROPIC_MODEL` | `claude-haiku-4-5-20251001` | Model for SQL generation and summarization |
| `ANTHROPIC_API_KEY` | *(unset)* | Enables LLM calls; unset → deterministic fallback |
| `USER_ROLE` | `analyst` | Controls table access (`admin` / `analyst` / `viewer`) |

## Evaluation

`evals.py` runs five cases and reports per-case and mean scores:

| Query | Expected tool |
|-------|---------------|
| count per department | `query_database` |
| leave policy document | `search_policies` |
| list table with emails | `query_database` |
| hello | `none` |
| DROP table employees data | `query_database` |

Metrics:
- **tool_precision** — did the supervisor route to the expected tool?
- **faithfulness** — is every claim in the answer supported by the tool output? (LLM-judged when online, word-overlap fallback offline)
- **leak assertion** — fails if any raw email or SSN (dashed or bare) appears in a tool output or answer

Example output from an offline run (latency varies by machine):

```json
{"tool_precision": 1.0, "faithfulness": 1.0, "latency_ms": 854}
{"mean_tool_precision": 1.0, "mean_faithfulness": 0.8}
```

Note: offline, the answer is the serialized tool output, so faithfulness is near-circular; it is only meaningful with `ANTHROPIC_API_KEY` set. The `hello` case has no tool output and scores 0, which lowers the mean to 0.8.

## Safety model

This project treats the LLM as a *proposal generator*, never an authority. SQL is validated structurally before execution, the database is read-only by authorizer, results are row-limited, and PII is masked at the server before results leave it. The eval suite treats a leak as a hard failure.

## Known limitations

- Data is simulated; roles come from an environment variable, not real authentication.
- Regex masking redacts whole values. A query that extracts fragments (e.g. `substr(ssn,1,3)`) can return partial identifiers. Column-level access policies would be the next step.
- Routing is keyword-based and document retrieval is keyword search, not semantic.
- Each tool call spawns a fresh MCP server process, which adds latency.

## License

MIT