"""Classify text into exactly one of a fixed set of categories."""

import json
import math

from local_llm._text import strip_fences as _strip_fences
from local_llm.ollama_client import generate


def classify(text: str, categories: list[str]) -> dict:
    """Classify 'text' into exactly one of 'categories'.

    Returns a dict {"label": <category>, "confidence": <float 0.0-1.0>} where
    label is normalized to the exact matching category string. Raises
    ValueError if categories is empty, the model output is not a JSON object,
    its label does not match any valid category, or the model's confidence is
    not a finite number (NaN or infinity).
    """
    if not categories:
        raise ValueError("categories must be a non-empty list of category names")

    category_list = ", ".join(categories)
    prompt = (
        "Classify the following text into exactly one of these categories: "
        + category_list + ". "
        "Respond with ONLY a JSON object of the form "
        '{"label": "<one category>", "confidence": <float 0.0-1.0>}. '
        "No markdown, no code fences, no commentary.\n\n"
        "Text:\n" + text
    )

    raw = generate(prompt)
    parsed = json.loads(_strip_fences(raw))
    if not isinstance(parsed, dict):
        raise ValueError(
            "Model returned valid JSON that is not an object. Model output: "
            + raw[:500]
        )

    label = parsed.get("label", "")
    normalized = None
    for category in categories:
        if str(label).strip().lower() == category.strip().lower():
            normalized = category
            break
    if normalized is None:
        raise ValueError(
            "Model returned label '" + str(label) + "' which does not match any "
            "valid category. Valid categories: " + category_list + ". "
            "Model output: " + raw[:500]
        )

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError, OverflowError):
        confidence = 0.0
    # NaN compares false against both bounds below, and an infinity would be
    # clamped into a plausible-looking 0.0 or 1.0, so non-finite values are
    # rejected as invalid model output rather than clamped.
    if not math.isfinite(confidence):
        raise ValueError(
            "Model returned confidence " + repr(confidence) + " which is not a "
            "finite number. Model output: " + raw[:500]
        )
    if confidence < 0.0:
        confidence = 0.0
    elif confidence > 1.0:
        confidence = 1.0

    return {"label": normalized, "confidence": confidence}
