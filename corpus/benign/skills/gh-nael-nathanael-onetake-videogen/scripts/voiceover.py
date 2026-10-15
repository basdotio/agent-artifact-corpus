#!/usr/bin/env python3
"""
Indonesian voice-over with VoxCPM2 (runs in the VoxCPM venv via run.sh).

  run.sh voiceover.py SCRIPT.txt OUT.wav [--ref voice.wav --ref-text "..."]
                      [--voice "(pria muda, ramah, energik)"] [--seed 7]

SCRIPT.txt: paragraphs separated by blank lines. A line "[pause 1.5]" inserts silence.
Without --ref, one anchor sentence is generated from the --voice description and then
used as the cloning prompt for every sentence, so the whole narration keeps one voice.
"""

import argparse
import re
from pathlib import Path

import numpy as np
import soundfile as sf

SR = 48000
SENT_GAP, PARA_GAP = 0.22, 0.65


def sentences(par):
    parts = re.split(r"(?<=[.!?])\s+", par.strip())
    out = []
    for p in parts:
        # keep chunks short: long inputs drift in prosody
        while len(p) > 220:
            cut = p.rfind(",", 0, 220)
            cut = cut if cut > 60 else 220
            out.append(p[:cut + 1].strip())
            p = p[cut + 1:]
        if p.strip():
            out.append(p.strip())
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--ref", help="reference voice wav to clone (5-20 s, clean)")
    ap.add_argument("--ref-text", help="transcript of --ref (better cloning)")
    ap.add_argument("--voice", default="(Suara pria muda Indonesia, ramah, jelas, energik, gaya YouTuber edukasi)")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--cfg", type=float, default=2.0)
    ap.add_argument("--steps", type=int, default=10)
    a = ap.parse_args()

    import torch
    from voxcpm import VoxCPM
    model = VoxCPM.from_pretrained("openbmb/VoxCPM2", load_denoiser=False)
    out = Path(a.out)
    parts_dir = out.with_suffix("")
    parts_dir.mkdir(parents=True, exist_ok=True)

    def gen(text, **kw):
        torch.manual_seed(a.seed)
        wav = model.generate(text=text, cfg_value=a.cfg, inference_timesteps=a.steps, **kw)
        return np.asarray(wav, dtype=np.float32).reshape(-1)

    if a.ref:
        clone = {"prompt_wav_path": a.ref, "prompt_text": a.ref_text} if a.ref_text else {"reference_wav_path": a.ref}
    else:
        anchor_text = "Halo semuanya, selamat datang. Hari ini kita akan belajar sesuatu yang seru."
        anchor = gen(a.voice + anchor_text)
        anchor_path = parts_dir / "anchor.wav"
        sf.write(anchor_path, anchor, SR)
        clone = {"prompt_wav_path": str(anchor_path), "prompt_text": anchor_text}

    chunks = []
    paragraphs = re.split(r"\n\s*\n", Path(a.script).read_text().strip())
    n = 0
    for pi, par in enumerate(paragraphs):
        m = re.fullmatch(r"\[pause\s+([\d.]+)\]", par.strip())
        if m:
            chunks.append(np.zeros(int(float(m.group(1)) * SR), np.float32))
            continue
        for si, s in enumerate(sentences(par)):
            w = gen(s, **clone)
            sf.write(parts_dir / f"{n:03d}.wav", w, SR)
            n += 1
            chunks.append(w)
            chunks.append(np.zeros(int(SENT_GAP * SR), np.float32))
            print(f"[{pi}.{si}] {len(w) / SR:5.1f}s  {s[:70]}")
        chunks.append(np.zeros(int((PARA_GAP - SENT_GAP) * SR), np.float32))
    audio = np.concatenate(chunks) if chunks else np.zeros(SR, np.float32)
    peak = np.abs(audio).max() or 1
    sf.write(out, audio / peak * 0.89, SR, subtype="PCM_16")
    print(f"{len(audio) / SR:.1f}s narration, {n} sentences -> {out}")


if __name__ == "__main__":
    main()
