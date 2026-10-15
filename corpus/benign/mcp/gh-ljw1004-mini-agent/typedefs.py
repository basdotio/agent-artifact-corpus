from __future__ import annotations
from pathlib import Path
import pydantic
from typing import Literal, Any, Tuple


###############################################################
## MESSAGES ###################################################
###############################################################

class SystemMessage(pydantic.BaseModel):
    role: Literal["system"] = "system"
    content: str | list[TextMessageContent]

class UserMessage(pydantic.BaseModel):
    role: Literal["user"] = "user"
    content: str | list[TextMessageContent | ToolResultMessageContent]

class AssistantMessage(pydantic.BaseModel):
    role: Literal["assistant"] = "assistant"
    id: str
    content: list[TextMessageContent | ThinkingMessageContent | ToolUseMessageContent]
    type: Literal["message"] = "message"
    model: str
    stop_reason: str | None = None  # what values have we seen?
    stop_sequence: str | None = None  # what values have we seen?
    usage: dict[str, Any] | None = None  # Vendor-specific token usage information, if available

class TextMessageContent(pydantic.BaseModel):
    type: Literal["text"] = "text"
    text: str

class ThinkingMessageContent(pydantic.BaseModel):
    type: Literal["thinking"] = "thinking"
    thinking: str
    signature: str

class ToolUseMessageContent(pydantic.BaseModel):
    type: Literal["tool_use"] = "tool_use"
    id: str
    name: str
    input: Any

class ToolResultMessageContent(pydantic.BaseModel):
    type: Literal["tool_result"] = "tool_result"
    tool_use_id: str
    content: str | list[TextMessageContent]  # For internal tools, these are for-AI-consumption text prose from tools, not the structured tool output
    is_error: bool | None = None


###############################################################
## SPECIAL TOOL RESULT CONTENTS ###############################
###############################################################

class AgentCallbackPredigest(pydantic.BaseModel):
    """This user content will be "predigested" by doing a non-agentic request to a simpler model"""
    digest_description: str  # for UI display only
    system_content: list[str]
    user_content: list[str]

class AgentCallback(pydantic.BaseModel):
    """If tool_result is this json structure, then the agentic loop will kick off the described sub-loop.
    It will replace the tool_result with the agent's response."""
    kind: Literal["agent_callback"] = "agent_callback"
    subagent_type: str | None  # for UI display only
    callback_description: str  # for UI display only
    tools: list[str] | None  # if None, then inherit all tools; if any tool doesn't exist, it's silently ignored
    system_content: list[str]
    user_content: list[str | AgentCallbackPredigest]

class PlanCallback(pydantic.BaseModel):
    """If tool_result is this json structure, then the agentic loop will ask the user, and if they
    confirm then it will reset the `planning-mode://set/{bool}` flag.
    It will replace the tool_result with text_on_{accept,reject}."""
    kind: Literal["plan_callback"] = "plan_callback"
    plan: str  # will be shown to the user
    text_on_accept: str  # if the user accepts, this text is used for the tool_result
    text_on_reject: str  # if the user rejects, this text is used for the tool_result

class BashCallback(pydantic.BaseModel):
    """If tool_result is this json structure, then the agentic loop will execute the command.
    It will replace the tool_result with the command's output, truncated to 30000 characters.
    Specifically:
    - If 0 exit code, then output is {stdout}\n{stderr}
    - If non-0 exit code, then output is {stderr}\n{stdout}
    - If timeout, then output is "Command timed out after {timeout}s\n{stderr}\n{stdout}"
    """
    kind: Literal["bash_callback"] = "bash_callback"
    command: str  # the command to execute
    callback_description: str | None  # will be shown to the user
    timeout: float = 12.0  # timeout in seconds


###############################################################
## TRANSCRIPT #################################################
###############################################################

class AssistantTranscriptItem(pydantic.BaseModel):
    type: Literal["assistant"] = "assistant"
    message: AssistantMessage
    requestId: str | None = None  # API request ID like "req_011CR2VVWjziXhjir1dLhbzh"

class UserTranscriptItem(pydantic.BaseModel):
    type: Literal["user"] = "user"
    message: UserMessage
    isCompactSummary: bool | None = None  # only when compacting
    isMeta: bool | None = None  # ??
    toolUseResult: Any | None = None  # message may contain a for-AI-summary of the tool, but this is the raw result


###############################################################
## HOOKS ######################################################
###############################################################

class UserPromptSubmitHookInput(pydantic.BaseModel):
    session_id: str = "default"
    transcript_path: str
    cwd: str = pydantic.Field(default_factory=lambda: str(Path.cwd()))
    hook_event_name: Literal["UserPromptSubmit"] = "UserPromptSubmit"
    prompt: str

