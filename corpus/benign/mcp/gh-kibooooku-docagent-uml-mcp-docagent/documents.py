"""Bounded document tools shared by the local and MCP transports.

The JSON format is deliberately small. PDF import is a page-text heuristic:
it does not perform OCR, infer reading order, or recognize tables or figures.
"""

from __future__ import annotations

import base64
import json
import re
import shutil
from pathlib import Path
from typing import Any


class ToolError(ValueError):
    """An invalid document request or a recoverable tool execution failure."""


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


def _schema(properties: dict[str, dict], required: list[str]) -> dict:
    return {"type": "object", "properties": properties, "required": required,
            "additionalProperties": False}


_DOC = {"type": "string", "description": "Document identifier"}
TOOL_DEFINITIONS = [
    {"name": "get_outline", "description": "Read section, table, and image identifiers and page numbers.",
     "inputSchema": _schema({"doc_id": _DOC}, ["doc_id"])},
    {"name": "search", "description": "Literal case-insensitive search in sections, tables, and image captions; returns full matching evidence.",
     "inputSchema": _schema({"doc_id": _DOC, "keyword": {"type": "string", "minLength": 1, "maxLength": 200}}, ["doc_id", "keyword"])},
    {"name": "get_section_content", "description": "Read the complete text of one document section.",
     "inputSchema": _schema({"doc_id": _DOC, "section_id": {"type": "string"}}, ["doc_id", "section_id"])},
    {"name": "get_image", "description": "Read an identified figure and its caption as evidence, with image content.",
     "inputSchema": _schema({"doc_id": _DOC, "image_id": {"type": "string"}}, ["doc_id", "image_id"])},
    {"name": "get_page_images", "description": "Render an inclusive one-based PDF page range (at most 8 pages).",
     "inputSchema": _schema({"doc_id": _DOC, "start_page_num": {"type": "integer", "minimum": 1}, "end_page_num": {"type": "integer", "minimum": 1}}, ["doc_id", "start_page_num", "end_page_num"])},
    {"name": "get_table_image", "description": "Read a table's authoritative text and optional table image.",
     "inputSchema": _schema({"doc_id": _DOC, "table_id": {"type": "string"}}, ["doc_id", "table_id"])},
]


