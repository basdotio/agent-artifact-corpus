#!/usr/bin/env python3
"""Build a usable library from every automated public-source collector, unattended.

Example: "$PY" bootstrap.py --data ~/buffett-munger-data
Run it with the Python that has the retrieval dependencies, normally
<DATA>/runtime/bin/python. It writes only under --data:
  <DATA>/buffett-munger-library   library, models, semantic index, Q&A units
  <DATA>/staging/bootstrap        staged batches, logs/, state.json, merge-report.json
  <DATA>/bootstrap-report.json    final JSON report (also printed to stdout)

The step sequence is fixed. Finished collector steps are recorded in state.json
and skipped on rerun; failed or partial ones are retried. Collectors, merge and the
index build are incremental themselves, so an interrupted run resumes where it
stopped. Exit 0 only when the library has documents, the semantic index and Q&A
units are current and a hybrid, reranked search returns results for both people.
Source gaps (items a collector found but could not capture) are listed, not hidden.
"""
import argparse
import contextlib
import importlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import sys
import time

import attribution
from library import now

SCRIPTS = Path(__file__).resolve().parent
SKILL = SCRIPTS.parent
COLLECTORS = ("collect-buffett-letters", "collect-wesco-letters", "collect-reports",
              "collect-financials", "collect-meetings", "collect-speeches")
SMOKE_QUERIES = {"Warren Buffett": "What is a circle of competence?",
                 "Charlie Munger": "Why do incentives matter so much?"}


def skill_version():
    match = re.search(r'^\s+version:\s*"?([^"\n]+)"?\s*$', (SKILL / "SKILL.md").read_text(encoding="utf-8"), re.M)
    return match[1] if match else None


def install_hint():
    return (f'uv pip install --python "{sys.executable}" -r "{SCRIPTS / "requirements-retrieval.txt"}" '
            "pypdf lxml brotli")


def check_dependencies():
    """Return (problems, versions, warnings) for the dependencies listed in local-library.md."""
    problems, versions, warnings = [], {}, []
    if sys.version_info < (3, 9):
        problems.append("Python 3.9+ required, found " + sys.version.split()[0])
    try:
        sqlite3.connect(":memory:").execute("CREATE VIRTUAL TABLE probe USING fts5(text)")
    except sqlite3.Error:
        problems.append("This Python's SQLite lacks FTS5")
    pins = dict(line.strip().split("==", 1) for line in
                (SCRIPTS / "requirements-retrieval.txt").read_text().splitlines() if "==" in line)

    def importable(module, package=None):
        try:
            importlib.import_module(module)
        except Exception:
            return False
        try:
            versions[package or module] = importlib.metadata.version(package or module)
        except importlib.metadata.PackageNotFoundError:
            versions[package or module] = "unknown"
        return True

    for package in pins:
        if not importable(package):
            problems.append(f"{package} is not importable (semantic search and reranking)")
        elif versions[package] != pins[package]:
            warnings.append(f"{package} {versions[package]} differs from pinned {pins[package]}")
    if not importable("pypdf") and not shutil.which("pdftotext"):
        problems.append("PDF extraction needs pypdf (or pdftotext on PATH)")
    if not importable("lxml"):
        problems.append("lxml is not importable (collect_speeches.py)")
    if not importable("brotli", "Brotli") and not (os.environ.get("BUFFETT_MUNGER_NODE") or shutil.which("node")):
        problems.append("Brotli responses need the brotli package (or Node.js via BUFFETT_MUNGER_NODE)")
    return problems, versions, warnings


