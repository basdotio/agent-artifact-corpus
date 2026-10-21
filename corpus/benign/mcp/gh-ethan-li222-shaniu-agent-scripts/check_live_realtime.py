"""Check running Shaniu with one real model reply and received WebRTC media.

Run with .venv-media Python. Makes one model request; removes its conversation.
"""
import asyncio
import json
from pathlib import Path

import numpy as np
from aiohttp import ClientSession, ClientTimeout, CookieJar, WSMsgType
from aiortc import RTCConfiguration, RTCPeerConnection, RTCSessionDescription


async def main():
    pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
    counts = dict(video=0, audio=0, speech=0)
    speech = asyncio.Event()
    consumers = []

    @pc.on('track')
    def received(track):
        async def consume():
            while True:
                frame = await track.recv()
                counts[track.kind] += 1
                if track.kind == 'audio' and np.max(np.abs(frame.to_ndarray().astype(np.float32))) > 100:
                    counts['speech'] += 1
                    speech.set()
        consumers.append(asyncio.create_task(consume()))

    pc.addTransceiver('audio', direction='recvonly')
    pc.addTransceiver('video', direction='recvonly')
    async with ClientSession('http://127.0.0.1:8011', cookie_jar=CookieJar(unsafe=True),
                             timeout=ClientTimeout(total=180), headers={'X-Shaniu-Client': 'web'}) as client:
        base = None
        try:
            health = await (await client.get('/api/health')).json()
            assert health['service'] == 'shaniu'
            record = await (await client.post('/api/conversations', json={})).json()
            base = '/api/conversations/' + record['id']
            await pc.setLocalDescription(await pc.createOffer())
            response = await client.post(base + '/media/offer', json=dict(type='offer', sdp=pc.localDescription.sdp))
            answer = await response.json()
            assert response.status == 200, answer
            await pc.setRemoteDescription(RTCSessionDescription(sdp=answer['sdp'], type=answer['type']))
            async with client.ws_connect(base + '/events') as ws:
                await ws.receive_json()
                response = await client.post(base + '/turns', json=dict(
                    text='你好，请用一句简短的话介绍自己。', playback='realtime',
                    connection_id=answer['connection_id'], subtitles=True))
                assert response.status == 202, await response.text()
                async def completed():
                    while True:
                        event = await ws.receive(timeout=120)
                        assert event.type == WSMsgType.TEXT, 'Event connection closed'
                        payload = json.loads(event.data)
                        if payload['type'] in ('assistant.error', 'media.error'):
                            raise RuntimeError(payload)
                        if payload['type'] == 'assistant.done':
                            return
                await asyncio.wait_for(asyncio.gather(completed(), speech.wait()), 150)
                status = await (await client.get(base + '/media/connection/' + answer['connection_id'])).json()
                history = await (await client.get(base + '/messages')).json()
                replies = [m for m in history['messages'] if m['role'] == 'assistant']
                assert replies and replies[-1]['status'] == 'done' and replies[-1]['content']
                assert counts['video'] > 0 and counts['speech'] > 0
                report = dict(ok=True, model_reply=True, reply_characters=len(replies[-1]['content']),
                              connection=pc.connectionState, counts=counts, speech=status['speech'])
                output = Path(__file__).resolve().parents[1] / 'artifacts/live_realtime_check.json'
                output.parent.mkdir(exist_ok=True)
                output.write_text(json.dumps(report, indent=2), encoding='utf-8')
                print(json.dumps(report))
        finally:
            await pc.close()
            for task in consumers:
                task.cancel()
            await asyncio.gather(*consumers, return_exceptions=True)
            if base:
                await client.delete(base)


if __name__ == '__main__':
    asyncio.run(main())
