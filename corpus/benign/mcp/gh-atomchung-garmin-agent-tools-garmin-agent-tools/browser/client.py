"""SDK invocation prints actual guidance/schema before its single MCP act."""
import asyncio
import json
import os
import sys
import uuid
from datetime import timedelta
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import read_protocol as read, write_protocol as write
from .server import GUIDANCE, catalogue
from .state import ensure_state_root


async def invoke(mode, *, workout_id=None, name=None, date=None, preview_id=None, proposal_sha256=None):
    home = ensure_state_root()
    runtime = write.runtime(write.PRIVATE)
    run_id = uuid.uuid4().hex
    receipts = runtime / "receipts" / ("run-" + run_id)
    receipts.mkdir(mode=0o700)
    sequence = 0

    def record(stage, value):
        nonlocal sequence
        sequence += 1
        item = {"stage": stage, "run_id": run_id, "value": value}
        write.save_once(receipts / f"{sequence:03d}-{stage}.json", write.canonical(item), immutable=True)
        print(json.dumps(item, ensure_ascii=False), flush=True)

    if mode == "read-workout":
        arguments = read.ReadInput(workout_id=workout_id).model_dump()
        tool_name = "read_workout"
    elif mode == "preview":
        arguments = write.PreviewInput(name=name, date=date).model_dump()
        tool_name = "preview_test"
    elif mode == "apply-existing":
        arguments = write.ApplyInput(preview_id=preview_id, proposal_sha256=proposal_sha256).model_dump()
        tool_name = "apply_test"
    elif mode == "inspect":
        arguments, tool_name = None, None
    else:
        raise ValueError("invalid_mode")

    async def discover_request(task, known_runs):
        while True:
            manifests = [p for p in read.RUNS.glob("*/ready/*.json") if p.parents[1].name not in known_runs]
            if manifests:
                # This client performs one read. Concurrent unrelated reads are
                # disambiguated by a caller token passed to this server process.
                for manifest in manifests:
                    meta = read.read_private_json(manifest)
                    if meta.get("client_id") != run_id:
                        continue
                    request_dir = read.request_directory(Path(meta["run_dir"]), meta["request_id"])
                    request = read.ReadRequest.model_validate(read.read_private_json(request_dir / "request.json"))
                    expected = {"request_id": request.request_id, "run_dir": str(request_dir.parents[1]),
                                "request_dir": str(request_dir), "workout_id": request.workout_id,
                                "created_at": request.created_at, "expires_at": request.expires_at,
                                "client_id": run_id}
                    if meta != expected or request.workout_id != workout_id:
                        raise ValueError("manifest_mismatch")
                    record("request_ready", meta)
                    return request
            if task.done():
                return None
            await asyncio.sleep(0.05)

    read.ensure_runtime()
    known_runs = {p.name for p in read.RUNS.iterdir()}
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "garmin_agent_tools.browser", "serve"],
        cwd=str(Path(__file__).resolve().parents[2]),
        env={"PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1",
             "GARMIN_AGENT_BROWSER_HOME": str(home), "GARMIN_BROWSER_CLIENT_ID": run_id,
             "GARMIN_WRITEPREP_RUNTIME": str(runtime)})
    with open(os.devnull, "w") as sink:
        async with stdio_client(params, errlog=sink) as (incoming, outgoing):
            async with ClientSession(incoming, outgoing, read_timeout_seconds=timedelta(seconds=320)) as session:
                initialized = await session.initialize()
                tools = await session.list_tools()
                prompts = await session.list_prompts()
                prompt = await session.get_prompt("browser_workflow", arguments={})
                assert initialized.instructions == GUIDANCE
                assert [t.model_dump(mode="json", by_alias=True) for t in tools.tools] == [t.model_dump(mode="json", by_alias=True) for t in await catalogue()]
                assert [p.name for p in prompts.prompts] == ["browser_workflow"]
                assert len(prompt.messages) == 1 and prompt.messages[0].content.text == GUIDANCE
                record("public_mcp_context", {"browser_home": str(home), "write_runtime": str(runtime),
                    "initialize_instructions": initialized.instructions,
                    "tools": tools.model_dump(mode="json", by_alias=True),
                    "prompts": prompts.model_dump(mode="json", by_alias=True),
                    "get_prompt_matches_initialize_instructions": True})
                if tool_name is None:
                    record("inspection_complete", {"tool_invoked": False})
                    return
                if mode == "read-workout":
                    task = asyncio.create_task(session.call_tool(tool_name, arguments=arguments))
                    try:
                        request = await discover_request(task, known_runs)
                        result = await task
                    finally:
                        if not task.done():
                            task.cancel()
                            await asyncio.gather(task, return_exceptions=True)
                    if result.isError or request is None:
                        raise ValueError("read_failed")
                    value = read.ReadResult.model_validate(result.structuredContent)
                    selected = {k: v for k, v in value.model_dump().items()
                                if k not in ("outcome", "external_writes_enabled", "source_limit")}
                    read.validate_response(selected, request)
                else:
                    result = await session.call_tool(tool_name, arguments=arguments)
                    if result.isError:
                        raise ValueError("blocked_request")
                record("call_tool_result", result.model_dump(mode="json", by_alias=True))
