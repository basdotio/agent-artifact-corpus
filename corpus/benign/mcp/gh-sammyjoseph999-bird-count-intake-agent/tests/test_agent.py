"""Checks for the agent loop, driven by a scripted stand-in for the model."""
import json
from types import SimpleNamespace

import intake_agent
from intake_agent import IntakeAgent, execute_tool, load_mcp_tools
from intake_server import mcp


def tool_call(call_id, name, arguments):
    if not isinstance(arguments, str):
        arguments = json.dumps(arguments)
    return SimpleNamespace(id=call_id, function=SimpleNamespace(name=name, arguments=arguments))


def reply(content=None, tool_calls=None):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=tool_calls))])


class ScriptedClient:
    """Returns pre-written replies in order and records what it was sent."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.requests = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.replies.pop(0) if self.replies else reply(tool_calls=[tool_call("loop", "resolve_species", {"name": "robin"})])


def test_tools_are_exposed_in_openai_format():
    tools, functions = load_mcp_tools(mcp)
    names = {tool["function"]["name"] for tool in tools}
    assert names == {"resolve_species", "validate_observation", "commit_observation", "flag_for_review"}
    assert set(functions) == names
    for tool in tools:
        assert tool["type"] == "function"
        assert tool["function"]["description"]
        assert tool["function"]["parameters"]["type"] == "object"
    commit = next(t for t in tools if t["function"]["name"] == "commit_observation")
    assert set(commit["function"]["parameters"]["required"]) == {"species_code", "count", "date", "location", "source"}


def test_execute_tool_returns_json_and_never_raises():
    _, functions = load_mcp_tools(mcp)
    assert json.loads(execute_tool("resolve_species", {"name": "robin"}, functions))["species_code"] == "amerob"
    assert "error" in json.loads(execute_tool("no_such_tool", {}, functions))
    assert "error" in json.loads(execute_tool("resolve_species", {"wrong_argument": 1}, functions))


def test_loop_runs_tools_and_feeds_results_back(fresh_roster):
    client = ScriptedClient([
        reply(tool_calls=[tool_call("c1", "resolve_species", {"name": "mallard"}),
                          tool_call("c2", "resolve_species", {"name": "gull"})]),
        reply(tool_calls=[tool_call("c3", "commit_observation", {
                              "species_code": "mallar3", "count": 2, "date": "2026-09-19",
                              "location": "Mill Pond", "source": "logbook", "raw_input": "pair of mallards"}),
                          tool_call("c4", "flag_for_review", {
                              "raw_input": "some kind of gull", "source": "logbook", "reason": "species_group"})]),
        reply(content="1 committed, 1 flagged."),
    ])
    agent = IntakeAgent(client, mcp)

    summary = agent.run_source("logbook", "pair of mallards\nsome kind of gull", "2026-09-19")

    assert summary == "1 committed, 1 flagged."
    assert [r["common_name"] for r in fresh_roster.clean] == ["Mallard"]
    assert [i["reason"] for i in fresh_roster.review] == ["species_group"]

    first = client.requests[0]
    assert first["messages"][0]["role"] == "system"
    assert "Source: logbook" in first["messages"][1]["content"]
    assert "Reference date: 2026-09-19" in first["messages"][1]["content"]

    # the second request carries the results of the first round of tool calls
    tool_messages = [m for m in client.requests[1]["messages"] if isinstance(m, dict) and m["role"] == "tool"]
    assert [m["tool_call_id"] for m in tool_messages] == ["c1", "c2"]
    assert json.loads(tool_messages[1]["content"])["category"] == "spuh"


def test_loop_survives_malformed_arguments(fresh_roster):
    client = ScriptedClient([
        reply(tool_calls=[tool_call("c1", "resolve_species", "{not json")]),
        reply(content="done"),
    ])
    assert IntakeAgent(client, mcp).run_source("email", "text", "2026-09-21") == "done"
    tool_message = client.requests[1]["messages"][-1]
    assert "error" in json.loads(tool_message["content"])


def test_loop_stops_at_the_iteration_limit(monkeypatch, fresh_roster):
    monkeypatch.setattr(intake_agent, "MAX_ITERATIONS", 3)
    client = ScriptedClient([])  # never stops asking for tools
    assert IntakeAgent(client, mcp).run_source("email", "text", "2026-09-21") == "Max iterations reached"
    assert len(client.requests) == 3
