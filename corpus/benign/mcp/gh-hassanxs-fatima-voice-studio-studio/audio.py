"""Audio helpers in plain numpy: reading, trimming, loudness (ITU-R BS.1770), limiting, noise reduction,
stitching segments, and writing WAV / MP3."""
import io
import math
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 24000  # what the voice models produce


def load(path_or_bytes, mono: bool = True) -> tuple[np.ndarray, int]:
    """Read WAV / FLAC / OGG / MP3 into float32 (mono by default)."""
    src = io.BytesIO(path_or_bytes) if isinstance(path_or_bytes, (bytes, bytearray)) else str(path_or_bytes)
    try:
        data, sr = sf.read(src, dtype="float32", always_2d=True)
    except Exception as e:
        raise ValueError("That file isn't audio this app can read (use WAV, MP3, FLAC or OGG).") from e
    data = data.mean(axis=1) if mono else data
    return np.ascontiguousarray(data, dtype=np.float32), sr


def save_wav(path: Path, audio: np.ndarray, sr: int) -> None:
    tmp = Path(path).with_suffix(".tmp.wav")
    sf.write(str(tmp), np.clip(audio, -1, 1), sr, subtype="PCM_16")
    tmp.replace(path)


def mp3_bytes(audio: np.ndarray, sr: int, bitrate: int = 128) -> bytes:
    import lameenc
    if sr < 32000:  # MPEG-2 rates (16/22.05/24 kHz) top out at 160 kbps
        bitrate = min(bitrate, 160)
    enc = lameenc.Encoder()
    enc.set_bit_rate(int(bitrate))
    enc.set_in_sample_rate(sr)
    enc.set_channels(1)
    enc.set_quality(2)  # 2 = high quality, slower
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2").tobytes()
    return bytes(enc.encode(pcm) + enc.flush())


def save_mp3(path: Path, audio: np.ndarray, sr: int, bitrate: int = 128) -> None:
    tmp = Path(path).with_suffix(".tmp.mp3")
    tmp.write_bytes(mp3_bytes(audio, sr, bitrate))
    tmp.replace(path)


def wav_bytes(audio: np.ndarray, sr: int) -> bytes:
    out = io.BytesIO()
    sf.write(out, np.clip(audio, -1, 1), sr, format="WAV", subtype="PCM_16")
    return out.getvalue()


def duration(path: Path) -> float:
    info = sf.info(str(path))
    return info.frames / info.samplerate


# ---- silence ----------------------------------------------------------------

def _frame_db(audio: np.ndarray, sr: int, ms: float = 10) -> tuple[np.ndarray, int]:
    hop = max(1, int(sr * ms / 1000))
    n = len(audio) // hop
    if n == 0:
        return np.array([-120.0]), hop
    frames = audio[: n * hop].reshape(n, hop)
    rms = np.sqrt(np.mean(frames.astype(np.float64) ** 2, axis=1) + 1e-12)
    return 20 * np.log10(rms), hop


def trim_silence(audio: np.ndarray, sr: int, threshold_db: float = -45, pad_ms: float = 40) -> np.ndarray:
    """Cut quiet lead-in and tail. The threshold is relative to the loudest 10 ms of the clip."""
    db, hop = _frame_db(audio, sr)
    loud = np.nonzero(db > db.max() + threshold_db)[0]
    if len(loud) == 0:
        return audio
    pad = int(sr * pad_ms / 1000)
    start = max(0, loud[0] * hop - pad)
    end = min(len(audio), (loud[-1] + 1) * hop + pad)
    return audio[start:end]


def silence(seconds: float, sr: int) -> np.ndarray:
    return np.zeros(int(round(max(0.0, seconds) * sr)), dtype=np.float32)


