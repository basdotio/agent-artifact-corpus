"""Command line interface for Integrum."""

import sys
from typing import List, Optional
import click

from integrum.filter import MemberFilter
from integrum.inspector import import_target, inspect_class, inspect_function, inspect_module
from integrum.server import IntegrumServer


@click.group()
@click.version_option()
def main() -> None:
    """Integrum: Expose Python modules as Model Context Protocol (MCP) servers."""
    pass


@main.command("expose")
@click.argument("targets", nargs=-1, required=True)
@click.option("--name", default="integrum-server", help="Name of the MCP server.")
@click.option("--include", "-i", multiple=True, help="Regex pattern(s) to include.")
@click.option("--exclude", "-e", multiple=True, help="Regex pattern(s) to exclude.")
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "http", "sse"], case_sensitive=False),
    default="stdio",
    help="MCP transport protocol (default: stdio).",
)
@click.option("--host", default="127.0.0.1", help="Host to bind for HTTP/SSE (default: 127.0.0.1).")
@click.option("--port", "-p", default=8000, type=int, help="Port to bind for HTTP/SSE (default: 8000).")
def expose_cmd(
    targets: List[str],
    name: str,
    include: List[str],
    exclude: List[str],
    transport: str,
    host: str,
    port: int,
) -> None:
    """Expose TARGETS (modules, classes, or functions) as an MCP server."""
    server = IntegrumServer(name=name)
    inc_list = list(include) if include else None
    exc_list = list(exclude) if exclude else None

    try:
        registered = server.expose(list(targets), include=inc_list, exclude=exc_list)
        if not registered:
            click.echo("Warning: No tools were registered. Check your targets or filter patterns.", err=True)
        else:
            click.echo(f"Successfully registered {len(registered)} tools: {', '.join(registered)}", err=True)

        click.echo(f"Starting Integrum MCP server '{name}' via transport={transport}...", err=True)
        server.run(transport=transport, host=host, port=port)
    except Exception as e:
        click.echo(f"Error starting Integrum server: {e}", err=True)
        sys.exit(1)


@main.command("list")
@click.argument("targets", nargs=-1, required=True)
@click.option("--include", "-i", multiple=True, help="Regex pattern(s) to include.")
@click.option("--exclude", "-e", multiple=True, help="Regex pattern(s) to exclude.")
def list_cmd(targets: List[str], include: List[str], exclude: List[str]) -> None:
    """Preview the functions and classes that would be exposed from TARGETS."""
    inc_list = list(include) if include else None
    exc_list = list(exclude) if exclude else None
    member_filter = MemberFilter(include=inc_list, exclude=exc_list) if (inc_list or exc_list) else None

    for target_str in targets:
        try:
            obj = import_target(target_str)
        except Exception as e:
            click.echo(f"Error importing '{target_str}': {e}", err=True)
            continue

        click.echo(f"\nTarget: {target_str} ({type(obj).__name__})")
        click.echo("-" * 40)

        import inspect
        if inspect.isfunction(obj) or inspect.isbuiltin(obj):
            fn_info = inspect_function(obj)
            click.echo(f"  [Function] {fn_info.name}{fn_info.signature}")
            if fn_info.docstring:
                first_line = fn_info.docstring.strip().split("\n")[0]
                click.echo(f"             Doc: {first_line}")
        elif inspect.isclass(obj):
            cls_info = inspect_class(obj, member_filter=member_filter)
            click.echo(f"  [Class] {cls_info.name}")
            click.echo(f"    Constructor: {cls_info.name}_create{cls_info.init_signature}")
            for m_name, m_info in cls_info.methods.items():
                click.echo(f"    Method: {cls_info.name}_{m_name}{m_info.signature}")
        elif inspect.ismodule(obj):
            mod_info = inspect_module(obj, member_filter=member_filter)
            if mod_info.functions:
                click.echo("  Functions:")
                for fn_name, fn_info in mod_info.functions.items():
                    click.echo(f"    - {fn_name}{fn_info.signature}")
            if mod_info.classes:
                click.echo("  Classes:")
                for c_name, c_info in mod_info.classes.items():
                    click.echo(f"    - {c_name} ({len(c_info.methods)} methods)")
                    for m_name in c_info.methods:
                        click.echo(f"        * {c_name}_{m_name}")


if __name__ == "__main__":
    main()
