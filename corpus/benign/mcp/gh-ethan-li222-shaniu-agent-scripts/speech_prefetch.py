"""Bounded speech preparation ahead of playback; no GPU dependency."""
import asyncio
import tempfile
from pathlib import Path

from speech import synthesize, trim_realtime_padding


class PreparedSpeech:
    def __init__(self, folder, result):
        self.folder, self.result = folder, result

    def close(self):
        self.folder.cleanup()


def prepare_speech(text, emotion, config, stop, root):
    folder = tempfile.TemporaryDirectory(prefix='speech-', dir=root)
    try:
        result = synthesize(text, Path(folder.name)/'voice.wav', emotion, dict(config, terminal_pause=False), stop)
        trim_realtime_padding(result, stop)
        return PreparedSpeech(folder, result)
    except BaseException:
        folder.cleanup()
        raise


class SpeechPrefetch:
    def __init__(self, inputs, prepare, valid, on_idle=None):
        self.inputs, self.prepare, self.valid = inputs, prepare, valid
        self.ready = asyncio.Queue(maxsize=2)
        self.working = False
        self.on_idle = on_idle
        self.task = asyncio.create_task(self.run())

    def clear(self):
        while not self.ready.empty():
            _, result, _ = self.ready.get_nowait()
            if result:
                result.close()

    async def run(self):
        while True:
            item = await self.inputs.get()
            if not self.valid(item):
                continue
            self.working = True
            result, queued = None, False
            work = asyncio.create_task(asyncio.to_thread(self.prepare, item))
            try:
                error = None
                try:
                    result = await asyncio.shield(work)
                except Exception as exception:
                    error = exception
                if self.valid(item):
                    await self.ready.put((item, result, error))
                    queued = True
            except asyncio.CancelledError:
                # A thread cannot be cancelled; collect and clean its WAV first.
                try:
                    result = await work
                except Exception:
                    pass
                raise
            finally:
                if result and not queued:
                    result.close()
                self.working = False
                if self.on_idle:
                    await self.on_idle()

    async def close(self):
        self.task.cancel()
        await asyncio.gather(self.task, return_exceptions=True)
        self.clear()
