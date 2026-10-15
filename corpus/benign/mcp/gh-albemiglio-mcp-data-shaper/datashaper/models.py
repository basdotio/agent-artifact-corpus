"""
datashaper.models
==============

Pydantic models used as the structured-output contract between mcp-data-shaper and
every LLM provider.

``CorrectedRow`` is the unit of change: only rows whose label differs from
the original are returned by the LLM.  ``BatchOutput`` wraps a list of them.

Both models are intentionally shallow and provider-agnostic — they translate
directly into a JSON schema that is sent to the LLM via ``response_format``
(OpenAI) or ``response_schema`` (Gemini).  The ``Field`` descriptions are
therefore part of the prompt surface, not just documentation.
"""

from __future__ import annotations

from typing import TypeVar

from pydantic import BaseModel, Field


class CorrectedRow(BaseModel):
    id: str = Field(description="Row ID — exact string copied from the input item.")
    corrected_label: str = Field(description="The new, corrected label as a plain string.")
    original_label: str = Field(description="The original label — copy it verbatim from the input.")
    reasoning: str = Field(description="One-sentence explanation of what changed and why.")


class BatchOutput(BaseModel):
    corrected_rows: list[CorrectedRow] = Field(
        description=(
            "Only rows where the label must change. "
            "Return an empty list if every label in the batch is already correct."
        )
    )


# Generic TypeVar bound to BaseModel — used by LLMClient.parse_structured_output
T = TypeVar("T", bound=BaseModel)
