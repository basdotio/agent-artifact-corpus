"""Optional worker, isolated from the lightweight control application's dependencies."""

import sys


def main():
    import numpy as np
    import soundfile as sf
    import torch
    from demucs.apply import apply_model
    from demucs.pretrained import get_model
    from scipy.signal import resample_poly

    torch.set_num_threads(4)
    source, destination = sys.argv[1:3]
    model = get_model("htdemucs_6s").cpu().eval()
    audio, rate = sf.read(source, always_2d=True, dtype="float32")
    if audio.shape[1] == 1:
        audio = np.repeat(audio, 2, axis=1)
    if rate != model.samplerate:
        import math

        divisor = math.gcd(rate, model.samplerate)
        audio = resample_poly(audio, model.samplerate // divisor, rate // divisor, axis=0)
    wav = torch.from_numpy(audio[:, :2].T.copy())
    mean, std = wav.mean(), wav.std().clamp_min(1e-7)
    with torch.no_grad():
        stems = apply_model(
            model, ((wav - mean) / std)[None], device="cpu", shifts=0, split=True, overlap=0.25, progress=True
        )[0]
    guitar = stems[model.sources.index("guitar")] * std + mean
    sf.write(destination, guitar.T.numpy(), model.samplerate, subtype="FLOAT")


if __name__ == "__main__":
    main()
