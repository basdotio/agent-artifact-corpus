from __future__ import annotations
from typing import Awaitable, TypeVar
import json
import sys
import time
import itertools
import asyncio
import mcp
import uuid
from typing import Any
from pathlib import Path
from datetime import datetime
from typedefs import AssistantMessage, AssistantTranscriptItem, SystemMessage, TextMessageContent, ThinkingMessageContent, ToolResultMessageContent, ToolUseMessageContent, UserMessage, UserTranscriptItem


###############################################################
## STATIC TYPING FOR LITELLM ##################################
###############################################################

async def acompletion(model: str, tools: list[mcp.Tool], messages: list[SystemMessage | UserMessage | AssistantMessage]) -> AssistantMessage:
    import litellm  # egregiously slow import, so we're doing it lazily

    # Prompt caching strategy.
    # Observation: our message list grows monotonically in a given transcript,
    # and every fresh transcript for a given CLAUDE.md will share much the same initial message.
    # 1. OpenAI automatically caches prompt prefixes every 128 tokens, for prompts that are 1024 tokens or longer.
    #    It routes requests to a machine based on a combination of the first 256 tokens
    #    and the prompt_cache_key. We use the current working directory as our
    #    prompt_cache_key, so that requests for the current transcript and for future
    #    transcripts in the same project will likely be routed to the same server.
    # 2. Gemini does implicit cache prompting always.
    # 3. Anthropic caches prompt prefixes at up to four points where you tell it,
    #    via "cache_control" markers in the message content. (These markers cause
    #    gemini to fail; they should only be added if using anthropic). We add them here:
    #    - message 0, likely the system message shared by every user of the same core-tools,
    #    - message 1, likely the initial user message that contains CLAUDE.md and is shared by all transcripts for this project
    #    - message N-1, the final user message, shared by the next iteration of this agent
    openai_prompt_cache_key = str(hash(str(Path.cwd())))  # used by OpenAI
    is_anthropic = model.startswith("anthropic/") or model.startswith("claude")

    response = await spinner(litellm.acompletion(  # type: ignore
        model=model,
        tools=[openai_tool_desc(tool) for tool in tools],
        messages=[openai_message(msg, is_anthropic and (i<=1 or i==len(messages)-1)) for i,msg in enumerate(messages)],
        user=openai_prompt_cache_key,
    ))
    return assistant_message(response)

T = TypeVar("T")

async def spinner(awaitable: Awaitable[T]) -> T:
    if not sys.stdout.isatty():
        return await awaitable
    t0, spinner, task = time.time(), itertools.cycle("🌑🌒🌓🌔🌕🌖🌗🌘"), asyncio.ensure_future(awaitable)
    try:
        while True:
            sys.stdout.write(f"\r{next(spinner)} {time.time() - t0:.1f}s")
            sys.stdout.flush()
            try:
                return await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
            except asyncio.TimeoutError:
                continue
    finally:
        sys.stdout.write("\r" + " " * 30 + "\r")


def openai_tool_desc(tool: mcp.Tool) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.inputSchema
        }
    }


def openai_message(message: SystemMessage | UserMessage | AssistantMessage, add_cache_control: bool) -> dict[str, Any]:
    """Turns our format of messages into the OpenAI format used by litellm.
    We'll also add the cache_control header on user/system messages if the flag is passed.
    (Note: presence of the flag causes gemini to fail)."""
    def openai_tool_use(item: ToolUseMessageContent) -> dict[str, Any]:
        return {
            "id": item.id,
            "type": "function",
            "function": {
                "name": item.name,
                "arguments": item.input if isinstance(item.input, str) else json.dumps(item.input)
            }
        }

    if isinstance(message, AssistantMessage):
        tool_calls = [openai_tool_use(item) for item in message.content if isinstance(item, ToolUseMessageContent)]
        content = [item.model_dump() for item in message.content if not isinstance(item, ToolUseMessageContent)]
        return {"role": message.role, **({"content": content} if len(content)>0 else {}), **({"tool_calls": tool_calls} if len(tool_calls)>0 else {}) }
        # OpenAI requires tool_calls key to be absent if there aren't any
    else:
        message_content = [TextMessageContent(text=message.content)] if isinstance(message.content, str) else message.content
        tools = [item for item in message_content if isinstance(item, ToolResultMessageContent)]
        texts = [item for item in message_content if isinstance(item, TextMessageContent)]
        if len(tools) == 0:
            r, content = {"role": message.role}, [item.model_dump() for item in texts]
        elif len(tools) > 0 and len(texts) == 0:
            content = [TextMessageContent(text=c) if isinstance(c,str) else c for tool in tools for c in tool.content]
            content = [item.model_dump() for item in content]
            r, content = {"role": "tool", "tool_call_id": tools[0].tool_use_id, "type": "tool_use"}, content
        else:
            raise ValueError(f"LiteLLM cant express {len(tools)} tool results with {len(texts)} text messages")
        if add_cache_control and len(content) > 0:
            content[-1] |= {"cache_control": {"type": "ephemeral"}}
        return {**r, "content": content}


