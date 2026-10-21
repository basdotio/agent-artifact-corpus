"""Source-span indexes for legislation. Boundaries and legal effect require review."""

import re
from datetime import date


def provision_locator(value):
    """Return a canonical locator, immediate parent and source-label pattern."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("a specific statutory provision is required")
    value = re.sub(r"\s+", " ", value.strip())
    tail = r"((?:\([A-Za-z0-9]+\))*)"
    number = r"([1-9]\d*[A-Za-z]*)"
    schedule = re.fullmatch(r"((?:[A-Za-z]+ |[1-9]\d* )?Schedule)(?:,? (?:para|paragraph)\.?\s*" + number + tail + r")?", value, re.I)
    order = re.fullmatch(r"(?:O\.?|Order)\s*" + number + r"(?:\s+r(?:ule)?\.?\s*" + number + tail + r")?", value, re.I)
    unit = re.fullmatch(r"(s(?:ection)?|reg(?:ulation)?|r(?:ule)?|art(?:icle)?|para(?:graph)?)\.?\s*" + number + tail, value, re.I)
    if schedule:
        base = schedule[1].title()
        if schedule[2] is None:
            return base, None, re.escape(base).replace(r"\ ", r"\s+") + r"\b"
        root, suffix, parent, label = base + " para " + schedule[2].upper(), schedule[3], base, schedule[2].upper()
    elif order:
        base = "O " + order[1].upper()
        if order[2] is None:
            return base, None, r"(?:ORDER|O\.?)\s*" + re.escape(order[1]) + r"\b"
        root, suffix, parent, label = base + " r " + order[2].upper(), order[3], base, order[2].upper()
    elif unit:
        aliases = {"section": "s", "regulation": "reg", "rule": "r", "article": "art", "paragraph": "para"}
        kind = aliases.get(unit[1].lower(), unit[1].lower())
        root, suffix, parent, label = kind + " " + unit[2].upper(), unit[3], None, unit[2].upper()
    else:
        raise ValueError("unsupported provision locator; use e.g. s 9A(2)(b), reg 4(1), O 9 r 1(2), or First Schedule para 2")
    if suffix:
        tokens = re.findall(r"\(([A-Za-z0-9]+)\)", suffix)
        parent = root + "".join("(" + t + ")" for t in tokens[:-1])
        label_pattern = re.escape("(" + tokens[-1] + ")")
    else:
        # A top-level numbered unit must carry its source number and delimiter.
        label_pattern = re.escape(label) + r"(?:\.|[—–])"
    return root + suffix, parent, label_pattern


def canonical_provision(value):
    return provision_locator(value)[0]


ROMAN = {"i": 1, "v": 5, "x": 10, "l": 50, "c": 100}


def roman_value(token):
    lowered = token.lower()
    if not re.fullmatch(r"[ivxlc]+", lowered):
        return None
    total = 0
    for i, ch in enumerate(lowered):
        value = ROMAN[ch]
        total += -value if i + 1 < len(lowered) and ROMAN[lowered[i + 1]] > value else value
    return total


def to_roman(value, upper):
    out = ""
    for amount, numeral in ((100, "c"), (90, "xc"), (50, "l"), (40, "xl"), (10, "x"),
                            (9, "ix"), (5, "v"), (4, "iv"), (1, "i")):
        while value >= amount:
            out, value = out + numeral, value - amount
    return out.upper() if upper else out


def next_labels(token):
    """Labels that may follow `token` in the same series: the next unit or an inserted one."""
    found = set()
    numeric = re.fullmatch(r"([1-9]\d*)([A-Z]*)", token)
    if numeric:
        number, suffix = numeric[1], numeric[2]
        found.add(str(int(number) + 1))
        found.add(number + (suffix[:-1] + chr(ord(suffix[-1]) + 1) if suffix and suffix[-1] != "Z" else suffix + "A"))
        return found
    if re.fullmatch(r"[a-z]+|[A-Z]+", token):
        # (b) -> (c), or an inserted (ba); (ba) -> (bb) or (c).
        first, last = token[0], token[-1]
        if first not in "zZ":
            found.add(chr(ord(first) + 1))
        found.add(token + ("a" if token.islower() else "A"))
        if len(token) > 1 and last not in "zZ":
            found.add(token[:-1] + chr(ord(last) + 1))
        value = roman_value(token)
        if value:
            found.add(to_roman(value + 1, token.isupper()))
    return found


def label_token(locator):
    tokens = re.findall(r"\(([A-Za-z0-9]+)\)", locator)
    return tokens[-1] if tokens else None


def build_provisions(text, manifest):
    """Bind reviewed hierarchical locators to original text, preserving whole units."""
    if not isinstance(manifest, dict) or not isinstance(manifest.get("provisions"), list) or not manifest["provisions"]:
        raise ValueError("provision map needs a non-empty provisions array")
    rows, by_locator = [], {}
    for item in manifest["provisions"]:
        if not isinstance(item, dict):
            raise ValueError("malformed provision map entry")
        locator, parent, label = provision_locator(item.get("locator"))
        if locator in by_locator:
            raise ValueError("duplicate provision locator in source map")
        start, end = item.get("start"), item.get("end")
        if type(start) is not int or type(end) is not int or not 0 <= start < end <= len(text):
            raise ValueError("invalid provision source span")
        passage = text[start:end]
        label_match = re.match(label, passage, re.I)
        if not label_match:
            raise ValueError(f"{locator}: source span does not begin with the correct provision label")
        if not re.search(r"[^\s.—–:\-]", passage[label_match.end():]):
            raise ValueError(f"{locator}: source span contains only a label, not the provision text")
        if item.get("status") not in ("in-force", "partly-in-force", "not-in-force", "repealed", "uncertain") or not isinstance(item.get("status_note"), str) or not item["status_note"].strip():
            raise ValueError(f"{locator}: record provision-specific operative status and status_note")
        row = {"locator": locator, "parent": parent, "start": start, "end": end,
               "text": passage, "status": item["status"], "status_note": item["status_note"]}
        if "tail_start" in item:
            # Parent text after its last child: closing words, provisos, Explanations.
            tail = item["tail_start"]
            if type(tail) is not int or not start < tail < end or not text[tail:end].strip():
                raise ValueError(f"{locator}: tail_start must point inside the unit at its trailing text")
            if text[text.rfind("\n", 0, tail) + 1:tail].strip():
                raise ValueError(f"{locator}: tail_start must begin a line of the parent's trailing text")
            if re.match(r"\s*\([A-Za-z0-9]+\)", text[tail:]):
                raise ValueError(f"{locator}: tail_start points at a child label; map that unit instead")
            row["tail_start"] = tail
        rows.append(row)
        by_locator[locator] = row
    for row in rows:
        if row["parent"]:
            parent = by_locator.get(row["parent"])
            if parent is None or not parent["start"] <= row["start"] < row["end"] <= parent["end"]:
                raise ValueError(f"{row['locator']}: capture its complete parent provision and keep the child inside it")
    def ancestor(a, b):
        parent = b["parent"]
        while parent:
            if parent == a["locator"]:
                return True
            parent = by_locator[parent]["parent"]
        return False

    for i, left in enumerate(rows):
        for right in rows[i + 1:]:
            if left["start"] < right["end"] and right["start"] < left["end"]:
                if not ancestor(left, right) and not ancestor(right, left):
                    raise ValueError("unrelated/sibling provision spans overlap; check the boundaries")
    for row in rows:
        if "tail_start" in row:
            children = [p for p in rows if p["parent"] == row["locator"]]
            if not children or any(p["end"] > row["tail_start"] for p in children):
                raise ValueError(f"{row['locator']}: tail_start must follow every mapped child unit")

    root_label = r"[1-9]\d*[A-Za-z]*(?:\.|[—–])"
    heading = r"(?:ORDER\s+[1-9]\d*|(?:[A-Za-z]+\s+)?SCHEDULE|PART\s+(?:[IVXLCDM]+|[1-9]\d*))\b"
    note_line = r"\[[^\]\n]{1,80}\][ \t]*(?:\n|$)"  # e.g. SSO amendment notes such as [23/2018]

    def skip_space_and_notes(position):
        while True:
            position += len(text[position:]) - len(text[position:].lstrip())
            note = re.match(note_line, text[position:])
            if not note or text[text.rfind("\n", 0, position) + 1:position].strip():
                return position
            position += note.end()

    for row in rows:
        # Check the remainder of the saved source, not sentence punctuation: units
        # legitimately end with colons, semicolons, quotations and table cells.
        following = skip_space_and_notes(row["end"])
        if following >= len(text):
            continue
        next_rows = [p for p in rows if p["start"] == following]
        if next_rows:
            if any(ancestor(row, p) for p in next_rows):
                raise ValueError(f"{row['locator']}: provision span ends before its own child unit")
            continue
        parent = by_locator.get(row["parent"]) if row["parent"] else None
        if parent and skip_space_and_notes(parent.get("tail_start", len(text))) == following:
            continue  # The child ends where its parent's declared trailing text begins.
        rest = text[following:]
        at_line_start = not text[text.rfind("\n", 0, following) + 1:following].strip()
        # Unmapped neighbouring units may supply a visible boundary; only accept
        # explicit line-start labels, never arbitrary continuation prose.
        boundary = at_line_start and re.match(r"(?:" + root_label + "|" + heading + ")", rest, re.I)
        if at_line_start and not boundary:
            # The next unit's own heading line, e.g. a marginal note, before its number.
            heading_line = re.match(r"([A-Z][^\n]{0,150})\n[ \t]*(?:" + root_label + "|" + heading + ")", rest)
            # SSO headings may end "etc."; other end punctuation suggests cut-off prose.
            boundary = heading_line and not re.search(r"(?<!\betc)[.,;:—–-]\s*$", heading_line[1])
        child = re.match(r"\(([A-Za-z0-9]+)\)", rest) if at_line_start else None
        if child and row["parent"]:
            # A child label ends this unit only as its own or an ancestor's next sibling,
            # never as one of its own unmapped sub-units.
            series, current = set(), row["locator"]
            while current:
                token = label_token(current)
                if token:
                    series |= next_labels(token)
                current = by_locator[current]["parent"] if current in by_locator else None
            boundary = child[1] in series
        if not boundary:
            raise ValueError(f"{row['locator']}: provision span cuts off before remaining source text; "
                             "extend it to the next unit boundary, map the omitted unit, or declare the "
                             "parent's trailing words with tail_start")
    return rows


def checked_provisions(source, text):
    index = source.get("provision_index")
    if not isinstance(index, dict) or index.get("boundaries_reviewed") is not True or not isinstance(index.get("review_note"), str) or not index["review_note"].strip():
        raise ValueError("statutory evidence needs a provision index with reviewed boundaries")
    if index.get("text_sha256") != source.get("text_sha256"):
        raise ValueError("provision index refers to a different text snapshot")
    expected = build_provisions(text, index)
    if expected != index.get("provisions"):
        raise ValueError("provision index does not match source labels, full text and offsets")
    return expected


def select_provision(rows, locator):
    locator = canonical_provision(locator)
    by_locator = {p["locator"]: p for p in rows}
    if locator not in by_locator:
        raise ValueError("cited provision is missing from the reviewed source map")
    selected, context = by_locator[locator], []
    parent = selected["parent"]
    while parent:
        context.insert(0, dict(by_locator[parent]))
        parent = by_locator[parent]["parent"]
    return [dict(selected)], context


def verify_statute_receipt(data, source):
    receipt = source.get("statute_verification")
    if not isinstance(receipt, dict):
        raise ValueError("legislation needs a fresh statute_verification receipt")
    for field in ("identity_note", "version_note", "commencement_note"):
        if not isinstance(receipt.get(field), str) or not receipt[field].strip():
            raise ValueError(f"statute_verification needs {field}")
    if receipt.get("instrument_kind") not in ("act", "subsidiary-legislation", "constitution", "other-written-law"):
        raise ValueError("identify whether the instrument is an Act, subsidiary legislation or other written law")
    if receipt.get("instrument_title") != source.get("title") or receipt.get("instrument_citation") != source.get("citation"):
        raise ValueError("statute_verification does not identify the actual source instrument")
    if receipt.get("source_version") != source.get("version"):
        raise ValueError("statute_verification does not match the actual source version")
    if not data.get("run_id") or receipt.get("run_id") != data["run_id"] or receipt.get("checked_on") != data.get("research_date"):
        raise ValueError("statute identity and version must be rechecked for this run and research date")
    draft_hash = data["draft"].get("sha256") if isinstance(data.get("draft"), dict) else None
    if receipt.get("draft_sha256") != draft_hash:
        raise ValueError("statute_verification belongs to a different draft snapshot; recheck this fresh draft")
    if not isinstance(receipt.get("law_as_at"), str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", receipt["law_as_at"]):
        raise ValueError("statute_verification needs its selected law_as_at date")
    date.fromisoformat(receipt["law_as_at"])
    return receipt