def execute(command, log_path, capture=False):
    """Run one skill script; output is appended to its log. Returns (exit code, stdout if captured)."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as log:
        log.write(f"\n# {now()}\n$ {' '.join(command)}\n".encode())
        log.flush()
        result = subprocess.run(command, stdout=subprocess.PIPE if capture else log, stderr=log,
                                env=dict(os.environ, PYTHONUNBUFFERED="1"))
    return result.returncode, result.stdout.decode("utf-8", "replace") if capture else ""


def tail(path, lines=15):
    try:
        return "\n".join(path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:])
    except OSError:
        return ""


def mtime(path):
    return path.stat().st_mtime_ns if path.exists() else None


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def collector_plan(library, stage, workers):
    py = sys.executable
    plan = []
    for kind in ("buffett-letters", "wesco-letters", "reports"):
        plan.append(("collect-" + kind, [py, str(SCRIPTS / "collect.py"), "--library", str(library), "--kind", kind],
                     library / "discovery" / (kind + "-last-run.json")))
    plan.append(("collect-financials", [py, str(SCRIPTS / "collect_financials.py"), "--stage", str(stage / "financials"),
                                        "--library", str(library), "--from-year", "1995", "--kind", "all",
                                        "--workers", str(workers)], stage / "financials" / "manifest.json"))
    plan.append(("collect-meetings", [py, str(SCRIPTS / "collect_meetings.py"), "--output", str(stage / "meetings"),
                                      "--from-year", "1994", "--to-year", "2024", "--workers", str(workers)],
                 stage / "meetings" / "manifest.json"))
    plan.append(("collect-speeches", [py, str(SCRIPTS / "collect_speeches.py"), "--output", str(stage / "speeches")],
                 stage / "speeches" / "manifest.json"))
    return plan


def summarize_result(name, data):
    """Item-level gaps and counts from a collector's own result file."""
    if name in ("collect-buffett-letters", "collect-wesco-letters", "collect-reports"):
        counts = {key: data.get(key) for key in ("discovered", "selected", "indexed", "skipped")}
    elif name == "collect-financials":
        statuses = [doc.get("status") for doc in data.get("documents", [])]
        counts = {"discovered": data.get("discovered"), "staged": statuses.count("staged"),
                  "already_indexed": statuses.count("already_indexed")}
    elif name == "collect-meetings":
        counts = {"sessions_discovered": data.get("sessions_discovered"), "staged": len(data.get("documents", []))}
    else:
        counts = {"staged": len(data.get("documents", []))}
    return counts, [{"step": name, **gap} for gap in data.get("failures", [])]


def corpus_summary(library):
    database = library / "corpus.sqlite3"
    if not database.exists():
        return {"documents": 0, "chunks": 0}
    with contextlib.closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        speakers = {"Warren Buffett": 0, "Charlie Munger": 0, "other": 0, "unassigned": 0}
        for speaker, count in db.execute("SELECT speaker, count(*) FROM chunks GROUP BY speaker"):
            key = "unassigned" if speaker is None else attribution.canonical(speaker) or "other"
            speakers[key] += count
        documents = {row[0] for row in db.execute("SELECT id FROM documents")}
        series = {}
        for (metadata,) in db.execute("SELECT metadata FROM documents"):
            key = json.loads(metadata).get("series") or "unspecified"
            series[key] = series.get(key, 0) + 1
        mapped = attribution.load_map()
        return {"documents": len(documents), "chunks": sum(speakers.values()), "chunks_by_speaker": speakers,
                "documents_by_series": dict(sorted(series.items())),
                "attribution_map": {"entries": len(mapped),
                                    "matching_documents": sum(doc in documents for doc in mapped)}}


def library_urls(library):
    database = library / "corpus.sqlite3"
    if not database.exists():
        return set()
    with contextlib.closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        return {row[0] for row in db.execute("SELECT url FROM documents WHERE url IS NOT NULL")}


