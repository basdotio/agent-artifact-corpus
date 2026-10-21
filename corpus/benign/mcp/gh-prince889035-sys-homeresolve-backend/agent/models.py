"""Validated wire data and bounded in-memory conversation state."""

import os
import re
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

ShortText = Annotated[str, StringConstraints(strict=True, min_length=1, max_length=200, pattern=r"^[^\x00-\x1f\x7f]+$")]
SourceRef = Annotated[str, StringConstraints(strict=True, pattern=r"^data/evidence\.json#[a-z0-9-]+$", max_length=160)]


class AgentError(ValueError):
    """Safe caller-facing error; never embed raw provider/network exceptions."""


def redact(text: str) -> str:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        text = text.replace(key, "[REDACTED]")
    text = re.sub(r"\bsk-[A-Za-z0-9_-]+", "[REDACTED]", text)
    return re.sub(r'''(?i)((?:api[_ -]?key|password|passwd|secret|access[_ -]?token)\s*[:=]\s*|bearer\s+)(?:"[^"]*"|'[^']*'|\S+)''',
                  r"\1[REDACTED]", text)


class WireModel(BaseModel):
    # Extra document text cannot become executable instructions or response prose.
    model_config = ConfigDict(strict=True, extra="ignore")


class Appliance(WireModel):
    id: ShortText
    name: ShortText
    category: ShortText
    brand: ShortText
    model: ShortText
    serial: ShortText
    household: ShortText


class FindResult(WireModel):
    synthetic_demo: Literal[True]
    matches: list[Appliance] = Field(max_length=50)
    count: int = Field(ge=0, le=50)


class WarrantyDocument(WireModel):
    evidence_status: Literal["verified_demo", "missing"]
    start_date: str | None
    end_date: str | None
    source_refs: list[SourceRef] = Field(max_length=20)


class PurchaseResult(WireModel):
    synthetic_demo: Literal[True]
    appliance_id: ShortText
    evidence_status: Literal["verified_demo", "missing"]
    purchase_date: str | None
    retailer: ShortText | None
    receipt_id: ShortText | None
    source_refs: list[SourceRef] = Field(max_length=20)
    missing_information: list[Literal["purchase receipt", "purchase date", "warranty document"]] = Field(max_length=10)
    warranty_evidence: WarrantyDocument


class WarrantyResult(WireModel):
    synthetic_demo: Literal[True]
    appliance_id: ShortText
    evaluation_date: str
    status: Literal["active", "expired", "unknown"]
    claim_approval: Literal["not_determined"]
    source_refs: list[SourceRef] = Field(max_length=20)
    period_start: str | None = None
    period_end: str | None = None


class ToolCall(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")
    call_id: ShortText
    name: ShortText
    arguments: dict[str, Any]


class ResponsePlan(BaseModel):
    """A model response contract: facts are verified before safe rendering."""

    model_config = ConfigDict(strict=True, extra="forbid")
    action: Literal["report", "prepare", "clarify", "unsupported", "history"]
    proposal_id: str | None = Field(default=None, max_length=80)
    appliance_id: str | None = None
    warranty_status: Literal["active", "expired", "unknown"] | None = None
    source_refs: list[SourceRef] = Field(default_factory=list, max_length=20)


@dataclass
class ModelTurn:
    calls: list[ToolCall] = field(default_factory=list)
    final: ResponsePlan | None = None


@dataclass
class Conversation:
    household_id: str = "Demo Hearth Household"
    conversation_id: str = field(default_factory=lambda: str(uuid4()))
    selected: dict[str, Any] | None = None
    recent_messages: deque[str] = field(default_factory=lambda: deque(maxlen=8))
    evidence: dict[str, dict[str, Any]] = field(default_factory=dict)
    candidates: list[dict[str, Any]] = field(default_factory=list)
    pending_proposal_id: str | None = None
    clarification: str | None = None
    phase: str = "ready"
    busy: bool = False
    saved_history: dict[str, Any] | None = None
    execution_trace: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=64))

    def context(self, request: str, results: list[dict[str, Any]], evaluation_date: str) -> dict[str, Any]:
        return {"request": request, "recent_messages": list(self.recent_messages), "selected": self.selected,
                "candidates": self.candidates, "evidence": self.evidence, "turn_results": results,
                "household_id": self.household_id, "evaluation_date": evaluation_date}


@dataclass
class AgentReply:
    text: str
    tools: list[str] = field(default_factory=list)
    status: str = "ok"
    local_tools: list[str] = field(default_factory=list)
