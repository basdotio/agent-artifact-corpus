"""Measure score candidates, because you cannot listen: tempo, beat-grid fit, level per second, energy jumps
(bass entries, drops), and a spectrogram per file with the beat grid drawn on.

    uv run --with librosa --with matplotlib python3 scripts/analyze_music.py assets/audio/music/*.mp3

Put the printed bpm and firstBeat into timeline.json. Place cuts on the printed events (bass entry, phrase swells,
drops). A generated intro is often ~10 dB quieter than the body and can open with silence: trim whole bars with
timeline.json musicStart (bars keep the grid) and lift the rest with audio.json music.introLift.
"""
import os
import sys

import librosa
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

paths = sys.argv[1:]
fig, axes = plt.subplots(len(paths), 1, figsize=(20, 3.2 * len(paths)), squeeze=False)
for ax, p in zip(axes[:, 0], paths):
    y, sr = librosa.load(p, sr=22050, mono=True)
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr, tightness=300)
    bt = librosa.frames_to_time(beats, sr=sr)
    n = np.arange(len(bt))
    a, b = np.linalg.lstsq(np.vstack([np.ones_like(n), n]).T, bt, rcond=None)[0]
    resid = np.std(bt - (a + b * n)) * 1000
    hop = 256
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=hop))
    f = librosa.fft_frequencies(sr=sr, n_fft=2048)
    t = librosa.frames_to_time(np.arange(S.shape[1]), sr=sr, hop_length=hop)
    low = 20 * np.log10(S[(f > 30) & (f < 200)].mean(0) + 1e-9)
    k = int(0.25 * sr / hop)
    sm = np.convolve(low, np.ones(k) / k, "same")
    lag = int(0.5 * sr / hop)
    jump = sm[lag:] - sm[:-lag]
    events = []
    for i in np.argsort(-jump):
        tt = t[i + lag // 2]
        if jump[i] < 6:
            break
        if all(abs(tt - e) > 2 for e, _ in events):
            events.append((tt, jump[i]))
        if len(events) >= 8:
            break
    rms = librosa.feature.rms(y=y, hop_length=512)[0]
    rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=512)
    db = 20 * np.log10(rms + 1e-9)
    per_sec = [np.mean(db[(rt >= s) & (rt < s + 1)]) for s in range(int(len(y) / sr))]
    print(f"\n{os.path.basename(p)}  {len(y) / sr:.1f}s  bpm {60 / b:.2f}  firstBeat {a % b:.3f}  grid residual {resid:.1f} ms")
    print("  low-band jumps (bass entries):", ", ".join(f"{e:.2f}s (+{j:.0f} dB)" for e, j in sorted(events)))
    print("  dB per second:", " ".join(f"{v:.0f}" for v in per_sec))
    ax.imshow(librosa.amplitude_to_db(S, ref=np.max), origin="lower", aspect="auto", cmap="magma", extent=[0, len(y) / sr, 0, sr / 2], vmin=-80, vmax=0)
    ax.set_ylim(0, 6000)
    for x in np.arange(a % b, len(y) / sr, 4 * b):
        ax.axvline(x, color="white", lw=0.4, alpha=0.5)
    for e, _ in events:
        ax.axvline(e, color="cyan", lw=1.2)
    ax.set_title(f"{os.path.basename(p)}  bpm {60 / b:.2f}  first beat {a % b:.3f}s (white = bars, cyan = bass entries)")
out = os.path.join(os.path.dirname(__file__), "..", "review", "music_candidates.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
plt.tight_layout()
plt.savefig(out, dpi=60)
print("\nwrote", os.path.abspath(out))
