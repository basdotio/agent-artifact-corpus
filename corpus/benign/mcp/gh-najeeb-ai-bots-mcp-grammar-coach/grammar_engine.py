"""
grammar_engine.py — the analysis logic behind the grammar-coach MCP tools.

Kept separate from server.py so the tool definitions stay clean and the engine
is independently testable. Uses language_tool_python when available, with a
lightweight fallback so the server always returns a structured result.
"""

import re

_FALLBACK_PATTERNS = [
    (" dont ", "don't", "Missing apostrophe: 'don't'."),
    (" cant ", "can't", "Missing apostrophe: 'can't'."),
    (" wont ", "won't", "Missing apostrophe: 'won't'."),
    (" alot ", "a lot", "'a lot' is two words."),
    (" could of ", "could have", "Use 'could have', not 'could of'."),
    (" should of ", "should have", "Use 'should have', not 'should of'."),
    (" would of ", "would have", "Use 'would have', not 'would of'."),
    (" more better ", "better", "Double comparative: use 'better'."),
    (" theres ", "there's", "Missing apostrophe: 'there's'."),
]


def run_grammar_check(text: str) -> dict:
    """Return a structured grammar report (never free-form prose)."""
    if not text or not text.strip():
        return {"error_count": 0, "errors": [], "engine": "none"}

    try:
        import language_tool_python
        tool = language_tool_python.LanguageTool("en-US")
        matches = tool.check(text)
        errors = [{
            "message": m.message,
            "suggestion": ", ".join(m.replacements[:3]) if m.replacements else "",
            "context": m.context,
            "rule": m.ruleId,
        } for m in matches[:25]]
        try:
            tool.close()
        except Exception:
            pass
        return {"error_count": len(matches), "errors": errors, "engine": "LanguageTool"}
    except Exception:
        pass

    low = " " + text.lower() + " "
    errors = []
    for bad, good, msg in _FALLBACK_PATTERNS:
        if bad in low:
            errors.append({"message": msg, "suggestion": good,
                           "context": bad.strip(), "rule": "FALLBACK"})
    if re.search(r"\bi\b", text):
        errors.append({"message": "Capitalize the pronoun 'I'.", "suggestion": "I",
                       "context": "i", "rule": "FALLBACK"})
    return {"error_count": len(errors), "errors": errors, "engine": "heuristic-fallback"}


def readability_metrics(text: str) -> dict:
    """Return structured readability metrics."""
    words = re.findall(r"\b\w+\b", text)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    wc = len(words)
    sc = max(1, len(sentences))
    awps = round(wc / sc, 1)

    # Flesch Reading Ease (approx) needs syllable count
    def _syllables(w):
        w = w.lower()
        groups = re.findall(r"[aeiouy]+", w)
        n = len(groups)
        if w.endswith("e") and n > 1:
            n -= 1
        return max(1, n)

    syll = sum(_syllables(w) for w in words) if wc else 0
    if wc and sc:
        ease = 206.835 - 1.015 * (wc / sc) - 84.6 * (syll / wc)
    else:
        ease = 0.0
    ease = round(max(0.0, min(100.0, ease)), 1)

    if ease >= 70:
        grade = "Grade 6-7 (easy)"
    elif ease >= 50:
        grade = "Grade 8-10 (standard)"
    elif ease >= 30:
        grade = "Grade 11-13 (difficult)"
    else:
        grade = "College+ (very difficult)"

    return {
        "word_count": wc,
        "sentence_count": len(sentences),
        "avg_words_per_sentence": awps,
        "reading_ease": ease,
        "grade_level": grade,
    }
