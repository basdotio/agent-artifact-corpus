"""Exercise the real stdio protocol, including error results; no LLM or API key needed."""
import asyncio
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from test_boardview import FIXTURE


async def check(root: Path) -> dict:
    params = StdioServerParameters(command=sys.executable,
        args=[str(Path(__file__).with_name('server.py')), '--root', str(root)])
    checks = []
    async with stdio_client(params) as (reader, writer):
        async with ClientSession(reader, writer) as session:
            init = await session.initialize()
            tools = (await session.list_tools()).tools
            assert len(tools) == 7
            assert all(t.annotations.readOnlyHint for t in tools)

            async def call(name, args, error=False):
                r = await session.call_tool(name, args)
                assert bool(r.isError) == error, (name, r)
                checks.append({'tool': name, 'expected_error': error, 'passed': True})
                return r.structuredContent

            catalog = await call('board_catalog', {})
            assert catalog['total'] == 2
            info = await call('board_info', {'path': 'sample.cad'})
            assert info['components'] == 2 and info['declared_nodes'] == 3
            search = await call('board_search', {'path': 'sample.cad', 'query': 'r1'})
            assert search['items'][0]['reference'] == 'R1'
            await call('board_search', {'path': 'sample.cad', 'query': '1.8', 'kind': 'net'})
            comp = await call('board_component', {'path': 'sample.cad', 'reference': 'R1', 'limit': 1})
            assert comp['pins']['next_offset'] == 1
            pin = await call('board_pin', {'path': 'sample.cad', 'reference': 'R1', 'pin': '2'})
            assert pin['pin']['net'] == '+1.8V S5'
            net = await call('board_net', {'path': 'sample.cad', 'net': '+1.8V S5'})
            assert net['total'] == 2
            nearby = await call('board_nearby', {'path': 'sample.cad', 'reference': 'R1', 'radius': 5, 'same_side': False})
            assert nearby['items'][0]['origin_distance'] == 5
            same = await call('board_nearby', {'path': 'sample.cad', 'reference': 'R1', 'radius': 5})
            assert same['total'] == 0
            await call('board_info', {'path': 'bad.fz'}, error=True)
            await call('board_info', {'path': '../outside.cad'}, error=True)
            await call('board_net', {'path': 'sample.cad', 'net': 'MISSING'}, error=True)
            await call('board_pin', {'path': 'sample.cad', 'reference': 'R1', 'pin': '9'}, error=True)
            await call('board_component', {'path': 'sample.cad', 'reference': 'R1', 'limit': 101}, error=True)
            await call('board_search', {'path': 'sample.cad', 'query': '', 'kind': 'invalid'}, error=True)
            return {'protocol': init.protocolVersion, 'tools': [t.name for t in tools], 'checks': checks}


async def main():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / 'boards'
        root.mkdir()
        (root / 'sample.cad').write_bytes(FIXTURE)
        (root / 'bad.fz').write_bytes(b'unsupported binary')
        (Path(d) / 'outside.cad').write_bytes(FIXTURE)
        receipt = {'checked_at': datetime.now(timezone.utc).isoformat(), 'synthetic': await check(root)}
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
