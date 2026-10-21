"""Isolated CUDA worker: local Chinese TTS -> Wav2Lip -> H.264/AAC clip.

Reads job JSON from stdin, emits a statistics JSON on stdout. No model API calls.
Reference model and feature extraction are imported from the local AIAvatar checkout.
"""
import importlib.util
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import time
from fractions import Fraction
from functools import lru_cache
from speech import synthesize, draw_caption, write_subtitles
import shutil

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))
from shaniu.avatar_catalog import DEFAULT_AVATAR, SHANIU_AVATAR, avatar_asset_root
from avatar_quality import blend_mouth


class CoordinateReader(pickle.Unpickler):
    def find_class(self, module, name):
        # AIAvatar coordinate caches may contain numpy integer scalars.
        import numpy as np
        allowed = {
            ('numpy', 'dtype'): np.dtype,
            ('numpy.core.multiarray', 'scalar'): np.core.multiarray.scalar,
            ('numpy._core.multiarray', 'scalar'): np.core.multiarray.scalar,
        }
        if (module, name) not in allowed:
            raise pickle.UnpicklingError('Unsupported object in coordinate cache')
        return allowed[(module, name)]


def reference_module(source):
    name = 'shaniu_aiavatar_wav2lip'
    spec = importlib.util.spec_from_file_location(name, source / 'src/wav2lip/__init__.py', submodule_search_locations=[str(source / 'src/wav2lip')])
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    from importlib import import_module
    return import_module(name + '.models').Wav2Lip, import_module(name + '.audio')


def mirror(index, size):
    if size <= 1:
        return 0
    index %= size * 2
    return index if index < size else size * 2 - index - 1


