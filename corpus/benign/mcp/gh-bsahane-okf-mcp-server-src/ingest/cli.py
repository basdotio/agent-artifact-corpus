"""`okf-ingest`: operator command for building, validating and evaluating snapshots.

Runs separately from the MCP server; AI clients never trigger ingestion.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

from okf_mcp_server.src.settings import settings


def _quiet_third_party() -> None:
    """Hide model-loading chatter so FAILED/SKIPPED/WARNING lines stay readable.

    Must run before Docling imports its models. RapidOCR resets its own logger
    to INFO on import, so INFO is disabled globally. Warnings from Python's
    `warnings` module (for example Pillow's DecompressionBombWarning) still show.
    """
    import logging
    import warnings

    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
    os.environ.setdefault("TQDM_DISABLE", "1")
    logging.disable(logging.INFO)
    warnings.filterwarnings("ignore", category=UserWarning, module=r"torch\..*")


def audit_event(event: str, **fields: object) -> None:
    """Append an ingestion event to OKF_AUDIT_LOG (if set) as one JSON line."""
    if not settings.OKF_AUDIT_LOG:
        return
    from datetime import datetime, timezone

    record = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
        "event": event,
        **fields,
    }
    with open(settings.OKF_AUDIT_LOG, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, default=str) + "\n")


def _sync_and_refresh(args: argparse.Namespace) -> int:
    from okf_mcp_server.src.connectors import config as connectors

    try:
        cfg = connectors.load(args.connectors)
    except (OSError, ValueError) as e:
        print(f"ERROR   {e}", file=sys.stderr)
        return 2
    results = connectors.run(cfg, only=args.source)
    failed = False
    for result in results:
        for rel, error in sorted(result.errors.items()):
            print(f"FAILED  {result.source}/{rel}: {error}", file=sys.stderr)
            failed = True
        for rel, reason in sorted(result.skipped.items()):
            print(f"SKIPPED {result.source}/{rel}: {reason}", file=sys.stderr)
        s = result.summary()
        print(
            f"synced {s['source']}: {s['downloaded']} downloaded, {s['unchanged']} unchanged, "
            f"{s['deleted']} deleted, {s['skipped']} skipped, {s['errors']} errors"
        )
        audit_event("ingest.sync", **s)
    if args.command == "sync":
        return 1 if failed else 0
    if failed and not args.allow_failures:
        print(
            "NOT building: a source failed to sync (use --allow-failures)",
            file=sys.stderr,
        )
        return 1
    return main(
        [
            "--data-dir",
            str(args.data_dir),
            "build",
            cfg["mirror"],
            "--keep",
            str(args.keep),
        ]
        + (["--allow-failures"] if args.allow_failures else [])
        + (["--no-embeddings"] if args.no_embeddings else [])
    )


def main(argv: Optional[List[str]] = None) -> int:
    """Entry point for the `okf-ingest` console script."""
    parser = argparse.ArgumentParser(prog="okf-ingest", description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(settings.OKF_DATA_DIR),
        help="snapshot directory (default: OKF_DATA_DIR)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser(
        "build", help="ingest a source folder and publish a new snapshot"
    )
    b.add_argument("source", type=Path, help="folder of source documents")
    b.add_argument(
        "--artifacts-path",
        type=Path,
        help="pre-downloaded Docling models (offline use)",
    )
    b.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="show Docling/OCR/model logs and progress bars",
    )
    b.add_argument(
        "--no-embeddings",
        action="store_true",
        help="skip the semantic index (keyword search only)",
    )
    b.add_argument(
        "--keep",
        type=int,
        default=3,
        help="snapshots to keep after publishing, including the new one (min 2)",
    )
    b.add_argument(
        "--allow-failures",
        action="store_true",
        help="publish even if some files failed to extract (failures.json lists them)",
    )

    sub.add_parser("validate", help="check the published bundle against OKF v0.2 §11")

    s = sub.add_parser(
        "suggest-config", help="print a draft _okf.yaml for a source folder (review it)"
    )
    s.add_argument("source", type=Path, help="folder of source documents")

    sub.add_parser(
        "fetch-model",
        help="download the pinned embedding model for semantic search (~493 MB)",
    )

    for name, text in (
        ("sync", "mirror the sources in a connectors file (documents and permissions)"),
        (
            "refresh",
            "sync, then build and publish a snapshot from the mirror (schedule this)",
        ),
    ):
        c = sub.add_parser(name, help=text)
        c.add_argument("connectors", type=Path, help="connectors.yaml")
        c.add_argument(
            "--source", action="append", help="only this source (repeatable)"
        )
        if name == "refresh":
            c.add_argument("--allow-failures", action="store_true")
            c.add_argument("--no-embeddings", action="store_true")
            c.add_argument("--keep", type=int, default=3)

    e = sub.add_parser("eval", help="measure Hit@k against a question set")
    e.add_argument("questions", type=Path, help="YAML question file")
    e.add_argument("-k", type=int, default=5)

    args = parser.parse_args(argv)
    if args.command == "build":
        if not args.verbose:
            _quiet_third_party()
        from okf_mcp_server.src.ingest.pipeline import build

        try:
            report = build(
                args.source,
                args.data_dir,
                args.artifacts_path,
                args.allow_failures,
                keep=args.keep,
                embeddings=not args.no_embeddings,
            )
        except ValueError as e:
            print(f"ERROR   {e}", file=sys.stderr)
            return 2
        for rel, error in sorted(report.failures.items()):
            print(f"FAILED  {rel}: {error}", file=sys.stderr)
        for rel, reason in sorted(report.skipped.items()):
            print(f"SKIPPED {rel}: {reason}", file=sys.stderr)
        for warning in report.warnings:
            print(f"WARNING {warning}", file=sys.stderr)
        for problem in report.problems:
            print(f"INVALID {problem}", file=sys.stderr)
        for kind, text in report.changes:
            print(f"{kind:<9} {text}")
        state = "published" if report.published else "NOT published"
        print(
            f"snapshot {report.snapshot_id} {state}: {report.concepts} concepts, "
            f"{report.passages} passages, {report.reused} extractions reused, "
            f"{len(report.failures)} failures, {len(report.skipped)} skipped"
        )
        if report.embedding_model:
            print(
                f"semantic index: {report.embedded} passages embedded, "
                f"{report.vectors_reused} reused ({report.embedding_model.split('@')[0]})"
            )
        audit_event(
            "ingest.build",
            snapshot_id=report.snapshot_id,
            published=report.published,
            concepts=report.concepts,
            passages=report.passages,
            failures=len(report.failures),
            skipped=len(report.skipped),
            changes=len(report.changes),
        )
        if report.pruned:
            print(
                f"removed {len(report.pruned)} old snapshot(s): {', '.join(report.pruned)}"
            )
        return 0 if report.published and not report.failures else 1

    if args.command in ("sync", "refresh"):
        return _sync_and_refresh(args)

    if args.command == "fetch-model":
        from okf_mcp_server.src.knowledge.embed import (
            MODEL_ID,
            MODEL_REVISION,
            fetch_model,
        )

        print(f"downloading {MODEL_ID} @ {MODEL_REVISION[:8]} from huggingface.co ...")
        print(f"saved to {fetch_model()}")
        return 0

    if args.command == "suggest-config":
        from okf_mcp_server.src.ingest.suggest import suggest_config

        print(suggest_config(args.source), end="")
        return 0

    from okf_mcp_server.src.knowledge.snapshot import current_snapshot

    if args.command == "validate":
        from okf_mcp_server.src.knowledge.validate import validate_bundle

        problems = validate_bundle(current_snapshot(args.data_dir).bundle)
        for problem in problems:
            print(problem)
        print("conformant" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0

    from okf_mcp_server.src.ingest.evaluate import evaluate

    result = evaluate(args.data_dir, args.questions, args.k)
    for row in result["questions"]:
        mark = "n/a " if not row["answerable"] else ("HIT " if row["hit"] else "MISS")
        extra = "" if row["all_found"] in (None, True) else "  (not all evidence found)"
        print(f"{mark} {row['question']}{extra}")
        for flag in row["flags"]:
            print(f"       flagged: {flag}")
    score = result[f"hit_at_{args.k}"]
    print(json.dumps({k: v for k, v in result.items() if k != "questions"}))
    return 0 if score is not None else 1


if __name__ == "__main__":
    sys.exit(main())
