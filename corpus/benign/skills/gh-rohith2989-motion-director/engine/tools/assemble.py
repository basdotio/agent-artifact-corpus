"""
Deliverables from the lossless master: splice (frame-exact), mux the mix, encode, verify.

python tools/assemble.py --name Acme_Launch --v v1 --audio audio/out/mix.wav renders/master.mkv
    [--seg renders/a.mkv:0:4143 --seg renders/tr.mkv --seg renders/a.mkv:8403:9300]   splice by FRAME index
    [--cover 3.6] [--srt audio/out/captions.srt] [--crf 13]

Writes out/<name>_<v>.mp4 (H.264 High, CRF 13, BT.709 tags, AAC 320k from the float WAV, faststart),
out/<name>_<v>_preview.mp4 (short side 720), out/<name>_<v>_cover.png, and prints frames, duration,
integrated loudness and true peak of the delivered file. Splices use ffmpeg's trim by frame index and a
lossless FFV1 re-encode: the concat demuxer's inpoint/outpoint is NOT frame-exact (it drifted 6 frames).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ff import ffmpeg, ffprobe, ROOT  # noqa: E402


def run(args):
    subprocess.run(args, check=True)


def probe(path):
    out = subprocess.run([ffprobe(), "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames,width,height,r_frame_rate:format=duration", "-of", "json", path],
                         capture_output=True, text=True, check=True).stdout
    j = json.loads(out)
    s = j["streams"][0]
    return {"frames": int(s.get("nb_read_frames", 0)), "w": s["width"], "h": s["height"], "fps": s["r_frame_rate"], "dur": float(j["format"]["duration"])}


def loudness(path):
    r = subprocess.run([ffmpeg(), "-hide_banner", "-i", path, "-map", "0:a", "-af", "ebur128=peak=true", "-f", "null", "-"],
                       capture_output=True, text=True)
    txt = r.stderr
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", txt)
    p = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", txt)
    return (float(i[-1]) if i else None, float(p[-1]) if p else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("master", nargs="?", help="lossless master (FFV1 .mkv) — or use --seg")
    ap.add_argument("--seg", action="append", default=[], help="file[:startFrame:endFrame] (repeatable, in order)")
    ap.add_argument("--audio", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--v", default="v1")
    ap.add_argument("--cover", type=float, default=None, help="time (s) of the cover frame")
    ap.add_argument("--srt", default=None)
    ap.add_argument("--crf", type=int, default=13)
    ap.add_argument("--fps", type=int, default=None)
    a = ap.parse_args()
    out_dir = os.path.join(ROOT, "out")
    os.makedirs(out_dir, exist_ok=True)
    cfg = json.load(open(os.path.join(ROOT, "comp", "config.json")))
    fps = a.fps or cfg["fps"]
    master = a.master
    if a.seg:
        ins, chains = [], []
        for i, s in enumerate(a.seg):
            parts = s.split(":")
            f = parts[0] if not re.match(r"^[A-Za-z]$", parts[0]) else parts[0] + ":" + parts[1]  # Windows drive letters
            rest = parts[1:] if f == parts[0] else parts[2:]
            ins += ["-i", f]
            if rest:
                chains.append(f"[{i}:v]trim=start_frame={int(rest[0])}:end_frame={int(rest[1])},setpts=PTS-STARTPTS[s{i}]")
            else:
                chains.append(f"[{i}:v]setpts=PTS-STARTPTS[s{i}]")
        n = len(a.seg)
        fc = ";".join(chains) + ";" + "".join(f"[s{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0,fps={fps}[out]"
        master = os.path.join(ROOT, "renders", f"spliced_{a.name}_{a.v}.mkv")
        run([ffmpeg(), "-y", "-loglevel", "error", *ins, "-filter_complex", fc, "-map", "[out]", "-c:v", "ffv1", "-level", "3", "-pix_fmt", "bgr0", master])
    info = probe(master)
    print(f"master: {info['frames']} frames, {info['w']}x{info['h']} @ {info['fps']}, {info['dur']:.3f}s")
    mp4 = os.path.join(out_dir, f"{a.name}_{a.v}.mp4")
    run([ffmpeg(), "-y", "-loglevel", "error", "-i", master, "-i", a.audio, "-map", "0:v", "-map", "1:a",
         "-vf", "scale=out_color_matrix=bt709:out_range=tv,format=yuv420p",
         "-c:v", "libx264", "-preset", "slow", "-crf", str(a.crf), "-profile:v", "high", "-g", str(fps * 2), "-bf", "3",
         "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
         "-c:a", "aac", "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-shortest", mp4])
    short = 720
    scale = f"scale=-2:{short}" if info["w"] >= info["h"] else f"scale={short}:-2"
    prev = os.path.join(out_dir, f"{a.name}_{a.v}_preview.mp4")
    run([ffmpeg(), "-y", "-loglevel", "error", "-i", master, "-i", a.audio, "-map", "0:v", "-map", "1:a",
         "-vf", f"{scale}:flags=lanczos,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "21",
         "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", prev])
    if a.cover is not None:
        run([ffmpeg(), "-y", "-loglevel", "error", "-ss", str(a.cover), "-i", master, "-frames:v", "1", os.path.join(out_dir, f"{a.name}_{a.v}_cover.png")])
    if a.srt:
        shutil.copy(a.srt, os.path.join(out_dir, f"{a.name}_{a.v}.srt"))
    d = probe(mp4)
    L, P = loudness(mp4)
    print(f"delivered: {mp4}\n  {d['frames']} frames, {d['w']}x{d['h']} @ {d['fps']}, {d['dur']:.3f}s, {os.path.getsize(mp4) / 1e6:.1f} MB")
    print(f"  loudness {L} LUFS integrated, peak {P} dBFS (targets: -14 LUFS, <= -1.0 dBTP)")
    print(f"  preview: {prev}")


if __name__ == "__main__":
    main()
