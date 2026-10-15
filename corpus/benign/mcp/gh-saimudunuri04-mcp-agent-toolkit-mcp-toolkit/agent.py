"""LangGraph agent: decide (LLM) -> act (MCP tool) -> ... -> validate -> answer."""
from __future__ import annotations

import json
from typing import TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from .llm import DECIDE_MARKER
from .mcp_client import MCPToolClient

MAX_STEPS = 4
MAX_ANSWER_CHARS = 4000

TOOL_CATALOG = """- doc_search(query: str, k: int = 3): Search bundled support documentation.
- record_lookup(record_id: str): Look up a record by ID (e.g. R-2003).
- text_stats(text: str): Compute text statistics (counts, reading time, keywords)."""


class AgentState(TypedDict, total=False):
    question: str
    steps: list
    observations: list
    answer: str
    tools_used: list
    valid: bool
    decision: dict


def _synthesize(state: AgentState) -> str:
    parts = [
        f"{s['tool']}: {o[:200]}"
        for s, o in zip(state.get("steps", []), state.get("observations", []))
    ]
    return "Based on tool results — " + " | ".join(parts)


def build_agent(llm, tool_client: MCPToolClient):
    def decide_node(state: AgentState) -> dict:
        history = "\n".join(
            f"Action: tool={s['tool']} args={json.dumps(s['args'])}\n"
            f"Observation[{s['tool']}]: {o}"
            for s, o in zip(state.get("steps", []), state.get("observations", []))
        ) or "(no actions yet)"
        if len(state.get("steps", [])) >= MAX_STEPS:
            return {"decision": {"answer": _synthesize(state)}}
        prompt = (
            f"{DECIDE_MARKER}\nYou are a tool-using assistant. Available tools:\n"
            f"{TOOL_CATALOG}\nQuestion: {state['question']}\nHistory:\n{history}\n"
            'Reply with EXACTLY one JSON object: {"tool": "<name>", "args": {...}} '
            'to call a tool, or {"answer": "<final answer>"} to answer directly.'
        )
        raw = llm.invoke([HumanMessage(content=prompt)]).content.strip()
        try:
            decision = json.loads(raw)
        except Exception:
            decision = {"answer": raw[:MAX_ANSWER_CHARS]}
        return {"decision": decision}

    async def act_node(state: AgentState) -> dict:
        decision = state.get("decision", {})
        name, args = decision.get("tool"), decision.get("args") or {}
        try:
            observation = await tool_client.call_tool(name, args)
            ok = True
        except Exception as exc:
            observation, ok = f"tool_error: {exc}", False
        steps = list(state.get("steps", [])) + [{"tool": name, "args": args, "ok": ok}]
        observations = list(state.get("observations", [])) + [observation]
        tools_used = list(state.get("tools_used", []))
        if name not in tools_used:
            tools_used.append(name)
        return {"steps": steps, "observations": observations, "tools_used": tools_used}

    def validate_node(state: AgentState) -> dict:
        answer = (state.get("answer") or "").strip()
        valid = bool(answer) and len(answer) <= MAX_ANSWER_CHARS
        if not valid:
            answer = "I couldn't produce a reliable answer. Please try rephrasing."
        return {"answer": answer, "valid": valid}

    def after_decide(state: AgentState) -> str:
        decision = state.get("decision", {})
        if "answer" in decision:
            return "validate"
        return "act"

    def _answer_from_decision(state: AgentState) -> dict:
        return {"answer": state.get("decision", {}).get("answer", "")}

    graph = StateGraph(AgentState)
    graph.add_node("decide", decide_node)
    graph.add_node("act", act_node)
    graph.add_node("take_answer", _answer_from_decision)
    graph.add_node("validate", validate_node)
    graph.set_entry_point("decide")
    graph.add_conditional_edges("decide", after_decide, {"act": "act", "validate": "take_answer"})
    graph.add_edge("act", "decide")
    graph.add_edge("take_answer", "validate")
    graph.add_edge("validate", END)
    return graph.compile()


async def run_ask(app, question: str) -> dict:
    state = await app.ainvoke({"question": question})
    return {
        "answer": state.get("answer", ""),
        "tools_used": state.get("tools_used", []),
        "steps": len(state.get("steps", [])),
        "valid": bool(state.get("valid", False)),
    }
