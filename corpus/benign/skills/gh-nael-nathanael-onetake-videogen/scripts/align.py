#!/usr/bin/env python3
"""
Give a voice-over's Whisper words the spelling of the text that was meant to be on screen.

  run.sh align.py WORDS.json TEXT.txt

Whisper hears the narration, so names, brands and symbols come out as it guesses them
("miraystudio", a lone "%"). This keeps Whisper's timings and takes the words from TEXT.txt:
the script as it should read in captions (digits as digits, names spelled right). `[pause N]`
paragraphs are skipped. Words Whisper heard that TEXT lacks are kept; words in TEXT that were
never heard are dropped; both are listed.

The first run keeps the original as WORDS.whisper.json next to WORDS.json and later runs align
from it, so rerunning after a text edit is safe. Exits 1 without writing when under 70% of the
text matches: that is the wrong text file, not a spelling difference.
"""

import argparse
import re
from difflib import SequenceMatcher
from pathlib import Path

from common import load_json, save_json

MIN_MATCH = 0.7


def norm(token):
    return re.sub(r"[\W_]+", "", token.lower())


def text_tokens(text):
    """Caption tokens of the text; a token with no letters or digits joins the one before it."""
    out = []
    for par in re.split(r"\n\s*\n", text.strip()):
        if re.fullmatch(r"\[pause\s+[\d.]+\]", par.strip()):
            continue
        for tok in par.split():
            if not norm(tok) and out:
                out[-1] += tok if re.fullmatch(r"[%.,!?;:)\]]+", tok) else " " + tok
            else:
                out.append(tok)
    return out


def glue_symbols(words):
    """Whisper emits symbols as words of their own ("%"): put each back on the word before it."""
    out = []
    for w in words:
        if not norm(w["text"]) and out:
            out[-1] = {**out[-1], "text": out[-1]["text"] + w["text"].strip(), "end": w["end"]}
        else:
            out.append(dict(w))
    return out


def wrote_symbol(heard, written):
    """True when the written token carries a symbol that is read aloud and the heard word lacks it."""
    spoken = r"[%$€£¥&+=°#@]"
    return bool(re.search(spoken, written)) and not re.search(spoken, heard)


def spread(tokens, start, end):
    """Timings for tokens sharing one stretch of audio, each given time by its length."""
    weights = [max(1, len(norm(t))) for t in tokens]
    total, at, out = sum(weights), start, []
    for tok, wt in zip(tokens, weights):
        nxt = at + (end - start) * wt / total
        out.append({"text": tok, "start": round(at, 3), "end": round(nxt, 3)})
        at = nxt
    return out


def align(words, tokens):
    """-> (aligned words, share of text tokens matched exactly, heard-only texts, unheard tokens)."""
    words = glue_symbols(words)
    sm = SequenceMatcher(None, [norm(w["text"]) for w in words], [norm(t) for t in tokens], autojunk=False)
    out, matched, extra, unheard = [], 0, [], []
    # Everything between two matching runs is one stretch of audio said one way and written another
    # ("90 percent" / "90%"), whatever mix of replace, delete and insert the matcher reports for it.
    i, j = 0, 0
    for a, b, size in sm.get_matching_blocks():
        heard, written = words[i:a], tokens[j:b]
        if heard and not written and out and wrote_symbol(words[i - 1]["text"], out[-1]["text"]):
            # "90" + "percent" against "90%": the symbol is that word, so it takes its time.
            out[-1]["end"] = heard[-1]["end"]
        elif heard and not written:
            extra += [w["text"] for w in heard]
            out += heard
        elif written and not heard:
            unheard += written
        elif len(heard) == len(written):
            out += [{**w, "text": t} for w, t in zip(heard, written)]
        elif heard:
            base = {**heard[0], "prob": min(w.get("prob", 1) for w in heard), "filler": False}
            out += [{**base, **timed} for timed in spread(written, heard[0]["start"], heard[-1]["end"])]
        out += [{**w, "text": t} for w, t in zip(words[a:a + size], tokens[b:b + size])]
        matched += size
        i, j = a + size, b + size
    for i, w in enumerate(out):
        w["i"] = i
    return out, matched / max(1, len(tokens)), extra, unheard


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words")
    ap.add_argument("text")
    a = ap.parse_args()

    path = Path(a.words)
    original = path.with_suffix(".whisper.json")
    data = load_json(original if original.exists() else path)
    out, share, extra, unheard = align(data["words"], text_tokens(Path(a.text).read_text()))
    if share < MIN_MATCH:
        raise SystemExit(f"only {share:.0%} of {a.text} matches the narration in {a.words}: wrong text file?")
    if not original.exists():
        save_json(data, original)
    save_json({**data, "words": out}, path)
    changed = sum(1 for w in out if w["text"] not in {x["text"] for x in data["words"]})
    print(f"{len(out)} words, {changed} respelled from {a.text} ({share:.0%} matched) -> {path}")
    if extra:
        print(f"heard but not in the text, kept: {' '.join(extra)}")
    if unheard:
        print(f"in the text but not heard, dropped: {' '.join(unheard)}")


if __name__ == "__main__":
    main()
