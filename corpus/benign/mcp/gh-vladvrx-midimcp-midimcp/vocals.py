"""Preserve recorded vocal performances and mix them without pitch/time edits."""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import math
from pathlib import Path
import shutil

import numpy as np
import soundfile as sf

MAX_SECONDS = 1200
MAX_BYTES = 512 * 1024 * 1024
BLOCK = 65536
PROVENANCE = {"user_supplied_stem", "separated_from_mix"}


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _offset(value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value) or not 0 <= value <= MAX_SECONDS:
        raise ValueError("timeline_start_seconds must be finite and between 0 and 1200")
    return float(value)


def _inspect(path: Path) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("Audio must be a file no larger than 512 MiB")
    with sf.SoundFile(path) as stream:
        if not 1 <= stream.channels <= 2 or not 8000 <= stream.samplerate <= 192000:
            raise ValueError("Audio requires mono/stereo and a sample rate from 8000 to 192000")
        if not 0 < stream.frames <= min(60_000_000, stream.samplerate * MAX_SECONDS):
            raise ValueError("Audio must be nonempty and bounded to 1200 seconds / 60 million frames")
        peak = 0.0
        for block in stream.blocks(blocksize=BLOCK, dtype="float64", always_2d=True):
            if not np.isfinite(block).all():
                raise ValueError("Audio contains nonfinite samples")
            peak = max(peak, float(np.max(np.abs(block))))
        return {"path": str(path), "sample_rate": stream.samplerate, "channels": stream.channels,
                "frames": stream.frames, "duration_seconds": stream.frames / stream.samplerate,
                "peak": peak, "silent": peak == 0.0, "sha256": _hash(path)}


def preserve_vocals(source: Path, output_dir: Path, provenance: str,
                    timeline_start_seconds: float = 0.0, original_mix: Path | None = None,
                    separation_model: str | None = None) -> dict:
    """Copy vocal audio byte-for-byte. Provenance is a caller declaration, not detection."""
    if provenance not in PROVENANCE:
        raise ValueError("provenance must be user_supplied_stem or separated_from_mix")
    offset = _offset(timeline_start_seconds)
    if provenance == "separated_from_mix" and (original_mix is None or not isinstance(separation_model, str) or not separation_model.strip()):
        raise ValueError("Separated vocals require original_mix and separation_model provenance")
    info = _inspect(source)
    mix = _inspect(original_mix) if original_mix is not None else None
    if offset + info["duration_seconds"] > MAX_SECONDS:
        raise ValueError("Vocal timeline exceeds 1200 seconds")
    output = Path(output_dir).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    target = output / ("preserved_vocals" + Path(info["path"]).suffix.lower())
    with Path(info["path"]).open("rb") as src, target.open("xb") as dst:
        shutil.copyfileobj(src, dst, length=1024 * 1024)
    if _hash(target) != info["sha256"]:
        raise ValueError("Source changed during preservation; copied asset is not verified")
    return {**info, "path": str(target), "source": info["path"], "source_sha256": info["sha256"],
            "role": "original_performance_audio", "provenance": provenance,
            "provenance_basis": "caller_declared", "original_mix": mix,
            "separation_model": separation_model, "timeline_start_seconds": offset,
            "byte_identical_copy": True, "synthesis_applied": False,
            "time_stretch_applied": False, "pitch_shift_applied": False,
            "warnings": (["Separated vocals may contain instrumental bleed or separation artifacts."]
                         if provenance == "separated_from_mix" else
                         ["User-supplied stem provenance is declared, not independently verified."])
                        + (["Vocal asset is silent."] if info["silent"] else [])}


