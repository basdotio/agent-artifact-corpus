from __future__ import annotations

import ipaddress
import os
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path
from threading import Event
from urllib.parse import urlparse

import httpx

from .models import ReferenceRequest


def public_url(url: str):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Use a public HTTPS source URL")
    addresses = socket.getaddrinfo(parsed.hostname, parsed.port or 443)
    if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
        raise ValueError("Private network sources are not allowed")
    return parsed


def run_process(args: list[str], cancel: Event, timeout=180):
    import tempfile

    # Redirect potentially large logs to a temporary file to avoid pipe deadlock.
    with tempfile.TemporaryFile() as log:
        process = subprocess.Popen(args, stdout=log, stderr=log)
        started = time.monotonic()
        while process.poll() is None:
            if cancel.wait(0.2) or time.monotonic() - started > timeout:
                process.kill()
                process.wait()
                raise RuntimeError("Operation cancelled or timed out")
        log.seek(0)
        output = log.read().decode(errors="replace")
        if process.returncode:
            raise RuntimeError(output[-1600:])
        return output


def clip(source: Path, destination: Path, start: float, duration: float, cancel: Event):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg not installed")
    run_process(
        [
            ffmpeg,
            "-nostdin",
            "-y",
            "-v",
            "error",
            "-ss",
            str(start),
            "-i",
            str(source),
            "-t",
            str(duration),
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_f32le",
            str(destination),
        ],
        cancel,
    )


def acquire(request: ReferenceRequest, destination: Path, cancel: Event):
    if not request.permitted:
        raise ValueError("Confirm that you may process this reference source")
    parsed = public_url(request.url)
    temporary = destination.with_suffix(".source")
    try:
        if parsed.hostname in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}:
            # No cookies, credential transfer, DRM circumvention, or account bypass.
            run_process(
                [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--no-playlist",
                    "--no-progress",
                    "--no-warnings",
                    "--max-filesize",
                    "80M",
                    "--socket-timeout",
                    "15",
                    "--retries",
                    "1",
                    "--format",
                    "bestaudio/best",
                    "--output",
                    str(temporary),
                    request.url,
                ],
                cancel,
            )
        else:
            url = request.url
            with httpx.Client(timeout=30, follow_redirects=False) as client:
                for _ in range(5):
                    public_url(url)
                    with client.stream("GET", url) as response:
                        if response.is_redirect:
                            url = str(response.url.join(response.headers["location"]))
                            continue
                        response.raise_for_status()
                        total = 0
                        with temporary.open("wb") as file:
                            for chunk in response.iter_bytes():
                                if cancel.is_set():
                                    raise RuntimeError("Cancelled")
                                total += len(chunk)
                                if total > 80_000_000:
                                    raise ValueError("Reference exceeds 80 MB")
                                file.write(chunk)
                        break
                else:
                    raise ValueError("Too many source redirects")
        clip(temporary, destination, request.start, request.duration, cancel)
    finally:
        temporary.unlink(missing_ok=True)


def separate(source: Path, destination: Path, cancel: Event):
    python = os.environ.get("MUSTANG_DEMUCS_PYTHON")
    if not python:
        local = Path(__file__).resolve().parents[1] / ".venv-audio/Scripts/python.exe"
        if not local.exists():
            raise RuntimeError("Install the optional separator with scripts/install-separator.ps1")
        python = str(local)
    run_process(
        [python, str(Path(__file__).with_name("separate_worker.py")), str(source), str(destination)],
        cancel,
        timeout=900,
    )