def _identifier(value: Any, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ToolError(f"Invalid {label}: use 1-80 ASCII letters, digits, underscores, or hyphens.")
    return value


class DocumentStore:
    """Read-only tool access restricted to one directory, including all assets."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir).resolve()
        if not self.data_dir.is_dir():
            raise ToolError("Document data directory does not exist.")

    def _path(self, relative: str) -> Path:
        if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
            raise ToolError("Document asset paths must be nonempty relative paths.")
        candidate = (self.data_dir / relative).resolve()
        if not candidate.is_relative_to(self.data_dir):
            raise ToolError("Document path escapes the configured data directory.")
        if not candidate.is_file():
            raise ToolError("Document asset does not exist.")
        return candidate

    def _load(self, doc_id: str) -> dict:
        _identifier(doc_id, "doc_id")
        try:
            document = json.loads(self._path(f"{doc_id}.json").read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ToolError("Could not read document JSON.") from exc
        if not isinstance(document, dict) or document.get("doc_id") != doc_id:
            raise ToolError("Document identifier does not match its file.")
        pages = []
        for kind in ("sections", "tables", "images"):
            entries = document.get(kind, [])
            if not isinstance(entries, list):
                raise ToolError(f"Document {kind} must be a list.")
            seen = set()
            for entry in entries:
                if not isinstance(entry, dict):
                    raise ToolError("Document entries must be objects.")
                identity = _identifier(entry.get("id"), "entry id")
                if identity in seen:
                    raise ToolError("Duplicate document entry identifier.")
                seen.add(identity)
                page = entry.get("page")
                if type(page) is not int or page < 1:
                    raise ToolError("Document pages must be positive one-based integers.")
                pages.append(page)
                text_key = "caption" if kind == "images" else "text"
                if not isinstance(entry.get(text_key), str):
                    raise ToolError(f"Document entry requires string {text_key}.")
        inferred_count = max(pages, default=1)
        page_count = document.get("page_count", inferred_count)
        if type(page_count) is not int or page_count < inferred_count:
            raise ToolError("Document page_count is invalid.")
        document["page_count"] = page_count
        return document

    @staticmethod
    def _evidence(document: dict, entry: dict, source_type: str) -> dict:
        return {"id": f"{document['doc_id']}:{source_type}:{entry['id']}",
                "doc_id": document["doc_id"], "page": entry["page"],
                "section_id": entry["id"], "text": entry["caption"] if source_type == "image" else entry["text"],
                "source_type": source_type}

    @staticmethod
    def _entry(document: dict, kind: str, identity: str) -> dict:
        _identifier(identity, "entry id")
        for entry in document.get(kind, []):
            if entry["id"] == identity:
                return entry
        raise ToolError(f"Unknown {kind} identifier.")

    def _image(self, relative: str) -> dict:
        path = self._path(relative)
        data = path.read_bytes()
        if len(data) > 8 * 1024 * 1024:
            raise ToolError("Image exceeds the 8 MiB tool limit.")
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            mime = "image/png"
        elif data.startswith(b"\xff\xd8\xff"):
            mime = "image/jpeg"
        else:
            raise ToolError("Only PNG and JPEG document images are supported.")
        return {"data": base64.b64encode(data).decode("ascii"), "mimeType": mime}

    def call(self, name: str, arguments: dict) -> dict:
        definition = next((item for item in TOOL_DEFINITIONS if item["name"] == name), None)
        if definition is None:
            raise ToolError("Unknown document tool.")
        schema = definition["inputSchema"]
        if not isinstance(arguments, dict) or set(arguments) != set(schema["required"]):
            raise ToolError("Tool arguments must exactly match the required fields.")
        document = self._load(arguments["doc_id"])
        if name == "get_outline":
            return {"doc_id": document["doc_id"], "title": document.get("title", document["doc_id"]),
                    "page_count": document["page_count"],
                    "sections": [{key: entry[key] for key in ("id", "title", "page") if key in entry} for entry in document.get("sections", [])],
                    "tables": [{"id": entry["id"], "page": entry["page"]} for entry in document.get("tables", [])],
                    "figures": [{"id": entry["id"], "page": entry["page"], "caption": entry["caption"]} for entry in document.get("images", [])],
                    "evidence": []}
        if name == "search":
            keyword = arguments["keyword"]
            if not isinstance(keyword, str) or not keyword.strip() or len(keyword) > 200:
                raise ToolError("Search keyword must contain 1-200 characters.")
            found = []
            for kind, source_type in (("sections", "text"), ("tables", "table"), ("images", "image")):
                for entry in document.get(kind, []):
                    evidence = self._evidence(document, entry, source_type)
                    if keyword.casefold() in (entry.get("title", "") + "\n" + evidence["text"]).casefold():
                        found.append(evidence)
            return {"doc_id": document["doc_id"], "keyword": keyword, "evidence": found}
        if name == "get_section_content":
            entry = self._entry(document, "sections", arguments["section_id"])
            return {"evidence": [self._evidence(document, entry, "text")]}
        if name == "get_image":
            entry = self._entry(document, "images", arguments["image_id"])
            return {"evidence": [self._evidence(document, entry, "image")], "images": [self._image(entry.get("path"))]}
        if name == "get_table_image":
            entry = self._entry(document, "tables", arguments["table_id"])
            return {"evidence": [self._evidence(document, entry, "table")],
                    "images": [self._image(entry["image_path"])] if entry.get("image_path") else []}
        start, end = arguments["start_page_num"], arguments["end_page_num"]
        if type(start) is not int or type(end) is not int or not 1 <= start <= end <= document["page_count"]:
            raise ToolError("Page range must be inclusive, one-based, ordered, and within the document.")
        if end - start + 1 > 8:
            raise ToolError("At most 8 pages may be rendered in one request.")
        if not document.get("source_pdf"):
            raise ToolError("This document has no source PDF for page rendering.")
        import fitz

        try:
            with fitz.open(self._path(document["source_pdf"])) as pdf:
                if end > len(pdf):
                    raise ToolError("Page range exceeds the source PDF.")
                images = []
                for page_number in range(start, end + 1):
                    page = pdf[page_number - 1]
                    scale = min(1.5, 1600 / max(page.rect.width, page.rect.height))
                    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
                    images.append({"data": base64.b64encode(pixmap.tobytes("png")).decode("ascii"), "mimeType": "image/png"})
        except (RuntimeError, ValueError, OSError) as exc:
            if isinstance(exc, ToolError):
                raise
            raise ToolError("Could not render source PDF pages.") from exc
        evidence = []
        for kind, source_type in (("sections", "text"), ("tables", "table"), ("images", "image")):
            evidence.extend(self._evidence(document, entry, source_type) for entry in document.get(kind, []) if start <= entry["page"] <= end)
        return {"pages": list(range(start, end + 1)), "evidence": evidence, "images": images}


def import_pdf(path: Path, output_dir: Path, doc_id: str | None = None) -> Path:
    """Copy a PDF and extract page text; retain page images for manual inspection.

    This intentionally makes no table, figure segmentation, OCR, or layout-quality
    claim. An image-only page has empty text and must be inspected visually.
    Existing document JSON/source PDFs are never silently overwritten.
    """
    import fitz

    source = Path(path).resolve()
    if not source.is_file() or source.suffix.lower() != ".pdf":
        raise ToolError("Import requires an existing PDF file.")
    identity = _identifier(doc_id or source.stem, "doc_id")
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    destination = target_dir / f"{identity}.pdf"
    json_path = target_dir / f"{identity}.json"
    if json_path.exists() or (destination.exists() and destination != source):
        raise ToolError("Import target already exists; choose a new doc_id.")
    with fitz.open(source) as pdf:
        if pdf.is_encrypted:
            raise ToolError("Encrypted PDFs are not supported.")
        if not len(pdf):
            raise ToolError("PDF contains no pages.")
        sections = [{"id": f"p{index + 1}", "title": f"Page {index + 1}", "page": index + 1,
                     "text": page.get_text("text", sort=True).strip()} for index, page in enumerate(pdf)]
    document = {"doc_id": identity, "title": source.stem, "source_pdf": destination.name,
                "page_count": len(sections), "sections": sections, "images": [], "tables": [],
                "parser": {"kind": "pymupdf-page-text-heuristic", "ocr": False,
                           "limitations": "Page text only; no table/figure recognition or guaranteed reading order."}}
    if source != destination:
        shutil.copyfile(source, destination)
    json_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return json_path
