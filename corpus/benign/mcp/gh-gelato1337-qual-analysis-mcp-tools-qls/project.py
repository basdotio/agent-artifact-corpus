"""Project folder, ingestion, and run lifecycle (create, fork, replay).

    qls.toml        settings (TypeDB connection, transcript parsing)
    intent.yaml     research question, method, stance: frozen into each run at creation
    qls.db          the ledger: sources, runs, event log (SQLite)
    sources/        original files
    corpus/text/    extracted text per source (Docling output is cached here)

Each run is one TypeDB database named <prefix>_<run>.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tomllib
from pathlib import Path

import yaml

from .graph import Graph, lit
from .ingest import build_document, read_text, safe_id
from .ledger import Ledger
from .method import Method, core_schema, load_method
from .util import QlsError, now, sha256_bytes

CONFIG = "qls.toml"

DEFAULT_CONFIG = """\
[project]
name = "{name}"

[typedb]
# address = "127.0.0.1:1729"     # or $QLS_TYPEDB
# user = "admin"                 # or $QLS_TYPEDB_USER
# password = "password"          # or $QLS_TYPEDB_PASSWORD
database_prefix = "{prefix}"

[transcripts]
interviewer_labels = ["I", "Q", "H", "Interviewer", "Haastattelija", "Moderator"]
max_segment_chars = 2000
"""

INTENT = """\
# The intent of the study: the only content fixed in advance. Frozen into each run.
# Findings are expected to depend on it: a different question should give a different structure.
research_question: >
  What is the question the analysis should answer?
method: gioia
stance: >
  Who is asking, from which perspective or discipline, and what do they already assume?
prior_research: >
  What the researchers already know: the literature and debates the study builds on (optional).
sensitizing_concepts: >
  Concepts or theory that orient attention without fixing what will be found (optional).
study_context: >
  Setting, informants, sampling, how the interviews were done.
