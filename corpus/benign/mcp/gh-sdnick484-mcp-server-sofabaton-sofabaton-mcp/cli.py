"""Entry point: `mcp-server-sofabaton [serve|check|doctor|simulate]`.

serve     speak MCP: stdio by default, or --http for a long-lived service behind
          Cloudflare Access (remote.py). --dry-run reads the hub but sends nothing
          that changes anything.
check     first contact: pick the hub the way the server will, print its model,
          what it can do here, and the names the model will use.
call      call one tool exactly as the model would (through an in-process MCP
          client, so argument validation is the same) and print the result:
          `call start_activity activity="Watch Shield"`, `call tools` to list.
doctor    check each way to the hub, layer by layer (doctor.py).
simulate  a fake hub with no hardware: a fake sofabaton-x-server (REST), and for
          an X2 a fake MQTT broker and the X2's MQTT side, sharing one state.
          Type commands at its prompt to act like the physical remote.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import json
import logging
import os
import sys
from pathlib import Path

from . import __version__, remote
from .api import ServerAPI, SofabatonError
from .client import SofabatonClient
from .config import load_settings
from .logsafe import setup_logging


def _setup_logging(args: argparse.Namespace, default: int = logging.INFO) -> None:
    level = logging.DEBUG if getattr(args, "verbose", 0) else default
    unredacted = getattr(args, "no_redact", False) or os.environ.get("SOFABATON_LOG_UNREDACTED") in ("1", "true")
    setup_logging(level, redacted=not unredacted)


async def _cmd_check() -> int:
    settings = load_settings()
    for p in settings.problems:
        print(f"Config: {p}", file=sys.stderr)
    c = SofabatonClient(settings, ServerAPI(settings.url) if settings.url else None)
    await c.start()
    try:
        if settings.mqtt is not None:
            # Give MQTT a moment to connect (up to 3 s), so the status reflects it.
            for _ in range(60):
                if c.mqtt is not None and (c.mqtt.connected or c.mqtt.auth_failed):
                    break
                await asyncio.sleep(0.05)
        st = await c.status()
        print(f"Hub: {st['hub_name'] or 'name unknown'} ({st['model'] or 'model unknown'})")
        print(f"Commands go via: {st['via'] or 'nothing right now'}")
        print(f"Running: {st['running_activity'] or 'nothing'}")
        print(f"Can: {', '.join(st['capabilities']) or 'nothing yet'}")
        for lim in st["limitations"]:
            print(f"Note: {lim}")
        print("Activities:")
        for name, on in await c.activities():
            print(f"  {name}{'  (running)' if on else ''}")
        print("Devices:")
        for name, brand, cls in await c.devices():
            print(f"  {name}  [{brand or '?'} {cls or ''}]")
    except SofabatonError as exc:
        print(exc, file=sys.stderr)
        return 1
    finally:
        await c.stop()
    return 0


async def _cmd_doctor(args: argparse.Namespace) -> int:
    from .doctor import render, run_doctor, to_json

    report = await run_doctor(
        load_settings(), timeout=args.timeout, dump_dir=Path(args.dump) if args.dump else None, listen_s=args.listen
    )
    print(to_json(report) if args.json else render(report))
    return 0 if report.ok else 1


async def _cmd_call(args: argparse.Namespace) -> int:
    from mcp import Client

    from .server import mcp

    tool_args: dict[str, object] = {}
    for pair in args.args:
        key, sep, raw = pair.partition("=")
        if not sep:
            print(f"arguments are key=value, got {pair!r}", file=sys.stderr)
            return 2
        try:
            tool_args[key] = json.loads(raw)  # repeat=3 -> 3, target=null -> None
        except json.JSONDecodeError:
            tool_args[key] = raw  # activity=Watch Shield -> a string
    async with Client(mcp) as c:
        if args.tool == "tools":
            for t in (await c.list_tools()).tools:
                print(f"{t.name:<20} {(t.description or '').splitlines()[0]}")
            return 0
        result = await c.call_tool(args.tool, tool_args)
    if result.is_error:
        print(" ".join(getattr(part, "text", "") for part in result.content) or "error", file=sys.stderr)
        return 1
    body = result.structured_content
    if isinstance(body, dict) and set(body) == {"result"}:
        body = body["result"]
    print(json.dumps(body, indent=2))
    return 0


# --- simulate -------------------------------------------------------------------------------
SIM_HELP = """Commands (act like the physical remote, or change the scene):
  off                  press OFF on the remote (everything off; X2 publishes 255)
  start <name>         start an activity as if from the remote
  key <device> <cmd>   press a Wifi-Device key (X2 publishes <MAC>/up), e.g. key 3 1
  app on|off           the Sofabaton app opens/closes (server goes to observe/control)
  hub on|off           the server loses/regains its hub session
  state                show what the fake hub thinks
  help, quit"""


async def _cmd_simulate(args: argparse.Namespace, ready: asyncio.Event | None = None) -> int:
    import uvicorn

    from .sim.fake_server import FakeServer
    from .sim.hub_state import load_state

    state = load_state(model=args.model, mqtt_id_offset=args.mqtt_id_offset)
    with_server = not args.no_server
    with_mqtt = args.model == "X2" and not args.no_mqtt
    if not with_server and not with_mqtt:
        print("Nothing to simulate: an X1/X1S needs the server (no MQTT on those models).", file=sys.stderr)
        return 2
    env: dict[str, str] = {}
    tasks: list[asyncio.Task[None]] = []
    fake_server = None
    stoppers = []
    if with_server:
        fake_server = FakeServer(state, host="127.0.0.1")
        fake_server.settle_reads = args.settle_reads
        server = uvicorn.Server(uvicorn.Config(fake_server.app, host="127.0.0.1", port=args.port, log_level="warning"))
        tasks.append(asyncio.create_task(server.serve()))
        while not server.started:
            await asyncio.sleep(0.05)
        env["SOFABATON_URL"] = f"http://127.0.0.1:{args.port}"

        async def stop_server() -> None:
            server.should_exit = True

        stoppers.append(stop_server)
    else:
        env["SOFABATON_URL"] = "none"
    if with_mqtt:
        try:
            from .sim.broker import Broker
            from .sim.fake_x2 import FakeX2
        except ImportError:
            print("The X2's MQTT side needs aiomqtt: pip install 'mcp-server-sofabaton[mqtt]'", file=sys.stderr)
            return 2
        host, port = "127.0.0.1", args.mqtt_port
        if args.broker:
            from urllib.parse import urlparse

            u = urlparse(args.broker)
            host, port = u.hostname or "127.0.0.1", u.port or 1883
        else:
            broker = Broker(port=port)
            await broker.start()
            stoppers.append(broker.stop)
        x2 = FakeX2(state, host, port)
        await x2.start()
        stoppers.insert(0, x2.stop)
        env["SOFABATON_MQTT_URL"] = f"mqtt://{host}:{port}"
        env["SOFABATON_MQTT_MAC"] = state.mac
    lines = [f"export {k}={v}" for k, v in env.items()]
    if args.write_env:
        Path(args.write_env).write_text("\n".join(lines) + "\n")
    print(f"Fake Sofabaton {state.model} '{state.name}' running (hand-built protocol; see assumptions.py):")
    print("  REST (fake sofabaton-x-server): " + (env["SOFABATON_URL"] if with_server else "off"))
    print("  MQTT (fake broker + X2):        " + (env.get("SOFABATON_MQTT_URL", "off")))
    print("\nIn another terminal:\n  " + "\n  ".join(lines) + "\n  mcp-server-sofabaton doctor\n")
    print(SIM_HELP)
    sys.stdout.flush()
    if ready is not None:
        ready.set()
    try:
        if args.no_prompt:
            await asyncio.Event().wait()
        while True:
            try:
                line = (await asyncio.to_thread(input, "sim> ")).strip()
            except EOFError:
                await asyncio.Event().wait()  # stdin closed (e.g. backgrounded): just keep serving
            words = line.split()
            if not words:
                continue
            cmd = words[0].lower()
            if cmd in ("quit", "exit"):
                break
            if cmd == "off":
                state.press_remote_off()
            elif cmd == "start" and len(words) > 1:
                wanted = " ".join(words[1:]).lower()
                hit = next((a for a in state.activities if a.name.lower() == wanted), None)
                if hit is not None:
                    state.set_running(hit.activity_id)
                else:
                    print("unknown activity")
            elif cmd == "key" and len(words) == 3:
                state.press_virtual_key(int(words[1]), int(words[2]))
                if fake_server is not None:  # the server's press log sees it too (as an HTTP Wifi Device would)
                    fake_server.presses.append(
                        {
                            "seq": len(fake_server.presses) + 1,
                            "hub_id": fake_server.hub_id,
                            "device_id": int(words[1]),
                            "command_id": int(words[2]),
                            "slot": None,
                            "label": None,
                            "press_type": "short",
                            "resolution": "resolved",
                            "transport": "http",
                            "source": "127.0.0.1",
                            "received_at": "now",
                        }
                    )
            elif cmd == "app" and len(words) == 2 and fake_server is not None:
                fake_server.mode = "observe" if words[1] == "on" else "control"
            elif cmd == "hub" and len(words) == 2 and fake_server is not None:
                fake_server.hub_connected = words[1] == "on"
                fake_server.mode = "control" if fake_server.hub_connected else "disconnected"
            elif cmd == "state":
                running = state.activity(state.running) if state.running is not None else None
                mode = fake_server.mode if fake_server else "n/a"
                print(f"running: {running.name if running else 'nothing'}; server mode: {mode}")
                for e in state.executed[-10:]:
                    print(f"  {e}")
            else:
                print(SIM_HELP)
    finally:
        for stop in stoppers:
            with contextlib.suppress(Exception):
                await stop()
        for t in tasks:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(t, 5)
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mcp-server-sofabaton",
        description="MCP server for Sofabaton X1/X1S/X2 (sofabaton-x-server and/or X2 MQTT)",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("-v", "--verbose", action="count", default=0, help="debug logging")
    common.add_argument(
        "--no-redact",
        action="store_true",
        help="don't mask IPs and MACs in logs; secrets stay masked (SOFABATON_LOG_UNREDACTED=1)",
    )
    sub = parser.add_subparsers(dest="cmd")
    serve = sub.add_parser("serve", parents=[common], help="Run the MCP server (stdio by default, or --http)")
    serve.add_argument("--dry-run", action="store_true", help="read the hub but send nothing that changes anything")
    remote.add_http_arguments(serve, default_port=8714, default_path="/sofabaton/mcp")
    sub.add_parser("check", parents=[common], help="Pick the hub, show its model, capabilities and names")
    call = sub.add_parser("call", parents=[common], help="Call one tool as the model would and print the result")
    call.add_argument("tool", help="tool name, or 'tools' to list them")
    call.add_argument("args", nargs="*", metavar="key=value", help="tool arguments (values are JSON if they parse)")
    call.add_argument("--dry-run", action="store_true", help="send nothing that changes anything")
    doc = sub.add_parser("doctor", parents=[common], help="Check sofabaton-x-server and/or MQTT, layer by layer")
    doc.add_argument("--json", action="store_true")
    doc.add_argument("--dump", metavar="DIR", help="also write what the hub returns to DIR (redacted)")
    doc.add_argument("--timeout", type=float, default=5.0, help="seconds per step (default 5)")
    doc.add_argument("--listen", type=float, default=0.0, metavar="SECONDS", help="print MQTT traffic for SECONDS")
    sim = sub.add_parser("simulate", parents=[common], help="Run a fake hub (REST, and MQTT for an X2) locally")
    sim.add_argument("--model", choices=["X1", "X1S", "X2"], default="X2")
    sim.add_argument("--port", type=int, default=8480, help="fake sofabaton-x-server port")
    sim.add_argument("--mqtt-port", type=int, default=1883, help="port for the in-package broker")
    sim.add_argument(
        "--broker", metavar="URL", help="use this broker instead (e.g. mqtt://localhost:1883 for mosquitto)"
    )
    sim.add_argument("--no-server", action="store_true", help="X2 over MQTT only")
    sim.add_argument("--no-mqtt", action="store_true", help="REST only")
    sim.add_argument("--settle-reads", type=int, default=3, help="GET /activity reads before a change shows over REST")
    sim.add_argument("--mqtt-id-offset", type=int, default=0, help="give MQTT different ids than REST (S-MQTT-IDS)")
    sim.add_argument("--write-env", metavar="FILE", help="write the export lines to FILE")
    sim.add_argument("--no-prompt", action="store_true", help="don't read commands from stdin")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.cmd in ("check", "call", "doctor", "simulate"):
        _setup_logging(args, default=logging.WARNING)
        if getattr(args, "dry_run", False):
            os.environ["SOFABATON_DRY_RUN"] = "1"
        with contextlib.suppress(KeyboardInterrupt):
            if args.cmd == "check":
                sys.exit(asyncio.run(_cmd_check()))
            if args.cmd == "call":
                sys.exit(asyncio.run(_cmd_call(args)))
            if args.cmd == "doctor":
                sys.exit(asyncio.run(_cmd_doctor(args)))
            sys.exit(asyncio.run(_cmd_simulate(args)))
        sys.exit(130)

    _setup_logging(args)
    if getattr(args, "dry_run", False):
        os.environ["SOFABATON_DRY_RUN"] = "1"  # read by load_settings in the server's lifespan
    from .server import mcp  # imported late: the other commands don't need the server code

    if getattr(args, "http", False):
        try:
            remote.serve_http(mcp, remote.http_config(args))
        except remote.ConfigError as exc:
            parser.exit(2, f"mcp-server-sofabaton: {exc}\n")
    else:
        mcp.run()  # stdio: JSON-RPC over stdin/stdout
