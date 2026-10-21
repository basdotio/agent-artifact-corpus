"""Explicit live smoke test. Uses local .env; never prints the API key.

python scripts/check_model.py              # one non-streaming request
python scripts/check_model.py --stream     # one streaming request
python scripts/check_model.py --app        # two real Shaniu turns in a temporary database
Requests consume the configured model's quota. Not run by pytest.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sys
import time
import tempfile
from dataclasses import replace

import aiohttp

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))
from shaniu.config import Settings


async def check_app(settings):
    from aiohttp import CookieJar
    from aiohttp.test_utils import TestClient, TestServer
    from shaniu.server import create_app
    headers = {'X-Shaniu-Client': 'web'}
    reports = []
    with tempfile.TemporaryDirectory(prefix='shaniu-live-') as temp:
        app = create_app(replace(settings, database=Path(temp) / 'live.sqlite3'))
        async with TestClient(TestServer(app), cookie_jar=CookieJar(unsafe=True)) as client:
            await client.get('/api/health')
            response = await client.post('/api/conversations', json={'emotion': 'cool'}, headers=headers)
            cid = (await response.json())['id']
            base = '/api/conversations/' + cid
            response = await client.post('/api/memories', json={'content': '用户希望被称呼为小千。', 'confirmed': True}, headers=headers)
            assert response.status == 201
            async with client.ws_connect(base + '/events') as ws:
                await ws.receive_json()
                for emotion in ['cool', 'happy']:
                    await client.patch(base + '/emotion', json={'emotion': emotion}, headers=headers)
                    response = await client.post(base + '/turns', json={'text': '请用记忆里的称呼叫我，只用一句话回应：今天学习有点累。'}, headers=headers)
                    assert response.status == 202
                    tid = (await response.json())['turn_id']
                    text = ''
                    chunks = 0
                    while True:
                        event = await asyncio.wait_for(ws.receive_json(), 100)
                        if event.get('turn_id') != tid:
                            continue
                        if event['type'] == 'error':
                            raise RuntimeError(event['payload']['message'])
                        if event['type'] == 'assistant.delta':
                            chunks += 1
                            text += event['payload']['text']
                        if event['type'] == 'assistant.done':
                            assert text == event['payload']['text'] and text.strip()
                            report = {'emotion': emotion, 'characters': len(text), 'chunks': chunks, 'memory_used': '小千' in text, **event['payload']['metrics']}
                            reports.append(report)
                            print(json.dumps(report, ensure_ascii=False))
                            break
                saved = await (await client.get(base + '/messages')).json()
                assert len(saved['messages']) == 4
                assert all(m['status'] == 'done' for m in saved['messages'])
                assert all(report['memory_used'] for report in reports), '模型未使用已确认的称呼记忆'
    artifacts = Path(__file__).resolve().parents[1] / 'artifacts'
    artifacts.mkdir(exist_ok=True)
    (artifacts / 'model_check.json').write_text(json.dumps({'ok': True, 'model': settings.model, 'checks': reports}, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Shaniu live check passed: authenticated API, two emotions, streamed final answers, confirmed memory and persisted history.')
    return 0


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stream', action='store_true')
    parser.add_argument('--app', action='store_true')
    args = parser.parse_args()
    settings = Settings.from_env()
    if settings.provider != 'compatible':
        raise SystemExit('请先在 .env 设置 SHANIU_PROVIDER=compatible')
    if args.app:
        try:
            return await check_app(settings)
        except Exception as error:
            print(json.dumps({'ok': False, 'error_type': type(error).__name__}, ensure_ascii=False))
            return 1
    started = time.perf_counter()
    payload = {'model': settings.model, 'messages': [{'role': 'user', 'content': '你好，请只回复一句简短的问候。'}], 'stream': args.stream, 'max_tokens': 256}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=100, sock_read=80)) as client:
            async with client.post(settings.api_base + '/chat/completions', json=payload, headers={'Authorization': 'Bearer ' + settings.api_key}) as response:
                print(json.dumps({'http_status': response.status, 'stream': args.stream, 'model': settings.model}, ensure_ascii=False))
                if response.status != 200:
                    # Provider bodies can contain request data; do not echo them.
                    print('模型调用失败，请检查密钥、模型权限或额度。响应正文未输出。')
                    return 1
                text = ''
                chunks = 0
                first = None
                reasoning = 0
                if args.stream:
                    async for raw in response.content:
                        line = raw.decode('utf-8').strip()
                        if not line.startswith('data:'):
                            continue
                        data = line[5:].strip()
                        if data == '[DONE]':
                            break
                        event = json.loads(data)
                        if event.get('error'):
                            print('流式服务返回错误，响应正文未输出。')
                            return 1
                        for choice in event.get('choices', []):
                            delta = choice.get('delta', {})
                            reasoning += len(delta.get('reasoning_content') or '')
                            content = delta.get('content')
                            if isinstance(content, str) and content:
                                first = first or (time.perf_counter() - started)
                                chunks += 1
                                text += content
                else:
                    data = await response.json()
                    choices = data.get('choices') or []
                    if choices:
                        text = choices[0].get('message', {}).get('content') or ''
                print(json.dumps({'ok': bool(text.strip()), 'characters': len(text), 'chunks': chunks, 'first_text_seconds': round(first, 2) if first else None, 'total_seconds': round(time.perf_counter() - started, 2), 'reasoning_characters': reasoning}, ensure_ascii=False))
                return 0 if text.strip() else 1
    except Exception as error:
        print(json.dumps({'ok': False, 'error_type': type(error).__name__}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
