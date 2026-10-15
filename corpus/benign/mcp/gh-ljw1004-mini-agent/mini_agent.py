#!/usr/bin/env python3

from __future__ import annotations
from typing import Any, Literal, Tuple
from pathlib import Path
from datetime import datetime
import dataclasses
import readline
import json
import sys
import argparse
import asyncio
import base64
import re
import contextlib
import urllib.parse
import pydantic
import mcp
import mcp.types
import mcp.client.stdio
from typedefs import AgentCallback, AgentCallbackPredigest, AssistantTranscriptItem, BashCallback, PlanCallback, PostToolUseHookInput, PostToolUseHookOutput, PreToolUseHookInput, PreToolUseHookOutput, SystemMessage, TextMessageContent, ToolUseMessageContent, UserMessage, ToolResultMessageContent, UserPromptSubmitHookInput, UserPromptSubmitHookOutput, UserTranscriptItem
import adapter

# INVARIANT: 'transcript' strictly alternates User and Assistant, starting with User.
# At the end of each iteration of the loop, any Assistant is followed by a User which has
# a ToolResult message content for each ToolUse in the Assistant.
# (This is different from the transcript file on disk, which uses multiple messages of the
# same type in a row because it only allows one content-block per message.)
# Also, 'transcript' always has UserTranscriptItem.toolUseResult=None; this field
# only exist on disk, and is reconstructed from ToolUseMessageContent

# INVARIANT: our agent never changes directory, like CLAUDE_BASH_MAINTAIN_PROJECT_WORKING_DIR.
# Any tools whose behavior is influenced by cwd will correctly only ever use their mcp
# server's launch cwd, which is the same as the agent's current cwd, the same as its launch cwd.

async def main() -> None:
    astack = contextlib.AsyncExitStack()
    histfile = Path("~/.mini_agent_history").expanduser()
    readline.read_history_file(histfile) if histfile.exists() else None

    try:
        env = await Env.from_argv(sys.argv, astack)

        # User interaction loop
        while True:
            if len(env.transcript) == 0 or not isinstance(env.transcript[-1], UserTranscriptItem):
                prompt = input("> ")
                if prompt == "/plan true" or prompt == "/plan false":
                    await mcp_read_resources(env.resources, f"plan-mode://set/{prompt[6:]}")
                    print(f"! plan mode set to '{prompt[6:]}'")
                elif prompt.startswith("/"):
                    print("HELP\n/plan true|false -- set planning mode")
                else:
                    item = await user_prompt_hook(env, prompt)
                    env.append_to_transcript(item) if item else None
            if len(env.transcript) > 0 and isinstance(env.transcript[-1], UserTranscriptItem):
                response = await agentic_loop(env)
                print("\n".join([f"< {text.text}" for text in response]))            
                print()
            if not env.interactive:
                sys.exit(0)

    finally:
        readline.set_history_length(100)
        readline.write_history_file(histfile)
        await astack.aclose()


async def agentic_loop(env: Env) -> list[TextMessageContent]:
    """Runs an agentic loop: given a transcript which ends with a user message, we call the LLM
    to get the following assistant message; if that message involved any tool-uses then invoke them
    and repeat the loop. (For versality, this function also allows a transcript which already ends
    with an assistant message, in which case we jump straight to invoking the tools.)"""
    while True:
        # Call the LLM to get an assistant message.
        if isinstance(env.transcript[-1], UserTranscriptItem):
            try:
                response = await adapter.acompletion(env.models[env.model], [tool[0] for tool in env.tools], [env.system_message, *[item.message for item in env.transcript]])
            except Exception as e:
                input(f"! {e}\nPress enter to try the same message again\nretry> ")
                continue
            if isinstance(response.usage, dict) and 'message' in response.usage:
                print(f"[{response.usage['message']}]")
            item = AssistantTranscriptItem(type="assistant", message=response, requestId=None)
            env.append_to_transcript(item)            

        tool_uses = [content for content in env.transcript[-1].message.content if isinstance(content, ToolUseMessageContent)]
        texts = [content for content in env.transcript[-1].message.content if isinstance(content, TextMessageContent)]

        if len(tool_uses) == 0:
            return texts
        if not env.execute_tools:
            print(json.dumps([tool_use.model_dump() for tool_use in tool_uses], indent=2))
            sys.exit(2)

        # Execute tools
        tool_results = [await invoke_tool(env, tool_use) for tool_use in tool_uses]
        combined_content = [content_block for tool_result in tool_results for content_block in tool_result]
        non_interleaved_content = sorted(combined_content, key=lambda x: isinstance(x, TextMessageContent))  # Claude needs all text at the end
        item = UserTranscriptItem(message=UserMessage(content=non_interleaved_content))
        env.append_to_transcript(item)


