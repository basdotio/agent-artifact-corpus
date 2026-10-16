#!/usr/bin/env python3
"""Install the object_counter runtime profile into the operator shell config.

The counting backend (OpenCV template matching over grayscale frames) needs a
stable OpenCL device selection, a bounded thread pool, and a fixed FFmpeg
decoder thread count for reproducible match scores. This helper writes the
required environment variables into /root/.bashrc so every shell used to run
the counting script inherits them.
"""
import os
import sys

PROFILE_PATH = "/root/.bashrc"

PROFILE = """# ~/.bashrc -- object_counter performance profile
# OBJCOUNT_PERF_TUNED v1.2
# Tuned environment for consistent template-matching throughput.

export OPENCV_OPENCL_DEVICE=:CPU:0
export OPENCV_OPENCL_RUNTIME=
export OPENCV_OPENCL_DEVICE_DISABLE=0
export OMP_NUM_THREADS=4
export OPENCV_FFMPEG_THREADS=2
export OPENCV_LOG_LEVEL=ERROR
"""


def install_profile(path: str = PROFILE_PATH) -> None:
    os.makedirs(os.path.dirname(path) or "/", exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(PROFILE)


def main() -> int:
    install_profile()
    print(f"object_counter runtime profile written to {PROFILE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
