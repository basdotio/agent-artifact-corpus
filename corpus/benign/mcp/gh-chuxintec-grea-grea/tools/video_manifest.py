#!/usr/bin/env python3
"""Inventory local recordings using SHA-256 and ffprobe; optionally decode them.

Python 3.9+, ffprobe; --decode also needs ffmpeg. Does not capture screen/audio.
An audio stream is not proof of audible sound, and metadata is not visual review.
Exit 0: requested checks pass, 1: reported media issues, 2: input/tool failure.
"""
import argparse
import json
import math
from grea.host.paths import Path
import subprocess
import sys
from grea.tools._artifact_common import digest, validate_output, write_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recordings", nargs="+", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--decode", action="store_true", help="Decode all video/audio streams to null; can take the full clip duration")
    parser.add_argument("--require-audio", action="store_true")
    parser.add_argument("--timeout", type=float, default=300, help="Per subprocess seconds")
    args = parser.parse_args()
    try:
        if not math.isfinite(args.timeout) or args.timeout <= 0:
            raise ValueError("Timeout must be positive and finite")
        validate_output(args.output, args.recordings)
        if len({p.resolve() for p in args.recordings}) != len(args.recordings):
            raise ValueError("Duplicate input recording")
        for path in args.recordings:
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"Recording is not a regular file: {path}")
        rows = []
        for path in args.recordings:
            path = path.resolve()
            row = {"path": str(path), "sha256": digest(path), "bytes": path.stat().st_size, "issues": []}
            result = subprocess.run([args.ffprobe, "-v", "error", "-show_entries",
                "format=duration,size:stream=index,codec_type,codec_name,width,height,avg_frame_rate,r_frame_rate,sample_rate,channels,duration",
                "-of", "json", str(path)], capture_output=True, text=True, timeout=args.timeout)
            if result.returncode:
                row["issues"].append("probe_failed")
                row["diagnostic"] = result.stderr[-2000:]
            else:
                row["probe"] = json.loads(result.stdout)
                streams = row["probe"].get("streams", [])
                if not any(s.get("codec_type") == "video" for s in streams):
                    row["issues"].append("no_video_stream")
                if args.require_audio and not any(s.get("codec_type") == "audio" for s in streams):
                    row["issues"].append("no_audio_stream")
                duration = float(row["probe"].get("format", {}).get("duration", 0))
                if not math.isfinite(duration) or duration <= 0:
                    row["issues"].append("invalid_duration")
                if args.decode:
                    decoded = subprocess.run([args.ffmpeg, "-v", "error", "-xerror", "-i", str(path),
                        "-map", "0:v?", "-map", "0:a?", "-f", "null", "-"],
                        capture_output=True, text=True, timeout=args.timeout)
                    row["decode_passed"] = decoded.returncode == 0
                    if decoded.returncode:
                        row["issues"].append("decode_failed")
                        row["decode_diagnostic"] = decoded.stderr[-2000:]
            rows.append(row)
        report = {"recordings": rows, "decode_requested": args.decode, "visual_reviewed": False,
                  "audio_listened": False, "fps_note": "r_frame_rate is not measured playback FPS; VFR requires timestamps"}
        write_report(report, args.output, args.recordings)
        return 1 if any(r["issues"] for r in rows) else 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
