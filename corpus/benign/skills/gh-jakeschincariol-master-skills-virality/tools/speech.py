#!/usr/bin/env python3
"""speech.py - how long a line takes to say, and what a transcript actually measures.

New in the virality skill (Jakeschincariol/master-skills). Shared by breakdown.py,
voice.py and preflight.py, so every timing in the skill is computed the same way.

Two jobs:

  1. TIME A LINE. Word counts lie about numbers. "$4,200" is one token on the page
     and "four thousand two hundred dollars" out loud, and payoff hooks are full of
     numbers. spoken_words() says each number the way a person would before it counts.

  2. READ A TRANSCRIPT. SRT, WebVTT, Whisper JSON, YouTube json3 auto-captions, or
     plain text. With timings it measures the real speaking pace, which is the number
     to pass as --wpm everywhere else in this skill.

Timings are estimates from a words-per-minute rate. Good enough to plan a cut, not a
substitute for recording the take. Most people land between 150 and 190 wpm; fast
short-form talkers run 220 to 300. Measure yours once from one of your own videos.

Usage
  python3 speech.py --line "I saved $4,200 last month."            # one line
  python3 speech.py --line "Hook." --line "Second beat." --wpm 180  # a timed sequence
  python3 speech.py my_best_video.srt                              # measure your pace
  python3 speech.py captions.en.json3 --json
"""

import argparse
import json
import os
import re
import sys

DEFAULT_WPM = 165.0

# A numeric token, after surrounding punctuation is stripped.
NUM_RE = re.compile(
    r"^(?P<cur>[$£€¥])?"            # $ GBP EUR JPY
    r"(?P<num>\d[\d,]*(?:\.\d+)?)"
    r"(?P<suf>bn|[kKmMbB]|%|[xX]|st|nd|rd|th|s)?"
    r"(?P<rest>.*)$")
COMPOUND_NUM_RE = re.compile(r"^\d+(?:[/:\-–]\d+)+$")   # 24/7, 3:30, 5-10
STRIP_EDGES = "\"'()[]{}<>.,!?;:*_‘’“”"
SYMBOL_WORDS = {"&": 1, "+": 1, "=": 1, "%": 1, "@": 1}
DOMAIN_RE = re.compile(r"^[A-Za-z0-9-]+(?:\.[A-Za-z]{2,})+$")
SENT_SPLIT_RE = re.compile(r"(?<=[.!?])[\"'’”)]*\s+|\n+")


# --------------------------------------------------------------------------- numbers

def _under_1000(g):
    hundreds, rest = divmod(g, 100)
    w = 2 if hundreds else 0                     # "four hundred"
    if rest:
        w += 1 if (rest < 20 or rest % 10 == 0) else 2   # "twelve", "forty", "forty two"
    return w


def int_words(n):
    """Words in an integer said out loud, US style ("four hundred twelve thousand")."""
    n = abs(int(n))
    if n == 0:
        return 1
    words, scale = 0, 0
    while n:
        n, group = divmod(n, 1000)
        if group:
            words += _under_1000(group) + (1 if scale else 0)   # + thousand / million
        scale += 1
    return words


def year_words(n):
    """1999 -> nineteen ninety nine, 2026 -> twenty twenty six, 2005 -> two thousand five."""
    if 2000 <= n <= 2009:
        return 2 if n == 2000 else 3
    hi, lo = divmod(n, 100)
    if lo == 0:
        return _under_1000(hi) + 1                # "nineteen hundred"
    return _under_1000(hi) + (1 if lo < 10 else 0) + _under_1000(lo)


def number_token_words(token):
    """Spoken word count for one numeric token, or None if it is not a number."""
    if COMPOUND_NUM_RE.match(token):
        parts = re.split(r"[/:\-–]", token)
        joins = len(re.findall(r"[\-–]", token))      # 5-10 -> "five to ten"
        return sum(int_words(p) for p in parts) + joins
    m = NUM_RE.match(token)
    if not m:
        return None
    cur, num, suf, rest = m.group("cur"), m.group("num"), m.group("suf") or "", m.group("rest")
    whole, _, frac = num.replace(",", "").partition(".")
    if not whole:
        return None
    value = int(whole)
    plain = not cur and not suf and "," not in num and not frac
    if plain and 1900 <= value <= 2099:
        words = year_words(value)
    elif suf == "s" and 1900 <= value <= 2099:        # the 1990s
        words = year_words(value)
    else:
        words = int_words(value)
    if frac:
        words += 1 + len(frac)                     # "point two five"
    if suf.lower() in ("k", "m", "b", "bn", "x", "%"):
        words += 1                                 # thousand / million / billion / ex / percent
    if cur:
        words += 1                                 # dollars
    if rest:
        words += len(re.findall(r"[A-Za-z]+", rest))   # "$20/mo" -> + "mo"
    return words


