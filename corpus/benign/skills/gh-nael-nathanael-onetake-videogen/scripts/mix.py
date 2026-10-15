#!/usr/bin/env python3
"""
Final mix: speech + ducked music bed (+ optional title-card overlays, sound effects), loudness -14 LUFS.

  run.sh mix.py VIDEO OUT.mp4 [--voice narration.wav] [--music bed.wav] [--music-db -16]
                [--overlay title.mov@1.5 ...] [--sfx cues.json]

--voice replaces the video's own audio (explainer mode). Without it the video's audio is the speech.
Music is side-chain ducked under the speech so words stay clear, and swells back in pauses.
Video is stream-copied unless overlays are given (then re-encoded with NVENC, x264 fallback).

--sfx places sound effects so each one's loudest 10 ms (measured after pitch and filter) lands on its
`at` time, dips the music under big hits, then normalises with a linear two-pass loudnorm (a lookahead
limiter goes in front only when a plain gain would break the peak ceiling). Writes OUT.sfx.json.
cues.json is a list of cues, or {"manifest": "audio/manifest.json", "cues": [...]}; each cue:
  file       path (relative to cues.json) or a key of the manifest's "sfx"
  at         seconds on the video timeline where the loudest point lands
  gain_db    loudest 10 ms over the RMS of the speech + music (silence excluded; -26 dBFS if none)
  pan        -1 (left) .. 1 (right), default 0
  pitch_hz   retune (tape style: pitch and length change together); source_hz is measured if omitted
  lowpass_hz, keep_s (trim with a fade over the last 40%), duck_db (music dip around the hit), name
"""

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from common import probe, run

SR = 48000
LOUDNORM = "I=-14:TP=-1.5:LRA=11"


def load_cues(path):
    path = Path(path).resolve()
    d = json.loads(path.read_text())
    cues, man, mdir = d, {}, path.parent
    if isinstance(d, dict):
        cues = d["cues"]
        if d.get("manifest"):
            mp = (path.parent / d["manifest"]).resolve()
            man, mdir = json.loads(mp.read_text()).get("sfx", {}), mp.parent
    for c in cues:
        c["path"] = str(mdir / man[c["file"]]["file"] if c["file"] in man else path.parent / c["file"])
        if not Path(c["path"]).exists():
            raise SystemExit(f"cue {c.get('name', c['file'])}: {c['path']} not found")
    return cues


def decode(path, filters=()):
    cmd = ["ffmpeg", "-v", "error", "-i", path, *(["-af", ",".join(filters)] if filters else []),
           "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, np.float32).astype(np.float64)


def rms_env(y, win=480):
    return np.sqrt(np.convolve(y ** 2, np.ones(win) / win, "same"))


def source_pitch(y):
    """Strongest partial (Hz) in the 300 ms after the loudest point."""
    pk = int(np.argmax(rms_env(y)))
    seg = y[pk:pk + int(0.3 * SR)]
    n = 1 << 18
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg)), n))
    freqs = np.fft.rfftfreq(n, 1 / SR)
    i = int(np.argmax(np.where((freqs > 80) & (freqs < 5000), spec, 0)))
    a, b, c = np.log(spec[i - 1:i + 2] + 1e-12)
    return float(freqs[i] + (a - c) / (2 * (a - 2 * b + c)) * (freqs[1] - freqs[0]))


def cue_signal(c):
    """Processed mono cue scaled to a unit 10 ms RMS peak, and the sample index of that peak."""
    f = [f"aresample={SR}"]
    if c.get("pitch_hz"):
        c.setdefault("source_hz", round(source_pitch(decode(c["path"], f)), 2))
        f += [f"asetrate={SR * c['pitch_hz'] / c['source_hz']:.3f}", f"aresample={SR}"]
    if c.get("lowpass_hz"):
        f.append(f"lowpass=f={c['lowpass_hz']}")
    if c.get("keep_s"):
        f.append(f"afade=t=out:st={c['keep_s'] * 0.6:.3f}:d={c['keep_s'] * 0.4:.3f}")
    y = decode(c["path"], f)
    if c.get("keep_s"):
        y = y[:int(c["keep_s"] * SR)]
    env = rms_env(y)
    return y / (env.max() + 1e-12), int(env.argmax())


def duck_envelope(cues, n):
    """Music gain: 40 ms down before each ducking hit, 150 ms hold, 700 ms back."""
    t = np.arange(n) / SR
    g = np.ones(n)
    for c in cues:
        if c.get("duck_db"):
            lo, at = 10 ** (-c["duck_db"] / 20), c["at"]
            g = np.minimum(g, np.interp(t, [at - 0.04, at, at + 0.15, at + 0.85], [1, lo, lo, 1]))
    return g


