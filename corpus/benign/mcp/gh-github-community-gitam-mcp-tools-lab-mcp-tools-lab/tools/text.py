"""Simple text statistics, with deliberately documented counting rules."""

import re
from collections import Counter


def analyze_text(text: str) -> dict:
    """Count Unicode words, characters, lines, and approximate sentences.

    Words are letter/digit sequences (apostrophes within words are kept).
    Sentences are nonempty pieces separated by '.', '!', or '?'.
    This is a simple heuristic, not linguistic analysis.
    """
    words = re.findall(r"[^\W_]+(?:['’][^\W_]+)*", text.lower())
    return {
        "characters": len(text),
        "words": len(words),
        "lines": len(text.splitlines()),
        "sentences": sum(bool(part.strip()) for part in re.split(r"[.!?]+", text)),
        "frequent_words": [
            {"word": word, "count": count}
            for word, count in Counter(words).most_common(10)
        ],
    }
