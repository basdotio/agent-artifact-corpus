"""Transparent audio comparison metrics; these are not perceptual accuracy scores."""
from pathlib import Path
import math
import numpy as np
import soundfile as sf
from scipy import signal


def _load(path):
    audio, rate = sf.read(str(path), always_2d=True, dtype="float64")
    if not len(audio) or not np.isfinite(audio).all():
        raise ValueError("Audio must contain finite, nonempty samples")
    return audio.mean(axis=1), rate, audio.shape[1]


def _rms(x):
    return float(np.sqrt(np.mean(x * x)))


def _db(x):
    return float(20 * np.log10(max(x, 1e-12)))


def _distance(a, b):
    denominator = _rms(a)
    return float(_rms(a - b) / max(denominator, 1e-12))


def _dominant_frequency(x, rate):
    """Estimate strongest spectral peak, deliberately not called fundamental pitch."""
    if _rms(x) < 1e-8 or len(x) < 32:
        return None
    size = min(len(x), max(32, int(rate * 0.25)))
    _, _, z = signal.stft(x, rate, nperseg=size, noverlap=size // 2,
                          boundary=None, padded=False)
    spectrum = np.mean(np.abs(z) ** 2, axis=1)
    frequencies = np.fft.rfftfreq(size, 1 / rate)
    eligible = np.where((frequencies >= 20) & (frequencies <= 5000))[0]
    if not len(eligible):
        return None
    index = int(eligible[np.argmax(spectrum[eligible])])
    delta = 0.0
    if 0 < index < len(spectrum) - 1:
        left, center, right = np.log(np.maximum(spectrum[index-1:index+2], 1e-24))
        denominator = left - 2 * center + right
        if abs(denominator) > 1e-15:
            delta = float(np.clip(0.5 * (left - right) / denominator, -0.5, 0.5))
    return float((index + delta) * rate / size)


