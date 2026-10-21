"""Strict browser contracts; no household, provider or approval authority in chat."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.agent.models import Appliance, PurchaseResult, WarrantyResult


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ChatRequest(RequestModel):
    message: str = Field(min_length=1, max_length=2000)
    request_id: str = Field(min_length=36, max_length=36)
    conversation_id: str | None = Field(default=None, min_length=36, max_length=36)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("A request is required")
        return value.strip()

    @field_validator("request_id", "conversation_id")
    @classmethod
    def uuid_field(cls, value: str | None) -> str | None:
        if value is not None:
            UUID(value)
        return value


class ProposalRequest(RequestModel):
    conversation_id: str = Field(min_length=36, max_length=36)
    issue_description: str = Field(min_length=1, max_length=2000)

    @field_validator("issue_description")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Describe the issue")
        return value.strip()


class ApproveRequest(RequestModel):
    decision: Literal["APPROVE"]
    confirmation: Literal["APPROVE"]


class RejectRequest(RequestModel):
    decision: Literal["REJECT"]
    confirmation: Literal["REJECT"]


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    scope: Literal["local-single-user-demo"] = "local-single-user-demo"


class AppInfo(BaseModel):
    name: str = "HomeResolve"
    mode: Literal["demo", "llm", "ollama"]
    mode_label: str
    llm_verified: bool = False
    household: str
    evaluation_date: str
    csrf_token: str


class ApplianceDetail(BaseModel):
    appliance: Appliance
    purchase: PurchaseResult
    warranty: WarrantyResult


class ChatResponse(BaseModel):
    conversation_id: str
    status: Literal["ok", "error"]
    message: str
    tools: list[Literal["find_appliance", "get_purchase_evidence", "evaluate_warranty"]]
    local_tools: list[Literal["get_repair_history"]] = Field(default_factory=list)
    protocol: str | None
    selected: Appliance | None
    purchase: PurchaseResult | None
    warranty: WarrantyResult | None
    candidates: list[Appliance]
    phase: str


class Proposal(BaseModel):
    proposal_id: str
    appliance_id: str
    issue_description: str
    warranty_evaluation_snapshot: WarrantyResult
    supporting_evidence_references: list[str]
    purchase_evidence_snapshot: PurchaseResult
    status: Literal["pending", "approved", "rejected"]
    created_at: str
    updated_at: str


class RepairCase(BaseModel):
    case_id: str
    proposal_id: str
    appliance_id: str
    issue_description: str
    status: Literal["open"]
    created_at: str
    updated_at: str


class AuditEvent(BaseModel):
    event_id: int
    proposal_id: str
    case_id: str | None
    event_type: str
    event_timestamp: str
    metadata_json: dict[str, str]
