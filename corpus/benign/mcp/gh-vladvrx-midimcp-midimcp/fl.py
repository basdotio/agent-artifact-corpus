"""Render saved FLP snapshots with FL Studio's documented Windows CLI.

This does not load a Serum preset, select export settings, or prove patch identity.
The project must already contain the intended instrument state and render settings.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time
from datetime import datetime, timezone

import numpy as np
import soundfile as sf


def _existing_fl_instances() -> list[int]:
    """Read process names before launch: FL may forward projects to a live instance."""
    if os.name != "nt":
        return []
    import ctypes
    from ctypes import wintypes

    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD),
                    ("th32ProcessID", wintypes.DWORD), ("th32DefaultHeapID", ctypes.c_size_t),
                    ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError("Cannot verify FL process isolation")
    pids = []
    try:
        entry = Entry()
        entry.dwSize = ctypes.sizeof(Entry)
        found = kernel.Process32FirstW(handle, ctypes.byref(entry))
        if not found:
            raise OSError("Cannot enumerate running processes")
        while found:
            if entry.szExeFile.lower() in ("fl.exe", "fl64.exe", "fl64 (scaled).exe"):
                pids.append(int(entry.th32ProcessID))
            found = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return pids


def _hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover_fl() -> Path | None:
    """Find a local 64-bit FL executable without launching an application."""
    candidates = []
    for key in ("ProgramFiles", "ProgramFiles(x86)"):
        root = os.environ.get(key)
        if root:
            candidates.extend(Path(root).glob("Image-Line/FL Studio*/FL64.exe"))
    return next((p.resolve() for p in sorted(candidates, reverse=True) if p.is_file()), None)


def _audio_metrics(path: Path) -> dict:
    """Stream the render so long projects do not require a full audio allocation."""
    count = clipped = frames = 0
    peak = square_sum = 0.0
    with sf.SoundFile(str(path)) as audio:
        samplerate, channels = audio.samplerate, audio.channels
        subtype = audio.subtype
        for block in audio.blocks(blocksize=65536, dtype="float64", always_2d=True):
            if not np.isfinite(block).all():
                raise ValueError("Rendered WAV contains non-finite samples")
            frames += len(block)
            count += block.size
            peak = max(peak, float(np.max(np.abs(block), initial=0)))
            square_sum += float(np.sum(block * block))
            clipped += int(np.count_nonzero(np.abs(block) >= 0.999))
    rms = math.sqrt(square_sum / count) if count else 0.0
    return {"sample_rate": samplerate, "channels": channels, "frames": frames,
            "duration_seconds": frames / samplerate, "subtype": subtype,
            "peak": peak, "rms": rms, "finite": True,
            "silent": peak <= 1e-7 or rms <= 1e-9,
            "clipped_samples": clipped, "clipping_threshold": 0.999}


def render_project(project: Path, output_dir: Path, fl_executable: Path,
                   timeout_seconds: float = 180) -> dict:
    """Render into a new job folder and return a JSON-serializable evidence record.

    Expected failures return ``status=error`` and a machine-readable error code.
    Only the subprocess started here is terminated on timeout. Existing FL instances
    cause a refusal before launch, preventing FL's single-instance project forwarding.
    Every job gets its own output and log files.
    """
    result = {"status": "error", "started_at": datetime.now(timezone.utc).isoformat(),
              "backend": "fl_studio_cli", "render_settings": "inherited_from_saved_project_and_FL_configuration",
              "patch_identity_verified": False}
    job = None
    start = time.monotonic()

    def finish(code=None, message=None):
        result["finished_at"] = datetime.now(timezone.utc).isoformat()
        result["elapsed_seconds"] = time.monotonic() - start
        if code:
            result["error"] = {"code": code, "message": message}
        else:
            result["status"] = "ok"
        if job is not None:
            try:
                with (job / "job.json").open("x", encoding="utf-8") as stream:
                    json.dump(result, stream, indent=2, allow_nan=False)
            except OSError as exc:
                result["manifest_error"] = str(exc)
        return result

    try:
        project = Path(project).expanduser().resolve()
        executable = Path(fl_executable).expanduser().resolve()
        output_dir = Path(output_dir).expanduser().resolve()
        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            return finish("invalid_timeout", "timeout_seconds must be finite and positive")
        if not project.is_file() or project.suffix.lower() != ".flp":
            return finish("missing_project", "An existing .flp project is required")
        if not executable.is_file():
            return finish("missing_executable", "FL Studio executable does not exist")
        existing = _existing_fl_instances()
        if existing:
            result["existing_fl_pids"] = existing
            return finish("fl_already_running", "Save and close FL Studio before CLI rendering; this FL version may forward the project into an existing session")
        project_hash = _hash(project)
        result.update(project=str(project), project_sha256=project_hash,
                      fl_executable=str(executable))
        output_dir.mkdir(parents=True, exist_ok=True)
        job = Path(tempfile.mkdtemp(prefix="fl-render-", dir=str(output_dir)))
        result["job_dir"] = str(job)
        # subprocess handles Windows argument quoting, including spaces in /O.
        args = [str(executable), "/Ewav", "/R", str(project), "/O" + str(job)]
        result["command"] = args
        log_path = job / "process.log"
        result["process_log"] = str(log_path)
        with log_path.open("xb") as log:
            process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=log,
                                       stderr=subprocess.STDOUT, cwd=str(job), shell=False)
            result["pid"] = process.pid
            try:
                result["returncode"] = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
                return finish("render_timeout", "Timed out; terminated only this render process")
        if result["returncode"] != 0:
            return finish("renderer_failed", "FL Studio exited with a nonzero code; inspect process.log")
        if _hash(project) != project_hash:
            return finish("project_changed", "Input FLP changed during rendering; evidence is invalid")
        wavs = [p for p in job.iterdir() if p.suffix.lower() == ".wav" and p.is_file()]
        if len(wavs) != 1:
            return finish("missing_or_ambiguous_audio", f"Expected exactly one fresh WAV; found {len(wavs)}")
        wav = wavs[0]
        if wav.is_symlink() or wav.resolve().parent != job.resolve():
            return finish("invalid_output", "Render output must be a regular file inside its job directory")
        before = wav.stat()
        time.sleep(0.25)
        stable = wav.stat()
        if (before.st_size, before.st_mtime_ns) != (stable.st_size, stable.st_mtime_ns):
            return finish("unstable_audio", "WAV is still changing after FL exited")
        result["audio"] = {"path": str(wav), **_audio_metrics(wav), "sha256": _hash(wav),
                           "size_bytes": stable.st_size, "mtime_ns": stable.st_mtime_ns}
        after = wav.stat()
        if (after.st_size, after.st_mtime_ns) != (stable.st_size, stable.st_mtime_ns):
            return finish("unstable_audio", "WAV changed during validation")
        if result["audio"]["silent"]:
            return finish("silent_audio", "Render is empty or silent")
        if result["audio"]["clipped_samples"]:
            return finish("clipped_audio", "Render reaches the clipping threshold; lower the saved project level")
        return finish()
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        return finish("render_error", str(exc))
