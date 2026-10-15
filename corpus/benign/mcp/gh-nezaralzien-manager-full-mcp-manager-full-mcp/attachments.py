"""Turn any evidence file into what Manager will actually accept: images.

Manager's Image field silently rejects PDFs, and a multi-page document has to
become one image per page so each page can be attached to its own record. This
module does that conversion itself — no poppler, no ImageMagick, no Pillow — so
the rule cannot fail for want of a tool that is not installed.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

from manager_full_mcp.config import home

IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tif", ".tiff"})
DEFAULT_DPI = 150
MAX_DPI = 400


class ConversionError(RuntimeError):
    """The file could not be turned into images."""


def output_dir() -> Path:
    path = home() / "converted"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _to_rgb(width: int, height: int, stride: int, buffer: bytes) -> bytearray:
    """Tightly packed RGB pixels, no PNG filter bytes."""
    out = bytearray()
    for y in range(height):
        start = y * stride
        row = bytearray(buffer[start : start + width * 3])
        row[0::3], row[2::3] = row[2::3], row[0::3]  # BGR -> RGB
        out += row
    return out


def _png_from_rgb(width: int, height: int, pixels: bytes) -> bytes:
    """Encode tightly packed RGB pixels as a PNG."""
    rows = bytearray()
    for y in range(height):
        rows += b"\x00" + pixels[y * width * 3 : (y + 1) * width * 3]

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(bytes(rows), 6))
        + chunk(b"IEND", b"")
    )


WHITE = 0xFF
GAP_PIXELS = 24


def _stack(pages: list[tuple[int, int, bytearray]], direction: str) -> tuple[int, int, bytearray]:
    """Compose rendered pages of ONE document into a single canvas."""
    if direction == "vertical":
        width = max(p[0] for p in pages)
        height = sum(p[1] for p in pages) + GAP_PIXELS * (len(pages) - 1)
    else:
        width = sum(p[0] for p in pages) + GAP_PIXELS * (len(pages) - 1)
        height = max(p[1] for p in pages)
    canvas = bytearray([WHITE]) * (width * height * 3)
    offset = 0
    for page_width, page_height, pixels in pages:
        for y in range(page_height):
            src = pixels[y * page_width * 3 : (y + 1) * page_width * 3]
            if direction == "vertical":
                start = ((offset + y) * width) * 3
            else:
                start = (y * width + offset) * 3
            canvas[start : start + len(src)] = src
        offset += (page_height if direction == "vertical" else page_width) + GAP_PIXELS
    return width, height, canvas


@dataclass
class Prepared:
    source: Path
    files: list[Path]
    converted: bool
    pages: int
    note: str

    def payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "source": str(self.source),
            "converted": self.converted,
            "pages": self.pages,
            "files": [str(f) for f in self.files],
            "note": self.note,
        }


def prepare(
    path: str | Path,
    *,
    dpi: int = DEFAULT_DPI,
    out_dir: Path | None = None,
    combine: str = "none",
) -> Prepared:
    """Render `path` to attachable images.

    `combine` only ever joins pages of the *same* document: "none" (one image per
    page), "vertical" or "horizontal". Two different proofs are never merged —
    each one is its own attachment.
    """
    if combine not in {"none", "vertical", "horizontal"}:
        raise ConversionError("combine must be 'none', 'vertical' or 'horizontal'.")
    source = Path(path).expanduser()
    if not source.is_file():
        raise ConversionError(f"No such file: {source}")
    suffix = source.suffix.casefold()

    if suffix in IMAGE_SUFFIXES:
        return Prepared(
            source=source,
            files=[source],
            converted=False,
            pages=1,
            note="Already an image — attach it as is.",
        )
    if suffix != ".pdf":
        raise ConversionError(
            f"Manager accepts images only, and '{suffix or source.name}' is neither an "
            "image nor a PDF this tool can rasterise. Convert it to PNG or JPEG first."
        )

    dpi = max(72, min(int(dpi), MAX_DPI))
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:  # pragma: no cover - dependency is declared
        raise ConversionError(
            "pypdfium2 is not installed in this environment, so PDFs cannot be "
            "converted. Install it, or convert the file to PNG before attaching."
        ) from exc

    target = Path(out_dir) if out_dir else output_dir()
    target.mkdir(parents=True, exist_ok=True)
    try:
        document = pdfium.PdfDocument(str(source))
        count = len(document)
    except Exception as exc:
        raise ConversionError(f"Could not read {source.name} as a PDF: {exc}") from exc

    stem = source.stem.replace("/", "-")
    pages: list[tuple[int, int, bytearray]] = []
    for index in range(count):
        bitmap = document[index].render(scale=dpi / 72)
        if bitmap.mode != "BGR":  # pragma: no cover - pdfium default is BGR
            raise ConversionError(f"Unexpected bitmap mode {bitmap.mode!r} from pdfium.")
        pages.append(
            (
                bitmap.width,
                bitmap.height,
                _to_rgb(bitmap.width, bitmap.height, bitmap.stride, bytes(bitmap.buffer)),
            )
        )

    written: list[Path] = []
    if combine != "none" and count > 1:
        width, height, canvas = _stack(pages, combine)
        out = target / f"{stem}-all-{count}-pages.png"
        out.write_bytes(_png_from_rgb(width, height, bytes(canvas)))
        written.append(out)
        note = (
            f"PDF rasterised at {dpi} dpi and its {count} pages joined "
            f"{combine}ly into ONE image ({width}x{height}px) — one document, one "
            "attachment. Two different proofs are still attached separately."
        )
    else:
        for index, (width, height, pixels) in enumerate(pages):
            name = f"{stem}.png" if count == 1 else f"{stem}-p{index + 1}.png"
            out = target / name
            out.write_bytes(_png_from_rgb(width, height, bytes(pixels)))
            written.append(out)
        note = (
            f"PDF rasterised at {dpi} dpi. Manager rejects PDFs, so attach these "
            f"image{'s' if count > 1 else ''} instead of the original file."
        )
        if count > 1:
            note += (
                f" The document has {count} pages, one image each. If they are one "
                "document (a statement, a contract), pass combine='vertical' to get "
                "a single attachment instead. Never merge two DIFFERENT proofs."
            )
    return Prepared(source=source, files=written, converted=True, pages=count, note=note)
