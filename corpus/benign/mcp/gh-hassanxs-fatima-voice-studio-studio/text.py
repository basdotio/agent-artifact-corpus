"""Turning a script into segments the engine speaks one at a time.

A script is split at paragraphs (blank lines) and [pause] tags, then each paragraph's sentences are packed into
segments of up to `max_chars` characters. Segments never cross a paragraph or a pause, so the silence between
them is always ours (and the right length), and a segment can be regenerated on its own.

Pause tags: [pause] (1 second), [pause 2], [pause 2s], [pause 1.5 s], [pause 500ms].
Other words in square brackets are tags for voice models that act on them (S2 Pro: [whisper], [excited],
[low voice]...): sent to those as written, left out everywhere else (other models, subtitles, estimates).
"""
import re
import unicodedata

PAUSE_TAG = re.compile(r"\[\s*pause(?:\s+(\d+(?:[.,]\d+)?)\s*(ms|s|sec|seconds?)?)?\s*\]", re.I)
# Chinese and Japanese put no space after a full stop or comma; their closing quotes stay with the sentence.
SENTENCE_END = re.compile(r"(?<=[.!?…])[\"'”’»)\]]*\s+|(?<=[。！？])(?![」』”’）)\]。！？])\s*|(?<=[。！？][」』”’）)\]])\s*")
CLAUSE_END = re.compile(r"(?<=[,;:—–])\s+|(?<=[、，；：])\s*")
NO_SPACE = re.compile(r"[\u3000-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff\uff00-\uffef]")  # written without spaces
TAG = re.compile(r"\[(?!\s*pause\b)[^\[\]\n]{1,60}\]", re.I)  # [whisper], not [pause 2]
MIN_SEGMENT = 40  # characters: shorter sentences are joined to their neighbour when they fit


def _pause_seconds(m: re.Match) -> float:
    if not m.group(1):
        return 1.0
    value = float(m.group(1).replace(",", "."))
    return value / 1000 if (m.group(2) or "").lower() == "ms" else value


def clean(text: str) -> str:
    """Normalise spacing and characters the engine reads badly."""
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace(" ", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\s*\n\s*\n\s*", "\n\n", text)  # paragraph breaks
    text = re.sub(r"(?<!\n)\n(?!\n)", " ", text)  # single line breaks are just wrapping
    return text.strip()


def width(text: str) -> int:
    """Room on screen: Chinese, Japanese and Korean characters take two letters' worth."""
    return sum(2 if unicodedata.east_asian_width(c) in "WF" else 1 for c in text)


SLOW = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")  # Chinese characters and kana: about three letters' worth of speech each


def spoken(text: str) -> int:
    """Length for sizing parts and estimating time: like width(), but a Chinese character or kana counts three."""
    return width(text) + len(SLOW.findall(text))


def glue(a: str, b: str) -> str:
    """Join two pieces of a script: with a space, except where the writing uses none (Chinese, Japanese)."""
    if not a or not b:
        return a or b
    return a + b if NO_SPACE.match(a[-1]) or NO_SPACE.match(b[0]) else f"{a} {b}"


def _split_long(sentence: str, limit: int) -> list[str]:
    """A sentence longer than the limit: split at commas/semicolons, else between words (or characters)."""
    if spoken(sentence) <= limit:
        return [sentence]
    out, cur = [], ""
    for part in CLAUSE_END.split(sentence):
        if spoken(part) > limit:  # no punctuation to split at: cut between words
            words = [w for w in part.split(" ") if w]
            for w in words:
                while spoken(w) > limit:  # one long run without spaces
                    k, n = 0, 0
                    while k < len(w) and n + spoken(w[k]) <= limit:
                        n += spoken(w[k])
                        k += 1
                    if cur:
                        out.append(cur)
                        cur = ""
                    out.append(w[:k])
                    w = w[k:]
                if cur and spoken(glue(cur, w)) > limit:
                    out.append(cur)
                    cur = w
                else:
                    cur = glue(cur, w)
            continue
        if cur and spoken(glue(cur, part)) > limit:
            out.append(cur)
            cur = part
        else:
            cur = glue(cur, part)
    if cur:
        out.append(cur)
    return out


def sentences(paragraph: str) -> list[str]:
    return [s.strip() for s in SENTENCE_END.split(paragraph) if s.strip()]


def _pack(paragraph: str, limit: int) -> list[str]:
    """Pack a paragraph's sentences into chunks of at most `limit` characters, balanced in size."""
    parts = [p for s in sentences(paragraph) for p in _split_long(s, limit)]
    if not parts:
        return []
    total = sum(spoken(p) + 1 for p in parts)
    # Aim for evenly sized chunks rather than full ones followed by a stub.
    target = min(limit, max(MIN_SEGMENT, total / max(1, -(-total // limit))))
    out, cur = [], ""
    for p in parts:
        if cur and (spoken(glue(cur, p)) > limit or spoken(cur) >= target):
            out.append(cur)
            cur = p
        else:
            cur = glue(cur, p)
    if cur:
        if out and spoken(cur) < MIN_SEGMENT and spoken(glue(out[-1], cur)) <= limit:
            out[-1] = glue(out[-1], cur)
        else:
            out.append(cur)
    return out


def split(text: str, *, max_chars: int = 600, pause_segment: float = 0.25,
          pause_paragraph: float = 0.7) -> list[dict]:
    """[{"text", "pause_after" (seconds of silence after it), "paragraph" (0-based)}]"""
    text = clean(text)
    segments: list[dict] = []
    paragraph = 0
    for block in text.split("\n\n"):
        start, ended_by_tag = len(segments), False
        pos = 0
        for m in [*PAUSE_TAG.finditer(block), None]:
            chunk = block[pos:m.start() if m else len(block)].strip()
            for t in _pack(chunk, max_chars):
                segments.append({"text": t, "pause_after": pause_segment, "paragraph": paragraph})
            ended_by_tag = bool(m) and not block[m.end():].strip()
            if m:
                if len(segments) > start:  # a tag before any text in this paragraph has nothing to follow
                    segments[-1]["pause_after"] = _pause_seconds(m)
                pos = m.end()
        if len(segments) > start:
            if not ended_by_tag:
                segments[-1]["pause_after"] = pause_paragraph
            paragraph += 1
    if segments:
        segments[-1]["pause_after"] = 0.0
    return segments


def title_of(text: str, words: int = 6) -> str:
    """A short title from the start of a script (for file names and lists)."""
    first = re.sub(PAUSE_TAG, " ", clean(text)).split("\n")[0]
    w = re.findall(r"[\w'’-]+", first)
    return " ".join(w[:words]) or "Untitled"


def strip_tags(text: str) -> str:
    """The text without [tags] (pause tags stay): what's actually said."""
    text = TAG.sub(" ", text)
    text = re.sub(r" +([,.;:!?…])", r"\1", re.sub(r"[ \t]{2,}", " ", text))
    return text.strip()


def estimate_seconds(text: str) -> float:
    """Rough speaking time: about 14 characters per second across our languages (tags aren't spoken)."""
    return spoken(re.sub(PAUSE_TAG, "", strip_tags(text))) / 14.0
