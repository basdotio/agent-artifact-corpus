"""Offline converters from saved court and legislation pages to evidence text.

They read a page already saved by a browser or other permitted retrieval; they never
fetch anything. Output is structural text for `snapshot --text`; the conversion is a
transformation that still needs review against the original page.
"""

import html as html_module
from collections import Counter
from html.parser import HTMLParser
import re
from statistics import median

ELITIGATION_TRANSFORMATION = (
    "extract-elitigation: numbered Judg-1 paragraphs as [n]; unnumbered paragraphs, "
    "sub-paragraphs, Judg-List levels and quotations kept as continuation lines of the preceding paragraph; "
    "opinion boundaries tracked; separate sections and trailing blocks saved separately; "
    "headings and author lines omitted from paragraph text; footnote pop-ups moved to a "
    "separate notes file with inline [note: N] markers; whitespace normalised within blocks.")

SSO_TRANSFORMATION = (
    "extract-sso: text of the page's provision container (id=legisContent) only, with tags as "
    "line breaks, split labels such as '(a)' and '146.—(1)' rejoined, and navigation, version "
    "list and footer removed; whitespace normalised within lines.")

NUMBERED = re.compile(r"\s*(\d+)[  \t]+(.*)", re.S)


def clean(text):
    return " ".join(text.replace(" ", " ").split())