def assistant_message(response: Any) -> AssistantMessage:
    import litellm.types.utils  # pyright: ignore  # egregiously slow import, and not even typesafe
    if not isinstance(response, litellm.types.utils.ModelResponse):
        raise TypeError(f"Expected litellm.types.utils.ModelResponse, got {type(response)}")
    if not isinstance(response.choices[0], litellm.types.utils.Choices):
        raise TypeError(f"Expected litellm.types.utils.Choice, got {type(response.choices[0])}")
    usage = getattr(response, 'usage', None)
    message = response.choices[0].message
    content: list[TextMessageContent | ThinkingMessageContent | ToolUseMessageContent] = []
    if message.content:
        content.append(TextMessageContent(type="text", text=message.content))
    if hasattr(message, 'reasoning_content') and message.reasoning_content:
        content.append(TextMessageContent(type="text", text=message.reasoning_content))
    for tool_call in (message.tool_calls or []) if hasattr(message,'tool_calls') else []:
        content.append(ToolUseMessageContent(type="tool_use", id=tool_call.id, name=str(tool_call.function.name), input=json.loads(tool_call.function.arguments)))
    for thinking in (message.thinking_blocks or []) if hasattr(message,'thinking_blocks') else []:
        if 'thinking' in thinking and 'signature' in thinking:
            content.append(ThinkingMessageContent(type="thinking", thinking=thinking['thinking'], signature=thinking['signature']))

    if isinstance(usage, litellm.types.utils.Usage):
        cached = usage.prompt_tokens_details.cached_tokens if usage.prompt_tokens_details else None
        message = (f"{cached} cached input tokens, {usage.prompt_tokens - cached} further input tokens" if cached else f"{usage.prompt_tokens} input tokens") + f", {usage.completion_tokens} response tokens"
        usage = usage.model_dump()
        usage['message'] = message # our ad-hoc extension to the usage data

    return AssistantMessage(
        role="assistant",
        id=response.id,
        content=content,
        type="message",
        model=str(response.model),
        stop_reason="tool_use" if hasattr(message, 'tool_calls') else "end_turn",
        stop_sequence=None,
        usage=usage,
    )


###############################################################
## TRANSCRIPT DISK FILE #######################################
###############################################################


def append_to_transcript_file(transcript_file: Path, item: UserTranscriptItem | AssistantTranscriptItem) -> None:
    claude_compat_fields = {
        "cwd": str(Path.cwd()),
        "isSidechain": False,
        "parentUuid": None,
        "sessionId": "default",
        "timestamp": datetime.now().isoformat(),
        "uuid": str(uuid.uuid4()),
        "userType": "human",
        "version": "0.1",
        }

    # The file only has one content_block per line, so this is a list of content_blocks we'll need to write
    content_blocks: list[str | dict[str, Any]] = []
    if isinstance(item.message.content, str):
        content_blocks.append(item.message.content)
    else:
        for content_block in item.message.content:
            if isinstance(content_block, TextMessageContent):
                content_blocks.append(content_block.text)
            else:
                content_blocks.append(content_block.model_dump())

    # Now it's a bit messy how much we duplicate of the item per content_block...
    with open(transcript_file, "a") as f:
        if isinstance(item, UserTranscriptItem):
            for content_block in content_blocks:
                message = {**item.message.model_dump(), "content": content_block}
                raw_item = {
                    **item.model_dump(),
                    **claude_compat_fields,
                    "uuid": str(uuid.uuid4()),
                    "message": message,
                    "toolUseResult": content_block if getattr(content_block, 'type', None) == 'tool_result' else None,
                }
                f.write(json.dumps(raw_item) + "\n")
        else:
            for i, content_block in enumerate(content_blocks):
                is_final = i == len(content_blocks) - 1
                message = {
                    **item.message.model_dump(),
                    "content": content_block,
                    "stop_reason": item.message.stop_reason if is_final else None,
                    "stop_sequence": item.message.stop_sequence if is_final else None,
                    "usage": item.message.usage if is_final else None,
                }
                raw_item = {
                    **item.model_dump(),
                    **claude_compat_fields,
                    "uuid": str(uuid.uuid4()),
                    "message": message,
                }
                f.write(json.dumps(raw_item) + "\n")


