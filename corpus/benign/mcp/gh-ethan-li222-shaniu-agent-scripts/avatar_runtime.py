"""Persistent CUDA renderer shared by the realtime service.

Upstream avatars use small warps; Shaniu preserves the photographed face contour.
An optional complete avatar under data/avatar/emotions/<emotion> overrides them.
"""
from pathlib import Path
import tempfile
import threading
from fractions import Fraction
from functools import lru_cache

import cv2
import numpy as np
import torch
from scipy.io import wavfile
from scipy.signal import resample_poly
from render_avatar import ROOT, CoordinateReader, reference_module, mirror
from speech import synthesize, SpeechCancelled, draw_caption
from shaniu.avatar_catalog import DEFAULT_AVATAR, SHANIU_AVATAR, avatar_root, avatar_ready, avatar_asset_root
from avatar_quality import blend_mouth


def expression(image, emotion, strength=1.0):
    """Local face-coordinate remap; preserve the outline and audio-driven mouth opening."""
    if emotion == 'cool' or strength <= 0:
        return image
    height, width = image.shape[:2]
    y, x = np.mgrid[0:height, 0:width].astype(np.float32)
    nx, ny = x / width, y / height
    lift = {'happy': .018, 'gentle': .007, 'shy': .01}.get(emotion, 0) * strength
    # Lift the two mouth corners without closing the central speaking mouth.
    corners = np.exp(-((nx-.34)**2 + (ny-.73)**2)/.003) + np.exp(-((nx-.66)**2 + (ny-.73)**2)/.003)
    result = cv2.remap(image, x, y + corners * height * lift, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)
    if emotion == 'shy':
        cheeks = np.exp(-((nx-.24)**2 + (ny-.59)**2)/.007) + np.exp(-((nx-.76)**2 + (ny-.59)**2)/.007)
        alpha = (cheeks * .08 * strength)[..., None]
        result = (result * (1-alpha) + np.array([105, 125, 220]) * alpha).clip(0, 255).astype(np.uint8)
    return result


