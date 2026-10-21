"""Extract structured JSON from free text, validated with pydantic.

SCHEMA CONTRACT
---------------
'schema' is a dict mapping each field name to a JSON type name string. The
allowed type names are:

    "string"  -> str
    "integer" -> int
    "number"  -> float
    "boolean" -> bool
    "array"   -> list
    "object"  -> dict

All fields are required, and any string is a valid field name (names are
aliased onto generated internal ones). The schema is turned into a pydantic model via
pydantic.create_model and used to validate the model's JSON output. An unknown
type name raises ValueError.
"""

import json

import pydantic

from local_llm._text import strip_fences as _strip_fences
from local_llm.ollama_client import generate

_TYPE_MAP = {
    "string": str,
    "integer": int,
    "number": float,
    "boolean": bool,
    "array": list,
    "object": dict,
}


def _build_model(schema: dict):
    """Build a pydantic model from the schema. Raises ValueError on bad type."""
    # Public field names are NOT used as Pydantic attribute names: a leading
    # underscore is silently dropped, model_config is rejected, and names such
    # as schema or copy shadow BaseModel attributes. Each field gets a generated
    # internal name and the public name travels as its alias, so any schema key
    # validates from, and dumps back to, exactly the name the caller wrote.
    fields = {}
    for index, (name, type_name) in enumerate(schema.items()):
        if type_name not in _TYPE_MAP:
            raise ValueError(
                "Unknown schema type '" + str(type_name) + "' for field '"
                + str(name) + "'. Valid types: " + ", ".join(_TYPE_MAP.keys())
            )
        fields["field_%d" % index] = (
            _TYPE_MAP[type_name], pydantic.Field(..., alias=name))
    return pydantic.create_model("ExtractModel", **fields)


def extract_json(text: str, schema: dict, model: str | None = None) -> dict:
    """Extract the fields described by 'schema' from 'text'.

    See the module SCHEMA CONTRACT for the schema format. Calls the model up to
    twice (initial attempt plus one retry); on the retry a stricter reminder is
    appended. Returns the validated fields as a plain dict. Raises ValueError if
    the schema contains an unknown type, or if both attempts fail to produce
    valid JSON matching the schema. `model` (optional) overrides the configured
    default model for this call only.
    """
    validator = _build_model(schema)

    field_descriptions = ", ".join(
        name + " (" + type_name + ")" for name, type_name in schema.items()
    )
    base_prompt = (
        "Extract the following fields from the text and return ONLY a JSON "
        "object with EXACTLY those field names and types. No markdown, no code "
        "fences, no commentary.\n"
        "Fields: " + field_descriptions + "\n\n"
        "Text:\n" + text
    )

    last_raw = ""
    last_error = ""
    for attempt in range(2):
        prompt = base_prompt
        if attempt == 1:
            prompt = (
                base_prompt
                + "\n\nIMPORTANT: Your previous response was not valid. Return "
                "valid JSON only, with exactly the requested field names and "
                "types, and nothing else."
            )

        last_raw = generate(prompt, model=model)
        try:
            parsed = json.loads(_strip_fences(last_raw))
        except json.JSONDecodeError as exc:
            last_error = str(exc)
            continue
        # Valid JSON that is not an object (an array, string, number or null)
        # is invalid output like any other: it gets the retry, then ValueError.
        if not isinstance(parsed, dict):
            last_error = "model returned valid JSON that is not an object"
            continue
        try:
            validated = validator(**parsed)
        except pydantic.ValidationError as exc:
            last_error = str(exc)
            continue
        return validated.model_dump(by_alias=True)

    raise ValueError(
        "Failed to extract valid JSON after 2 attempts. Last error: "
        + last_error + ". Last model output: " + last_raw[:500]
    )
