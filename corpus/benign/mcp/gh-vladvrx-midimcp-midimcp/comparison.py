"""Numbered, stereo-preserving listening files with transparent gain matching."""
from pathlib import Path
import hashlib
import numpy as np
import soundfile as sf


def export_pair(first: Path, second: Path, output_dir: Path, match_rms: bool = True) -> dict:
    if not isinstance(match_rms, bool):
        raise ValueError('match_rms must be boolean')
    sources = [Path(first).resolve(strict=True), Path(second).resolve(strict=True)]
    output_dir = Path(output_dir).resolve()
    targets = [output_dir/'1 - First.wav', output_dir/'2 - Second.wav']
    if any(p.exists() or p in sources for p in targets):
        raise ValueError('Comparison outputs must be new files')
    arrays, rates, rms, hashes = [], [], [], []
    for path in sources:
        info = sf.info(path)
        if info.channels not in (1, 2) or not 0 < info.frames <= 192000 * 600 or info.duration > 600:
            raise ValueError('Use nonempty mono/stereo audio up to 10 minutes')
        if not 8000 <= info.samplerate <= 192000:
            raise ValueError('Sample rate must be 8000..192000 Hz')
        data, rate = sf.read(path, dtype='float32', always_2d=True)
        if not np.isfinite(data).all():
            raise ValueError('Audio contains nonfinite samples')
        value = float(np.sqrt(np.mean(data.astype(np.float64)**2)))
        if value < 1e-8:
            raise ValueError('Cannot compare silent audio')
        arrays.append(data)
        rates.append(rate)
        rms.append(value)
        with path.open('rb') as handle:
            hashes.append(hashlib.file_digest(handle, 'sha256').hexdigest())
    gains = [min(rms)/value if match_rms else 1.0 for value in rms]
    peak = max(float(np.max(np.abs(data)))*gain for data, gain in zip(arrays, gains))
    common = min(1.0, .98/peak)
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    for i, (data, rate, gain, path) in enumerate(zip(arrays, rates, gains, targets)):
        gain *= common
        sf.write(path, data * gain, rate, subtype='PCM_24')
        files.append({'number': i+1, 'path': str(path), 'source': str(sources[i]),
                      'source_sha256': hashes[i], 'sample_rate': rate,
                      'channels': data.shape[1], 'frames': len(data),
                      'duration_seconds': len(data)/rate, 'gain_db': float(20*np.log10(gain))})
    return {'files': files, 'level_matching': 'full_track_rms' if match_rms else 'none',
            'common_attenuation_db': float(20*np.log10(common)),
            'timing_modified': False, 'stereo_preserved': True,
            'warnings': ['RMS matching is not perceptual loudness matching. These are listening files, not an accuracy score.']}
