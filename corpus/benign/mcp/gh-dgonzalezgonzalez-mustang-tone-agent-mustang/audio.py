from __future__ import annotations

import math
from pathlib import Path
from threading import Event

import numpy as np
import sounddevice as sd
import soundfile as sf
from scipy import signal


def devices() -> list[dict]:
    return [
        {
            "index": i,
            "name": d["name"],
            "inputs": d["max_input_channels"],
            "rate": d["default_samplerate"],
            "hostapi": sd.query_hostapis(d["hostapi"])["name"],
        }
        for i, d in enumerate(sd.query_devices())
        if d["max_input_channels"] > 0
    ]


def fender_device() -> dict:
    candidates = [d for d in devices() if "Fender Mustang" in d["name"]]
    candidates.sort(key=lambda d: ("WASAPI" not in d["hostapi"], "MME" not in d["hostapi"]))
    if not candidates:
        raise RuntimeError("Fender Mustang USB audio input not connected. No microphone fallback is used.")
    return candidates[0]


def record(path: Path, seconds: int, cancel: Event, progress=lambda _: None, loopback=False):
    for remaining in (3, 2, 1):
        progress(f"Ready in {remaining}")
        if cancel.wait(1):
            raise RuntimeError("Recording cancelled")
    progress("Recording — play the same phrase" if not loopback else "Recording computer playback")
    if loopback:
        import soundcard as sc

        speaker = sc.default_speaker()
        mic = sc.get_microphone(speaker.id, include_loopback=True)
        parts = []
        with mic.recorder(samplerate=44100) as recorder:
            for _ in range(seconds * 4):
                if cancel.is_set():
                    raise RuntimeError("Recording cancelled")
                parts.append(recorder.record(numframes=11025))
        audio, rate, name = np.concatenate(parts), 44100, "Windows playback loopback"
    else:
        device = fender_device()
        rate, name = int(device["rate"]), device["name"]
        channels = min(2, device["inputs"])
        parts = []
        with sd.InputStream(
            device=device["index"], samplerate=rate, channels=channels, dtype="float32"
        ) as stream:
            for _ in range(seconds * 4):
                if cancel.is_set():
                    raise RuntimeError("Recording cancelled")
                chunk, overflow = stream.read(rate // 4)
                if overflow:
                    raise RuntimeError("USB recording overflow; close other audio applications and retry")
                parts.append(chunk)
        audio = np.concatenate(parts)
    sf.write(path, audio, rate, subtype="FLOAT")
    return {"device": name, "rate": rate, "seconds": seconds, **features(audio, rate)}


def features(audio: np.ndarray, rate: int) -> dict:
    audio = np.asarray(audio, dtype=float)
    if audio.ndim == 1:
        audio = audio[:, None]
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Empty or invalid audio")
    peak = float(np.max(np.abs(audio)))
    rms = float(np.sqrt(np.mean(audio**2)))
    clipped = float(np.mean(np.abs(audio) >= 0.999))
    quality = []
    if rms < 0.0003:
        quality.append("silence_or_too_quiet")
    if clipped > 0.001:
        quality.append("clipping")
    if len(audio) / rate < 4:
        quality.append("too_short")
    mono = audio.mean(axis=1)
    # Window power is averaged per channel, avoiding stereo phase-cancellation in tonal measurements.
    frequency, power = signal.welch(audio, fs=rate, nperseg=min(4096, len(audio)), axis=0)
    power = power.mean(axis=1)
    edges = np.geomspace(80, min(10000, rate / 2), 25)
    bands = [float(power[(frequency >= a) & (frequency < b)].sum()) for a, b in zip(edges[:-1], edges[1:])]
    relative = np.array(bands) / max(float(np.sum(bands)), 1e-30)
    spectral = 10 * np.log10(np.maximum(relative, 1e-12))
    spectral -= spectral.mean()
    frame = max(1, int(rate * 0.025))
    trim = len(mono) // frame * frame
    envelope = np.sqrt(np.mean(mono[:trim].reshape(-1, frame) ** 2, axis=1))
    active = envelope[envelope > max(rms * 0.15, 0.0001)]
    if len(active) < 20:
        quality.append("insufficient_playing")
    centroid = float((frequency * power).sum() / (power.sum() + 1e-15))
    stereo = 0.0
    if audio.shape[1] > 1 and rms > 1e-6:
        stereo = float(np.sqrt(np.mean((audio[:, 0] - audio[:, 1]) ** 2)) / (2 * rms))
    chroma = np.zeros(12)
    selected = (frequency >= 80) & (frequency <= 1200)
    notes = np.rint(69 + 12 * np.log2(frequency[selected] / 440)).astype(int) % 12
    np.add.at(chroma, notes, power[selected])
    chroma /= max(float(np.linalg.norm(chroma)), 1e-30)
    return {
        "valid": not quality,
        "issues": quality,
        "rms_db": round(20 * math.log10(rms + 1e-15), 2),
        "peak": round(peak, 5),
        "clipped_fraction": clipped,
        "spectral_db": spectral.round(3).tolist(),
        "centroid_hz": round(centroid, 1),
        "crest_db": round(20 * math.log10((peak + 1e-15) / (rms + 1e-15)), 3),
        "activity": round(float(np.mean(envelope > max(rms * 0.15, 0.0001))), 3),
        "stereo_width": round(stereo, 3),
        "pitch_profile": chroma.round(4).tolist(),
        "envelope_cv": round(float(np.std(active) / (np.mean(active) + 1e-15)) if len(active) else 0, 3),
    }


def contamination(take: Path, reference: Path) -> bool:
    """Detect nearly exact playback copies, rather than penalizing similar guitar timbre."""

    def load(path):
        values, rate = sf.read(path, always_2d=True)
        values = signal.resample_poly(values.mean(axis=1), 8000, rate)
        return values - values.mean()

    a, b = load(take), load(reference)
    short, long = (a, b) if len(a) <= len(b) else (b, a)
    energy = float(np.dot(short, short))
    if len(short) < 8000 or energy < 1e-10:
        return False
    correlation = signal.correlate(long, short, mode="valid", method="fft")
    running = np.concatenate(([0], np.cumsum(long**2)))
    denominator = np.sqrt(np.maximum(energy * (running[len(short) :] - running[: -len(short)]), 1e-20))
    return bool(np.max(np.abs(correlation) / denominator) > 0.92)


def comparable(a: dict, b: dict) -> bool:
    if "pitch_profile" not in a or "pitch_profile" not in b:
        return True
    return float(np.dot(a["pitch_profile"], b["pitch_profile"])) >= 0.45


def file_features(path: Path) -> dict:
    audio, rate = sf.read(path, always_2d=True)
    return {"rate": rate, "seconds": len(audio) / rate, **features(audio, rate)}


def distance(a: dict, b: dict) -> dict:
    if not a["valid"] or not b["valid"]:
        raise ValueError("Invalid audio cannot be compared")
    spectrum = float(np.mean(np.abs(np.array(a["spectral_db"]) - np.array(b["spectral_db"]))))
    dynamics = abs(a["crest_db"] - b["crest_db"])
    envelope = abs(a["envelope_cv"] - b["envelope_cv"])
    spatial = abs(a["stereo_width"] - b["stereo_width"])
    return {
        "distance": round(spectrum + 0.15 * dynamics + 0.2 * envelope + 0.2 * spatial, 4),
        "spectral_db": round(spectrum, 3),
        "crest_db": round(dynamics, 3),
        "envelope_cv": round(envelope, 3),
        "stereo_width": round(spatial, 3),
        "interpretation": "Lower is closer on these features; not a perceptual similarity percentage.",
        "limitations": [
            "Playing and pitch differences influence measurements",
            "Mixed or separated references may contain other instruments",
            "A listening comparison is required",
        ],
    }


def matched_audio(path: Path, destination: Path):
    audio, rate = sf.read(path, always_2d=True)
    rms = np.sqrt(np.mean(audio**2))
    audio *= min(0.08 / (rms + 1e-12), 0.95 / (np.max(np.abs(audio)) + 1e-12))
    sf.write(destination, audio, rate, subtype="PCM_24")
