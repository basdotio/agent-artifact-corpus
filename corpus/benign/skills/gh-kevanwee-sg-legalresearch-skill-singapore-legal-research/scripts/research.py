#!/usr/bin/env python3
"""Offline evidence helpers. No legal database API, citator, or semantic verifier."""

import argparse
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import sys
import unicodedata
import uuid
import xml.etree.ElementTree as ET
import zipfile

# Load bundled siblings explicitly: isolated/safe-path Python omits this folder
# from sys.path, and a working-directory/PYTHONPATH module must not replace them.
def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(
        "_sg_legalresearch_" + name, Path(__file__).resolve().with_name(name + ".py"))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load the bundled {name}.py helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_statutory = _load_sibling("statutory")
converters = _load_sibling("converters")
canonical_provision = _statutory.canonical_provision
build_provisions = _statutory.build_provisions
checked_provisions = _statutory.checked_provisions
select_provision = _statutory.select_provision
verify_statute_receipt = _statutory.verify_statute_receipt

MODES = ("research", "deep-research", "find-authority", "cite-check",
         "legislation-hansard", "case-prep", "library", "proofread")
KINDS = ("case", "legislation", "hansard", "bill", "secondary", "other")
ASSESSMENTS = ("supported", "qualified", "unsupported", "unresolved", "editorial")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,63}\Z")
# Direct identifiers that never belong in a query sent to a search service. Amounts and case
# numbers are left out: statutory thresholds and reported cases are legitimate search terms.
IDENTIFIERS = {
    "NRIC or FIN number": re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I),
    "UEN": re.compile(r"\b(?:\d{8,9}[A-Z]|[RST]\d{2}[A-Z]{2}\d{4}[A-Z])\b"),
    "email address": re.compile(r"\b[\w.+-]+@[\w-]+(?:\.[\w-]+)+\b"),
    "telephone number": re.compile(r"(?<!\d)(?:\+65[\s-]?)?[3689]\d{3}[\s-]?\d{4}(?!\d)"),
}


def read_terms(path):
    """Known sensitive terms, one per line; '#' starts a comment. An unreadable file is an error."""
    terms = []
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        term = " ".join(line.split("#", 1)[0].split())
        if term:
            terms.append(term)
    return terms


def screen_text(text, terms=()):
    """Direct identifiers and matter terms in text, by category and position, never echoing the match."""
    text = unicodedata.normalize("NFKC", str(text))
    findings = [{"category": label, "at": m.start()} for label, pattern in IDENTIFIERS.items()
                for m in pattern.finditer(text)]
    for number, term in enumerate(terms, 1):
        words = r"\s+".join(map(re.escape, unicodedata.normalize("NFKC", term).split()))
        for m in re.finditer(rf"(?<!\w){words}(?!\w)", text, re.I):
            findings.append({"category": f"matter term {number}", "at": m.start()})
    return sorted(findings, key=lambda f: f["at"])


def screen(text, terms_file=None):
    findings = screen_text(text, read_terms(terms_file) if terms_file else ())
    return {"status": "fail" if findings else "pass", "findings": findings,
            "terms_checked": terms_file is not None,
            "meaning": "Direct identifiers and listed terms only. Indirect identifiers, such as a "
                       "distinctive fact pattern, remain the researcher's responsibility."}


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(65536), b""):
            h.update(block)
    return h.hexdigest()


def normalise(text):
    # Whitespace and Unicode composition only: no case/punctuation/word changes.
    return " ".join(unicodedata.normalize("NFC", text).split())


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("date must use YYYY-MM-DD")
    date.fromisoformat(value)
    return value


def inside(root, relative):
    if not isinstance(relative, str) or not relative or Path(relative).is_absolute():
        raise ValueError("evidence paths must be non-empty relative paths")
    target = (Path(root) / relative).resolve()
    if not target.is_relative_to(Path(root).resolve()):
        raise ValueError("evidence path escapes the run folder")
    return target


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value, *, new=False):
    path = Path(path)
    text = json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    if new:
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
    else:
        temporary = path.with_name(path.name + ".tmp")
        # "w": a temporary file left by an interrupted write must not block the run.
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        temporary.replace(path)


def load_run(root):
    data = read_json(Path(root) / "run.json")
    if not isinstance(data, dict):
        raise ValueError("run.json must be an object")
    return data


PIN_UNIT = (r"\[([1-9]\d*)((?:\([A-Za-z0-9]+\))*)\]"
            r"(?:\s*[-–—]\s*\[([1-9]\d*)((?:\([A-Za-z0-9]+\))*)\])?")


def pinpoint_units(value):
    """Parse explicit paragraph pinpoints, keeping any sub-paragraph labels such as [185(b)]."""
    if not nonempty(value):
        raise ValueError("a paragraph pinpoint is required")
    value = re.sub(r"^at\s+", "", value.strip())
    value = re.sub(r"\s+and\s+", ", ", value)
    if not re.fullmatch(PIN_UNIT + r"(?:\s*,\s*" + PIN_UNIT + r")*", value):
        raise ValueError("use paragraph pinpoints such as [35], [35]–[37], [35], [39] or [35(b)]")
    units = []
    for m in re.finditer(PIN_UNIT, value):
        first, last = int(m[1]), int(m[3] or m[1])
        first_sub, last_sub = m[2], (m[4] if m[3] else m[2])
        if last < first:
            raise ValueError("paragraph ranges must run forwards")
        simple = re.fullmatch(r"\(([a-z])\)", first_sub or "") and re.fullmatch(r"\(([a-z])\)", last_sub or "")
        if first == last and simple and last_sub < first_sub:
            raise ValueError("sub-paragraph ranges must run forwards")
        units.append((first, first_sub, last, last_sub))
    return units


def parse_pinpoint(value):
    """Paragraph ranges cited; a sub-paragraph resolves to its whole paragraph."""
    return [(first, last) for first, _, last, _ in pinpoint_units(value)]


def canonical_pinpoint(value):
    def unit(first, first_sub, last, last_sub):
        start = f"[{first}{first_sub}]"
        return start if (first, first_sub) == (last, last_sub) else f"{start}–[{last}{last_sub}]"
    return ", ".join(unit(*u) for u in pinpoint_units(value))


def has_subparagraph(value):
    try:
        return any(first_sub or last_sub for _, first_sub, _, last_sub in pinpoint_units(value))
    except ValueError:
        return False


