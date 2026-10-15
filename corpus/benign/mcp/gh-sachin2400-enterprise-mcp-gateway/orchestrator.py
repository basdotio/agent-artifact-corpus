"""Supervisor routing and FastAPI orchestration over the MCP server."""

import asyncio
import json
import os
import re
import sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from anthropic import Anthropic
from fastapi import FastAPI
from pydantic import BaseModel

MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")
_client = Anthropic() if os.getenv("ANTHROPIC_API_KEY") else None

SCHEMA = """Table employees(id INT, name TEXT, email TEXT, ssn TEXT, department TEXT, salary INT)
Table policies(id INT, title TEXT, body TEXT)"""


class QueryRequest(BaseModel):
    query: str


def _call_llm(system: str, user: str) -> str:
    if _client is None:
        return ""
    try:
        resp = _client.messages.create(model=MODEL, max_tokens=256, messages=[{"role": "user", "content": user}], system=system)
        return resp.content[0].text
    except Exception:
        return ""


class SupervisorAgent:
    """Routes queries to SQL, RAG, or none."""

    @staticmethod
    def route(query: str) -> str:
        q = query.lower()
        sql_kw = ["data", "count", "table", "employees", "salary"]
        rag_kw = ["document", "policy"]
        if any(k in q for k in sql_kw):
            return "sql"
        if any(k in q for k in rag_kw):
            return "rag"
        return "none"


class SqlAgent:
    """Generates a safe SQLite SELECT from a natural-language query."""

    @staticmethod
    def generate_sql(query: str) -> str:
        text = _call_llm(
            system=f"Output ONLY one SQLite SELECT query. Schema: {SCHEMA}. No prose, no markdown fences.",
            user=query,
        )
        text = text.strip().strip("`").strip()
        if text.lower().startswith("sql"):
            text = text[3:].strip()
        if text:
            return text
        destructive = ["drop", "delete", "update", "insert", "alter", "create", "attach", "pragma", "replace"]
        if any(re.search(rf"\b{w}\b", query.lower()) for w in destructive):
            return query
        if "count" in query.lower():
            return "SELECT department, COUNT(*) AS n FROM employees GROUP BY department"
        return "SELECT id, name, email, ssn, department FROM employees"


class RagAgent:
    """Retrieves policy documents via the MCP search_policies tool."""

    @staticmethod
    def retrieve(query: str) -> str:
        words = [w for w in query.split() if len(w) > 3]
        return max(words, key=len) if words else "policy"


async def call_tool(name: str, args: dict) -> dict:
    """Spawn the MCP server over stdio and invoke a tool."""
    server = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mcp_server.py")
    params = StdioServerParameters(command=sys.executable, args=[server], env={"USER_ROLE": os.getenv("USER_ROLE", "analyst")})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, args)
            return json.loads(result.content[0].text)


async def handle(query: str) -> dict:
    """Route a query, run the appropriate tool, and produce a final answer."""
    route = SupervisorAgent.route(query)
    if route == "sql":
        tool = "query_database"
        sql = await asyncio.to_thread(SqlAgent.generate_sql, query)
        tool_output = await call_tool(tool, {"sql": sql})
    elif route == "rag":
        tool = "search_policies"
        sql = ""
        keyword = RagAgent.retrieve(query)
        tool_output = await call_tool(tool, {"query": keyword})
        if not tool_output.get("rows"):
            tool_output = await call_tool(tool, {"query": "policy"})
    else:
        return {"route": "none", "tool": "none", "sql": "", "tool_output": {}, "answer": "No matching agent."}

    answer = ""
    if _client is not None:
        answer = await asyncio.to_thread(
            _call_llm,
            "Summarize the tool output for the user. If the answer is not present in the tool output, say 'not found'. No prose.",
            f"Query: {query}\nTool output: {json.dumps(tool_output)}",
        )
    answer = answer or json.dumps(tool_output)

    return {"route": route, "tool": tool, "sql": sql, "tool_output": tool_output, "answer": answer}


app = FastAPI()


@app.post("/ask")
async def ask(req: QueryRequest):
    return await handle(req.query)


if __name__ == "__main__":
    print(json.dumps(asyncio.run(handle(sys.argv[1] if len(sys.argv) > 1 else "count per department"))))