class Runtime:
    def __init__(self, source, speech_config=None):
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable')
        torch.set_num_threads(4)
        self.speech_config = speech_config or {}
        model_type, self.audio = reference_module(Path(source))
        checkpoint = torch.load(ROOT / 'data/avatar/wav2lip.pth', map_location='cpu', weights_only=True)
        self.model = model_type().eval()
        self.model.load_state_dict({k.removeprefix('module.'): v for k, v in checkpoint['state_dict'].items()})
        self.model.cuda()
        self.lock = threading.Lock()
        self.avatar_id = DEFAULT_AVATAR
        with torch.inference_mode():
            self.model(torch.zeros(1, 1, 80, 16, device='cuda'), torch.zeros(1, 6, 256, 256, device='cuda'))
        self.asset('cool')

    @lru_cache(maxsize=4)
    def asset(self, emotion):
        custom = ROOT / 'data/avatar/emotions' / emotion if self.avatar_id == DEFAULT_AVATAR else avatar_root(self.avatar_id) / 'emotions' / emotion
        independent = all((custom / p).exists() for p in ['coords.pkl', 'full_imgs', 'face_imgs'])
        root = avatar_asset_root(self.avatar_id, emotion)
        frames = sorted(p for p in (root / 'full_imgs').iterdir() if p.suffix.lower() in {'.jpg', '.png'})
        faces = sorted(p for p in (root / 'face_imgs').iterdir() if p.suffix.lower() in {'.jpg', '.png'})
        with (root / 'coords.pkl').open('rb') as file:
            coords = CoordinateReader(file).load()
        if not frames or len(frames) != len(faces) or len(frames) != len(coords):
            raise RuntimeError('Invalid emotion avatar assets')
        return frames, faces, coords, independent

    def select_avatar(self, avatar_id):
        if not avatar_ready(avatar_id):
            raise RuntimeError('Avatar assets unavailable')
        with self.lock:
            self.avatar_id = avatar_id
            self.asset.cache_clear()
            self.read.cache_clear()
            self.asset('cool')

    @lru_cache(maxsize=48)
    def read(self, path, face=False):
        image = cv2.imread(str(path))
        if image is None:
            raise RuntimeError('Unreadable avatar image')
        return cv2.resize(image, (256, 256)) if face else image

    def compose(self, original, crop, coord, emotion, independent, strength, seconds=0):
        result = original.copy()
        y1, y2, x1, x2 = map(int, coord)
        if not (0 <= y1 < y2 <= result.shape[0] and 0 <= x1 < x2 <= result.shape[1]):
            raise RuntimeError('Invalid face coordinates')
        shaniu = self.avatar_id == SHANIU_AVATAR
        if shaniu:
            result[y1:y2, x1:x2] = blend_mouth(result[y1:y2, x1:x2], crop)
        else:
            crop = crop if independent else expression(crop, emotion, strength)
            result[y1:y2, x1:x2] = cv2.resize(crop, (x2-x1, y2-y1))
        scale = min(1, 640 / max(result.shape[:2]))
        size = (int(result.shape[1]*scale)//2*2, int(result.shape[0]*scale)//2*2)
        result = cv2.resize(result, size)
        return result

    def idle(self, emotion, strength=1):
        frames, faces, coords, independent = self.asset(emotion)
        if self.avatar_id == SHANIU_AVATAR:
            original = self.read(frames[0])
            scale = min(1, 640/max(original.shape[:2]))
            return cv2.resize(original, (int(original.shape[1]*scale)//2*2, int(original.shape[0]*scale)//2*2))
        return self.compose(self.read(frames[0]), self.read(faces[0], True), coords[0], emotion, independent, strength)

    def render(self, text, emotion, strength, stop, publish, subtitles=True, metadata=None, prepared=None, frame_offset=0):
        """Publish paired 40 ms frames with backpressure; stop between every batch/frame."""
        with self.lock, tempfile.TemporaryDirectory(prefix='rtc-', dir=ROOT / 'data/media') as folder:
            if stop.is_set():
                return
            wav = Path(folder) / 'voice.wav'
            try:
                speech = prepared.result if prepared else synthesize(text, wav, emotion, self.speech_config, stop)
                wav = speech.path
            except SpeechCancelled:
                return
            if metadata:
                metadata(dict(speech_provider=speech.provider, voice=speech.voice, natural_speech=speech.natural, added_pause_seconds=speech.added_pause_seconds, subtitle_alignment=speech.alignment, subtitle_cues=len(speech.cues), warning=speech.warning))
            rate, samples = wavfile.read(wav)
            samples = samples.astype(np.float32) / 32768
            if samples.ndim > 1:
                samples = samples.mean(axis=1)
            ratio = Fraction(16000, rate)
            samples = resample_poly(samples, ratio.numerator, ratio.denominator).astype(np.float32)
            if not .1 <= len(samples)/16000 <= 45:
                raise RuntimeError('Sentence audio too long')
            mel = self.audio.melspectrogram(samples)
            if not np.isfinite(mel).all():
                raise RuntimeError('Invalid audio features')
            if mel.shape[1] < 16:
                mel = np.pad(mel, ((0, 0), (0, 16-mel.shape[1])), mode='edge')
            frames, faces, coords, independent = self.asset(emotion)
            count = int(np.ceil(len(samples)/640))
            pcm = (np.clip(samples, -1, 1)*32767).astype(np.int16)
            pcm = np.pad(pcm, (0, count*640-len(pcm)))
            for first in range(0, count, 8):
                if stop.is_set():
                    return
                indexes = [mirror(i+frame_offset, len(frames)) for i in range(first, min(first+8, count))]
                images = np.stack([self.read(faces[i], True) for i in indexes])
                masked = images.copy()
                masked[:, 128:] = 0
                batch = np.concatenate([masked, images], axis=3).astype(np.float32)/255
                starts = [min(int(i*80/25), mel.shape[1]-16) for i in range(first, min(first+8, count))]
                chunks = np.stack([mel[:, i:i+16] for i in starts])[:, None].astype(np.float32)
                with torch.inference_mode():
                    predictions = self.model(torch.from_numpy(chunks).cuda(), torch.from_numpy(batch.transpose(0, 3, 1, 2)).cuda()).cpu().numpy().transpose(0, 2, 3, 1)
                for offset, (index, predicted) in enumerate(zip(indexes, predictions)):
                    if stop.is_set():
                        return
                    image = self.compose(self.read(frames[index]), (predicted*255).clip(0, 255).astype(np.uint8), coords[index], emotion, independent, strength, (frame_offset+first+offset)*.04)
                    if subtitles:
                        image = draw_caption(image, speech.cues, (first+offset)*.04, bottom_margin=16 if self.avatar_id == SHANIU_AVATAR else None)
                    if not publish(image, pcm[(first+offset)*640:(first+offset+1)*640]):
                        return