def build_paragraphs(text, style):
    """Index explicit line-start labels; boundary accuracy still needs source review."""
    if style not in ("bracketed", "numbered"):
        raise ValueError("paragraph style must be bracketed or numbered")
    # A conversion must keep notes separate. Refuse rather than guess which note
    # belongs to which paragraph or silently drop potentially relevant material.
    note_block = (r"^\s*(?:(?:footnotes?|endnotes?|notes)\s*:?\s*$"
                  r"|\[(?:note|fn)\s*:?\s*\d+\]"
                  r"|(?:footnote|endnote)\s+\d+\s*(?:[:.)\]—–-]|$))")
    if re.search(note_block, text, re.I | re.M):
        raise ValueError("separate footnote/endnote block in judgment text; preserve notes separately "
                         "and use a documented body-only extraction before indexing")
    label = r"\[([1-9]\d*)\]" if style == "bracketed" else r"([1-9]\d*)"
    horizontal = r"[\t \u00a0\u2000-\u200a]"
    bare_label = r"(?:\[[1-9]\d*\]|[1-9]\d*)"
    if re.search(r"^" + horizontal + "*" + bare_label + horizontal + r"*\r?$", text, re.M):
        raise ValueError("paragraph label on its own line; use an extraction that preserves paragraph boundaries")
    lettered = r"\[[1-9]\d*[A-Za-z]\]" if style == "bracketed" else r"[1-9]\d*[A-Za-z]"
    if re.search(r"^" + horizontal + "*" + lettered + r"(?=" + horizontal + r"|\r?$)", text, re.M):
        raise ValueError("lettered paragraph labels need manual verification; this indexer supports integer labels only")
    matches = list(re.finditer(r"^" + horizontal + "*" + label + horizontal + r"+(?=\S)", text, re.M))
    if not matches:
        raise ValueError("no explicit paragraph labels found; use a suitable source text extraction")
    numbers = [int(m[1]) for m in matches]
    for previous, current in zip(numbers, numbers[1:]):
        if current != previous + 1:
            raise ValueError(f"paragraph numbering must be consecutive; found {previous} then {current}. Check extraction or split separate opinions")
    rows = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        end = start + len(text[start:end].rstrip())
        if not text[start:end].strip():
            raise ValueError("empty paragraph")
        rows.append({"paragraph": int(match[1]), "start": start, "end": end, "text": text[start:end]})
    return rows


def checked_paragraphs(source, text):
    index = source.get("paragraph_index")
    if not isinstance(index, dict) or index.get("boundaries_reviewed") is not True or not nonempty(index.get("review_note")):
        raise ValueError("case evidence needs a paragraph index with reviewed boundaries")
    if index.get("text_sha256") != source.get("text_sha256"):
        raise ValueError("paragraph index refers to a different text snapshot")
    expected = build_paragraphs(text, index.get("style"))
    if index.get("paragraphs") != expected:
        raise ValueError("paragraph index does not match source paragraph labels, full text and offsets")
    return expected


def select_paragraphs(rows, pinpoint):
    selected, seen = [], set()
    for first, last in parse_pinpoint(pinpoint):
        matches = [p for p in rows if first <= p["paragraph"] <= last]
        if len(matches) != last - first + 1:
            raise ValueError("cited paragraph or part of its range is missing from the source")
        for p in matches:
            if p["paragraph"] not in seen:
                selected.append(dict(p))
                seen.add(p["paragraph"])
    return selected


def source_and_text(root, source_id):
    data = load_run(root)
    source = next((s for s in data["sources"] if s.get("id") == source_id), None)
    if source is None:
        raise ValueError("unknown source id")
    for p, h in (("file", "sha256"), ("text_file", "text_sha256")):
        if digest(inside(root, source[p])) != source[h]:
            raise ValueError("source snapshot changed; do not index altered evidence")
    return data, source, inside(root, source["text_file"]).read_text(encoding="utf-8-sig")


def index_paragraphs(root, source_id, style, review_note):
    if not nonempty(review_note):
        raise ValueError("explain how paragraph boundaries and numbering were checked against the source")
    data, source, text = source_and_text(root, source_id)
    source["paragraph_index"] = {"style": style, "text_sha256": source["text_sha256"],
        "boundaries_reviewed": True, "review_note": review_note, "paragraphs": build_paragraphs(text, style)}
    write_json(Path(root) / "run.json", data)
    return {"source_id": source_id, "paragraphs_indexed": len(source["paragraph_index"]["paragraphs"])}


def capture_passages(root, source_id, pinpoint):
    _, source, text = source_and_text(root, source_id)
    paragraphs = select_paragraphs(checked_paragraphs(source, text), pinpoint)
    citation = source["citation"]
    if source["title"] not in citation:
        citation = source["title"] + " " + citation
    pinpoint = canonical_pinpoint(pinpoint)
    return {"case_name": source["title"], "citation": citation + " at " + pinpoint,
            "version": source["version"], "url": source["url"],
            "evidence": {"source_id": source_id, "pinpoint": pinpoint, "passages": paragraphs,
                         "pinpoint_reviewed": False, "support_note": ""}}


def index_provisions(root, source_id, manifest, review_note):
    data, source, text = source_and_text(root, source_id)
    if source.get("kind") != "legislation" or not nonempty(review_note):
        raise ValueError("select a legislation source and explain the boundary review")
    if not isinstance(manifest, dict):
        raise ValueError("provision map must be an object")
    receipt = manifest.get("statute_verification")
    candidate = dict(source, statute_verification=receipt)
    verify_statute_receipt(data, candidate)
    iso_date(receipt.get("law_as_at"))
    source["provision_index"] = {"text_sha256": source["text_sha256"], "boundaries_reviewed": True,
        "review_note": review_note, "provisions": build_provisions(text, manifest)}
    source["statute_verification"] = receipt
    write_json(Path(root) / "run.json", data)
    return {"source_id": source_id, "provisions_indexed": len(source["provision_index"]["provisions"])}


def capture_provision(root, source_id, locator):
    data, source, text = source_and_text(root, source_id)
    passages, context = select_provision(checked_provisions(source, text), locator)
    receipt = verify_statute_receipt(data, source)
    return {"instrument": source["title"], "instrument_citation": source["citation"],
            "version": source["version"], "url": source["url"],
            "evidence": {"source_id": source_id, "pinpoint": canonical_provision(locator),
                         "locator_type": "provision", "law_as_at": receipt.get("law_as_at"),
                         "passages": passages, "context": context,
                         "pinpoint_reviewed": False, "support_note": ""}}


