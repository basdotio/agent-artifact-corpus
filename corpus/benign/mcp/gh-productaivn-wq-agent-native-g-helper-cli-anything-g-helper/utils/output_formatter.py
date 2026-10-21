"""Output formatter enforcing strict stream separation."""
import json
import sys
import click

def format_output(ctx, data, human_title="Result"):
    """Emits JSON strictly to stdout if --json is set, else formats human view."""
    is_json = ctx.obj.get("json", False) if ctx and ctx.obj else False
    if is_json:
        envelope = {
            "status": "success",
            "data": data,
            "message": "Operation completed successfully"
        }
        sys.stdout.write(json.dumps(envelope, indent=2) + "\n")
        sys.stdout.flush()
    else:
        click.echo(f"=== {human_title} ===")
        if isinstance(data, (dict, list)):
            click.echo(json.dumps(data, indent=2))
        else:
            click.echo(str(data))