class _Judgment(HTMLParser):
    """Collect top-level Judg-* blocks; route footnote modal content to notes."""

    HEADER_BREAKS = frozenset(("div", "br", "p", "table", "tr", "td", "th", "li"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks, self.notes, self.header = [], [], []
        self.cls, self.depth, self.buf = None, 0, []
        self.skip, self.sup, self.note, self.in_header = 0, False, None, 0
        self.references, self.sup_buf = [], []
        self.sup_button, self.sup_target = False, None
        self.note_depth, self.modal_id, self.modal_header = 0, None, []

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class") or ""
        if self.skip:
            if self.note_depth and tag in self.HEADER_BREAKS:
                self.note.append(" ")
            if tag == "div":
                self.skip += 1
                if cls.startswith("FootnoteRef"):
                    if self.note is None:
                        self.note = []
                    else:
                        self.note.append(" ")
                    self.note_depth = self.skip
            return
        if self.cls and tag in self.HEADER_BREAKS and not (tag == "div" and cls.startswith("modal")):
            self.buf.append("\n")
        if self.in_header:
            self.in_header += tag == "div"
        elif tag == "div" and cls.startswith("HN-CaseName"):
            self.in_header = 1
        if self.in_header and tag in self.HEADER_BREAKS:
            self.header.append(" ")
        if tag == "div" and cls.startswith("modal"):
            self.skip, self.note = 1, None
            self.note_depth, self.modal_id, self.modal_header = 0, dict(attrs).get("id"), []
        elif tag == "sup" and self.cls:
            self.sup = True
            self.sup_buf, self.sup_button, self.sup_target = [], False, None
        elif tag == "button" and self.sup:
            self.sup_button = True
            self.sup_target = (dict(attrs).get("data-target") or "").removeprefix("#") or None
        elif tag == "div":
            if self.cls is None and cls.startswith("Judg-"):
                self.cls, self.depth, self.buf = cls.split()[0], 1, []
            elif self.cls is not None:
                self.depth += 1

    def handle_endtag(self, tag):
        if self.skip:
            if self.note_depth and tag in self.HEADER_BREAKS:
                self.note.append(" ")
            if tag == "div":
                if self.skip == self.note_depth:
                    self.note_depth = 0
                self.skip -= 1
                if self.skip == 0 and self.note is not None:
                    label = re.search(r"\bFoot\s*Note\s*:?\s*(\d+)\b", "".join(self.modal_header), re.I)
                    self.notes.append({"number": label[1] if label else None, "target": self.modal_id,
                                       "text": clean("".join(self.note))})
                    self.note = None
            return
        if self.cls and tag in self.HEADER_BREAKS:
            self.buf.append("\n")
        if self.in_header:
            if tag in self.HEADER_BREAKS:
                self.header.append(" ")
            if tag == "div":
                self.in_header -= 1
        if tag == "sup":
            if self.sup:
                number = clean("".join(self.sup_buf))
                if self.sup_button and re.fullmatch(r"\d+", number):
                    self.references.append({"number": number, "target": self.sup_target})
                    self.buf.append(f"[note: {number}]")
                else:
                    self.buf.extend(self.sup_buf)
            self.sup = False
        elif tag == "div" and self.cls is not None:
            self.depth -= 1
            if self.depth == 0:
                self.blocks.append((self.cls, "".join(self.buf)))
                self.cls = None

    def handle_data(self, data):
        if self.skip:
            if self.note is not None and self.note_depth:
                self.note.append(data)
            elif self.note is None:
                self.modal_header.append(data)
            return
        if self.in_header:
            self.header.append(data)
        if self.cls and self.sup:
            self.sup_buf.append(data)
        elif self.cls:
            self.buf.append(data)


def _judgment_notes(parser):
    """Resolve note labels from source titles/targets; never invent collection-order ids."""
    notes, warnings, mismatched = [], [], []
    for note in parser.notes:
        labels = {ref["number"] for ref in parser.references
                  if note["target"] and ref["target"] == note["target"]}
        number = note["number"]
        if number is None and len(labels) == 1:
            number = next(iter(labels))
        if labels and (len(labels) != 1 or (number is not None and labels != {number})):
            mismatched.append({"target": note["target"], "definition": number, "references": sorted(labels)})
        notes.append(dict(note, number=number))
    references = Counter(ref["number"] for ref in parser.references)
    definitions = Counter(note["number"] for note in notes if note["number"] is not None)
    missing = sorted(set(references) - set(definitions))
    duplicates = sorted(n for n, count in definitions.items() if count > 1)
    unreferenced = sorted(set(definitions) - set(references))
    unlabelled = sum(note["number"] is None for note in notes)
    targets = {note["target"] for note in notes if note["target"]}
    missing_targets = sorted({ref["target"] for ref in parser.references if ref["target"] and ref["target"] not in targets})
    for label, items in (("missing definitions", missing), ("duplicate definitions", duplicates),
                         ("unreferenced definitions", unreferenced), ("missing popup targets", missing_targets)):
        if items:
            warnings.append(f"footnotes: {label}: {', '.join(items)}")
    if unlabelled:
        warnings.append(f"footnotes: {unlabelled} unlabelled definitions retained without invented numbers")
    if mismatched:
        warnings.append("footnotes: conflicting marker and definition identifiers; inspect note_reconciliation")
    reconciliation = {"reference_counts": dict(references), "definition_counts": dict(definitions),
                      "missing": missing, "duplicates": duplicates, "unreferenced": unreferenced,
                      "unlabelled": unlabelled, "mismatched": mismatched, "missing_targets": missing_targets}
    return [f"[note: {n['number'] if n['number'] is not None else 'unlabelled'}] {n['text']}" for n in notes], reconciliation, warnings


def extract_elitigation(html):
    """Return opinions (each with [n] paragraph text), separated notes and a reconciliation report."""
    parser = _Judgment()
    parser.feed(html)
    opinions, current, trailing = [], None, []
    closed = None
    report = {"html_numbered_blocks": 0, "spacer_blocks": 0, "continuation_blocks": 0,
              "excluded_blocks": 0, "block_counts": {}, "source_block_classes": {},
              "paragraph_sizes": [], "warnings": []}

    def count(kind):
        counts = report["block_counts"]
        counts[kind] = counts.get(kind, 0) + 1

    def retain(cls, text, reason):
        trailing.append({"class": cls, "text": text, "reason": reason})

    def start_opinion(author):
        nonlocal current, closed
        closed = None
        current = {"author": author, "lines": [], "numbers": [], "sizes": []}
        opinions.append(current)

    for block_index, (cls, raw) in enumerate(parser.blocks):
        classes = report["source_block_classes"]
        classes[cls] = classes.get(cls, 0) + 1
        text = clean(raw)
        match = NUMBERED.match(raw) if cls == "Judg-1" else None
        if match:
            report["html_numbered_blocks"] += 1
        if cls == "Judg-Author":
            count("author")
            if current is None or current["numbers"] or closed:
                start_opinion(text)
            else:
                current["author"] = text
            continue
        section_heading = cls.startswith("Judg-Heading") and re.match(
            r"^(?:annex(?:es|ures?)?|appendix|appendices|schedules?|attachments?)\b", text, re.I)
        # A plural overview heading can introduce the next ordinary body paragraph
        # (e.g. a paragraph describing the annexes), rather than start an annex.
        overview = False
        if section_heading and not closed and current and current["numbers"] and re.fullmatch(
                r"annexes|annexures|appendices|schedules|attachments", text, re.I):
            following = next(((c, t) for c, t in parser.blocks[block_index + 1:] if clean(t)), None)
            next_number = NUMBERED.match(following[1]) if following and following[0] == "Judg-1" else None
            overview = bool(next_number and int(next_number[1]) == current["numbers"][-1] + 1)
        if section_heading and not overview:
            closed = "separate section heading"
            count("section_boundary")
            retain(cls, text, closed)
            report["warnings"].append(f"separate section retained outside opinion text: {text}")
            continue
        if cls.startswith(("Judg-Sign", "Judg-Lawyers", "Judg-EOF")):
            closed = "opinion ended at signature, counsel or end marker"
            count("opinion_end")
            report["excluded_blocks"] += 1
            if text:
                retain(cls, text, closed)
            continue
        if closed:
            count("trailing")
            if text:
                retain(cls, text, closed)
            if match:
                report["warnings"].append("numbered block after an opinion end retained as trailing material; "
                                          "a new author line is needed to start another opinion")
            continue
        if cls.startswith("Judg-Heading"):
            count("heading")
            report["excluded_blocks"] += 1
            continue
        # Do not turn a detached paragraph label into continuation prose. In
        # particular, a final label has no later numbering gap to expose it.
        # Preserve <br> boundaries until this check, before whitespace cleanup.
        if cls == "Judg-1" and re.search(
                r"^\s*(?:\[[1-9]\d*\]|[1-9]\d*)[\t \u00a0\u2000-\u200a]*\r?$", raw, re.M):
            raise ValueError("paragraph label on its own line in Judg-1; compare the saved HTML "
                             "and use an extraction that preserves the label with its paragraph text")
        # An unsupported labelled section must not masquerade as unnumbered prose.
        if current and current["numbers"] and re.match(r"^\[?[A-Z]\.[1-9]\d*\]?\s", text):
            closed = "unsupported section numbering"
            count("section_boundary")
            retain(cls, text, closed)
            report["warnings"].append("unsupported section numbering retained outside opinion text: " + text[:80])
            continue
        if match:
            count("numbered")
            number = int(match[1])
            if current is None:
                start_opinion("")
            elif current["numbers"] and number == 1:
                start_opinion("")
                report["warnings"].append("paragraph numbering restarted without an author line; "
                                          "treated as a separate opinion")
            elif current["numbers"] and number != current["numbers"][-1] + 1:
                report["warnings"].append(f"numbering gap: [{current['numbers'][-1]}] then [{number}]")
            current["numbers"].append(number)
            content = clean(match[2])
            current["lines"].append(f"[{number}] {content}")
            current["sizes"].append(len(content))
            continue
        if current is None or not current["numbers"]:
            count("front_matter")
            continue
        is_list = bool(re.fullmatch(r"Judg-List-[1-9]\d*", cls))
        if cls.startswith("Judg-Quote") or is_list or cls in ("Judg-1", "Judg-2", "Judg-3", "Judg-4"):
            if text:
                count("continuation")
                current["lines"].append(("    " if cls.startswith("Judg-Quote") else "") + text)
                current["sizes"][-1] += 1 + len(text)
                report["continuation_blocks"] += 1
            else:
                count("spacer")
                report["spacer_blocks"] += 1
        else:
            count("unrecognised")
            retain(cls, text, "unrecognised block type")
            report["warnings"].append(f"unrecognised block retained outside opinion text: {cls}")
    opinions = [o for o in opinions if o["numbers"]]
    if not opinions:
        raise ValueError("no numbered judgment paragraphs found; check that this is a saved eLitigation judgment page")
    extracted = sum(len(o["numbers"]) for o in opinions)
    if extracted != report["html_numbered_blocks"]:
        report["warnings"].append("extracted paragraph count differs from numbered blocks in the page; "
                                  "review separate/trailing sections")
    for opinion in opinions:
        numbers, sizes = opinion["numbers"], opinion["sizes"]
        if numbers != list(range(numbers[0], numbers[0] + len(numbers))):
            report["warnings"].append(f"opinion '{opinion['author']}' numbering is not consecutive")
        baseline = median(sizes[:-1]) if len(sizes) > 1 else None
        report["paragraph_sizes"].append({"author": opinion["author"], "last_paragraph": numbers[-1],
                                          "last_characters": sizes[-1], "preceding_median": baseline})
        if (baseline is not None and sizes[-1] > max(2000, baseline * 10)) or sizes[-1] > 50000:
            report["warnings"].append(f"unusually large final paragraph [{numbers[-1]}]; "
                                      "inspect source boundaries (size is a diagnostic, not a boundary rule)")
    notes, reconciliation, note_warnings = _judgment_notes(parser)
    report["warnings"].extend(note_warnings)
    report["note_reconciliation"] = reconciliation
    return {"header": clean("".join(parser.header)),
            "opinions": [{"author": o["author"], "first": o["numbers"][0], "last": o["numbers"][-1],
                          "paragraphs": len(o["numbers"]), "text": "\n".join(o["lines"]) + "\n"} for o in opinions],
            "notes": notes,
            "trailing": trailing,
            "report": dict(report, extracted_paragraphs=extracted)}


def _flat(fragment):
    return html_module.unescape(re.sub(r"<[^>]+>", " ", fragment))


class _SsoContent(HTMLParser):
    """Capture one complete legisContent subtree, not the page tail after it."""

    VOID = frozenset(("area", "base", "br", "col", "embed", "hr", "img", "input",
                      "link", "meta", "param", "source", "track", "wbr"))

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.found, self.stack, self.parts = False, [], []

    def handle_starttag(self, tag, attrs):
        if dict(attrs).get("id") == "legisContent":
            if self.found:
                raise ValueError("multiple SSO provision containers found; save one unambiguous provision view")
            if tag in self.VOID:
                raise ValueError("SSO provision container cannot be a void element")
            self.found = True
            self.stack.append(tag)
            return
        if self.stack:
            self.parts.append("\n")
            if tag not in self.VOID:
                self.stack.append(tag)

    def handle_endtag(self, tag):
        if self.stack and tag not in self.VOID:
            if tag != self.stack[-1]:
                raise ValueError("unbalanced SSO provision container; save a complete browser-rendered page")
            self.stack.pop()
            self.parts.append("\n")

    def handle_data(self, data):
        if self.stack and not any(tag in ("script", "style") for tag in self.stack):
            self.parts.append(data)

    def content(self):
        if not self.found:
            raise ValueError("no SSO provision content found (id=legisContent); save the provision view of the page")
        if self.stack:
            raise ValueError("unclosed SSO provision container; save the complete page instead of a truncated fragment")
        return "".join(self.parts)


def extract_sso(page):
    """Return SSO provision text plus the page's title, version status and Act amendment list."""
    parser = _SsoContent()
    parser.feed(page)
    parser.close()
    text = parser.content()
    lines = [" ".join(line.split()) for line in text.splitlines()]
    text = "\n".join(line for line in lines if line)
    text = re.sub(r"\(\n(\w+)\n\)", r"(\1)", text)          # "(\na\n)" -> "(a)"
    text = re.sub(r"^(\d+[A-Z]*\.)\n(—)", r"\1\2", text, flags=re.M)  # "146.\n—(1)" -> "146.—(1)"
    text = re.sub(r"\n([),;.])", r"\1", text)               # stray punctuation lines
    text = text.strip() + "\n"
    flat = " ".join(_flat(page).split())
    title = re.search(r"<title>\s*(.*?)\s*(?:-\s*Singapore Statutes Online)?\s*</title>", page, re.S)
    status = re.search(r"Status:\s*(.+?)\s+Print\b", flat)
    sections = re.findall(r"^(\d+[A-Z]*)\.(?:—|\s)", text, re.M)
    warnings = []
    if not status:
        warnings.append("no version status line found; record the version from the page manually")
    if not sections:
        warnings.append("no numbered provision found in the content; check the saved view")
    return {"title": " ".join(title[1].split()) if title else "",
            "status": status[1] if status else "",
            "act_amendments": [{"date": d, "by": act} for d, act in
                               re.findall(r"(\d{2} \w{3} \d{4}) Amended by (Act \d+ of \d{4})", flat)],
            "provisions": sections, "text": text, "warnings": warnings}
