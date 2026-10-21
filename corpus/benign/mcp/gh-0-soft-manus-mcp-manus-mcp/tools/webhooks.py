"""Tools for `/v2/webhook.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.webhooks import (
    WebhookCreateRequest,
    WebhookCreateResponse,
    WebhookDeleteRequest,
    WebhookDeleteResponse,
    WebhookListQuery,
    WebhookListResponse,
    WebhookPublicKeyQuery,
    WebhookPublicKeyResponse,
)
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_webhook_create",
    description=(
        "Register an HTTPS webhook URL to receive task_created and task_stopped events. "
        "Manus sends a test request before activation; endpoint must return 2xx within 10 seconds."
    ),
    input_schema=WebhookCreateRequest,
    output_schema=WebhookCreateResponse,
)
async def webhook_create(req: WebhookCreateRequest, ctx: ToolCtx) -> WebhookCreateResponse:
    return await ctx.client.call(
        "POST",
        "/v2/webhook.create",
        json_body=req,
        response_model=WebhookCreateResponse,
        rate_limit_key="webhook.create",
    )


@manus_tool(
    name="manus_webhook_list",
    description="List all registered webhooks.",
    input_schema=WebhookListQuery,
    output_schema=WebhookListResponse,
)
async def webhook_list(q: WebhookListQuery, ctx: ToolCtx) -> WebhookListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/webhook.list",
        response_model=WebhookListResponse,
        rate_limit_key="webhook.list",
    )


@manus_tool(
    name="manus_webhook_delete",
    description="Delete a webhook. The endpoint will stop receiving notifications immediately.",
    input_schema=WebhookDeleteRequest,
    output_schema=WebhookDeleteResponse,
)
async def webhook_delete(req: WebhookDeleteRequest, ctx: ToolCtx) -> WebhookDeleteResponse:
    return await ctx.client.call(
        "POST",
        "/v2/webhook.delete",
        json_body=req,
        response_model=WebhookDeleteResponse,
        rate_limit_key="webhook.delete",
    )


@manus_tool(
    name="manus_webhook_public_key",
    description=(
        "Get the RSA public key used to sign webhook deliveries. Cache this (1 hour recommended)."
    ),
    input_schema=WebhookPublicKeyQuery,
    output_schema=WebhookPublicKeyResponse,
)
async def webhook_public_key(q: WebhookPublicKeyQuery, ctx: ToolCtx) -> WebhookPublicKeyResponse:
    return await ctx.client.call(
        "GET",
        "/v2/webhook.publicKey",
        response_model=WebhookPublicKeyResponse,
        rate_limit_key="webhook.publicKey",
    )
