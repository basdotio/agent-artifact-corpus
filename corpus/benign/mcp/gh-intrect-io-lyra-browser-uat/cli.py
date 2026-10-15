"""lyra-uat: run personas, batches, and inspect what they produce.

Subcommands::

    lyra-uat run <spec> [--target FILE] [--brain NAME] [--model M] [--out DIR] ...
    lyra-uat batch <batch.yaml>
    lyra-uat validate <spec>
    lyra-uat schema [run|batch|report]
    lyra-uat render <report.json>

Exit codes of ``run``: 0 when the run completed (findings or not), 2 when it
was cut off (budget, wall clock, harness) or the brain never finished, 130 when
it was interrupted (SIGINT/SIGTERM; a partial report is still written), 1 on an
error before the browser did anything useful.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import signal
import sys
from pathlib import Path

from .spec import BatchSpec, RunSpec, load_batch_spec, load_run_spec

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_INCOMPLETE = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lyra-uat", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run one persona and write report.json.")
    run.add_argument("spec", type=Path, help="Run file, or a persona file with --target.")
    run.add_argument("--target", type=Path, help="Target file (persona-per-file layout).")
    run.add_argument(
        "--brain",
        help="Backend: anthropic, openrouter, ollama, openai-compat, claude-code, codex, scripted.",
    )
    run.add_argument("--model", help="Model name as the backend spells it.")
    run.add_argument("--base-url", help="OpenAI-compatible endpoint (openai-compat).")
    run.add_argument("--api-key-env", help="Env var holding the API key (OpenAI-compatible).")
    run.add_argument("--out", type=Path, help="Where run directories go (default uat-runs/).")
    run.add_argument("--brief", type=Path, help="Round addendum shown to the persona.")
    run.add_argument("--prior-findings", type=Path, help="JSON list of earlier findings.")
    run.add_argument("--data-dir", type=Path, help="Existing browser data dir to use.")
    run.add_argument("--headful", action="store_true", help="Show the window (default headless).")
    run.add_argument(
        "--dry-run", action="store_true", help="Resolve the spec and print it; start nothing."
    )

    batch = sub.add_parser("batch", help="Run several personas in groups.")
    batch.add_argument("spec", type=Path)
    batch.add_argument("--out", type=Path)
    batch.add_argument("--brain")
    batch.add_argument("--model")
    batch.add_argument("--only", nargs="*", help="Persona ids to run (default: all groups).")
    batch.add_argument("--dry-run", action="store_true")

    validate = sub.add_parser("validate", help="Check a run or batch file and exit.")
    validate.add_argument("spec", type=Path)
    validate.add_argument("--target", type=Path)

    schema = sub.add_parser("schema", help="Print a JSON Schema.")
    schema.add_argument("which", nargs="?", default="report", choices=["run", "batch", "report"])

    render = sub.add_parser("render", help="Render report.json as Markdown to stdout.")
    render.add_argument("report", type=Path)

    demo = sub.add_parser(
        "demo-site", help="Serve the built-in demo site to run a persona against."
    )
    demo.add_argument("--port", type=int, default=8787)
    return parser


def _run_overrides(args: argparse.Namespace) -> dict:
    """Command-line values as top-level spec overrides; absent flags stay absent."""
    from .spec import load_document

    brain = {
        k: v
        for k, v in {
            "backend": args.brain,
            "model": args.model,
            "base_url": args.base_url,
            "api_key_env": args.api_key_env,
        }.items()
        if v is not None
    }
    overrides: dict = {
        "brain": brain or None,
        "out_dir": str(args.out) if args.out else None,
        "data_dir": str(args.data_dir) if args.data_dir else None,
        "headless": False if args.headful else None,
    }
    if args.target:
        overrides["target"] = load_document(args.target)
    if args.brief:
        overrides["brief"] = args.brief.read_text(encoding="utf-8")
    if args.prior_findings:
        overrides["prior_findings"] = load_document(args.prior_findings)
    return overrides


def _print_spec(spec) -> None:
    print(json.dumps(spec.model_dump(mode="json"), indent=2, ensure_ascii=False))


EXIT_INTERRUPTED = 130


def run_with_signals(coro):
    """Run ``coro`` so that SIGINT and SIGTERM cancel it, whatever they were set to.

    A job started in the background by a non-interactive shell inherits SIGINT as
    *ignored*, and Python then installs no handler for it, so ``kill -INT`` would do
    nothing and a plain ``kill`` would end the process without its cleanup — leaving a
    harness, its server and a browser running. Cancelling the task instead runs the
    cleanup (the browser is closed, the harness's process group stopped, a report of
    what happened so far written) and then raises ``CancelledError`` to the caller.
    """

    async def main():
        loop = asyncio.get_running_loop()
        task = asyncio.current_task()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, task.cancel)
            except (NotImplementedError, RuntimeError):  # not the main thread, or not POSIX
                pass
        return await coro

    return asyncio.run(main())


def cmd_run(args: argparse.Namespace) -> int:
    spec = load_run_spec(args.spec, **_run_overrides(args))
    if args.dry_run:
        _print_spec(spec)
        return EXIT_OK
    from .runner import run_spec

    try:
        report = run_with_signals(run_spec(spec))
    except asyncio.CancelledError:
        print(
            "interrupted: the report of what happened so far is under the run directory",
            file=sys.stderr,
        )
        return EXIT_INTERRUPTED
    print(report.one_line())
    print(report.artifacts.report_json)
    return EXIT_OK if report.run.status == "completed" else EXIT_INCOMPLETE


def cmd_batch(args: argparse.Namespace) -> int:
    spec = load_batch_spec(args.spec)
    if args.out:
        spec.out_dir = args.out
    if args.brain:
        spec.brain.backend = args.brain
    if args.model:
        spec.brain.model = args.model
    if args.dry_run:
        _print_spec(spec)
        return EXIT_OK
    from .batch import run_batch

    try:
        summary = run_with_signals(run_batch(spec, only=args.only))
    except asyncio.CancelledError:
        print(
            "interrupted: each running persona was stopped and wrote a partial report; "
            "no batch summary was written",
            file=sys.stderr,
        )
        return EXIT_INTERRUPTED
    print(summary.one_line())
    print(summary.path)
    return EXIT_OK if summary.all_completed else EXIT_INCOMPLETE


def cmd_validate(args: argparse.Namespace) -> int:
    from .spec import load_document

    document = load_document(args.spec)
    kind = "batch" if isinstance(document, dict) and "groups" in document else "run"
    try:
        if kind == "batch":
            spec = load_batch_spec(args.spec)
        else:
            target = load_document(args.target) if args.target else None
            spec = load_run_spec(args.spec, target=target)
    except Exception as exc:  # noqa: BLE001 — reported, not raised: this is the check
        print(f"INVALID {kind} spec {args.spec}: {exc}", file=sys.stderr)
        return EXIT_ERROR
    name = spec.persona.id if isinstance(spec, RunSpec) else f"{len(spec.personas)} personas"
    print(f"OK {kind} spec {args.spec}: {name}")
    return EXIT_OK


def cmd_schema(args: argparse.Namespace) -> int:
    if args.which == "run":
        schema = RunSpec.model_json_schema()
    elif args.which == "batch":
        schema = BatchSpec.model_json_schema()
    else:
        from .report import Report

        schema = Report.model_json_schema()
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    return EXIT_OK


def cmd_render(args: argparse.Namespace) -> int:
    from .report import Report, render_markdown

    report = Report.model_validate_json(args.report.read_text(encoding="utf-8"))
    print(render_markdown(report))
    return EXIT_OK


def cmd_demo_site(args: argparse.Namespace) -> int:
    from .demo_site import serve_forever

    serve_forever(args.port)
    return EXIT_OK


_COMMANDS = {
    "run": cmd_run,
    "batch": cmd_batch,
    "validate": cmd_validate,
    "schema": cmd_schema,
    "render": cmd_render,
    "demo-site": cmd_demo_site,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