class UserPromptSubmitHookAdditionalOutput(pydantic.BaseModel):
    hookEventName: Literal["UserPromptSubmit"] = "UserPromptSubmit"
    additionalContext: str | list[TextMessageContent] | None = None  # if decision=undefined and continue=true, this is appended to the user message in the transcript
    additionalContextPre: str | list[TextMessageContent] | None = None  # like additionalContext, but prepended. THIS ISN'T PART OF CLAUDE HOOKS

class UserPromptSubmitHookOutput(pydantic.BaseModel):
    """Runs when the user submits a prompt, before Claude processes it.
    This allows you to add additional context based on the prompt/conversation,
    validate prompts, or block certain types of prompts. Behavior:
    1. Construct a JSON object from stdout if it starts with "{", or if not then like this:
       - if exit_code=2 then {"continue":"true","decision":"block", "reason":STDERR}
       - else {"continue":"true","additionalContext":STDOUT if exit_code=0 else undefined}
    2. If decision="block" then print reason to user, and don't add anything to the transcript.
    3. If continue="false" then print stopReason to the user, and don't add anything to the transcript.
    4. Otherwise add user-prompt to transcript, plus additionalContext if defined."""
    decision: Literal["block"] | None = None  # "block" is the first way to prevent user message from being added to the transcript
    reason: str | None = None  # if decision=block, this is shown to the user
    continue_: bool = True  # If decision=None, then continue=false is the second way to prevent user message from being added to the transcript
    stopReason: str | None = None  # if decision=None and continue=false, this is shown to the user
    suppressOutput: bool = False  # I didn't try this. Not sure what it does.
    hookSpecificOutput: UserPromptSubmitHookAdditionalOutput = UserPromptSubmitHookAdditionalOutput()

    @staticmethod
    def combine(outputs: list[UserPromptSubmitHookOutput]) -> Tuple[UserPromptSubmitHookOutput, list[TextMessageContent], list[TextMessageContent]]:
        """Combine multiple outputs into one. For convenience, returns pre and post additional contexts also as lists."""
        def texts(i: str | list[TextMessageContent] | None) -> list[TextMessageContent]:
            return [TextMessageContent(type="text", text=i)] if isinstance(i, str) else i or []
        pre = [text for o in outputs for text in texts(o.hookSpecificOutput.additionalContextPre)]
        post = [text for o in outputs for text in texts(o.hookSpecificOutput.additionalContext)]
        output = UserPromptSubmitHookOutput(
            decision="block" if any(o.decision for o in outputs) else None,
            reason="\n".join(filter(None, [o.reason for o in outputs])),
            continue_=all(o.continue_ for o in outputs),
            stopReason="\n".join(filter(None, [o.stopReason for o in outputs])),
            suppressOutput=all(o.suppressOutput for o in outputs),
            hookSpecificOutput=UserPromptSubmitHookAdditionalOutput(
                additionalContextPre=None if len(pre) == 0 else pre[0].text if len(pre) == 1 else pre,
                additionalContext=None if len(post) == 0 else post[0].text if len(post) == 1 else post,
            )
        )
        return output, pre, post



class PostToolUseHookInput(pydantic.BaseModel):
    session_id: str = "default"
    transcript_path: str
    cwd: str = pydantic.Field(default_factory=lambda: str(Path.cwd()))
    hook_event_name: Literal["PostToolUse"] = "PostToolUse"
    tool_name: str
    tool_input: Any
    tool_response: Any


class PostToolUseHookOutput(pydantic.BaseModel):
    """Runs immediately after a tool completes successfully.
    1. If stdout doesn't start with "{" and exit_code is not 0/2, then tool-result goes in transcript,
       stderr is shown to user in yellow, and the assistant is invoked.
       NOTE: this behavior can't be expressed in the PostToolUseHookOutput schema.
    2. Otherwise, construct a JSON object from stdout if it starts with "{", or if not then like this:
       - if exit_code=0 then {continue:"true"}
       - else {continue:"true", decision:"block", reason:STDERR}
    3. If continue="false" then stopReason is shown to the user in yellow, and tool-result goes
       in the transcript, but the assistant is not invoked; the next user prompt will be appended to the
       user message that contains that previous tool-result.
    4. If continue="true" and decision="block", then reason is shown to the user in grey,
       tool-result and reason both go in the transcript in the current user message,
       and the assistant is invoked. Note that in the case of multiple tools with reasons,
       Claude API requires that all tool-results first followed by all reasons: not interleaved.
    5. If continue="true" and decision=None, then tool-result alone goes in the current user message
       and the assistant is invoked."""
    continue_: bool
    stopReason: str | None = None
    decision: Literal["block"] | None
    reason: str | None = None

    @staticmethod
    def combine(outputs: list[PostToolUseHookOutput]) -> PostToolUseHookOutput:
        return PostToolUseHookOutput(
            continue_=all(o.continue_ for o in outputs),
            stopReason="\n".join(filter(None, [o.stopReason for o in outputs])),
            decision="block" if any(o.decision for o in outputs) else None,
            reason="\n".join(filter(None, [o.reason for o in outputs])),
        )


