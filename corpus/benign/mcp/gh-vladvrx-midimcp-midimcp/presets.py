"""Source-preserving adapter for the pinned upstream serum-mcp codec and schema."""
from __future__ import annotations

import hashlib
import math
import os
import re
from copy import deepcopy
from pathlib import Path
from uuid import uuid4

from serum_mcp.generation.spec import PresetSpec
from serum_mcp.preset.introspect import extract_spec
from serum_mcp.preset.mapping import apply_spec
from serum_mcp.preset.packer import SerumPreset, pack_bytes, unpack_bytes

UPSTREAM_REVISION = "6c471bb8424f3f06f16f5b9fc5bfab244fd11384"
_ASSET_FIELDS = {"custom_harmonics", "sample_source", "sample_playback_source", "granular_source", "spectral_source"}


def parameter_schema() -> dict:
    """Return the upstream JSON schema with unknown properties forbidden."""
    schema = PresetSpec.model_json_schema(by_alias=True)
    def close(node):
        if isinstance(node, dict):
            if "properties" in node:
                node["additionalProperties"] = False
            for value in list(node.values()):
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)
    close(schema)
    return schema


def _check_keys(value, schema, root, path="spec"):
    if "$ref" in schema:
        schema = root["$defs"][schema["$ref"].rsplit("/", 1)[-1]]
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            if "$ref" in branch or branch.get("type") == "object":
                _check_keys(value, branch, root, path)
        return
    if isinstance(value, dict) and "properties" in schema:
        props = schema["properties"]
        for key, child in value.items():
            if key not in props:
                raise ValueError(f"Unknown preset field: {path}.{key}")
            _check_keys(child, props[key], root, f"{path}.{key}")
    elif isinstance(value, list) and "items" in schema:
        for index, child in enumerate(value):
            _check_keys(child, schema["items"], root, f"{path}[{index}]")


def _validate(spec: dict, name: str):
    if not isinstance(spec, dict):
        raise ValueError("spec must be a JSON object")
    if not isinstance(name, str) or not name.strip() or len(name) > 128:
        raise ValueError("name must contain 1 to 128 characters")
    payload = deepcopy(spec)
    if "name" in payload and payload["name"] != name:
        raise ValueError("spec.name and name disagree")
    payload["name"] = name
    payload.setdefault("description", "")
    schema = parameter_schema()
    _check_keys(payload, schema, schema)
    model = PresetSpec.model_validate(payload, strict=True)
    for osc in payload.get("oscillators", []):
        if any(osc.get(field) for field in _ASSET_FIELDS):
            raise ValueError("New custom wavetables/sample ingestion is not supported by this adapter yet; it would write into the Serum library. Existing asset references are preserved.")
        if isinstance(osc.get("wavetable"), str) and ".." in Path(osc["wavetable"]).parts:
            raise ValueError("Wavetable references may not contain parent traversal")
    return model, payload


def _init_path() -> Path:
    root = os.environ.get("MIDIMCP_UPSTREAM_ROOT")
    if root:
        candidate = Path(root).expanduser().resolve() / "fixtures" / "init_preset.SerumPreset"
        if not candidate.is_file():
            raise FileNotFoundError(f"MIDIMCP_UPSTREAM_ROOT has no init fixture: {candidate}")
        return candidate
    import serum_mcp
    package = Path(serum_mcp.__file__).resolve().parent
    for candidate in (package / "fixtures" / "init_preset.SerumPreset", package.parent.parent / "fixtures" / "init_preset.SerumPreset"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("The serum-mcp wheel does not ship its init fixture. Set MIDIMCP_UPSTREAM_ROOT to the pinned upstream checkout, or edit a user-owned init preset.")


def _references(data, prefix=""):
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, str) and value and any(token in key.lower() for token in ("path", "filename")):
                found.append({"field": path, "reference": value, "resolution": "requires local Serum library; not bundled"})
            else:
                found.extend(_references(value, path))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_references(value, f"{prefix}[{index}]"))
    return found


