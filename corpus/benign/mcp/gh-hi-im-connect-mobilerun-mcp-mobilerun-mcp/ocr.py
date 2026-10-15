"""Host-side OCR with tesseract, used for screens whose accessibility tree is sparse."""

from __future__ import annotations

import asyncio
import shutil
from dataclasses import dataclass, replace

from .models import Bounds, Mark

MIN_CONF = 50.0


@dataclass(frozen=True)
class OcrLine:
    text: str
    bounds: Bounds
    confidence: float


def parse_tesseract_tsv(tsv: str) -> list[OcrLine]:
    """Group word rows into text lines (block/paragraph/line), dropping low-confidence words."""
    grouped: dict[tuple[str, str, str], list[tuple[int, int, int, int, str, float]]] = {}
    for row in tsv.splitlines()[1:]:
        cols = row.split("\t")
        if len(cols) < 12 or cols[0] != "5":
            continue
        try:
            conf = float(cols[10])
            left, top, width, height = (int(c) for c in cols[6:10])
        except ValueError:
            continue
        text = cols[11].strip()
        if not text or conf < MIN_CONF:
            continue
        grouped.setdefault((cols[2], cols[3], cols[4]), []).append(
            (left, top, left + width, top + height, text, conf)
        )
    lines = []
    for words in grouped.values():
        words.sort()
        lines.append(
            OcrLine(
                text=" ".join(w[4] for w in words),
                bounds=Bounds(
                    min(w[0] for w in words),
                    min(w[1] for w in words),
                    max(w[2] for w in words),
                    max(w[3] for w in words),
                ),
                confidence=sum(w[5] for w in words) / len(words),
            )
        )
    return sorted(lines, key=lambda ln: (ln.bounds.top, ln.bounds.left))


def available() -> bool:
    return shutil.which("tesseract") is not None


async def run_tesseract(png: bytes, lang: str = "eng", timeout: float = 30.0) -> list[OcrLine]:
    binary = shutil.which("tesseract")
    if binary is None:
        return []
    proc = await asyncio.create_subprocess_exec(
        binary,
        "stdin",
        "stdout",
        "-l",
        lang,
        "--psm",
        "11",
        "tsv",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(png), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return []
    return parse_tesseract_tsv(out.decode("utf-8", "replace"))


def uncovered_lines(lines: list[OcrLine], marks: list[Mark]) -> list[OcrLine]:
    """OCR lines whose center is not inside any existing mark."""
    result = []
    for line in lines:
        cx, cy = line.bounds.center
        if not any(m.bounds.contains_point(cx, cy) for m in marks):
            result.append(line)
    return result


def merge_ocr_marks(marks: list[Mark], lines: list[OcrLine]) -> list[Mark]:
    """Append uncovered OCR text as extra marks, renumbering everything in reading order."""
    extra = [
        Mark(
            id=0, kind="text", label=ln.text[:80], bounds=ln.bounds, element_index=-1, source="ocr"
        )
        for ln in uncovered_lines(lines, marks)
    ]
    combined = sorted(marks + extra, key=lambda m: (m.bounds.top, m.bounds.left))
    return [replace(m, id=i) for i, m in enumerate(combined, start=1)]
