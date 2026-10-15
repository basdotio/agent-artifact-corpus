"""
Minimal, dependency-free Jev client for OpenRouter (Python 3.8+, stdlib only).

Jev is TypeSafe's System One decision model. This client sends a `state` plus one
or more typed `questions` (noul / choice / score) and returns the typed answers
with probabilities and confidence. See ../references/02-openrouter-decisions-api.md.

Auth: set OPENROUTER_API_KEY in your environment (get a key at
https://openrouter.ai/keys).

IMPORTANT: the raw endpoint path still varies across OpenRouter docs. It is exposed
below as ENDPOINT so it is a one-line change. If a call 404s, switch it to the
other documented path, or use the official `typesafe_sdk` instead (which handles
the path for you). Verify against https://openrouter.ai/typesafe/jev-1.13 .
"""

import json
import os
import urllib.request
import urllib.error

MODEL = "typesafe/jev-1.13"
# Two documented paths exist; try this first, fall back to the other if it 404s.
ENDPOINT = "https://openrouter.ai/api/alpha/decisions"
# ALT_ENDPOINT = "https://openrouter.ai/api/v1/systemone"


# ---- question builders (keep request construction in one place) ----


def noul(instructions):
    """Yes/no question. Response: {'type':'noul','noul': P(yes) float 0..1}."""
    return {"type": "noul", "instructions": instructions}


def choice(instructions, options):
    """Pick one option. `options` is {key: description}. Max 255 options.
    Response: {'choice': key, 'confidence': float, 'probabilities': {key: p}}."""
    if not 1 <= len(options) <= 255:
        raise ValueError("choice needs 1..255 options")
    return {"type": "choice", "instructions": instructions, "criteria": dict(options)}


def score(instructions, levels):
    """Graded level on an ordered rubric, lowest first (2..10 levels).
    Response: {'score': float, 'confidence': float, 'legend': {...}, 'probabilities': {...}}."""
    if not 2 <= len(levels) <= 10:
        raise ValueError("score needs 2..10 rubric levels, lowest first")
    return {"type": "score", "instructions": instructions, "criteria": list(levels)}


# ---- the call ----


def decide(state, questions, api_key=None, endpoint=ENDPOINT, timeout=30):
    """Send one Jev decision request. Returns the parsed response dict:
    {'answers': {name: {...}}, 'usage': {'input_tokens', 'output_tokens', 'cost'}}.
    `questions` is {name: builder_result}, e.g. {'urgent': noul('...')}.
    """
    api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENROUTER_API_KEY (see .env.example)")

    body = json.dumps({"model": MODEL, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(
        endpoint,
        data=body,
        headers={
            "Authorization": "Bearer " + api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        raise RuntimeError(
            "Jev call failed (HTTP %s). If 404, try the ALT_ENDPOINT or the "
            "typesafe_sdk. Body: %s" % (e.code, detail)
        )


# ---- tiny answer helpers (non-authoritative: return decision + confidence) ----


def answer_of(response, name):
    """Return the raw answer object for a question by name."""
    return response["answers"][name]


def confident(answer, threshold=0.8):
    """True only if the answer's confidence (or P(yes) distance from 0.5 for noul)
    clears the threshold. Keep thresholds and actions in YOUR code, not in Jev."""
    if answer["type"] == "noul":
        p = answer["noul"]
        return max(p, 1 - p) >= threshold
    return answer.get("confidence", 0.0) >= threshold


if __name__ == "__main__":
    # smoke test (needs OPENROUTER_API_KEY)
    r = decide(
        state="My card was charged twice and support has not replied in 3 days.",
        questions={
            "urgent": noul("Does this convey urgency?"),
            "team": choice(
                "Which team should handle this?",
                {
                    "billing": "Payments, invoices, refunds",
                    "technical": "Bugs, outages, integrations",
                    "sales": "Pricing, upgrades, new accounts",
                },
            ),
            "frustration": score(
                "How frustrated is the customer?", ["Calm", "Frustrated", "Very angry"]
            ),
        },
    )
    print(json.dumps(r, indent=2))
