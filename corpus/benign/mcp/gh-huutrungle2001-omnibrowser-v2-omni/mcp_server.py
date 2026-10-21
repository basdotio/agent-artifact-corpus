"""Seven STDIO tools; lazy, serial, thread-owned CDP; thin image adaptation."""
import argparse
import asyncio
import base64
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import logging

import anyio
from jsonschema import Draft202012Validator
from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

from . import __version__
from .cdp import connect
from .cli import dispatch, failure, parser, run, validate
from .commands.screenshot import ScreenshotResult
from .errors import invalid
from .models import serialize


def schema(properties, required=(), **extra):
    return {'type': 'object', 'properties': properties, 'required': list(required), 'additionalProperties': False, **extra}


def action_variant(action, required=(), forbidden=()):
    return {'properties': {'action': {'const': action}}, 'required': list(required),
            'not': {'anyOf': [{'required': [key]} for key in forbidden]}}


TAB = {'type': 'string', 'minLength': 1, 'description': 'Exact stable tab_id; no implicit tab selection.'}
URL = {'type': 'string', 'minLength': 1, 'description': 'Absolute HTTP(S) URL without embedded credentials.'}
TEXT = {'type': 'string'}
TIMEOUT = {'type': 'integer', 'minimum': 1, 'description': 'Phase timeout in milliseconds (10000; download 120000).'}
FILE_OPTIONS = {'output': {'type': 'string', 'minLength': 1, 'description': 'Prefer an absolute output path.'},
                'mkdir': {'type': 'boolean', 'default': False}, 'overwrite': {'type': 'boolean', 'default': False}}
TOOLS = [
    types.Tool(name='list_tabs', description='List stable page-target IDs, titles and URLs without selecting/focusing a tab.',
               inputSchema=schema({'timeout': TIMEOUT})),
    types.Tool(name='goto', description='Navigate an explicit tab or create one only with new_tab=true. No hidden observe.',
               inputSchema=schema({'url': URL, 'tab_id': TAB, 'new_tab': {'type': 'boolean', 'default': False}, 'timeout': TIMEOUT}, ('url',), oneOf=[
                   {'required': ['tab_id'], 'properties': {'new_tab': {'const': False}}},
                   {'required': ['new_tab'], 'properties': {'new_tab': {'const': True}}, 'not': {'required': ['tab_id']}},
               ])),
    types.Tool(name='observe', description='Clean content, links and controls with exact refs; continue all streams using next_cursor. No field values.',
               inputSchema=schema({'tab_id': TAB, 'cursor': {'type': 'string', 'minLength': 1, 'maxLength': 512},
                                   'max_bytes': {'type': 'integer', 'minimum': 2048, 'maximum': 65536, 'default': 15360}, 'timeout': TIMEOUT}, ('tab_id',))),
    types.Tool(name='act', description='Native click/fill/press/select on an exact observed ref. No replay or hidden observe. select is native HTML only.',
               inputSchema=schema({'tab_id': TAB, 'ref': {'type': 'string', 'minLength': 1},
                                   'action': {'type': 'string', 'enum': ['click', 'fill', 'press', 'select']},
                                   'value': TEXT, 'label': TEXT, 'key': {'type': 'string', 'minLength': 1}, 'timeout': TIMEOUT},
                                  ('tab_id', 'ref', 'action'), oneOf=[
                    action_variant('click', forbidden=('value', 'label', 'key')),
                    action_variant('fill', ('value',), ('label', 'key')),
                    action_variant('press', ('key',), ('value', 'label')),
                    action_variant('select', ('value',), ('label', 'key')),
                    action_variant('select', ('label',), ('value', 'key')),
               ])),
    types.Tool(name='download', description='Cookie-scoped HTTP GET streaming; atomic output, no Save dialog. No POST/blob/challenge fallback.',
               inputSchema=schema({'tab_id': TAB, 'url': URL, **FILE_OPTIONS,
                                   'max_bytes': {'type': 'integer', 'minimum': 1, 'default': 536870912}, 'timeout': TIMEOUT}, ('tab_id', 'url', 'output'))),
    types.Tool(name='screenshot', description='Return actual PNG ImageContent and metadata; optional safe output file. No focus/resize/scroll. Max 6M pixels, 8192px/side, 4 MiB.',
               inputSchema=schema({'tab_id': TAB, **FILE_OPTIONS, 'full_page': {'type': 'boolean', 'default': False}, 'timeout': TIMEOUT}, ('tab_id',))),
    types.Tool(name='scroll', description='One main-document native wheel input. CSS pixels; reports before/after movement, not lazy-load completeness. Inner panes unsupported.',
               inputSchema=schema({'tab_id': TAB, 'direction': {'type': 'string', 'enum': ['up', 'down']},
                                   'amount': {'type': 'integer', 'minimum': 1, 'maximum': 10000}, 'timeout': TIMEOUT}, ('tab_id', 'direction'))),
]
VALIDATORS = {tool.name: Draft202012Validator(tool.inputSchema) for tool in TOOLS}