def locate_quote(root, source_id, pinpoint, words, occurrence=None, quote_id="", claim_id=""):
    """Find quoted words inside the cited passage only and return a quote record for run.json."""
    if not nonempty(words):
        raise ValueError("give the quoted words")
    if re.search(r"\.\.\.|…", words):
        raise ValueError("quote each unaltered segment separately; do not include an ellipsis")
    data, source, text = source_and_text(root, source_id)
    if source.get("kind") == "legislation":
        rows = checked_provisions(source, text)
        passages, _ = select_provision(rows, pinpoint)
        pinpoint = canonical_provision(pinpoint)
        where = lambda i: next((p["locator"] for p in sorted(rows, key=lambda p: p["end"] - p["start"])
                                if p["start"] <= i < p["end"]), "outside the mapped provisions")
    else:
        rows = checked_paragraphs(source, text)
        passages = select_paragraphs(rows, pinpoint)
        pinpoint = canonical_pinpoint(pinpoint)
        where = lambda i: next((f"[{p['paragraph']}]" for p in rows if p["start"] <= i < p["end"]),
                               "outside the numbered paragraphs")
    # Exact words, but any run of whitespace in them may match any run in the source.
    pattern = re.compile(r"\s+".join(re.escape(w) for w in words.split()))
    hits = [m for p in passages for m in pattern.finditer(text, p["start"], p["end"])]
    if not hits:
        elsewhere = list(dict.fromkeys(where(m.start()) for m in pattern.finditer(text)))  # source order
        found = f"; the words occur at {', '.join(elsewhere)}" if elsewhere else "; they do not occur in the source"
        raise ValueError(f"quoted words not found in {pinpoint}{found}")
    if occurrence is None and len(hits) > 1:
        raise ValueError(f"the words occur {len(hits)} times in {pinpoint}; choose one with --occurrence")
    if occurrence is not None and not 1 <= occurrence <= len(hits):
        raise ValueError(f"--occurrence must be between 1 and {len(hits)}")
    match = hits[(occurrence or 1) - 1]
    record = {"id": quote_id, "claim_id": claim_id, "source_id": source_id, "pinpoint": pinpoint,
              "text": match.group(0), "start": match.start(), "end": match.end(), "pinpoint_reviewed": False}
    if source.get("kind") == "case" and has_subparagraph(pinpoint):
        record["scope"] = {
            "kind": "full-numbered-paragraphs", "requested_pinpoint": pinpoint,
            "searched_paragraphs": [p["paragraph"] for p in passages],
            "warning": "Sub-paragraph boundaries are not indexed. The search covers the full parent "
                       "paragraph(s), so sibling text may match. Manually verify the stated sub-paragraph "
                       "before setting pinpoint_reviewed=true."}
    return record


def init_run(root, question, mode, research_date, law_as_at, matter_terms=None):
    iso_date(research_date)
    iso_date(law_as_at)
    if mode not in MODES or not nonempty(question):
        raise ValueError("a question and a supported mode are required")
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "run_id": uuid.uuid4().hex, "question": question, "mode": mode,
            "research_date": research_date, "law_as_at": law_as_at,
            "sources": [], "claims": [], "quotes": [], "inventory": [],
            "search_log": [], "gaps": [], "review": "", "draft": None}
    if matter_terms is not None:
        read_terms(matter_terms)
        data["matter_terms"] = str(Path(matter_terms).resolve())
    write_json(root / "run.json", data, new=True)
    return data


def snapshot(root, file, source_id, title, kind, url, citation, version,
             text_file=None, transformation=""):
    root = Path(root)
    data = load_run(root)
    if not ID.fullmatch(source_id) or kind not in KINDS:
        raise ValueError("invalid source id or kind")
    if any(s.get("id") == source_id for s in data["sources"]):
        raise ValueError("source id already exists")
    if not all(nonempty(v) for v in (title, url, citation, version)):
        raise ValueError("title, URL, citation, and actual version are required")
    if text_file and not nonempty(transformation):
        raise ValueError("a derived text file needs a transformation description")
    file = Path(file)
    if not text_file:
        file.read_text(encoding="utf-8-sig")  # Reject binary input as quotation text.
    else:
        Path(text_file).read_text(encoding="utf-8-sig")
    folder = root / "sources" / source_id
    folder.mkdir(parents=True, exist_ok=False)
    original = folder / ("source" + file.suffix.lower())
    shutil.copyfile(file, original)
    text_path = original
    if text_file:
        text_path = folder / "extracted.txt"
        shutil.copyfile(text_file, text_path)
    source = {"id": source_id, "title": title, "kind": kind, "url": url,
              "citation": citation, "version": version,
              "snapshotted_at": datetime.now(timezone.utc).isoformat(),
              "retrieved_on": "", "file": original.relative_to(root).as_posix(),
              "sha256": digest(original), "text_file": text_path.relative_to(root).as_posix(),
              "text_sha256": digest(text_path), "transformation": transformation,
              "publication_authority": "", "identity_verified": False,
              "full_text_reviewed": False, "review_note": "", "version_review": "",
              "treatment": {"status": "not-checked", "note": "", "search_ids": []}}
    data["sources"].append(source)
    write_json(root / "run.json", data)
    return source


def xml_text(node):
    pieces = []
    for child in node.iter():
        if child.tag in (W + "t", W + "delText"):
            pieces.append(child.text or "")
        elif child.tag == W + "tab":
            pieces.append("\t")
        elif child.tag in (W + "br", W + "cr"):
            pieces.append("\n")
        elif child.tag in (W + "footnoteReference", W + "endnoteReference"):
            label = child.tag.split("}")[1].replace("Reference", "")
            pieces.append(f"[{label}-id:{child.get(W + 'id')}]")
    return "".join(pieces)