def spoken_words(text):
    """Word count of `text` as said out loud: numbers expanded, symbols voiced, emoji silent."""
    total = 0
    for raw in text.split():
        token = raw.strip(STRIP_EDGES)
        if not token:
            continue
        n = number_token_words(token)
        if n is not None:
            total += n
            continue
        if token in SYMBOL_WORDS:
            total += SYMBOL_WORDS[token]
            continue
        if re.match(r"^#\d+$", token):                     # "#1" -> "number one"
            total += 1 + int_words(token[1:])
            continue
        # "highest-paying" is two words out loud, "don't" is one, "opusjake.ai" is three.
        parts = [p for p in re.split(r"[-–/.]+", token) if re.search(r"[A-Za-z0-9]", p)]
        if parts:
            total += len(parts)
            if DOMAIN_RE.match(token):
                total += token.count(".")                   # "dot"
    return total


def seconds(text, wpm=DEFAULT_WPM):
    return spoken_words(text) * 60.0 / float(wpm)


def sentences(text):
    """Split into sentences without breaking "1.2M" or "$4.50" in half."""
    parts = SENT_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p and re.search(r"[A-Za-z0-9]", p)]


def timecode(sec):
    sec = max(0.0, float(sec))
    m, s = divmod(sec, 60)
    return "%d:%04.1f" % (int(m), s)


# ----------------------------------------------------------------------- transcripts

TS_RE = re.compile(r"(?:(\d+):)?(\d{1,2}):(\d{2})(?:[.,](\d{1,3}))?")
CUE_RE = re.compile(r"^\s*(\S+)\s*-->\s*(\S+)")
VTT_TAG_RE = re.compile(r"<[^>]+>")


def parse_ts(s):
    m = TS_RE.search(s)
    if not m:
        raise ValueError("bad timestamp: %r" % s)
    h, mi, se, ms = m.groups()
    return int(h or 0) * 3600 + int(mi) * 60 + int(se) + (int((ms or "0").ljust(3, "0")) / 1000.0)


def _load_subtitles(raw):
    cues, cur = [], None
    for line in raw.splitlines():
        m = CUE_RE.match(line)
        if m:
            try:
                cur = [parse_ts(m.group(1)), parse_ts(m.group(2)), []]
                cues.append(cur)
            except ValueError:
                cur = None
            continue
        if line.strip("\r") == "":
            cur = None            # an empty line ends a cue (SRT and WebVTT agree on this)
            continue
        if cur is None:
            continue              # sequence numbers, the WEBVTT header, NOTE and STYLE blocks
        text = VTT_TAG_RE.sub("", line).strip()
        if text:                  # YouTube puts whitespace-only lines inside its cues
            cur[2].append(text)
    out, prev = [], []
    for start, end, lines in cues:
        # YouTube's rolling auto-captions repeat the previous cue's lines at the top of the
        # next one. Keep only the lines that are new, or every sentence is counted twice.
        fresh = [l for l in lines if l not in prev]
        if fresh:
            out.append((start, end, " ".join(fresh)))
        prev = lines
    return out


def _load_json(data):
    if isinstance(data, dict) and "events" in data:           # YouTube json3
        events = [e for e in data["events"] if e.get("segs")]
        out = []
        for i, e in enumerate(events):
            text = "".join(s.get("utf8", "") for s in e["segs"]).replace("\n", " ").strip()
            if not text:
                continue
            start = e.get("tStartMs", 0) / 1000.0
            dur = e.get("dDurationMs")
            if dur is None:
                nxt = events[i + 1].get("tStartMs") if i + 1 < len(events) else None
                end = nxt / 1000.0 if nxt is not None else start
            else:
                end = start + dur / 1000.0
            out.append((start, end, text))
        return out
    segs = data.get("segments", []) if isinstance(data, dict) else data
    out = []
    for s in segs or []:
        if not isinstance(s, dict):
            continue
        text = (s.get("text") or "").strip()
        if text:
            out.append((float(s.get("start", 0)), float(s.get("end", s.get("start", 0))), text))
    if not out and isinstance(data, dict) and isinstance(data.get("text"), str):
        out = [(None, None, data["text"].strip())]
    return out


