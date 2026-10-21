"""MCP server: the session's tools over stdio, for any MCP client (Claude Code, Cowork, others).

Bound to one project, one run and one scholar when it starts:

    qls mcp --run r1 --actor agent:scholar-1            # an analyst
    qls mcp --run r1 --actor reviewer:anna              # read-only

Method tools (add_concept, add_theme, ...) are generated from the method's actions.yaml.
Researcher actions (approve, reject, answer, resume) stay in the CLI, so an agent can never
approve its own work.
"""

from __future__ import annotations

import inspect
import os
import threading
from typing import Any

from .session import HUMAN_TOOLS, Session, is_human
from .util import QlsError

_LOCK = threading.Lock()  # tools run in worker threads; one call at a time per server

INSTRUCTIONS = """\
A qualitative-analysis memory server. The analysis lives in a graph whose ontology refuses what breaks
the method's form; you do the interpretation. Start with your task, then intent() (the research question:
findings should answer it), method_guide() (how to do the method), ways_of_working() and status().
Work one interview at a time with begin(source). Quotes are checked against the transcript in the same
call that adds a concept: copy the informant's exact words while the interview is in front of you.
Use memos and the codebook as your long-term memory; look things up instead of relying on recall.
When the method asks for a checkpoint, call checkpoint() and stop until the researcher resumes the run.
"""


def build_server(session: Session):
    try:
        from mcp.server.mcpserver import MCPServer as Server  # mcp >= 2
    except ImportError:
        try:
            from mcp.server.fastmcp import FastMCP as Server  # mcp 1.x
        except ImportError as exc:
            raise QlsError("pip install 'qual-analysis-mcp-tools[mcp]' to run the MCP server") from exc

    mcp = Server("qls", instructions=INSTRUCTIONS)
    for name in session.tools():
        if name in HUMAN_TOOLS:
            continue
        if name in session.m.actions:
            fn = method_tool(session, name)
        else:
            fn = _wrap(getattr(session, name), name)
        mcp.tool(name=name, description=fn.__doc__ or name)(fn)
    return mcp


def _wrap(fn, name):
    """Expose a bound method with its signature; turn errors into refusals the model can read."""
    sig = inspect.signature(fn)

    def tool(**kwargs):
        try:
            with _LOCK:
                out = fn(**kwargs)
                fn.__self__.log_read(name, kwargs, out)
                return out
        except QlsError as exc:
            return {"ok": False, "error": str(exc)}

    tool.__name__ = name
    tool.__doc__ = inspect.getdoc(fn)
    tool.__signature__ = sig
    tool.__annotations__ = {p.name: p.annotation for p in sig.parameters.values() if p.annotation is not inspect._empty}
    if sig.return_annotation is not inspect._empty:
        tool.__annotations__["return"] = sig.return_annotation
    return tool


def method_tool(session: Session, name: str):
    """A tool function for a method action, with parameters taken from actions.yaml."""
    a = session.m.actions[name]
    params, ann = [], {}

    def add(pname, typ, default=inspect.Parameter.empty):
        params.append(inspect.Parameter(pname, inspect.Parameter.KEYWORD_ONLY, default=default, annotation=typ))
        ann[pname] = typ

    fields = session.m.fields.get(a.type, [])
    for f in fields:
        if f.required:
            add(f.param, str)
    group = session.m.group_of(a.type) if a.kind == "create_group" else None
    if a.kind == "create_code":
        add("quotes", list[dict[str, Any]])
        if a.into:
            add(a.into_param, list[dict[str, Any]])
    elif group and group.min == 0:
        pass   # a group that may start empty: its members are optional (added below)
    else:
        add(a.members_param, list[dict[str, Any]])
        if a.answers == "required":
            add("answers", str)
    for f in fields:
        if not f.required:
            add(f.param, str | None, None)
    if a.kind == "create_code":
        add("source", str | None, None)
    if group and group.min == 0:
        add(a.members_param, list[dict[str, Any]] | None, None)
        if a.answers == "required":
            add("answers", str)
    if a.kind == "create_group" and a.answers == "optional":
        add("answers", str | None, None)

    def tool(**kwargs):
        try:
            with _LOCK:
                return session.act(name, **{k: v for k, v in kwargs.items() if v is not None})
        except QlsError as exc:
            return {"ok": False, "error": str(exc)}

    lines = [a.doc, "", "Parameters:"] + [f"- {f.param}: {f.doc}" for f in fields if f.doc]
    tool.__name__ = name
    tool.__doc__ = "\n".join(lines)
    tool.__signature__ = inspect.Signature(params, return_annotation=dict)
    tool.__annotations__ = {**ann, "return": dict}
    return tool


def main(project: str | None, run: str | None, actor: str | None, model: str | None = None) -> None:
    from .project import Project

    run = run or os.environ.get("QLS_RUN")
    actor = actor or os.environ.get("QLS_ACTOR")
    if not run or not actor:
        raise QlsError("qls mcp needs --run (or $QLS_RUN) and --actor (or $QLS_ACTOR)")
    if is_human(actor):
        raise QlsError("Researcher actions go through the CLI (qls respond / resume), not an MCP server.")
    session = Session(Project.find(project), run, actor, model or os.environ.get("QLS_MODEL"))
    build_server(session).run()
