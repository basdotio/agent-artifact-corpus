#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import tomllib

DEFAULT_MODELS_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_PRIORITY = 1000
JsonObject = dict[str, Any]


class CatalogError(RuntimeError):
    """An actionable catalog generation failure."""


@dataclass(frozen=True)
class CodexSchema:
    template: JsonObject
    reasoning_order: tuple[str, ...]
    reasoning_descriptions: dict[str, str]
    input_modalities: tuple[str, ...]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a Codex model_catalog_json from OpenRouter models."
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Catalog path. Overrides config discovery.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        help="Codex TOML file whose top-level model_catalog_json selects the output.",
    )
    parser.add_argument(
        "--openrouter-json",
        type=Path,
        help="Read a saved OpenRouter /models response instead of fetching it.",
    )
    parser.add_argument(
        "--bundled-json",
        type=Path,
        help="Read a saved `codex debug models --bundled` response.",
    )
    parser.add_argument("--models-url", default=DEFAULT_MODELS_URL)
    parser.add_argument("--codex-bin", default=os.environ.get("CODEX_BIN", "codex"))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 0 when the catalog is current, 1 when it would change.",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip parsing the candidate with Codex (intended for isolated tests).",
    )
    return parser.parse_args(argv)


def codex_home() -> Path:
    return Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()


def output_from_config(path: Path) -> Path | None:
    try:
        config = tomllib.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CatalogError(f"config file does not exist: {path}") from None
    except tomllib.TOMLDecodeError as exc:
        raise CatalogError(f"invalid TOML in {path}: {exc}") from exc

    value = config.get("model_catalog_json")
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise CatalogError(f"model_catalog_json in {path} must be a non-empty string")

    output = Path(os.path.expandvars(value)).expanduser()
    if not output.is_absolute():
        output = path.parent / output
    return output


def resolve_output(output: Path | None, config: Path | None) -> Path:
    if output is not None:
        return output.expanduser().absolute()

    if config is not None:
        config = config.expanduser().absolute()
        configured = output_from_config(config)
        if configured is None:
            raise CatalogError(f"model_catalog_json is not set in {config}")
        return configured.absolute()

    home = codex_home().absolute()
    for candidate in (home / "openrouter.config.toml", home / "config.toml"):
        if not candidate.is_file():
            continue
        configured = output_from_config(candidate)
        if configured is not None:
            return configured.absolute()
    return (home / "openrouter.model.json").absolute()


def load_json_file(path: Path, label: str) -> JsonObject:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CatalogError(f"{label} file does not exist: {path}") from None
    except json.JSONDecodeError as exc:
        raise CatalogError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError(f"{label} root must be a JSON object")
    return value


def fetch_openrouter_models(url: str, timeout: float) -> JsonObject:
    headers = {
        "Accept": "application/json",
        "User-Agent": "codex-openrouter-model-catalog/1",
    }
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        raise CatalogError(f"failed to fetch {url}: {exc}") from exc

    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"OpenRouter returned invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError("OpenRouter response root must be a JSON object")
    return value


