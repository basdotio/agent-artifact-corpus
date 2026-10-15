"""Bounded offline level inspection and transparent constant-gain matching.

LUFS: optional pyloudnorm BS.1770 meter. Oversampled peaks are estimates from
SciPy's 4x polyphase interpolation, not a certified true-peak meter.
"""
from pathlib import Path
import hashlib
import math
import warnings

import numpy as np
from scipy import signal
import soundfile as sf

CEILING_DB = -0.1


def _db(value):
    return float(20 * np.log10(value)) if value > 0 else None


def _read(path):
    path = Path(path).expanduser().resolve(strict=True)
    info = sf.info(path)
    if info.channels not in (1, 2) or not 8000 <= info.samplerate <= 192000:
        raise ValueError("Only mono/stereo audio at 8–192 kHz is supported")
    if info.frames <= 0 or info.frames > 30_000_000 or info.duration > 1800:
        raise ValueError("Audio must be nonempty and within 30 million frames / 30 minutes")
    audio, rate = sf.read(path, always_2d=True, dtype="float64")
    if not np.isfinite(audio).all():
        raise ValueError("Audio contains nonfinite samples")
    return path, audio, rate


def _peak4(audio, rate):
    peak = float(np.max(np.abs(audio)))
    step = rate * 10
    # Overlap protects chunk boundaries from interpolation padding artifacts.
    for start in range(0, len(audio), step):
        stop = min(len(audio), start + step)
        lo, hi = max(0, start - 64), min(len(audio), stop + 64)
        expanded = signal.resample_poly(audio[lo:hi], 4, 1, axis=0)
        selected = expanded[(start-lo)*4:(stop-lo)*4]
        peak = max(peak, float(np.max(np.abs(selected))))
    return peak


def _blocks(audio, rate):
    size = round(rate * .4)
    return np.array([np.sqrt(np.mean(audio[i:i+size] ** 2)) for i in range(0, len(audio), size)])


def _measure(audio, rate):
    peak = float(np.max(np.abs(audio)))
    true_peak = _peak4(audio, rate)
    rms = float(np.sqrt(np.mean(audio ** 2)))
    loudness, reason = None, None
    try:
        import pyloudnorm
    except ImportError:
        reason = "Reinstall MidiMCP dependencies; pyloudnorm is required for integrated LUFS"
    else:
        if len(audio) < round(.4 * rate):
            reason = "Integrated LUFS needs at least 400 ms"
        elif peak == 0:
            reason = "Silence has no finite integrated LUFS"
        else:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", RuntimeWarning)
                value = float(pyloudnorm.Meter(rate).integrated_loudness(audio))
            if math.isfinite(value):
                loudness = value
            else:
                reason = "Audio is below the loudness meter's absolute gate"
    blocks = _blocks(audio, rate)
    active = np.flatnonzero(blocks > max(float(blocks.max()) * 10**(-45/20), 1e-9))
    return {"duration_seconds": len(audio)/rate, "sample_rate": rate, "channels": audio.shape[1],
            "rms_dbfs": _db(rms), "sample_peak_dbfs": _db(peak),
            "oversampled_peak_estimate_dbtp": _db(true_peak), "oversampling_factor": 4,
            "integrated_lufs": loudness, "lufs_unavailable_reason": reason,
            "samples_at_or_above_full_scale": int(np.count_nonzero(np.abs(audio) >= 1)),
            "active_window_seconds": [float(active[0]*.4), min(float((active[-1]+1)*.4), len(audio)/rate)] if len(active) else None,
            "window_rms_dbfs": [_db(float(v)) for v in blocks], "window_seconds": .4,
            "warnings": ["Oversampled peak is a 4x interpolation estimate, not a certified true-peak measurement.",
                         "RMS, LUFS and peaks measure different properties; none is a musical similarity score."]}


def inspect_level(path) -> dict:
    """Inspect one complete mono/stereo file; null dB values mean silence/unavailable."""
    path, audio, rate = _read(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), **_measure(audio, rate)}