def fade(audio: np.ndarray, sr: int, ms: float = 8) -> np.ndarray:
    """Short fades so cuts never click."""
    n = min(len(audio) // 2, int(sr * ms / 1000))
    if n > 1:
        audio = audio.copy()
        ramp = np.linspace(0, 1, n, dtype=np.float32)
        audio[:n] *= ramp
        audio[-n:] *= ramp[::-1]
    return audio


def stitch(parts: list[tuple[np.ndarray, float]], sr: int) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """[(audio, pause_after_seconds)] -> one track, plus each part's (start, end) time in it.
    Each part's own leading/trailing silence is trimmed first so the pauses are exactly what was asked."""
    out, spans, t = [], [], 0.0
    for audio, pause in parts:
        a = fade(trim_silence(audio, sr), sr)
        spans.append((t, t + len(a) / sr))
        out += [a, silence(pause, sr)]
        t += len(a) / sr + len(out[-1]) / sr
    if not out:
        return np.zeros(0, dtype=np.float32), []
    return np.concatenate(out), spans


# ---- speed (WSOLA time-stretch: faster or slower, same pitch) -------------------

def time_stretch(audio: np.ndarray, sr: int, rate: float) -> np.ndarray:
    """Speed speech up (rate > 1) or slow it down (rate < 1) without changing the voice's pitch.
    WSOLA: overlap-add short windows taken from the input at the new pace, each one nudged (within a few ms)
    to where it best continues the previous window, so the waveform stays smooth."""
    if abs(rate - 1.0) < 0.005 or len(audio) < sr // 10:
        return audio
    n = int(0.030 * sr) // 2 * 2         # 30 ms windows
    hs = n // 2                          # output hop (50% overlap)
    ha = hs * rate                       # input hop
    tol = int(0.008 * sr)                # how far a window may be nudged
    win = np.hanning(n).astype(np.float32)
    pad = tol + n
    x = np.concatenate([np.zeros(pad, np.float32), audio.astype(np.float32), np.zeros(pad + n, np.float32)])
    frames = int((len(audio) / rate) / hs) + 1
    out = np.zeros(frames * hs + n, dtype=np.float32)
    norm = np.zeros_like(out)
    nfft = 1 << int(np.ceil(np.log2(n + 2 * tol + n)))
    prev = pad
    for k in range(frames):
        ideal = int(pad + k * ha)
        if k == 0:
            pos = ideal
        else:
            natural = x[prev + hs: prev + hs + n]
            lo = max(0, ideal - tol)
            region = x[lo: lo + n + 2 * tol]
            if len(region) < n + 2 * tol or not natural.any():
                pos = ideal
            else:
                corr = np.fft.irfft(np.fft.rfft(region, nfft) * np.conj(np.fft.rfft(natural, nfft)), nfft)[: 2 * tol + 1]
                pos = lo + int(np.argmax(corr))
        seg = x[pos: pos + n]
        if len(seg) < n:
            break
        out[k * hs: k * hs + n] += seg * win
        norm[k * hs: k * hs + n] += win
        prev = pos
    out = out / np.maximum(norm, 1e-3)
    return out[: int(round(len(audio) / rate))].astype(np.float32)


# ---- loudness (ITU-R BS.1770-4) ----------------------------------------------

def _k_weighting_power(freqs: np.ndarray, sr: int) -> np.ndarray:
    """|H(f)|² of the BS.1770 K-weighting (high shelf + high pass), designed for this sample rate."""
    def biquad_resp(b, a):
        z = np.exp(-1j * 2 * np.pi * freqs / sr)
        return (b[0] + b[1] * z + b[2] * z * z) / (a[0] + a[1] * z + a[2] * z * z)

    # High shelf: +4 dB above ~1.5 kHz (same design as pyloudnorm / libebur128)
    G, Q, fc = 3.99984385397, 0.7071752369554193, 1681.9744509555319
    A = 10 ** (G / 40)
    w0 = 2 * np.pi * fc / sr
    alpha = np.sin(w0) / (2 * Q)
    cw = np.cos(w0)
    b1 = [A * ((A + 1) + (A - 1) * cw + 2 * np.sqrt(A) * alpha), -2 * A * ((A - 1) + (A + 1) * cw),
          A * ((A + 1) + (A - 1) * cw - 2 * np.sqrt(A) * alpha)]
    a1 = [(A + 1) - (A - 1) * cw + 2 * np.sqrt(A) * alpha, 2 * ((A - 1) - (A + 1) * cw),
          (A + 1) - (A - 1) * cw - 2 * np.sqrt(A) * alpha]
    # High pass at ~38 Hz
    Q2, fc2 = 0.5003270373253953, 38.13547087613982
    w0 = 2 * np.pi * fc2 / sr
    alpha = np.sin(w0) / (2 * Q2)
    cw = np.cos(w0)
    b2 = [(1 + cw) / 2, -(1 + cw), (1 + cw) / 2]
    a2 = [1 + alpha, -2 * cw, 1 - alpha]
    return np.abs(biquad_resp(b1, a1) * biquad_resp(b2, a2)) ** 2


def loudness(audio: np.ndarray, sr: int) -> float:
    """Integrated loudness in LUFS (mono), with the standard -70 LUFS and relative -10 LU gates.
    Each 400 ms block's K-weighted power is taken in the frequency domain (Parseval)."""
    block, hop = int(0.4 * sr), int(0.1 * sr)
    if len(audio) < block:
        audio = np.pad(audio, (0, block - len(audio)))
    weights = _k_weighting_power(np.fft.rfftfreq(block, 1 / sr), sr)
    n_blocks = 1 + (len(audio) - block) // hop
    powers = np.empty(n_blocks)
    step = 512  # blocks per batch, to keep memory small on long tracks
    for i in range(0, n_blocks, step):
        idx = np.arange(i, min(n_blocks, i + step))[:, None] * hop + np.arange(block)[None, :]
        spec = np.fft.rfft(audio[idx].astype(np.float64), axis=1)
        p = (np.abs(spec) ** 2) * weights
        p[:, 1:-1] *= 2  # one-sided spectrum
        powers[i:i + len(idx)] = p.sum(axis=1) / block ** 2
    lufs = lambda p: -0.691 + 10 * np.log10(p + 1e-20)
    gated = powers[lufs(powers) > -70]
    if len(gated) == 0:
        return -70.0
    rel = lufs(gated.mean()) - 10
    gated = gated[lufs(gated) > rel]
    return float(lufs(gated.mean())) if len(gated) else -70.0


def limit(audio: np.ndarray, sr: int, ceiling_db: float = -1.0, lookahead_ms: float = 5, release_ms: float = 60) -> np.ndarray:
    """Peak limiter: smooth gain reduction wherever a peak would pass the ceiling."""
    ceiling = 10 ** (ceiling_db / 20)
    peak = np.abs(audio)
    if peak.max() <= ceiling:
        return audio
    need = np.minimum(1.0, ceiling / np.maximum(peak, 1e-9))
    # Spread each reduction over the lookahead window (running minimum), then smooth the release.
    w = max(1, int(sr * lookahead_ms / 1000))
    n = -(-len(need) // w)
    padded = np.pad(need, (0, n * w - len(need)), constant_values=1.0).reshape(n, w).min(axis=1)
    padded = np.minimum(padded, np.concatenate([padded[1:], [1.0]]))  # also cover the block before
    padded = np.minimum(padded, np.concatenate([[1.0], padded[:-1]]))
    gain = np.repeat(padded, w)[: len(audio)]
    r = max(1, int(sr * release_ms / 1000))
    c = np.concatenate([[0.0], np.cumsum(gain, dtype=np.float64)])  # centred moving average via a running sum
    lo = np.clip(np.arange(len(gain)) - r // 2, 0, len(gain))
    hi = np.clip(lo + r, 0, len(gain))
    smooth = (c[hi] - c[lo]) / np.maximum(hi - lo, 1)
    gain = np.minimum(gain, smooth)  # never less reduction than needed, release eased
    out = audio * gain.astype(np.float32)
    return np.clip(out, -ceiling, ceiling)


def normalize(audio: np.ndarray, sr: int, target_lufs: float = -16.0, ceiling_db: float = -1.5) -> tuple[np.ndarray, float]:
    # -1.5 dBFS sample peaks keep the true peak (between samples, after MP3 encoding) under -1 dBTP.
    """Bring speech to a target loudness (YouTube voiceovers: -16 to -14 LUFS), with a peak ceiling.
    Returns the audio and the loudness it had before."""
    before = loudness(audio, sr)
    if before <= -69:
        return audio, before
    gain = 10 ** ((target_lufs - before) / 20)
    return limit((audio * gain).astype(np.float32), sr, ceiling_db), before


def peak_normalize(audio: np.ndarray, peak_db: float = -1.0) -> np.ndarray:
    p = float(np.abs(audio).max()) if len(audio) else 0.0
    return audio if p < 1e-6 else (audio * (10 ** (peak_db / 20) / p)).astype(np.float32)


# ---- noise reduction (for reference clips) -------------------------------------

def denoise(audio: np.ndarray, sr: int, strength: float = 1.0) -> np.ndarray:
    """Spectral gating: learn the noise floor from the quietest moments, then turn down whatever sits near it."""
    n_fft = 1024 if sr >= 22050 else 512
    hop = n_fft // 4
    if len(audio) < n_fft * 4:
        return audio
    win = np.hanning(n_fft).astype(np.float32)
    pad = np.pad(audio, (n_fft, n_fft))
    n = 1 + (len(pad) - n_fft) // hop
    idx = np.arange(n)[:, None] * hop + np.arange(n_fft)[None, :]
    spec = np.fft.rfft(pad[idx] * win, axis=1)
    mag = np.abs(spec)
    # Noise profile per frequency: the level of the quietest 10% of frames.
    frame_energy = mag.mean(axis=1)
    quiet = mag[frame_energy <= np.percentile(frame_energy, 10)]
    noise = quiet.mean(axis=0) if len(quiet) else np.percentile(mag, 10, axis=0)
    snr = mag / (noise[None, :] * (1.5 + strength) + 1e-9)
    gain = np.clip((snr - 1) / (snr + 1e-9), 0, 1) ** 0.5
    floor = 10 ** (-(10 + 10 * strength) / 20)  # never fully silent: avoids "underwater" artefacts
    gain = np.maximum(gain, floor)
    # Smooth the mask over time and frequency to avoid musical noise.
    k = np.ones(3) / 3
    gain = np.apply_along_axis(lambda g: np.convolve(g, k, mode="same"), 0, gain)
    gain = np.apply_along_axis(lambda g: np.convolve(g, k, mode="same"), 1, gain)
    frames = np.fft.irfft(spec * gain, n=n_fft, axis=1) * win
    out = np.zeros(len(pad), dtype=np.float64)
    norm = np.zeros(len(pad), dtype=np.float64)
    for i in range(n):  # overlap-add
        out[i * hop:i * hop + n_fft] += frames[i]
        norm[i * hop:i * hop + n_fft] += win ** 2
    out = out / np.maximum(norm, 1e-6)
    return out[n_fft:n_fft + len(audio)].astype(np.float32)


def noise_level(audio: np.ndarray, sr: int) -> float:
    """Rough signal-to-noise ratio in dB (loud frames vs quiet frames); under ~25 dB the clip sounds noisy."""
    db, _ = _frame_db(audio, sr, ms=20)
    if len(db) < 10:
        return 60.0
    return float(np.percentile(db, 95) - np.percentile(db, 10))


def clip_report(audio: np.ndarray, sr: int) -> dict:
    """What a reference clip is like: length, loudness, noise, clipping."""
    dur = len(audio) / sr
    peak = float(np.abs(audio).max()) if len(audio) else 0.0
    return {"seconds": round(dur, 1), "snr_db": round(noise_level(audio, sr), 1),
            "clipped": bool(np.mean(np.abs(audio) > 0.995) > 0.001),
            "peak_db": round(20 * math.log10(peak), 1) if peak > 0 else -120.0}
