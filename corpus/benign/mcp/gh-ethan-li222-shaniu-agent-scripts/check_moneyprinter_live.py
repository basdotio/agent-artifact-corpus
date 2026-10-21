"""Submit a short real task through Shaniu's adapter and verify result downloads."""
import argparse
import asyncio
import json
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import aiohttp
from aiohttp.test_utils import TestClient, TestServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.config import Settings
from shaniu.server import create_app


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8080')
    parser.add_argument('--kind', choices=['audio', 'subtitle', 'video'], default='audio')
    parser.add_argument('--no-subtitles', action='store_true')
    args = parser.parse_args()
    headers = {'X-Shaniu-Client': 'web'}
    with tempfile.TemporaryDirectory() as temp:
        settings = replace(Settings(), database=Path(temp) / 'tasks.db', moneyprinter_enabled=True, moneyprinter_url=args.url)
        async with TestClient(TestServer(create_app(settings)), cookie_jar=aiohttp.CookieJar(unsafe=True)) as client:
            await client.get('/api/health')
            base = '/api/agent/tools/'
            async def tool(name, arguments):
                response = await client.post(base + name, json=arguments, headers=headers)
                data = await response.json()
                if response.status != 200:
                    raise RuntimeError(data.get('error', 'Tool failed'))
                return data
            assert (await tool('moneyprinter_health', {}))['ready']
            params = dict(kind=args.kind, subject='Shaniu 接口联调', script='你好，我是傻妞。', subtitles=not args.no_subtitles, moneyprinter_enabled=True)
            if args.kind == 'video':
                params['terms'] = 'flowers'
            task = await tool('moneyprinter_create', params)
            print(json.dumps(task, ensure_ascii=False), flush=True)
            previous = None
            for _ in range(180):
                result = await tool('moneyprinter_status', dict(task_id=task['task_id']))
                status = (result['status'], result['progress'])
                if status != previous:
                    print(json.dumps(dict(status=status[0], progress=status[1]), ensure_ascii=False), flush=True)
                    previous = status
                if result['status'] in {'completed', 'failed'}:
                    break
                await asyncio.sleep(1)
            assert result['status'] == 'completed', result
            expected = dict(audio='audio_file', subtitle='subtitle_path', video='videos')[args.kind]
            assert any(item['kind'] == expected for item in result['artifacts']), 'Expected result file missing'
            downloads = []
            async with aiohttp.ClientSession() as upstream:
                for artifact in result['artifacts']:
                    async with upstream.get(artifact['url']) as response:
                        data = await response.read()
                        assert response.status == 200 and len(data) > 20, 'Download failed or empty result'
                        if artifact['filename'].endswith('.srt'):
                            assert b'-->' in data
                        if artifact['filename'].endswith('.mp4'):
                            assert b'ftyp' in data[:32]
                        downloads.append(dict(filename=artifact['filename'], bytes=len(data)))
            report = dict(ok=True, kind=args.kind, subtitles=not args.no_subtitles, task_id=task['task_id'], downloads=downloads, simulated=False)
            target = ROOT / 'artifacts' / f'moneyprinter-live-{args.kind}-{"off" if args.no_subtitles else "on"}.json'
            target.parent.mkdir(exist_ok=True)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    asyncio.run(main())
