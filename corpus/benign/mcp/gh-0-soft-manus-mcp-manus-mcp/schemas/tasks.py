"""Schemas for `/v2/task.*` endpoints."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import ConfigDict, Field

from manus_mcp.schemas.common import IntField, ManusModel, ResponseEnvelope, UnixSeconds

TaskStatus = Literal["running", "stopped", "waiting", "error"]
TaskType = Literal["standard", "project", "agent_subtask"]
ShareVisibility = Literal["private", "team", "public"]
AgentProfile = Literal["manus-1.6", "manus-1.6-lite", "manus-1.6-max"]
TaskListScope = Literal["all", "standard", "project", "agent_subtask"]
Order = Literal["asc", "desc"]
SlidesFormat = Literal["html", "pptx"]


# ----- Content parts used in message.content -----


class TextPart(ManusModel):
    type: Literal["text"]
    text: str


class FilePart(ManusModel):
    type: Literal["file"]
    file_id: str | None = None
    file_url: str | None = None
    file_data: str | None = Field(default=None, description="Base64-encoded bytes")


class VoicePart(ManusModel):
    type: Literal["voice"]
    file_id: str | None = None
    file_url: str | None = None


ContentPart = TextPart | FilePart | VoicePart


class MessageBlock(ManusModel):
    content: str | list[ContentPart]
    connectors: list[str] | None = None
    enable_skills: list[str] | None = None
    force_skills: list[str] | None = None


# ----- task.create -----


class TaskCreateRequest(ManusModel):
    message: MessageBlock
    project_id: str | None = None
    locale: str | None = None
    interactive_mode: bool | None = None
    hide_in_task_list: bool | None = None
    share_visibility: ShareVisibility | None = None
    agent_profile: AgentProfile | None = None
    title: str | None = None


class TaskCreateResponse(ResponseEnvelope):
    task_id: str
    task_title: str | None = None
    task_url: str | None = None
    share_url: str | None = None
    share_visibility: ShareVisibility | None = None


# ----- task.detail -----


class CreatedByApiKey(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str | None = None
    name: str | None = None


class TaskRecord(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    status: TaskStatus
    created_at: UnixSeconds
    updated_at: UnixSeconds
    task_type: TaskType | None = None
    share_visibility: ShareVisibility | None = None
    title: str | None = None
    credit_usage: IntField | None = None
    task_url: str | None = None
    created_by_api_key: CreatedByApiKey | None = None


class TaskDetailQuery(ManusModel):
    task_id: str


class TaskDetailResponse(ResponseEnvelope):
    task: TaskRecord


# ----- task.list -----


class TaskListQuery(ManusModel):
    limit: int | None = Field(default=None, ge=1, le=100)
    cursor: str | None = None
    order: Order | None = None
    scope: TaskListScope | None = None
    agent_id: str | None = None
    project_id: str | None = None


class TaskListResponse(ResponseEnvelope):
    data: list[TaskRecord] = []
    has_more: bool | None = None
    next_cursor: str | None = None


# ----- task.update -----


class TaskUpdateRequest(ManusModel):
    task_id: str
    title: str | None = None
    share_visibility: ShareVisibility | None = None
    enable_visible_in_task_list: bool | None = None


class TaskUpdateResponse(ResponseEnvelope):
    task_id: str
    task_title: str | None = None
    task_url: str | None = None
    share_url: str | None = None
    share_visibility: ShareVisibility | None = None


# ----- task.stop -----


class TaskStopRequest(ManusModel):
    task_id: str


class TaskStopResponse(ResponseEnvelope):
    pass


# ----- task.delete -----


class TaskDeleteRequest(ManusModel):
    task_id: str


class TaskDeleteResponse(ResponseEnvelope):
    id: str | None = None
    deleted: bool | None = None


# ----- task.sendMessage -----


class TaskSendMessageRequest(ManusModel):
    task_id: str
    message: MessageBlock


class TaskSendMessageResponse(ResponseEnvelope):
    task_id: str


# ----- task.listMessages -----


class Attachment(ManusModel):
    model_config = ConfigDict(extra="allow")
    type: str | None = None
    filename: str | None = None
    url: str | None = None
    content_type: str | None = None


class UserMessageBody(ManusModel):
    model_config = ConfigDict(extra="allow")
    content: str | None = None
    message_type: str | None = None
    attachments: list[Attachment] | None = None


class AssistantMessageBody(ManusModel):
    model_config = ConfigDict(extra="allow")
    content: str | None = None
    attachments: list[Attachment] | None = None


class ErrorMessageBody(ManusModel):
    model_config = ConfigDict(extra="allow")
    error_type: str | None = None
    content: str | None = None


class StatusDetail(ManusModel):
    model_config = ConfigDict(extra="allow")
    waiting_for_event_id: str | None = None
    waiting_for_event_type: str | None = None
    waiting_description: str | None = None
    confirm_input_schema: dict[str, Any] | None = None


class StatusUpdateBody(ManusModel):
    model_config = ConfigDict(extra="allow")
    agent_status: TaskStatus | None = None
    status_detail: StatusDetail | None = None
    brief: str | None = None
    description: str | None = None


class ToolUsedBody(ManusModel):
    model_config = ConfigDict(extra="allow")
    tool: str | None = None
    action_id: str | None = None
    status: str | None = None
    brief: str | None = None
    description: str | None = None
    message: dict[str, Any] | None = None


class PlanStep(ManusModel):
    model_config = ConfigDict(extra="allow")
    status: str | None = None
    title: str | None = None
    started_at: UnixSeconds | None = None
    end_at: UnixSeconds | None = None


class PlanUpdateBody(ManusModel):
    steps: list[PlanStep] | None = None


class NewPlanStepBody(ManusModel):
    step_id: str | None = None
    title: str | None = None


class ExplanationBody(ManusModel):
    content: str | None = None


class TaskMessage(ManusModel):
    model_config = ConfigDict(extra="allow")
    id: str
    type: str
    timestamp: UnixSeconds | None = None
    user_message: UserMessageBody | None = None
    assistant_message: AssistantMessageBody | None = None
    error_message: ErrorMessageBody | None = None
    status_update: StatusUpdateBody | None = None
    tool_used: ToolUsedBody | None = None
    plan_update: PlanUpdateBody | None = None
    new_plan_step: NewPlanStepBody | None = None
    explanation: ExplanationBody | None = None


class TaskListMessagesQuery(ManusModel):
    task_id: str
    limit: int | None = Field(default=None, ge=1, le=200)
    cursor: str | None = None
    order: Order | None = None
    verbose: bool | None = None
    slides_format: SlidesFormat | None = None


class TaskListMessagesResponse(ResponseEnvelope):
    task_id: str
    messages: list[TaskMessage] = []
    has_more: bool | None = None
    next_cursor: str | None = None


# ----- task.confirmAction -----


class TaskConfirmActionRequest(ManusModel):
    task_id: str
    event_id: str
    input: dict[str, Any] | None = None


class TaskConfirmActionResponse(ResponseEnvelope):
    task_id: str
    confirmed: bool | None = None
