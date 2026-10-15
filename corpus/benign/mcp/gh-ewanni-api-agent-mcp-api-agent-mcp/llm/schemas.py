from typing import Literal

from pydantic import BaseModel, Field


class HypothesisResult(BaseModel):
    status: Literal["confirmed", "refuted", "inconclusive"]
    confidence: float = Field(ge=0.0, le=1.0)
    key_findings: list[str] = Field(max_length=5)
    evidence_or_code: str | None = None


class Proposal(BaseModel):
    agent: str
    summary: str
    content: str


class Critique(BaseModel):
    agent: str
    strengths: list[str] = Field(default_factory=list, max_length=5)
    concerns: list[str] = Field(default_factory=list, max_length=8)
    questions: list[str] = Field(default_factory=list, max_length=5)


class Verdict(BaseModel):
    """Judge output; final_answer is required even when consensus is absent."""

    verdict: Literal["consensus", "no_consensus"]
    confidence: float = Field(ge=0.0, le=1.0)
    winner: str | None = None
    final_answer: str = Field(min_length=1)
    unresolved: list[str] = Field(default_factory=list)
    rationale: str
