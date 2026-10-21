"""Thin client for the local Ollama HTTP generate endpoint.

Talks to Ollama at OLLAMA_URL. All errors (connection refused, timeout, non-200
status -- which now includes a 400 `exceed_context_size_error` when the prompt
is too big, and a redirect, which is never followed) are surfaced as OllamaError so callers never hang, never see a raw
requests exception, and -- with truncate:false -- never receive a silently
truncated (and therefore wrong) answer.

Model-agnostic: model / context size / think are configurable via
LOCAL_LLM_* env vars or per-call kwargs, so swapping the backend model is config,
not code. `truncate: False` is sent TOP-LEVEL (Ollama ignores it inside options),
so an oversized prompt fails loud (HTTP 400) instead of being silently cut down.
"""

import os

import requests


def _parse_think_env(raw):
    """Map LOCAL_LLM_THINK to True / False / None(omit). Default (unset) = False,
    preserving the current gemma4 thinking-model behavior. 'omit'/'none'/'null'
    drops the flag entirely for a non-thinking model that would reject it."""
    val = (raw or "").strip().lower()
    if val in ("true", "1", "yes", "on"):
        return True
    if val in ("omit", "none", "null"):
        return None
    return False


OLLAMA_URL = os.environ.get(
    "LOCAL_LLM_OLLAMA_URL", "http://localhost:11434/api/generate")
MODEL = os.environ.get("LOCAL_LLM_MODEL", "gemma4:12b-it-qat")
TIMEOUT_SECONDS = int(os.environ.get("LOCAL_LLM_TIMEOUT_SECONDS", "120"))
NUM_CTX = int(os.environ.get("LOCAL_LLM_NUM_CTX", "32768"))
THINK = _parse_think_env(os.environ.get("LOCAL_LLM_THINK", "false"))

# Default sampling options. temperature=0 makes the offload tasks (summarize /
# classify / extract) as deterministic as the backend allows, so identical
# inputs yield stable outputs run-to-run. Callers can override via 'options'.
DEFAULT_OPTIONS = {"temperature": 0}

_UNSET = object()  # distinguishes "caller passed nothing" from an explicit None


class OllamaError(RuntimeError):
    pass


def generate(prompt: str, *, options: dict | None = None, model: str | None = None,
             num_ctx: int | None = None, think=_UNSET) -> str:
    """Send a prompt to Ollama and return the generated text.

    Builds a non-streaming payload. `num_ctx` is set explicitly (default NUM_CTX)
    so behavior does not depend on the server-startup OLLAMA_CONTEXT_LENGTH, and
    `truncate: False` is sent TOP-LEVEL so an over-context prompt raises OllamaError
    (HTTP 400) instead of being silently truncated. `model` / `num_ctx` / `think`
    override the env defaults for a swapped model. Raises OllamaError on any
    transport failure (connection refused or timeout), any non-200 status, or a
    200 body that is not a JSON object. On success returns the "response" field
    (empty string if absent).
    """
    model = model or MODEL
    num_ctx = num_ctx or NUM_CTX
    think = THINK if think is _UNSET else think

    merged_options = dict(DEFAULT_OPTIONS)
    merged_options["num_ctx"] = num_ctx
    if options is not None:
        merged_options.update(options)

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "truncate": False,
        "options": merged_options,
    }
    if think is not None:
        payload["think"] = think

    try:
        # Redirects are not followed: the prompt would be re-sent to a host the
        # configured URL does not name.
        response = requests.post(OLLAMA_URL, json=payload,
                                 timeout=TIMEOUT_SECONDS, allow_redirects=False)
    except requests.exceptions.RequestException as exc:
        raise OllamaError(
            "Ollama unreachable at " + OLLAMA_URL + ": " + str(exc)
        ) from exc

    if 300 <= response.status_code < 400:
        raise OllamaError(
            "Ollama answered with a redirect (HTTP " + str(response.status_code)
            + "); redirects are not followed. Point LOCAL_LLM_OLLAMA_URL at "
            "the final address."
        )
    if response.status_code != 200:
        body = response.text[:500]
        raise OllamaError(
            "Ollama returned HTTP " + str(response.status_code) + ": " + body
        )

    # The body is left out of these messages: it is unexpected content of
    # unknown size, not a structured error worth echoing.
    try:
        data = response.json()
    except ValueError as exc:
        raise OllamaError(
            "Ollama returned HTTP 200 with a body that is not valid JSON"
        ) from exc
    if not isinstance(data, dict):
        raise OllamaError(
            "Ollama returned HTTP 200 with a JSON body that is not an object"
        )
    text = data.get("response", "")
    if not isinstance(text, str):
        raise OllamaError(
            "Ollama returned HTTP 200 with a response field that is not text"
        )
    return text
