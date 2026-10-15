"""The final answer as data: a ``submit_answer`` tool whose input schema follows the turn's answer type.

The model ends a turn by calling ``submit_answer`` once. Its arguments are checked against the
schema; a call that does not match is answered with the validation error, as a tool would, and
the model may try again. The grader then compares typed values: nothing is read out of prose.

The tool is the runner's, not the MCP server's, and is the same for every model provider.
"""

from __future__ import annotations

from typing import Any

import jsonschema

NAME = "submit_answer"

_ANSWER: dict[str, dict[str, Any]] = {
    "boolean": {"type": "boolean", "description": "true for yes, false for no."},
    "number": {"type": "number", "description": "The number, as a JSON number."},
    "string": {"type": "string", "description": "The value only, without explanation."},
    "set": {"type": "array", "items": {"type": "string"},
            "description": "Every item, one per array element; an empty array if there are none."},
    "text": {"type": "string", "description": "Your full answer to the user."},
}


def kind(turn: dict[str, Any]) -> str:
    answer_type = (turn.get("answer") or {}).get("type")
    return answer_type if answer_type in ("boolean", "number", "string", "set") else "text"


def schema(turn: dict[str, Any]) -> dict[str, Any]:
    properties: dict[str, Any] = {"answer": _ANSWER[kind(turn)]}
    required = ["answer"]
    if kind(turn) != "text":
        # Without this a failed lookup that defaults to "no" would score as right whenever the
        # true answer is no. A guess is declared, and graded as not answered.
        properties["determined"] = {"type": "boolean", "description":
                                    "true if the tool results establish the answer; false if they did not and the answer is a guess."}
        required.append("determined")
    properties["explanation"] = {"type": "string", "description": "Optional: how you found it, or why it could not be determined."}
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


def tool(turn: dict[str, Any]) -> dict[str, Any]:
    return {"type": "function", "function": {
        "name": NAME,
        "description": "Submit your final answer to the user's question. Call it once, when you are done; it ends your turn.",
        "parameters": schema(turn)}}


def validate(turn: dict[str, Any], arguments: Any) -> str | None:
    """None if the arguments match the turn's schema, otherwise the message the model sees."""
    try:
        jsonschema.validate(arguments, schema(turn))
    except jsonschema.ValidationError as exc:
        where = "/".join(str(p) for p in exc.absolute_path) or "arguments"
        return f"Error: submit_answer was not recorded. {where}: {exc.message}. Call submit_answer again with valid arguments."
    return None


def text(submitted: dict[str, Any] | None) -> str:
    """The submitted answer as plain text, for checks that read what the user was told."""
    if not submitted:
        return ""
    value = submitted.get("answer")
    body = ", ".join(map(str, value)) if isinstance(value, list) else str(value)
    return body + ("\n" + submitted["explanation"] if submitted.get("explanation") else "")
