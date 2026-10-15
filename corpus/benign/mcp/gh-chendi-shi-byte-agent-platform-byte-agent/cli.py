import argparse
import json
import sqlite3
import os
import sys
import hashlib
import time
from dataclasses import asdict
from contextlib import ExitStack
from pathlib import Path
from .knowledge import Knowledge
from .model import Ollama, Scripted
from .runtime import Runtime, RuntimeBusy, SYSTEM
from .tools import registry


def seed_metrics(path):
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS metrics (service TEXT, minute INTEGER, requests INTEGER, errors INTEGER, p95_ms REAL, PRIMARY KEY(service,minute))")
        db.executemany("INSERT OR REPLACE INTO metrics VALUES (?,?,?,?,?)", [("search", i, 1000, 50, 480) for i in range(30)] + [("live", i, 2000, 2, 120) for i in range(30)])
    db.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["dataset", "ingest", "demo", "run", "mcp", "enqueue", "worker", "status", "cancel", "prepare-model"])
    parser.add_argument("--knowledge", type=Path, default=Path("examples/knowledge"))
    parser.add_argument("--data", type=Path, default=Path("runs/data"))
    parser.add_argument("--output", type=Path, default=Path("runs/demo"))
    parser.add_argument("--task", default="Diagnose search service errors using metrics and cite the runbook.")
    parser.add_argument("--model")
    parser.add_argument("--target", default="qwen3:0.6b-byte")
    parser.add_argument("--connection", type=Path)
    parser.add_argument("--skill", type=Path, help="explicit trusted operator workflow")
    parser.add_argument("--service", help="operator-selected exact tool service scope")
    parser.add_argument("--verify", action="store_true", help="validate observed diagnostic facts and boundedly repair output")
    parser.add_argument("--model-context", type=int, default=4096)
    parser.add_argument("--model-output", type=int, default=384)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sdk", action="store_true")
    parser.add_argument("--transport", choices=["local", "mcp"], default="local")
    parser.add_argument("--queue", type=Path, default=Path("runs/jobs.sqlite"))
    parser.add_argument("--job-id")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--worker-id")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--embedding-model")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--max-steps", type=int, default=8)
    parser.add_argument("--max-calls", type=int, default=16)
    parser.add_argument("--max-tokens", type=int, default=12000)
    args = parser.parse_args()
    if args.verify and (args.command not in {"run", "worker"} or (args.command == "run" and not args.service)):
        parser.error("--verify requires --service and run/worker")
    if args.command == "demo" and args.connection:
        parser.error("demo seeds synthetic data; use run with an existing connection")
    system = SYSTEM
    if args.skill:
        from .skills import load_skill
        system = load_skill(args.skill).prompt(system)
    if args.verify:
        from .domain import answer_schema
        system += "\nInspect all three tools for the exact service. Return only JSON conforming to this schema; copy service_metrics.error_rate for the entire 30-minute window, not recent_error_rate.\n" + json.dumps(answer_schema())
    if args.command == "prepare-model":
        from .model import prepare_template_variant
        print(json.dumps(prepare_template_variant(args.model or "qwen3:0.6b", args.target, args.base_url), indent=2))
        return
    if args.command in {"enqueue", "status", "cancel"}:
        from .jobs import JobQueue
        queue = JobQueue(args.queue)
        if args.command == "enqueue":
            job = queue.enqueue(args.task, payload={"service": args.service} if args.service else {}, idempotency_key=args.idempotency_key)
        else:
            if not args.job_id:
                parser.error("status/cancel requires --job-id")
            job = queue.cancel(args.job_id) if args.command == "cancel" else queue.get(args.job_id)
        print(json.dumps(asdict(job) if job else {"error": "job not found"}, ensure_ascii=False, indent=2))
        return
    args.data.mkdir(parents=True, exist_ok=True)
    if args.command == "dataset":
        from .domain import create_dataset
        manifest = create_dataset(args.data)
        kb = Knowledge(args.data / "knowledge.sqlite")
        try:
            chunks = kb.ingest(args.data / "knowledge")
        finally:
            kb.db.close()
        print(json.dumps({"synthetic": True, "tasks": len(manifest["tasks"]), "chunks": chunks, "data": str(args.data)}))
        return
    knowledge = Knowledge(args.data / "knowledge.sqlite")
    embedding = Ollama(args.embedding_model, args.base_url).embed if args.embedding_model else None
    metrics = args.data / "metrics.sqlite"
    if args.connection:
        from .connectors import load_sources
        connector = load_sources(args.connection)
        metrics = connector.metrics_database
        connector.ingest_into(knowledge, embedding)
    if args.command == "ingest":
        chunks = knowledge.db.execute("SELECT count(*) FROM chunks").fetchone()[0] if args.connection else knowledge.ingest(args.knowledge, embedding)
        print(json.dumps({"chunks": chunks, "retrieval": "hybrid" if embedding else "lexical"}))
        knowledge.db.close()
        return
    if args.command == "demo":
        knowledge.ingest(args.knowledge)
        seed_metrics(metrics)
        evidence = knowledge.search("search error rollback", 1)
        citation = evidence[0]["id"] if evidence else "missing"
        model = Scripted([{"calls": [{"name": "service_metrics", "arguments": {"service": "search"}},
                                     {"name": "knowledge_search", "arguments": {"query": "search error rollback"}}]},
                          {"answer": f"Synthetic search error rate is 5%. Investigate the release and use rollback review per [{citation}]. This is a scripted fixture."}])
    else:
        model = Ollama(args.model, args.base_url, args.model_context, args.model_output, args.timeout, args.seed) if args.model else None
    tools = registry(knowledge, metrics, embedding)
    if args.service and args.command != "worker":
        from .verification import scope_tools
        tools = scope_tools(tools, args.service)
    if args.command == "mcp":
        from .mcp import serve, serve_sdk
        (serve_sdk if args.sdk else serve)(tools)
        return
    if model is None:
        parser.error("run requires --model; ingest knowledge and provide metrics.sqlite first")
    if not model.fixture:
        model.revision = model.describe()
    with ExitStack() as stack:
        stack.callback(knowledge.db.close)
        if args.transport == "mcp":
            if args.connection or args.embedding_model:
                parser.error("MCP transport currently requires a prepared --data snapshot")
            from .mcp_client import SyncMCPClient
            client = stack.enter_context(SyncMCPClient(sys.executable, ["-m", "byte_agent.mcp", "--data", str(args.data.resolve()), "--sdk"], dict(os.environ)))
            snapshot = hashlib.sha256(json.dumps([t.revision for t in tools.values()], sort_keys=True).encode()).hexdigest()
            tools = client.tools(list(tools), revision=snapshot)
            if args.service and args.command != "worker":
                from .verification import scope_tools
                tools = scope_tools(tools, args.service)
        options = dict(max_steps=args.max_steps, max_calls=args.max_calls, max_tokens=args.max_tokens, system_prompt=system)
        if args.verify and args.command != "worker":
            from .verification import make_diagnostic_validator
            options["answer_validator"] = make_diagnostic_validator(args.service, args.task)
        if args.command == "worker":
            from .jobs import JobQueue, Worker
            def handle(job, cancelled):
                job_options = dict(options)
                job_tools = tools
                service = job.payload.get("service")
                if "service" in job.payload and (not isinstance(service, str) or not service):
                    raise ValueError("job service must be a nonempty string")
                if service and args.service and args.service != service:
                    raise ValueError("job service conflicts with worker service")
                service = service if service is not None else args.service
                if service is not None:
                    from .verification import scope_tools
                    job_tools = scope_tools(tools, service)
                if args.verify:
                    from .verification import make_diagnostic_validator
                    if not service:
                        raise ValueError("verified job requires an authorized service; enqueue with --service")
                    job_options["answer_validator"] = make_diagnostic_validator(service, job.task)
                while True:
                    if cancelled():
                        return {"agent_status": "cancelled", "requires_review": True}
                    try:
                        result = Runtime(args.output / job.id, model, job_tools, **job_options).run(job.task, is_cancelled=cancelled)
                        return {"agent_status": result["status"], "answer": result["answer"], "trace": str(args.output / job.id / "trace.json"), "requires_review": result["status"] != "completed"}
                    except RuntimeBusy:
                        # A previous lease owner may still finish an issued
                        # provider call. Renew this lease while waiting.
                        time.sleep(.1)
            worker = Worker(JobQueue(args.queue), handle, worker_id=args.worker_id)
            if args.once:
                job = worker.run_once()
                print(json.dumps(asdict(job) if job else {"status": "idle"}, ensure_ascii=False, indent=2))
            else:
                try:
                    worker.run_forever()
                except KeyboardInterrupt:
                    pass
            return
        result = Runtime(args.output, model, tools, **options).run(args.task)
    print(json.dumps({"status": result["status"], "fixture": result["fixture"], "answer": result["answer"], "trace": str(args.output / "trace.json")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
