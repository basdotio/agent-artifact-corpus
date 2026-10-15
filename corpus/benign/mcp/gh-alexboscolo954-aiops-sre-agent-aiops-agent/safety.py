"""Output hygiene for anything that reaches the model: redact secrets, cap size.

Tool output is untrusted (pod logs, events, alert annotations) and lands in the
model's context, so it is scrubbed and bounded before it gets there.
"""

import re

_REDACTED = "[REDACTED]"

# ponytail: regex redaction catches common token shapes, not every secret.
# The real control is not exposing secret values at all (env values and
# Secret objects are never read by the tools).
_PATTERNS = [
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
    re.compile(r"\beyJ[\w-]{10,}\.[\w-]{10,}\.[\w-]{10,}"),  # JWT
    re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"),  # AWS access key id
    re.compile(r"\b(?:sk|pk|rk)-[A-Za-z0-9_-]{16,}"),  # sk-... style API keys
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}"),  # GitHub tokens
    re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}"),  # Slack tokens
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/-]{12,}=*"),
    re.compile(
        r"(?i)((?:password|passwd|secret|token|api[_-]?key|access[_-]?key)\s*[=:]\s*)"
        r"[\"']?[^\s\"',;]{4,}"
    ),
]


def redact(text: str) -> str:
    for pattern in _PATTERNS:
        if pattern.groups:
            text = pattern.sub(lambda m: m.group(1) + _REDACTED, text)
        else:
            text = pattern.sub(_REDACTED, text)
    return text


def truncate(text: str, limit: int, keep: str = "head") -> str:
    """Cap text at `limit` chars. keep="tail" keeps the end (right for logs)."""
    if len(text) <= limit:
        return text
    cut = len(text) - limit
    marker = f"\n...[truncated {cut} chars]...\n"
    if keep == "tail":
        return marker + text[-limit:]
    return text[:limit] + marker