"""


class Project:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        if not (self.root / CONFIG).exists():
            raise QlsError(f"No {CONFIG} in {self.root}. Run `qls init`.")
        self.config = tomllib.loads((self.root / CONFIG).read_text(encoding="utf-8"))
        self._ledger: Ledger | None = None
        self._graph: Graph | None = None

    @classmethod
    def init(cls, root: str | Path, name: str | None = None) -> "Project":
        root = Path(root).resolve()
        root.mkdir(parents=True, exist_ok=True)
        name = name or root.name
        if not (root / CONFIG).exists():
            prefix = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:30] or "qls"
            (root / CONFIG).write_text(DEFAULT_CONFIG.format(name=name, prefix=f"qls_{prefix}"), encoding="utf-8")
        if not (root / "intent.yaml").exists():
            (root / "intent.yaml").write_text(INTENT, encoding="utf-8")
        for d in ("sources", "corpus/text", "reports"):
            (root / d).mkdir(parents=True, exist_ok=True)
        return cls(root)

    @classmethod
    def find(cls, start: str | Path | None = None) -> "Project":
        start = start or os.environ.get("QLS_PROJECT") or os.getcwd()
        p = Path(start).resolve()
        for cand in [p, *p.parents]:
            if (cand / CONFIG).exists():
                return cls(cand)
        raise QlsError(f"No {CONFIG} found in {p} or its parents. Run `qls init <folder>`.")

    def cfg(self, section: str, key: str, default=None):
        return self.config.get(section, {}).get(key, default)

    @property
    def ledger(self) -> Ledger:
        if self._ledger is None:
            self._ledger = Ledger(self.root / "qls.db")
        return self._ledger

    @property
    def graph(self) -> Graph:
        if self._graph is None:
            self._graph = Graph(self.cfg("typedb", "address"), self.cfg("typedb", "user"), self.cfg("typedb", "password"),
                                self.cfg("typedb", "tls"))
        return self._graph

    def db_name(self, run: str) -> str:
        return f"{self.cfg('typedb', 'database_prefix', 'qls')}_{run}"

    def method_of(self, run: dict) -> Method:
        m = load_method(run["config"].get("method_path") or run["method"])
        if m.hash != run["method_hash"]:
            raise QlsError(f"Method {m.name!r} changed since run {run['id']} was created ({run['method_hash'][:19]} -> {m.hash[:19]}). "
                           "Fork into a new run, or restore the method files.")
        return m

    # -- ingestion --------------------------------------------------------------

    def ingest(self, path: str | Path, source_id: str | None = None, participant: str | None = None,
               interviewer: list[str] | None = None, title: str | None = None) -> dict:
        path = Path(path)
        if not path.exists():
            raise QlsError(f"File not found: {path}")
        sid = safe_id(source_id or path.stem)
        raw = path.read_bytes()
        cache, meta_f = self.root / "corpus" / "text" / f"{sid}.md", self.root / "corpus" / "text" / f"{sid}.json"
        if cache.exists() and meta_f.exists() and json.loads(meta_f.read_text())["source_sha256"] == sha256_bytes(raw):
            text, parser = cache.read_text(encoding="utf-8"), json.loads(meta_f.read_text())["parser"]
        else:
            text, parser = read_text(path)
            cache.write_text(text, encoding="utf-8")
            meta_f.write_text(json.dumps({"source_sha256": sha256_bytes(raw), "parser": parser}))
        labels = list(self.cfg("transcripts", "interviewer_labels", [])) + list(interviewer or [])
        doc = build_document(sid, text, labels, int(self.cfg("transcripts", "max_segment_chars", 2000)))
        if not doc["segments"]:
            raise QlsError(f"{path.name}: no informant text found; check speaker labels (--interviewer).")
        canonical, units = canonical_text(doc)
        dest = self.root / "sources" / path.name
        if dest.resolve() != path.resolve():
            shutil.copy2(path, dest)
        meta = {"participant": participant or sid, "file": f"sources/{path.name}", "file_sha256": sha256_bytes(raw),
                "parser": parser, "speakers": doc["speakers"]}
        version = self.ledger.add_source(sid, canonical, units, title or path.stem, meta)
        return {"id": sid, "version": version, "turns": len(doc["turns"]), "segments": len(doc["segments"]),
                "speakers": doc["speakers"], "parser": parser}

    # -- runs -------------------------------------------------------------------

    def read_intent(self, path: str | Path | None = None, **overrides) -> dict:
        p = Path(path) if path else self.root / "intent.yaml"
        intent = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
        norm = lambda d: {k: (" ".join(str(v).split()) if isinstance(v, str) else v) for k, v in (d or {}).items()}
        template = norm(yaml.safe_load(INTENT))
        # unedited placeholder text from the template is not part of the intent
        intent = {k: v for k, v in norm(intent).items() if v and (k == "method" or v != template.get(k))}
        intent.update({k: v for k, v in overrides.items() if v})
        if not intent.get("research_question"):
            raise QlsError(f"Write the research question in {p} (or pass --question) before creating a run.")
        return intent

    def new_run(self, run: str, method: str | None = None, intent: dict | None = None, sources: list[str] | None = None,
                config: dict | None = None) -> dict:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,40}", run):
            raise QlsError("Run names: letters, digits, - and _, up to 40 characters.")
        intent = intent or self.read_intent()
        m = load_method(method or intent.get("method") or "gioia")
        intent["method"] = m.name
        config = dict(config or {})
        if method and Path(method).is_dir():
            config["method_path"] = str(Path(method).resolve())
        pinned = {s["id"]: s["version"] for s in self.ledger.sources() if not sources or s["id"] in sources}
        if not pinned:
            raise QlsError("No sources. `qls ingest` the interviews first.")
        config["sources"] = pinned
        db = self.db_name(run)
        self.graph.create(db, [core_schema(), m.schema])
        try:
            with self.ledger.lock():
                self.ledger.create_run(run, m.name, m.hash, intent, config, db)
                queries = setup_queries(intent, {sid: self.ledger.source(sid, v) for sid, v in pinned.items()})
                self.graph.write(db, queries)
                self.ledger.append(run, 1, "setup", "system", {"intent": intent, "sources": pinned}, {"ids": []}, queries,
                                   "run created")
        except Exception:
            self.graph.drop(db)
            raise
        return {"run": run, "db": db, "method": m.name, "method_hash": m.hash, "sources": len(pinned)}

    def stage_start(self, run: str, stage: str) -> int:
        """The event that moved the run into `stage` (the last time it did)."""
        hits = [e["seq"] for e in self.ledger.events(run) if e["action"] == "stage" and e["params"]["stage"] == stage]
        if not hits:
            raise QlsError(f"Run {run} never entered stage {stage!r}.")
        return hits[-1]

    def fork(self, run: str, new: str, at: int | None = None, note: str = "", at_stage: str | None = None) -> dict:
        r = self.ledger.run(run)
        if at_stage:
            at = self.stage_start(run, at_stage)
        at = at if at is not None else self.ledger.next_seq(run) - 1
        db = self.db_name(new)
        m = self.method_of(r)
        self.graph.create(db, [core_schema(), m.schema])
        try:
            with self.ledger.lock():
                self.ledger.create_run(new, r["method"], r["method_hash"], r["intent"], {**r["config"], "note": note}, db,
                                       parent=run, fork_at=at)
                n = self.ledger.copy_events(run, new, at)
            self.replay_into(new, db)
        except Exception:
            self.graph.drop(db)
            self.ledger.delete_run(new)
            raise
        return {"run": new, "parent": run, "fork_at": at, "events": n, "state": self.graph.state_hash(db)}

    def replay_into(self, run: str, db: str) -> int:
        evs = self.ledger.events(run)
        for e in evs:
            self.graph.write(db, e["queries"])
        return len(evs)

    def replay(self, run: str) -> dict:
        """Rebuild the run from its log into a scratch database and compare with the live graph."""
        r = self.ledger.run(run)
        m = self.method_of(r)
        scratch = f"{r['db']}__replay"
        self.graph.drop(scratch)
        self.graph.create(scratch, [core_schema(), m.schema])
        try:
            n = self.replay_into(run, scratch)
            a, b = self.graph.state_hash(r["db"]), self.graph.state_hash(scratch)
        finally:
            self.graph.drop(scratch)
        return {"run": run, "events": n, "live": a, "replayed": b, "identical": a == b}

    def drop_run(self, run: str) -> None:
        r = self.ledger.run(run)
        self.graph.drop(r["db"])
        self.ledger.delete_run(run)


def setup_queries(intent: dict, sources: dict[str, dict]) -> list[str]:
    attrs = {"research_question": "research-question", "method": "method-name", "stance": "stance",
             "sensitizing_concepts": "sensitizing", "prior_research": "prior-research", "study_context": "description"}
    has = "".join(f", has {a} {lit(intent[k])}" for k, a in attrs.items() if intent.get(k))
    qs = [f'insert $i isa intent, has id "intent"{has};']
    for sid, s in sources.items():
        qs.append(f"insert $s isa source, has id {lit(sid)}, has label {lit(s['title'] or sid)}, has version {s['version']};")
    return qs


def canonical_text(doc: dict) -> tuple[str, list[dict]]:
    """Render turns as 'Speaker: text' blocks; every turn and segment becomes an offset range in that text."""
    parts, units, pos = [], [], 0
    turn_pos: dict[str, int] = {}
    for t in doc["turns"]:
        prefix = "" if t["role"] == "meta" else f"{t['speaker']}: "
        start = pos + len(prefix)
        parts.append(prefix + t["text"] + "\n\n")
        units.append({"id": t["id"], "kind": "turn", "role": t["role"], "speaker": t["speaker"],
                      "start": start, "end": start + len(t["text"])})
        turn_pos[t["id"]] = start
        pos += len(prefix) + len(t["text"]) + 2
    text = "".join(parts)
    cursor: dict[str, int] = {}
    for s in doc["segments"]:
        base = turn_pos[s["turn"]]
        turn_text = next(t["text"] for t in doc["turns"] if t["id"] == s["turn"])
        i = turn_text.find(s["text"], cursor.get(s["turn"], 0))
        if i < 0:
            raise QlsError(f"segment {s['id']} is not a slice of its turn")
        cursor[s["turn"]] = i + len(s["text"])
        units.append({"id": s["id"], "kind": "segment", "role": "informant", "speaker": s["speaker"], "turn": s["turn"],
                      "start": base + i, "end": base + i + len(s["text"]), "question": s.get("question"),
                      "question_turn": s.get("question_turn"), "question_gap": s.get("question_gap", 0),
                      "section": s.get("section")})
    return text, units


__all__ = ["Project", "canonical_text", "now"]