def match_level(reference, candidate, out, tolerance_db=.5, max_gain_db=24) -> dict:
    """Match corresponding complete files using LUFS and one constant gain.

    Requires equal duration within one sample and matching channel counts.
    Rejects silent/missing 400-ms candidate regions wherever reference is active.
    Output must be a new .wav path. Gain is capped at -0.1 dB estimated peak;
    unmet targets are reported, never hidden by limiting or compression.
    """
    for name, value, high in (("tolerance_db", tolerance_db, 6), ("max_gain_db", max_gain_db, 60)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= high:
            raise ValueError(f"{name} must be finite between 0 and {high}")
    ref_path, ref, ref_rate = _read(reference)
    cand_path, cand, rate = _read(candidate)
    output = Path(out).expanduser().resolve()
    if output in (ref_path, cand_path) or output.exists() or output.suffix.lower() != ".wav":
        raise ValueError("out must be a new WAV path, preserving both sources")
    if ref.shape[1] != cand.shape[1]:
        raise ValueError("Corresponding files must have the same channel count")
    if abs(len(ref)/ref_rate-len(cand)/rate) > max(1/ref_rate, 1/rate) + 1e-10:
        raise ValueError("Corresponding files must cover the same duration; extract matching windows first")
    before, target = _measure(cand, rate), _measure(ref, ref_rate)
    if target["integrated_lufs"] is None or before["integrated_lufs"] is None:
        raise ValueError("Finite integrated LUFS required: " + str(target["lufs_unavailable_reason"] or before["lufs_unavailable_reason"]))
    rb, cb = _blocks(ref, ref_rate), _blocks(cand, rate)
    count = min(len(rb), len(cb))
    reference_active = rb[:count] > max(float(rb.max()) * 10**(-45/20), 1e-9)
    candidate_active = cb[:count] > max(float(cb.max()) * 10**(-55/20), 1e-10)
    missing = np.flatnonzero(reference_active & ~candidate_active)
    if len(missing):
        raise ValueError(f"Candidate missing active reference coverage in {len(missing)} corresponding 400-ms windows")
    requested = target["integrated_lufs"] - before["integrated_lufs"]
    peak_limit = CEILING_DB - before["oversampled_peak_estimate_dbtp"]
    applied = min(requested, max_gain_db, peak_limit)
    capped = []
    if requested > max_gain_db:
        capped.append("maximum_gain")
    if requested > peak_limit:
        capped.append("estimated_peak_ceiling")
    output.parent.mkdir(parents=True, exist_ok=True)
    result_audio = cand * 10**(applied/20)
    # Exclusive file handle avoids overwriting a path created concurrently.
    with output.open("xb") as stream:
        sf.write(stream, result_audio, rate, format="WAV", subtype="FLOAT")
    after = inspect_level(output)
    error = after["integrated_lufs"] - target["integrated_lufs"] if after["integrated_lufs"] is not None else None
    return {"path": str(output), "reference": {"path": str(ref_path), **target},
            "candidate_before": {"path": str(cand_path), **before}, "output": after,
            "reference_sha256": hashlib.sha256(ref_path.read_bytes()).hexdigest(),
            "candidate_sha256": hashlib.sha256(cand_path.read_bytes()).hexdigest(),
            "requested_gain_db": requested, "applied_gain_db": applied, "gain_caps": capped,
            "estimated_peak_ceiling_dbtp": CEILING_DB, "loudness_error_db": error,
            "tolerance_db": tolerance_db, "target_achieved": error is not None and abs(error) <= tolerance_db,
            "processing": "constant gain only; no limiter, compressor, pitch or timing changes",
            "coverage": "same duration and channel count; reference-active 400-ms windows checked",
            "warnings": ["Matching LUFS cannot also guarantee matching peaks or dynamics.",
                         "Coverage checks detect missing active regions, not wrong notes or instruments."]}