async def mcp_read_resources(resources: list[Tuple[str, mcp.ClientSession]], uri: str) -> list[str]:
    mcps = [mcp for template_uri, mcp in resources if uri.startswith(re.sub(r'\{.*\}$', '', template_uri))]
    results = [content for mcp in mcps for content in (await mcp.read_resource(pydantic.AnyUrl(uri))).contents]
    return [c.text if isinstance(c, mcp.types.TextResourceContents) else base64.b64decode(c.blob).decode('utf-8') for c in results]


async def invoke_hooks(env: Env, hook_type: Literal["UserPromptSubmit","PreToolUse","PostToolUse"], input: pydantic.BaseModel) -> list[dict[str,Any]]:
    uri = f"hook://{hook_type}/{urllib.parse.quote(input.model_dump_json(), safe='')}"
    return [json.loads(text) for text in await mcp_read_resources(env.resources, uri)]


async def user_prompt_hook(env: Env, prompt: str) -> UserTranscriptItem | None:
    """This is called upon user prompt submission.
    It invokes hooks as appropriate. If they denied the submission, it returns None.
    Otherwise it returns a UserTranscriptItem with the prompt plus any context added by hooks."""

    # hook
    hook_input = UserPromptSubmitHookInput(transcript_path=str(env.transcript_file), prompt=prompt)
    hook_output, pre, post = UserPromptSubmitHookOutput.combine([UserPromptSubmitHookOutput(**output) for output in await invoke_hooks(env, "UserPromptSubmit", hook_input)])
    if hook_output.decision == "block" or not hook_output.continue_:
        print(f"[BLOCKED: {hook_output.reason or hook_output.stopReason}]")
        return None
    for insertion in [*pre, *post]:
        print(f"  >> {(insertion.text if len(insertion.text) < 400 else insertion.text[:120]).replace('\n', ' ') + '...'}")
    
    content: list[TextMessageContent | ToolResultMessageContent] = [*pre, TextMessageContent(type="text", text=prompt), *post]
    return UserTranscriptItem(message=UserMessage(content=content if len(content) > 1 else prompt))