def load_bundled_catalog(codex_bin: str, timeout: float) -> JsonObject:
    try:
        result = subprocess.run(
            [codex_bin, "debug", "models", "--bundled"],
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise CatalogError(f"Codex executable not found: {codex_bin}") from None
    except subprocess.TimeoutExpired as exc:
        raise CatalogError("timed out reading the bundled Codex model catalog") from exc

    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise CatalogError(f"`codex debug models --bundled` failed: {detail}")
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"Codex returned invalid bundled model JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise CatalogError("bundled Codex catalog root must be a JSON object")
    return value


def object_list(root: JsonObject, key: str, label: str) -> list[JsonObject]:
    values = root.get(key)
    if not isinstance(values, list):
        raise CatalogError(f"{label} must contain a {key!r} array")
    if not values:
        raise CatalogError(f"{label} {key!r} array is empty")
    if any(not isinstance(value, dict) for value in values):
        raise CatalogError(f"every item in {label} {key!r} must be an object")
    return values


def validate_openrouter_models(models: list[JsonObject]) -> None:
    seen: set[str] = set()
    for index, model in enumerate(models):
        slug = model.get("id")
        if not isinstance(slug, str) or not slug.strip():
            raise CatalogError(f"OpenRouter model at index {index} has no non-empty id")
        if slug in seen:
            raise CatalogError(f"OpenRouter returned duplicate model id: {slug}")
        seen.add(slug)


def derive_codex_schema(bundled: JsonObject) -> CodexSchema:
    models = object_list(bundled, "models", "bundled Codex catalog")
    templates = [
        model
        for model in models
        if isinstance(model.get("model_messages"), dict)
        or isinstance(model.get("base_instructions"), str)
    ]
    if not templates:
        raise CatalogError(
            "bundled Codex catalog has no model with model_messages or base_instructions"
        )

    reasoning_order: list[str] = []
    descriptions: dict[str, str] = {}
    input_modalities: list[str] = []
    for model in models:
        for preset in model.get("supported_reasoning_levels") or []:
            if not isinstance(preset, dict):
                continue
            effort = preset.get("effort")
            description = preset.get("description")
            if isinstance(effort, str) and effort and effort not in reasoning_order:
                reasoning_order.append(effort)
            if isinstance(effort, str) and isinstance(description, str):
                descriptions.setdefault(effort, description)
        for modality in model.get("input_modalities") or []:
            if (
                isinstance(modality, str)
                and modality
                and modality not in input_modalities
            ):
                input_modalities.append(modality)

    if not reasoning_order:
        raise CatalogError("bundled Codex catalog advertises no reasoning efforts")
    if not input_modalities:
        input_modalities.append("text")

    return CodexSchema(
        template=copy.deepcopy(templates[0]),
        reasoning_order=tuple(reasoning_order),
        reasoning_descriptions=descriptions,
        input_modalities=tuple(input_modalities),
    )


def positive_int(value: Any) -> int | None:
    return (
        value
        if isinstance(value, int) and not isinstance(value, bool) and value > 0
        else None
    )


def reasoning_presets(
    source: JsonObject, schema: CodexSchema
) -> tuple[str | None, list[JsonObject]]:
    reasoning = source.get("reasoning")
    if not isinstance(reasoning, dict):
        return None, []
    advertised = reasoning.get("supported_efforts")
    if not isinstance(advertised, list):
        return None, []

    supported = {effort for effort in advertised if isinstance(effort, str) and effort}
    efforts = [effort for effort in schema.reasoning_order if effort in supported]
    presets = [
        {
            "effort": effort,
            "description": schema.reasoning_descriptions.get(
                effort, f"OpenRouter {effort} reasoning effort"
            ),
        }
        for effort in efforts
    ]
    if not efforts:
        return None, presets

    default = reasoning.get("default_effort")
    if default not in efforts:
        default = "medium" if "medium" in efforts else efforts[0]
    return default, presets


def normalized_modalities(source: JsonObject, schema: CodexSchema) -> list[str]:
    architecture = source.get("architecture")
    advertised = (
        architecture.get("input_modalities") if isinstance(architecture, dict) else None
    )
    advertised_set = {
        value for value in advertised or [] if isinstance(value, str) and value
    }
    modalities = [
        modality for modality in schema.input_modalities if modality in advertised_set
    ]
    if not modalities and "text" in schema.input_modalities:
        modalities.append("text")
    return modalities


def build_model(source: JsonObject, schema: CodexSchema, priority: int) -> JsonObject:
    model = copy.deepcopy(schema.template)
    slug = source["id"]
    parameters = {
        value
        for value in source.get("supported_parameters") or []
        if isinstance(value, str)
    }
    has_tools = "tools" in parameters
    modalities = normalized_modalities(source, schema)
    default_reasoning, supported_reasoning = reasoning_presets(source, schema)

    model.update(
        {
            "slug": slug,
            "display_name": source.get("name") or slug,
            "description": source.get("description"),
            "default_reasoning_level": default_reasoning,
            "supported_reasoning_levels": supported_reasoning,
            "shell_type": schema.template.get("shell_type", "shell_command")
            if has_tools
            else "disabled",
            "visibility": "list",
            "supported_in_api": True,
            "priority": priority,
            "additional_speed_tiers": [],
            "service_tiers": [],
            "availability_nux": None,
            "upgrade": None,
            "support_verbosity": "verbosity" in parameters,
            "default_verbosity": schema.template.get("default_verbosity")
            if "verbosity" in parameters
            else None,
            "apply_patch_tool_type": schema.template.get("apply_patch_tool_type")
            if has_tools
            else None,
            "supports_parallel_tool_calls": has_tools,
            "supports_image_detail_original": "image" in modalities,
            "experimental_supported_tools": [],
            "input_modalities": modalities,
            "supports_search_tool": False,
            "use_responses_lite": False,
        }
    )

    context_window = positive_int(source.get("context_length"))
    if context_window is None:
        provider = source.get("top_provider")
        if isinstance(provider, dict):
            context_window = positive_int(provider.get("context_length"))
    model["context_window"] = context_window
    model["max_context_window"] = context_window

    for key in (
        "default_service_tier",
        "comp_hash",
        "auto_review_model_override",
        "tool_mode",
        "multi_agent_version",
    ):
        model.pop(key, None)

    model_messages = model.get("model_messages")
    if isinstance(model_messages, dict) and isinstance(
        model_messages.get("instructions_template"), str
    ):
        model.pop("base_instructions", None)
    elif not isinstance(model.get("base_instructions"), str):
        raise CatalogError("Codex template has no usable instruction payload")

    supports_reasoning_summary = bool(
        supported_reasoning and "include_reasoning" in parameters
    )
    for key in (
        "supports_reasoning_summary_parameter",
        "supports_reasoning_summaries",
    ):
        if key in model:
            model[key] = supports_reasoning_summary
    return model


def build_catalog(openrouter: JsonObject, bundled: JsonObject) -> JsonObject:
    models = object_list(openrouter, "data", "OpenRouter response")
    validate_openrouter_models(models)
    schema = derive_codex_schema(bundled)
    return {
        "models": [
            build_model(model, schema, DEFAULT_PRIORITY + index)
            for index, model in enumerate(models)
        ]
    }


def render_catalog(catalog: JsonObject) -> bytes:
    return (json.dumps(catalog, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def catalog_diff(existing: bytes | None, catalog: JsonObject) -> tuple[int, int, int]:
    if existing is None:
        return len(catalog["models"]), 0, 0
    try:
        old_root = json.loads(existing)
        old_models = old_root.get("models", []) if isinstance(old_root, dict) else []
        old_by_slug = {
            model.get("slug"): model
            for model in old_models
            if isinstance(model, dict) and isinstance(model.get("slug"), str)
        }
    except (json.JSONDecodeError, UnicodeDecodeError):
        return len(catalog["models"]), 0, 0

    new_by_slug = {model["slug"]: model for model in catalog["models"]}
    added = len(new_by_slug.keys() - old_by_slug.keys())
    removed = len(old_by_slug.keys() - new_by_slug.keys())
    changed = sum(
        old_by_slug[slug] != model
        for slug, model in new_by_slug.items()
        if slug in old_by_slug
    )
    return added, removed, changed


def validate_with_codex(path: Path, codex_bin: str, timeout: float) -> None:
    override = f"model_catalog_json={json.dumps(str(path))}"
    try:
        result = subprocess.run(
            [codex_bin, "debug", "models", "-c", override],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        raise CatalogError(f"Codex executable not found: {codex_bin}") from None
    except subprocess.TimeoutExpired as exc:
        raise CatalogError(
            "timed out validating the generated catalog with Codex"
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"exit status {result.returncode}"
        raise CatalogError(f"Codex rejected the generated catalog: {detail}")


def install_catalog(
    output: Path,
    payload: bytes,
    codex_bin: str,
    timeout: float,
    validate: bool,
) -> bool:
    output.parent.mkdir(parents=True, exist_ok=True)
    existing = output.read_bytes() if output.exists() else None
    if existing == payload:
        if validate:
            validate_with_codex(output, codex_bin, timeout)
        return False

    mode = (output.stat().st_mode & 0o777) if output.exists() else 0o644
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        if validate:
            validate_with_codex(temporary, codex_bin, timeout)
        os.replace(temporary, output)
        temporary = None
        directory_fd = os.open(output.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.timeout <= 0:
        raise CatalogError("--timeout must be greater than zero")
    output = resolve_output(args.output, args.config)
    openrouter = (
        load_json_file(args.openrouter_json, "OpenRouter response")
        if args.openrouter_json
        else fetch_openrouter_models(args.models_url, args.timeout)
    )
    bundled = (
        load_json_file(args.bundled_json, "bundled Codex catalog")
        if args.bundled_json
        else load_bundled_catalog(args.codex_bin, args.timeout)
    )
    catalog = build_catalog(openrouter, bundled)
    payload = render_catalog(catalog)
    existing = output.read_bytes() if output.exists() else None
    added, removed, changed = catalog_diff(existing, catalog)

    if args.check:
        if existing == payload:
            print(f"up to date: {output} ({len(catalog['models'])} models)")
            return 0
        print(
            f"out of date: {output} ({len(catalog['models'])} models; "
            f"+{added} -{removed} ~{changed})"
        )
        return 1

    updated = install_catalog(
        output,
        payload,
        args.codex_bin,
        args.timeout,
        validate=not args.no_validate,
    )
    status = "updated" if updated else "up to date"
    print(
        f"{status}: {output} ({len(catalog['models'])} models; "
        f"+{added} -{removed} ~{changed})"
    )
    return 0


def main() -> int:
    try:
        return run()
    except (CatalogError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