def extract_docx(file):
    """Inventory paragraphs including table cells; retain note IDs and warn on revisions."""
    blocks, warnings = [], []
    with zipfile.ZipFile(file) as archive:
        if sum(i.file_size for i in archive.infolist()) > 100 * 1024 * 1024:
            raise ValueError("DOCX uncompressed content exceeds 100 MiB")
        for part in ("document", "footnotes", "endnotes"):
            name = f"word/{part}.xml"
            if name not in archive.namelist():
                if part == "document":
                    raise ValueError("missing Word document body")
                continue
            xml = ET.fromstring(archive.read(name))
            if any(n.tag in (W + "ins", W + "del", W + "moveFrom", W + "moveTo") for n in xml.iter()):
                warnings.append(f"{part}: tracked changes present; extracted text is not an accepted/final view")
            if any(n.tag in (W + "fldChar", W + "instrText", W + "fldSimple") for n in xml.iter()):
                warnings.append(f"{part}: fields present; verify displayed values and citation fields in Word")
            if part == "document":
                groups = [("body", xml)]
            else:
                singular = part[:-1]
                groups = [(f"{singular}-id:{n.get(W + 'id')}", n)
                          for n in xml.findall(W + singular)
                          if n.get(W + "type", "normal") == "normal"]
            for prefix, group in groups:
                for number, para in enumerate(group.iter(W + "p"), 1):
                    text = xml_text(para)
                    if text.strip():
                        blocks.append({"id": f"{prefix}/p:{number}", "text": text})
        if any(n.startswith(("word/header", "word/footer", "word/comments")) for n in archive.namelist()):
            warnings.append("Headers, footers and comments are not inventoried; inspect separately if in scope")
    warnings.append("OOXML note IDs may differ from displayed numbers; reconcile with Word. Text boxes and complex layouts need visual review.")
    return {"blocks": blocks, "warnings": warnings}


def write_new_text(path, text):
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def extract_elitigation_page(html_file, out, notes_out=None, trailing_out=None):
    """Convert a saved eLitigation page to [n] paragraph text without overwriting files."""
    result = converters.extract_elitigation(Path(html_file).read_text(encoding="utf-8-sig"))
    out = Path(out)
    many = len(result["opinions"]) > 1
    targets = [out.with_name(f"{out.stem}-opinion-{i}{out.suffix}") if many else out
               for i in range(1, len(result["opinions"]) + 1)]
    notes_out = Path(notes_out) if notes_out else out.with_name(out.stem + "-notes" + out.suffix)
    trailing_out = Path(trailing_out) if trailing_out else out.with_name(out.stem + "-trailing" + out.suffix)
    outputs = targets + ([notes_out] if result["notes"] else []) + ([trailing_out] if result["trailing"] else [])
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise ValueError("opinion, notes and trailing output paths must be distinct")
    for path in outputs:
        if path.exists():
            raise FileExistsError(f"{path} already exists; choose new output paths")
    files = []
    for path, opinion in zip(targets, result["opinions"]):
        write_new_text(path, opinion["text"])
        files.append({"file": str(path), "author": opinion["author"], "first": opinion["first"],
                      "last": opinion["last"], "paragraphs": opinion["paragraphs"]})
    if result["notes"]:
        write_new_text(notes_out, "\n".join(result["notes"]) + "\n")
    if result["trailing"]:
        write_new_text(trailing_out, "\n\n".join(
            f"[{block['class']}: {block['reason']}]\n{block['text']}" for block in result["trailing"]) + "\n")
    return {"header": result["header"], "opinions": files,
            "notes_file": str(notes_out) if result["notes"] else None, "notes": len(result["notes"]),
            "trailing_file": str(trailing_out) if result["trailing"] else None,
            "trailing_blocks": result["trailing"],
            "report": result["report"], "transformation": converters.ELITIGATION_TRANSFORMATION,
            "next": "Review the warnings and header, then snapshot the saved page with --text set to "
                    "each opinion file and this transformation; separate opinions need separate source IDs."}


def extract_sso_page(html_file, out):
    """Convert a saved SSO provision view to text and report its version evidence."""
    result = converters.extract_sso(Path(html_file).read_text(encoding="utf-8-sig"))
    write_new_text(out, result["text"])
    return {"file": str(out), "title": result["title"], "status": result["status"],
            "provisions": result["provisions"], "act_amendments": result["act_amendments"],
            "warnings": result["warnings"], "transformation": converters.SSO_TRANSFORMATION,
            "next": "Use the status line as the snapshot --version and check act_amendments (Act-wide, not "
                    "provision-specific) in version_review; then snapshot the saved page with --text set to this file."}


def attach_draft(root, file):
    root = Path(root)
    data = load_run(root)
    if data.get("draft") or data.get("inventory"):
        raise ValueError("draft already attached; use a new run for a revised draft")
    extracted = extract_docx(file)
    if not extracted["blocks"]:
        raise ValueError("draft contains no extractable text")
    folder = root / "draft"
    folder.mkdir(exist_ok=False)
    target = folder / "snapshot.docx"
    shutil.copyfile(file, target)
    write_json(folder / "extraction.json", extracted, new=True)
    data["draft"] = {"file": "draft/snapshot.docx", "sha256": digest(target),
                     "extraction": "draft/extraction.json", "extraction_sha256": digest(folder / "extraction.json")}
    data["inventory"] = [dict(b, reviewed=False, claim_ids=[], reason="") for b in extracted["blocks"]]
    data["gaps"].extend(extracted["warnings"])
    write_json(root / "run.json", data)
    return extracted


