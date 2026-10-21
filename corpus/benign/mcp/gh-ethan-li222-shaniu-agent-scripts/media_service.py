"""Loopback-only authenticated WebRTC service; launched and owned by the backend."""
import asyncio
import concurrent.futures
from fractions import Fraction
import json
from pathlib import Path
import secrets
import sys
import threading
import time

import numpy as np
from aiohttp import web
from aiortc import MediaStreamTrack, RTCConfiguration, RTCPeerConnection, RTCSessionDescription
from av import AudioFrame, VideoFrame
from avatar_runtime import Runtime, ROOT
from replay_recorder import ReplayRecorder
from speech_prefetch import SpeechPrefetch, prepare_speech


class Track(MediaStreamTrack):
    def __init__(self, session, kind):
        super().__init__()
        self.kind = kind
        self.session = session
        self.index = 0

    async def recv(self):
        session = self.session
        step = .04 if self.kind == 'video' else .02
        if session.clock is None:
            session.clock = time.monotonic()
        await asyncio.sleep(max(0, session.clock + self.index*step-time.monotonic()))
        queue = session.video if self.kind == 'video' else session.audio
        try:
            item = queue.get_nowait()
            if self.kind == 'video':
                session.last_frame = item
        except asyncio.QueueEmpty:
            waiting = session.processing or session.prefetch.working or not session.sentences.empty() or not session.prefetch.ready.empty()
            item = (session.last_frame if waiting else session.idle) if self.kind == 'video' else np.zeros(320, dtype=np.int16)
        if self.kind == 'video':
            frame = VideoFrame.from_ndarray(item, format='bgr24')
            frame.pts = self.index * 3600
            frame.time_base = Fraction(1, 90000)
            session.video_sent += 1
        else:
            frame = AudioFrame.from_ndarray(item.reshape(1, -1), format='s16', layout='mono')
            frame.sample_rate = 16000
            frame.pts = self.index * 320
            frame.time_base = Fraction(1, 16000)
        self.index += 1
        return frame


