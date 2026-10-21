"""Encode the frames and PCM used by a realtime answer, without rerendering."""
from fractions import Fraction
from pathlib import Path
import threading

import av


class ReplayRecorder:
    def __init__(self, directory, turn_id):
        self.path = Path(directory) / (turn_id + '.mp4')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.pending = self.path.with_suffix('.pending')
        self.temporary = self.path.with_suffix('.part.mp4')
        self.pending.touch()
        self.lock = threading.Lock()
        self.container = None
        self.closed = False
        self.frames = 0

    def write(self, image, samples):
        with self.lock:
            if self.closed:
                return
            if self.container is None:
                self.container = av.open(str(self.temporary), 'w')
                self.video = self.container.add_stream('libx264', rate=25)
                self.video.width, self.video.height = image.shape[1], image.shape[0]
                self.video.pix_fmt = 'yuv420p'
                self.video.options = {'preset': 'ultrafast', 'crf': '23'}
                self.audio = self.container.add_stream('aac', rate=16000)
                self.audio.layout = 'mono'
            frame = av.VideoFrame.from_ndarray(image, format='bgr24')
            frame.pts, frame.time_base = self.frames, Fraction(1, 25)
            for packet in self.video.encode(frame):
                self.container.mux(packet)
            audio = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format='s16', layout='mono')
            audio.sample_rate = 16000
            audio.pts, audio.time_base = self.frames * 640, Fraction(1, 16000)
            for packet in self.audio.encode(audio):
                self.container.mux(packet)
            self.frames += 1

    def close(self, complete=False):
        with self.lock:
            if self.closed:
                return
            self.closed = True
            try:
                if self.container:
                    try:
                        for stream in (self.video, self.audio):
                            for packet in stream.encode(None):
                                self.container.mux(packet)
                    finally:
                        self.container.close()
                if complete and self.frames:
                    self.temporary.replace(self.path)
            finally:
                self.temporary.unlink(missing_ok=True)
                self.pending.unlink(missing_ok=True)