def check_run(root):
    root = Path(root)
    data = load_run(root)
    errors, limits = [], []
    if data.get("schema_version") != 1:
        errors.append("unsupported schema_version")
    for field in ("question", "review"):
        if not nonempty(data.get(field)):
            errors.append(f"missing {field}")
    if data.get("mode") not in MODES:
        errors.append("invalid mode")
    for field in ("research_date", "law_as_at"):
        try:
            iso_date(data.get(field))
        except ValueError:
            errors.append(f"invalid {field}")
    for field in ("sources", "claims", "quotes", "inventory", "search_log", "gaps"):
        if not isinstance(data.get(field), list):
            errors.append(f"{field} must be an array")
    if errors:
        return result(data, errors, limits)

    def indexed(items, label):
        output = {}
        for item in items:
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                errors.append(f"{label}: every record needs an id")
            elif item["id"] in output:
                errors.append(f"{label}: duplicate id {item['id']}")
            else:
                output[item["id"]] = item
        return output

    sources = indexed(data["sources"], "sources")
    claims = indexed(data["claims"], "claims")
    searches = indexed(data["search_log"], "search_log")
    inventory = indexed(data["inventory"], "inventory")
    quotes = indexed(data["quotes"], "quotes")
    texts, paragraph_rows, provision_rows = {}, {}, {}

    def check_hash(record, path_key, hash_key, label):
        try:
            path = inside(root, record.get(path_key))
            if digest(path) != record.get(hash_key):
                raise ValueError("hash mismatch")
            return path
        except (OSError, ValueError) as exc:
            errors.append(f"{label}: {path_key}: {exc}")
            return None

    terms = []
    if data.get("matter_terms") is not None:
        try:
            terms = read_terms(data["matter_terms"])
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"matter terms unreadable, so search queries cannot be screened: {exc}")
    for key, search in searches.items():
        if not all(nonempty(search.get(f)) for f in ("database", "query", "coverage", "result_note")):
            errors.append(f"{key}: incomplete search record")
        for finding in screen_text(search.get("query", ""), terms):
            errors.append(f"{key}: query contains a {finding['category']}; search with legal concepts only")
        try:
            iso_date(search.get("searched_on"))
        except ValueError:
            errors.append(f"{key}: invalid searched_on")
    for key, source in sources.items():
        if not ID.fullmatch(key) or source.get("kind") not in KINDS:
            errors.append(f"{key}: invalid source id or kind")
        for f in ("title", "url", "citation", "version"):
            if not nonempty(source.get(f)):
                errors.append(f"{key}: missing {f}")
        for f in ("identity_verified", "full_text_reviewed"):
            if not isinstance(source.get(f), bool):
                errors.append(f"{key}: {f} must be boolean")
        check_hash(source, "file", "sha256", key)
        path = check_hash(source, "text_file", "text_sha256", key)
        if source.get("text_file") != source.get("file") and not nonempty(source.get("transformation")):
            errors.append(f"{key}: missing transformation description")
        if path:
            try:
                texts[key] = path.read_text(encoding="utf-8-sig")
            except (OSError, UnicodeError) as exc:
                errors.append(f"{key}: cannot read UTF-8 source text: {exc}")
        if source.get("identity_verified") is True or source.get("full_text_reviewed") is True:
            for f in ("publication_authority", "review_note"):
                if not nonempty(source.get(f)):
                    errors.append(f"{key}: reviewed source missing {f}")
            try:
                iso_date(source.get("retrieved_on"))
            except ValueError:
                errors.append(f"{key}: reviewed source needs retrieved_on")
        if not (source.get("identity_verified") is True and source.get("full_text_reviewed") is True):
            limits.append(f"{key}: source not reviewed")
        if source.get("paragraph_index") is not None and key in texts:
            try:
                paragraph_rows[key] = checked_paragraphs(source, texts[key])
            except ValueError as exc:
                errors.append(f"{key}: {exc}")
        if source.get("provision_index") is not None and key in texts:
            try:
                provision_rows[key] = checked_provisions(source, texts[key])
            except ValueError as exc:
                errors.append(f"{key}: {exc}")

    used = set()
    for key, claim in claims.items():
        assessment = claim.get("assessment")
        if assessment not in ASSESSMENTS or not all(nonempty(claim.get(f)) for f in ("text", "location", "reason")):
            errors.append(f"{key}: incomplete claim or invalid assessment")
        refs = claim.get("evidence")
        if not isinstance(refs, list):
            errors.append(f"{key}: evidence must be an array")
            continue
        if assessment in ("supported", "qualified") and not refs:
            errors.append(f"{key}: support requires evidence")
        if assessment in ("qualified", "unsupported", "unresolved"):
            limits.append(f"{key}: {assessment}: {claim.get('reason', '')}")
        for ref in refs:
            if not isinstance(ref, dict):
                errors.append(f"{key}: malformed evidence reference")
                continue
            sid = ref.get("source_id")
            if not isinstance(sid, str) or sid not in sources:
                errors.append(f"{key}: unknown source_id")
                continue
            used.add(sid)
            if not all(nonempty(ref.get(f)) for f in ("pinpoint", "support_note")) or ref.get("pinpoint_reviewed") is not True:
                errors.append(f"{key}: evidence needs pinpoint, support_note and pinpoint_reviewed=true")
            if assessment in ("supported", "qualified") and not (
                    sources[sid].get("identity_verified") is True and sources[sid].get("full_text_reviewed") is True):
                errors.append(f"{key}: support relies on unreviewed source {sid}")
            if sources[sid].get("kind") == "case":
                try:
                    if ref.get("locator_type", "paragraph") == "paragraph":
                        if sid not in paragraph_rows:
                            raise ValueError("case evidence needs a valid reviewed paragraph index")
                        expected = select_paragraphs(paragraph_rows[sid], ref.get("pinpoint"))
                        if ref.get("passages") != expected:
                            raise ValueError("case evidence must retain every full cited paragraph with its source offsets")
                        if has_subparagraph(ref.get("pinpoint")):
                            limits.append(f"{key}: {ref['pinpoint']} checked against the full paragraph; "
                                          "the sub-paragraph's own boundaries were reviewed manually")
                    elif ref.get("locator_type") == "page":
                        if sources[sid].get("paragraph_index") is not None or not nonempty(sources[sid].get("paragraphs_unavailable_reason")):
                            raise ValueError("page fallback needs an unnumbered source and paragraphs_unavailable_reason")
                        if not nonempty(ref.get("locator_note")) or not isinstance(ref.get("passages"), list) or not ref["passages"]:
                            raise ValueError("page fallback needs source passages and a locator_note")
                        for passage in ref["passages"]:
                            if not isinstance(passage, dict):
                                raise ValueError("malformed page passage")
                            a, b = passage.get("start"), passage.get("end")
                            if (sid not in texts or type(a) is not int or type(b) is not int
                                    or not 0 <= a < b <= len(texts[sid]) or not nonempty(passage.get("text"))
                                    or texts[sid][a:b] != passage["text"]):
                                raise ValueError("page passage does not match its source span")
                        limits.append(f"{key}: page locator reviewed manually: {ref['locator_note']}")
                    else:
                        raise ValueError("case locator_type must be paragraph or page")
                except ValueError as exc:
                    errors.append(f"{key}: {exc}")
            if sources[sid].get("kind") == "legislation":
                try:
                    receipt = verify_statute_receipt(data, sources[sid])
                    iso_date(receipt.get("law_as_at"))
                    if ref.get("locator_type") != "provision" or sid not in provision_rows:
                        raise ValueError("statutory evidence needs a reviewed provision index and locator_type=provision")
                    expected, context = select_provision(provision_rows[sid], ref.get("pinpoint"))
                    if ref.get("passages") != expected or ref.get("context") != context:
                        raise ValueError("statutory evidence must retain the exact cited provision and its complete parent context")
                    if ref.get("law_as_at") != receipt["law_as_at"]:
                        raise ValueError("statutory evidence date does not match the verified source version")
                    if ref["law_as_at"] != data["law_as_at"] and not nonempty(ref.get("date_basis")):
                        raise ValueError("explain the event date or historical comparison when using a different law-as-at date")
                    for p in expected:
                        if p["status"] != "in-force":
                            limits.append(f"{key}: {p['locator']} {p['status']}: {p['status_note']}")
                        if (p["status"] in ("repealed", "not-in-force") and assessment == "supported"
                                and not nonempty(ref.get("date_basis"))):
                            errors.append(f"{key}: {p['locator']} {p['status']} needs a qualified claim "
                                          "or evidence date_basis explaining historical or saved application")
                except ValueError as exc:
                    errors.append(f"{key}: {exc}")

        has_authority = any(isinstance(ref, dict) and isinstance(ref.get("source_id"), str)
                       and sources.get(ref["source_id"], {}).get("kind") in ("case", "legislation") for ref in refs)
        if "citation_check" in claim or (data["mode"] == "cite-check" and has_authority):
            cited = claim.get("citation_check")
            if not isinstance(cited, dict):
                errors.append(f"{key}: cite-check finding needs citation_check preserving the original citation")
                continue
            status = cited.get("result")
            sid, pin = cited.get("source_id"), cited.get("pinpoint")
            if status not in ("supported", "wrong-pinpoint", "wrong-instrument", "wrong-version", "unsupported", "missing-pinpoint", "unverifiable"):
                errors.append(f"{key}: invalid citation_check result")
            if not all(nonempty(cited.get(f)) for f in ("citation", "reason")) or not isinstance(pin, str):
                errors.append(f"{key}: citation_check needs original citation, pinpoint and reason")
                continue
            location = inventory.get(claim.get("location"), {}) if isinstance(claim.get("location"), str) else {}
            draft_text = location.get("text", "")
            if data["mode"] == "cite-check" and (not isinstance(draft_text, str) or normalise(cited["citation"]) not in normalise(draft_text)):
                errors.append(f"{key}: original citation is not present in the inventoried draft location")
            if status == "missing-pinpoint" and pin:
                errors.append(f"{key}: missing-pinpoint must preserve an empty original pinpoint")
            if status not in ("missing-pinpoint", "unverifiable"):
                if not isinstance(sid, str) or sources.get(sid, {}).get("kind") not in ("case", "legislation") or not nonempty(pin):
                    errors.append(f"{key}: checked citation needs its source and original pinpoint")
                    continue
                # Preserve literal locators from the draft; canonicalise only dash/space variants.
                squash = lambda s: re.sub(r"\s+", "", s).replace("–", "-").replace("—", "-")
                def same_locator(ref):
                    if not nonempty(ref.get("pinpoint")):
                        return False
                    if ref.get("locator_type", "paragraph") == "paragraph" and sid in paragraph_rows:
                        try:
                            # Same paragraphs; where a sub-paragraph is cited, the same labels too:
                            # [185(c)] is not [185(b)], but [35]–[36] is still [35], [36].
                            labels = lambda p: [(s1, s2) for _, s1, _, s2 in pinpoint_units(p)]
                            same_labels = (not (has_subparagraph(ref["pinpoint"]) or has_subparagraph(pin))
                                           or labels(ref["pinpoint"]) == labels(pin))
                            return (select_paragraphs(paragraph_rows[sid], ref["pinpoint"])
                                    == select_paragraphs(paragraph_rows[sid], pin) and same_labels)
                        except ValueError:
                            return False
                    if sources[sid].get("kind") == "legislation":
                        try:
                            resolved = cited.get("resolved_pinpoint", pin)
                            if resolved != pin and not nonempty(cited.get("pinpoint_resolution_note")):
                                return False
                            return canonical_provision(ref["pinpoint"]) == canonical_provision(resolved)
                        except ValueError:
                            return False
                    return squash(ref["pinpoint"]) == squash(pin)
                if squash(pin) not in squash(cited["citation"]):
                    errors.append(f"{key}: original pinpoint does not occur in the original citation")
                linked = [ref for ref in refs if isinstance(ref, dict) and ref.get("source_id") == sid
                          and same_locator(ref)]
                if not linked:
                    errors.append(f"{key}: original cited paragraph/provision must be checked separately from any correction")
                if status == "wrong-pinpoint" and not any(isinstance(ref, dict) and ref.get("source_id") == sid
                        and nonempty(ref.get("pinpoint")) and not same_locator(ref) for ref in refs):
                    errors.append(f"{key}: wrong-pinpoint needs separately captured proposed replacement paragraphs/provisions")
            is_statute = isinstance(sid, str) and sources.get(sid, {}).get("kind") == "legislation"
            if is_statute:
                for field, allowed in (("instrument_result", ("matched", "wrong-instrument", "ambiguous", "unverifiable")),
                                       ("version_result", ("matched", "wrong-version", "unverifiable"))):
                    if cited.get(field) not in allowed:
                        errors.append(f"{key}: statutory citation needs {field}")
                    elif cited[field] != "matched":
                        note = cited.get("instrument_note" if field == "instrument_result" else "version_note", "")
                        limits.append(f"{key}: {field} {cited[field]}: {note}")
                if not all(nonempty(cited.get(f)) for f in ("instrument_note", "version_note", "date_basis")):
                    errors.append(f"{key}: explain instrument identity, applicable date and version selection")
                if cited.get("resolved_instrument") != sources[sid].get("title"):
                    errors.append(f"{key}: citation identity does not resolve to the actual source instrument")
                try:
                    iso_date(cited.get("applicable_on"))
                except ValueError:
                    errors.append(f"{key}: statutory citation needs its applicable_on date")
                if status == "supported":
                    receipt = sources[sid].get("statute_verification", {})
                    if cited.get("instrument_result") != "matched" or cited.get("version_result") != "matched":
                        errors.append(f"{key}: wrong or unverified instrument/version cannot be marked supported")
                    if not isinstance(receipt, dict) or receipt.get("law_as_at") != cited.get("applicable_on"):
                        errors.append(f"{key}: supported citation must use the version verified for its applicable date")
                if status == "wrong-instrument" and cited.get("instrument_result") != "wrong-instrument":
                    errors.append(f"{key}: wrong-instrument result conflicts with the identity finding")
                if status == "wrong-version" and cited.get("version_result") != "wrong-version":
                    errors.append(f"{key}: wrong-version result conflicts with the version finding")
            if status != "supported":
                limits.append(f"{key}: citation {status}: {cited['reason']}")
                if assessment == "supported":
                    errors.append(f"{key}: a defective or unverified citation cannot be marked supported")
            elif assessment not in ("supported", "qualified"):
                errors.append(f"{key}: supported citation conflicts with claim assessment")

    for sid in used:
        source = sources[sid]
        if source.get("kind") == "legislation" and not nonempty(source.get("version_review")):
            errors.append(f"{sid}: legislation needs provision-specific version_review")
        if source.get("kind") == "case":
            treatment = source.get("treatment", {})
            if not isinstance(treatment, dict) or treatment.get("status") not in (
                    "not-checked", "public-search-limited", "citator-checked", "adverse-treatment-found"):
                errors.append(f"{sid}: invalid treatment record")
                continue
            if not nonempty(treatment.get("note")):
                errors.append(f"{sid}: case needs a treatment note")
            ids = treatment.get("search_ids")
            if not isinstance(ids, list) or any(not isinstance(i, str) or i not in searches for i in ids):
                errors.append(f"{sid}: invalid treatment search_ids")
            elif treatment["status"] != "not-checked" and not ids:
                errors.append(f"{sid}: treatment check needs search records")
            if treatment["status"] != "citator-checked":
                limits.append(f"{sid}: treatment {treatment['status']}: {treatment.get('note', '')}")

    for key, quote in quotes.items():
        sid, cid = quote.get("source_id"), quote.get("claim_id")
        if not isinstance(sid, str) or sid not in texts or not isinstance(cid, str) or cid not in claims:
            errors.append(f"{key}: unknown quote source or claim")
            continue
        refs = claims[cid].get("evidence", [])
        if not isinstance(refs, list) or not any(isinstance(r, dict) and r.get("source_id") == sid and r.get("pinpoint") == quote.get("pinpoint") for r in refs):
            errors.append(f"{key}: quote source and pinpoint must be linked to its claim")
        start, end = quote.get("start"), quote.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(texts[sid]):
            errors.append(f"{key}: invalid character span")
        elif not nonempty(quote.get("text")) or normalise(texts[sid][start:end]) != normalise(quote["text"]):
            errors.append(f"{key}: quotation does not match the recorded source span")
        if quote.get("pinpoint_reviewed") is not True or not nonempty(quote.get("pinpoint")):
            errors.append(f"{key}: quote pinpoint not reviewed")
        if not (sources[sid].get("identity_verified") is True and sources[sid].get("full_text_reviewed") is True):
            errors.append(f"{key}: quotation source is unreviewed")
        if sources[sid].get("kind") in ("case", "legislation") and type(start) is int and type(end) is int:
            matching = [ref for ref in refs if isinstance(ref, dict) and ref.get("source_id") == sid
                        and ref.get("pinpoint") == quote.get("pinpoint")]
            spans = [p for ref in matching if isinstance(ref.get("passages"), list) for p in ref["passages"] if isinstance(p, dict)
                     and type(p.get("start")) is int and type(p.get("end")) is int]
            covered = any(p["start"] <= start < p["end"] for p in spans) and any(p["start"] < end <= p["end"] for p in spans)
            skipped = any(p["start"] < end and start < p["end"] and p not in spans for p in paragraph_rows.get(sid, []))
            if not covered or skipped:
                errors.append(f"{key}: quotation lies outside the full paragraphs/passages cited")

    draft = data.get("draft")
    if data["mode"] == "cite-check" and not draft and not inventory:
        errors.append("cite-check needs a draft inventory")
    if draft is not None:
        if not isinstance(draft, dict):
            errors.append("draft must be an object or null")
        else:
            path = check_hash(draft, "file", "sha256", "draft")
            extraction_path = check_hash(draft, "extraction", "extraction_sha256", "draft")
            if path and extraction_path:
                try:
                    original = extract_docx(path)
                    saved = read_json(extraction_path)
                    if saved != original:
                        errors.append("draft extraction differs from the snapshot")
                    expected = {b["id"]: b["text"] for b in original["blocks"]}
                    actual = {k: v.get("text") for k, v in inventory.items()}
                    if expected != actual:
                        errors.append("inventory does not cover the exact draft blocks")
                except (OSError, ValueError, ET.ParseError, zipfile.BadZipFile) as exc:
                    errors.append(f"draft extraction cannot be verified: {exc}")
    for key, item in inventory.items():
        ids = item.get("claim_ids")
        if not nonempty(item.get("text")):
            errors.append(f"{key}: inventory needs the exact draft text")
        if item.get("reviewed") is not True:
            errors.append(f"{key}: inventory location not reviewed")
        if not isinstance(ids, list) or any(not isinstance(i, str) or i not in claims for i in ids):
            errors.append(f"{key}: invalid claim_ids")
        elif not ids and not nonempty(item.get("reason")):
            errors.append(f"{key}: explain why there are no research items")
        elif ids:
            for cid in ids:
                if claims[cid].get("location") != key:
                    errors.append(f"{key}: claim {cid} must identify this inventory location")
    if data["mode"] == "cite-check":
        linked = {cid for item in inventory.values() for cid in item.get("claim_ids", [])
                  if isinstance(cid, str)} if all(isinstance(i.get("claim_ids"), list) for i in inventory.values()) else set()
        for cid in claims:
            if cid not in linked:
                errors.append(f"{cid}: cite-check finding is not linked to the draft inventory")
    if not claims and data["mode"] not in ("library", "proofread", "cite-check"):
        errors.append("research run has no claims")
    if data["mode"] == "library" and not sources:
        errors.append("library run has no sources")
    for gap in data["gaps"]:
        if not nonempty(gap):
            errors.append("gaps must contain non-empty descriptions")
        else:
            limits.append(gap)
    return result(data, errors, limits)


