"""Interactive REPL skin for human operators."""
import sys
import shlex
import click

def start_repl(ctx):
    click.echo("╔══════════════════════════════════════════╗")
    click.echo("║       cli-anything-g_helper v1.0.0      ║")
    click.echo("║     Agent-Native Harness for g_helper    ║")
    click.echo("╚══════════════════════════════════════════╝")
    click.echo("Type commands or 'exit' / 'quit' to close.\n")

    while True:
        try:
            line = input("g_helper> ").strip()
            if not line:
                continue
            if line.lower() in ["exit", "quit"]:
                click.echo("Goodbye! 👋")
                sys.exit(0)
            args = shlex.split(line)
            try:
                ctx.command.main(args=args, prog_name="cli-anything-g_helper", standalone_mode=False)
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
        except (KeyboardInterrupt, EOFError):
            click.echo("\nGoodbye! 👋")
            break
