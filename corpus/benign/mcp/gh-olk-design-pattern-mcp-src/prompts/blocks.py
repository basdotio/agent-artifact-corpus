"""Untrusted-block delimiters and list rendering shared by every prompt (§1.3 rule 6).

The description and everything derived from it is UNTRUSTED DATA: it is embedded ONLY inside
delimited blocks in user prompts and NEVER concatenated into a system prompt.
"""

from __future__ import annotations

from collections.abc import Sequence

#: Delimiters for untrusted, description-derived text (§1.3 rule 6). Everything between them is
#: data to classify, never instructions to follow.
UNTRUSTED_BLOCK_BEGIN = "<<<UNTRUSTED_DESCRIPTION>>>"
UNTRUSTED_BLOCK_END = "<<<END_UNTRUSTED_DESCRIPTION>>>"


def untrusted_block(content: str) -> str:
    """Wrap untrusted, description-derived content in the §1.3 rule 6 delimiters."""
    return f"{UNTRUSTED_BLOCK_BEGIN}\n{content}\n{UNTRUSTED_BLOCK_END}"


def render_list(items: Sequence[str]) -> str:
    """Dash-list rendering used inside prompt blocks; empty lists render as an explicit ``- (none)``."""
    return "\n".join(f"  - {item}" for item in items) if items else "  - (none)"