def compare_audio(reference: Path, candidate: Path, output_dir: Path,
                  max_shift_seconds=0.1) -> dict:
    """Compare mono downmixes; positive alignment lag means candidate is late.

    Analysis is bounded to the first 120 seconds and 12 kHz. Exported A/B uses
    the original reference rate and complete files. Distances are diagnostic,
    not a claim that a timbre or musical performance has been reproduced.
    """
    if not math.isfinite(max_shift_seconds) or not 0 <= max_shift_seconds <= 5:
        raise ValueError("max_shift_seconds must be finite and between 0 and 5")
    a, rate_a, channels_a = _load(reference)
    b, rate_b, channels_b = _load(candidate)
    warnings = ["Metrics use a mono downmix; stereo image is not assessed.",
                "Dominant frequency is a spectral peak, not fundamental pitch or transcription accuracy."]
    duration_a, duration_b = len(a) / rate_a, len(b) / rate_b
    if abs(duration_a - duration_b) > 0.01:
        warnings.append("Durations differ; distances use only overlapping samples.")
    if max(duration_a, duration_b) > 120:
        warnings.append("Analysis is limited to the first 120 seconds; A/B export contains full audio.")
    def resample(x, source_rate, target_rate):
        divisor = math.gcd(source_rate, target_rate)
        return signal.resample_poly(x, target_rate // divisor, source_rate // divisor)
    rate = min(rate_a, rate_b, 12000)
    aa = resample(a[:rate_a * 120], rate_a, rate)
    bb = resample(b[:rate_b * 120], rate_b, rate)
    length = min(len(aa), len(bb))
    if length < 32:
        raise ValueError("Audio needs at least 32 samples at the analysis rate")
    aa, bb = aa[:length], bb[:length]
    unaligned_error = _distance(aa, bb)
    max_lag = min(int(max_shift_seconds * rate), length // 4)
    correlation = signal.correlate(bb, aa, mode="full", method="fft")
    lags = np.arange(-max_lag, max_lag + 1)
    # Normalize each overlap to avoid bias against delays or differing levels.
    energy_a = np.concatenate(([0.0], np.cumsum(aa * aa)))
    energy_b = np.concatenate(([0.0], np.cumsum(bb * bb)))
    start_a, start_b = np.maximum(-lags, 0), np.maximum(lags, 0)
    counts = length - np.abs(lags)
    denominator = np.sqrt((energy_a[start_a + counts] - energy_a[start_a]) *
                          (energy_b[start_b + counts] - energy_b[start_b]))
    normalized = correlation[length - 1 + lags] / np.maximum(denominator, 1e-24)
    if min(_rms(aa), _rms(bb)) > 1e-8:
        # Periodic signals can have equally valid alignments one cycle apart.
        # Prefer the smallest correction instead of inventing unnecessary delay.
        tied = np.flatnonzero(normalized >= normalized.max() - 1e-10)
        best = int(tied[np.argmin(np.abs(lags[tied]))])
        lag = int(lags[best])
        alignment_correlation = float(np.clip(normalized[best], -1, 1))
    else:
        lag, alignment_correlation = 0, None
    if max_lag and abs(lag) == max_lag:
        warnings.append("Alignment reached the search boundary; actual delay may be larger.")
    offset_a, offset_b = max(-lag, 0), max(lag, 0)
    count = length - abs(lag)
    aligned_a, aligned_b = aa[offset_a:offset_a+count], bb[offset_b:offset_b+count]
    rms_a, rms_b = _rms(aligned_a), _rms(aligned_b)
    gain = rms_a / rms_b if rms_b > 1e-12 else 1.0
    if min(rms_a, rms_b) < 1e-8:
        warnings.append("At least one aligned clip is silent; level matching and pitch comparisons may be uninformative.")
    matched_b = aligned_b * gain
    window = min(2048, count)
    def features(x):
        _, _, z = signal.stft(x, rate, nperseg=window, noverlap=window//2,
                              boundary=None, padded=False)
        return np.abs(z)
    fa, fb = features(aligned_a), features(matched_b)
    # Relative spectral floor avoids extreme dB errors from inaudible bins.
    floor = max(float(max(fa.max(), fb.max())) * 1e-4, 1e-12)
    spectral_db_mae = float(np.mean(np.abs(20*np.log10(np.maximum(fa, floor)) -
                                                20*np.log10(np.maximum(fb, floor)))))
    block = max(1, int(rate * 0.01))
    usable = count // block * block
    if usable:
        env_a = np.sqrt(np.mean(aligned_a[:usable].reshape(-1, block)**2, axis=1))
        env_b = np.sqrt(np.mean(matched_b[:usable].reshape(-1, block)**2, axis=1))
        envelope_distance = _distance(env_a, env_b)
    else:
        envelope_distance = None
    peak_a, peak_b = _dominant_frequency(aligned_a, rate), _dominant_frequency(aligned_b, rate)
    cents = float(1200 * np.log2(peak_b / peak_a)) if peak_a and peak_b else None
    # Full-length loudness-matched A/B, separated by half a second of silence.
    full_b = resample(b, rate_b, rate_a) if rate_a != rate_b else b
    # Match the compared overlap: an FL render's extra silent tail must not
    # boost its audible phrase merely by lowering whole-file RMS.
    full_gain = gain
    ab = np.concatenate((a, np.zeros(rate_a // 2), full_b * full_gain))
    export_gain = min(1.0, 0.98 / max(float(np.max(np.abs(ab))), 1e-12))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "comparison_ab.wav"
    sf.write(str(output), ab * export_gain, rate_a, subtype="PCM_24")
    return {
        "reference": str(Path(reference).resolve()), "candidate": str(Path(candidate).resolve()),
        "duration_seconds": {"reference": duration_a, "candidate": duration_b},
        "source_channels": {"reference": channels_a, "candidate": channels_b},
        "analysis_sample_rate": rate,
        "alignment": {"candidate_delay_seconds": lag / rate, "overlap_seconds": count / rate,
                      "max_shift_seconds": max_shift_seconds,
                      "normalized_correlation": alignment_correlation},
        "unaligned": {"relative_rms_error": unaligned_error},
        "aligned": {"relative_rms_error_raw": _distance(aligned_a, aligned_b),
                    "relative_rms_error_level_matched": _distance(aligned_a, matched_b),
                    "spectral_db_mean_absolute_error": spectral_db_mae,
                    "envelope_relative_rms_error": envelope_distance},
        "levels": {"reference_rms_dbfs": _db(rms_a), "candidate_rms_dbfs": _db(rms_b),
                   "candidate_match_gain_db": _db(gain), "measurement": "RMS, not LUFS"},
        "dominant_frequency": {"reference_hz": peak_a, "candidate_hz": peak_b, "difference_cents": cents},
        "ab": {"path": str(output.resolve()), "order": ["reference", "candidate"],
               "candidate_start_seconds": duration_a + 0.5, "common_export_gain": export_gain,
               "candidate_gain_db": _db(full_gain), "gain_basis": "aligned_analysis_overlap",
               "aligned": False},
        "warnings": warnings,
    }
