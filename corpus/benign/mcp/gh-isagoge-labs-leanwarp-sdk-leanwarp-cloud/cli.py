"""Agent-friendly JSON CLI; stdin/stdout credentials never pass through the model."""

from __future__ import annotations

import argparse
import getpass
import json
import sys
from importlib.resources import files
from pathlib import Path
from typing import Any, NoReturn

import httpx

from . import __version__
from .amounts import usd_spending_cap
from .client import LeanWarpCloud, LeanWarpCloudError, OperationTimeout
from .config import credentials_path, load_client, save_credentials
from .endpoints import ConfigurationError
from .outcome import OperationOutcome, reported
from .project import ProjectError, plan_upload
from .resources import published_worker_resources
from .session import MAX_INLINE_WAIT_SECONDS, ProjectSession, SessionError, UsageError

DEFAULT_WAIT_SECONDS = 30.0


def _spending_cap(value: str) -> int:
    try:
        return usd_spending_cap(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


_DESCRIPTION = """\
Check and verify Lean proofs on LeanWarp's hosted workers.
Every command prints one JSON object."""

_EPILOG = f"""\
a typical session:
  leanwarp doctor            show which environment this project runs on
  leanwarp files             list the Lean files that would upload
  leanwarp connect           create the project's workspace (no compute yet)
  leanwarp check Main.lean   compile a file and report Lean errors
  leanwarp verify Main.lean --declaration NAME --target 'STATEMENT'
  leanwarp stop              stop the worker when you are done

results:
  Operations wait up to {DEFAULT_WAIT_SECONDS:g} seconds for their result. "success" is true
  when the check passed or the proof was verified, false when it did not,
  and null while the work is still running.

exit codes:
  0  success
  1  the check or proof did not pass, or the project has no environment
  2  the command could not run (see "message")
  3  still running: run `leanwarp wait`, never submit it again

AI agents: run `leanwarp skill` for the full workflow."""


def _wait_seconds(value: str) -> float:
    try:
        seconds = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("must be a number of seconds") from None
    if not 0 <= seconds <= MAX_INLINE_WAIT_SECONDS:
        raise argparse.ArgumentTypeError(
            f"must be between 0 and {MAX_INLINE_WAIT_SECONDS} seconds; "
            "run `leanwarp wait` to wait longer"
        )
    return seconds


class _Parser(argparse.ArgumentParser):
    """Report argument mistakes as JSON on stdout, like every other result."""

    def error(self, message: str) -> NoReturn:
        _emit({"error": "invalid_arguments", "message": message, "usage": self.format_usage()})
        raise SystemExit(2)


def parser() -> argparse.ArgumentParser:
    root = _Parser(
        prog="leanwarp",
        description=_DESCRIPTION,
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    root.add_argument("--version", action="version", version=f"leanwarp {__version__}")
    root.add_argument(
        "--project",
        default=".",
        metavar="DIR",
        help="the Lean project directory (default: the current directory)",
    )
    commands = root.add_subparsers(dest="command", required=True, metavar="COMMAND")

    auth = commands.add_parser("auth", help="sign in with an API key, or sign out")
    auth_commands = auth.add_subparsers(dest="auth_command", required=True, metavar="ACTION")
    auth_commands.add_parser(
        "login",
        help="paste an API key at a hidden prompt (in automation, set LEANWARP_API_KEY instead)",
    )
    auth_commands.add_parser(
        "logout", help="forget the saved key on this machine (revoke it in the dashboard)"
    )

    environment_help = (
        "an environment from `leanwarp environments`; use it even if the project pins "
        "another toolchain or lockfile"
    )
    doctor = commands.add_parser(
        "doctor", help="show which environment this project runs on (no compute)"
    )
    doctor.add_argument("--environment", metavar="NAME", help=environment_help)
    commands.add_parser(
        "files",
        help=(
            "list the Lean files that would upload, with sizes and problems; .gitignore and "
            ".leanwarpignore exclude files (no key needed)"
        ),
    )

    connect = commands.add_parser(
        "connect", help="create this project's workspace (no compute until the first operation)"
    )
    selection = connect.add_mutually_exclusive_group()
    selection.add_argument("--environment", metavar="NAME", help=environment_help)
    selection.add_argument("--bundle", help=argparse.SUPPRESS)
    # Deprecated wire compatibility for existing automation and saved requests.
    connect.add_argument("--profile", metavar="SIZE", help=argparse.SUPPRESS)
    connect.add_argument(
        "--max-profile",
        metavar="SIZE",
        help=argparse.SUPPRESS,
    )
    connect.add_argument(
        "--max-spend",
        metavar="USD",
        type=_spending_cap,
        help="cap total workspace spending in USD (up to six decimals); no cap by default",
    )

    check = commands.add_parser("check", help="compile a file and report Lean errors and warnings")
    check.add_argument("file", metavar="FILE", help="a .lean file in the project")
    check.add_argument(
        "--draft",
        action="store_true",
        help=(
            "a faster check while you edit: Lean reuses its work on the unchanged part of "
            "the file, and `sorry` is only a warning"
        ),
    )

    inspect = commands.add_parser(
        "inspect", help="show the goals and local context at a position in a proof"
    )
    inspect.add_argument("file", metavar="FILE", help="a .lean file in the project")

    tactics = commands.add_parser(
        "try-tactics", help="try tactics at a position without editing the file"
    )
    tactics.add_argument("file", metavar="FILE", help="a .lean file in the project")

    for command in (inspect, tactics):
        command.add_argument("--line", type=int, required=True, help="line number, from 1")
        command.add_argument("--column", type=int, required=True, help="column number, from 1")
    tactics.add_argument(
        "--tactic",
        action="append",
        required=True,
        metavar="TACTIC",
        help="a tactic to try; repeat for several",
    )

    verify = commands.add_parser(
        "verify", help="check that a declaration proves exactly the statement you give"
    )
    verify.add_argument("file", metavar="FILE", help="the .lean file that contains the proof")
    verify.add_argument(
        "--declaration", required=True, metavar="NAME", help="the theorem's name in FILE"
    )
    verify.add_argument(
        "--target",
        required=True,
        metavar="STATEMENT",
        help="the statement the proof must establish, e.g. '∀ n : Nat, n + 0 = n'",
    )
    verify.add_argument(
        "--context-file",
        type=Path,
        metavar="PATH",
        help="Lean imports and definitions the statement needs, e.g. `import Mathlib`",
    )
    verify.add_argument(
        "--fresh", action="store_true", help="verify on a separate worker that stops afterwards"
    )

    for operation in (check, inspect, tactics, verify):
        operation.add_argument(
            "--wait",
            type=_wait_seconds,
            default=DEFAULT_WAIT_SECONDS,
            metavar="SECONDS",
            help=(
                f"wait up to this long for the result, 0 to {MAX_INLINE_WAIT_SECONDS} "
                f"(default: {DEFAULT_WAIT_SECONDS:g}); then use `leanwarp wait`"
            ),
        )
        operation.add_argument(
            "--execution-timeout",
            type=int,
            metavar="SECONDS",
            help="stop the operation on the server after this long, 1 to 600",
        )
        operation.add_argument(
            "--profile",
            metavar="SIZE",
            help=argparse.SUPPRESS,
        )

    wait = commands.add_parser("wait", help="wait for the latest operation's result")
    wait.add_argument(
        "--timeout",
        type=float,
        default=300,
        metavar="SECONDS",
        help="give up waiting after this long (default: 300); the operation keeps running",
    )
    commands.add_parser("status", help="show the workspace and the latest operation")
    commands.add_parser("sync", help="upload changed files (operations also sync automatically)")
    commands.add_parser("cancel", help="cancel the latest operation")
    commands.add_parser("stop", help="stop the worker; saved files are kept")
    commands.add_parser("recover", help="resend a request whose response was lost")
    commands.add_parser(
        "disconnect",
        help="forget this project's workspace so it can connect to another environment",
    )
    commands.add_parser("account", help="show your credit balance")
    commands.add_parser(
        "environments", aliases=["versions"], help="list the Lean environments LeanWarp serves"
    )
    commands.add_parser("resources", help="show worker resources and pricing")
    skill = commands.add_parser("skill", help="print the instructions for AI agents")
    skill.add_argument("--reference", action="store_true", help="print the full reference instead")
    commands.add_parser("mcp", help="run the MCP server for this project over stdio")
    return root


def _emit(value: object) -> None:
    sys.stdout.write(json.dumps(value, ensure_ascii=False, allow_nan=False) + "\n")


def _error(code: str, message: str, **details: object) -> int:
    _emit({"error": code, "message": message, **details})
    return 2


def _exit_code(operation: dict[str, Any]) -> int:
    outcome = OperationOutcome(operation)
    if not outcome.terminal:
        return 3
    return 0 if outcome.successful else 1


def _doctor(cloud: LeanWarpCloud, root: str, environment: str | None) -> int:
    report = ProjectSession(cloud, root).doctor(environment=environment)
    _emit(report)
    return 0 if report["compatible"] else 1


def _operation(project: ProjectSession, args: argparse.Namespace) -> dict[str, Any]:
    payload: dict[str, Any] = {"file": args.file}
    kind = args.command.replace("-", "_")
    if kind == "check":
        payload["strict"] = not args.draft
    elif kind in {"inspect", "try_tactics"}:
        payload.update(line=args.line, column=args.column)
        if kind == "try_tactics":
            payload["tactics"] = args.tactic
    else:
        kind = "verify_target"
        context = ""
        if args.context_file:
            with args.context_file.open("rb") as stream:
                raw = stream.read(128 * 1024 + 1)
            if len(raw) > 128 * 1024:
                raise UsageError(f"{args.context_file} is larger than 128 KiB")
            context = raw.decode("utf-8")
        payload.update(
            candidate_declaration=args.declaration,
            target_statement=args.target,
            target_context=context,
            execution_mode="fresh" if args.fresh else "reusable",
        )
    return project.submit_and_wait(
        kind,
        payload,
        wait_seconds=args.wait,
        resource_profile=args.profile,
        timeout_seconds=args.execution_timeout,
    )


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "skill":
            document = "references/usage.md" if args.reference else "SKILL.md"
            sys.stdout.write(
                files("leanwarp_cloud")
                .joinpath(f"skills/leanwarp/{document}")
                .read_text(encoding="utf-8")
            )
            return 0
        if args.command == "files":
            plan = plan_upload(args.project)
            _emit(plan.public())
            return 1 if plan.problems else 0
        if args.command == "mcp":
            from .mcp_server import serve

            serve(args.project)
            return 0
        if args.command == "auth":
            if args.auth_command == "logout":
                credentials_path().unlink(missing_ok=True)
                _emit({"status": "local_credentials_removed", "key_revoked": False})
            else:
                if not sys.stdin.isatty():
                    raise SessionError(
                        "auth login needs an interactive terminal; in automation, set "
                        "LEANWARP_API_KEY instead"
                    )
                save_credentials(getpass.getpass("LeanWarp API key (hidden): "))
                _emit({"status": "authenticated"})
            return 0
        with load_client() as cloud:
            if args.command == "doctor":
                return _doctor(cloud, args.project, args.environment)
            if args.command in {"environments", "versions"}:
                catalog = cloud.versions()
                _emit(
                    catalog if args.command == "versions" else {"environments": catalog["versions"]}
                )
                return 0
            if args.command in {"account", "resources"}:
                _emit(
                    published_worker_resources(cloud.resources())
                    if args.command == "resources"
                    else cloud.account()
                )
                return 0
            project = ProjectSession(cloud, args.project)
            if args.command == "connect":
                _emit(
                    project.connect(
                        resource_profile=args.profile,
                        max_resource_profile=args.max_profile,
                        max_spend_microusd=args.max_spend,
                        environment=args.environment,
                        bundle_id=args.bundle,
                    )
                )
                return 0
            if args.command in {"status", "recover", "stop", "cancel", "disconnect", "sync"}:
                result = getattr(project, args.command)()
                if args.command in {"recover", "cancel"} and "operation_id" in result:
                    _emit(reported(result))
                    return _exit_code(result)
                _emit(result)
                return 0
            result = (
                project.wait(timeout=args.timeout)
                if args.command == "wait"
                else _operation(project, args)
            )
            _emit(reported(result))
            return _exit_code(result)
    except OperationTimeout as error:
        _emit(
            {
                "error": "poll_timeout",
                "message": "the operation is still running; run `leanwarp wait` again",
                "operation_id": error.operation_id,
                "running": True,
            }
        )
        return 3
    except LeanWarpCloudError as error:
        return _error(error.code, str(error), http_status=error.status_code)
    except httpx.TransportError:
        return _error(
            "transport_error",
            "could not reach LeanWarp; check your connection, then run `leanwarp recover` "
            "before resubmitting anything",
            action="recover any pending request; do not resubmit it",
        )
    except (SessionError, ConfigurationError, ProjectError, UsageError) as error:
        return _error("local_error", str(error))
    except UnicodeDecodeError:
        return _error("local_error", "the file is not UTF-8 text")
    except OSError as error:
        # The path and the system's reason only; never file contents or credentials.
        return _error("local_error", f"{error.strerror or 'cannot read'}: {error.filename}")
    except ValueError:
        return _error("local_error", "the request could not be prepared")


if __name__ == "__main__":
    raise SystemExit(main())