async def invoke_tool(env: Env, tool_use: ToolUseMessageContent) -> list[ToolResultMessageContent | TextMessageContent]:
    """This is called when the agentic loop has seen a ToolUseMessageContent request from the LLM.
    It invokes the tool, running pre- and post-hooks if any are installed.
    As a side effect, it prints to stdout."""

    # prehook
    prehook_input = PreToolUseHookInput(transcript_path=str(env.transcript_file), tool_name=tool_use.name, tool_input=tool_use.input)
    prehook_output = PreToolUseHookOutput.combine([PreToolUseHookOutput(**output) for output in await invoke_hooks(env, "PreToolUse", prehook_input)])
    if prehook_output.hookSpecificOutput.permissionDecision == "deny":
        print(f"  >> {tool_use.name}(...) [BLOCKED: {prehook_output.hookSpecificOutput.permissionDecisionReason}]")
        reason = f"{tool_use.name} operation blocked by hook:\n-{prehook_output.hookSpecificOutput.permissionDecisionReason}"
        r = ToolResultMessageContent(type="tool_result", tool_use_id=tool_use.id, content=reason, is_error=True)
        return [r]

    # invoke the tool
    try:
        mcp_server = [mcp for tool, mcp in env.tools if tool.name == tool_use.name][0]
        r = await mcp_server.call_tool(tool_use.name, tool_use.input)
        result = [TextMessageContent(type="text", text=c.text) for c in r.content if isinstance(c, mcp.types.TextContent)]
        is_success = not r.isError
    except Exception as e:
        is_success, result = False, str(e)

    # did the tool delegate work to us?
    callback: AgentCallback | PlanCallback | BashCallback | None = None
    try:
        if isinstance(result, list) and len(result) == 1 and result[0].text.startswith("{"):
            data = json.loads(result[0].text)
            kind = data.get("kind",None)
            callback = AgentCallback(**data) if kind == "agent_callback" \
                else PlanCallback(**data) if kind == "plan_callback" \
                else BashCallback(**data) if kind == "bash_callback" \
                else None
    except BaseException:
        pass
    if isinstance(callback, AgentCallback):
        is_success, result = await handle_agent_callback(env, callback, tool_use)
    elif isinstance(callback, PlanCallback):
        is_success, result = await handle_plan_callback(env, callback)
    elif isinstance(callback, BashCallback):
        is_success, result = await handle_bash_callback(callback)

    # record the result of tool invocation
    print(f"  >> {tool_use.name}(...) -> {json.dumps([r if isinstance(r,str) else r.model_dump() for r in result]).replace('\n', ' ')[:120]}")
    content: list[TextMessageContent | ToolResultMessageContent] = []
    content.append(ToolResultMessageContent(type="tool_result", tool_use_id=tool_use.id, content=result, is_error=not is_success))

    # posthook only on success https://github.com/anthropics/claude-code/issues/4831
    if is_success:  
        posthook_input = PostToolUseHookInput(transcript_path=str(env.transcript_file), tool_name=tool_use.name, tool_input=tool_use.input, tool_response=result)
        posthook_output = PostToolUseHookOutput.combine([PostToolUseHookOutput(**output) for output in await invoke_hooks(env, "PostToolUse", posthook_input)])
        if posthook_output.decision == "block" and posthook_output.reason:
            content.append(TextMessageContent(type="text", text=posthook_output.reason))
            print(f"  >> {posthook_output.reason}")

    return content

async def handle_agent_callback(env: Env, callback: AgentCallback, tool_use: ToolUseMessageContent) -> Tuple[bool, list[TextMessageContent]]:
    """Runs the agentic loop for a subagent. Returns the final response of that loop."""
    content: list[TextMessageContent | ToolResultMessageContent] = []
    for user_content in callback.user_content:
        # Digests are a hack to workaround the lack of a good central Websearch service.
        # All they let us do the phases of websearch (digesting individual pages, consolidating them)
        # here in mini_agent.py without additional back-and-forths with the Websearch tool.
        if isinstance(user_content, AgentCallbackPredigest):
            digest_system_message = SystemMessage(content=[TextMessageContent(text=text) for text in user_content.system_content])
            digest_user_message = UserMessage(content=[TextMessageContent(text=text) for text in user_content.user_content])
            print(f"  >> {user_content.digest_description}")
            try:
                response = await adapter.acompletion(env.models["digest-model"], [], [digest_system_message, digest_user_message])
            except Exception as e:
                input(f"! {e}\nPress enter to try the same message again\nretry> ")
                continue
            content.extend(text for text in response.content if isinstance(text, TextMessageContent))
        else:
            content.append(TextMessageContent(type="text", text=user_content))

    subenv = dataclasses.replace(
        env,
        tools = (env.tools if callback.tools is None else [(tool, mcp) for tool, mcp in env.tools if tool.name in callback.tools]),
        system_message = SystemMessage(content=[TextMessageContent(text=text) for text in callback.system_content]),
        transcript_file = env.transcript_file.with_suffix(f".{callback.subagent_type}-{tool_use.id}.jsonl"),
        transcript = [],
        execute_tools = True,
    )
    subenv.transcript_file.touch()    
    subenv.append_to_transcript(UserTranscriptItem(message=UserMessage(content=content)))
    print(f"  >> {callback.subagent_type}({callback.callback_description}) ... [{subenv.transcript_file}]")
    return True, await agentic_loop(subenv)

