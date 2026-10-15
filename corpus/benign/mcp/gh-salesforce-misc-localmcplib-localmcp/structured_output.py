"""Structured output for LangChain agents across models and gateways."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Sequence
from typing import Annotated, Any, NotRequired

from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, AgentState, ModelRequest, ModelResponse, hook_config
from langchain.agents.middleware.types import PrivateStateAttr
from langchain.agents.structured_output import StructuredOutputError
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, AnyMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.messages.tool import tool_call
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.runtime import Runtime
from pydantic import BaseModel, ValidationError

from localmcp.retry import ModelCallRetryMiddleware


class SubmitResultError(StructuredOutputError):
    """Raised when a model exhausts its attempts without submitting a valid result."""

    def __init__(self, tool_name: str, attempts: int, ai_message: AIMessage) -> None:
        super().__init__(f"model did not submit a valid {tool_name} result after {attempts} attempts")
        self.tool_name = tool_name
        self.attempts = attempts
        self.ai_message = ai_message


class _SubmitResultState(AgentState[Any]):
    submit_result_attempts: NotRequired[Annotated[int, PrivateStateAttr]]


def _format_validation_error(exc: ValidationError) -> str:
    # Omit input values: they echo the model's own arguments and can be large.
    lines = [
        f"- {'.'.join(str(part) for part in error['loc']) or '<root>'}: {error['msg']}"
        for error in exc.errors(include_url=False, include_input=False)
    ]
    return "\n".join(lines)


class SubmitResultMiddleware[SchemaT: BaseModel](AgentMiddleware[_SubmitResultState, Any, Any]):
    """Collect structured output through an ordinary, unforced submission tool.

    ``ToolStrategy`` forces ``tool_choice``, which some models reject (for
    example with extended thinking), and ``ProviderStrategy`` depends on a
    native schema constraint that gateways may drop or that lets a model answer
    without using its other tools. This middleware instead registers a
    ``tool_name`` tool whose arguments are ``schema`` and leaves ``tool_choice``
    unset, so every tool-capable model can use it.

    This is a cross-model requirement, not a naive retry: an unforced tool is
    the lowest common denominator that every tool-capable model and gateway
    accepts. Because the call cannot be forced, the correction rounds below are
    what make it dependable. They also absorb differences in response shape:
    fenced or prose-wrapped JSON, unparseable arguments, and schema mismatches
    are never salvaged by a model-specific parser but returned to the model to
    resubmit. Do not replace them with a forced ``tool_choice`` unless every
    model the application can be configured with supports it.

    A valid submission becomes ``structured_response`` and ends the run. A
    plain-text final answer is answered with a reminder, and an invalid
    submission with its validation errors, before returning to the model. Each
    counts as one attempt; exhausting ``max_attempts`` raises
    :class:`SubmitResultError`. The count restarts with every run. Tool calls
    whose arguments could not be parsed are rewritten with empty arguments and
    answered with an error instead of being replayed to the provider. Do not
    combine this with ``response_format``.
    """

    state_schema = _SubmitResultState

    def __init__(
        self,
        schema: type[SchemaT],
        *,
        tool_name: str = "submit_result",
        description: str = "Submit your final structured result. Call this exactly once, as your last action.",
        max_attempts: int = 5,
    ) -> None:
        super().__init__()
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        self._schema = schema
        self._tool_name = tool_name
        self._max_attempts = max_attempts
        self._instruction = (
            f"When you are finished, call the `{tool_name}` tool exactly once with your final result. "
            "Do not give your final answer as plain text."
        )
        self.tools: list[BaseTool] = [
            StructuredTool.from_function(
                func=self._unexpected_execution,
                name=tool_name,
                description=description,
                args_schema=schema,
            )
        ]

    @property
    def name(self) -> str:
        return f"{type(self).__name__}[{self._tool_name}]"

    def _unexpected_execution(self, **_: Any) -> str:
        # after_model answers every submission before the tools node runs.
        return f"{self._tool_name} was not processed; call it again as your only tool call."

    def _with_instruction(self, request: ModelRequest) -> ModelRequest:
        system = request.system_message
        if system is None:
            return request.override(system_message=SystemMessage(content=self._instruction))
        if isinstance(system.content, str):
            content: str | list[str | dict[str, Any]] = f"{system.content}\n\n{self._instruction}"
        else:
            content = [*system.content, {"type": "text", "text": self._instruction}]
        return request.override(system_message=SystemMessage(content=content))

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        return handler(self._with_instruction(request))

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        return await handler(self._with_instruction(request))

    def before_agent(self, state: _SubmitResultState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        # The counter is a checkpointed channel; reset it so a reused thread starts each run with a full budget.
        return {"submit_result_attempts": 0}

    async def abefore_agent(self, state: _SubmitResultState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)

    @hook_config(can_jump_to=["model", "end"])
    def after_model(self, state: _SubmitResultState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        message = state["messages"][-1] if state["messages"] else None
        if not isinstance(message, AIMessage):
            return None
        submissions = [call for call in message.tool_calls if call["name"] == self._tool_name]
        others = [call for call in message.tool_calls if call["name"] != self._tool_name]
        if others and not submissions and not message.invalid_tool_calls:
            return None

        # Providers replay unparseable arguments verbatim, which some backends reject for the rest of the run.
        # Rewrite them as empty-object calls and answer each one here so the tools node never runs them.
        unparsed = [
            tool_call(name=call["name"] or "", args={}, id=call["id"] or f"invalid_{index}")
            for index, call in enumerate(message.invalid_tool_calls)
        ]
        replies: list[AnyMessage] = []
        if unparsed:
            replies.append(
                message.model_copy(update={"tool_calls": [*message.tool_calls, *unparsed], "invalid_tool_calls": []})
            )

        if len(submissions) == 1:
            try:
                result = self._schema.model_validate(submissions[0]["args"])
            except ValidationError as exc:
                feedback = f"Invalid {self._tool_name} arguments:\n{_format_validation_error(exc)}"
            else:
                replies.append(ToolMessage(content="Result submitted.", tool_call_id=submissions[0]["id"] or ""))
                replies += [
                    ToolMessage(content="Not run: the result was already submitted.", tool_call_id=call["id"] or "")
                    for call in [*others, *unparsed]
                ]
                return {"messages": replies, "structured_response": result, "jump_to": "end"}
        elif submissions:
            feedback = f"Call {self._tool_name} exactly once; this turn called it {len(submissions)} times."
        else:
            feedback = ""

        replies += [
            ToolMessage(
                content=f"Not run: the {call['name'] or 'tool'} arguments were not a valid JSON object. "
                "Call it again with valid JSON arguments.",
                tool_call_id=call["id"],
                status="error",
            )
            for call in unparsed
        ]
        replies += [
            ToolMessage(content=feedback, tool_call_id=call["id"] or "", status="error") for call in submissions
        ]
        failed_submission = bool(submissions) or any(call["name"] == self._tool_name for call in unparsed)
        # Other valid tool calls still run and the tools node then returns to the model; a turn with none of them
        # makes no progress and is answered directly.
        update: dict[str, Any] = {}
        if not others:
            update["jump_to"] = "model"
            if not submissions and not unparsed:
                replies.append(HumanMessage(content=f"You have not submitted a result. {self._instruction}"))
        if failed_submission or not others:
            attempts = state.get("submit_result_attempts", 0) + 1
            if attempts >= self._max_attempts:
                raise SubmitResultError(self._tool_name, attempts, message)
            update["submit_result_attempts"] = attempts
        update["messages"] = replies
        return update

    async def aafter_model(self, state: _SubmitResultState, runtime: Runtime[Any]) -> dict[str, Any] | None:
        return self.after_model(state, runtime)


async def submit_structured[SchemaT: BaseModel](
    model: BaseChatModel,
    schema: type[SchemaT],
    *,
    system_prompt: str,
    messages: Sequence[AnyMessage],
    config: RunnableConfig | None = None,
    max_attempts: int = 5,
    retry: ModelCallRetryMiddleware | None = None,
) -> SchemaT:
    """Return one ``schema`` result from ``model`` through an unforced submission tool.

    A portable replacement for ``with_structured_output``: its
    ``function_calling`` method forces ``tool_choice``, and its ``json_schema``
    method relies on a native constraint that gateways may drop. Neither works
    across all models, so this uses :class:`SubmitResultMiddleware`, the lowest
    common denominator. The model is offered no other tools. Invalid submissions are corrected within the run,
    and exhausting ``max_attempts`` raises :class:`SubmitResultError`. Transient
    model errors are retried by ``retry``, a default
    :class:`~localmcp.retry.ModelCallRetryMiddleware` when omitted.
    """
    agent = create_agent(
        model,
        [],
        system_prompt=system_prompt,
        middleware=[SubmitResultMiddleware(schema, max_attempts=max_attempts), retry or ModelCallRetryMiddleware()],
    )
    result: dict[str, Any] = await agent.ainvoke({"messages": list(messages)}, config=config)
    return schema.model_validate(result["structured_response"])
