"""A self-contained website of one run: the whole analysis, how it was made, and with what instructions.

    qls site RUN -o reports/RUN.html

Everything the researcher can see goes in: the data structure (dimensions, themes, concepts, quotes
and every reason), each interview's objects and memos, the codebook, every agent session (its task
prompt, model, length and final report), checkpoints and decisions, the full event log, and the
instructions the agents worked from. The page needs no server: one HTML file with the data inline.
Full transcripts are left out; quotes carry their segment ids.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from importlib import resources
from pathlib import Path

from .project import Project
from .session import Session


def _rows(s: Session, q: str) -> list[dict]:
    return s._rows(q)


def _attr(s: Session, typ: str, attr: str) -> dict[str, str]:
    return {r["i"]: r["v"] for r in _rows(s, f"match $x isa {typ}, has id $i, has {attr} $v; select $i, $v;")}


def _num(oid: str) -> tuple:
    head, _, n = oid.rpartition("-")
    return (head, int(n)) if n.isdigit() else (oid, 0)


TYPE_NAMES = {   # display names; any other type is shown by its own name
    "concept": ("1st-order concept", "1st-order concepts"), "theme": ("2nd-order theme", "2nd-order themes"),
    "dimension": ("aggregate dimension", "aggregate dimensions"),
    "segment": ("coded segment", "coded segments"), "content-category": ("category", "categories"),
}


def collect(p: Project, run: str) -> dict:
    s = Session(p, run, "reviewer:site")
    r, m = s.run, s.m
    srcs = {sid: p.ledger.source(sid, v) for sid, v in r["config"]["sources"].items()}
    levels = m.levels()                       # bottom-up: the code type, then each group type
    code_t = levels[0]

    # -- every object of the method's types, with its fields
    objects: dict[str, dict] = {}
    for lv, typ in enumerate(levels):
        lab = _attr(s, typ, "label")
        common = {k: _attr(s, typ, a) for k, a in (("description", "description"), ("event", "event"), ("actor", "actor"))}
        fields = {f.param: _attr(s, typ, f.attr) for f in m.fields.get(typ, []) if f.param not in ("label", "description")}
        cbv = _attr(s, typ, "codebook-version") if typ == code_t else {}
        for i in lab:
            objects[i] = {"id": i, "type": typ, "level": lv, "label": lab[i], "description": common["description"].get(i, ""),
                          "event": common["event"].get(i), "actor": common["actor"].get(i),
                          "fields": {k: v[i] for k, v in fields.items() if i in v}, "codebook_version": cbv.get(i),
                          "members": [], "in": [], "quotes": [], "sources": []}

    # -- evidence for codes
    ev = _rows(s, f"match $c isa {code_t}, has id $i; $e isa evidence (claim: $c, quote: $q); $e has reason $r; "
                  "$q has id $qid, has start-offset $a, has end-offset $b, has unit $u; quoting (source: $s, quote: $q); "
                  "$s has id $sid; select $i, $r, $qid, $a, $b, $u, $sid;")
    for e in ev:
        src = srcs[e["sid"]]
        objects[e["i"]]["quotes"].append({"id": e["qid"], "source": e["sid"], "unit": e["u"], "start": int(e["a"]), "end": int(e["b"]),
                                          "text": src["text"][int(e["a"]):int(e["b"])], "reason": e["r"]})
    for o in objects.values():
        if o["type"] == code_t:
            o["quotes"].sort(key=lambda q: (q["source"], q["start"]))
            o["sources"] = sorted({q["source"] for q in o["quotes"]})

    # -- groupings, both directions, each with its reason
    for g in m.groups:
        for x in _rows(s, f"match $g isa {g.type}, has id $gid; $r isa {g.relation} ({g.group_role}: $g, {g.member_role}: $x); "
                          f"$r has reason $why; $x has id $mid; select $gid, $mid, $why;"):
            if x["gid"] in objects and x["mid"] in objects:
                objects[x["gid"]]["members"].append({"id": x["mid"], "reason": x["why"]})
                objects[x["mid"]]["in"].append({"id": x["gid"], "reason": x["why"]})
    for typ in levels[1:]:
        for a in _rows(s, f"match $d isa {typ}, has id $i; $r isa answering (answer: $d); $r has reason $w; select $i, $w;"):
            objects[a["i"]]["answers"] = a["w"]
    for o in objects.values():
        o["members"].sort(key=lambda x: _num(x["id"]))
        o["in"].sort(key=lambda x: _num(x["id"]))
    for o in objects.values():   # codes: which groups at every level above they end up in
        if o["type"] == code_t:
            seen, todo = [], [x["id"] for x in o["in"]]
            while todo:
                gid = todo.pop(0)
                if gid not in seen:
                    seen.append(gid)
                    todo += [x["id"] for x in objects[gid]["in"]]
            o["under"] = seen

    # -- memos
    memos = {}
    for m in _rows(s, "match $m isa memo, has id $i, has memo-kind $k, has memo-level $l, has body $b, has actor $a, has event $e; "
                      "select $i, $k, $l, $b, $a, $e;"):
        memos[m["i"]] = {"id": m["i"], "kind": m["k"], "level": m["l"], "body": m["b"], "actor": m["a"], "event": m["e"],
                         "about": [], "cites": []}
    for a in _rows(s, "match $m isa memo, has id $i; about (memo: $m, target: $t); $t has id $tid; select $i, $tid;"):
        memos[a["i"]]["about"].append(a["tid"])
    for c in _rows(s, "match $m isa memo, has id $i; citation (citing: $m, cited: $c); $c has id $cid; select $i, $cid;"):
        memos[c["i"]]["cites"].append(c["cid"])

    # -- codebook
    cb = {}
    lab = _attr(s, "codebook-entry", "label")
    for k, attr in (("definition", "description"), ("use_when", "inclusion"), ("not_when", "exclusion"),
                    ("status", "status"), ("version", "version"), ("actor", "actor"), ("event", "event")):
        vals = _attr(s, "codebook-entry", attr)
        for i in lab:
            cb.setdefault(i, {"id": i, "label": lab[i]})[k] = vals.get(i)
    for x in _rows(s, "match $e isa codebook-entry, has id $i; exemplar (entry: $e, quote: $q); $q has id $qid; select $i, $qid;"):
        cb[x["i"]].setdefault("examples", []).append(x["qid"])

    # -- sessions, with what the harness reported
    sessions = []
    for x in p.ledger.sessions(run):
        res, tools = {}, defaultdict(int)
        log = p.root / x["log"] if x["log"] else None
        if log and log.exists():
            for line in log.open(encoding="utf-8"):
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("type") == "result":
                    res = msg
                elif msg.get("type") == "assistant":
                    for part in (msg.get("message") or {}).get("content") or []:
                        if part.get("type") == "tool_use":
                            tools[part["name"].replace("mcp__qls__", "")] += 1
        cfg = json.loads(x["config"] or "{}")
        sessions.append({"id": x["id"], "task": x["task"], "stage": x["stage"], "started": x["started"], "ended": x["ended"],
                         "model": x["model"], "harness": f"{x['harness']} {cfg.get('harness_version', '')}".strip(),
                         "sources": cfg.get("sources", []), "prompt": x["prompt"], "prompt_sha": x["prompt_sha"],
                         "exit": x["exit"], "turns": res.get("num_turns"), "minutes": round((res.get("duration_ms") or 0) / 60000, 1),
                         "cost": round(res.get("total_cost_usd") or 0, 2), "report": res.get("result") or "",
                         "tools": dict(sorted(tools.items(), key=lambda kv: -kv[1]))})

    # -- events (the decision log)
    events = []
    for e in p.ledger.events(run):
        prm = e["params"]
        short = {k: v for k, v in prm.items() if k not in ("quotes", "examples", "concepts", "themes", "segments", "categories", "text", "summary", "intent")}
        events.append({"seq": e["seq"], "action": e["action"], "actor": e["actor"], "stage": e["meta"].get("stage"),
                       "session": e["meta"].get("session"), "reason": e["reason"], "ts": e["ts"], "ids": e["result"].get("ids", []),
                       "params": short, "summary": prm.get("summary"), "questions": prm.get("questions"),
                       "text": prm.get("text") if e["action"] in ("answer",) else None})

    # -- instructions
    m = s.m
    agents_md = resources.files("qls.agents").joinpath("AGENTS.md").read_text(encoding="utf-8")
    probes = {}
    for f in sorted((p.root / "probes").glob("*.json")) if (p.root / "probes").exists() else []:
        try:
            probes[f.stem] = json.loads(f.read_text())["result"]
        except Exception:
            pass

    return {
        "run": {"id": run, "parent": r["parent"], "fork_at": r["fork_at"], "created": r["created"], "status": r["status"],
                "method": r["method"], "method_hash": r["method_hash"], "stage": s.stage(), "note": r["config"].get("note")},
        "intent": r["intent"],
        "sources": [{"id": sid, "title": src["title"], "chars": len(src["text"]), "text": src["text"],
                     "turns": [{"start": u["start"], "end": u["end"], "role": u["role"], "speaker": u["speaker"]}
                               for u in src["units"] if u["kind"] == "turn"],
                     "segments": sum(1 for u in src["units"] if u["kind"] == "segment")} for sid, src in sorted(srcs.items())],
        "project": p.cfg("project", "name", p.root.name),
        "method": {"name": m.name, "title": m.title, "code_type": code_t,
                   "levels": [{"type": x, "name": TYPE_NAMES.get(x, (x, x + "s"))[0], "plural": TYPE_NAMES.get(x, (x, x + "s"))[1]}
                              for x in levels]},
        "objects": sorted(objects.values(), key=lambda o: (o["level"], _num(o["id"]))),
        "memos": sorted(memos.values(), key=lambda x: _num(x["id"])),
        "codebook": sorted(cb.values(), key=lambda x: _num(x["id"])),
        "sessions": sessions,
        "events": events,
        "docs": {"ways_of_working": agents_md, "method": m.guide, "guides": m.guides, "tasks": m.tasks,
                 "stages": m.stages, "checks": m.checks},
        "probes": probes,
    }


NAME_LINE = re.compile(r"^Haastattelun nimi:[ \t]*(.+)$", re.M)   # "interview name" in Finnish transcript headers


def names_in(p: Project, run: str) -> list[str]:
    """Interviewee names (and the organisation after them) from the transcript headers, as single words."""
    out = set()
    for sid, v in p.ledger.run(run)["config"]["sources"].items():
        for m in NAME_LINE.finditer(p.ledger.source(sid, v)["text"]):
            out |= {w for w in re.findall(r"[^\W\d_][\w.-]+", m.group(1)) if len(w) >= 3}
    return sorted(out, key=len, reverse=True)


def redact(data: dict, names: list[str]) -> dict:
    """Black out names everywhere. In transcripts the bars keep the length, so quote offsets still line up."""
    if not names:
        return data
    pat = re.compile(r"\b(" + "|".join(map(re.escape, names)) + r")\b", re.I)
    for s in data["sources"]:
        s["text"] = pat.sub(lambda m: "\u2588" * len(m.group(0)), s["text"])
    for c in data["objects"]:
        for q in c.get("quotes", []):
            q["text"] = pat.sub(lambda m: "\u2588" * len(m.group(0)), q["text"])

    def walk(x):
        if isinstance(x, str):
            return pat.sub("[name]", x)
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, dict):
            return {k: (v if k in ("text",) and isinstance(v, str) and "\u2588" in v else walk(v)) for k, v in x.items()}
        return x

    return walk(data)


def build(p: Project, run: str, keep_names: bool = False) -> str:
    data = collect(p, run)
    if not keep_names:
        data = redact(data, names_in(p, run))
    tpl = resources.files("qls").joinpath("site_template.html").read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return tpl.replace("__TITLE__", f"Gioia run {run}").replace("/*__DATA__*/null", blob)


def write(p: Project, run: str, out: str | Path, keep_names: bool = False) -> Path:
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(p, run, keep_names), encoding="utf-8")
    return out
