"""Pull a PCActn out of an MCP ``tools/call``.

The agreed ``PCA-Action`` convention carries the proof in one of two places, checked in order:

1. The MCP request metadata (``_meta``) under the key ``"PCA-Action"``, as base64url of the proof's
   strict-canonical JSON. This is the resource-server-correct channel: metadata rides every request
   kind and is not part of the tool's own argument schema.
2. The tool-call ``arguments`` under ``"PCA-Action"``, as the same base64url string **or** as the
   PCActn object inline. This is a fallback for clients that cannot set ``_meta``.

Decoding reuses the strict base64url + strict-JSON profile from :mod:`atlas_pca`, so a malformed proof
is reported as ``"undecodable"`` (fail-closed), never silently parsed leniently.
"""
from typing import Mapping, Optional, Tuple

from atlas_pca.pca import StrictJsonError, decode_b64u_strict, strict_parse

PCA_META_KEY = "PCA-Action"

# ``(pcactn, error)`` — ``error`` is ``"absent"`` or ``"undecodable"`` when ``pcactn`` is ``None``.
Extracted = Tuple[Optional[dict], Optional[str]]


def _as_mapping(obj: object) -> Optional[Mapping[str, object]]:
    """Normalise MCP ``_meta`` / arguments (a dict or a pydantic model) to a plain mapping."""
    if obj is None:
        return None
    if isinstance(obj, Mapping):
        return obj
    dump = getattr(obj, "model_dump", None)
    if callable(dump):
        try:
            result = dump(by_alias=True)
        except TypeError:
            result = dump()
        if isinstance(result, Mapping):
            return result
    return None


def _decode_b64u_pcactn(raw: str) -> Extracted:
    decoded = decode_b64u_strict(raw)
    if decoded is None:
        return None, "undecodable"
    try:
        obj = strict_parse(decoded)
    except StrictJsonError:
        return None, "undecodable"
    if not isinstance(obj, dict):
        return None, "undecodable"
    return obj, None


def _from_container(container: Optional[Mapping[str, object]], key: str) -> Extracted:
    """Look up ``key`` in a mapping and coerce it to a PCActn (base64url string or inline object)."""
    if container is None or key not in container:
        return None, None  # not here; caller decides whether that is "absent"
    value = container[key]
    if isinstance(value, str):
        return _decode_b64u_pcactn(value)
    if isinstance(value, Mapping):
        return dict(value), None
    return None, "undecodable"


def extract_pcactn(
    meta: object = None,
    arguments: object = None,
    *,
    meta_key: str = PCA_META_KEY,
) -> Extracted:
    """Return ``(pcactn, error)`` for an MCP ``tools/call``.

    ``meta``      — the request ``_meta`` (a mapping or pydantic model), the primary channel.
    ``arguments`` — the tool-call arguments, the fallback channel.
    ``meta_key``  — the key the proof travels under in both places (default ``"PCA-Action"``).
    """
    meta_map = _as_mapping(meta)
    pcactn, err = _from_container(meta_map, meta_key)
    if pcactn is not None or err is not None:
        return pcactn, err

    arg_map = _as_mapping(arguments)
    pcactn, err = _from_container(arg_map, meta_key)
    if pcactn is not None or err is not None:
        return pcactn, err

    return None, "absent"
