"""Reusable browser SDK and trusted-parent helpers; credentials are never inputs."""
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path


def positive_id(value):
    if not re.fullmatch(r"[1-9][0-9]{0,15}", value) or int(value) > 9007199254740991:
        raise argparse.ArgumentTypeError("positive exact integer required")
    return int(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("serve", help="Official SDK stdio server; no browser controller")
    sub.add_parser("inspect", help="Retrieve actual MCP guidance and catalogue, without calling a tool")
    sub.add_parser("worker-path", help="Print the packaged CUA worker source path")
    sub.add_parser("skill-path", help="Locate the portable packaged Skill")
    sub.add_parser("training-guidance", help="Read the shared reference; no athlete data or plan is loaded")
    parent = sub.add_parser("record-read", help="Trusted parent browser report, outside MCP")
    parent.add_argument("--run-dir", type=Path, required=True)
    parent.add_argument("--request-id", required=True)
    parent.add_argument("--observation-file", type=Path, required=True)
    read = sub.add_parser("read-workout")
    read.add_argument("--workout-id", type=positive_id, required=True)
    preview = sub.add_parser("preview")
    preview.add_argument("--name", required=True)
    preview.add_argument("--date", required=True)
    apply = sub.add_parser("apply-existing")
    apply.add_argument("--preview-id", required=True)
    apply.add_argument("--proposal-sha256", required=True)
    publish = sub.add_parser("publish-read")
    publish.add_argument("--run-dir", type=Path, required=True)
    publish.add_argument("--request-id", required=True)
    observation = sub.add_parser("record-observation", help="Trusted parent selected UI recorder, outside MCP")
    observation.add_argument("--preview-id", required=True)
    observation.add_argument("--proposal-sha256", required=True)
    observation.add_argument("--observation-file", type=Path, required=True)
    args = vars(parser.parse_args())
    mode = args.pop("mode")
    try:
        if mode == "skill-path":
            print(Path(__file__).with_name("resources") / "garmin-browser-tools" / "SKILL.md")
        elif mode == "training-guidance":
            from .guidance import training_reference
            print(json.dumps(training_reference(), ensure_ascii=False))
        elif mode == "record-read":
            from .publisher import record_parent_read
            record_parent_read(**args)
            print('{"status":"observation_published","observation_method":"parent_browser_tool"}')
        elif mode == "serve":
            from .server import run
            run()
        elif mode == "worker-path":
            print(Path(__file__).with_name("browser_worker.js"))
        elif mode == "publish-read":
            from .publisher import publish
            publish(args["run_dir"], args["request_id"])
            print('{"status":"observation_published"}')
        elif mode == "record-observation":
            from . import write_protocol as p
            p.runtime(p.PRIVATE)
            selected = p.read_json(args.pop("observation_file"))
            value = p.record_browser_observation(p.PRIVATE, args, selected)
            keys = ("preview_id", "proposal_sha256", "receipt_id", "status", "browser_readback_match",
                    "verification", "independently_verified", "api_authentication", "watch", "account_identity")
            print(json.dumps({k: value[k] for k in keys}))
        else:
            from .client import invoke
            asyncio.run(invoke(mode, **args))
        return 0
    except Exception:
        print('{"error":"invalid_or_blocked_browser_operation; no automatic retry"}', file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