class Session:
    def __init__(self, runtime, emotion):
        self.runtime = runtime
        self.pc = RTCPeerConnection(RTCConfiguration(iceServers=[]))
        self.video = asyncio.Queue(maxsize=25)
        self.audio = asyncio.Queue(maxsize=50)
        self.sentences = asyncio.Queue(maxsize=64)
        self.idle = runtime.idle(emotion)
        self.last_frame = self.idle
        self.emotion = emotion
        self.strength = 1.0
        self.epoch = ''
        self.stop = threading.Event()
        self.clock = None
        self.processing = False
        self.finished_input = True
        self.error = ''
        self.video_sent = 0
        self.rendered = 0
        self.first_frame_seconds = None
        self.started = 0
        self.subtitles = True
        self.speech = {}
        self.closed = False
        self.recorder = None
        self.finalizers = set()
        self.replay_error = ''
        self.loop = asyncio.get_running_loop()
        self.prefetch = SpeechPrefetch(self.sentences,
            lambda item: prepare_speech(item[1], item[2], self.runtime.speech_config, item[4], ROOT / 'data/media'),
            lambda item: not self.closed and item[0] == self.epoch,
            self.finalize_replay)
        self.pump = asyncio.create_task(self.run())
        self.pc.addTrack(Track(self, 'audio'))
        self.pc.addTrack(Track(self, 'video'))

    def clear(self):
        for queue in [self.video, self.audio, self.sentences]:
            while not queue.empty():
                queue.get_nowait()
        self.prefetch.clear()

    def abort(self):
        if self.recorder:
            try:
                self.recorder.close()
            except Exception:
                self.replay_error = '本轮回放保存失败，实时播放不受影响'
            self.recorder = None
        self.stop.set()
        self.epoch = ''
        self.clear()
        self.finished_input = True

    def begin(self, data):
        self.abort()
        self.epoch = data['turn_id']
        self.stop = threading.Event()
        self.emotion = data['emotion']
        self.strength = float(data.get('strength', 1))
        self.subtitles = data.get('subtitles', True)
        self.speech = {}
        self.idle = self.runtime.idle(self.emotion, self.strength)
        self.last_frame = self.idle
        self.finished_input = False
        self.error = ''
        self.rendered = 0
        self.first_frame_seconds = None
        self.started = time.monotonic()
        self.replay_error = ''
        try:
            self.recorder = ReplayRecorder(ROOT / 'data/replays', self.epoch)
        except OSError:
            self.replay_error = '本轮回放保存失败，实时播放不受影响'

    async def put(self, epoch, image, samples):
        while self.video.full() or self.audio.qsize() > self.audio.maxsize-2:
            if self.closed or epoch != self.epoch:
                return False
            await asyncio.sleep(.005)
        if self.closed or epoch != self.epoch:
            return False
        self.video.put_nowait(image)
        self.audio.put_nowait(samples[:320])
        self.audio.put_nowait(samples[320:])
        self.rendered += 1
        if self.first_frame_seconds is None:
            self.first_frame_seconds = round(time.monotonic()-self.started, 3)
        return True

    def publish(self, epoch, image, samples):
        future = asyncio.run_coroutine_threadsafe(self.put(epoch, image, samples), self.loop)
        try:
            accepted = future.result(timeout=10)
            recorder = self.recorder
            if accepted and epoch == self.epoch and recorder:
                try:
                    recorder.write(image, samples)
                except Exception:
                    try:
                        recorder.close()
                    except Exception:
                        pass
                    if self.recorder is recorder:
                        self.recorder = None
                        self.replay_error = '本轮回放保存失败，实时播放不受影响'
            return accepted
        except (concurrent.futures.TimeoutError, concurrent.futures.CancelledError):
            future.cancel()
            return False

    async def run(self):
        while not self.closed:
            item, prepared, error = await self.prefetch.ready.get()
            epoch, text, emotion, strength, stop, subtitles = item
            if epoch != self.epoch:
                if prepared:
                    prepared.close()
                continue
            self.processing = True
            try:
                if error:
                    raise error
                await asyncio.to_thread(self.runtime.render, text, emotion, strength, stop,
                    lambda image, samples: self.publish(epoch, image, samples), subtitles,
                    lambda info: self.loop.call_soon_threadsafe(self.set_speech, epoch, info), prepared, self.rendered)
            except Exception:
                if epoch == self.epoch:
                    self.abort()
                    self.error = '本地语音或 GPU 推理失败，请切换手动视频或检查媒体环境'
            finally:
                if prepared:
                    prepared.close()
                self.processing = False
                if epoch == self.epoch:
                    await self.finalize_replay()

    async def finalize_replay(self):
        if self.finished_input and not self.processing and not self.prefetch.working and self.prefetch.ready.empty() and self.sentences.empty() and self.recorder:
            recorder, self.recorder = self.recorder, None
            task = asyncio.create_task(asyncio.to_thread(recorder.close, True))
            self.finalizers.add(task)
            try:
                await asyncio.shield(task)
            except Exception:
                self.replay_error = '本轮回放保存失败，实时播放不受影响'
            finally:
                if task.done():
                    self.finalizers.discard(task)

    def set_speech(self, epoch, info):
        if epoch == self.epoch:
            self.speech = info

    def status(self):
        playing = bool(self.epoch) and (self.processing or self.prefetch.working or not self.prefetch.ready.empty() or not self.sentences.empty() or not self.video.empty() or not self.audio.empty() or not self.finished_input)
        return dict(connected=self.pc.connectionState, playing=playing, turn_id=self.epoch, avatar_id=self.runtime.avatar_id,
            emotion=self.emotion, expression='mouth_blend' if self.runtime.avatar_id == 'wav2lip_avatar_shaniu' else 'independent_asset' if self.runtime.asset(self.emotion)[3] else 'lightweight_warp',
            queued_sentences=self.sentences.qsize(), buffered_frames=self.video.qsize(),
            prepared_sentences=self.prefetch.ready.qsize(), preparing_speech=self.prefetch.working,
            rendered_frames=self.rendered, video_sent=self.video_sent,
            first_frame_seconds=self.first_frame_seconds, error=self.error, subtitles=self.subtitles, speech=self.speech,
            replay_ready=bool(self.epoch and (ROOT / 'data/replays' / (self.epoch + '.mp4')).is_file()), replay_error=self.replay_error)

    async def close(self):
        if self.closed:
            return
        self.closed = True
        self.abort()
        await self.prefetch.close()
        await self.pc.close()
        # A worker already rendering exits on stop. An idle worker is waiting on get().
        if not self.processing:
            self.pump.cancel()
        else:
            for _ in range(200):
                if not self.processing:
                    break
                await asyncio.sleep(.01)
            self.pump.cancel()
        await asyncio.gather(self.pump, return_exceptions=True)
        # Ensure deleting a conversation cannot race a late MP4 rename.
        await asyncio.gather(*self.finalizers, return_exceptions=True)
        self.finalizers.clear()