def load_transcript(path):
    """Return [(start, end, text)]. Plain text comes back as one cue with no timings."""
    if path == "-":
        raw = sys.stdin.read()
    else:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            raw = fh.read()
    ext = os.path.splitext(path)[1].lower()
    stripped = raw.lstrip()
    if ext in (".json", ".json3") or (ext not in (".srt", ".vtt", ".txt", ".md") and stripped[:1] in "{["):
        try:
            data = json.loads(raw)
        except ValueError:
            data = None
        if data is not None:
            return _load_json(data)   # valid JSON with no transcript in it is empty, not prose
    if "-->" in raw:
        return _load_subtitles(raw)
    text = " ".join(raw.split())
    return [(None, None, text)] if text else []


def measure(cues):
    """Words, span and pace of a transcript. Pace is None when there are no timings."""
    text = " ".join(c[2] for c in cues)
    words = spoken_words(text)
    timed = [c for c in cues if c[0] is not None]
    if timed:
        start, end = min(c[0] for c in timed), max(c[1] for c in timed)
        span = max(0.0, end - start)
    else:
        start = end = span = None
    pace = round(words / (span / 60.0)) if span else None
    return {"cues": len(cues), "words": words, "start": start, "end": end,
            "span": round(span, 2) if span is not None else None, "wpm": pace, "text": text}


# ------------------------------------------------------------------------------- cli

def main():
    ap = argparse.ArgumentParser(
        description="Time lines out loud, or measure the speaking pace of a transcript.",
        epilog="Numbers are expanded the way they are said, so '$4,200' counts as five words.")
    ap.add_argument("input", nargs="?", help="transcript (.srt .vtt .json .json3 .txt) or - for stdin")
    ap.add_argument("--line", action="append", default=[], help="a line to time (repeatable)")
    ap.add_argument("--wpm", type=float, default=DEFAULT_WPM,
                    help="speaking rate for timing lines (default %(default)s)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    if args.wpm <= 0:
        ap.error("--wpm must be positive")
    if not args.line and not args.input:
        ap.print_help(sys.stderr)
        return 2

    if args.line:
        rows, clock = [], 0.0
        for line in args.line:
            dur = seconds(line, args.wpm)
            rows.append({"line": line, "spoken_words": spoken_words(line),
                         "start": round(clock, 2), "seconds": round(dur, 2)})
            clock += dur
        if args.json:
            print(json.dumps({"wpm": args.wpm, "lines": rows, "total": round(clock, 2)}, indent=1))
            return 0
        print()
        for r in rows:
            print("  %s  %4.1fs  %2d words  %s" % (timecode(r["start"]), r["seconds"],
                                                   r["spoken_words"], r["line"]))
        print("\n  total %.1fs at %g wpm\n" % (clock, args.wpm))
        return 0

    if args.input != "-" and not os.path.exists(args.input):
        print("no such file: %s" % args.input, file=sys.stderr)
        return 2
    cues = load_transcript(args.input)
    if not cues:
        print("no speech found in %s" % args.input, file=sys.stderr)
        return 1
    m = measure(cues)
    if args.json:
        print(json.dumps({k: v for k, v in m.items() if k != "text"}, indent=1))
        return 0
    print()
    if m["wpm"]:
        print("  %s   %d cues   %d spoken words   %s -> %s (%.1fs)   pace %d wpm" % (
            args.input, m["cues"], m["words"], timecode(m["start"]), timecode(m["end"]),
            m["span"], m["wpm"]))
        print("  Pass --wpm %d when you time scripts for this voice.\n" % m["wpm"])
    else:
        print("  %s   %d spoken words, no timings in this file." % (args.input, m["words"]))
        print("  At %g wpm that is about %.1fs. Use a .srt/.vtt/.json3 to measure real pace.\n"
              % (args.wpm, m["words"] * 60.0 / args.wpm))
    return 0


if __name__ == "__main__":
    sys.exit(main())
