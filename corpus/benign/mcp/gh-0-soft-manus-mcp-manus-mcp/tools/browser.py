"""Tools for `/v2/browser.*` endpoints."""

from __future__ import annotations

from manus_mcp.schemas.browser import BrowserOnlineListQuery, BrowserOnlineListResponse
from manus_mcp.tools.registry import ToolCtx, manus_tool


@manus_tool(
    name="manus_browser_online_list",
    description=(
        "List online browser clients. Use the returned client_id with manus_task_confirm_action "
        "when the agent triggers a needConnectMyBrowser waiting event. Empty list means you need "
        "to install/enable the Manus Browser Extension."
    ),
    input_schema=BrowserOnlineListQuery,
    output_schema=BrowserOnlineListResponse,
)
async def browser_online_list(q: BrowserOnlineListQuery, ctx: ToolCtx) -> BrowserOnlineListResponse:
    return await ctx.client.call(
        "GET",
        "/v2/browser.onlineList",
        response_model=BrowserOnlineListResponse,
        rate_limit_key="browser.onlineList",
    )
