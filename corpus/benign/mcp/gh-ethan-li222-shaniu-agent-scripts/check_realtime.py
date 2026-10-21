"""Real GPU / ICE / RTP check. Run with .venv-media Python; no model API calls."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
import numpy as np
from aiohttp import CookieJar
from aiohttp.test_utils import TestClient, TestServer
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from shaniu.config import Settings
from shaniu.server import create_app, SERVICE


class DelayedProvider:
    async def stream(self, history, emotion, memories):
        yield '你好，我是傻妞。'
        await asyncio.sleep(20)
        yield '这是第二句话。'


async def main():
    headers = {'X-Shaniu-Client': 'web'}
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    counts = {'video': 0, 'audio': 0, 'speech': 0}
    consumers = []
    first_speech = asyncio.Event()
    @pc.on('track')
    def track_received(track):
        async def consume():
            while True:
                frame = await track.recv()
                counts[track.kind] += 1
                if track.kind == 'audio' and np.max(np.abs(frame.to_ndarray().astype(np.float32))) > 100:
                    counts['speech'] += 1
                    first_speech.set()
        consumers.append(asyncio.create_task(consume()))
    pc.addTransceiver('audio', direction='recvonly')
    pc.addTransceiver('video', direction='recvonly')
    with tempfile.TemporaryDirectory() as temp:
        app = create_app(Settings(database=Path(temp) / 'test.db', tts_provider='edge' if '--edge' in sys.argv else 'windows'), DelayedProvider())
        try:
            async with TestClient(TestServer(app), cookie_jar=CookieJar(unsafe=True)) as client:
                await client.get('/api/health')
                record = await (await client.post('/api/conversations', json={}, headers=headers)).json()
                base = f'/api/conversations/{record["id"]}'
                await pc.setLocalDescription(await pc.createOffer())
                response = await client.post(base+'/media/offer', json={'type': 'offer', 'sdp': pc.localDescription.sdp}, headers=headers)
                answer = await response.json()
                assert response.status == 200, answer
                await pc.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'], type=answer['type']))
                for _ in range(100):
                    if pc.connectionState == 'connected':
                        break
                    await asyncio.sleep(.1)
                assert pc.connectionState == 'connected'
                started = time.perf_counter()
                response = await client.post(base+'/turns', json={'text': '你好', 'playback': 'realtime', 'connection_id': answer['connection_id']}, headers=headers)
                assert response.status == 202, await response.text()
                await asyncio.wait_for(first_speech.wait(), 15)
                first = round(time.perf_counter()-started, 3)
                status_url = base+'/media/connection/'+answer['connection_id']
                status = await (await client.get(status_url)).json()
                assert status['subtitles'] is True
                assert status['speech']['subtitle_alignment'] == 'word_boundary'
                history = await (await client.get(base+'/messages')).json()
                assert history['active_turn'], 'Must play before the full LLM response finishes'
                assert counts['video'] > 0 and counts['speech'] > 0
                await client.post(base+'/interrupt', headers=headers)
                stopped = await (await client.get(status_url)).json()
                assert not stopped['playing'] and stopped['buffered_frames'] == 0
                await asyncio.sleep(.4)
                later = await (await client.get(status_url)).json()
                assert later['rendered_frames'] == stopped['rendered_frames'], 'Late frames after cancellation'
                await client.patch(base+'/emotion', json={'emotion': 'happy'}, headers=headers)
                happy = await (await client.get(status_url)).json()
                assert happy['emotion'] == 'happy'
                report = dict(ok=True, connection=pc.connectionState, first_received_speech_seconds=first,
                    server_first_frame_seconds=status['first_frame_seconds'], counts=counts,
                    played_before_text_done=True, interruption=True, emotion=happy['expression'], speech=status['speech'], subtitles=True)
                (ROOT/'artifacts').mkdir(exist_ok=True)
                (ROOT/'artifacts/realtime_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                print(json.dumps(report))
                await client.delete(status_url, headers=headers)
        finally:
            await pc.close()
            for task in consumers:
                task.cancel()
            await asyncio.gather(*consumers, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