def result(data, errors, limits):
    return {"status": "fail" if errors else ("pass-with-limits" if limits else "pass-record-checks"),
            "errors": errors, "limits": limits,
            "counts": {k: len(data[k]) for k in ("sources", "claims", "quotes", "inventory", "search_log")
                       if isinstance(data.get(k), list)},
            "meaning": "Record integrity and declared review only; not legal correctness, authenticity, completeness, or current-law certification."}


def export_library(root, output):
    report = check_run(root)
    if report["errors"]:
        raise ValueError("run record checks failed; run check for details")
    data, records, seen = load_run(root), [], set()
    for source in data["sources"]:
        if "csl" not in source:
            continue
        if source.get("identity_verified") is not True or source.get("full_text_reviewed") is not True:
            raise ValueError(f"{source['id']}: cannot export an unreviewed record")
        record = source["csl"]
        if not isinstance(record, dict) or not all(nonempty(record.get(f)) for f in ("type", "title")):
            raise ValueError("CSL record needs a verified type and title")
        if record["type"] not in ("legal_case", "legislation", "article-journal", "book", "report", "webpage", "speech", "chapter"):
            raise ValueError("unsupported CSL type; extend deliberately if needed")
        key = (normalise(source["citation"]).casefold(), normalise(source["version"]).casefold())
        if key in seen:
            raise ValueError("duplicate legal identifier and version in library export")
        seen.add(key)
        record = dict(record, id=source["id"], URL=source["url"])
        records.append(record)
    if not records:
        raise ValueError("no reviewed sources with CSL metadata to export")
    write_json(output, records, new=True)
    return {"exported": len(records), "path": str(output), "limits": report["limits"]}


