"""qls: the researcher's command line, and a shell transport for agent tools.

Set up:
    qls init DIR                        project folder with qls.toml and intent.yaml
    qls doctor                          check TypeDB and the MCP SDK
    qls ingest FILES...                 add sources (txt/md/srt/vtt, or anything Docling reads)
    qls sources

Runs (one TypeDB database each):
    qls run new NAME [--intent intent.yaml] [--question "..."] [--method gioia|DIR] [--sources P01 P02]
    qls run fork RUN --at N --as NAME   branch after event N (default: latest)
    qls run fork RUN --at-stage S --as NAME   branch at the start of stage S
    qls run replay RUN                  rebuild from the log; the graph must be identical
    qls run drop RUN                    delete the run and its database
    qls runs | status RUN | log RUN [--since N] | check RUN

Researcher at a checkpoint:
    qls review RUN                      what happened since the last checkpoint; questions and uncertainty first
    qls respond RUN --approve CB-3 [--set use_when="..."] | --reject ID --reason R
                    | --revise ID --set label="..." --reason R | --answer "..."
    qls resume RUN
    qls stage RUN [STAGE|next]          show or move the run's stage (also resumes)

Agents:
    qls mcp --run RUN --actor agent:NAME [--model M]      MCP server (stdio)
    qls mcp-config RUN --actor agent:NAME                 .mcp.json entry for Claude Code / Cowork
    qls tool RUN NAME '{"json": "args"}' --actor A        any tool from the shell
    qls tools RUN --actor A                               list tools
    qls agent RUN --task TASK [--sources P01 ...]         one isolated agent session (Claude Code)
    qls pipeline RUN --auto --calibration K [--batch N] [--seed S] [--until STAGE]   all stages, AI-only policy
    qls sessions RUN | provenance RUN [--session ID]      who did what, with which prompt and model, having read what

Results:
    qls report RUN [--format md|html] [-o FILE]
    qls site RUN [-o FILE]              one-file website: graph, step by step, interviews, codebook, instructions, log
    qls compare RUN_A RUN_B             selection and structure agreement on informant segments
    qls query RUN 'match ... select ...;'
    qls methods | method NAME | guide
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import __version__
from .util import QlsError


def _p(a):
    from .project import Project

    return Project.find(a.project)


def _s(a, run: str, actor: str | None = None):
    from .session import Session

    actor = actor or getattr(a, "actor", None) or os.environ.get("QLS_ACTOR")
    if not actor:
        raise QlsError("Who is acting? Pass --actor (agent:NAME, human:NAME, reviewer:NAME) or set QLS_ACTOR.")
    return Session(_p(a), run, actor, os.environ.get("QLS_MODEL"))


def _researcher(a) -> str:
    actor = getattr(a, "actor", None) or os.environ.get("QLS_ACTOR") or ""
    return actor if actor.startswith(("human", "auto:")) else f"human:{os.environ.get('USER', 'researcher')}"


def _out(obj) -> None:
    print(obj if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False, indent=1, default=str))


def _sets(items: list[str] | None) -> dict:
    out = {}
    for it in items or []:
        if "=" not in it:
            raise QlsError(f"--set expects key=value, got {it!r}")
        k, v = it.split("=", 1)
        out[k.strip()] = v
    return out


# -- set up ---------------------------------------------------------------------

def cmd_init(a):
    from .project import Project

    p = Project.init(a.dir, a.name)
    print(f"Project at {p.root}. Next: write intent.yaml, start TypeDB, `qls ingest` the interviews, `qls run new r1`.")


def cmd_doctor(a):
    from .graph import Graph

    try:
        p = _p(a)
        g = p.graph
    except QlsError:
        g = Graph()
    try:
        names = [d.name for d in g.driver.databases.all()]
        print(f"TypeDB at {g.address}: reachable, {len(names)} database(s).")
    except QlsError as exc:
        print(f"TypeDB: {exc}")
    try:
        import mcp  # noqa: F401

        print("MCP SDK: installed.")
    except ImportError:
        print("MCP SDK: missing (pip install 'qual-analysis-mcp-tools[mcp]').")


def cmd_ingest(a):
    p = _p(a)
    for f in a.files:
        r = p.ingest(f, a.id if len(a.files) == 1 else None, a.participant, a.interviewer)
        roles = ", ".join(f"{k}={v}" for k, v in r["speakers"].items())
        print(f"{r['id']} v{r['version']}: {r['segments']} informant segments, {r['turns']} turns ({r['parser']}); {roles}")


def cmd_sources(a):
    L = _p(a).ledger
    for s in L.sources():
        src = L.source(s["id"])
        segs = sum(1 for u in src["units"] if u["kind"] == "segment")
        print(f"{s['id']:<20} v{s['version']}  {segs:>4} segments  {len(src['text']):>8} chars  {src['title']}")


# -- runs -----------------------------------------------------------------------

def cmd_run_new(a):
    p = _p(a)
    intent = p.read_intent(a.intent, research_question=a.question, stance=a.stance)
    config = {"note": a.note} if a.note else {}
    r = p.new_run(a.name, a.method or intent.get("method"), intent, a.sources, config)
    print(f"Run {r['run']} created: method {r['method']}, {r['sources']} sources, TypeDB database {r['db']}.")
    print(f"Attach an agent: qls mcp-config {r['run']} --actor agent:scholar-1")


def cmd_run_fork(a):
    r = _p(a).fork(a.run, a.name, a.at, a.note or "", a.at_stage)
    print(f"Run {r['run']} forked from {r['parent']} after event #{r['fork_at']} ({r['events']} events replayed).")


def cmd_run_replay(a):
    r = _p(a).replay(a.run)
    verdict = "identical" if r["identical"] else "DIFFERENT"
    print(f"{a.run}: {r['events']} events replayed; graph {verdict} ({r['live'][:19]} vs {r['replayed'][:19]})")
    if not r["identical"]:
        sys.exit(1)


def cmd_run_drop(a):
    if not a.yes:
        raise QlsError(f"This deletes run {a.run}, its log and its TypeDB database. Add --yes.")
    _p(a).drop_run(a.run)
    print(f"Run {a.run} dropped.")


def cmd_runs(a):
    for r in _p(a).ledger.runs():
        fork = f"  fork of {r['parent']}@{r['fork_at']}" if r["parent"] else ""
        print(f"{r['id']:<20} {r['method']:<10} {r['status']:<8} {r['created']}{fork}")


def cmd_status(a):
    _out(_s(a, a.run, a.actor or "reviewer:cli").status())


def cmd_check(a):
    _out(_s(a, a.run, a.actor or "reviewer:cli").check())


def cmd_log(a):
    from .report import what

    for e in _p(a).ledger.events(a.run, since=a.since):
        ids = ", ".join(e["result"].get("ids", []))
        detail = what(e) or ids or (e["params"].get("label") or e["params"].get("source") or "")
        reason = "" if e["reason"] in (str(detail), e["params"].get("label")) else e["reason"]
        print(f"#{e['seq']:<5} {e['actor']:<22} {e['action']:<18} {str(detail)[:70]:<70} {reason[:60]}")


# -- researcher -----------------------------------------------------------------

def cmd_review(a):
    s = _s(a, a.run, "reviewer:cli")
    p = s.L
    r = s.run
    evs = p.events(a.run)
    last = max([e["seq"] for e in evs if e["action"] in ("resume", "setup")] or [0])
    new = [e for e in evs if e["seq"] > last]
    print(f"Run {a.run}: {r['status']}" + (f" at checkpoint #{r['checkpoint_seq']}" if r["status"] == "waiting" else ""))
    print(f"Research question: {r['intent'].get('research_question')}\n")
    for e in new:
        if e["action"] == "checkpoint":
            print(f"Checkpoint #{e['seq']} by {e['actor']}: {e['params']['summary']}")
            for q in e["params"].get("questions") or []:
                print(f"  ? {q}")
    unc = [m for m in s.memos()["memos"] if m["kind"] in ("uncertainty", "negative-case")]
    if unc:
        print("\nUncertainty and negative cases:")
        for m in unc:
            print(f"  {m['id']} ({m['kind']}) about {', '.join(m['about'])}: {m['text'][:300]}")
    props = [e for e in s.codebook()["entries"] if e["status"] == "proposed"]
    if props:
        print("\nCodebook proposals (qls respond RUN --approve ID | --reject ID --reason R):")
        for e in props:
            print(f"  {e['id']} {e['label']} (by {e['by']}): {e['definition']}")
    counts = {}
    for e in new:
        counts[e["action"]] = counts.get(e["action"], 0) + 1
    print(f"\nSince #{last}: " + ", ".join(f"{k} {v}" for k, v in counts.items()))
    created = [(e["result"].get("id"), e["params"].get("label")) for e in new if e["action"] in s.m.actions]
    for cid, label in created[:80]:
        print(f"  + {cid} {label}")
    open_ = s.check()["open"]
    print(f"\nStill open: {len(open_)} (qls check {a.run})")
    print(f"Full detail: qls report {a.run} --format html -o reports/{a.run}.html")


def cmd_respond(a):
    s = _s(a, a.run, _researcher(a))
    if a.approve:
        _out(s.approve(a.approve, _sets(a.set), a.reason or ""))
    elif a.reject:
        if not a.reason:
            raise QlsError("--reject needs --reason")
        _out(s.reject(a.reject, a.reason))
    elif a.revise:
        if not a.reason:
            raise QlsError("--revise needs --reason")
        _out(s.revise(a.revise, _sets(a.set), a.reason))
    elif a.answer:
        _out(s.answer(a.answer))
    else:
        raise QlsError("Give --approve, --reject, --revise or --answer.")


def cmd_resume(a):
    _out(_s(a, a.run, _researcher(a)).resume(a.note or ""))


def cmd_stage(a):
    s = _s(a, a.run, _researcher(a))
    if not a.stage:
        _out({"stage": s.stage(), "stages": [x["id"] for x in s.m.stages], "status": s.run["status"]})
        return
    _out(s.set_stage(a.stage, a.reason or ""))


# -- agents ---------------------------------------------------------------------

def cmd_agent(a):
    from .agent import run_session

    _out(run_session(_p(a), a.run, a.task, a.sources, a.actor or "agent:scholar-1", a.model, a.web))


def cmd_pipeline(a):
    from .agent import pipeline

    if not a.auto:
        raise QlsError("pipeline runs every stage with the AI-only policy; pass --auto. For human review, use `qls agent` per task.")
    pipeline(_p(a), a.run, a.calibration, a.seed, a.batch, a.actor or "agent:scholar-1", model=a.model, until=a.until,
             say=lambda m: print(m, flush=True))


def cmd_sessions(a):
    for r in _p(a).ledger.sessions(a.run):
        print(f"{r['started'][:19]}  {r['id']:<40} {r['task']:<18} stage={r['stage']:<12} model={r['model']} exit={r['exit']} "
              f"prompt={r['prompt_sha'][:12]}")


def cmd_provenance(a):
    L = _p(a).ledger
    evs = [e for e in L.events(a.run) if not a.session or e["meta"].get("session") == a.session]
    reads = L.reads(a.run, a.session)
    if a.json:
        _out({"events": [{k: e[k] for k in ("seq", "action", "actor", "model", "meta", "reason", "ts")} for e in evs], "reads": reads})
        return
    for e in evs:
        m = e["meta"]
        print(f"#{e['seq']:<5} {e['action']:<18} {e['actor']:<18} stage={m.get('stage')} task={m.get('task')} "
              f"model={e['model']} session={m.get('session')}  {str(e['reason'])[:60]}")
    print(f"{len(reads)} reads" + (f" in session {a.session}" if a.session else ""))
    for r in reads[-a.tail:] if a.tail else []:
        print(f"  after #{r['after_seq']:<5} {r['tool']:<16} {r['args'][:80]}  ({r['size']} chars)")


def cmd_mcp(a):
    from .server import main

    main(a.project, a.run, a.actor, a.model)


def cmd_mcp_config(a):
    p = _p(a)
    p.ledger.run(a.run)
    args = ["-m", "qls", "mcp", "--project", str(p.root), "--run", a.run, "--actor", a.actor]
    if a.model:
        args += ["--model", a.model]
    env = {k: os.environ[k] for k in ("QLS_TYPEDB", "QLS_TYPEDB_USER", "QLS_TYPEDB_PASSWORD") if k in os.environ}
    entry = {"command": sys.executable, "args": args}
    if env:
        entry["env"] = env
    _out({"mcpServers": {"qls": entry}})


def cmd_tool(a):
    args = json.loads(a.args) if a.args else {}
    _out(_s(a, a.run).call(a.name, args))


def cmd_tools(a):
    s = _s(a, a.run)
    for name in s.tools():
        fn = getattr(s, name, None)
        doc = (s.m.actions[name].doc if name in s.m.actions else (fn.__doc__ or "")).split("\n")[0].strip()
        print(f"{name:<20} {doc[:110]}")


# -- results --------------------------------------------------------------------

def cmd_report(a):
    from .report import build, to_html, to_markdown

    rep = build(_s(a, a.run, "reviewer:report"))
    txt = to_html(rep) if a.format == "html" else to_markdown(rep)
    if a.output:
        Path(a.output).parent.mkdir(parents=True, exist_ok=True)
        Path(a.output).write_text(txt, encoding="utf-8")
        print(f"wrote {a.output}")
    else:
        print(txt)


def cmd_compare(a):
    from .analysis import compare_groups, segment_groups

    sa, sb = _s(a, a.a, "reviewer:cli"), _s(a, a.b, "reviewer:cli")
    if sa.m.levels() != sb.m.levels():
        print(f"note: different methods ({sa.m.name} vs {sb.m.name}); comparing selection and the code level only")
    levels = sa.m.levels() if sa.m.levels() == sb.m.levels() else [sa.m.code_type]
    ga = segment_groups(sa.G, sa.db, sa.m)
    gb = segment_groups(sb.G, sb.db, sb.m)
    if levels != sa.m.levels():
        gb = {levels[0]: gb[sb.m.code_type]}
    r = compare_groups(ga, gb, levels)
    if a.json:
        _out(r)
        return
    same = sa.run["intent"].get("research_question") == sb.run["intent"].get("research_question")
    print(f"{a.a} vs {a.b}: {'same' if same else 'DIFFERENT'} research question")
    sel = r["selection"]
    print(f"  selection  coded segments {sel['segments_a']} / {sel['segments_b']}, both {sel['both']}, Jaccard {sel['jaccard']}")
    for lvl, sc in r["levels"].items():
        print(f"  {lvl:<10} n={sc['n']:<4} Rand={sc['rand']} ARI={sc['ari']} NMI={sc['nmi']} pairF1={sc['pair_f1']}  "
              f"groups {sc['groups_a']}/{sc['groups_b']}")


def cmd_site(a):
    from .site import write

    out = write(_p(a), a.run, a.output or f"reports/{a.run}-site.html", a.keep_names)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


def cmd_query(a):
    _out(_s(a, a.run, "reviewer:cli").query(a.typeql))


def cmd_methods(a):
    from .method import builtin_methods

    print("\n".join(builtin_methods()))


def cmd_method(a):
    from .method import load_method

    m = load_method(a.name)
    print(m.guide)
    _out(m.summary())


def cmd_guide(a):
    from importlib import resources

    print(resources.files("qls.agents").joinpath("AGENTS.md").read_text(encoding="utf-8"))


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", help="project folder (default: search upwards or $QLS_PROJECT)")
    ap = argparse.ArgumentParser(prog="qls", description="A memory server for qualitative analysis: strict ontology, free agents.")
    ap.add_argument("--version", action="version", version=f"qls {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    def add(name, fn, parent=sub, **kw):
        sp = parent.add_parser(name, parents=[common], **kw)
        sp.set_defaults(fn=fn)
        return sp

    sp = add("init", cmd_init, help="create a project")
    sp.add_argument("dir", nargs="?", default=".")
    sp.add_argument("--name")
    add("doctor", cmd_doctor, help="check TypeDB and the MCP SDK")
    sp = add("ingest", cmd_ingest, help="add sources")
    sp.add_argument("files", nargs="+")
    sp.add_argument("--id")
    sp.add_argument("--participant")
    sp.add_argument("--interviewer", action="append", help="extra interviewer speaker label")
    add("sources", cmd_sources, help="list sources")

    run = sub.add_parser("run", help="create, fork, replay, drop runs").add_subparsers(dest="sub", required=True)
    sp = add("new", cmd_run_new, run)
    sp.add_argument("name")
    sp.add_argument("--intent", help="intent file (default: intent.yaml)")
    sp.add_argument("--question", help="research question (overrides the intent file)")
    sp.add_argument("--stance")
    sp.add_argument("--method", help="built-in method name or a method folder")
    sp.add_argument("--sources", nargs="+")
    sp.add_argument("--note")
    sp = add("fork", cmd_run_fork, run)
    sp.add_argument("run")
    sp.add_argument("--at", type=int)
    sp.add_argument("--at-stage")
    sp.add_argument("--as", dest="name", required=True)
    sp.add_argument("--note")
    sp = add("replay", cmd_run_replay, run)
    sp.add_argument("run")
    sp = add("drop", cmd_run_drop, run)
    sp.add_argument("run")
    sp.add_argument("--yes", action="store_true")

    add("runs", cmd_runs, help="list runs")
    for name, fn in (("status", cmd_status), ("check", cmd_check)):
        sp = add(name, fn)
        sp.add_argument("run")
        sp.add_argument("--actor")
    sp = add("log", cmd_log, help="event log")
    sp.add_argument("run")
    sp.add_argument("--since", type=int, default=0)
    sp = add("review", cmd_review, help="what to look at, at a checkpoint")
    sp.add_argument("run")
    sp = add("respond", cmd_respond, help="researcher decisions")
    sp.add_argument("run")
    sp.add_argument("--actor", help="human:NAME (default: human:$USER)")
    sp.add_argument("--approve", metavar="ID")
    sp.add_argument("--reject", metavar="ID")
    sp.add_argument("--revise", metavar="ID")
    sp.add_argument("--set", action="append", metavar="KEY=VALUE")
    sp.add_argument("--reason")
    sp.add_argument("--answer")
    sp = add("resume", cmd_resume, help="let agents continue")
    sp.add_argument("run")
    sp.add_argument("--actor")
    sp.add_argument("--note")

    sp = add("stage", cmd_stage, help="show or move the run's stage")
    sp.add_argument("run")
    sp.add_argument("stage", nargs="?")
    sp.add_argument("--actor")
    sp.add_argument("--reason")
    sp = add("agent", cmd_agent, help="run one isolated agent session")
    sp.add_argument("run")
    sp.add_argument("--task", required=True)
    sp.add_argument("--sources", nargs="*")
    sp.add_argument("--actor")
    sp.add_argument("--model", default="opus")
    sp.add_argument("--web", action="store_true", help="allow web search/fetch (off by default)")
    sp = add("pipeline", cmd_pipeline, help="run all stages with the AI-only policy")
    sp.add_argument("run")
    sp.add_argument("--auto", action="store_true")
    sp.add_argument("--seed", type=int, default=1)
    sp.add_argument("--calibration", type=int, help="k: interviews coded in the calibration session (methods with a calibration stage)")
    sp.add_argument("--batch", type=int, default=0, help="n: interviews per batch (0 = no batches, one review after all)")
    sp.add_argument("--until", help="stop when the run reaches this stage")
    sp.add_argument("--actor")
    sp.add_argument("--model", default="opus")
    sp = add("sessions", cmd_sessions, help="agent sessions of a run")
    sp.add_argument("run")
    sp = add("provenance", cmd_provenance, help="events with their metadata, and what agents read")
    sp.add_argument("run")
    sp.add_argument("--session")
    sp.add_argument("--tail", type=int, default=0)
    sp.add_argument("--json", action="store_true")
    sp = add("mcp", cmd_mcp, help="MCP server (stdio) bound to a run and a scholar")
    sp.add_argument("--run")
    sp.add_argument("--actor")
    sp.add_argument("--model")
    sp = add("mcp-config", cmd_mcp_config, help="print an .mcp.json entry")
    sp.add_argument("run")
    sp.add_argument("--actor", required=True)
    sp.add_argument("--model")
    sp = add("tool", cmd_tool, help="call a tool from the shell")
    sp.add_argument("run")
    sp.add_argument("name")
    sp.add_argument("args", nargs="?")
    sp.add_argument("--actor")
    sp = add("tools", cmd_tools, help="list the tools an actor has")
    sp.add_argument("run")
    sp.add_argument("--actor")

    sp = add("report", cmd_report, help="readable report of a run")
    sp.add_argument("run")
    sp.add_argument("--format", choices=["md", "html"], default="md")
    sp.add_argument("-o", "--output")
    sp = add("compare", cmd_compare, help="agreement between two runs")
    sp.add_argument("a")
    sp.add_argument("b")
    sp.add_argument("--json", action="store_true")
    sp = add("site", cmd_site, help="one-file website of a run: structure, steps, interviews, instructions, log")
    sp.add_argument("run")
    sp.add_argument("-o", "--output")
    sp.add_argument("--keep-names", action="store_true", help="do not black out interviewee names")
    sp = add("query", cmd_query, help="read-only TypeQL")
    sp.add_argument("run")
    sp.add_argument("typeql")
    add("methods", cmd_methods, help="built-in methods")
    sp = add("method", cmd_method, help="show a method")
    sp.add_argument("name")
    add("guide", cmd_guide, help="ways of working (AGENTS.md)")
    return ap


def main(argv: list[str] | None = None) -> None:
    a = build_parser().parse_args(argv)
    try:
        a.fn(a)
    except QlsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
