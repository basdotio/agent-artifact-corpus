"""Ask the local model for a summary of at most max_words words."""

from local_llm.ollama_client import OllamaError, generate


def summarize(text: str, max_words: int) -> str:
    """Ask the model for a summary of 'text' in at most max_words words.

    The word limit is a request in the prompt, not enforced: the model's reply
    is returned as-is (surrounding whitespace stripped), never truncated or
    word-counted, so it can be longer than max_words.
    Raises ValueError if max_words is not a positive integer. Raises OllamaError
    if the model returns an empty response (e.g. a thinking-model regression
    leaving the 'response' field blank) so callers never receive an empty string
    masquerading as a valid summary.
    """
    if max_words <= 0:
        raise ValueError(
            "max_words must be a positive integer, got " + str(max_words)
        )

    prompt = (
        "Summarize the following text in at most " + str(max_words) + " words. "
        "Return ONLY the summary with no preamble, no labels, and no commentary.\n\n"
        "Text:\n" + text
    )
    summary = generate(prompt).strip()
    if not summary:
        raise OllamaError(
            "Model returned an empty summary. Ensure the model is loaded and "
            "responding (a blank 'response' field can indicate a thinking-model "
            "configuration issue)."
        )
    return summary
