"""Reports a reader can check: intent, data structure, claim -> quote table, memos, codebook, decisions.

    qls report RUN [--format md|html] [-o FILE]

The data structure follows the method's levels (Gioia: concept -> theme -> dimension, left to
right). Every quote is printed from its source offsets, so the report shows exactly the words the
server verified.
"""

from __future__ import annotations

import html
from collections import Counter

from .session import Session, _num

DECISIONS = {"merge", "withdraw", "reject", "revise", "remove_from_group", "approve", "answer", "checkpoint", "resume"}


def build(session: Session) -> dict:
    s, m = session, session.m
    levels = m.levels()  # bottom-up
    top = levels[-1]
    ids = {lvl: [r["i"] for r in s._rows(f"match $x isa {lvl}, has id $i; select $i;")] for lvl in levels}
    nodes: dict[str, dict] = {}
    for lvl in levels:
        for i in sorted(ids[lvl], key=_num):
            p = s.pack(i, quotes_per_item=99)
            nodes[i] = p

    def tree(i: str) -> dict:
        p = nodes[i]
        out = {"id": i, "type": p["type"], "label": p.get("label"), "description": p.get("description"),
               "answers": p.get("answers") or []}
        if "members" in p:
            out["children"] = [{**tree(c["id"]), "reason": c.get("reason")} for c in p["members"]]
        else:
            out["quotes"] = p.get("quotes", [])
        return out

    roots = [tree(i) for i in sorted(ids[top], key=_num)]
    unplaced = {lvl: [tree(i) for i in sorted(ids[lvl], key=_num) if not nodes[i].get("in")] for lvl in levels[:-1]}
    events = s.L.events(s.run_id)
    run = s.run
    return {
        "run": s.run_id, "method": m.title, "intent": run["intent"], "status": run["status"], "parent": run["parent"],
        "fork_at": run["fork_at"], "levels": levels, "tree": roots, "unplaced": unplaced,
        "counts": s.status()["objects"], "events": len(events), "actors": dict(Counter(e["actor"] for e in events)),
        "state_hash": s.G.state_hash(s.db), "memos": s.memos()["memos"], "codebook": s.codebook()["entries"],
        "decisions": [e for e in events if e["action"] in DECISIONS], "open": s.check()["open"],
    }


def _c(x) -> str:
    return " ".join(str(x or "").split()).replace("|", "\\|")


def _leaves(n: dict):
    if "quotes" in n:
        yield n
    for c in n.get("children", []):
        yield from _leaves(c)


def _rows(n: dict, depth: int) -> list[list[str]]:
    me = f"{n['id']} {n['label']}"
    kids = n.get("children")
    if kids is None:
        return [[me] + [""] * (depth - 1)]
    rows = [r for c in kids for r in _rows(c, depth - 1)] or [[""] * (depth - 1)]
    return [[me if i == 0 else ""] + r for i, r in enumerate(rows)]


def what(e: dict) -> str:
    p = e["params"]
    a = e["action"]
    if a == "merge":
        return f"{', '.join(p['ids'])} → {p['into']}"
    if a in ("withdraw", "reject", "approve"):
        return p["id"]
    if a == "revise":
        return f"{p['id']}: {', '.join(p['fields'])}"
    if a == "remove_from_group":
        return f"{p['member']} out of {p['group']}"
    if a == "checkpoint":
        return p["summary"] + ("" if not p.get("questions") else " — " + " / ".join(p["questions"]))
    if a == "answer":
        return p["text"]
    return ""


