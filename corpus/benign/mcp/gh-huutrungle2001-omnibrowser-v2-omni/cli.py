import argparse
import os
import sys

from . import __version__
from .cdp import connect, endpoint, http_url
from .errors import OmniError, invalid
from .models import serialize


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default message may echo unknown arguments / filled secrets.
        raise invalid("Invalid arguments; run --help for usage.")


def parser():
    p = Parser(description="Minimal local Chrome CLI", allow_abbrev=False)
    p.add_argument("--version", action="version", version=__version__)
    actions = p.add_mutually_exclusive_group(required=True)
    actions.add_argument("--list-tabs", action="store_true")
    actions.add_argument("--goto", metavar="URL")
    actions.add_argument("--observe", action="store_true")
    actions.add_argument("--act", action="store_true")
    actions.add_argument("--download", action="store_true")
    actions.add_argument("--screenshot", action="store_true")
    actions.add_argument("--scroll", action="store_true")
    p.add_argument("--cdp-url", default=os.environ.get("OMNI_CDP_URL", "http://127.0.0.1:17082"))
    p.add_argument("--timeout", type=int, metavar="MS")
    p.add_argument("--pretty", action="store_true")
    p.add_argument("--tab")
    p.add_argument("--new-tab", action="store_true")
    p.add_argument("--ref")
    p.add_argument("--action", choices=("click", "fill", "press", "select"))
    p.add_argument("--value")
    p.add_argument("--key")
    p.add_argument("--label")
    p.add_argument("--url")
    p.add_argument("--output")
    p.add_argument("--mkdir", action="store_true")
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("--max-bytes", type=int)
    p.add_argument("--cursor")
    p.add_argument("--full-page", action="store_true")
    p.add_argument("--direction", choices=("up", "down"))
    p.add_argument("--amount", type=int)
    return p


def validate(a, mcp=False):
    a.cdp_url = endpoint(a.cdp_url)
    if a.new_tab and (a.goto is None or a.tab):
        raise invalid("--new-tab requires --goto and cannot be combined with --tab.")
    if not a.list_tabs and not (a.goto is not None and a.new_tab) and not a.tab:
        raise invalid("--tab is required.")
    if a.list_tabs and a.tab:
        raise invalid("--list-tabs does not accept --tab.")
    if a.goto is not None:
        http_url(a.goto)
    if a.act:
        if not a.ref or not a.action:
            raise invalid("--act requires --ref and --action.")
        if a.action == "fill" and a.value is None or a.action not in {"fill", "select"} and a.value is not None:
            raise invalid("fill requires --value; only fill/select accept --value.")
        if a.action == "press" and not a.key or a.action != "press" and a.key is not None:
            raise invalid("press requires --key and other actions reject --key.")
        if a.action == "select" and ((a.value is None) == (a.label is None)):
            raise invalid("select requires exactly one of --value or --label.")
        if a.action != "select" and a.label is not None:
            raise invalid("--label is only valid for select.")
    elif any(v is not None for v in (a.ref, a.action, a.value, a.key, a.label)):
        raise invalid("Action options require --act.")
    if a.download:
        if not a.url or not a.output:
            raise invalid("--download requires --url and --output.")
        http_url(a.url)
        from .commands.download import destination
        destination(a.output, a.mkdir, a.overwrite)
    elif a.url is not None:
        raise invalid("Download options require --download.")
    if not (a.download or a.screenshot) and (a.output is not None or a.mkdir or a.overwrite):
        raise invalid("File output options require --download or --screenshot.")
    if a.max_bytes is not None and not (a.observe or a.download):
        raise invalid("--max-bytes requires --observe or --download.")
    if a.cursor is not None and not a.observe:
        raise invalid("--cursor requires --observe.")
    if a.observe:
        a.max_bytes = 15360 if a.max_bytes is None else a.max_bytes
        if not 2048 <= a.max_bytes <= 65536:
            raise invalid("Observe --max-bytes must be in 2048..65536.")
    if a.download:
        a.max_bytes = 512 * 1024 * 1024 if a.max_bytes is None else a.max_bytes
        if a.max_bytes <= 0:
            raise invalid("Download --max-bytes must be positive.")
    if a.screenshot:
        if not a.output and not mcp:
            raise invalid("--screenshot requires --tab and --output.")
        if not a.output and (a.mkdir or a.overwrite):
            raise invalid("--mkdir/--overwrite require an explicit screenshot output.")
        from .commands.screenshot import destination
        destination(a.output, a.mkdir, a.overwrite)
    elif a.full_page:
        raise invalid("--full-page requires --screenshot.")
    if a.scroll:
        if not a.tab:
            raise invalid("--scroll requires --tab.")
        if a.direction is None:
            raise invalid("--scroll requires --direction up or down.")
        if a.amount is not None and not 1 <= a.amount <= 10000:
            raise invalid("--scroll --amount must be in 1..10000 CSS pixels.")
    elif a.direction is not None or a.amount is not None:
        raise invalid("--direction/--amount require --scroll.")
    a.timeout = (120000 if a.download else 10000) if a.timeout is None else a.timeout
    if a.timeout <= 0:
        raise invalid("--timeout must be positive.")


