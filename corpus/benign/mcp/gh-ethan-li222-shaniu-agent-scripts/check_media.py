"""Explicit local GPU integration check, with no paid model calls."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from aiohttp import CookieJar
from aiohttp.test_utils import TestClient, TestServer
from shaniu.config import Settings
from shaniu.server import create_app, SERVICE


async def check_avatar(avatar_id):
    headers = {'X-Shaniu-Client': 'web'}
    with tempfile.TemporaryDirectory() as temp:
        app = create_app(Settings(database=Path(temp) / 'test.db', tts_provider='edge' if '--edge' in sys.argv else 'windows'))
        async with TestClient(TestServer(app), cookie_jar=CookieJar(unsafe=True)) as client:
            await client.get('/api/health')
            record = await (await client.post('/api/conversations', json={}, headers=headers)).json()
            cid = record['id']
            if avatar_id:
                selected = await client.patch(f'/api/conversations/{cid}/avatar', json={'avatar_id': avatar_id}, headers=headers)
                assert selected.status == 200, await selected.text()
            mid = app[SERVICE].store.add_message(cid, 'gpu-check', 'assistant', '你好，我是傻妞。')
            start = time.perf_counter()
            response = await client.post(f'/api/conversations/{cid}/media', json={'message_id': mid}, headers=headers)
            result = await response.json()
            if response.status != 200:
                raise RuntimeError(result.get('error', 'Media check failed'))
            video = await client.get(result['url'], headers={'Range': 'bytes=0-31'})
            assert video.status == 206
            assert b'ftyp' in await video.read()
            audio = await client.get(result['audio_url'])
            assert audio.status == 200 and (await audio.read()).startswith(b'RIFF')
            subtitles = await client.get(result['subtitle_url'])
            assert subtitles.status == 200 and '-->' in await subtitles.text()
            vtt = await client.get(result['vtt_url'])
            assert vtt.status == 200 and (await vtt.text()).startswith('WEBVTT')
            assert result['metrics']['subtitle_alignment'] == 'word_boundary'
            report = dict(result['metrics'], avatar_id=avatar_id or record['avatar_id'], api_seconds=round(time.perf_counter()-start, 2), range_status=video.status)
            (ROOT / 'artifacts').mkdir(exist_ok=True)
            filename = f'media_check_{avatar_id}.json' if avatar_id else 'media_check.json'
            (ROOT / 'artifacts' / filename).write_text(json.dumps(report, indent=2), encoding='utf-8')
            print(json.dumps(report))
            await client.post(f'/api/conversations/{cid}/interrupt', headers=headers)
            assert (await client.get(result['url'])).status == 404
            assert (await client.get(result['audio_url'])).status == 404
            assert (await client.get(result['subtitle_url'])).status == 404
            pending = asyncio.create_task(client.post(f'/api/conversations/{cid}/media', json={'message_id': mid}, headers=headers))
            for _ in range(100):
                if app[SERVICE].avatar.busy:
                    break
                await asyncio.sleep(.01)
            await asyncio.sleep(.5)
            await client.post(f'/api/conversations/{cid}/interrupt', headers=headers)
            assert (await pending).status == 409
            assert not app[SERVICE].avatar.busy
            assert cid not in app[SERVICE].avatar.jobs
            print('Real media cancellation passed: worker stopped; no late video result.')


async def main():
    if '--all-avatars' in sys.argv:
        from shaniu.avatar_catalog import AVATARS
        for avatar in AVATARS:
            await check_avatar(avatar['id'])
    else:
        await check_avatar(None)


if __name__ == '__main__':
    asyncio.run(main())