def to_markdown(rep: dict) -> str:
    L = rep["levels"]
    it = rep["intent"]
    out = [f"# Run `{rep['run']}`", "",
           f"**Research question.** {it.get('research_question')}  ",
           f"**Method.** {rep['method']}. **Stance.** {it.get('stance') or '—'}", "",
           f"Status **{rep['status']}**, {rep['events']} events, state `{rep['state_hash'][:19]}…`"
           + (f", forked from `{rep['parent']}` at #{rep['fork_at']}" if rep["parent"] else "") + ".  ",
           "Objects: " + ", ".join(f"{k} {v}" for k, v in rep["counts"].items()) + ".  ",
           "Actors: " + ", ".join(f"`{k}` {v}" for k, v in rep["actors"].items()) + ".", "",
           "## Data structure", "", "| " + " | ".join(x.capitalize() for x in L) + " |", "|" + "---|" * len(L)]
    for top in rep["tree"]:
        out += ["| " + " | ".join(_c(c) for c in reversed(row)) + " |" for row in _rows(top, len(L))]
    for lvl, ns in rep["unplaced"].items():
        if ns:
            out += ["", f"Not yet placed ({lvl}): " + ", ".join(f"{n['id']} {n['label']}" for n in ns)]
    for top in rep["tree"]:
        for a in top.get("answers") or []:
            out.append(f"\n{top['id']} answers the question: {a}")
    out += ["", "## Claims and evidence", "", f"| {L[0].capitalize()} | Quote | Source | Why this quote | Words |", "|---|---|---|---|---|"]
    leaves = [x for t in rep["tree"] for x in _leaves(t)] + [x for ns in rep["unplaced"].values() for n in ns for x in _leaves(n)]
    for c in leaves:
        for q in c["quotes"]:
            out.append(f"| {c['id']} {_c(c['label'])} | {q['quote']} | {q['source']} | {_c(q['reason'])} | “{_c(q['text'])}” |")
    out += ["", "## Codebook", ""] + [f"- **{e['id']} {e['label']}** ({e['status']}{', v' + str(e['version']) if e.get('version') else ''}): "
                                      f"{_c(e['definition'])}" + (f" Use when: {_c(e['use_when'])}." if e.get("use_when") else "")
                                      + (f" Not when: {_c(e['not_when'])}." if e.get("not_when") else "") for e in rep["codebook"]]
    first = {"uncertainty": 0, "negative-case": 1}
    out += ["", "## Memos", ""] + [f"- **{x['id']}** ({x['kind']}, {x['level']}, {x['by']}) about {', '.join(x['about'])}: {_c(x['text'])}"
                                   for x in sorted(rep["memos"], key=lambda x: (first.get(x["kind"], 9), _num(x["id"])))]
    out += ["", "## Decisions", "", "| # | Actor | Action | What | Reason |", "|---|---|---|---|---|"]
    out += [f"| {e['seq']} | {e['actor']} | {e['action']} | {_c(what(e))} | {_c(e['reason'])} |" for e in rep["decisions"]]
    out += ["", f"## Still open ({len(rep['open'])})", ""] + [f"- {o['item']}: {o['text']}" for o in rep["open"][:60]]
    return "\n".join(out) + "\n"


CSS = """
:root{--bg:#fff;--fg:#1d1d1f;--mut:#6b6b70;--line:#d8d8dc;--c1:#eef4ff;--c2:#f3f0ff;--c3:#fff4e8}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--fg:#ececf0;--mut:#9a9aa2;--line:#33333a;--c1:#1b2433;--c2:#231d33;--c3:#33281b}}
body{background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,sans-serif;max-width:1200px;margin:0 auto;padding:16px}
h1,h2{font-weight:600}.mut{color:var(--mut)}table{border-collapse:collapse;width:100%}td,th{border-top:1px solid var(--line);padding:6px;vertical-align:top;text-align:left}
.ds{display:grid;gap:8px}.row{display:grid;grid-template-columns:2.4fr 1fr;gap:8px;border-top:1px solid var(--line);padding-top:8px}
.box{border-radius:8px;padding:8px}.l0{background:var(--c3)}.l1{background:var(--c2)}.l2{background:var(--c1)}
.sub{display:grid;gap:8px}.pair{display:grid;grid-template-columns:1.4fr 1fr;gap:8px}
details summary{cursor:pointer}blockquote{margin:4px 0 4px 8px;padding-left:8px;border-left:3px solid var(--line)}
@media (max-width:700px){.row,.pair{grid-template-columns:1fr}}
"""


