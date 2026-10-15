"""Mandatory review bound to the exact prepared video, original source and audio."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from job_state import atomic_json, job_lock

COMMON_FILES = (
    "upload.mp4", "original.mp4", "composite-silent.mp4", "seedance-input.mp4",
    "audio-manifest.json", "original-audio.wav", "vocals.wav",
)
FILES = COMMON_FILES + ("depth.mp4", "mask.mp4")


def _mode(folder):
    path = Path(folder) / "workflow-mode.json"
    try:
        mode = json.loads(path.read_text(encoding="utf-8")).get("mode") if path.exists() else "depth"
    except (ValueError, AttributeError) as exc:
        raise ValueError("The saved workflow mode is invalid; prepare this job again.") from exc
    if mode not in ("depth", "face_mesh", "depth_mesh"):
        raise ValueError("Unknown prepared workflow mode.")
    return mode


def is_mesh(folder):
    return _mode(folder) in ("face_mesh", "depth_mesh")


def fingerprint(folder):
    """Hash every submitted and restored input; approval cannot outlive a change."""
    folder = Path(folder)
    mode = _mode(folder)
    names = list(COMMON_FILES)
    if (folder / "workflow-mode.json").exists():
        names.append("workflow-mode.json")
    if mode in ("depth", "depth_mesh"):
        names.extend(("depth.mp4", "mask.mp4"))
    if mode in ("face_mesh", "depth_mesh"):
        names.append("face-landmarks.json")
    if mode == "depth_mesh":
        names.append("depth-composite-silent.mp4")
    try:
        audio = json.loads((folder / "audio-manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Prepare the exact video and audio before review.") from exc
    pitched = audio.get("embedded_vocals") if isinstance(audio, dict) else None
    if not isinstance(pitched, str) or not pitched or Path(pitched).name != pitched or "\\" in pitched:
        raise ValueError("Prepared embedded vocals are missing from the audio manifest.")
    names.append(pitched)
    digest = hashlib.sha256(("genjutsu-reviewed-input-v2:" + mode).encode("utf-8"))
    for name in sorted(set(names)):
        path = folder / name
        if not path.is_file():
            raise ValueError("Prepare the exact video, source and audio before review; missing " + name + ".")
        item = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                item.update(chunk)
        digest.update(json.dumps([name, path.stat().st_size, item.hexdigest()]).encode("utf-8"))
    return digest.hexdigest()


def state(folder):
    path = Path(folder) / "mask-review.json"
    try:
        saved = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, ValueError):
        saved = {}  # A damaged review requires a fresh approval of intact assets.
    try:
        current = fingerprint(folder)
    except (OSError, ValueError):
        return {"approved": False, "status": "unavailable", "note": "Prepare the exact video and audio first."}
    if not isinstance(saved, dict) or saved.get("fingerprint") != current:
        return {
            "approved": False,
            "status": "pending",
            "note": "Review the entire prepared input, embedded dialogue and timing; inspect mask coverage or facial tracking and overlay alignment.",
            "fingerprint": current,
        }
    return saved


def review(folder, approved, note, expected):
    if not isinstance(approved, bool):
        raise ValueError("Approval must be a boolean.")
    with job_lock(folder):
        current = fingerprint(folder)
        if current != expected:
            raise ValueError("The prepared video, source or audio changed. Reload and review the latest preview.")
        data = {
            "approved": approved,
            "status": "approved" if approved else "rejected",
            "note": note,
            "fingerprint": current,
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        }
        atomic_json(Path(folder) / "mask-review.json", data)
        return data


def require_approved(folder):
    if state(folder).get("approved") is not True:
        raise ValueError("Input review required: inspect the whole prepared video and embedded audio, then approve its current artifacts before submitting.")
