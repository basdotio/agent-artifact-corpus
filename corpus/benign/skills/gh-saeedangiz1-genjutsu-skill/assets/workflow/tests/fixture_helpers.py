"""Small local inputs for mocked provider regression tests, not visual evidence."""
import json
from pathlib import Path
from PIL import Image
import mask_review


def prepared_fixture(folder, mode="depth"):
    folder = Path(folder)
    for name in mask_review.COMMON_FILES:
        (folder / name).write_bytes(b"test artifact")
    (folder / "audio-manifest.json").write_text(json.dumps({"embedded_vocals": "vocals-plus3.wav"}), encoding="utf-8")
    (folder / "vocals-plus3.wav").write_bytes(b"test pitched audio")
    if mode != "depth":
        (folder / "workflow-mode.json").write_text(json.dumps({"mode": mode}), encoding="utf-8")
    if mode in ("depth", "depth_mesh"):
        for name in ("depth.mp4", "mask.mp4"):
            (folder / name).write_bytes(b"test mask artifact")
    if mode in ("face_mesh", "depth_mesh"):
        (folder / "face-landmarks.json").write_text("{}", encoding="utf-8")
    if mode == "depth_mesh":
        (folder / "depth-composite-silent.mp4").write_bytes(b"test depth artifact")
    reference = folder / "reference.png"
    Image.new("RGB", (64, 64), (70, 120, 150)).save(reference)
    return reference
