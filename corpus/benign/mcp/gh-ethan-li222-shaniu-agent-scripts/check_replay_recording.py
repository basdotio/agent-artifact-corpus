"""Real encoder check using media Python; no GPU/model calls."""
import tempfile
import json

import av
import numpy as np
from replay_recorder import ReplayRecorder


with tempfile.TemporaryDirectory() as directory:
    recorder = ReplayRecorder(directory, 'test')
    for index in range(50):
        image = np.full((128, 128, 3), index * 4, dtype=np.uint8)
        audio = (np.sin((np.arange(640) + index * 640) * 2 * np.pi * 440 / 16000) * 10000).astype(np.int16)
        recorder.write(image, audio)
    assert not recorder.path.exists() and recorder.pending.exists()
    recorder.close(True)
    with av.open(str(recorder.path)) as container:
        video = list(container.decode(video=0))
    with av.open(str(recorder.path)) as container:
        audio = list(container.decode(audio=0))
    assert len(video) == 50 and audio
    assert max(np.max(np.abs(frame.to_ndarray())) for frame in audio) > .1
    assert not recorder.pending.exists() and not recorder.temporary.exists()
    recorder.close(True)
    cancelled = ReplayRecorder(directory, 'cancelled')
    cancelled.write(image, np.zeros(640, dtype=np.int16))
    cancelled.close(False)
    assert not cancelled.path.exists() and not cancelled.temporary.exists() and not cancelled.pending.exists()
    print(json.dumps(dict(ok=True, video_frames=len(video), audio_frames=len(audio), cancelled_removed=True)))
