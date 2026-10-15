"""
Command-Line Interface for Preflight.
Provides interactive verification with Rich terminal formatting,
server launch, and fixture management.
"""

import sys
import json
import asyncio
import argparse
from typing import Optional
from pathlib import Path

# Ensure UTF-8 output encoding across platforms (especially Windows consoles)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.syntax import Syntax
from rich import box

from preflight import __version__
from preflight.server import verify_claim, quick_check, mcp
from preflight.search_client import FIXTURES_DIR, SerpApiSearchClient


console = Console(highlight=False)


def display_verdict_rich(verdict_data: dict) -> None:
    """Format and print a PreflightVerdict dictionary with Rich UI components."""
    status = verdict_data.get("verdict", "UNVERIFIABLE")
    confidence = verdict_data.get("confidence", 0.0)
    summary = verdict_data.get("summary", "")
    canonical = verdict_data.get("canonical_reference")
    correction = verdict_data.get("correction")
    suggested_action = verdict_data.get("suggested_action")
    evidence = verdict_data.get("top_evidence", [])
    queries = verdict_data.get("queries_executed", [])
    response_time_ms = verdict_data.get("response_time_ms", 0)
    is_replayed = verdict_data.get("is_replayed", False)

    # 1. Header Banner
    console.print()
    badge = "[bold cyan]Preflight[/bold cyan] [dim]v" + __version__ + "[/dim]"
    mode_text = "[bold magenta][REPLAY FIXTURE][/bold magenta]" if is_replayed else "[bold green][LIVE SERPAPI][/bold green]"
    console.print(Panel(
        f"[bold white]Claim Verification Report[/bold white]\n[dim]Claim:[/dim] {verdict_data.get('claim')}",
        title=f"{badge} * {mode_text}",
        border_style="cyan" if not is_replayed else "magenta",
        padding=(0, 1),
    ))

    # 2. Formulated Search Vectors
    if queries:
        console.print(f"[bold dim][*] Formulated Search Vectors ({len(queries)}):[/bold dim]")
        for q in queries:
            console.print(f"  * [cyan]{q}[/cyan]")
        console.print()

    # 3. Evidence Table
    if evidence:
        table = Table(
            title="Collected SerpApi Evidence",
            box=box.ROUNDED,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("#", justify="center", width=3)
        table.add_column("Tier", justify="center", width=8)
        table.add_column("Source / Title", style="bold", ratio=2)
        table.add_column("Score", justify="right", width=7)
        table.add_column("Key Signals / Excerpt", ratio=3)

        for i, item in enumerate(evidence, 1):
            tier = item.get("trust_tier", 3)
            if tier == 1:
                tier_badge = "[bold green]Tier 1[/bold green]"
            elif tier == 2:
                tier_badge = "[bold yellow]Tier 2[/bold yellow]"
            else:
                tier_badge = "[dim]Tier 3[/dim]"

            score = item.get("trust_score", 0.0)
            score_text = f"{score:.2f}"
            if score >= 0.7:
                score_str = f"[green]{score_text}[/green]"
            elif score >= 0.4:
                score_str = f"[yellow]{score_text}[/yellow]"
            else:
                score_str = f"[dim]{score_text}[/dim]"

            domain = item.get("domain", "")
            title = item.get("title", "")
            source_cell = f"{title}\n[dim underline]{domain}[/dim underline]"

            snippet = item.get("snippet", "")
            signals = item.get("signals", [])
            signal_tags = " ".join([f"[reverse red]{s}[/reverse red]" if "deprecation" in s or "removed" in s else f"[reverse green]{s}[/reverse green]" for s in signals])
            excerpt = f"{signal_tags}\n[italic dim]{snippet[:140]}...[/italic dim]" if snippet else signal_tags

            table.add_row(str(i), tier_badge, source_cell, score_str, excerpt)

        console.print(table)
        console.print()

    # 4. Final Verdict Panel
    if status == "CONFIRMED":
        v_color = "green"
        v_title = f"[bold green][OK] CONFIRMED ({confidence * 100:.0f}% confidence)[/bold green]"
    elif status == "OUTDATED":
        v_color = "red"
        v_title = f"[bold red][X] OUTDATED / DEPRECATED ({confidence * 100:.0f}% confidence)[/bold red]"
    elif status == "CONFLICTING":
        v_color = "yellow"
        v_title = f"[bold yellow][!] CONFLICTING SOURCES ({confidence * 100:.0f}% confidence)[/bold yellow]"
    else:
        v_color = "blue"
        v_title = f"[bold blue][?] UNVERIFIABLE ({confidence * 100:.0f}% confidence)[/bold blue]"

    verdict_content = [f"[bold]{summary}[/bold]"]

    if suggested_action:
        verdict_content.append(f"\n[bold yellow]Action:[/bold yellow] {suggested_action}")

    if canonical:
        verdict_content.append(f"\n[bold cyan]Canonical Documentation:[/bold cyan] {canonical}")

    if correction:
        verdict_content.append(f"\n[bold green]Recommended Correction:[/bold green] [bold white]{correction}[/bold white]")

    panel_text = "\n".join(verdict_content)
    console.print(Panel(
        panel_text,
        title=v_title,
        border_style=v_color,
        padding=(1, 2),
    ))

    console.print(f"[dim]Verified in {response_time_ms}ms[/dim]\n")


def cmd_verify(args: argparse.Namespace) -> None:
    """Execute claim verification."""
    result_json = asyncio.run(
        verify_claim(
            claim=args.claim,
            ecosystem=args.ecosystem,
            target_package=args.package,
            replay=args.replay,
            serpapi_key=args.serpapi_key,
        )
    )

    if args.json:
        print(result_json)
        return

    verdict_data = json.loads(result_json)
    display_verdict_rich(verdict_data)


def cmd_quick_check(args: argparse.Namespace) -> None:
    """Execute shorthand symbol verification."""
    result_json = asyncio.run(
        quick_check(
            package=args.package,
            symbol=args.symbol,
            version=args.version,
            replay=args.replay,
            serpapi_key=args.serpapi_key,
        )
    )

    if args.json:
        print(result_json)
        return

    data = json.loads(result_json)
    status = data.get("status", "UNVERIFIABLE")
    color = "green" if status == "CONFIRMED" else ("red" if status == "OUTDATED" else "yellow")
    console.print()
    console.print(Panel(
        f"[bold]Package:[/bold] {data.get('package')}\n"
        f"[bold]Symbol:[/bold] {data.get('symbol')}\n"
        f"[bold]Status:[/bold] [{color}]{status}[/{color}]\n"
        f"[bold]Reference:[/bold] {data.get('latest_reference') or 'None'}\n"
        f"[bold]Details:[/bold] {data.get('note')}",
        title=f"[bold cyan]Preflight Quick Check[/bold cyan]",
        border_style=color,
    ))
    console.print()


def cmd_fixtures(args: argparse.Namespace) -> None:
    """List available real recorded SerpApi replay fixtures."""
    fixtures = list(FIXTURES_DIR.glob("*.json"))
    console.print(Panel(
        f"[bold white]Preflight Replay Fixtures[/bold white]\n"
        f"Location: [dim]{FIXTURES_DIR}[/dim]\n"
        f"These fixtures contain [bold green]real SerpApi search responses[/bold green] recorded during development "
        f"to allow offline testing and judge evaluations without expending live credits.",
        title="[REPLAY FIXTURES]",
        border_style="magenta",
    ))
    table = Table(box=box.ROUNDED)
    table.add_column("Fixture Name", style="cyan")
    table.add_column("Size", justify="right")
    table.add_column("Description")

    descriptions = {
        "pydantic_v2_replay.json": "Pydantic v2 BaseSettings moved to pydantic-settings",
        "nextjs_15_replay.json": "Next.js 15 page/layout props params is an async Promise",
        "requests_verify_replay.json": "Requests session.verify=False SSL verification parameter",
        "react_19_forwardref_replay.json": "React 19 forwardRef deprecated in favor of ref prop",
    }

    for f in fixtures:
        size = f"{f.stat().st_size / 1024:.1f} KB"
        desc = descriptions.get(f.name, "Recorded SerpApi Query")
        table.add_row(f.name, size, desc)

    console.print(table)
    console.print("\n[dim]Usage: preflight verify \"<claim>\" --replay[/dim]\n")


def cmd_serve(args: argparse.Namespace) -> None:
    """Start the FastMCP stdio or SSE server."""
    if args.serpapi_key:
        os.environ["SERPAPI_API_KEY"] = args.serpapi_key
    # Informational logs go to stderr so stdout remains purely JSON-RPC for MCP clients
    err_console = Console(stderr=True, highlight=False)
    err_console.print(f"[bold cyan]Starting Preflight MCP Server[/bold cyan] [dim]v{__version__}[/dim]...")
    err_console.print("[dim]Transport: stdio (Model Context Protocol)[/dim]")
    # Run server via FastMCP
    mcp.run(transport="stdio")


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize Preflight MCP configuration in target AI coding client(s)."""
    from preflight.client_installer import (
        install_client,
        SUPPORTED_CLIENTS,
        ClientConfigConflictError,
    )

    targets = SUPPORTED_CLIENTS if args.client == "all" else [args.client]
    console.print()
    console.print(Panel(
        f"[bold white]Preflight MCP Client Setup[/bold white]\n"
        f"Configuring Preflight server for: [bold cyan]{', '.join(targets)}[/bold cyan]",
        title="[bold green]Zero-Friction Client Integration[/bold green]",
        border_style="cyan",
        padding=(0, 1),
    ))

    successes = 0
    for client in targets:
        try:
            res = install_client(
                client=client,
                is_global=args.is_global,
                project_dir=args.project_dir,
                force=args.force,
            )
            action_badge = f"[bold green][{res.action}][/bold green]"
            console.print(f"  {action_badge} [bold]{res.client}[/bold]: {res.config_path}")
            console.print(f"          [dim]Command:[/dim] [cyan]{res.command} {' '.join(res.args)}[/cyan]")
            successes += 1
        except ClientConfigConflictError:
            console.print(f"  [bold yellow][EXISTS][/bold yellow] [bold]{client}[/bold]: 'preflight' already configured. Use [cyan]--force[/cyan] to overwrite.")
        except Exception as e:
            console.print(f"  [bold red][ERROR][/bold red] [bold]{client}[/bold]: {e}")

    console.print()
    if successes > 0:
        console.print("[bold green]Success![/bold green] Restart or reload your AI client to start verifying claims.")
        console.print("[dim]Note: Ensure SERPAPI_API_KEY is configured in your environment or .env file for live search.[/dim]\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="preflight",
        description="Preflight: Authoritative Real-Time Grounding Engine for AI Coding Agents",
    )
    parser.add_argument("--version", action="version", version=f"preflight {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # verify
    verify_p = subparsers.add_parser("verify", help="Verify a code or API claim")
    verify_p.add_argument("claim", type=str, help="Claim to verify (e.g. 'In Pydantic v2 BaseSettings is in pydantic')")
    verify_p.add_argument("--ecosystem", "-e", type=str, choices=["python", "javascript", "typescript", "rust", "go", "general"], help="Ecosystem hint")
    verify_p.add_argument("--package", "-p", type=str, help="Target package name hint")
    verify_p.add_argument("--replay", "-r", action="store_true", help="Use recorded real SerpApi responses (no API key needed)")
    verify_p.add_argument("--serpapi-key", "-k", type=str, help="Explicit SerpApi API key (overrides SERPAPI_API_KEY env)")
    verify_p.add_argument("--json", action="store_true", help="Output raw JSON verdict")
    verify_p.set_defaults(func=cmd_verify)

    # quick-check
    qc_p = subparsers.add_parser("quick-check", help="Lightweight symbol status check")
    qc_p.add_argument("package", type=str, help="Package name")
    qc_p.add_argument("symbol", type=str, help="Symbol / function / class name")
    qc_p.add_argument("--version-num", "-v", dest="version", type=str, help="Version string")
    qc_p.add_argument("--replay", "-r", action="store_true", help="Use recorded real SerpApi responses")
    qc_p.add_argument("--serpapi-key", "-k", type=str, help="Explicit SerpApi API key")
    qc_p.add_argument("--json", action="store_true", help="Output raw JSON")
    qc_p.set_defaults(func=cmd_quick_check)

    # fixtures
    fix_p = subparsers.add_parser("fixtures", help="List bundled real SerpApi replay fixtures")
    fix_p.set_defaults(func=cmd_fixtures)

    # serve
    serve_p = subparsers.add_parser("serve", help="Run the FastMCP server for agents")
    serve_p.add_argument("--transport", default="stdio", choices=["stdio"], help="MCP transport protocol")
    serve_p.add_argument("--serpapi-key", "-k", type=str, help="Explicit SerpApi API key")
    serve_p.set_defaults(func=cmd_serve)

    # init
    init_p = subparsers.add_parser("init", help="Configure Preflight MCP server in an AI coding client")
    init_p.add_argument(
        "--client", "-c",
        choices=["claude-code", "claude-desktop", "cursor", "opencode", "all"],
        default="all",
        help="Target AI client to configure (default: all)",
    )
    init_p.add_argument(
        "--global", "-g",
        dest="is_global",
        action="store_true",
        help="Target global user configuration rather than project-level (where applicable)",
    )
    init_p.add_argument(
        "--force", "-f",
        action="store_true",
        help="Overwrite existing preflight MCP configuration if present",
    )
    init_p.add_argument(
        "--project-dir", "-d",
        type=Path,
        default=None,
        help="Target project directory (defaults to current working directory)",
    )
    init_p.set_defaults(func=cmd_init)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)


if __name__ == "__main__":
    main()