def parse_transcript_file(transcript_file: Path) -> list[UserTranscriptItem | AssistantTranscriptItem]:
    lines = transcript_file.read_text().splitlines()
    result: list[UserTranscriptItem | AssistantTranscriptItem] = []
    for line in lines:
        data = json.loads(line)
        if "message" in data and "content" in data["message"]:
            data["message"]["content"] = parse_message_content(data["message"]["content"])
        item_type = data.get("type")
        if item_type == "assistant":
            result.append(AssistantTranscriptItem(**data))
        elif item_type == "user":
            result.append(UserTranscriptItem(**data))
        elif item_type == "system" or item_type == "summary":
            pass
        else:
            raise ValueError(f"Unknown transcript item type '{item_type}'")
        
        # The file on disk uses multiple messages of the same type in a row,
        # but we load them as a single message with multiple content blocks.
        if len(result) >= 2 and isinstance(result[-1], UserTranscriptItem) and isinstance(result[-2], UserTranscriptItem):
            item1 = result[-2]
            item2 = result[-1]
            ucontent1: list[TextMessageContent | ToolResultMessageContent] = [TextMessageContent(type="text", text=item1.message.content)] if isinstance(item1.message.content, str) else item1.message.content
            ucontent2: list[TextMessageContent | ToolResultMessageContent] = [TextMessageContent(type="text", text=item2.message.content)] if isinstance(item2.message.content, str) else item2.message.content
            item2.message.content = ucontent1 + ucontent2
            item2.toolUseResult = None
            del result[-2]
        elif len(result) >= 2 and isinstance(result[-1], AssistantTranscriptItem) and isinstance(result[-2], AssistantTranscriptItem):
            item1 = result[-2]
            item2 = result[-1]
            acontent1: list[TextMessageContent | ToolUseMessageContent | ThinkingMessageContent] = [TextMessageContent(type="text", text=item1.message.content)] if isinstance(item1.message.content, str) else item1.message.content
            acontent2: list[TextMessageContent | ToolUseMessageContent | ThinkingMessageContent] = [TextMessageContent(type="text", text=item2.message.content)] if isinstance(item2.message.content, str) else item2.message.content
            item2.message.content = acontent1 + acontent2
            del result[-2]

    return result


def parse_message_content(raw_content: str | list[dict[str,Any]]) -> str | list[TextMessageContent | ThinkingMessageContent | ToolUseMessageContent | ToolResultMessageContent]:
    """Given content which was parsed from json, i.e. is either a string or a list of dicts,
    this constructs strongly typed pydantic content blocks."""
    if isinstance(raw_content, str):
        return raw_content
    
    result: list[TextMessageContent | ThinkingMessageContent | ToolUseMessageContent | ToolResultMessageContent] = []
    for content_block in raw_content:
        data_type = content_block.get("type")
        if data_type == "text":
            result.append(TextMessageContent(**content_block))
        elif data_type == "tool_result":
            result.append(ToolResultMessageContent(**content_block))
        elif data_type == "thinking":
            result.append(ThinkingMessageContent(**content_block))
        elif data_type == "tool_use":
            result.append(ToolUseMessageContent(**content_block))
        else:
            raise ValueError(f"Unknown user content block type '{data_type}'")        
    return result