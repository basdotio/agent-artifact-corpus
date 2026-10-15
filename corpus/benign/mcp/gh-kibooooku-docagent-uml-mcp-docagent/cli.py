"""Small local CLI; personal documents and live outputs stay under ignored folders."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from .agents import ChatModel, ExtractiveDemoAgents, LLMAgents, ModelConfig, ModelError
from .core import MemoryStore, WorkflowEngine
from .documents import import_pdf
from .evaluation import evaluate
from .gateway import LocalGateway, MCPGateway


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(description="Evidence-governed document agents with MCP")
    commands = root.add_subparsers(dest="command", required=True)
    for command in ("ask", "demo"):
        item = commands.add_parser(command, help="Live QA" if command == "ask" else "Offline extractive workflow demo")
        item.add_argument("question", nargs="?", default="港湾系统的试点规模为多少名读者？")
        item.add_argument("--doc-id", default="harbor")
        item.add_argument("--data-dir", type=Path, default=Path("examples/documents"))
        item.add_argument("--mode", choices=("baseline", "engineered", "optimized"), default="optimized")
        item.add_argument("--output", type=Path, default=Path("outputs/last_run.json"))
        item.add_argument("--memory", type=Path, default=Path("outputs/memory.json"))
    item = commands.add_parser("tools", help="List tools through a real MCP subprocess")
    item.add_argument("--data-dir", type=Path, default=Path("examples/documents"))
    item = commands.add_parser("import-pdf", help="Import a text PDF with heuristic page sections; no OCR")
    item.add_argument("path", type=Path)
    item.add_argument("--output-dir", type=Path, default=Path("data/documents"))
    item.add_argument("--doc-id")
    item = commands.add_parser("evaluate", help="Run real-model comparisons; never uses mock answers")
    item.add_argument("--data-dir", type=Path, default=Path("examples/documents"))
    item.add_argument("--questions", type=Path, default=Path("examples/questions.json"))
    item.add_argument("--output-dir", type=Path, default=Path("outputs/evaluation"))
    item.add_argument("--modes", nargs="+", choices=("baseline", "engineered", "optimized"),
                      default=["baseline", "engineered", "optimized"])
    item.add_argument("--limit", type=int)
    item.add_argument("--concurrency", type=int, default=3)
    item.add_argument("--resume", action="store_true")
    item = commands.add_parser("faults", help="Controlled fault injection and ablations; no model calls")
    item.add_argument("--data-dir", type=Path, default=Path("examples/documents"))
    item.add_argument("--output-dir", type=Path, default=Path("outputs/robustness"))
    return root


async def run(args):
    if args.command == "faults":
        from .robustness import run_robustness
        report = await run_robustness(args.data_dir, args.output_dir)
        print(json.dumps(report.get("summary", report), ensure_ascii=False, indent=2))
        return
    if args.command == "import-pdf":
        print(import_pdf(args.path, args.output_dir, args.doc_id))
        return
    if args.command == "tools":
        async with MCPGateway(args.data_dir) as gateway:
            print(json.dumps(await gateway.list_tools(), ensure_ascii=False, indent=2))
        return
    if args.command == "evaluate":
        if args.concurrency < 1 or args.concurrency > 8:
            raise ValueError("Choose concurrency from 1 to 8.")
        report = await evaluate(args.data_dir, args.questions, args.output_dir, args.modes,
                                args.limit, args.concurrency, resume=args.resume)
        print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
        return
    gateway_type = LocalGateway if args.mode == "baseline" else MCPGateway
    async with gateway_type(args.data_dir) as gateway:
        model = None
        if args.command == "ask":
            model = ChatModel(ModelConfig.from_env())
            agents = LLMAgents(model)
        else:
            agents = ExtractiveDemoAgents()
        try:
            engine = WorkflowEngine(agents.actor, agents.reviewer, gateway,
                                    memory_store=MemoryStore(args.memory), max_tool_calls=32)
            result = await engine.run(args.question, args.doc_id, mode=args.mode)
            result["provider"] = "live" if model else "offline-extractive-demo"
            if model:
                result["usage"] = model.usage
                result["returned_models"] = sorted(model.returned_models)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if result.get("state") == "failed":
                raise RuntimeError("Task failed; see the saved execution record.")
        finally:
            if model:
                await model.client.aclose()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        asyncio.run(run(parser().parse_args()))
    except (ModelError, ValueError, FileNotFoundError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