def parse_json(text):
    try:
        return json.loads(text)
    except ValueError:
        return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--data", required=True, help="Data root; the library is <DATA>/buffett-munger-library")
    parser.add_argument("--workers", type=int, default=3, help="Parallel downloads per staged collector (max 4)")
    parser.add_argument("--threads", type=int, default=4, help="ONNX threads for the index and Q&A builds")
    args = parser.parse_args(argv)
    data = Path(args.data).expanduser().resolve()
    stage = data / "staging" / "bootstrap"
    stage.mkdir(parents=True, exist_ok=True)
    import fcntl
    # One writer per library: a second bootstrap on the same data root refuses to start.
    with (stage / "bootstrap.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print(json.dumps({"ok": False, "error": "Another bootstrap is running on " + str(data)}), file=sys.stderr)
            return 1
        return bootstrap(data, args.workers, args.threads)


def bootstrap(data, workers, threads):
    library = data / "buffett-munger-library"
    stage = data / "staging" / "bootstrap"
    logs = stage / "logs"
    state_path = stage / "state.json"
    report_path = data / "bootstrap-report.json"
    started = time.monotonic()
    report = {"ok": False, "skill_version": skill_version(), "data": str(data), "library": str(library),
              "python": sys.executable, "started_at": now(), "steps": [], "failures": [], "source_gaps": [],
              "warnings": []}

    def progress(message):
        print("[bootstrap] " + message, file=sys.stderr, flush=True)

    def finish(code):
        report.update(corpus_summary(library))
        report["wiki_pages"] = len([p for p in (library / "wiki").glob("*.md") if p.name not in {"index.md", "log.md"}])
        report["finished_at"] = now()
        report["elapsed_seconds"] = round(time.monotonic() - started)
        report["report_path"] = str(report_path)
        save_json(report_path, report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return code

    if Path(sys.prefix).resolve() != (data / "runtime").resolve():
        report["warnings"].append(f"Not running from {data / 'runtime'}; the skill expects "
                                  f"{data / 'runtime' / 'bin' / 'python'} when answering questions")
    problems, versions, warnings = check_dependencies()
    report["dependencies"] = versions
    report["warnings"].extend(warnings)
    if problems:
        report["failures"].append({"step": "dependencies", "error": "; ".join(problems), "fix": install_hint()})
        return finish(1)

    # A new or deleted library invalidates step records left by an earlier run.
    state = load_json(state_path) if state_path.exists() and (library / "corpus.sqlite3").exists() else {"steps": {}}

    def record(name, status, seconds=0, **extra):
        entry = {"name": name, "status": status, "seconds": round(seconds), "log": str(logs / (name + ".log")), **extra}
        report["steps"].append(entry)
        return entry

    def run(name, command, capture=False):
        progress(f"{name}: running (log {logs / (name + '.log')})")
        began = time.monotonic()
        code, stdout = execute(command, logs / (name + ".log"), capture)
        return code, stdout, time.monotonic() - began

    def step_failed(name, code, seconds, error=None, **extra):
        error = error or f"exit code {code}"
        report["failures"].append({"step": name, "error": error, "log_tail": tail(logs / (name + ".log"))})
        progress(f"{name}: FAILED ({error})")
        return record(name, "failed", seconds, exit_code=code, **extra)

    try:
        code, _, seconds = run("init", [sys.executable, str(SCRIPTS / "library.py"), "--library", str(library), "init"])
        if code:
            step_failed("init", code, seconds)
            return finish(1)
        record("init", "ok", seconds)

        speeches = stage / "speeches"
        speeches.mkdir(parents=True, exist_ok=True)
        if not (speeches / "chapter-links.json").exists():
            shutil.copyfile(SKILL / "assets" / "chapter-links.json", speeches / "chapter-links.json")

        for name, command, result_path in collector_plan(library, stage, workers):
            previous = state["steps"].get(name, {})
            if previous.get("status") == "ok":
                progress(f"{name}: skipped (finished in an earlier run)")
                record(name, "skipped", counts=previous.get("counts"))
                continue
            before = mtime(result_path)
            code, _, seconds = run(name, command)
            fresh = result_path.exists() and mtime(result_path) != before
            result = load_json(result_path) if fresh else None
            if result is None:
                entry = step_failed(name, code, seconds, None if code else "no result file written")
            else:
                counts, gaps = summarize_result(name, result)
                whole = [gap["error"] for gap in gaps if gap.get("stage") == "index"]
                if whole or (code and not gaps):
                    entry = step_failed(name, code, seconds, "; ".join(whole) or None, counts=counts)
                else:
                    status = "partial" if gaps else "ok"
                    entry = record(name, status, seconds, exit_code=code, counts=counts, gaps=gaps)
                    progress(f"{name}: {status} in {round(seconds)}s {json.dumps(counts)}"
                             + (f", {len(gaps)} source gaps" if gaps else ""))
            state["steps"][name] = {"status": entry["status"], "finished_at": now(), "counts": entry.get("counts"),
                                    "gaps": entry.get("gaps", [])}
            save_json(state_path, state)

        manifests = [str(path) for path in (stage / "meetings" / "manifest.json", stage / "financials" / "manifest.json",
                                            stage / "speeches" / "manifest.json") if path.exists()]
        merge_report = stage / "merge-report.json"
        if not manifests:
            record("merge", "skipped", reason="no staged manifests")
        else:
            before = mtime(merge_report)
            code, _, seconds = run("merge", [sys.executable, str(SCRIPTS / "merge_staged.py"), "--library", str(library),
                                             "--report", str(merge_report)] + manifests)
            merged = load_json(merge_report) if merge_report.exists() and mtime(merge_report) != before else None
            if merged is None:
                step_failed("merge", code, seconds)
            else:
                for failure in merged["failures"]:
                    entry = failure.get("entry", {})
                    report["failures"].append({"step": "merge", "manifest": failure.get("manifest"),
                                               "document": entry.get("id") or entry.get("document_id") or entry.get("url"),
                                               "error": failure.get("error")})
                record("merge", "failed" if merged["failures"] else "ok", seconds, exit_code=code,
                       counts={"indexed": len(merged["indexed"]), "skipped": len(merged["skipped"]),
                               "failures": len(merged["failures"])})
                progress(f"merge: indexed {len(merged['indexed'])}, unchanged {len(merged['skipped'])}, "
                         f"failed {len(merged['failures'])}")

        # A document one collector could not fetch may have been captured by another (the annual-report
        # PDFs are reachable from both collect.py and collect_financials.py); only unfilled gaps are gaps.
        indexed = library_urls(library)
        report["filled_gaps"] = []
        for name in COLLECTORS:
            for gap in state["steps"].get(name, {}).get("gaps", []):
                report["filled_gaps" if gap.get("url") in indexed else "source_gaps"].append(gap)

        code, _, seconds = run("models", [sys.executable, str(SCRIPTS / "setup_retrieval.py"),
                                          "--models-dir", str(library / "retrieval" / "models")])
        if code:
            step_failed("models", code, seconds)
        else:
            record("models", "ok", seconds)

        retrieve = [sys.executable, str(SCRIPTS / "retrieve.py"), "--library", str(library)]
        code, _, seconds = run("index", retrieve + ["build", "--max-tokens", "512", "--batch-size", "32",
                                                    "--threads", str(threads)])
        _, stdout, _ = run("index-status", retrieve + ["status"], capture=True)
        index = parse_json(stdout) or {"ready": False, "reason": "status output unreadable"}
        report["semantic_index"] = index
        if code or not index.get("ready"):
            step_failed("index", code, seconds, None if code else "index not ready: " + str(index.get("reason")))
        else:
            record("index", "ok", seconds, chunks=index.get("chunks"))

        qa = [sys.executable, str(SCRIPTS / "qa.py"), "--library", str(library)]
        _, stdout, _ = run("qa-status", qa + ["status"], capture=True)
        units = parse_json(stdout) or {}
        if units.get("ready") and units.get("semantic"):
            record("qa", "skipped", reason="Q&A units already current", units=units.get("units"))
        else:
            code, _, seconds = run("qa", qa + ["build", "--threads", str(threads)])
            _, stdout, _ = run("qa-status", qa + ["status"], capture=True)
            units = parse_json(stdout) or {"ready": False}
            if code or not (units.get("ready") and units.get("semantic")):
                step_failed("qa", code, seconds, None if code else "Q&A units not ready: " + json.dumps(units))
            else:
                record("qa", "ok", seconds, units=units.get("units"))
        report["qa_units"] = units

        report["smoke_test"] = {}
        for person, query in SMOKE_QUERIES.items():
            name = "smoke-" + person.split()[-1].lower()
            code, stdout, seconds = run(name, retrieve + ["search", query, "--speaker", person, "--mode", "hybrid",
                                                          "--limit", "3", "--context", "0"], capture=True)
            result = parse_json(stdout) or {}
            summary = {"query": query, "mode_used": result.get("mode_used"), "reranked": result.get("reranked"),
                       "results": len(result.get("results", [])), "warnings": result.get("warnings")}
            report["smoke_test"][person] = summary
            if code or summary["mode_used"] != "hybrid" or not summary["reranked"] or not summary["results"]:
                step_failed(name, code, seconds, "hybrid reranked search did not return results: " + json.dumps(summary))
            else:
                record(name, "ok", seconds)
    except KeyboardInterrupt:
        report["failures"].append({"step": "bootstrap", "error": "interrupted; rerun the same command to resume"})
        return finish(130)

    summary = corpus_summary(library)
    if not summary["documents"]:
        report["failures"].append({"step": "library", "error": "library has no documents"})
    report["ok"] = not report["failures"]
    progress("done: " + ("ok" if report["ok"] else f"{len(report['failures'])} failures")
             + f", {len(report['source_gaps'])} source gaps")
    return finish(0 if report["ok"] else 1)


if __name__ == "__main__":
    sys.exit(main())