def main(argv=None):
    # Source text is not limited to the console code page (e.g. U+2011 in SSO text);
    # piped Windows output would otherwise crash or emit non-UTF-8 JSON.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="create a new private research ledger")
    init.add_argument("run", type=Path)
    init.add_argument("--question", required=True)
    init.add_argument("--mode", choices=MODES, default="research")
    init.add_argument("--research-date", type=iso_date, required=True)
    init.add_argument("--law-as-at", type=iso_date, required=True)
    init.add_argument("--matter-terms", type=Path, help="private file of names and terms that must never appear in a search query")
    scr = sub.add_parser("screen", help="check text for identifiers and matter terms before it leaves this machine")
    scr.add_argument("text")
    scr.add_argument("--terms", type=Path)
    scr.add_argument("--run", type=Path, help="use the matter terms recorded in this ledger")
    snap = sub.add_parser("snapshot", help="copy a retrieved source and record its hashes")
    snap.add_argument("run", type=Path)
    snap.add_argument("file", type=Path)
    for arg in ("id", "title", "url", "citation", "version"):
        snap.add_argument("--" + arg, required=True)
    snap.add_argument("--kind", choices=KINDS, required=True)
    snap.add_argument("--text", type=Path)
    snap.add_argument("--transformation", default="")
    index = sub.add_parser("index-paragraphs", help="index explicit judgment paragraph labels after boundary review")
    index.add_argument("run", type=Path)
    index.add_argument("--source", required=True)
    index.add_argument("--style", choices=("bracketed", "numbered"), required=True)
    index.add_argument("--confirm-boundaries", action="store_true", required=True)
    index.add_argument("--review-note", required=True)
    passages = sub.add_parser("passages", help="pull full paragraphs for an exact pinpoint or range")
    passages.add_argument("run", type=Path)
    passages.add_argument("--source", required=True)
    passages.add_argument("--pinpoint", required=True)
    statute_index = sub.add_parser("index-provisions", help="bind reviewed statutory locators to source spans and a fresh verification receipt")
    statute_index.add_argument("run", type=Path)
    statute_index.add_argument("--source", required=True)
    statute_index.add_argument("--map", type=Path, required=True)
    statute_index.add_argument("--confirm-boundaries", action="store_true", required=True)
    statute_index.add_argument("--review-note", required=True)
    provision = sub.add_parser("provision", help="capture the exact statutory provision and its parent context")
    provision.add_argument("run", type=Path)
    provision.add_argument("--source", required=True)
    provision.add_argument("--locator", required=True)
    quote = sub.add_parser("quote", help="find quoted words inside the cited passage and print a quote record")
    quote.add_argument("run", type=Path)
    quote.add_argument("--source", required=True)
    quote.add_argument("--pinpoint", required=True)
    quote.add_argument("--text", required=True)
    quote.add_argument("--occurrence", type=int)
    quote.add_argument("--id", default="")
    quote.add_argument("--claim", default="")
    elit = sub.add_parser("extract-elitigation", help="convert a saved eLitigation judgment page to [n] paragraph text")
    elit.add_argument("html", type=Path)
    elit.add_argument("--out", type=Path, required=True)
    elit.add_argument("--notes", type=Path)
    elit.add_argument("--trailing", type=Path)
    sso = sub.add_parser("extract-sso", help="convert a saved SSO provision view to text and report its version status")
    sso.add_argument("html", type=Path)
    sso.add_argument("--out", type=Path, required=True)
    docx = sub.add_parser("extract-docx", help="snapshot a Word draft and inventory text")
    docx.add_argument("run", type=Path)
    docx.add_argument("file", type=Path)
    check = sub.add_parser("check", help="check records, snapshots, coverage and quotation spans")
    check.add_argument("run", type=Path)
    export = sub.add_parser("export-library", help="write reviewed source records to CSL-JSON")
    export.add_argument("run", type=Path)
    export.add_argument("output", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            init_run(args.run, args.question, args.mode, args.research_date, args.law_as_at, args.matter_terms)
            output = {"created": str(args.run / "run.json")}
        elif args.command == "screen":
            terms = args.terms or (load_run(args.run).get("matter_terms") if args.run else None)
            output = screen(args.text, terms)
        elif args.command == "snapshot":
            output = snapshot(args.run, args.file, args.id, args.title, args.kind, args.url,
                              args.citation, args.version, args.text, args.transformation)
        elif args.command == "quote":
            output = locate_quote(args.run, args.source, args.pinpoint, args.text, args.occurrence, args.id, args.claim)
        elif args.command == "extract-elitigation":
            output = extract_elitigation_page(args.html, args.out, args.notes, args.trailing)
        elif args.command == "extract-sso":
            output = extract_sso_page(args.html, args.out)
        elif args.command == "extract-docx":
            output = attach_draft(args.run, args.file)
        elif args.command == "index-paragraphs":
            output = index_paragraphs(args.run, args.source, args.style, args.review_note)
        elif args.command == "passages":
            output = capture_passages(args.run, args.source, args.pinpoint)
        elif args.command == "index-provisions":
            output = index_provisions(args.run, args.source, read_json(args.map), args.review_note)
        elif args.command == "provision":
            output = capture_provision(args.run, args.source, args.locator)
        elif args.command == "check":
            output = check_run(args.run)
        else:
            output = export_library(args.run, args.output)
        print(json.dumps(output, indent=2, ensure_ascii=False))
        return 1 if output.get("status") == "fail" else 0
    except (OSError, ValueError, KeyError, TypeError, ET.ParseError, zipfile.BadZipFile) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
