import re


MAX_CLAIM_LENGTH = 500

INJECTION_PATTERNS = re.compile(
    r"""
    (
      ignore\s+(all\s+)?(previous|prior|above)\s+instructions
      |forget\s+(all\s+)?(previous|prior|above)\s+instructions
      |disregard\s+(all\s+)?(previous|prior|above)
      |you\s+are\s+now
      |act\s+as\s+(a|an)
      |system\s*:
      |developer\s*:
      |assistant\s*:
      |<\|im_start\|>
      |<\|im_end\|>
      |\#\#\#\s*system
      |return\s+only\s+verified
      |say\s+(this\s+is\s+)?verified
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


class UnsafeClaimError(ValueError):
    """Raised when a claim contains instruction-like text instead of only a checkable claim."""


def sanitize_claim(raw_claim: str) -> str:
    """Normalize a viral claim and reject obvious prompt-injection payloads."""
    claim = " ".join(raw_claim.strip().split())

    if not claim:
        raise ValueError("Claim is empty")

    if len(claim) > MAX_CLAIM_LENGTH:
        claim = claim[:MAX_CLAIM_LENGTH].rstrip()

    if INJECTION_PATTERNS.search(claim):
        raise UnsafeClaimError("Claim contains instruction-like or adversarial content")

    return claim
