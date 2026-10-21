"""The tools: what an agent (or a researcher) can do to a run.

A Session is bound to one run and one actor. Every write:

1. is validated here, with a message the agent can act on;
2. becomes TypeQL, run in one TypeDB transaction, where the ontology checks it again;
3. is appended to the event log with its queries, so the run can be replayed or forked.

Refusals are returned, not raised: {"ok": false, "error": ..., "hint": ...}.
Method tools (add_concept, add_theme, ...) come from the method's actions.yaml via `act()`.
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from importlib import resources

from .grounding import locate
from .graph import GraphError, lit
from .method import CORE_PREFIXES, Method
from .project import Project
from .util import QlsError

MEMO_KINDS = ["meaning", "informant", "surprise", "uncertainty", "residual", "method", "negative-case", "summary", "reflexive"]
MEMO_LEVELS = ["note", "interview", "batch", "corpus"]
QUOTE_THRESHOLD = 95  # below this, a quote is refused; at or above, the source's own words are stored

READ_TOOLS = ["intent", "method_guide", "guide", "ways_of_working", "list_sources", "read_source", "search", "get", "pack",
              "codebook", "memos", "query", "status", "check", "feedback", "history"]
WRITE_TOOLS = ["begin", "add_evidence", "add_to_group", "remove_from_group", "revise", "merge", "withdraw", "memo",
               "propose_codebook", "checkpoint"]
HUMAN_TOOLS = ["approve", "reject", "answer", "resume", "set_stage"]


def is_human(actor: str) -> bool:
    """A researcher: a person (human:NAME), or a fixed policy standing in for one (auto:NAME, e.g. in AI-only runs)."""
    return actor == "human" or actor.startswith(("human:", "auto:"))


def ok(**kw) -> dict:
    return {"ok": True, **kw}


def refuse(error: str, hint: str | None = None, **kw) -> dict:
    out = {"ok": False, "error": error}
    if hint:
        out["hint"] = hint
    out.update(kw)
    return out


class Refusal(Exception):
    def __init__(self, error: str, hint: str | None = None, **kw):
        super().__init__(error)
        self.payload = refuse(error, hint, **kw)


class _Ctx:
    def __init__(self, s: "Session", seq: int):
        self.s, self.seq, self.ids = s, seq, []

    def new_id(self, prefix: str) -> str:
        oid = self.s.L.new_id(self.s.run_id, prefix)
        self.ids.append(oid)
        return oid

    @property
    def stamp(self) -> str:
        return f", has actor {lit(self.s.actor)}, has event {self.seq}"


class Session:
    def __init__(self, project: Project, run: str, actor: str, model: str | None = None):
        if not actor or ":" not in actor and actor != "human":
            raise QlsError("actor must be agent:NAME, human:NAME or reviewer:NAME")
        self.p, self.L, self.G = project, project.ledger, project.graph
        self.run_id, self.actor, self.model = run, actor, model
        self.m: Method = project.method_of(self.L.run(run))
        # provenance, set by whoever launched this session (qls agent); never shown to the agent
        self.session_id = os.environ.get("QLS_SESSION")
        self.meta = {k: v for k, v in {"session": self.session_id, "harness": os.environ.get("QLS_HARNESS"),
                                       "task": os.environ.get("QLS_TASK")}.items() if v}

    # ------------------------------------------------------------------ plumbing

    @property
    def run(self) -> dict:
        return self.L.run(self.run_id)

    @property
    def db(self) -> str:
        return self.run["db"]

    def _rows(self, q: str) -> list[dict]:
        return self.G.rows(self.db, q)

    def _type(self, oid: str) -> str | None:
        rows = self._rows(f"match $x has id {lit(oid)}; $x isa! $t; select $t;")
        return rows[0]["t"] if rows else None

    def _need(self, oid: str, types: list[str] | None = None, what: str = "object") -> str:
        t = self._type(oid)
        if t is None:
            gone = self._fate(oid)
            raise Refusal(f"{oid} does not exist" + (f": {gone}" if gone else "."), "Use search() or query() to find ids.")
        if types and t not in types:
            raise Refusal(f"{oid} is a {t}; expected {' or '.join(types)}.")
        return t

    def _fate(self, oid: str) -> str | None:
        for e in reversed(self.L.events(self.run_id)):
            p = e["params"]
            if e["action"] == "merge" and oid in p.get("ids", []):
                return f"merged into {p['into']} at #{e['seq']} ({e['reason']})"
            if e["action"] in ("withdraw", "reject") and p.get("id") == oid:
                verb = {"withdraw": "withdrawn", "reject": "rejected"}[e["action"]]
                return f"{verb} at #{e['seq']} by {e['actor']} ({e['reason']})"
            if e["action"] == "approve" and oid in e["result"].get("replaced", []):
                return f"replaced by {p['id']} at #{e['seq']}"
        return None

    def _gate(self) -> dict | None:
        r = self.run
        if r["status"] == "waiting" and not is_human(self.actor):
            return refuse(f"Run {self.run_id} is waiting at checkpoint #{r['checkpoint_seq']} for the researcher.",
                          "Stop here. Writes resume when the researcher resumes the run; then read feedback().")
        if self.actor.startswith("reviewer"):
            return refuse("Reviewers have read-only access.")
        return None

    # ------------------------------------------------------------------ stages

    def stage(self) -> str | None:
        """The run's current stage: the last stage event, or the method's first stage."""
        if not self.m.stages:
            return None
        for e in reversed(self.L.events(self.run_id)):
            if e["action"] == "stage":
                return e["params"]["stage"]
        return self.m.stages[0]["id"]

    def _stage_allows_create(self, action: str) -> None:
        st = self.m.stage(self.stage())
        if st is None or is_human(self.actor) or action not in self.m.actions or action in st["create"]:
            return
        raise Refusal(f"{action} is not part of stage {st['id']} ({st.get('title', '')}).",
                      f"This stage creates: {', '.join(st['create']) or 'nothing'}. The researcher moves the run to the next "
                      "stage; if you need to, say so in a memo or a checkpoint question.")

    def _may_edit(self, t: str) -> None:
        st = self.m.stage(self.stage())
        if st is None or is_human(self.actor) or t in ("memo", "codebook-entry") or t in st["edit"]:
            return
        raise Refusal(f"Stage {st['id']} does not change {t}s.",
                      f"This stage changes: {', '.join(st['edit']) or 'nothing'}. Write a memo about it instead, or ask in a checkpoint.")

    def _write(self, action: str, params: dict, build, reason: str = "") -> dict:
        """Validate and build under the ledger lock; run in one TypeDB transaction; log the event."""
        if (g := self._gate()):
            return g
        try:
            self._stage_allows_create(action)
            with self.L.lock():
                ctx = _Ctx(self, self.L.next_seq(self.run_id))
                queries, result = build(ctx)
                self.G.write(self.db, queries)
                result = {**result, "ids": ctx.ids}
                self.L.append(self.run_id, ctx.seq, action, self.actor, params, result, queries, reason, self.model,
                              {**self.meta, "stage": self.stage()})
        except Refusal as r:
            return r.payload
        except GraphError as e:
            return refuse(str(e), "Nothing was saved. Adjust the call and try again.")
        out = {k: v for k, v in result.items() if k != "ids"}
        return ok(event=ctx.seq, **out)

    def _source(self, sid: str) -> dict:
        pinned = self.run["config"]["sources"]
        if sid not in pinned:
            raise Refusal(f"No source {sid!r} in this run.", f"Sources: {', '.join(pinned)}")
        return self.L.source(sid, pinned[sid])

    @staticmethod
    def _segments(src: dict) -> list[dict]:
        return [u for u in src["units"] if u["kind"] == "segment"]

    def _quote_info(self, qid: str) -> dict:
        r = self._rows(f"match $q isa quote, has id {lit(qid)}, has start-offset $a, has end-offset $b, has unit $u; "
                       f"quoting (source: $s, quote: $q); $s has id $sid; select $a, $b, $u, $sid;")
        if not r:
            return {"id": qid}
        r = r[0]
        src = self._source(r["sid"])
        unit = next((u for u in src["units"] if u["id"] == r["u"]), {})
        return {"id": qid, "source": r["sid"], "unit": r["u"], "start": r["a"], "end": r["b"],
                "text": src["text"][r["a"]:r["b"]], "question": unit.get("question")}

    # ------------------------------------------------------------------ quotes

    def _quote(self, ctx: _Ctx, spec: dict, default_source: str | None, queries: list, made: dict) -> dict:
        """Verify one quote spec; reuse an existing quote at the same place or add insert queries."""
        if spec.get("quote"):
            self._need(spec["quote"], ["quote"])
            return self._quote_info(spec["quote"])
        sid = (spec.get("source") or default_source or "").split(":")[0]
        if not sid:
            raise Refusal("Which source is this quote from?", 'Give "source" in each quote, or call begin(source) first.')
        src = self._source(sid)
        segs = self._segments(src)
        if spec.get("start") is not None and spec.get("end") is not None:
            a, b = int(spec["start"]), int(spec["end"])
            unit = next((u for u in segs if u["start"] <= a < b <= u["end"]), None)
            if unit is None:
                raise Refusal(f"Offsets {a}-{b} are not inside one informant answer in {sid}.",
                              "Quotes come from one informant answer; read_source() shows the segments.")
            match = "offsets"
        else:
            text = (spec.get("text") or "").strip()
            if not text:
                raise Refusal("A quote needs the informant's words (text) or start/end offsets.")
            best = None
            for u in segs:
                sp = locate(text, src["text"][u["start"]:u["end"]], QUOTE_THRESHOLD)
                if sp and (best is None or sp.score > best[1].score):
                    best = (u, sp)
                    if sp.score >= 100:
                        break
            if best is None:
                said_by_interviewer = any(locate(text, src["text"][u["start"]:u["end"]], QUOTE_THRESHOLD)
                                          for u in src["units"] if u["kind"] == "turn" and u["role"] != "informant")
                short = text if len(text) <= 90 else text[:87] + "..."
                if said_by_interviewer:
                    raise Refusal(f'"{short}" is the interviewer\'s, not the informant\'s. Nothing was saved.',
                                  "Only informants are quotable; quote their answer instead.")
                raise Refusal(f'Quote not found in {sid}: "{short}". Nothing was saved.',
                              f"Copy the informant's exact words from the interview (read_source(\"{sid}\") shows it again). "
                              "Do not paraphrase or join sentences from different answers.")
            unit, sp = best
            a, b = unit["start"] + sp.start, unit["start"] + sp.end
            match = sp.method
        key = (sid, a, b)
        if key in made:
            return made[key]
        rows = self._rows(f"match $s isa source, has id {lit(sid)}; $q isa quote, has start-offset {a}, has end-offset {b}; "
                          f"quoting (source: $s, quote: $q); $q has id $i; select $i;")
        if rows:
            info = {"id": rows[0]["i"], "existing": True}
        else:
            qid = ctx.new_id("Q")
            queries.append(f"match $s isa source, has id {lit(sid)}; insert $q isa quote, has id {lit(qid)}, "
                           f"has start-offset {a}, has end-offset {b}, has unit {lit(unit['id'])}; quoting (source: $s, quote: $q);")
            info = {"id": qid}
        info.update(source=sid, unit=unit["id"], text=src["text"][a:b], match=match)
        made[key] = info
        return info

    def _quotes(self, ctx: _Ctx, specs: list[dict], default_source: str | None, need_reason: bool = True) -> tuple[list, list]:
        if not specs:
            raise Refusal("At least one quote is needed: the evidence for this.",
                          'quotes=[{"text": "<the informant\'s exact words>", "reason": "<why they show it>"}]')
        queries, made, out = [], {}, []
        for i, spec in enumerate(specs, 1):
            if not isinstance(spec, dict):
                raise Refusal(f"quote {i} must be an object with text and reason.")
            if need_reason and not str(spec.get("reason") or "").strip():
                raise Refusal(f"quote {i} has no reason.", "Say in one line why these words show it.")
            info = self._quote(ctx, spec, default_source, queries, made)
            out.append({**info, "reason": spec.get("reason", "")})
        return queries, out

    def _current_source(self) -> str | None:
        for e in reversed(self.L.events(self.run_id)):
            if e["actor"] == self.actor and e["action"] == "begin":
                return e["params"]["source"]
        return None

    # ------------------------------------------------------------------ read: orientation

    def intent(self) -> dict:
        """The study's intent: research question, method, stance. Findings should answer this question."""
        r = self.run
        return {"run": self.run_id, **r["intent"], "method_title": self.m.title}

    def method_guide(self) -> dict:
        """How to do the analysis (the method's guide), and the objects and actions it defines."""
        return {"guide": self.m.guide, "structure": self.m.summary()}

    def guide(self, name: str) -> dict:
        """A short how-to for one task (e.g. "concept", "interview-memo"). method_guide() lists them."""
        if name not in self.m.guides:
            return refuse(f"No guide {name!r}.", f"Guides: {', '.join(sorted(self.m.guides)) or 'none'}")
        return ok(name=name, text=self.m.guides[name])

    def ways_of_working(self) -> str:
        """How to quote, give reasons, keep memos and work in a team with this server."""
        return resources.files("qls.agents").joinpath("AGENTS.md").read_text(encoding="utf-8")

    def list_sources(self) -> list[dict]:
        """Sources in this run: segments, who has read each, and how many codes cite it."""
        readers: dict[str, list] = {}
        for r in self._rows("match assignment (scholar: $p, source: $s); $s has id $sid; $p has id $pid; select $sid, $pid;"):
            readers.setdefault(r["sid"], []).append(r["pid"])
        codes: dict[str, set] = {}
        for r in self._rows("match $c isa code, has id $cid; evidence (claim: $c, quote: $q); quoting (source: $s, quote: $q); "
                            "$s has id $sid; select $sid, $cid;"):
            codes.setdefault(r["sid"], set()).add(r["cid"])
        out = []
        for sid, v in self.run["config"]["sources"].items():
            s = self.L.source(sid, v)
            out.append({"id": sid, "title": s["title"], "segments": len(self._segments(s)), "chars": len(s["text"]),
                        "read_by": sorted(readers.get(sid, [])), "codes": len(codes.get(sid, ()))})
        return out

    def read_source(self, source: str, from_segment: int | None = None, to_segment: int | None = None) -> str:
        """The transcript, with informant answers marked [segment id]. Optionally a range of segment numbers."""
        try:
            src = self._source(source.split(":")[0])
        except Refusal as r:
            return r.payload["error"]
        ranged = from_segment is not None or to_segment is not None
        by_turn: dict[str, list] = {}
        for u in self._segments(src):
            by_turn.setdefault(u["turn"], []).append(u)
        lines, pending = [], []
        for t in (u for u in src["units"] if u["kind"] == "turn"):
            if t["id"] not in by_turn:
                line = f"{t['speaker']}: {src['text'][t['start']:t['end']]}" if t["role"] != "meta" else src["text"][t["start"]:t["end"]]
                if ranged:
                    pending = [line] if t["role"] == "interviewer" else pending
                else:
                    lines.append(line)
                continue
            for u in by_turn[t["id"]]:
                n = int(u["id"].rsplit("s", 1)[1])
                if ranged and ((from_segment and n < from_segment) or (to_segment and n > to_segment)):
                    continue
                lines += pending
                pending = []
                lines.append(f"[{u['id']}] {u['speaker']}: {src['text'][u['start']:u['end']]}")
        return f"# {src['id']}: {src['title']}\n\n" + "\n\n".join(lines)

    def begin(self, source: str) -> dict:
        """Start work on one interview: returns the intent, the codebook, the interview and your notes on it.
        Records that you read it."""
        try:
            src = self._source(source.split(":")[0])
        except Refusal as r:
            return r.payload
        sid = src["id"]
        if not self._gate():
            have = self._rows(f"match $p isa scholar, has id {lit(self.actor)}; $s isa source, has id {lit(sid)}; "
                              f"assignment (scholar: $p, source: $s); select $p;")
            if not have:
                def build(ctx):
                    q = []
                    if not self._rows(f"match $p isa scholar, has id {lit(self.actor)}; select $p;"):
                        q.append(f"insert $p isa scholar, has id {lit(self.actor)};")
                    q.append(f"match $p isa scholar, has id {lit(self.actor)}; $s isa source, has id {lit(sid)}; "
                             f"insert $a isa assignment (scholar: $p, source: $s), has event {ctx.seq};")
                    return q, {}
                self._write("begin", {"source": sid}, build, f"{self.actor} reads {sid}")
        here = sorted({(r["cid"], r["l"], r.get("a")) for r in self._rows(
            f"match $s isa source, has id {lit(sid)}; quoting (source: $s, quote: $q); evidence (claim: $c, quote: $q); "
            f"$c has id $cid, has label $l; try {{ $c has actor $a; }}; select $cid, $l, $a;")}, key=lambda x: _num(x[0]))
        return ok(source=sid, title=src["title"], intent=self.run["intent"].get("research_question"),
                  codebook=self.codebook(include_proposals=False)["entries"],
                  your_memos=self.memos(about=sid, actor=self.actor)["memos"],
                  coded_here=[{"id": c, "label": l, "by": a} for c, l, a in here],
                  transcript=self.read_source(sid),
                  next="Read the whole interview, then add concepts with exact quotes, then write the interview memo.")

    # ------------------------------------------------------------------ read: look up

    def search(self, text: str, limit: int = 20) -> dict:
        """Find informant answers containing all the words, and objects whose label or description matches."""
        words = [w.lower() for w in re.findall(r"\w+", text)]
        if not words:
            return ok(segments=[], objects=[])
        segs = []
        for sid, v in self.run["config"]["sources"].items():
            src = self.L.source(sid, v)
            for u in self._segments(src):
                body = src["text"][u["start"]:u["end"]]
                low = body.lower()
                if all(w in low for w in words):
                    i = low.find(words[0])
                    segs.append({"unit": u["id"], "snippet": ("…" if i > 80 else "") + body[max(0, i - 80):i + 220] + "…"})
        objs = []
        for r in self._rows("match $x has id $i, has label $l; $x isa! $t; try { $x has description $d; }; select $i, $t, $l, $d;"):
            hay = f"{r['l']} {r.get('d') or ''}".lower()
            if all(w in hay for w in words):
                objs.append({"id": r["i"], "type": r["t"], "label": r["l"]})
        return ok(segments=segs[:limit], objects=sorted(objs, key=lambda o: _num(o["id"]))[:limit],
                  more=max(0, len(segs) - limit))

    def get(self, id: str) -> dict:
        """One object: its attributes and every relation it takes part in (with reasons). Quotes include their text."""
        t = self._type(id)
        if t is None:
            fate = self._fate(id)
            return refuse(f"{id} does not exist" + (f": {fate}" if fate else "."))
        attrs = self._rows(f"match $x has id {lit(id)}; fetch {{ \"a\": {{ $x.* }} }};")
        out = {"id": id, "type": t, **(attrs[0]["a"] if attrs else {})}
        if t == "quote":
            out.update(self._quote_info(id))
        links = []
        for r in self._rows(f"match $x has id {lit(id)}; $r links ($role: $x), links ($orole: $o); not {{ $o is $x; }}; "
                            f"$o has id $oid; $r isa! $rt; try {{ $r has reason $why; }}; select $rt, $role, $orole, $oid, $why;"):
            links.append({"relation": r["rt"], "as": r["role"].split(":")[1], "with": r["oid"],
                          "with_as": r["orole"].split(":")[1], "reason": r.get("why")})
        out["links"] = sorted(links, key=lambda x: (x["relation"], _num(x["with"])))
        return ok(**out)

    def pack(self, id: str, quotes_per_item: int = 3) -> dict:
        """Context pack: everything that supports an object, compact. For a code: its quotes and memos;
        for a group: its members with a few quotes each; for a source: its codes and memos."""
        t = self._type(id)
        if t is None:
            return refuse(f"{id} does not exist.")
        if t == "source":
            codes = sorted({(r["cid"], r["l"]) for r in self._rows(
                f"match $s isa source, has id {lit(id)}; quoting (source: $s, quote: $q); evidence (claim: $c, quote: $q); "
                f"$c has id $cid, has label $l; select $cid, $l;")}, key=lambda x: _num(x[0]))
            return ok(id=id, type=t, codes=[{"id": c, "label": l} for c, l in codes], memos=self.memos(about=id)["memos"])
        base = self.get(id)
        item = {"id": id, "type": t, "label": base.get("label"), "description": base.get("description")}
        if t == self.m.code_type:
            item["quotes"] = self._code_quotes(id)
        g = self.m.group_of(t)
        if g:
            item["members"] = []
            for l in base["links"]:
                if l["relation"] == g.relation and l["as"] == g.group_role:
                    sub = self.pack(l["with"], quotes_per_item)
                    sub.pop("ok", None)
                    sub["reason"] = l["reason"]
                    if "quotes" in sub:
                        sub["quotes"] = sub["quotes"][:quotes_per_item]
                    if "members" in sub:
                        for mm in sub["members"]:
                            mm.pop("memos", None)
                    item["members"].append(sub)
        up = self.m.group_for_member(t)
        if up:
            item["in"] = [l["with"] for l in base["links"] if l["relation"] == up.relation and l["as"] == up.member_role]
        item["answers"] = [l["reason"] for l in base["links"] if l["relation"] == "answering"]
        item["memos"] = self.memos(about=id)["memos"]
        return ok(**item)

    def _code_quotes(self, cid: str) -> list[dict]:
        out = []
        for r in self._rows(f"match $c isa {self.m.code_type}, has id {lit(cid)}; $e isa evidence (claim: $c, quote: $q); $q has id $qid; "
                            f"$e has reason $why; select $qid, $why;"):
            info = self._quote_info(r["qid"])
            out.append({"quote": r["qid"], "source": info.get("source"), "text": info.get("text"), "reason": r["why"],
                        "question": info.get("question")})
        return sorted(out, key=lambda x: _num(x["quote"]))

    def codebook(self, include_proposals: bool = True) -> dict:
        """The codebook: shared long-term memory of what codes mean. Approved entries, and pending proposals."""
        rows = self._rows("match $e isa codebook-entry, has id $i, has label $l, has status $st; try { $e has description $d; }; "
                          "try { $e has inclusion $inc; }; try { $e has exclusion $exc; }; try { $e has version $v; }; "
                          "try { $e has actor $a; }; select $i, $l, $st, $d, $inc, $exc, $v, $a;")
        entries = [{"id": r["i"], "label": r["l"], "definition": r.get("d"), "use_when": r.get("inc"),
                    "not_when": r.get("exc"), "status": r["st"], "version": r.get("v"), "by": r.get("a")}
                   for r in rows if include_proposals or r["st"] == "active"]
        return ok(version=self.L.counter(self.run_id, "CBV"), entries=sorted(entries, key=lambda e: _num(e["id"])))

    def memos(self, about: str | None = None, kind: str | None = None, level: str | None = None,
              actor: str | None = None) -> dict:
        """Memos, optionally filtered by what they are about, kind, level or author."""
        q = "match $m isa memo, has id $i, has memo-kind $k, has body $b; try { $m has memo-level $lv; }; try { $m has actor $a; };"
        if about:
            at = self._type(about)
            if at is None:
                return ok(memos=[])
            q += f" $t isa {at}, has id {lit(about)}; about (memo: $m, target: $t);"
        rows = self._rows(q + " select $i, $k, $b, $lv, $a;")
        targets: dict[str, list] = {}
        for r in self._rows("match about (memo: $m, target: $t); $m has id $mi; $t has id $ti; select $mi, $ti;"):
            targets.setdefault(r["mi"], []).append(r["ti"])
        out = []
        for r in rows:
            if (kind and r["k"] != kind) or (level and r.get("lv") != level) or (actor and r.get("a") != actor):
                continue
            out.append({"id": r["i"], "kind": r["k"], "level": r.get("lv"), "about": sorted(targets.get(r["i"], [])),
                        "text": r["b"], "by": r.get("a")})
        return ok(memos=sorted(out, key=lambda m: _num(m["id"])))

    def query(self, typeql: str, limit: int = 200) -> dict:
        """Read-only TypeQL against this run's graph, for your own questions. Example:
        match $c isa concept, has id $i; not { theme-membership (concept: $c); }; select $i;"""
        try:
            rows = self.G.rows(self.db, typeql)
        except GraphError as e:
            return refuse(f"Query failed: {e}", "Read-only TypeQL 3 (match ... select/fetch). method_guide() lists the types.")
        return ok(rows=rows[:limit], total=len(rows))

    def status(self) -> dict:
        """Where the run stands: status, counts per type, codebook version, open checks."""
        r = self.run
        counts = Counter(x["t"] for x in self._rows("match $x isa! $t, has id $i; select $t, $i;"))
        st = self.m.stage(self.stage())
        stage = {"id": st["id"], "title": st.get("title", ""), "creates": st["create"], "changes": st["edit"]} if st else None
        return ok(run=self.run_id, status=r["status"], checkpoint=r["checkpoint_seq"], method=r["method"], stage=stage,
                  objects=dict(sorted(counts.items())),
                  codebook_version=self.L.counter(self.run_id, "CBV"), events=self.L.next_seq(self.run_id) - 1,
                  open_checks=len(self.check()["open"]))

    def check(self) -> dict:
        """The method's soft expectations that are not met yet (what is still open)."""
        out = []
        for c in self.m.checks:
            for i in self.G.column(self.db, c["query"], "i"):
                out.append({"check": c["id"], "item": i, "text": c["text"]})
        return ok(open=out)

    def feedback(self) -> dict:
        """The researcher's responses since the last checkpoint: answers, approvals, rejections, edits."""
        r = self.run
        since = 0
        for e in self.L.events(self.run_id):
            if e["action"] == "checkpoint":
                since = e["seq"] - 1
        evs = [e for e in self.L.events(self.run_id, since=since) if is_human(e["actor"])]
        return ok(items=[{"event": e["seq"], "action": e["action"], "by": e["actor"], "params": e["params"],
                          "reason": e["reason"]} for e in evs], run_status=r["status"])

    def history(self, id: str) -> dict:
        """Every event that touched an object, with reasons."""
        out = []
        for e in self.L.events(self.run_id):
            blob = str(e["params"]) + " " + " ".join(e["result"].get("ids", []))
            if re.search(rf"(?<![\w-]){re.escape(id)}(?![\w])", blob):
                by = "researcher" if is_human(e["actor"]) else e["actor"]
                out.append({"event": e["seq"], "action": e["action"], "by": by, "reason": e["reason"]})
        return ok(id=id, events=out)

    # ------------------------------------------------------------------ write: method actions

    def act(self, action: str, **kw) -> dict:
        """Run a method action from actions.yaml (add_concept, add_theme, ...)."""
        a = self.m.actions.get(action)
        if a is None:
            return refuse(f"Unknown action {action!r}.", f"Actions: {', '.join(self.m.actions)}")
        fields = self.m.fields.get(a.type, [])
        known = {f.param for f in fields} | {"quotes", "source", "answers"} | ({a.members_param} if a.members_param else set()) \
            | ({a.into_param} if a.into_param else set())
        extra = set(kw) - known
        if extra:
            return refuse(f"{action} has no parameter {', '.join(sorted(extra))}.", f"Parameters: {', '.join(sorted(known))}")
        missing = [f.param for f in fields if f.required and not str(kw.get(f.param) or "").strip()]
        if missing:
            return refuse(f"{action} needs {', '.join(missing)}.")
        attrs = "".join(f", has {f.attr} {lit(kw[f.param])}" for f in fields if str(kw.get(f.param) or "").strip())
        if a.kind == "create_code":
            return self._create_code(a, kw, attrs)
        return self._create_group(a, kw, attrs)

    def _create_code(self, a, kw: dict, attrs: str) -> dict:
        default_source = kw.get("source") or self._current_source()

        def build(ctx):
            queries, quotes = self._quotes(ctx, kw.get("quotes") or [], default_source)
            cid = ctx.new_id(self.m.prefix(a.type))
            cbv = self.L.counter(self.run_id, "CBV")
            queries.append(f"insert $c isa {a.type}, has id {lit(cid)}{attrs}{ctx.stamp}, has codebook-version {cbv};")
            seen = set()
            for q in quotes:
                if q["id"] in seen:
                    continue
                seen.add(q["id"])
                queries.append(f"match $c isa {a.type}, has id {lit(cid)}; $q isa quote, has id {lit(q['id'])}; "
                               f"insert $e isa evidence (claim: $c, quote: $q), has reason {lit(q['reason'])}{ctx.stamp};")
            placed = []
            if a.into:   # placed in its groups in the same transaction, each with a reason
                g = next(x for x in self.m.groups if x.type == a.into and x.member_type == a.type)
                items = kw.get(a.into_param) or []
                if not isinstance(items, list) or len(items) < a.into_min:
                    raise Refusal(f"Say which {a.into}(s) this {a.type} belongs to: {a.into_param}=[{{\"id\", \"reason\"}}].")
                if g.exclusive and len(items) > 1:
                    raise Refusal(f"A {a.type} can be in one {a.into} only.")
                for it in items:
                    gid = str((it or {}).get("id") or "")
                    if not str((it or {}).get("reason") or "").strip():
                        raise Refusal(f"{gid or 'an item'} has no reason.", f"Say in one line why this {a.type} belongs there.")
                    self._need(gid, [a.into])
                    queries.append(f"match $g isa {a.into}, has id {lit(gid)}; $m isa {a.type}, has id {lit(cid)}; "
                                   f"insert $r isa {g.relation} ({g.group_role}: $g, {g.member_role}: $m), has reason {lit(it['reason'])}{ctx.stamp};")
                    placed.append(gid)
            out = {"id": cid, "quotes": [{k: q[k] for k in ("id", "source", "unit", "text", "match")} for q in quotes]}
            if a.into:
                out[a.into_param] = placed
            return queries, out

        return self._write(a.name, kw, build, kw.get("label", ""))

    def _members(self, g, items, group_id: str | None = None) -> list[dict]:
        if not isinstance(items, list):
            raise Refusal(f"Give the {g.member_type}s as a list of {{\"id\", \"reason\"}}.")
        out, seen = [], set()
        for i, it in enumerate(items, 1):
            it = {"id": it} if isinstance(it, str) else it
            mid = str(it.get("id") or "")
            if not str(it.get("reason") or "").strip():
                raise Refusal(f"{mid or f'item {i}'} has no reason.", f"Say in one line why it belongs in this {g.type}.")
            self._need(mid, [g.member_type])
            if mid in seen:
                raise Refusal(f"{mid} is listed twice.")
            seen.add(mid)
            if g.exclusive:
                cur = self.G.column(self.db, f"match $m isa {g.member_type}, has id {lit(mid)}; {g.relation} ({g.member_role}: $m, {g.group_role}: $g); "
                                             f"$g has id $gid; select $gid;", "gid")
                cur = [c for c in cur if c != group_id]
                if cur:
                    raise Refusal(f"{mid} is already in {cur[0]}; a {g.member_type} can be in one {g.type} only.",
                                  f"remove_from_group({cur[0]!r}, {mid!r}, reason) first, or merge the {g.type}s.")
            out.append({"id": mid, "reason": it["reason"]})
        return out

    def _create_group(self, a, kw: dict, attrs: str) -> dict:
        g = self.m.group_of(a.type)
        answers = str(kw.get("answers") or "").strip()

        def build(ctx):
            members = self._members(g, kw.get(a.members_param) or [])
            if len(members) < g.min:
                raise Refusal(f"A {a.type} groups at least {g.min} {g.member_type}(s); got {len(members)}.")
            if a.answers == "required" and not answers:
                raise Refusal(f"Say how this {a.type} answers the research question (answers=...).",
                              f"Research question: {self.run['intent'].get('research_question')}")
            gid = ctx.new_id(self.m.prefix(a.type))
            q = [f"insert $g isa {a.type}, has id {lit(gid)}{attrs}{ctx.stamp};"]
            for m in members:
                q.append(f"match $g isa {a.type}, has id {lit(gid)}; $m isa {g.member_type}, has id {lit(m['id'])}; "
                         f"insert $r isa {g.relation} ({g.group_role}: $g, {g.member_role}: $m), has reason {lit(m['reason'])}{ctx.stamp};")
            if answers:
                q.append(f"match $g isa {a.type}, has id {lit(gid)}; $i isa intent; "
                         f"insert $r isa answering (answer: $g, question: $i), has reason {lit(answers)}{ctx.stamp};")
            return q, {"id": gid, "members": [m["id"] for m in members]}

        return self._write(a.name, kw, build, kw.get("label", ""))

    # ------------------------------------------------------------------ write: core actions

    def add_evidence(self, code: str, quotes: list[dict]) -> dict:
        """Add more quotes to an existing code: [{"text": exact words, "reason": why, "source": optional}]."""
        default_source = self._current_source()

        def build(ctx):
            t = self._need(code, [self.m.code_type])
            self._may_edit(t)
            have = {x["quote"] for x in self._code_quotes(code)}
            queries, qs = self._quotes(ctx, quotes, default_source)
            for q in qs:
                if q["id"] not in have:
                    have.add(q["id"])
                    queries.append(f"match $c isa {t}, has id {lit(code)}; $q isa quote, has id {lit(q['id'])}; "
                                   f"insert $e isa evidence (claim: $c, quote: $q), has reason {lit(q['reason'])}{ctx.stamp};")
            return queries, {"id": code, "quotes": [{k: q[k] for k in ("id", "source", "unit", "text", "match")} for q in qs]}

        return self._write("add_evidence", {"code": code, "quotes": quotes}, build)

    def add_to_group(self, group: str, member: str, reason: str) -> dict:
        """Put a member into a group (a concept into a theme, a theme into a dimension), with a reason."""

        def build(ctx):
            t = self._need(group)
            self._may_edit(t)
            g = self.m.group_of(t)
            if g is None:
                raise Refusal(f"{group} is a {t}, which does not group anything.")
            [m] = self._members(g, [{"id": member, "reason": reason}], group)
            if group in self.G.column(self.db, f"match $m isa {g.member_type}, has id {lit(member)}; {g.relation} ({g.member_role}: $m, {g.group_role}: $g); "
                                                f"$g has id $gid; select $gid;", "gid"):
                raise Refusal(f"{member} is already in {group}.")
            return [f"match $g isa {t}, has id {lit(group)}; $m isa {g.member_type}, has id {lit(member)}; "
                    f"insert $r isa {g.relation} ({g.group_role}: $g, {g.member_role}: $m), has reason {lit(reason)}{ctx.stamp};"], {}

        return self._write("add_to_group", {"group": group, "member": member}, build, reason)

    def remove_from_group(self, group: str, member: str, reason: str) -> dict:
        """Take a member out of a group, with a reason."""

        def build(ctx):
            if not reason.strip():
                raise Refusal("Say why it leaves the group (reason).")
            t = self._need(group)
            self._may_edit(t)
            g = self.m.group_of(t)
            if g is None:
                raise Refusal(f"{group} is a {t}, which does not group anything.")
            members = self.G.column(self.db, f"match $g isa {t}, has id {lit(group)}; {g.relation} ({g.group_role}: $g, {g.member_role}: $m); "
                                             f"$m has id $mid; select $mid;", "mid")
            if member not in members:
                raise Refusal(f"{member} is not in {group}.")
            if len(members) - 1 < g.min:
                raise Refusal(f"{group} would have {len(members) - 1} {g.member_type}(s); a {t} needs at least {g.min}.",
                              f"Merge {group} into another {t}, or withdraw it, instead.")
            return [f"match $g isa {t}, has id {lit(group)}; $m isa {g.member_type}, has id {lit(member)}; $r isa {g.relation} ({g.group_role}: $g, {g.member_role}: $m); "
                    f"delete $r;"], {}

        return self._write("remove_from_group", {"group": group, "member": member}, build, reason)

    def _editable(self, t: str) -> dict[str, str]:
        if t == "memo":
            return {"text": "body", "kind": "memo-kind"}
        if t == "codebook-entry":
            return {"label": "label", "definition": "description", "use_when": "inclusion", "not_when": "exclusion"}
        return {f.param: f.attr for f in self.m.fields.get(t, [])}

    def revise(self, id: str, fields: dict, reason: str) -> dict:
        """Change fields of an object (label, description, ...; memo text), with a reason. History is kept."""

        def build(ctx):
            if not reason.strip():
                raise Refusal("Say why (reason).")
            t = self._need(id)
            self._may_edit(t)
            allowed = self._editable(t)
            if not allowed:
                raise Refusal(f"A {t} cannot be revised.")
            bad = set(fields) - set(allowed)
            if bad or not fields:
                raise Refusal(f"A {t} has fields {', '.join(allowed)}; got {', '.join(sorted(bad)) or 'none'}.")
            if t == "codebook-entry" and not is_human(self.actor):
                st = self.G.column(self.db, f"match $e has id {lit(id)}, has status $s; select $s;", "s")
                if st and st[0] == "active":
                    raise Refusal("Approved codebook entries change only through the researcher.",
                                  "propose_codebook(..., replaces=id) proposes a new version.")
            if t == "memo" and "text" in fields and len(fields["text"]) > self._memo_budget(id):
                raise Refusal(f"Memo text is over the budget ({self._memo_budget(id)} characters).")
            sets = ", ".join(f"has {allowed[k]} {lit(v)}" for k, v in fields.items())
            return [f"match $x isa {t}, has id {lit(id)}; update $x {sets}, has event {ctx.seq};"], {"id": id}

        return self._write("revise", {"id": id, "fields": fields}, build, reason)

    def _memo_budget(self, mid: str) -> int:
        lv = self.G.column(self.db, f"match $m has id {lit(mid)}, has memo-level $l; select $l;", "l")
        return self.m.memo_budget(lv[0] if lv else "note")

    def _removal(self, oid: str, t: str, into: str | None, ctx: _Ctx) -> list[str]:
        """Queries that remove an object from the current graph. Memos about it follow `into` (or the intent)."""
        q = []
        target = into or "intent"
        tt = t if into else "intent"
        for r in self._rows(f"match $x isa {t}, has id {lit(oid)}; about (memo: $m, target: $x); $m has id $mid; select $mid;"):
            mid = r["mid"]
            already = self._rows(f"match $m isa memo, has id {lit(mid)}; $t isa {tt}, has id {lit(target)}; about (memo: $m, target: $t); select $m;")
            if not already:
                q.append(f"match $m isa memo, has id {lit(mid)}; $t isa {tt}, has id {lit(target)}; insert about (memo: $m, target: $t);")
        q.append(f"match $x isa {t}, has id {lit(oid)}; $r links ($x); delete $r;")
        q.append(f"match $x isa {t}, has id {lit(oid)}; delete $x;")
        return q

    def merge(self, ids: list[str], into: str, reason: str) -> dict:
        """Merge objects into one of the same type: its quotes, members, groups and memos move to `into`."""

        def build(ctx):
            if not reason.strip():
                raise Refusal("Say why these are the same (reason).")
            t = self._need(into)
            self._may_edit(t)
            if t not in [self.m.code_type] + [g.type for g in self.m.groups]:
                raise Refusal(f"{t}s cannot be merged.")
            olds = [i for i in dict.fromkeys(ids) if i != into]
            if not olds:
                raise Refusal("Name at least one id to merge into the other.")
            for o in olds:
                self._need(o, [t])
            q: list[str] = []
            up, down = self.m.group_for_member(t), self.m.group_of(t)
            into_group = None
            if up:
                cur = self.G.column(self.db, f"match $m isa {t}, has id {lit(into)}; {up.relation} ({up.member_role}: $m, {up.group_role}: $g); $g has id $gid; select $gid;", "gid")
                into_group = cur[0] if cur else None
            have_quotes = {x["quote"] for x in self._code_quotes(into)} if t == self.m.code_type else set()
            for o in olds:
                if t == self.m.code_type:
                    for x in self._code_quotes(o):
                        if x["quote"] not in have_quotes:
                            have_quotes.add(x["quote"])
                            q.append(f"match $c isa {t}, has id {lit(into)}; $q isa quote, has id {lit(x['quote'])}; "
                                     f"insert $e isa evidence (claim: $c, quote: $q), has reason {lit(x['reason'])}{ctx.stamp};")
                if up:
                    for r in self._rows(f"match $m isa {t}, has id {lit(o)}; $r isa {up.relation} ({up.member_role}: $m, {up.group_role}: $g); "
                                        f"$g has id $gid; $r has reason $why; select $gid, $why;"):
                        if into_group and into_group != r["gid"]:
                            raise Refusal(f"{o} is in {r['gid']} but {into} is in {into_group}.",
                                          "Move them into the same group first, or merge the groups.")
                        if into_group is None:
                            into_group = r["gid"]
                            q.append(f"match $g isa {up.type}, has id {lit(r['gid'])}; $m isa {t}, has id {lit(into)}; "
                                     f"insert $r isa {up.relation} ({up.group_role}: $g, {up.member_role}: $m), has reason {lit(r['why'])}{ctx.stamp};")
                if down:
                    for r in self._rows(f"match $g isa {t}, has id {lit(o)}; $r isa {down.relation} ({down.group_role}: $g, {down.member_role}: $m); "
                                        f"$m has id $mid; $r has reason $why; select $mid, $why;"):
                        q.append(f"match $g isa {t}, has id {lit(into)}; $m isa {down.member_type}, has id {lit(r['mid'])}; "
                                 f"insert $r isa {down.relation} ({down.group_role}: $g, {down.member_role}: $m), has reason {lit(r['why'])}{ctx.stamp};")
                answering = [] if t == self.m.code_type else self._rows(
                    f"match $g isa {t}, has id {lit(o)}; $r isa answering (answer: $g); $r has reason $why; select $why;")
                for r in answering:
                    q.append(f"match $g isa {t}, has id {lit(into)}; $i isa intent; insert $r isa answering (answer: $g, question: $i), "
                             f"has reason {lit(r['why'])}{ctx.stamp};")
                q += self._removal(o, t, into, ctx)
            return q, {"into": into, "merged": olds}

        return self._write("merge", {"ids": ids, "into": into}, build, reason)

    def withdraw(self, id: str, reason: str) -> dict:
        """Withdraw a code or group from the analysis, with a reason (it stays in the history).
        Its memos move to the intent; members of a withdrawn group become unplaced."""

        def build(ctx):
            if not reason.strip():
                raise Refusal("Say why (reason).")
            t = self._need(id)
            self._may_edit(t)
            allowed = [self.m.code_type] + [g.type for g in self.m.groups]
            if t == "codebook-entry":
                st = self.G.column(self.db, f"match $e has id {lit(id)}, has status $s; select $s;", "s")
                if st and st[0] == "active":
                    raise Refusal("Approved codebook entries are withdrawn by the researcher.")
            elif t not in allowed:
                raise Refusal(f"A {t} cannot be withdrawn" + (" (memos are revised, not removed)." if t == "memo" else "."))
            self._guard_groups(id, t)
            return self._removal(id, t, None, ctx), {"id": id}

        return self._write("withdraw", {"id": id}, build, reason)

    def _guard_groups(self, oid: str, t: str) -> None:
        up = self.m.group_for_member(t)
        if not up:
            return
        for gid in self.G.column(self.db, f"match $m isa {t}, has id {lit(oid)}; {up.relation} ({up.member_role}: $m, {up.group_role}: $g); $g has id $gid; select $gid;", "gid"):
            n = len(self.G.column(self.db, f"match $g isa {up.type}, has id {lit(gid)}; {up.relation} ({up.group_role}: $g, {up.member_role}: $m); select $m;", "m"))
            if n - 1 < up.min:
                raise Refusal(f"{gid} would be left with {n - 1} {up.member_type}(s); a {up.type} needs at least {up.min}.",
                              f"Merge {oid} into another {t}, or change {gid} first.")

    def memo(self, about: list[str], kind: str, text: str, level: str = "note", cites: list[str] | None = None) -> dict:
        """Write a memo about one or more objects or sources. kind: meaning, informant, surprise, uncertainty,
        residual (what does not fit the codebook), method, negative-case, summary, reflexive. level: note | interview (about a source; one per scholar,
        later calls update it) | batch (cites interview memos) | corpus (cites batch memos)."""
        about = [about] if isinstance(about, str) else list(about or [])
        cites = [cites] if isinstance(cites, str) else list(cites or [])

        def build(ctx):
            if kind not in MEMO_KINDS:
                raise Refusal(f"Memo kind {kind!r} is not one of {', '.join(MEMO_KINDS)}.")
            if level not in MEMO_LEVELS:
                raise Refusal(f"Memo level {level!r} is not one of {', '.join(MEMO_LEVELS)}.")
            if not about:
                raise Refusal("A memo is about something: give ids (concepts, themes, sources, memos, the intent).")
            if not text.strip():
                raise Refusal("The memo is empty.")
            if len(text) > self.m.memo_budget(level):
                raise Refusal(f"Too long for a {level} memo ({len(text)} > {self.m.memo_budget(level)} characters).",
                              "Keep memos short; split them, or summarise at a higher level.")
            types = {a: self._need(a) for a in about}
            bad = [a for a, t in types.items() if t in ("quote", "scholar")]
            if bad:
                raise Refusal(f"Memos are not about {', '.join(bad)} directly.", "Write the memo about the code or source instead.")
            ctypes = {c: self._need(c, ["memo"]) for c in cites}
            if level == "interview":
                srcs = [a for a, t in types.items() if t == "source"]
                if not srcs:
                    raise Refusal("An interview memo is about a source.")
                existing = self.G.column(self.db, f"match $s isa source, has id {lit(srcs[0])}; $m isa memo, has memo-level \"interview\", "
                                                  f"has actor {lit(self.actor)}, has id $i; about (memo: $m, target: $s); select $i;", "i")
                if existing:
                    return [f"match $m isa memo, has id {lit(existing[0])}; update $m has body {lit(text)}, has memo-kind {lit(kind)}, "
                            f"has event {ctx.seq};"], {"id": existing[0], "updated": True}
            need = {"batch": "interview", "corpus": "batch"}.get(level)
            if need:
                lv = {c: (self.G.column(self.db, f"match $m has id {lit(c)}, has memo-level $l; select $l;", "l") or [None])[0] for c in ctypes}
                if not any(v == need for v in lv.values()):
                    raise Refusal(f"A {level} memo cites at least one {need} memo (cites=[...]).")
            mid = ctx.new_id("M")
            q = [f"insert $m isa memo, has id {lit(mid)}, has memo-kind {lit(kind)}, has memo-level {lit(level)}, has body {lit(text)}{ctx.stamp};"]
            for a in about:
                q.append(f"match $m isa memo, has id {lit(mid)}; $t isa {types[a]}, has id {lit(a)}; insert about (memo: $m, target: $t);")
            for c in cites:
                q.append(f"match $m isa memo, has id {lit(mid)}; $c isa memo, has id {lit(c)}; insert citation (citing: $m, cited: $c);")
            # memo, about and citations commit together: TypeDB checks @card(1..) on about at commit
            return q, {"id": mid}

        return self._write("memo", {"about": about, "kind": kind, "level": level, "cites": cites, "text": text}, build)

    def propose_codebook(self, label: str, definition: str, use_when: str = "", not_when: str = "",
                         examples: list[dict] | None = None, replaces: str | None = None) -> dict:
        """Propose a codebook entry (the shared long-term memory): label, definition, when to use it, when not,
        and example quotes [{"text", "reason", "source"}]. replaces: an entry this one would replace.
        The researcher approves; a researcher's own entries are approved at once."""
        human = is_human(self.actor)
        default_source = self._current_source()

        def build(ctx):
            if not label.strip() or not definition.strip():
                raise Refusal("A codebook entry needs a label and a definition.")
            if replaces:
                self._need(replaces, ["codebook-entry"])
            queries, qs = self._quotes(ctx, examples, default_source) if examples else ([], [])
            eid = ctx.new_id("CB")
            extra = "".join(f", has {a} {lit(v)}" for a, v in (("inclusion", use_when), ("exclusion", not_when)) if v.strip())
            result = {"id": eid, "status": "active" if human else "proposed"}
            if human:
                v = self.L.counter(self.run_id, "CBV") + 1
                self.L.set_counter(self.run_id, "CBV", v)
                extra += f", has version {v}"
                result["codebook_version"] = v
            queries.append(f"insert $e isa codebook-entry, has id {lit(eid)}, has label {lit(label)}, has description {lit(definition)}"
                           f"{extra}, has status {lit(result['status'])}{ctx.stamp};")
            for q in qs:
                queries.append(f"match $e isa codebook-entry, has id {lit(eid)}; $q isa quote, has id {lit(q['id'])}; "
                               f"insert exemplar (entry: $e, quote: $q), has reason {lit(q['reason'])};")
            if human and replaces:
                queries += self._removal(replaces, "codebook-entry", eid, ctx)
                result["replaced"] = [replaces]
            return queries, result

        params = {"label": label, "definition": definition, "use_when": use_when, "not_when": not_when,
                  "examples": examples or [], "replaces": replaces}
        return self._write("propose_codebook", params, build)

    def checkpoint(self, summary: str, questions: list[str] | None = None) -> dict:
        """Stop for the researcher: summarise what you did and ask what you need to know. Writes are blocked
        until the researcher resumes the run."""
        out = self._write("checkpoint", {"summary": summary, "questions": questions or []}, lambda ctx: ([], {}), summary)
        if out.get("ok"):
            self.L.set_status(self.run_id, "waiting", out["event"])
            out["next"] = "Stop now. When the run is resumed, read feedback() first."
        return out

    # ------------------------------------------------------------------ researcher only

    def _human(self) -> None:
        if not is_human(self.actor):
            raise QlsError("Only a researcher (human:NAME) can do this.")

    def approve(self, id: str, edits: dict | None = None, note: str = "") -> dict:
        """Approve a codebook proposal (optionally with edits): it becomes the next codebook version."""
        self._human()

        def build(ctx):
            self._need(id, ["codebook-entry"])
            st = self.G.column(self.db, f"match $e has id {lit(id)}, has status $s; select $s;", "s")
            if st and st[0] == "active":
                raise Refusal(f"{id} is already approved.")
            v = self.L.counter(self.run_id, "CBV") + 1
            self.L.set_counter(self.run_id, "CBV", v)
            allowed = self._editable("codebook-entry")
            bad = set(edits or {}) - set(allowed)
            if bad:
                raise Refusal(f"Codebook fields: {', '.join(allowed)}; got {', '.join(sorted(bad))}.")
            sets = "".join(f", has {allowed[k]} {lit(val)}" for k, val in (edits or {}).items())
            q = [f'match $e isa codebook-entry, has id {lit(id)}; update $e has status "active", has version {v}{sets}, has event {ctx.seq};']
            result = {"id": id, "codebook_version": v}
            prop = next((e for e in self.L.events(self.run_id) if e["action"] == "propose_codebook" and id in e["result"].get("ids", [])), None)
            old = (prop or {}).get("params", {}).get("replaces")
            if old and self._type(old):
                q += self._removal(old, "codebook-entry", id, ctx)
                result["replaced"] = [old]
            return q, result

        return self._write("approve", {"id": id, "edits": edits or {}}, build, note or "approved")

    def reject(self, id: str, reason: str) -> dict:
        """Remove any code, group, memo or codebook proposal from the analysis, with a reason."""
        self._human()

        def build(ctx):
            t = self._need(id)
            if t in ("source", "intent", "quote", "scholar"):
                raise Refusal(f"A {t} cannot be rejected.")
            self._guard_groups(id, t)
            return self._removal(id, t, None, ctx), {"id": id}

        return self._write("reject", {"id": id}, build, reason)

    def answer(self, text: str) -> dict:
        """Answer the agents' questions or give direction; they read it with feedback()."""
        self._human()
        return self._write("answer", {"text": text}, lambda ctx: ([], {}), text)

    def resume(self, note: str = "") -> dict:
        """Let the agents continue after a checkpoint."""
        self._human()
        out = self._write("resume", {"note": note}, lambda ctx: ([], {}), note or "resumed")
        if out.get("ok"):
            self.L.set_status(self.run_id, "open")
        return out

    def set_stage(self, stage: str, reason: str = "") -> dict:
        """Move the run to a stage ("next" for the following one). Also resumes a run waiting at a checkpoint."""
        self._human()
        ids = [s["id"] for s in self.m.stages]
        if not ids:
            return refuse(f"Method {self.m.name} has no stages.")
        cur = self.stage()
        if stage == "next":
            i = ids.index(cur) + 1
            if i >= len(ids):
                return refuse(f"{cur} is the last stage.")
            stage = ids[i]
        if stage not in ids:
            return refuse(f"No stage {stage!r}.", f"Stages: {', '.join(ids)}")
        out = self._write("stage", {"stage": stage, "from": cur}, lambda ctx: ([], {"stage": stage}), reason or f"{cur} -> {stage}")
        if out.get("ok"):
            self.L.set_status(self.run_id, "open")
        return out

    # ------------------------------------------------------------------ dispatch

    def log_read(self, name: str, args: dict, result) -> None:
        """Record what an agent looked at (provenance: what it knew when it wrote). Writes are events already."""
        if name in READ_TOOLS and not is_human(self.actor):
            try:
                size = len(json.dumps(result, ensure_ascii=False, default=str))
                self.L.log_read(self.run_id, self.actor, self.session_id, name, args, size)
            except Exception:
                pass

    def tools(self) -> list[str]:
        names = READ_TOOLS + ["begin"]
        if not self.actor.startswith("reviewer"):
            names = READ_TOOLS + WRITE_TOOLS + list(self.m.actions)
        if is_human(self.actor):
            names += HUMAN_TOOLS
        return names

    def call(self, name: str, args: dict | None = None):
        args = args or {}
        if name not in self.tools():
            return refuse(f"Unknown tool {name!r} for {self.actor}.", f"Tools: {', '.join(self.tools())}")
        try:
            if name in self.m.actions:
                return self.act(name, **args)
            out = getattr(self, name)(**args)
            self.log_read(name, args, out)
            return out
        except TypeError as exc:
            return refuse(f"Bad arguments for {name}: {exc}")
        except Refusal as r:
            return r.payload


def _num(oid: str) -> tuple:
    m = re.match(r"(.*?)-(\d+)$", oid or "")
    return (m.group(1), int(m.group(2))) if m else (oid or "", 0)


__all__ = ["Session", "is_human", "READ_TOOLS", "WRITE_TOOLS", "HUMAN_TOOLS", "CORE_PREFIXES"]
