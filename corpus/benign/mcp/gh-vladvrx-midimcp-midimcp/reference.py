"""Prepare precise reference excerpts without changing their level or sample rate."""
from pathlib import Path
import hashlib
import math
import numpy as np
import soundfile as sf


def excerpt(source: Path, output: Path, start_seconds: float, duration_seconds: float) -> dict:
    if not all(math.isfinite(v) for v in (start_seconds, duration_seconds)) or start_seconds < 0 or duration_seconds <= 0:
        raise ValueError("Require finite start >= 0 and duration > 0")
    if duration_seconds > 120:
        raise ValueError("Use a reference excerpt of at most 120 seconds")
    source = Path(source).resolve(strict=True)
    with sf.SoundFile(str(source)) as stream:
        rate = stream.samplerate
        start = round(start_seconds * rate)
        count = round(duration_seconds * rate)
        if not count or start >= len(stream) or start + count > len(stream):
            raise ValueError("Requested excerpt extends beyond the audio or is shorter than one sample")
        stream.seek(start)
        audio = stream.read(count, dtype="float64", always_2d=True)
    if not np.isfinite(audio).all():
        raise ValueError("Reference contains nonfinite audio")
    if Path(output).exists():
        raise FileExistsError("Reference output already exists")
    sf.write(str(output), audio, rate, subtype="FLOAT")
    return {"path": str(Path(output).resolve()), "source": str(source),
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "sample_rate": rate, "channels": audio.shape[1], "start_frame": start,
            "frames": count, "start_seconds": start / rate, "duration_seconds": count / rate,
            "normalization_applied": False, "sha256": hashlib.sha256(Path(output).read_bytes()).hexdigest()}
