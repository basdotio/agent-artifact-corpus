"""Real RTP continuity check across three separately synthesized test sentences."""
import asyncio
import json
from pathlib import Path
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'backend'))
import numpy as np
from aiohttp import CookieJar
from aiohttp.test_utils import TestClient, TestServer
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from shaniu.config import Settings
from shaniu.server import create_app


class Provider:
    async def stream(self, history, emotion, memories):
        for text in ['你好，我是傻妞。', '今天我们一起学习。', '准备好了就开始吧。']:
            yield text
            await asyncio.sleep(.03)


async def main():
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    audible, consumers = [], []
    @pc.on('track')
    def received(track):
        async def consume():
            while True:
                frame = await track.recv()
                if track.kind == 'audio':
                    samples = frame.to_ndarray().astype(np.float32)
                    audible.append(bool(np.sqrt(np.mean(samples*samples))>120))
        consumers.append(asyncio.create_task(consume()))
    pc.addTransceiver('audio', direction='recvonly')
    pc.addTransceiver('video', direction='recvonly')
    try:
        with tempfile.TemporaryDirectory() as temporary:
            app = create_app(Settings(database=Path(temporary)/'check.db', tts_provider='edge', tts_fallback=False), Provider())
            async with TestClient(TestServer(app), cookie_jar=CookieJar(unsafe=True)) as client:
                headers = {'X-Shaniu-Client': 'web'}
                await client.get('/api/health')
                cid = (await (await client.post('/api/conversations', json={}, headers=headers)).json())['id']
                base = '/api/conversations/'+cid
                await pc.setLocalDescription(await pc.createOffer())
                response = await client.post(base+'/media/offer', json=dict(type='offer', sdp=pc.localDescription.sdp), headers=headers)
                assert response.status == 200, await response.text()
                answer = await response.json()
                await pc.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'], type='answer'))
                for _ in range(100):
                    if pc.connectionState == 'connected':
                        break
                    await asyncio.sleep(.1)
                assert pc.connectionState == 'connected'
                started = time.monotonic()
                response = await client.post(base+'/turns', json=dict(text='测试连续播放', playback='realtime', connection_id=answer['connection_id']), headers=headers)
                assert response.status == 202
                for _ in range(600):
                    status = await (await client.get(base+'/media/connection/'+answer['connection_id'])).json()
                    assert not status.get('error'), status
                    if status['rendered_frames'] and not status['playing'] and status['replay_ready']:
                        break
                    await asyncio.sleep(.1)
                assert status['replay_ready'] and not status['playing'], status
                # Let the small receiver jitter buffer drain.
                await asyncio.sleep(.25)
                indexes = [i for i, value in enumerate(audible) if value]
                assert indexes, 'No audible RTP frames'
                run, longest = 0, 0
                for value in audible[indexes[0]:indexes[-1]+1]:
                    run = 0 if value else run+1
                    longest = max(longest, run)
                report = dict(ok=longest*.02 < .7, longest_internal_silence_seconds=round(longest*.02, 3), received_speech_span_seconds=round((indexes[-1]-indexes[0]+1)*.02, 3), elapsed_seconds=round(time.monotonic()-started, 3), rendered_frames=status['rendered_frames'], replay_ready=status['replay_ready'], speech=status['speech'])
                (ROOT/'artifacts/continuity_check.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
                print(json.dumps(report), flush=True)
                assert report['ok'], report
    finally:
        await pc.close()
        for task in consumers:
            task.cancel()
        await asyncio.gather(*consumers, return_exceptions=True)


if __name__ == '__main__':
    asyncio.run(main())
