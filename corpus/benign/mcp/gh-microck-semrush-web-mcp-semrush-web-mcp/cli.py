"""Local browser lifecycle and stdio entry point."""

import argparse
import asyncio
import json
import os
import shlex
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path
from typing import get_args, get_origin

from patchright.sync_api import sync_playwright
from pydantic import ValidationError

from .server import REPORTS, BrowserError, BrowserSession, SemrushError, serve

CONFIG_DIR = Path.home() / ".config/semrush-web-mcp"
CONFIG_FILE = CONFIG_DIR / "config.json"
SERVICE = "semrush-web-browser.service"


def report_commands(commands):
    """Derive command flags from the same query models used for MCP discovery."""
    for name, report in REPORTS.items():
        command = commands.add_parser(name.replace("_", "-"), help=report.description)
        command.set_defaults(report=name, report_fields=tuple(report.query.model_fields))
        for field_name, field in report.query.model_fields.items():
            flag = "--" + field_name.replace("_", "-")
            options = {
                "dest": field_name,
                "default": argparse.SUPPRESS,
                "required": field.is_required(),
                "help": field.description,
            }
            annotation = field.annotation
            if type(None) in get_args(annotation):
                annotation = next(item for item in get_args(annotation) if item is not type(None))
            if annotation is bool:
                options["action"] = argparse.BooleanOptionalAction
            elif annotation is dict or get_origin(annotation) is list:
                options["type"] = json.loads
                options["metavar"] = "JSON"
            else:
                options["type"] = annotation
            command.add_argument(flag, **options)
        command.add_argument("--json", action="store_true", help="Emit compact JSON")
        command.add_argument("--cdp-url", help="Existing authenticated browser CDP URL")


async def run_report(args):
    # Query validation happens before config lookup or browser connection.
    arguments = {name: getattr(args, name) for name in args.report_fields if hasattr(args, name)}
    REPORTS[args.report].query.model_validate(arguments)
    settings = config() if args.cdp_url is None else None
    session = BrowserSession(args.cdp_url or f"http://127.0.0.1:{settings['port']}")
    try:
        result = await session.report(args.report, arguments)
        print(json.dumps(result, ensure_ascii=False, indent=None if args.json else 2))
    finally:
        await session.close()


def config():
    try:
        return json.loads(CONFIG_FILE.read_text())
    except FileNotFoundError:
        raise SystemExit("Run semrush-web-mcp setup first.") from None


def browser_command(settings, *, headed=False):
    command = [
        settings["executable"],
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-dev-shm-usage",
        "--remote-debugging-address=127.0.0.1",
        f"--remote-debugging-port={settings['port']}",
        f"--user-data-dir={settings['profile']}",
    ]
    if not headed:
        command.append("--headless=new")
    if settings.get("user_agent"):
        command.append(f"--user-agent={settings['user_agent']}")
    command.append("https://www.semrush.com/login/" if headed else "about:blank")
    return command


def setup(args):
    if sys.platform != "linux":
        raise SystemExit(
            "Managed browser setup requires Linux/systemd. Use serve --cdp-url elsewhere."
        )
    with sync_playwright() as playwright:
        executable = args.executable or playwright.chromium.executable_path
    if not Path(executable).is_file():
        raise SystemExit(
            "Browser missing. Run python -m patchright install chromium, or pass --executable."
        )
    profile = Path(args.profile).expanduser().resolve()
    profile.mkdir(parents=True, exist_ok=True, mode=0o700)
    profile.chmod(0o700)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    CONFIG_DIR.chmod(0o700)
    settings = {
        "profile": str(profile),
        "executable": str(Path(executable).resolve()),
        "port": args.port,
        "user_agent": os.environ.get("SEMRUSH_WEB_USER_AGENT"),
    }
    descriptor = os.open(CONFIG_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(settings, stream, indent=2)
    CONFIG_FILE.chmod(0o600)
    unit_dir = Path.home() / ".config/systemd/user"
    unit_dir.mkdir(parents=True, exist_ok=True)
    executable_path = shlex.quote(sys.executable)
    (unit_dir / SERVICE).write_text(
        "[Unit]\nDescription=Private browser for Semrush web MCP\n\n"
        "[Service]\nType=simple\n"
        f"ExecStart={executable_path} -m semrush_web_mcp.cli browser\n"
        "Restart=on-failure\nRestartSec=5\nUMask=0077\n\n"
        "[Install]\nWantedBy=default.target\n"
    )
    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", SERVICE], check=True)
    subprocess.run(["systemctl", "--user", "restart", SERVICE], check=True)
    print(f"Private Semrush browser started on localhost:{args.port}.")
    print("Run semrush-web-mcp login to sign in, then configure your MCP client.")


def main():
    parser = argparse.ArgumentParser(description="Authenticated Semrush browser MCP")
    parser.add_argument("--version", action="version", version=version("semrush-web-mcp"))
    commands = parser.add_subparsers(dest="command", required=True)
    listing = commands.add_parser("reports", help="List available operations and input schemas")
    listing.add_argument("--json", action="store_true", help="Emit the operation catalog as JSON")
    report_commands(commands)
    serving = commands.add_parser("serve", help="Run the stdio MCP server")
    serving.add_argument("--cdp-url", help="Existing authenticated browser CDP URL")
    installing = commands.add_parser(
        "setup", help="Install and start a private Linux browser service"
    )
    installing.add_argument("--profile", default=str(CONFIG_DIR / "browser-profile"))
    installing.add_argument("--executable", help="Chromium executable path")
    installing.add_argument(
        "--port", type=int, choices=range(1024, 65536), default=9234, metavar="PORT"
    )
    commands.add_parser("browser", help="Run the managed background browser")
    commands.add_parser("login", help="Open the private profile in a visible browser")
    args = parser.parse_args()
    if hasattr(args, "report"):
        try:
            asyncio.run(run_report(args))
        except ValidationError as error:
            parser.exit(2, f"Invalid query: {error}\n")
        except SemrushError as error:
            parser.exit(1, f"{error}\n")
        except (BrowserError, TimeoutError):
            parser.exit(
                1, "Semrush browser request failed. Check the browser service and reconnect.\n"
            )
        except KeyboardInterrupt:
            parser.exit(130, "Interrupted.\n")
    elif args.command == "reports":
        if args.json:
            print(
                json.dumps(
                    [
                        {
                            "name": name,
                            "description": report.description,
                            "input_schema": report.query.model_json_schema(),
                        }
                        for name, report in REPORTS.items()
                    ]
                )
            )
        else:
            for name, report in REPORTS.items():
                print(f"{name.replace('_', '-')}: {report.description}")
    elif args.command == "setup":
        setup(args)
    elif args.command == "serve":
        settings = config() if args.cdp_url is None else None
        asyncio.run(serve(args.cdp_url or f"http://127.0.0.1:{settings['port']}"))
    elif args.command == "browser":
        command = browser_command(config())
        os.execv(command[0], command)
    elif args.command == "login":
        if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
            raise SystemExit(
                "Login needs a graphical desktop. Connect to the browser over local CDP instead."
            )
        settings = config()
        subprocess.run(["systemctl", "--user", "stop", SERVICE], check=True)
        try:
            subprocess.run(browser_command(settings, headed=True), check=True)
        finally:
            subprocess.run(["systemctl", "--user", "start", SERVICE], check=True)


if __name__ == "__main__":
    main()
