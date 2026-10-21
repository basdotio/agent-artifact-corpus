"""Opt-in live network/model and stdio checks; reports no credentials."""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from shaniu.assistant_tools import AssistantTools, LOCAL_TOOLS
from shaniu.config import Settings
from shaniu.providers import CompatibleProvider


async def check_mcp():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    parameters = StdioServerParameters(command=str(ROOT / '.venv-tools/Scripts/python.exe'), args=[str(ROOT / 'scripts/assistant_mcp.py')])
    async with stdio_client(parameters) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            await client.initialize()
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert len(names) == 5 and 'web_read' not in names
            result = await client.call_tool('knowledge_search', dict(query='WebRTC'))
            assert not result.isError
            assert json.loads(result.content[0].text)['matches']
            disabled = await client.call_tool('web_read', dict(url='https://example.com'))
            assert disabled.isError
            print('MCP handshake, tool listing, search and disabled-group checks passed')
    bundled = StdioServerParameters(command=parameters.command, args=parameters.args, env={'SHANIU_MCP_GROUPS': 'files,knowledge,web,moneyprinter'})
    async with stdio_client(bundled) as (reader, writer):
        async with ClientSession(reader, writer) as client:
            await client.initialize()
            names = {tool.name for tool in (await client.list_tools()).tools}
            assert len(names) == 12 and {'github_readme', 'moneyprinter_create'} <= names
            print('MCP bundled groups: all 12 tool definitions available')


async def main():
    if '--mcp' in sys.argv:
        await check_mcp()
        return
    with tempfile.TemporaryDirectory() as temporary:
        # The external-model check uses only newly created synthetic data.
        # No project documents, user notes or browser history leave the machine.
        documents = Path(temporary) / 'synthetic-docs'
        documents.mkdir()
        (documents / 'sample.md').write_text('Synthetic test: WebRTC supports real-time media.', encoding='utf-8')
        adapter = AssistantTools(Path(temporary) / 'workspace', documents)
        page = await adapter.call('check', 'web_read', dict(url='https://example.com'))
        assert 'Example Domain' in page['content']
        repo = await adapter.call('check', 'github_repository', dict(repository='aio-libs/aiohttp'))
        assert repo['full_name'] == 'aio-libs/aiohttp'
        readme = await adapter.call('check', 'github_readme', dict(repository='aio-libs/aiohttp'))
        assert 'aiohttp' in readme['content'].lower() and readme['url'].startswith('https://github.com/')
        print('Live public webpage and GitHub metadata checks passed')
        if '--model' not in sys.argv:
            return
        calls = []
        async def execute(name, args):
            calls.append(name)
            return await adapter.call('check', name, args)
        definitions = [dict(type='function', function=dict(name=t['name'], description=t['description'], parameters=t['inputSchema'])) for t in LOCAL_TOOLS if t['name'] in {'workspace_write', 'knowledge_search'}]
        provider = CompatibleProvider(Settings.from_env())
        history = [dict(role='user', content='请调用工具，将内容“今天学习 WebRTC。”保存为 check.md，然后检索本地 WebRTC 资料，简短告诉我保存结果和一条实际文档来源。', status='done')]
        answer = ''.join([part async for part in provider.stream_with_tools(history, 'cool', [], definitions, execute)])
        assert 'workspace_write' in calls and 'knowledge_search' in calls, calls
        assert adapter.path('check', 'check.md').is_file()
        assert answer.strip()
        print('Live model native tool loop passed:', ', '.join(calls))


if __name__ == '__main__':
    asyncio.run(main())
