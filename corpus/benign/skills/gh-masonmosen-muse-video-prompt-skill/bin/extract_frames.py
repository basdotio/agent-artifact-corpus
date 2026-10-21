#!/usr/bin/env python3
"""抽帧自查：从视频中按时间均匀抽 N 帧，用于验证提示词是否被吃进。

用法: extract_frames.py <video> [n=4] [out_prefix]
输出: <out_prefix>-f1.png ... <out_prefix>-fN.png
"""
import subprocess
import sys
import os


def main():
    if len(sys.argv) < 2:
        print("usage: extract_frames.py <video> [n=4] [out_prefix]")
        sys.exit(1)
    video = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    prefix = sys.argv[3] if len(sys.argv) > 3 else os.path.splitext(os.path.basename(video))[0]

    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True, check=True,
    )
    dur = float(r.stdout.strip())
    for i in range(n):
        t = dur * (i + 0.5) / n
        out = f"{prefix}-f{i + 1}.png"
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t),
             "-i", video, "-vframes", "1", out],
            check=True,
        )
        print(out)


if __name__ == "__main__":
    main()
