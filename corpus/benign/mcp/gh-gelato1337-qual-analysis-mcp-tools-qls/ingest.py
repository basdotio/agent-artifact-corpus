"""Ingestion: files -> text -> speaker turns -> informant segments.

Text formats (.txt, .md, .srt, .vtt) are read directly. Everything else
(PDF, DOCX, ODT, HTML, audio, video, ...) goes through Docling.

The transcript parser recognises "Speaker: text" lines (also **Speaker:**
from Markdown exports and VTT <v Speaker> tags), decides who the interviewer
is, and turns every informant turn into one or more segments. Each segment
remembers the interviewer question it answers, which is shown as context and
used to flag concepts that only echo the interview guide.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from .util import QlsError, now, sha256_bytes

TEXT_SUFFIXES = {".txt", ".md", ".markdown", ".srt", ".vtt"}
INTERVIEWER_HINT = re.compile(r"interview|haastattel|moderator|researcher|tutkija|fasilit", re.I)

_TS = r"\[?\(?\d{1,2}:\d{2}(?::\d{2})?(?:[.,]\d+)?\)?\]?"
_TIMESTAMP_PREFIX = re.compile(rf"^\s*{_TS}\s*(?:-->\s*{_TS})?\s*")
_SPEAKER = re.compile(
    r"^\s*(?:\*\*|__)?"
    r"(?P<label>[A-ZÅÄÖ][\wÅÄÖåäö.\-]*(?: [\wÅÄÖåäö.\-]+){0,3}|[A-Za-z]\d{0,3})"
    r"(?:\*\*|__)?\s*[:：](?:\*\*|__)?\s+(?P<text>\S.*)$"
)
_VTT_VOICE = re.compile(r"^\s*<v\s+([^>]+)>(.*?)(?:</v>)?\s*$")


# ---------------------------------------------------------------------------
# Reading files
# ---------------------------------------------------------------------------


def read_text(path: Path) -> tuple[str, str]:
    """Return (text, parser_name)."""
    suffix = path.suffix.lower()
    if suffix in TEXT_SUFFIXES:
        raw = path.read_text(encoding="utf-8", errors="replace")
        if suffix in (".srt", ".vtt"):
            return _strip_subtitles(raw), "subtitles"
        return raw, "text"
    return _docling_text(path), "docling"


def _strip_subtitles(raw: str) -> str:
    out = []
    for line in raw.splitlines():
        s = line.strip()
        if not s or s == "WEBVTT" or s.isdigit() or "-->" in s:
            continue
        m = _VTT_VOICE.match(s)
        if m:
            s = f"{m.group(1).strip()}: {m.group(2).strip()}"
        out.append(s)
    return "\n".join(out)


def _docling_text(path: Path) -> str:
    import logging
    import os

    for name in ("docling", "docling_core", "rapidocr", "RapidOCR", "transformers"):
        logging.getLogger(name).setLevel(logging.WARNING)
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
    try:
        from docling.datamodel.base_models import InputFormat
        from docling.document_converter import AudioFormatOption, DocumentConverter
    except ImportError as exc:
        raise QlsError(
            f"{path.name}: Docling is needed for {path.suffix} files. "
            "Install with: pip install 'qual-analysis-mcp-tools[docling]'"
        ) from exc

    format_options = {}
    try:  # audio needs the ASR pipeline wired explicitly (docling[asr] extra)
        from docling.datamodel import asr_model_specs
        from docling.datamodel.pipeline_options import AsrPipelineOptions
        from docling.pipeline.asr_pipeline import AsrPipeline

        opts = AsrPipelineOptions()
        opts.asr_options = asr_model_specs.WHISPER_TURBO
        format_options[InputFormat.AUDIO] = AudioFormatOption(pipeline_cls=AsrPipeline, pipeline_options=opts)
    except ImportError:
        pass

    result = DocumentConverter(format_options=format_options).convert(str(path))
    return result.document.export_to_markdown()


# ---------------------------------------------------------------------------
# Transcript parsing
# ---------------------------------------------------------------------------


SECTION = "__section__"
_HEADING = re.compile(r"^\s*#{1,6}\s+(.*)$")
_LABEL_ONLY = re.compile(
    r"^\s*(?:\*\*|__)?(?P<label>[A-ZÅÄÖ][\wÅÄÖåäö.\-]*(?: [\wÅÄÖåäö.\-]+){0,3}|[A-Za-z]\d{0,3})(?:\*\*|__)?\s*[:：](?:\*\*|__)?\s*$"
)
_NOISE = re.compile(r"^\s*<!--.*?-->\s*$")


_PAGE = re.compile(r"\bpage\s+\d+(\s+of\s+\d+)?\b|©|\(c\)\s*\d{4}", re.I)


def _boilerplate(lines: list[str]) -> set[str]:
    """Running page headers and footers: short lines that repeat on many pages (digits ignored),
    carrying a page number or a copyright mark. They are dropped, so quotes can span page breaks."""
    from collections import Counter

    key = lambda ln: re.sub(r"\d+", "#", " ".join(ln.split()))
    counts = Counter(key(ln) for ln in lines if ln.strip() and len(ln) < 160)
    return {k for k, n in counts.items() if n >= 3 and _PAGE.search(k)}


def _clean_lines(text: str) -> list[tuple[str, bool]]:
    """(line, was_heading). Markdown heading marks are removed: document converters
    sometimes render speaker labels or section titles as headings. Page headers and
    footers repeated through the document are dropped."""
    out = []
    raw = text.splitlines()
    junk = _boilerplate(raw)
    for ln in raw:
        if _NOISE.match(ln) or (junk and re.sub(r"\d+", "#", " ".join(ln.split())) in junk):
            continue
        ln = _TIMESTAMP_PREFIX.sub("", ln).rstrip()
        m = _HEADING.match(ln)
        out.append((m.group(1).strip(), True) if m else (ln, False))
    return out


def parse_turns(text: str) -> list[tuple[str | None, str]]:
    """Split text into (speaker, text) turns.

    speaker is None for unlabelled text and SECTION for section titles (headings
    that are not speaker lines). Handles "Name: text", a label alone on its line
    followed by the text, labels rendered as Markdown headings, and a full name
    used once ("Claire Moreau:") for a speaker otherwise labelled by surname.
    """
    lines = _clean_lines(text)

    def label_of(ln: str) -> tuple[str | None, str | None]:
        m = _SPEAKER.match(ln)
        if m:
            return m.group("label").strip(), m.group("text").strip()
        m = _LABEL_ONLY.match(ln)
        if m:
            return m.group("label").strip(), ""
        return None, None

    candidates = Counter(lab for ln, _ in lines if (lab := label_of(ln)[0]))
    # A label must recur to count as a speaker; "Note: ..." once is just prose.
    speakers = {lab for lab, n in candidates.items() if n >= 2}

    def resolve(lab: str | None) -> str | None:
        if lab is None:
            return None
        if lab in speakers:
            return lab
        last = lab.split()[-1] if " " in lab else None
        return last if last in speakers else None

    turns: list[list] = []
    for ln, heading in lines:
        lab, rest = label_of(ln)
        spk = resolve(lab)
        if spk:
            turns.append([spk, [rest] if rest else []])
        elif heading and speakers and ln:
            turns.append([SECTION, [ln]])
            turns.append([turns[-2][0] if len(turns) > 1 else None, []])  # text after a title continues the speaker
        elif ln.strip():
            if not turns:
                turns.append([None, []])
            turns[-1][1].append(ln.strip())
        elif turns and turns[-1][1] and turns[-1][1][-1] != "":
            turns[-1][1].append("")  # paragraph break inside a turn
    out = []
    for spk, parts in turns:
        body = "\n".join(parts).strip()
        body = re.sub(r"\n{2,}", "\n\n", body)
        if not body:
            continue
        if out and spk == out[-1][0] and spk not in (SECTION, None):
            out[-1] = (spk, out[-1][1] + "\n\n" + body)  # same speaker split by a title: one turn
        else:
            out.append((spk, body))
    if not speakers:
        # No speaker labels: treat each paragraph as an informant turn.
        paras: list[str] = []
        for p in (p.strip() for p in re.split(r"\n\s*\n", "\n".join(ln for ln, _ in lines)) if p.strip()):
            if paras and not re.search(_SENT_END + "$", paras[-1]):
                paras[-1] += " " + p  # sentence cut by a page break
            else:
                paras.append(p)
        return [(None, p) for p in paras]
    return out


def assign_roles(turns: list[tuple[str | None, str]], interviewer_labels: list[str]) -> dict[str, str]:
    labels = [s for s, _ in turns if s and s != SECTION]
    if not labels:
        return {}
    wanted = {x.lower() for x in interviewer_labels}
    roles = {s: ("interviewer" if s.lower() in wanted or INTERVIEWER_HINT.search(s) else "informant") for s in set(labels)}
    if "interviewer" not in roles.values() and len(roles) >= 2:
        names = list(roles)
        # 1. explicit: "... I am interviewing Lindqvist" / "interview with Lindqvist"
        for spk, text in turns:
            if spk not in roles:
                continue
            for other in names:
                if other != spk and re.search(rf"\binterview(?:ing|ed)?\b[^.\n]{{0,80}}\b{re.escape(other)}\b", text, re.I):
                    roles[spk] = "interviewer"
                    return roles

        # 2. heuristic: the interviewer asks the most questions per turn, and usually speaks first
        first = next((s for s, _ in turns if s in roles), None)

        def score(spk: str) -> float:
            ts = [t for s, t in turns if s == spk]
            q_ratio = sum(t.rstrip().endswith("?") for t in ts) / max(len(ts), 1)
            return q_ratio + (0.25 if spk == first else 0.0)

        roles[max(roles, key=score)] = "interviewer"
    return roles


_SENT_END = r"[.!?:;\"'”’)\]…]"


def _split_long(text: str, max_chars: int) -> list[str]:
    """Cut a long turn into segments that are exact slices of its text.

    Prefers paragraph breaks that end a sentence, then sentence ends; never cuts at
    a paragraph break inside a sentence (PDF page breaks), and only cuts mid-sentence
    when a single sentence is longer than max_chars.
    """
    if len(text) <= max_chars:
        return [text]
    para = [m.end() for m in re.finditer(r"\n\s*\n", text) if re.search(_SENT_END + r"\s*$", text[:m.start()])]
    sent = [m.end() for m in re.finditer(r"(?<=[.!?])\s+", text)]
    chunks, start = [], 0
    while len(text) - start > max_chars:
        limit = start + max_chars
        cands = [p for p in para if start < p <= limit] or [p for p in sent if start < p <= limit]
        cut = max(cands) if cands else limit
        chunks.append(text[start:cut].strip())
        start = cut
    chunks.append(text[start:].strip())
    return [c for c in chunks if c]


def build_document(doc_id: str, text: str, interviewer_labels: list[str], max_segment_chars: int) -> dict:
    turns_raw = parse_turns(text)
    roles = assign_roles(turns_raw, interviewer_labels)
    turns, segments = [], []
    last_q, section, gap = None, None, 0
    for i, (spk, body) in enumerate(turns_raw, start=1):
        # Unlabelled text in a labelled transcript (title, preamble) and section titles
        # are kept but never coded; the current section is remembered on each segment.
        if spk == SECTION:
            role, section = "meta", body
        else:
            role = roles.get(spk, "informant") if spk else ("meta" if roles else "informant")
        tid = f"{doc_id}:t{i:03d}"
        turns.append({"id": tid, "speaker": "section" if spk == SECTION else (spk or role), "role": role, "text": body})
        if role == "meta":
            continue
        if role == "interviewer":
            last_q, gap = {"turn": tid, "text": body}, 0
            continue
        for chunk in _split_long(body, max_segment_chars):
            segments.append({
                "id": f"{doc_id}:s{len(segments) + 1:03d}",
                "turn": tid,
                "speaker": spk or "informant",
                "text": chunk,
                "question": last_q["text"] if last_q else None,
                "question_turn": last_q["turn"] if last_q else None,
                # 0 = directly answers the question; n = n informant segments after it
                "question_gap": gap,
                "section": section,
            })
            gap += 1
    return {"speakers": roles, "turns": turns, "segments": segments}


def safe_id(stem: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_-]+", "-", stem).strip("-") or "doc"
    return s[:48]