async def main(config):
    token = config['token']
    runtime = None
    session = None
    lock = asyncio.Lock()
    ROOT.joinpath('data/media').mkdir(parents=True, exist_ok=True)

    @web.middleware
    async def authenticate(request, handler):
        if not secrets.compare_digest(request.headers.get('X-Media-Token', ''), token):
            raise web.HTTPForbidden()
        try:
            return await handler(request)
        except (KeyError, ValueError, TypeError):
            return web.json_response({'error': 'Invalid media request'}, status=400)

    async def offer(request):
        nonlocal runtime, session
        data = await request.json()
        if data.get('type') != 'offer' or data.get('emotion') not in {'cool', 'happy', 'gentle', 'shy'}:
            raise web.HTTPBadRequest()
        async with lock:
            if session:
                await session.close()
            if runtime is None:
                runtime = await asyncio.to_thread(Runtime, config['source'], config.get('speech'))
            from shaniu.avatar_catalog import DEFAULT_AVATAR
            await asyncio.to_thread(runtime.select_avatar, data.get('avatar_id', DEFAULT_AVATAR))
            session = Session(runtime, data['emotion'])
            current = session
            @current.pc.on('connectionstatechange')
            async def changed():
                if current.pc.connectionState == 'failed':
                    current.abort()
                    await current.pc.close()
            try:
                await current.pc.setRemoteDescription(RTCSessionDescription(sdp=data['sdp'], type='offer'))
                await current.pc.setLocalDescription(await current.pc.createAnswer())
                return web.json_response(dict(sdp=current.pc.localDescription.sdp, type='answer'))
            except BaseException:
                await current.close()
                session = None
                raise

    async def command(request):
        nonlocal session
        if not session:
            raise web.HTTPConflict(reason='WebRTC is not connected')
        op = request.match_info['op']
        data = await request.json() if request.can_read_body else {}
        if op == 'begin':
            if data.get('emotion') not in {'cool', 'happy', 'gentle', 'shy'} or not 0 <= float(data.get('strength', 1)) <= 1.5:
                raise web.HTTPBadRequest()
            session.begin(data)
        elif op == 'sentence':
            if data.get('turn_id') != session.epoch:
                raise web.HTTPConflict(reason='Stale turn')
            text = data.get('text')
            if not isinstance(text, str) or not 1 <= len(text) <= 120:
                raise web.HTTPBadRequest()
            if session.sentences.full():
                raise web.HTTPConflict(reason='Speech queue full')
            session.sentences.put_nowait((session.epoch, text, session.emotion, session.strength, session.stop, session.subtitles))
        elif op == 'finish':
            if data.get('turn_id') == session.epoch:
                session.finished_input = True
                await session.finalize_replay()
        elif op == 'interrupt':
            session.abort()
        elif op == 'emotion':
            session.abort()
            if data.get('emotion') not in {'cool', 'happy', 'gentle', 'shy'}:
                raise web.HTTPBadRequest()
            session.emotion = data['emotion']
            session.strength = float(data.get('strength', 1))
            session.idle = runtime.idle(session.emotion, session.strength)
        elif op == 'close':
            await session.close()
            session = None
            return web.json_response({'closed': True})
        elif op != 'status':
            raise web.HTTPNotFound()
        return web.json_response(session.status())

    app = web.Application(middlewares=[authenticate], client_max_size=65536)
    app.router.add_post('/offer', offer)
    app.router.add_post('/{op}', command)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    print(json.dumps({'port': port}), flush=True)
    try:
        # Parent pipe EOF is the lifecycle signal; never leave an orphan listener.
        await asyncio.to_thread(sys.stdin.buffer.read)
    finally:
        if session:
            await session.close()
        await runner.cleanup()


if __name__ == '__main__':
    config = json.loads(sys.stdin.buffer.readline().decode('utf-8'))
    asyncio.run(main(config))
