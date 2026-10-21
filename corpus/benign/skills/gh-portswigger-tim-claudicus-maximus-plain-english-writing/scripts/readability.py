#!/usr/bin/env python3
"""Score the readability of Markdown prose.

Usage: readability.py [FILE]        (reads stdin when FILE is omitted or "-")

Strips code, URLs, tables and headings, then prints Flesch Reading Ease,
Flesch-Kincaid grade, sentence-length figures and the longest sentences.
The result is advisory. It always exits 0. Use `--json` for machine output.
"""
import argparse
import json
import re
import sys

EASE_MIN = 40.0
GRADE_MAX = 10.0
LONG_SENTENCE = 25
MIN_WORDS = 100


def prose_only(markdown):
    """Return the running prose of a Markdown document as plain text."""
    text = re.sub(r"```.*?```", " ", markdown, flags=re.S)
    text = re.sub(r"~~~.*?~~~", " ", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("|"):
            lines.append("")
            continue
        if re.fullmatch(r"[-*_ ]{3,}", stripped):
            lines.append("")
            continue
        # Each list item counts as its own sentence.
        item = re.match(r"([-*+]|\d+[.)])\s+(.*)", stripped)
        if item:
            body = item.group(2).rstrip()
            if not re.search(r"[.!?:]$", body):
                body += "."
            lines.append(body)
        else:
            lines.append(stripped)
    text = "\n".join(lines)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "link", text)
    text = re.sub(r"`[^`]*`", "code", text)
    text = re.sub(r"[*_]{1,3}([^*_\n]+)[*_]{1,3}", r"\1", text)
    return text


def split_sentences(text):
    sentences = []
    for block in re.split(r"\n\s*\n|\n", text):
        block = block.strip()
        if not block:
            continue
        parts = re.split(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9`])", block)
        sentences.extend(p.strip() for p in parts if p.strip())
    return sentences


def words_in(sentence):
    return re.findall(r"[A-Za-z0-9]+(?:['’-][A-Za-z0-9]+)*", sentence)


def count_syllables(word):
    word = word.lower()
    word = re.sub(r"[^a-z]", "", word)
    if not word:
        return 1
    if len(word) <= 3:
        return 1
    word = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", word)
    word = re.sub(r"^y", "", word)
    groups = re.findall(r"[aeiouy]{1,2}", word)
    return max(1, len(groups))


def score(markdown):
    text = prose_only(markdown)
    sentences = split_sentences(text)
    per_sentence = [(s, len(words_in(s))) for s in sentences]
    per_sentence = [(s, n) for s, n in per_sentence if n > 0]
    words = [w for s, _ in per_sentence for w in words_in(s)]
    n_words, n_sent = len(words), len(per_sentence)
    if n_words == 0 or n_sent == 0:
        return {"words": 0, "sentences": 0, "reliable": False}
    syllables = sum(count_syllables(w) for w in words)
    wps = n_words / n_sent
    spw = syllables / n_words
    long_ones = [(s, n) for s, n in per_sentence if n > LONG_SENTENCE]
    longest = sorted(per_sentence, key=lambda p: -p[1])[:3]
    return {
        "words": n_words,
        "sentences": n_sent,
        "words_per_sentence": round(wps, 1),
        "reading_ease": round(206.835 - 1.015 * wps - 84.6 * spw, 1),
        "grade": round(0.39 * wps + 11.8 * spw - 15.59, 1),
        "long_sentences": len(long_ones),
        "long_sentence_share": round(len(long_ones) / n_sent, 2),
        "longest": [{"words": n, "text": s} for s, n in longest],
        "reliable": n_words >= MIN_WORDS,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("file", nargs="?", default="-")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--ease-min", type=float, default=EASE_MIN)
    parser.add_argument("--grade-max", type=float, default=GRADE_MAX)
    args = parser.parse_args()
    source = sys.stdin if args.file == "-" else open(args.file, encoding="utf-8")
    with source:
        result = score(source.read())
    if args.json:
        print(json.dumps(result, indent=2))
        return
    if not result["sentences"]:
        print("No prose found.")
        return
    ease_ok = result["reading_ease"] >= args.ease_min
    grade_ok = result["grade"] <= args.grade_max
    print(f"Words: {result['words']}   Sentences: {result['sentences']}   "
          f"Average sentence: {result['words_per_sentence']} words")
    print(f"Reading Ease: {result['reading_ease']} (target {args.ease_min:g} or higher) "
          f"{'ok' if ease_ok else 'BELOW TARGET'}")
    print(f"Grade level:  {result['grade']} (target {args.grade_max:g} or lower) "
          f"{'ok' if grade_ok else 'ABOVE TARGET'}")
    print(f"Sentences over {LONG_SENTENCE} words: {result['long_sentences']} "
          f"({round(result['long_sentence_share'] * 100)}%)")
    if not result["reliable"]:
        print(f"Note: fewer than {MIN_WORDS} words, so the scores are unreliable.")
    print("Longest sentences:")
    for item in result["longest"]:
        text = item["text"] if len(item["text"]) <= 160 else item["text"][:157] + "..."
        print(f"  {item['words']} words: {text}")


if __name__ == "__main__":
    main()