def run(job):
    import cv2
    import imageio_ffmpeg
    import numpy as np
    import torch
    from scipy.io import wavfile
    from scipy.signal import resample_poly

    if not torch.cuda.is_available():
        raise RuntimeError('CUDA is unavailable in media environment')
    started = time.perf_counter()
    source = Path(job['source']).resolve()
    output = Path(job['output']).resolve()
    if not output.is_relative_to((ROOT / 'data/media').resolve()):
        raise RuntimeError('Output must stay inside Shaniu/data/media')
    output.parent.mkdir(parents=True, exist_ok=True)
    assets = ROOT / 'data/avatar'
    avatar_id = job.get('avatar_id', DEFAULT_AVATAR)
    avatar = avatar_asset_root(avatar_id, job.get('emotion', 'cool'))
    faces = sorted((avatar / 'face_imgs').glob('*.png'))
    frames = sorted((avatar / 'full_imgs').glob('*.png'))
    if not faces:
        faces = sorted((avatar / 'face_imgs').glob('*.jpg'))
    if not frames:
        frames = sorted((avatar / 'full_imgs').glob('*.jpg'))
    with (avatar / 'coords.pkl').open('rb') as file:
        coords = CoordinateReader(file).load()
    if not frames or not len(frames) == len(faces) == len(coords):
        raise RuntimeError('Avatar frames, faces and coordinate counts do not match')
    Wav2Lip, audio = reference_module(source)
    torch.set_num_threads(4)
    checkpoint = torch.load(assets / 'wav2lip.pth', map_location='cpu', weights_only=True)
    model = Wav2Lip().eval()
    model.load_state_dict({key.removeprefix('module.'): value for key, value in checkpoint['state_dict'].items()})
    del checkpoint
    model = model.cuda()
    # Match the reference FP32 path first; optimize only after measured verification.
    with torch.inference_mode():
        model(torch.zeros(1, 1, 80, 16, device='cuda'), torch.zeros(1, 6, 256, 256, device='cuda'))
    torch.cuda.synchronize()
    loaded = time.perf_counter()

    @lru_cache(maxsize=64)
    def face(index):
        image = cv2.imread(str(faces[index]))
        if image is None:
            raise RuntimeError('Unreadable avatar face image')
        return cv2.resize(image, (256, 256))

    @lru_cache(maxsize=8)
    def frame(index):
        image = cv2.imread(str(frames[index]))
        if image is None:
            raise RuntimeError('Unreadable avatar full image')
        return image

    with tempfile.TemporaryDirectory(prefix=f'work-{output.stem}-', dir=output.parent) as work:
        wav = Path(work) / 'voice.wav'
        speech = synthesize(job['text'], wav, job.get('emotion', 'cool'), job.get('speech'))
        rate, samples = wavfile.read(wav)
        samples = samples.astype(np.float32) / 32768.0
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        ratio = Fraction(16000, rate)
        samples = resample_poly(samples, ratio.numerator, ratio.denominator).astype(np.float32)
        if not .1 <= len(samples) / 16000 <= 45:
            raise RuntimeError('Audio duration is outside 0.1–45 seconds')
        mel = audio.melspectrogram(samples)
        if not np.isfinite(mel).all():
            raise RuntimeError('Invalid mel features')
        if mel.shape[1] < 16:
            mel = np.pad(mel, ((0, 0), (0, 16 - mel.shape[1])), mode='edge')
        count = int(np.ceil(len(samples) / 16000 * 25))
        height, width = frame(0).shape[:2]
        scale = min(1, 720 / max(width, height))
        out_w, out_h = int(width * scale) // 2 * 2, int(height * scale) // 2 * 2
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        silent_video = Path(work) / 'silent.mp4'
        command = [ffmpeg, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{out_w}x{out_h}', '-r', '25', '-i', '-', '-an', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '23', '-pix_fmt', 'yuv420p', str(silent_video)]
        inference_seconds = 0
        with subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as encoder:
            try:
                for first in range(0, count, 8):
                    indexes = [mirror(i, len(frames)) for i in range(first, min(first + 8, count))]
                    images = np.stack([face(i) for i in indexes])
                    masked = images.copy()
                    masked[:, 128:] = 0
                    image_batch = np.concatenate([masked, images], axis=3).astype(np.float32) / 255.0
                    chunks = []
                    for i in range(first, min(first + 8, count)):
                        start = min(int(i * 80 / 25), mel.shape[1] - 16)
                        chunks.append(mel[:, start:start + 16])
                    mel_batch = np.stack(chunks)[:, None].astype(np.float32)
                    t0 = time.perf_counter()
                    with torch.inference_mode():
                        predicted = model(torch.from_numpy(mel_batch).cuda(), torch.from_numpy(image_batch.transpose(0, 3, 1, 2)).cuda())
                        predicted = predicted.cpu().numpy().transpose(0, 2, 3, 1) * 255
                    inference_seconds += time.perf_counter() - t0
                    for offset, (index, predicted_face) in enumerate(zip(indexes, predicted)):
                        original = frame(index).copy()
                        y1, y2, x1, x2 = (int(v) for v in coords[index])
                        if not (0 <= y1 < y2 <= height and 0 <= x1 < x2 <= width):
                            raise RuntimeError('Invalid face bounding box')
                        crop = predicted_face.astype(np.uint8)
                        seconds = (first+offset)/25
                        original[y1:y2, x1:x2] = blend_mouth(original[y1:y2, x1:x2], crop) if avatar_id == SHANIU_AVATAR else cv2.resize(crop, (x2-x1, y2-y1))
                        if scale < 1:
                            original = cv2.resize(original, (out_w, out_h))
                        if job.get('subtitles', True):
                            original = draw_caption(original, speech.cues, (first+offset)/25, bottom_margin=16 if avatar_id == SHANIU_AVATAR else None)
                        encoder.stdin.write(original.tobytes())
                encoder.stdin.close()
                if encoder.wait(timeout=60):
                    raise RuntimeError('Video encoder failed')
            except BaseException:
                encoder.kill()
                raise
        subprocess.run([ffmpeg, '-y', '-loglevel', 'error', '-i', str(silent_video), '-i', str(wav), '-c:v', 'copy', '-c:a', 'aac', '-shortest', '-movflags', '+faststart', str(output)], check=True, capture_output=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        shutil.copyfile(wav, output.with_suffix('.wav'))
        write_subtitles(output, speech.cues)
    return {'ok': True, 'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__, 'cuda': torch.version.cuda, 'frames': count, 'duration_seconds': round(count / 25, 2), 'resolution': [out_w, out_h], 'load_seconds': round(loaded-started, 2), 'inference_seconds': round(inference_seconds, 2), 'inference_fps': round(count / inference_seconds, 2), 'total_seconds': round(time.perf_counter()-started, 2), 'output_bytes': output.stat().st_size, 'speech_provider': speech.provider, 'voice': speech.voice, 'natural_speech': speech.natural, 'added_pause_seconds': speech.added_pause_seconds, 'subtitle_alignment': speech.alignment, 'subtitle_cues': len(speech.cues), 'subtitles': job.get('subtitles', True), 'warning': speech.warning}


if __name__ == '__main__':
    try:
        job = json.loads(sys.stdin.buffer.read().decode('utf-8'))
        if not isinstance(job.get('text'), str) or not 1 <= len(job['text']) <= 240:
            raise RuntimeError('Text length must be 1–240 characters')
        report = run(job)
        print(json.dumps(report, ensure_ascii=False), flush=True)
    except Exception as error:
        print(json.dumps({'ok': False, 'error_type': type(error).__name__, 'message': str(error) if isinstance(error, RuntimeError) else 'Media worker failed'}, ensure_ascii=False), flush=True)
        raise SystemExit(1)