def ducked_music(path, cues, tmp):
    raw = Path(tmp) / "music.wav"
    run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ar", str(SR), "-c:a", "pcm_f32le", raw])
    y, _ = sf.read(raw, dtype="float64", always_2d=True)
    out = Path(tmp) / "music-ducked.wav"
    sf.write(out, y * duck_envelope(cues, len(y))[:, None], SR, subtype="FLOAT")
    return str(out)


def loudnorm_json(stderr):
    return json.loads(stderr[stderr.rindex("{"):stderr.rindex("}") + 1])


def measure(path):
    return loudnorm_json(run(["ffmpeg", "-hide_banner", "-i", path, "-af",
                              f"loudnorm={LOUDNORM}:print_format=json", "-f", "null", "-"]).stderr)


def sfx_audio(inputs, fg, dur, cues, tmp, report_path):
    """Speech + music + cues -> loudness-normalised 48 kHz stereo wav. Returns its path."""
    n = int(round(dur * SR))
    base = np.zeros((n, 2))
    if fg:
        bp = Path(tmp) / "base.wav"
        run(["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(fg), "-map", "[mixed]",
             "-ac", "2", "-ar", str(SR), "-c:a", "pcm_f32le", "-t", f"{dur:.3f}", bp])
        b, _ = sf.read(bp, dtype="float64", always_2d=True)
        base[:min(n, len(b))] = b[:n]
    blk = int(0.1 * SR)
    pw = (base[:n // blk * blk].mean(1) ** 2).reshape(-1, blk).mean(1)
    act = pw[pw > 1e-6]  # 100 ms blocks above -60 dBFS
    ref_db = float(10 * np.log10(act.mean())) if len(act) else -26.0

    stem = np.zeros((n, 2))
    rows = []
    for c in cues:
        y, pk = cue_signal(c)
        y *= 10 ** ((ref_db + c.get("gain_db", 0)) / 20)
        s = int(round(c["at"] * SR)) - pk
        a, b = max(0, s), min(n, s + len(y))
        if a >= b:
            raise SystemExit(f"cue {c.get('name', c['file'])} at {c['at']} s falls outside the video")
        th = (c.get("pan", 0) + 1) * np.pi / 4
        stem[a:b, 0] += y[a - s:b - s] * np.cos(th)
        stem[a:b, 1] += y[a - s:b - s] * np.sin(th)
        rows.append({**c, "start_s": round(s / SR, 5), "peak_in_processed_s": round(pk / SR, 5)})
        if s < 0 and np.abs(y[:-s]).max() > 0.01 * np.abs(y).max():
            print(f"warning: cue {c.get('name', c['file'])} starts before 0 s; an audible head is cut")

    pre = base + stem
    pre_wav = Path(tmp) / "pre.wav"
    sf.write(pre_wav, pre.astype(np.float32), SR, subtype="FLOAT")
    # Plain gain to -14 LUFS first (float, no clipping), so the limiter ceiling is absolute.
    gain_db = -14 - float(measure(str(pre_wav))["input_i"])
    norm = Path(tmp) / "norm.wav"
    sf.write(norm, (pre * 10 ** (gain_db / 20)).astype(np.float32), SR, subtype="FLOAT")
    src, ceiling, out = norm, None, Path(tmp) / "final.wav"
    for attempt in range(5):
        m = measure(str(src))
        # loudnorm only goes linear when measured LRA <= target LRA. Linear never touches LRA (it is one
        # gain), so raise the target to what is there; the ceiling stays the only thing to satisfy.
        lra = min(50, max(11, int(np.ceil(float(m["input_lra"])))))
        af = (f"loudnorm=I=-14:TP=-1.5:LRA={lra}:measured_I={m['input_i']}:measured_TP={m['input_tp']}"
              f":measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}"
              f":offset={m['target_offset']}:linear=true:print_format=json")
        m2 = loudnorm_json(run(["ffmpeg", "-hide_banner", "-y", "-i", src, "-af", af, "-ar", str(SR),
                                "-c:a", "pcm_f32le", out]).stderr)
        if m2["normalization_type"] == "linear":
            break
        # Lookahead limiter, latency-compensated so cue peaks stay on their frames. Lower the ceiling by
        # what the peaks would overshoot after loudnorm's make-up gain (limiting costs loudness too).
        excess = float(m["input_tp"]) - 14 - float(m["input_i"]) + 1.5
        ceiling = round((float(m["input_tp"]) if ceiling is None else ceiling) - excess - 0.3, 2)
        print(f"loudnorm went dynamic (I {m['input_i']}, TP {m['input_tp']}): limiter at {ceiling} dBFS")
        src = Path(tmp) / f"lim{attempt}.wav"
        # 4x oversampled so the sample-peak limiter also catches inter-sample (true) peaks.
        run(["ffmpeg", "-y", "-v", "error", "-i", norm, "-af",
             f"aresample={4 * SR},alimiter=limit={10 ** (ceiling / 20):.5f}:attack=5:release=60:level=false"
             f":latency=true,aresample={SR}", "-c:a", "pcm_f32le", src])
    else:
        raise SystemExit(f"loudnorm stayed dynamic even with the limiter at {ceiling} dBFS")
    Path(report_path).write_text(json.dumps({
        "ref_db": round(ref_db, 2), "pre_gain_db": round(gain_db, 2), "limiter_ceiling_dbfs": ceiling,
        "loudnorm_target_lra": lra,
        "loudnorm_pass1": m, "loudnorm_pass2": m2, "cues": rows}, indent=1))
    print(f"sfx: {len(cues)} cues, speech/music RMS {ref_db:.1f} dBFS, limiter "
          f"{'off' if ceiling is None else f'{ceiling} dBFS'}, loudnorm {m2['normalization_type']} "
          f"-> {m2['output_i']} LUFS, {m2['output_tp']} dBTP, LRA {m2['output_lra']}")
    return str(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out")
    ap.add_argument("--voice")
    ap.add_argument("--music")
    ap.add_argument("--music-db", type=float, default=-16, help="music level before ducking")
    ap.add_argument("--overlay", action="append", default=[], help="FILE@START_SECONDS (alpha video)")
    ap.add_argument("--sfx", help="cues.json (see module doc)")
    a = ap.parse_args()

    info = probe(a.video)
    dur = info["duration"]
    tmpdir = tempfile.TemporaryDirectory() if a.sfx else None
    cues = load_cues(a.sfx) if a.sfx else []
    inputs = ["-i", a.video]
    idx = 1
    voice = None
    if a.voice:
        inputs += ["-i", a.voice]
        voice, idx = f"{idx}:a", idx + 1
    elif info["has_audio"]:
        voice = "0:a"
    music = None
    if a.music:
        mpath = ducked_music(a.music, cues, tmpdir.name) if any(c.get("duck_db") for c in cues) else a.music
        inputs += ["-i", mpath]
        music, idx = f"{idx}:a", idx + 1

    fg = []
    if voice and music:
        fg += [f"[{voice}]aresample=48000,asplit=2[vo][key]",
               f"[{music}]aresample=48000,volume={a.music_db}dB[mv]",
               "[mv][key]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=450[duck]",
               "[vo][duck]amix=inputs=2:duration=longest:normalize=0[mixed]"]
    elif voice:
        fg += [f"[{voice}]aresample=48000[mixed]"]
    elif music:
        fg += [f"[{music}]aresample=48000,volume={a.music_db}dB[mixed]"]
    has_audio = bool(fg)
    amap = "[a]"
    if a.sfx:
        final = sfx_audio(inputs, fg, dur, cues, tmpdir.name, f"{a.out}.sfx.json")
        inputs, idx, fg, amap, has_audio = ["-i", a.video, "-i", final], 2, [], "1:a", True
    elif has_audio:
        fg += ["[mixed]loudnorm=I=-14:TP=-1.5:LRA=11,aresample=48000[a]"]

    vlabel = "0:v"
    for k, ov in enumerate(a.overlay):
        path, start = ov.rsplit("@", 1)
        inputs += ["-i", path]
        fg += [f"[{idx}:v]setpts=PTS-STARTPTS+{float(start)}/TB[o{k}]",
               f"[{vlabel}][o{k}]overlay=eof_action=pass:format=auto[v{k}]"]
        vlabel, idx = f"v{k}", idx + 1

    maps = ["-map", f"[{vlabel}]" if a.overlay else "0:v"]
    if has_audio:
        maps += ["-map", amap]

    def cmd(vcodec):
        return ["ffmpeg", "-y", "-loglevel", "error", *inputs,
                *(["-filter_complex", ";".join(fg)] if fg else []), *maps, *vcodec,
                "-c:a", "aac", "-b:a", "192k", "-t", f"{dur:.3f}", "-movflags", "+faststart", a.out]

    if not a.overlay:
        run(cmd(["-c:v", "copy"]))
    else:
        try:
            run(cmd(["-c:v", "h264_nvenc", "-preset", "p5", "-rc", "vbr", "-cq", "19", "-b:v", "0"]))
        except RuntimeError:
            run(cmd(["-c:v", "libx264", "-preset", "medium", "-crf", "18"]))
    print(f"-> {a.out} ({dur:.1f}s)")


if __name__ == "__main__":
    main()
