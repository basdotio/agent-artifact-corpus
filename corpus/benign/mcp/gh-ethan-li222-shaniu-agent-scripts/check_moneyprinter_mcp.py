"""Real stdio MCP round trip against a temporary, simulated HTTP upstream."""
import asyncio
import json
import os
import sys
import tempfile
from pathlib import Path
from uuid import uuid4

from aiohttp import web
from aiohttp.test_utils import TestServer
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]


async def main():
    tid = str(uuid4())
    requests = []
    async def create(request):
        payload = await request.json()
        requests.append(payload)
        assert payload['subtitle_enabled'] is False
        return web.json_response(dict(status=200, data=dict(task_id=tid)))
    async def status(request):
        return web.json_response(dict(status=200, data=dict(state=1, progress=100, videos=[f'/tasks/{tid}/final-1.mp4'])))
    async def spec(request):
        return web.json_response(dict(paths={path: {} for path in ['/api/v1/videos', '/api/v1/audio', '/api/v1/subtitle', '/api/v1/tasks/{task_id}']}))
    app = web.Application()
    app.router.add_post('/api/v1/videos', create)
    app.router.add_get('/api/v1/tasks/{tid}', status)
    app.router.add_get('/openapi.json', spec)
    async with TestServer(app) as upstream:
        with tempfile.TemporaryDirectory() as temp:
            env = os.environ.copy()
            env.pop('SHANIU_API_KEY', None)
            env.update(SHANIU_MPT_URL=str(upstream.make_url('')).rstrip('/'), SHANIU_MCP_DATABASE=str(Path(temp) / 'mcp.db'))
            params = StdioServerParameters(command=sys.executable, args=[str(ROOT / 'scripts/moneyprinter_mcp.py')], env=env)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    assert {tool.name for tool in tools.tools} == {'moneyprinter_health', 'moneyprinter_create', 'moneyprinter_status', 'moneyprinter_tasks', 'moneyprinter_enhance'}
                    async def call(name, args):
                        result = await session.call_tool(name, args)
                        assert not result.isError, result
                        return json.loads(next(item.text for item in result.content if item.type == 'text'))
                    assert (await call('moneyprinter_health', {}))['ready']
                    assert (await call('moneyprinter_create', dict(kind='video', subject='测试', script='测试旁白。', terms='flowers', subtitles=False)))['task_id'] == tid
                    assert (await call('moneyprinter_status', dict(task_id=tid)))['status'] == 'completed'
                    assert (await call('moneyprinter_tasks', {}))['tasks'][0]['task_id'] == tid
                    invalid = await session.call_tool('moneyprinter_status', dict(task_id='../config.toml'))
                    assert invalid.isError
                    assert len(requests) == 1
    print('MCP stdio passed: initialize, discover 5 tools, create without subtitles, status/artifacts, list, invalid task rejection (simulated upstream).')


if __name__ == '__main__':
    asyncio.run(main())
