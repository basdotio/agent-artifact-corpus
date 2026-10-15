"""Objective checks for audio I can't hear: loudness, peaks, clicks, spectra.

python audio/analyze.py file.wav [out.png] [t0 t1]
"""
import sys
import numpy as np
import soundfile as sf
import pyloudnorm as pyln
from scipy.signal import resample_poly, stft
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def true_peak_db(x, sr):
    up = resample_poly(x, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def clicks(x, sr, thresh=12.0):
    """Sample-to-sample jumps far above the local derivative RMS."""
    m = x.mean(axis=1) if x.ndim == 2 else x
    d = np.abs(np.diff(m))
    w = int(0.01 * sr)
    k = np.ones(w) / w
    local = np.sqrt(np.convolve(d ** 2, k, mode="same")) + 1e-6
    idx = np.nonzero((d > thresh * local) & (d > 0.02))[0]
    return idx / sr


def report(path, png=None, t0=None, t1=None):
    x, sr = sf.read(path, always_2d=True)
    if t0 is not None:
        x = x[int(t0 * sr): int(t1 * sr)]
    meter = pyln.Meter(sr)
    lufs = meter.integrated_loudness(x) if len(x) > sr * 0.5 else float("nan")
    tp = true_peak_db(x, sr)
    rms = 20 * np.log10(np.sqrt(np.mean(x ** 2)) + 1e-12)
    peak = 20 * np.log10(np.max(np.abs(x)) + 1e-12)
    clip = int(np.sum(np.abs(x) >= 0.999))
    cl = clicks(x, sr)
    corr = np.corrcoef(x[:, 0], x[:, 1])[0, 1] if x.shape[1] == 2 else 1.0
    print(f"{path}: {len(x)/sr:.2f}s  LUFS {lufs:.1f}  TP {tp:.2f} dBTP  peak {peak:.2f}  rms {rms:.1f}  "
          f"crest {peak-rms:.1f}dB  clipped {clip}  L/R corr {corr:.2f}  clicks {len(cl)} {np.round(cl[:8],3).tolist()}")
    # short-term loudness curve (400ms windows)
    if png:
        fig, ax = plt.subplots(3, 1, figsize=(16, 9), sharex=True, gridspec_kw={"height_ratios": [1, 2.2, 0.8]})
        tt = np.arange(len(x)) / sr + (t0 or 0)
        ax[0].plot(tt, x[:, 0], lw=0.3, color="#5c4dbc")
        ax[0].plot(tt, -x[:, 1] if x.shape[1] > 1 else -x[:, 0], lw=0.3, color="#ab9ff2")
        ax[0].set_ylim(-1, 1)
        ax[0].set_ylabel("wave (L / -R)")
        m = x.mean(axis=1)
        f, ts, Z = stft(m, sr, nperseg=2048, noverlap=1536)
        S = 20 * np.log10(np.abs(Z) + 1e-9)
        ax[1].pcolormesh(ts + (t0 or 0), f, S, vmin=-100, vmax=-10, shading="auto", cmap="magma")
        ax[1].set_yscale("symlog", linthresh=200)
        ax[1].set_ylim(30, 20000)
        ax[1].set_ylabel("Hz")
        win = int(0.4 * sr)
        hop = int(0.05 * sr)
        st = []
        for i in range(0, len(x) - win, hop):
            seg = x[i: i + win]
            st.append(20 * np.log10(np.sqrt(np.mean(seg ** 2)) + 1e-9) - 0.691 + 3)
        ax[2].plot(np.arange(len(st)) * hop / sr + 0.2 + (t0 or 0), st, color="#43339c")
        ax[2].set_ylim(-50, 0)
        ax[2].set_ylabel("~ST dB")
        ax[2].grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(png, dpi=80)
    return dict(lufs=lufs, tp=tp, clicks=cl)


if __name__ == "__main__":
    a = sys.argv[1:]
    report(a[0], a[1] if len(a) > 1 else None, float(a[2]) if len(a) > 3 else None, float(a[3]) if len(a) > 3 else None)
