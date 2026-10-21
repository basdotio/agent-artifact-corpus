"""Variant binding models of the §8.4 language-realization step.

``VariantSummary`` is the compact sibling-variant view carried next to ``bound_variant``;
``LanguageBinding`` is the concrete realization of one pattern application in one language.
Both mirror ``docs/result-schema.json``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from src.schemas.enums import Language, Paradigm, SupportLevel


class VariantSummary(BaseModel):
    """Compact sibling-variant summary carried next to ``bound_variant``."""

    variant_id: str
    name: str
    paradigm: Paradigm
    min_standard: str | None = None
    requires_features: list[str] = Field(default_factory=list)


class LanguageBinding(BaseModel):
    """Concrete language realization of one application (§8.4)."""

    language: Language
    support: SupportLevel
    idiom_name: str | None = None
    implementation_notes: str
    code_sketch: str | None = None
    alternative: str | None = None
    bound_variant: str | None = None
    variants: list[VariantSummary] = Field(default_factory=list)
