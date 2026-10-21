"""Prompt content for the four prompted call kinds (§3.1).

Modules:
    blocks: untrusted-block delimiters and dash-list rendering (§1.3 rule 6).
    system: the system prompts — ANALYZE_SYSTEM_PROMPT, WEIGHTS_BATCH_SYSTEM_PROMPT,
            GENERATE_SYSTEM_PROMPT, EVALUATE_SYSTEM_PROMPT.
    library: PromptLibrary — the per-call system/user prompt builders.
"""

from src.prompts.blocks import UNTRUSTED_BLOCK_BEGIN, UNTRUSTED_BLOCK_END, render_list, untrusted_block
from src.prompts.library import PromptLibrary
from src.prompts.system import (
    ANALYZE_SYSTEM_PROMPT,
    EVALUATE_SYSTEM_PROMPT,
    GENERATE_SYSTEM_PROMPT,
    WEIGHTS_BATCH_SYSTEM_PROMPT,
)

__all__ = [
    "ANALYZE_SYSTEM_PROMPT",
    "EVALUATE_SYSTEM_PROMPT",
    "GENERATE_SYSTEM_PROMPT",
    "UNTRUSTED_BLOCK_BEGIN",
    "UNTRUSTED_BLOCK_END",
    "WEIGHTS_BATCH_SYSTEM_PROMPT",
    "PromptLibrary",
    "render_list",
    "untrusted_block",
]