def dispatch(a, browser, include_images=False):
    """Shared operation body; connection lifetime belongs to CLI or MCP caller."""
    from .tabs import resolve
    from .commands.goto import navigate
    if a.new_tab:
        page = browser.contexts[0].new_page()
    else:
        page = resolve(browser, a.tab)
    if a.goto is not None:
        return navigate(page, a.goto, a.timeout)
    if a.observe:
        from .commands.observe import observe
        return observe(page, a.tab, a.max_bytes, a.pretty, a.timeout, a.cursor)
    if a.act:
        from .commands.act import act
        return act(page, a.tab, a.ref, a.action, a.value, a.timeout, a.key, a.label)
    if a.download:
        from .commands.download import download
        return download(page.context, a.url, a.output, a.timeout, a.max_bytes, a.mkdir, a.overwrite)
    if a.screenshot:
        from .commands.screenshot import screenshot
        result = screenshot(page, a.tab, a.output, a.full_page, a.mkdir, a.overwrite, a.timeout)
        return result if include_images else result.metadata
    from .commands.scroll import scroll
    return scroll(page, a.tab, a.direction, a.amount, a.timeout)


def run(a):
    from .commands.list_tabs import list_tabs
    if a.list_tabs:
        return list_tabs(a.cdp_url, a.timeout)
    with connect(a.cdp_url, a.timeout) as browser:
        return dispatch(a, browser)


def failure(exc):
    """Shared sanitized CLI/MCP failure envelope. Never serialize call logs/args."""
    if isinstance(exc, OmniError):
        return {"ok": False, "error": {"code": exc.code, "message": exc.message}}, exc.exit_code
    pw = sys.modules.get("playwright.sync_api")
    code = (5 if pw and isinstance(exc, pw.TimeoutError) else
            4 if pw and isinstance(exc, pw.Error) else 1)
    name = "TIMEOUT" if code == 5 else "UNAVAILABLE_TARGET" if code == 4 else "INTERNAL"
    return {"ok": False, "error": {"code": name, "message": "Operation failed; inspect before retrying."}}, code


def main(argv=None):
    pretty = False
    try:
        args = parser().parse_args(argv)
        pretty = args.pretty
        validate(args)
        result = run(args)
        code = 0
    except OmniError as exc:
        result, code = failure(exc)
    except KeyboardInterrupt:
        result = {"ok": False, "error": {"code": "INTERRUPTED", "message": "Interrupted; inspect before retrying."}}
        code = 1
    except Exception as exc:
        result, code = failure(exc)
    print(serialize(result, pretty))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