def assemble_recreation(instrumental: Path, vocal_assets: list[dict], output_dir: Path) -> dict:
    """Mix preserved manifests on an explicit timeline; reject sample-rate mismatches.

    Writes floating-point instrumental, summed vocals, and complete mix. A common
    gain protects all three outputs from clipping; copied source assets stay raw.
    """
    if not isinstance(vocal_assets, list) or not 1 <= len(vocal_assets) <= 16:
        raise ValueError("Provide 1 to 16 preserved vocal asset manifests")
    backing = _inspect(instrumental)
    rate = backing["sample_rate"]
    assets = []
    for manifest in vocal_assets:
        if not isinstance(manifest, dict) or manifest.get("role") != "original_performance_audio" or manifest.get("provenance") not in PROVENANCE:
            raise ValueError("Expected preserved original-performance vocal manifest")
        if any(manifest.get(field) is not False for field in ("synthesis_applied", "time_stretch_applied", "pitch_shift_applied")):
            raise ValueError("Vocal manifest must explicitly declare no synthesis, stretching or pitch shift")
        info = _inspect(manifest["path"])
        if info["sha256"] != manifest.get("sha256"):
            raise ValueError("Preserved vocal asset hash does not match manifest")
        if info["sample_rate"] != rate:
            raise ValueError("Sample rates must match; resampling is not applied implicitly")
        offset = _offset(manifest.get("timeline_start_seconds", 0))
        assets.append({**info, "offset_frames": round(offset * rate), "requested_offset_seconds": offset,
                       "provenance": manifest["provenance"]})
    frames = max(backing["frames"], *(item["offset_frames"] + item["frames"] for item in assets))
    if frames > min(60_000_000, rate * MAX_SECONDS):
        raise ValueError("Combined timeline exceeds audio bounds")
    channels = max(backing["channels"], *(item["channels"] for item in assets))
    output = Path(output_dir).expanduser().resolve()
    paths = {key: output / f"{key}.wav" for key in ("instrumental", "vocals", "recreation")}
    if any(path.exists() for path in paths.values()):
        raise FileExistsError("Recreation outputs already exist")
    output.mkdir(parents=True, exist_ok=True)

    def blocks():
        with ExitStack() as stack:
            streams = [stack.enter_context(sf.SoundFile(item["path"])) for item in [backing, *assets]]
            for start in range(0, frames, BLOCK):
                count = min(BLOCK, frames - start)
                instrumental_block = np.zeros((count, channels))
                vocal_block = np.zeros_like(instrumental_block)
                for index, (item, stream) in enumerate(zip([backing, *assets], streams)):
                    offset = item.get("offset_frames", 0)
                    left, right = max(start, offset), min(start + count, offset + item["frames"])
                    if right <= left:
                        continue
                    stream.seek(left - offset)
                    chunk = stream.read(right - left, dtype="float64", always_2d=True)
                    if not np.isfinite(chunk).all():
                        raise ValueError("Audio changed or contains nonfinite samples")
                    target = instrumental_block if index == 0 else vocal_block
                    with np.errstate(over="raise", invalid="raise"):
                        try:
                            target[left-start:right-start] += chunk  # mono duplicates to stereo, without panning
                        except FloatingPointError:
                            raise ValueError("Audio sum exceeds finite numeric range") from None
                with np.errstate(over="raise", invalid="raise"):
                    try:
                        mixed = instrumental_block + vocal_block
                    except FloatingPointError:
                        raise ValueError("Audio sum exceeds finite numeric range") from None
                yield instrumental_block, vocal_block, mixed

    peaks = np.zeros(3)
    for chunks in blocks():
        peaks = np.maximum(peaks, [np.max(np.abs(chunk)) for chunk in chunks])
    gain = min(1.0, 0.98 / max(float(peaks.max()), 1e-30))
    with ExitStack() as stack:
        streams = [stack.enter_context(sf.SoundFile(stack.enter_context(path.open("xb")), mode="w",
                    samplerate=rate, channels=channels, format="WAV", subtype="FLOAT")) for path in paths.values()]
        for chunks in blocks():
            for stream, chunk in zip(streams, chunks):
                stream.write(chunk * gain)
    # Detect concurrent input changes rather than certifying a mixed version.
    for item in [backing, *assets]:
        if _hash(Path(item["path"])) != item["sha256"]:
            raise ValueError("An input changed during assembly; outputs are not verified")
    return {"outputs": {key: {"path": str(path), "sha256": _hash(path)} for key, path in paths.items()},
            "instrumental_source": backing, "vocal_assets": assets, "sample_rate": rate,
            "channels": channels, "frames": frames, "duration_seconds": frames / rate,
            "common_gain": gain, "common_gain_db": 20 * math.log10(gain),
            "unscaled_peaks": dict(zip(paths, map(float, peaks))),
            "resampling_applied": False, "time_stretch_applied": False, "pitch_shift_applied": False,
            "warnings": ["Provenance is caller-declared; vocal isolation quality is not assessed.",
                         "Mono sources are duplicated to both channels when any source is stereo."]}