def to_html(rep: dict) -> str:
    e = html.escape

    def box(n, cls):
        d = f"<div class=mut>{e(n.get('description') or '')}</div>" if n.get("description") else ""
        ans = "".join(f"<p><b>Answers the question:</b> {e(x)}</p>" for x in n.get("answers") or [])
        return f"<div class='box {cls}'><b>{e(n['id'])}</b> {e(n['label'] or '')}{d}{ans}</div>"

    def leaf(n):
        qs = "".join(f"<blockquote>“{e(q['text'] or '')}”<br><span class=mut>{e(q['quote'])} · {e(q['source'] or '')} · {e(q['reason'] or '')}</span></blockquote>"
                     for q in n["quotes"])
        return f"<details class='box l2'><summary><b>{e(n['id'])}</b> {e(n['label'] or '')}</summary>{qs}</details>"

    def mid(n):
        return f"<div class=pair><div class=sub>{''.join(leaf(c) for c in n.get('children', []))}</div>{box(n, 'l1')}</div>"

    rows = []
    if len(rep["levels"]) == 3:
        for d in rep["tree"]:
            rows.append(f"<div class=row><div class=sub>{''.join(mid(t) for t in d['children'])}</div>{box(d, 'l0')}</div>")
        for t in rep["unplaced"].get(rep["levels"][1], []):
            rows.append(f"<div class=row><div class=sub>{mid(t)}</div><div class='box mut'>(no {e(rep['levels'][2])} yet)</div></div>")
    it = rep["intent"]
    body = [f"<h1>Run {e(rep['run'])}</h1>",
            f"<p><b>Research question.</b> {e(it.get('research_question') or '')}<br><b>Method.</b> {e(rep['method'])}</p>",
            f"<p class=mut>Status <b>{e(rep['status'])}</b>, {rep['events']} events, state <code>{e(rep['state_hash'][:19])}…</code></p>"]
    if rows:
        body.append(f"<h2>Data structure</h2><p class=mut>{e(' · '.join(rep['levels']))}, left to right; open a {e(rep['levels'][0])} to see its quotes.</p><div class=ds>{''.join(rows)}</div>")
    unpl = rep["unplaced"].get(rep["levels"][0], [])
    if unpl:
        body.append(f"<p class=mut>Not yet in a {e(rep['levels'][1] if len(rep['levels']) > 1 else 'group')}: {e(', '.join(n['id'] + ' ' + (n['label'] or '') for n in unpl))}</p>")
    body.append("<h2>Codebook</h2><ul>" + "".join(f"<li><b>{e(c['id'])} {e(c['label'])}</b> <span class=mut>{e(c['status'])}</span><br>{e(c['definition'] or '')}</li>" for c in rep["codebook"]) + "</ul>")
    body.append("<h2>Memos</h2><ul>" + "".join(f"<li><b>{e(x['id'])}</b> <span class=mut>{e(x['kind'])} · {e(str(x['level']))} · {e(str(x['by']))} · {e(', '.join(x['about']))}</span><br>{e(x['text'])}</li>" for x in rep["memos"]) + "</ul>")
    body.append("<h2>Decisions</h2><table><tr><th>#</th><th>Actor</th><th>Action</th><th>What</th><th>Reason</th></tr>"
                + "".join(f"<tr><td>{d['seq']}</td><td>{e(d['actor'])}</td><td>{e(d['action'])}</td><td>{e(what(d))}</td><td>{e(d['reason'] or '')}</td></tr>" for d in rep["decisions"]) + "</table>")
    body.append(f"<h2>Still open ({len(rep['open'])})</h2><ul>" + "".join(f"<li>{e(o['item'])}: {e(o['text'])}</li>" for o in rep["open"][:60]) + "</ul>")
    return (f"<!doctype html><html lang=en><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Run {e(rep['run'])}</title><style>{CSS}</style></head><body>{''.join(body)}</body></html>")
