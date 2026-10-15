"""Reading any audio or video file (ffmpeg for video), separating a voice from music (UVR MDX-Net through
sherpa-onnx, on the CPU), and finding the best stretch of speech in a long recording."""
import os
import shutil
import subprocess
import threading
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from . import config

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
VIDEO_EXT = {".mp4", ".mkv", ".mov", ".webm", ".avi", ".m4v", ".wmv", ".flv", ".ts", ".m4a", ".aac", ".wma", ".opus"}


class MediaError(Exception):
    pass


def ffmpeg_exe() -> str | None:
    """The app's own ffmpeg (Setup / Models download), else one already on the PC."""
    own = config.tool_dir("ffmpeg") / "ffmpeg.exe"
    if own.exists():
        return str(own)
    return shutil.which("ffmpeg")


def ffmpeg_source() -> str | None:
    """'app', 'system' or None."""
    if (config.tool_dir("ffmpeg") / "ffmpeg.exe").exists():
        return "app"
    return "system" if shutil.which("ffmpeg") else None


def decode(path: Path, sr: int | None = None, mono: bool = True) -> tuple[np.ndarray, int]:
    """Any audio or video file -> float32 samples. WAV/MP3/FLAC/OGG are read directly; everything else (MP4, M4A,
    MKV…) goes through ffmpeg. With `sr`, the result is resampled to it (ffmpeg needed unless it already matches)."""
    path = Path(path)
    if path.suffix.lower() not in VIDEO_EXT:
        try:
            data, file_sr = sf.read(str(path), dtype="float32", always_2d=True)
            if sr is None or sr == file_sr:
                data = data.mean(axis=1) if mono else data
                return np.ascontiguousarray(data, dtype=np.float32), file_sr
        except Exception:
            pass  # not something libsndfile reads: try ffmpeg
    exe = ffmpeg_exe()
    if not exe:
        raise MediaError("Reading this file needs ffmpeg (for video and some audio formats). "
                         "Download it on the Models page (Tools), then try again.")
    tmp = config.DATA / "tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    out = tmp / f"dec-{uuid.uuid4().hex[:10]}.wav"
    args = [exe, "-nostdin", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1" if mono else "2",
            "-ar", str(sr or 44100), "-c:a", "pcm_s16le", str(out)]
    try:
        p = subprocess.run(args, capture_output=True, timeout=3600, creationflags=NO_WINDOW)
        if p.returncode or not out.exists():
            msg = (p.stderr or b"").decode("utf-8", "replace").strip().splitlines()
            raise MediaError("ffmpeg couldn't read that file" + (f": {msg[-1]}" if msg else "."))
        data, file_sr = sf.read(str(out), dtype="float32", always_2d=True)
    finally:
        out.unlink(missing_ok=True)
    data = data.mean(axis=1) if mono else data
    if not len(data):
        raise MediaError("That file has no audio track.")
    return np.ascontiguousarray(data, dtype=np.float32), file_sr


def to_wav16k(path: Path, out: Path) -> float:
    """Convert anything to the 16 kHz mono WAV Whisper wants; returns the duration in seconds."""
    data, sr = decode(path, sr=16000) if ffmpeg_exe() else decode(path)
    if sr != 16000:  # no ffmpeg, but a file libsndfile reads: resample in numpy
        n = int(round(len(data) * 16000 / sr))
        data = np.interp(np.linspace(0, len(data) - 1, n), np.arange(len(data)), data).astype(np.float32)
        sr = 16000
    sf.write(str(out), data, sr, subtype="PCM_16")
    return len(data) / sr


# ---- voice separation ---------------------------------------------------------------

_separator = None
_sep_lock = threading.Lock()


def separator_ready(cfg: dict) -> bool:
    return "uvr-vocals" in config.installed_models(cfg)


def separate_voice(audio: np.ndarray, sr: int, cfg: dict) -> tuple[np.ndarray, int]:
    """Keep the voice, drop music and background sound. Returns mono vocals and their sample rate (44.1 kHz)."""
    global _separator
    if not separator_ready(cfg):
        raise MediaError("The voice separator isn't downloaded. Get it on the Models page (Voice separator).")
    import sherpa_onnx
    with _sep_lock:  # one at a time; the model uses most CPU cores
        if _separator is None:
            model = Path(cfg["models_dir"]).resolve() / config.MODELS["uvr-vocals"]["files"][0]
            c = sherpa_onnx.OfflineSourceSeparationConfig(model=sherpa_onnx.OfflineSourceSeparationModelConfig(
                uvr=sherpa_onnx.OfflineSourceSeparationUvrModelConfig(model=str(model)),
                num_threads=max(2, (os.cpu_count() or 4) - 2), debug=False, provider="cpu"))
            if not c.validate():
                raise MediaError("The voice separator model didn't load. Download it again on the Models page.")
            _separator = sherpa_onnx.OfflineSourceSeparation(c)
        stereo = np.stack([audio, audio]) if audio.ndim == 1 else audio.T
        out = _separator.process(sample_rate=sr, samples=np.ascontiguousarray(stereo, dtype=np.float32))
    vocals = np.asarray(out.stems[0].data, dtype=np.float32).mean(axis=0)
    return vocals, out.sample_rate


# ---- picking the best stretch of speech ------------------------------------------------

def best_window(audio: np.ndarray, sr: int, seconds: float = 12.0) -> tuple[float, float]:
    """The `seconds`-long stretch with the most steady speech (few silences, no clipping), starting and ending
    at quiet moments. Returns (start, end) in seconds."""
    total = len(audio) / sr
    if total <= seconds + 2:
        return 0.0, total
    hop = int(0.05 * sr)
    n = len(audio) // hop
    frames = audio[: n * hop].reshape(n, hop)
    db = 20 * np.log10(np.sqrt((frames.astype(np.float64) ** 2).mean(axis=1)) + 1e-9)
    loud = db > (np.percentile(db, 95) - 30)          # frames with speech
    clipped = (np.abs(frames) > 0.99).any(axis=1)
    w = int(seconds / 0.05)
    score = np.convolve(loud.astype(float) - 2 * clipped, np.ones(w), mode="valid")
    start = int(np.argmax(score))
    # snap both ends to the quietest frame nearby (within 0.5 s), so no word is cut
    def quiet_near(i):
        lo, hi = max(0, i - 10), min(n - 1, i + 10)
        return lo + int(np.argmin(db[lo:hi + 1]))
    s, e = quiet_near(start), quiet_near(min(n - 1, start + w))
    return round(s * 0.05, 2), round(e * 0.05, 2)
