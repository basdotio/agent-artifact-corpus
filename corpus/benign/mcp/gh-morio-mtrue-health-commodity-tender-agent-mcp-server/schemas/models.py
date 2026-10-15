from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Citation(StrictModel):
    document_id: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    page: int = Field(ge=1)
    section: str = ""
    quote: str = Field(min_length=1)
    bbox: list[float] | None = None


class Criterion(StrictModel):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,40}$")
    stage: Literal["preliminary", "technical", "financial", "due_diligence"]
    wording: str = Field(min_length=1)
    mandatory: bool = True
    weight: Decimal | None = Field(default=None, ge=0, le=100)
    required_evidence: str
    method: Literal["present", "exact", "minimum", "expiry", "manual", "arithmetic"]
    field: str = ""
    expected: str = ""
    source: Citation
    supersedes: str | None = None
    active: bool = True


class Plan(StrictModel):
    id: str
    revision: int = Field(ge=1)
    criteria: list[Criterion] = Field(min_length=1, max_length=200)
    extraction_mode: str
    warnings: list[str] = Field(default_factory=list)
    locked: bool = False
    digest: str = ""
    approved_by: str | None = None
    approved_at: str | None = None

    @model_validator(mode="after")
    def unique_ids(self):
        ids = [c.id for c in self.criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("Criterion IDs must be unique")
        if not any(c.active for c in self.criteria):
            raise ValueError("Plan must contain an active criterion")
        if any(c.weight is not None for c in self.criteria):
            raise ValueError("Weighted scoring is not supported by this MVP; use manual review")
        return self


class ProductLine(StrictModel):
    item_id: str
    generic: str
    strength: str
    dosage_form: str
    base_unit: str
    pack_size: Decimal = Field(gt=0)
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    extended_price: Decimal = Field(ge=0)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    registration_number: str = ""
    registration_expiry: date | None = None
    shelf_life_months: Decimal | None = Field(default=None, ge=0)
    storage: str = ""


class Finding(StrictModel):
    id: str
    bidder_id: str
    criterion_id: str | None = None
    category: str
    status: Literal["SUPPORTED", "UNSUPPORTED", "AMBIGUOUS", "NOT_APPLICABLE", "UNRESOLVED"]
    claim: str
    citations: list[Citation] = Field(min_length=1)
    calculation: dict | None = None
    reviewer_action: str = "Review evidence before recording a committee decision."


class ApprovalRequest(StrictModel):
    reviewer: str = Field(min_length=2, max_length=100)
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    confirmed: Literal[True]
    note: str = Field(default="", max_length=2000)

    @field_validator("reviewer")
    @classmethod
    def named_reviewer(cls, value):
        value = value.strip()
        if len(value) < 2:
            raise ValueError("A named human reviewer is required")
        return value


class InputDocument(StrictModel):
    name: str = Field(min_length=1, max_length=150)
    kind: Literal["tender", "addendum", "bid"]
    content_base64: str
    bidder_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_-]{1,40}$")
    synthetic: bool = True
    source_url: str | None = None
    supersedes_document: str | None = None

    @model_validator(mode="after")
    def document_role(self):
        if self.kind != "bid" and self.bidder_id is not None:
            raise ValueError("Tender and addendum documents cannot supply bidder evidence")
        return self


class CaseRequest(StrictModel):
    name: str = Field(min_length=1, max_length=150)
    operator: str = Field(min_length=2, max_length=100)
    closed_on: date
    closure_source: str = Field(min_length=1)
    documents: list[InputDocument] = Field(min_length=2, max_length=50)