class PreToolUseHookInput(pydantic.BaseModel):
    session_id: str = "default"
    transcript_path: str
    cwd: str = pydantic.Field(default_factory=lambda: str(Path.cwd()))
    hook_event_name: Literal["PreToolUse"] = "PreToolUse"
    tool_name: str
    tool_input: Any

class PreToolUseHookAdditionalOutput(pydantic.BaseModel):
    hookEventName: Literal["PreToolUse"] = "PreToolUse"
    permissionDecision: Literal["allow","deny","ask"] | None = None
    permissionDecisionReason: str | None = None

class PreToolUseHookOutput(pydantic.BaseModel):
    """Runs after Claude creates tool parameters and before processing the tool call.
    Note: if this structure is serialized into Claude then it must be .model_dump(exclude_none=True),
    because Claude requires to see an absent permissionDecision field, rather than one with value null.

    1. If stdout doesn't start with "{" and exit_code is not 0/2, then tool-result goes in transcript,
       stderr is shown to user in yellow, and and the assistant is allowed to run.
       NOTE: this behavior can't be expressed in the PreToolUseHookOutput schema.
    2. Otherwise, construct a JSON object from stdout if it starts with "{", or if not then like this:
       - if exit_code=0 then {continue:"true", no permissionDecision field}
       - if exit_code=2 then {continue:"true", permissionDecision:"deny", permissionDecisionReason:"[{command}]: {stderr}"}
         where '{command}' is the command property for that hook in the .claude/settings.json file.
    3. Before processing, do some JSON cleanup of legacy fields:
       - If decision="approve" then use {permissionDecision:"allow", permissionDecisionReason:REASON} and remove the decision+reason fields
       - If decision="block" then use {permissionDecision:"deny", permissionDecisionReason:REASON} and remove the decision+reason fields
    4. If permissionDecision is "ask" then always ask the user for permission; if it's undefined then
       ask the user or not per existing permissions.
       If it is "deny" or if the ask was denied by user, then the tool is not invoked and tool_result
       is "{tool} operation blocked by hook:\n- {permissionDecisionReason}" and also permissionDecisionReason is shown to the user in pink.
       If it is "allow" or if the ask was approved by the user, then the tool is invoked and tool_result is normal.
    5. If any tool resulted in continue=false, then its stopReason is shown to the user in yellow, and the assistant is not invoked.
       But if all tools resulted in continue=true, then the assistant is invoked.
    """
    continue_: bool
    stopReason: str | None = None
    suppressOutput: bool = False
    decision: Literal["block", "approve"] | None = None
    reason: str | None = None
    hookSpecificOutput: PreToolUseHookAdditionalOutput = PreToolUseHookAdditionalOutput()

    @staticmethod
    def combine(outputs: list[PreToolUseHookOutput]) -> PreToolUseHookOutput:
        for o in outputs:
            if o.decision:
                o.hookSpecificOutput.permissionDecision = "allow" if o.decision == "approve" else "deny"
                o.hookSpecificOutput.permissionDecisionReason = o.reason
            o.decision = None
            o.reason = None
        decisions = [o.hookSpecificOutput.permissionDecision for o in outputs]
        denyReasons = [o.hookSpecificOutput.permissionDecisionReason for o in outputs if o.hookSpecificOutput.permissionDecision == "deny"]
        return PreToolUseHookOutput(
            continue_=all(o.continue_ for o in outputs),
            stopReason="\n".join(filter(None, [o.stopReason for o in outputs])),
            suppressOutput=all(o.suppressOutput for o in outputs),
            decision=None,
            reason=None,
            hookSpecificOutput=PreToolUseHookAdditionalOutput(
                permissionDecision="deny" if "deny" in decisions else "ask" if "ask" in decisions else "allow" if "allow" in decisions else None,
                permissionDecisionReason="\n".join(filter(None, denyReasons)) if any(denyReasons) else None,
            )
        )