async def handle_plan_callback(env: Env, callback: PlanCallback) -> Tuple[bool, list[TextMessageContent]]:
    """Prints a message to the user asking them to approve the plan."""
    is_success, result = True, [TextMessageContent(text=callback.text_on_accept)]
    if env.interactive and input(f"! {callback.plan}\n---\n1. approve plan\n2. reject plan\n? ") != "1":
        is_success, result = False, [TextMessageContent(text=callback.text_on_reject)]
    await mcp_read_resources(env.resources, f"plan-mode://set/{'false' if is_success else 'true'}")
    return is_success, result

async def handle_bash_callback(callback: BashCallback) -> Tuple[bool, list[TextMessageContent]]:
    """Runs a bash command, and returns stdout and stderr."""
    MAX_OUTPUT: int = 30000
    print(f"  $ {callback.command}")
    p = await asyncio.create_subprocess_shell(callback.command, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    # Our solution for getting partial stdout+stderr even in case of timeout
    # is to read from them concurrently ourselves.
    assert p.stdout is not None and p.stderr is not None
    stdout_parts: list[bytes] = []
    stderr_parts: list[bytes] = []
    async def read_stream(stream: asyncio.StreamReader, parts: list[bytes]) -> str:
        while (chunk := await stream.read(8192)) and sum(len(part) for part in parts) < MAX_OUTPUT:
            parts.append(chunk)                
        return b''.join(parts).decode('utf-8', errors='replace')[:MAX_OUTPUT]
    stdout_task = asyncio.create_task(read_stream(p.stdout, stdout_parts))
    stderr_task = asyncio.create_task(read_stream(p.stderr, stderr_parts))

    # Wait for the process to finish within timeout. In case of timeout,
    # we'll allow 5s for a gracefull SIGTERM, and if not then SIGKILL.
    exit_code: int | Literal["timeout"]
    try:
        exit_code = await asyncio.wait_for(p.wait(), callback.timeout)
    except asyncio.TimeoutError:
        p.terminate()
        try:
            await asyncio.wait_for(p.wait(), timeout=5.0)
        except BaseException:
            p.kill()
            await p.wait()
        exit_code = "timeout"
    
    # We can gather stdout+stderr uniformly now, whether it was success or timeout.
    # In case of timeout there might be partial utf-8 output, hence errors='replace' above.
    stdout, stderr = await asyncio.gather(stdout_task, stderr_task)
    if exit_code == "timeout":
        is_success, text = False, f"Command timed out after {callback.timeout:0.1f}s\n{stderr}\n{stdout}"
    elif exit_code == 0:
        is_success, text = True, f"{stdout}\n{stderr}"
    else:
        is_success, text = False, f"{stderr}\n{stdout}"
    return is_success, [TextMessageContent(text=text)]


@dataclasses.dataclass
class Env:
    """Environment needed for an agentic loop."""
    tools: list[Tuple[mcp.Tool, mcp.ClientSession]]
    resources: list[Tuple[str, mcp.ClientSession]]
    models: dict[Literal["model", "digest-model"], str]
    model: Literal["model", "digest-model"]
    interactive: bool
    execute_tools: bool
    transcript: list[UserTranscriptItem | AssistantTranscriptItem]
    transcript_file: Path
    system_message: SystemMessage

    @staticmethod
    async def from_argv(argv: list[str], astack: contextlib.AsyncExitStack[Any]) -> Env:
        parser = argparse.ArgumentParser()    
        parser.add_argument("--resume", type=str)
        parser.add_argument("--interactive", action=argparse.BooleanOptionalAction)
        parser.add_argument("--execute-tools", action=argparse.BooleanOptionalAction, default=True)
        parser.add_argument("--model", type=str)
        parser.add_argument("--digest-model", type=str, default=None)
        parser.add_argument("--mcp", type=str, action="append")
        parser.add_argument("-p", type=str)
        args = parser.parse_args(argv[1:])

        interactive = bool(sys.stdin.isatty() if args.interactive is None else args.interactive)
        execute_tools = bool(args.execute_tools)

        # --model and --digest-model
        model = str(args.model) if args.model else "gpt-4.1"
        digest_model = str(args.digest_model) if args.digest_model \
            else "gpt-4.1-nano" if model.startswith("gpt-") \
            else "o4-mini" if model.startswith("o") \
            else "gemini/gemini-2.5-flash" if model.startswith("gemini/") \
            else "anthropic/claude-3-haiku-20240307" if model.startswith("anthropic/") \
            else model
        print(f"[MODEL: {model} + {digest_model}]")
        
        # Connect to MCP servers, and get their tools, hooks and system prompts
        mcps = await Env.connect_mcps(args.mcp, astack)
        tools = [(tool, mcp) for mcp in mcps for tool in (await mcp.list_tools()).tools]
        resources = [(template.uriTemplate, mcp) for mcp in mcps for template in (await mcp.list_resource_templates()).resourceTemplates]
        system_texts = await mcp_read_resources(resources, "system-prompt://main")
        system_message = SystemMessage(content=[TextMessageContent(text=text) for text in system_texts])

        # Load the transcript or create a new one
        transcript_file = Path(args.resume or f"~/.claude/projects/default/{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.jsonl").expanduser()
        if not transcript_file.exists():
            print(f"[TRANSCRIPT: {transcript_file}]")
            transcript_file.parent.mkdir(parents=True, exist_ok=True)
            transcript_file.touch()
        transcript = adapter.parse_transcript_file(transcript_file)

        env = Env(tools, resources, {"model":model, "digest-model": digest_model}, "model", interactive, execute_tools, transcript, transcript_file, system_message)

        # If -p, then append it to the transcript
        prompt = str(args.p) if args.p else None
        if prompt:
            content = [item for item in adapter.parse_message_content(json.loads(prompt)) if isinstance(item, TextMessageContent) or isinstance(item, ToolResultMessageContent)] if prompt.lstrip().startswith("[") else prompt
            item = await user_prompt_hook(env, content) if isinstance(content, str) else UserTranscriptItem(message=UserMessage(content=content))
            env.append_to_transcript(item) if item else None
        if len(transcript) == 0 and not interactive:
            print("Needs either --interactive or -p", file=sys.stderr)
            sys.exit(1)

        return env

    @staticmethod
    async def connect_mcps(mcp_cmds: list[str] | None, astack: contextlib.AsyncExitStack) -> list[mcp.ClientSession]:
        if mcp_cmds is None:
            print("[IMPLICIT --mcp builtin]")
            mcp_cmds = ["builtin"]

        mcps: list[mcp.ClientSession] = []
        for command in mcp_cmds:
            if command == "builtin":
                import core_tools
                mcps.append(core_tools.clientSession)
                continue
            params = mcp.client.stdio.StdioServerParameters(command=command)
            read, write = await astack.enter_async_context(mcp.client.stdio.stdio_client(params))
            session = await astack.enter_async_context(mcp.ClientSession(read, write))
            await session.initialize()
            mcps.append(session)
        return mcps

    def append_to_transcript(self, item: UserTranscriptItem | AssistantTranscriptItem) -> None:
        self.transcript.append(item)
        adapter.append_to_transcript_file(self.transcript_file, item)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print()