def arguments(name, values):
    validator = VALIDATORS.get(name)
    if validator is None or not validator.is_valid(values):
        raise invalid('Invalid tool arguments; use the advertised schema.')
    argv = ['--goto=' + values['url']] if name == 'goto' else ['--' + name.replace('_', '-')]
    for key, val in values.items():
        if name == 'goto' and key == 'url':
            continue
        flag = '--' + ('tab' if key == 'tab_id' else key.replace('_', '-'))
        if isinstance(val, bool):
            if val:
                argv.append(flag)
        else:
            argv.append(flag + '=' + str(val))
    args = parser().parse_args(argv)
    validate(args, mcp=True)
    return args


class SessionOwner:
    """All methods, including close, run on the single executor thread."""
    def __init__(self):
        self.browser = None
        self.connection = None

    def close(self):
        connection, self.connection, self.browser = self.connection, None, None
        if connection:
            try:
                connection.__exit__(None, None, None)
            except Exception:
                pass

    def execute(self, name, values):
        try:
            args = arguments(name, values)
            if args.list_tabs:
                return run(args)
            if self.browser is not None and not self.browser.is_connected():
                self.close()
            if self.browser is None:
                connection = connect(args.cdp_url, args.timeout)
                self.browser = connection.__enter__()
                self.connection = connection
            self.browser.contexts[0].set_default_timeout(args.timeout)
            self.browser.contexts[0].set_default_navigation_timeout(args.timeout)
            return dispatch(args, self.browser, include_images=True)
        except Exception as exc:
            result, _ = failure(exc)
            from playwright.sync_api import Error
            if isinstance(exc, Error) or self.browser is not None and not self.browser.is_connected():
                self.close()
            return result


@asynccontextmanager
async def lifespan(server):
    owner = SessionOwner()
    executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix='omni-cdp')
    try:
        yield (owner, executor)
    finally:
        with anyio.CancelScope(shield=True):
            await asyncio.get_running_loop().run_in_executor(executor, owner.close)
        executor.shutdown(wait=True, cancel_futures=True)


server = Server('omni', version=__version__, lifespan=lifespan, instructions=(
    'Use explicit tab IDs and observed refs. Follow observe next_cursor while has_more; '
    'STALE_CURSOR needs a fresh observe. STALE_REF needs observe/new target. '
    'Never automatically replay mutations after failure/timeout/cancellation. '
    'Main/open Shadow DOM only; screenshots may show sensitive page content. '
    'Scroll is one wheel input, not a claim of lazy-load completeness. Coordinate shared tabs.'
))


@server.list_tools()
async def list_tools():
    return TOOLS


@server.call_tool(validate_input=False)
async def call_tool(name, values):
    try:
        owner, executor = server.request_context.lifespan_context
        result = await asyncio.get_running_loop().run_in_executor(executor, owner.execute, name, values)
    except Exception as exc:
        result, _ = failure(exc)
    images = []
    if isinstance(result, ScreenshotResult):
        images = [types.ImageContent(type='image', mimeType='image/png', data=base64.b64encode(result.png).decode())]
        result = result.metadata
    return types.CallToolResult(content=[types.TextContent(type='text', text=serialize(result)), *images],
                                structuredContent=result, isError=result.get('ok') is False)


async def serve():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main():
    p = argparse.ArgumentParser(description='Omni persistent seven-tool STDIO MCP (lazy CDP attach).')
    p.add_argument('--version', action='version', version=__version__)
    p.parse_args()
    logging.getLogger('mcp').setLevel(logging.WARNING)
    try:
        asyncio.run(serve())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()
