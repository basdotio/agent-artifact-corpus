"""One official-SDK MCP catalogue for browser reads and bounded test delivery."""
import asyncio
import json
import os
import time

from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import CallToolResult, GetPromptResult, Prompt, PromptMessage, TextContent, Tool, ToolAnnotations

from . import read_protocol as read, write_protocol as write
from .. import __version__

GUIDANCE = """These are agent-mediated Garmin browser connectivity tools, not a training coach.
The MCP server and SDK client run on the agent computer over local stdio. Neither
controls a browser, authenticates to Garmin's API, nor calls a model API. A parent
agent must use its supported CUA browser and existing user authorization; browser
operations connect to Garmin. No public MCP service or personal-computer token
transfer is required. Native platform registration and VM durability are separate.

read_workout creates one isolated expiring request for a specifically authorized
positive workout ID. The parent uses its own supported browser tool and must freshly observe that workout after request
creation, then publish only selected fields for the matching request and ID. Stop
on login, MFA, CAPTCHA, permission denial or ambiguity. Do not infer missing sport,
targets, durations or evidence from examples. Unknown values remain null/unknown.
Dot CUA can use the packaged worker; another host submits its own selected report
with record-read as documented in the packaged Skill. A report is parent-provided,
not an independent proof of browser access. The packaged read worker does not
navigate to a calendar or request device sync.

preview_test saves an exact local fixed 20-minute running connectivity proposal:
300/600/300 seconds, all NoTarget. Explicit tool-owned name and calendar date are
required. Show the saved proposal to the owner. Its ID and exact-byte SHA are
integrity identifiers, not approval. Only an actual current owner reply approving
that exact proposal permits a trusted outside-MCP operator confirmation record.
There is no MCP approve tool. Same-UID file trust is not a human signature.

apply_test queues that existing exact proposal once after checking confirmation.
A pending queue is not a Garmin write. Before any possible UI mutation, the trusted
parent must claim execution using the local helper and a fresh own-account
fingerprint matching the outside-MCP confirmation, recheck current authorization,
then create only the new named test and schedule only that
workout on the exact date. Stop on duplicate name or ambiguity. Never edit/delete
existing workouts, send to a device, log in or extract browser cookies/credentials.
No write selectors or automatic browser write implementation are supplied.

After actual UI readback, the outside-MCP parent may append bounded raw UI workout,
calendar and account-fingerprint observations. Repeating apply reads status without
redispatch. Only
exact matching selected evidence yields browser_observed_scheduled. This means
agent-reported UI evidence, not independent attestation, API authentication or watch
receipt. Partial/uncertain writes require read-only reconciliation, never automatic
replay. Preserve original claims, requests, journals and receipts. Never label an
offline fixture as live data. Private selected evidence stays outside source/Git;
do not retain raw HTML, provider bodies, credentials or unrelated health data.
"""
server = Server("Garmin Agent Tools browser", version=__version__, instructions=GUIDANCE)


@server.list_tools()
async def catalogue():
    return [
        Tool(name="read_workout", description="Read one authorized workout through a fresh parent-CUA browser observation; isolated request, positive ID, unknowns preserved. No API login or provider write.",
             inputSchema=read.ReadInput.model_json_schema(), outputSchema=read.ReadResult.model_json_schema(),
             annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=False, openWorldHint=True)),
        Tool(name="preview_test", description="Save an exact local 20-minute NoTarget running connectivity test proposal with explicit tool-owned name/date. No approval or Garmin write.",
             inputSchema=write.PreviewInput.model_json_schema(),
             annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=False, openWorldHint=False)),
        Tool(name="apply_test", description="Queue one existing exact preview only after outside-MCP owner confirmation, or read its delivery evidence without redispatch. Parent CUA performs approved external effects. A queue is pending; browser_observed_scheduled is agent-reported UI evidence, never watch/API-authentication proof.",
             inputSchema=write.ApplyInput.model_json_schema(),
             annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=True)),
    ]


@server.list_prompts()
async def prompts():
    return [Prompt(name="browser_workflow", description="Local stdio, supported parent browser, exact approval and observed delivery boundaries.", arguments=[])]


@server.get_prompt()
async def prompt(name, arguments=None):
    if name != "browser_workflow" or arguments:
        raise ValueError("invalid_prompt")
    return GetPromptResult(messages=[PromptMessage(role="user", content=TextContent(type="text", text=GUIDANCE))])


def error(code):
    return CallToolResult(isError=True, content=[TextContent(type="text", text=code)])


@server.call_tool(validate_input=False)
async def call_tool(name, arguments):
    try:
        if name in ("preview_test", "apply_test"):
            value = (write.preview_test if name == "preview_test" else write.apply_test)(write.PRIVATE, arguments)
            return CallToolResult(structuredContent=value, content=[TextContent(type="text", text=json.dumps(value))])
        if name != "read_workout":
            return error("unknown_tool")
        args = read.ReadInput.model_validate(arguments)
        # The supported SDK caller announces these private manifests. A direct
        # stdio host needs its own parent dispatcher; this is not a native plugin.
        run = read.create_run()
        request, directory = read.create_request(run, args.workout_id)
        deadline = time.monotonic() + read.MAX_WAIT_SECONDS
        while time.monotonic() < deadline:
            try:
                raw = read.read_private_json(directory / "response.json")
            except FileNotFoundError:
                await asyncio.sleep(min(0.2, max(0, deadline - time.monotonic())))
                continue
            selected = read.validate_response(raw, request)
            value = read.ReadResult(**selected.model_dump()).model_dump(mode="json")
            return CallToolResult(structuredContent=value, content=[TextContent(type="text", text=json.dumps(value))])
        return error("browser_observation_timeout")
    except Exception:
        return error("invalid_or_blocked_browser_request; no automatic retry")


async def run_async():
    async with stdio_server() as (incoming, outgoing):
        await server.run(incoming, outgoing, server.create_initialization_options())


def run():
    asyncio.run(run_async())