def _changes(before, after, prefix=""):
    if isinstance(before, dict) and isinstance(after, dict):
        result = []
        for key in sorted(before.keys() | after.keys()):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                result.append(path)
            else:
                result.extend(_changes(before[key], after[key], path))
        return result
    return [] if before == after else [prefix]


def _verify_requested(requested, actual, path="spec"):
    """Catch upstream's documented silently ignored default-reset operations."""
    if isinstance(requested, dict) and isinstance(actual, dict):
        for key, value in requested.items():
            if key in actual and key not in {"name", "description", "fx_chain", "mod_routes"}:
                _verify_requested(value, actual[key], f"{path}.{key}")
    elif isinstance(requested, list) and isinstance(actual, list):
        for index, value in enumerate(requested):
            if index < len(actual):
                _verify_requested(value, actual[index], f"{path}[{index}]")
    elif isinstance(requested, (int, float)) and not isinstance(requested, bool):
        if actual is not None and not math.isclose(float(requested), float(actual), rel_tol=1e-5, abs_tol=1e-6):
            raise ValueError(f"Upstream mapping did not apply {path}: requested {requested!r}, decoded {actual!r}. No preset was written.")
    elif isinstance(requested, bool) and actual != requested:
        raise ValueError(f"Upstream mapping did not apply {path}: requested {requested!r}, decoded {actual!r}. No preset was written.")


def _write(source: Path, spec: dict, output_dir: Path, name: str, *, creating: bool) -> dict:
    model, requested = _validate(spec, name)
    source = Path(source).expanduser().resolve(strict=True)
    raw = source.read_bytes()
    base = unpack_bytes(raw)
    external = []
    data = apply_spec(base.data, model, external_files=external)
    decoded = extract_spec(data).model_dump(by_alias=True)
    _verify_requested(requested, decoded)
    metadata = deepcopy(base.metadata)
    metadata["presetName"] = name
    if "description" in spec or creating:
        metadata["presetDescription"] = model.description
    if creating:
        metadata["presetAuthor"] = "MidiMCP"
    encoded = pack_bytes(SerumPreset(metadata=metadata, data=data))
    verified = unpack_bytes(encoded)
    if verified.data != data or verified.metadata != metadata:
        raise ValueError("Preset codec roundtrip changed state; no output was written")
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", name).strip("-_")[:64] or "preset"
    target = destination / f"midimcp-{slug}-{uuid4().hex}.SerumPreset"
    with target.open("xb") as stream:
        stream.write(encoded)
    return {
        "path": str(target), "name": name, "sha256": hashlib.sha256(encoded).hexdigest(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "upstream_revision": UPSTREAM_REVISION,
        "changed_raw_fields": _changes(base.data, data),
        "dependencies": _references(data),
        "external_files": [str(path) for path in external],
        "warnings": ["Preset codec validated; sound and FL Studio loading require a host render.",
                     "Supplied upstream module objects apply their defaults to omitted fields. Inspect changed_raw_fields before replacing a sound.",
                     "Dependency paths are preserved; their availability has not been verified."],
    }


def create_preset(spec: dict, output_dir: Path, name: str) -> dict:
    return _write(_init_path(), spec, output_dir, name, creating=True)


def edit_preset(source: Path, spec: dict, output_dir: Path, name: str) -> dict:
    """Create a distinct candidate, preserving the source bytes and unknown state."""
    return _write(source, spec, output_dir, name, creating=False)


def describe_preset(path: Path) -> dict:
    path = Path(path).expanduser().resolve(strict=True)
    raw = path.read_bytes()
    preset = unpack_bytes(raw)
    return {"path": str(path), "sha256": hashlib.sha256(raw).hexdigest(),
            "metadata": preset.metadata, "spec": extract_spec(preset.data).model_dump(mode="json", by_alias=True),
            "dependencies": _references(preset.data), "upstream_revision": UPSTREAM_REVISION,
            "warnings": ["Semantic description is incomplete; unknown raw fields remain in the original preset."]}
