"""On-host UI element detection for perceive_screen(detail="full").

Runs Microsoft's OmniParser v2 icon detector (YOLOv8, exported to ONNX by onnx-community) with
onnxruntime on the host, so it works for any device the server can screenshot: x86_64 or ARM,
emulator or physical. The model (~80 MB, AGPL-3.0) is not bundled; it is downloaded on first use
into ~/.cache/mobilerun-mcp (override with MOBILERUN_DETECTOR_MODEL=<path to .onnx>).
"""

from __future__ import annotations

import asyncio
import io
import os
import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

MODEL_URL = (
    "https://huggingface.co/onnx-community/OmniParser-v2.0_icon_detect/resolve/main/onnx/model.onnx"
)
CACHE = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "mobilerun-mcp"
INPUT = 640
CONF = 0.25
IOU = 0.5
MAX_BOXES = 200

_session = None
_lock = threading.Lock()


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int
    score: float


def model_path() -> Path:
    configured = os.environ.get("MOBILERUN_DETECTOR_MODEL")
    if configured:
        return Path(configured).expanduser()
    path = CACHE / "omniparser_icon_detect.onnx"
    if not path.is_file():
        CACHE.mkdir(parents=True, exist_ok=True)
        partial = path.with_suffix(".part")
        urllib.request.urlretrieve(MODEL_URL, partial)  # noqa: S310 - fixed https URL
        partial.rename(path)
    return path


def _get_session():
    global _session
    with _lock:
        if _session is None:
            import onnxruntime as ort

            _session = ort.InferenceSession(str(model_path()), providers=["CPUExecutionProvider"])
    return _session


def _letterbox(image: Image.Image) -> tuple[np.ndarray, float, int, int]:
    w, h = image.size
    scale = INPUT / max(w, h)
    nw, nh = round(w * scale), round(h * scale)
    canvas = Image.new("RGB", (INPUT, INPUT), (114, 114, 114))
    px, py = (INPUT - nw) // 2, (INPUT - nh) // 2
    canvas.paste(image.resize((nw, nh), Image.BILINEAR), (px, py))
    tensor = np.asarray(canvas, dtype=np.float32).transpose(2, 0, 1)[None] / 255.0
    return tensor, scale, px, py


def _iou(box: np.ndarray, others: np.ndarray) -> np.ndarray:
    x1 = np.maximum(box[0], others[:, 0])
    y1 = np.maximum(box[1], others[:, 1])
    x2 = np.minimum(box[2], others[:, 2])
    y2 = np.minimum(box[3], others[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area = (box[2] - box[0]) * (box[3] - box[1])
    areas = (others[:, 2] - others[:, 0]) * (others[:, 3] - others[:, 1])
    return inter / np.maximum(area + areas - inter, 1e-6)


def nms(boxes: np.ndarray, scores: np.ndarray, iou: float = IOU) -> list[int]:
    order = scores.argsort()[::-1]
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        rest = order[1:]
        order = rest[_iou(boxes[i], boxes[rest]) < iou]
    return keep


def decode(output: np.ndarray, scale: float, px: int, py: int, size: tuple[int, int]) -> list[Box]:
    """YOLOv8 head [1, 5, N] (cx, cy, w, h, score in 640 space) -> screen boxes."""
    pred = output[0].T
    pred = pred[pred[:, 4] >= CONF]
    if not len(pred):
        return []
    cx, cy, w, h = pred[:, 0], pred[:, 1], pred[:, 2], pred[:, 3]
    boxes = np.stack([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], axis=1)
    boxes[:, [0, 2]] = (boxes[:, [0, 2]] - px) / scale
    boxes[:, [1, 3]] = (boxes[:, [1, 3]] - py) / scale
    boxes[:, [0, 2]] = boxes[:, [0, 2]].clip(0, size[0])
    boxes[:, [1, 3]] = boxes[:, [1, 3]].clip(0, size[1])
    keep = nms(boxes, pred[:, 4])[:MAX_BOXES]
    return [
        Box(
            int(boxes[i, 0]),
            int(boxes[i, 1]),
            int(boxes[i, 2]),
            int(boxes[i, 3]),
            float(pred[i, 4]),
        )
        for i in keep
        if boxes[i, 2] - boxes[i, 0] >= 4 and boxes[i, 3] - boxes[i, 1] >= 4
    ]


def detect_sync(png: bytes) -> list[Box]:
    image = Image.open(io.BytesIO(png)).convert("RGB")
    tensor, scale, px, py = _letterbox(image)
    session = _get_session()
    output = session.run(None, {session.get_inputs()[0].name: tensor})[0]
    return decode(output, scale, px, py, image.size)


async def detect(png: bytes) -> list[Box]:
    return await asyncio.to_thread(detect_sync, png)
