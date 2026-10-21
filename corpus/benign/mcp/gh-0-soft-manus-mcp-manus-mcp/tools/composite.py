"""Composite, high-level tools that orchestrate multiple raw endpoints."""

from __future__ import annotations

import asyncio
import base64
import mimetypes
import time
from pathlib import Path
from typing import Any, Literal

import httpx
from pydantic import ConfigDict, Field, model_validator

from manus_mcp.client.errors import ManusApiError
from manus_mcp.schemas.common import ManusModel, ResponseEnvelope
from manus_mcp.schemas.files import FileCreateRequest, FileCreateResponse, FileRecord
from manus_mcp.schemas.tasks import (
    AssistantMessageBody,
    ErrorMessageBody,
    StatusDetail,
    TaskListMessagesQuery,
    TaskMessage,
    TaskRecord,
)
from manus_mcp.schemas.website import (
    PublishStatus,
    WebsitePublishRequest,
    WebsiteStatusResponse,
    WebsiteVisibility,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool

# ---------------------------------------------------------------------------
# manus_file_upload
# ---------------------------------------------------------------------------


class FileUploadSource(ManusModel):
    """One of path / base64 / url must be set."""

    path: str | None = Field(
        default=None, description="Absolute or relative local path to read bytes from"
    )
    base64: str | None = Field(default=None, description="Base64-encoded file bytes")
    url: str | None = Field(
        default=None, description="Public URL to download bytes from before uploading"
    )

    @model_validator(mode="after")
    def _one_of(self) -> FileUploadSource:
        provided = [v is not None for v in (self.path, self.base64, self.url)]
        if sum(provided) != 1:
            raise ValueError("Exactly one of path / base64 / url must be provided")
        return self


class FileUploadRequest(ManusModel):
    source: FileUploadSource
    filename: str | None = Field(
        default=None,
        description="Target filename (extension determines type). Derived from path/url if omitted.",
    )
    content_type: str | None = Field(
        default=None,
        description="MIME type for the presigned PUT. Auto-detected from filename if omitted.",
    )
    wait_for_processing: bool = Field(
        default=True,
        description="Poll file.detail until status=uploaded (or fail). If false, return immediately after PUT.",
    )
    wait_timeout_sec: float = Field(default=60.0, ge=1.0, le=180.0)
    poll_interval_sec: float = Field(default=2.0, ge=0.05, le=10.0)


class FileUploadResponse(ResponseEnvelope):
    file: FileRecord
    upload_url: str
    upload_expires_at: int | None = None
    uploaded: bool
    elapsed_sec: float


async def _read_source(src: FileUploadSource) -> tuple[bytes, str]:
    """Return (bytes, suggested_filename)."""
    if src.path is not None:
        p = Path(src.path)
        if not p.is_file():
            raise ManusApiError(
                code="invalid_argument",
                message=f"File not found: {src.path}",
            )
        return p.read_bytes(), p.name
    if src.base64 is not None:
        try:
            # Default extension is .txt because Manus blocks .bin server-side.
            return base64.b64decode(src.base64, validate=True), "upload.txt"
        except Exception as e:
            raise ManusApiError(
                code="invalid_argument",
                message=f"Invalid base64: {e}",
            ) from e
    if src.url is not None:
        async with httpx.AsyncClient(timeout=60.0) as raw:
            resp = await raw.get(src.url)
            if resp.status_code >= 300:
                raise ManusApiError(
                    code=f"source_http_{resp.status_code}",
                    message=f"Failed to fetch source URL: {resp.status_code}",
                    http_status=resp.status_code,
                )
            suggested = src.url.rstrip("/").rsplit("/", 1)[-1] or "download.bin"
            return resp.content, suggested
    raise ManusApiError(code="invalid_argument", message="No source provided")


def _guess_content_type(filename: str, override: str | None) -> str:
    if override:
        return override
    guess, _ = mimetypes.guess_type(filename)
    return guess or "application/octet-stream"


@manus_tool(
    name="manus_file_upload",
    description=(
        "Upload a file end-to-end: create presigned URL, PUT bytes, and (by default) wait until "
        "status=uploaded. Accepts one of: local path, base64-encoded bytes, or a public URL to "
        "fetch first. Returns the final file record ready to reference as file_id in tasks."
    ),
    input_schema=FileUploadRequest,
    output_schema=FileUploadResponse,
)
async def file_upload(req: FileUploadRequest, ctx: ToolCtx) -> FileUploadResponse:
    started = time.monotonic()
    data, suggested_name = await _read_source(req.source)
    filename = req.filename or suggested_name or "upload.txt"
    content_type = _guess_content_type(filename, req.content_type)

    try:
        presign: FileCreateResponse = await ctx.client.call(
            "POST",
            "/v2/file.upload",
            json_body=FileCreateRequest(filename=filename),
            response_model=FileCreateResponse,
            rate_limit_key="file.upload",
        )
    except ManusApiError as e:
        if e.code == "invalid_argument" and "blocked file type" in e.message.lower():
            raise ManusApiError(
                code=e.code,
                message=(
                    f"{e.message} (filename={filename!r}). Manus blocks certain "
                    "extensions; known-good: .txt, .pdf, .csv, .png, .jpg, .docx, "
                    ".xlsx, .json, .md. Pass filename= explicitly."
                ),
                http_status=e.http_status,
                request_id=e.request_id,
            ) from e
        raise
    await ctx.client.put_raw(presign.upload_url, data, content_type)

    file_record = presign.file
    uploaded = False
    if req.wait_for_processing:
        deadline = time.monotonic() + req.wait_timeout_sec
        from manus_mcp.schemas.files import FileDetailResponse

        while True:
            detail: FileDetailResponse = await ctx.client.call(
                "GET",
                "/v2/file.detail",
                params={"file_id": file_record.id},
                response_model=FileDetailResponse,
                rate_limit_key="file.detail",
            )
            file_record = detail.file
            status = file_record.status
            if status == "uploaded":
                uploaded = True
                break
            if status in ("deleted", "error"):
                raise ManusApiError(
                    code="upload_failed",
                    message=file_record.error_message or f"File status={status}",
                )
            if time.monotonic() >= deadline:
                raise ManusApiError(
                    code="upload_timeout",
                    message=f"File still status={status} after {req.wait_timeout_sec}s",
                )
            await asyncio.sleep(req.poll_interval_sec)
    else:
        uploaded = False

    return FileUploadResponse(
        request_id=presign.request_id,
        file=file_record,
        upload_url=presign.upload_url,
        upload_expires_at=presign.upload_expires_at,
        uploaded=uploaded,
        elapsed_sec=round(time.monotonic() - started, 3),
    )


# ---------------------------------------------------------------------------
# manus_task_wait
# ---------------------------------------------------------------------------


TerminalState = Literal["stopped", "waiting", "error"]


class TaskWaitRequest(ManusModel):
    task_id: str
    timeout_sec: float = Field(default=300.0, ge=1.0, le=3600.0)
    poll_interval_sec: float = Field(default=3.0, ge=0.05, le=60.0)
    since_message_id: str | None = Field(
        default=None,
        description="If set, only return messages newer than this ID in new_messages.",
    )
    include_verbose: bool = Field(
        default=False,
        description="Pass verbose=true to task.listMessages (adds tool_used/plan/explanation).",
    )
    include_assistant_content_only: bool = Field(
        default=False,
        description="If true, new_messages only contains user/assistant/error/status events.",
    )


class TaskWaitResponse(ResponseEnvelope):
    model_config = ConfigDict(extra="allow")

    terminal_state: TerminalState
    task: TaskRecord
    last_status_update: StatusDetail | None = None
    waiting_for_event_type: str | None = None
    waiting_for_event_id: str | None = None
    confirm_input_schema: dict[str, Any] | None = None
    new_messages: list[TaskMessage]
    last_assistant_message: AssistantMessageBody | None = None
    last_error_message: ErrorMessageBody | None = None
    elapsed_sec: float


async def _fetch_messages_asc(
    ctx: ToolCtx,
    task_id: str,
    since_id: str | None,
    verbose: bool,
) -> list[TaskMessage]:
    """Fetch all messages newer than since_id in chronological order."""
    from manus_mcp.schemas.tasks import TaskListMessagesResponse

    collected: list[TaskMessage] = []
    cursor: str | None = None
    stop = False
    while not stop:
        q = TaskListMessagesQuery(
            task_id=task_id,
            limit=100,
            cursor=cursor,
            order="desc",
            verbose=verbose,
        )
        resp: TaskListMessagesResponse = await ctx.client.call(
            "GET",
            "/v2/task.listMessages",
            params=q.model_dump(exclude_none=True),
            response_model=TaskListMessagesResponse,
            rate_limit_key="task.listMessages",
        )
        for msg in resp.messages:
            if since_id is not None and msg.id == since_id:
                stop = True
                break
            collected.append(msg)
        if stop:
            break
        if not resp.has_more or not resp.next_cursor:
            break
        cursor = resp.next_cursor
    collected.reverse()  # chronological
    return collected


@manus_tool(
    name="manus_task_wait",
    description=(
        "Poll a task until it reaches a terminal state (stopped / waiting / error) or times out. "
        "Returns the final status, new messages, and — if waiting — the event_id and input schema "
        "needed for manus_task_confirm_action or the body needed for manus_task_send_message."
    ),
    input_schema=TaskWaitRequest,
    output_schema=TaskWaitResponse,
)
async def task_wait(req: TaskWaitRequest, ctx: ToolCtx) -> TaskWaitResponse:
    from manus_mcp.schemas.tasks import TaskDetailResponse

    started = time.monotonic()
    deadline = started + req.timeout_sec
    terminal: TerminalState | None = None
    last_task: TaskRecord | None = None
    # Tolerate brief read-after-write 404 right after task.create.
    consecutive_not_found = 0
    not_found_grace = 15  # ~30s @ default 2s interval — Manus has notable read-after-write

    while True:
        try:
            detail: TaskDetailResponse = await ctx.client.call(
                "GET",
                "/v2/task.detail",
                params={"task_id": req.task_id},
                response_model=TaskDetailResponse,
                rate_limit_key="task.detail",
            )
            consecutive_not_found = 0
        except ManusApiError as e:
            if e.code == "not_found" and consecutive_not_found < not_found_grace:
                consecutive_not_found += 1
                if time.monotonic() >= deadline:
                    raise
                await asyncio.sleep(req.poll_interval_sec)
                continue
            raise
        last_task = detail.task
        if detail.task.status in ("stopped", "waiting", "error"):
            terminal = detail.task.status
            break
        if time.monotonic() >= deadline:
            raise ManusApiError(
                code="task_wait_timeout",
                message=(
                    f"Task still {detail.task.status} after {req.timeout_sec}s "
                    f"(task_id={req.task_id})"
                ),
            )
        await asyncio.sleep(req.poll_interval_sec)

    assert terminal is not None and last_task is not None
    new_messages = await _fetch_messages_asc(
        ctx, req.task_id, req.since_message_id, req.include_verbose
    )
    if req.include_assistant_content_only:
        keep = {"user_message", "assistant_message", "error_message", "status_update"}
        new_messages = [m for m in new_messages if m.type in keep]

    last_status: StatusDetail | None = None
    waiting_type: str | None = None
    waiting_id: str | None = None
    waiting_schema: dict[str, Any] | None = None
    last_assistant: AssistantMessageBody | None = None
    last_error: ErrorMessageBody | None = None

    for msg in reversed(new_messages):
        if msg.type == "status_update" and msg.status_update is not None and last_status is None:
            last_status = msg.status_update.status_detail
            if msg.status_update.status_detail is not None:
                waiting_type = msg.status_update.status_detail.waiting_for_event_type
                waiting_id = msg.status_update.status_detail.waiting_for_event_id
                waiting_schema = msg.status_update.status_detail.confirm_input_schema
        elif (
            msg.type == "assistant_message"
            and msg.assistant_message is not None
            and last_assistant is None
        ):
            last_assistant = msg.assistant_message
        elif msg.type == "error_message" and msg.error_message is not None and last_error is None:
            last_error = msg.error_message

    return TaskWaitResponse(
        terminal_state=terminal,
        task=last_task,
        last_status_update=last_status,
        waiting_for_event_type=waiting_type,
        waiting_for_event_id=waiting_id,
        confirm_input_schema=waiting_schema,
        new_messages=new_messages,
        last_assistant_message=last_assistant,
        last_error_message=last_error,
        elapsed_sec=round(time.monotonic() - started, 3),
    )


# ---------------------------------------------------------------------------
# manus_website_publish_and_wait
# ---------------------------------------------------------------------------


class WebsitePublishAndWaitRequest(ManusModel):
    task_id: str | None = None
    website_id: str | None = None
    visibility: WebsiteVisibility | None = None
    timeout_sec: float = Field(default=300.0, ge=1.0, le=1800.0)
    poll_interval_sec: float = Field(default=3.0, ge=0.05, le=60.0)

    @model_validator(mode="after")
    def _one_of(self) -> WebsitePublishAndWaitRequest:
        if (self.task_id is None) == (self.website_id is None):
            raise ValueError("Exactly one of task_id or website_id must be provided")
        return self


class WebsitePublishAndWaitResponse(ResponseEnvelope):
    website_id: str
    deployed_version_id: str
    final_status: PublishStatus
    status: WebsiteStatusResponse
    elapsed_sec: float


@manus_tool(
    name="manus_website_publish_and_wait",
    description=(
        "Deploy the latest checkpoint and poll until the website is published or the deployment "
        "fails. Returns the final website status with site URLs."
    ),
    input_schema=WebsitePublishAndWaitRequest,
    output_schema=WebsitePublishAndWaitResponse,
)
async def website_publish_and_wait(
    req: WebsitePublishAndWaitRequest, ctx: ToolCtx
) -> WebsitePublishAndWaitResponse:
    from manus_mcp.schemas.website import WebsitePublishResponse

    started = time.monotonic()
    publish_req = WebsitePublishRequest(
        task_id=req.task_id,
        website_id=req.website_id,
        visibility=req.visibility,
    )
    publish: WebsitePublishResponse = await ctx.client.call(
        "POST",
        "/v2/website.publish",
        json_body=publish_req,
        response_model=WebsitePublishResponse,
        rate_limit_key="website.publish",
    )

    website_id = publish.website_id
    deadline = started + req.timeout_sec
    last_status: WebsiteStatusResponse | None = None
    while True:
        status: WebsiteStatusResponse = await ctx.client.call(
            "GET",
            "/v2/website.status",
            params={"website_id": website_id},
            response_model=WebsiteStatusResponse,
            rate_limit_key="website.status",
        )
        last_status = status
        if status.publish_status in ("published", "failed"):
            break
        if time.monotonic() >= deadline:
            raise ManusApiError(
                code="publish_timeout",
                message=(
                    f"Website still {status.publish_status} after {req.timeout_sec}s "
                    f"(website_id={website_id})"
                ),
            )
        await asyncio.sleep(req.poll_interval_sec)

    assert last_status is not None
    return WebsitePublishAndWaitResponse(
        website_id=website_id,
        deployed_version_id=publish.version_id,
        final_status=last_status.publish_status,
        status=last_status,
        elapsed_sec=round(time.monotonic() - started, 3),
    )
