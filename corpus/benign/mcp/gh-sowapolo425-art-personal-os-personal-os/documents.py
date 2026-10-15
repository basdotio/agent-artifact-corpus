"""Text-only local PDF/DOCX imports. Never execute embedded instructions or macros."""
import io
import zipfile
from pathlib import PurePosixPath
from xml.etree import ElementTree

from .importer import MAX_UPLOAD, MAX_ITEMS, import_key
from .store import MAX_TEXT


def parse_document(filename, data):
    if (not isinstance(filename, str) or not filename or len(filename) > 180
            or "/" in filename or "\\" in filename):
        raise ValueError("Choose a file name, not a path")
    if not isinstance(data, bytes) or not 1 <= len(data) <= MAX_UPLOAD:
        raise ValueError("Document must be at most 8 MB")
    suffix = PurePosixPath(filename).suffix.lower()
    sections = []
    try:
        if suffix == ".pdf":
            from pypdf import PdfReader
            from pypdf.errors import PyPdfError
            try:
                reader = PdfReader(io.BytesIO(data))
                if reader.is_encrypted:
                    raise ValueError("Encrypted PDF is not supported")
                if len(reader.pages) > 200:
                    raise ValueError("PDF exceeds 200 pages; split it first")
                for page_number, page in enumerate(reader.pages, 1):
                    text = page.extract_text() or ""
                    if text.strip():
                        sections.append((f"第 {page_number} 页", text))
            except (PyPdfError, KeyError, TypeError) as exc:
                raise ValueError("Cannot read this PDF; export its text first") from exc
        elif suffix == ".docx":
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                infos = archive.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > 32 * 1024 * 1024:
                    raise ValueError("DOCX exceeds expanded size/file limits")
                if sum(i.filename == "word/document.xml" for i in infos) != 1:
                    raise ValueError("DOCX requires one word/document.xml")
                if archive.getinfo("word/document.xml").file_size > MAX_UPLOAD:
                    raise ValueError("DOCX body exceeds 8 MB")
                body = ElementTree.fromstring(archive.read("word/document.xml"))
                ns = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                # Preserve line breaks/tabs; ignore field instructions and metadata.
                tags = {"{" + ns["w"] + "}" + tag: value for tag, value in
                        (("tab", "\t"), ("br", "\n"), ("cr", "\n"))}
                text_tag = "{" + ns["w"] + "}t"
                paragraphs = ["".join((element.text or "") if element.tag == text_tag
                                      else tags.get(element.tag, "") for element in p.iter())
                              for p in body.findall(".//w:p", ns)]
                sections.append(("正文", "\n".join(p for p in paragraphs if p.strip())))
        else:
            raise ValueError("Binary import supports PDF and DOCX only")
    except (zipfile.BadZipFile, ElementTree.ParseError, RuntimeError, OSError) as exc:
        raise ValueError("Invalid document; export UTF-8 text instead") from exc
    if sum(len(text.encode("utf-8")) for _, text in sections) > MAX_UPLOAD:
        raise ValueError("Extracted text exceeds 8 MB; split the document")
    items = []
    for label, text in sections:
        if not text.strip():
            continue
        for offset in range(0, len(text), MAX_TEXT):
            chunk = text[offset:offset + MAX_TEXT]
            if not chunk.strip():
                continue
            title = f"{filename} · {label}" + (f" · 片段 {offset // MAX_TEXT + 1}" if len(text) > MAX_TEXT else "")
            locator = f"{label}/chunk:{offset // MAX_TEXT + 1}"
            items.append(dict(key=import_key(filename, locator, chunk), title=title, content=chunk,
                              locator=locator, filename=filename, source_created_at=None))
    if not items:
        raise ValueError("No extractable text; scanned PDFs/images require OCR by your Agent")
    if len(items) > MAX_ITEMS:
        raise ValueError("Too many text fragments; split the document")
    return list({item["key"]: item for item in items}.values())
