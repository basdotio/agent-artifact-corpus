from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "generate_catalog.py"
SPEC = importlib.util.spec_from_file_location("generate_catalog", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
generate_catalog = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_catalog
SPEC.loader.exec_module(generate_catalog)


def bundled_catalog() -> dict[str, object]:
    return {
        "models": [
            {
                "slug": "gpt-template",
                "display_name": "Template",
                "description": "Template model",
                "default_reasoning_level": "medium",
                "supported_reasoning_levels": [
                    {"effort": "low", "description": "Low reasoning"},
                    {"effort": "medium", "description": "Medium reasoning"},
                    {"effort": "high", "description": "High reasoning"},
                    {"effort": "xhigh", "description": "Extra-high reasoning"},
                ],
                "shell_type": "shell_command",
                "visibility": "list",
                "supported_in_api": True,
                "priority": 1,
                "additional_speed_tiers": ["fast"],
                "service_tiers": [{"id": "priority"}],
                "availability_nux": {"message": "new"},
                "upgrade": {"model": "next"},
                "model_messages": {
                    "instructions_template": "You are Codex.",
                    "instructions_variables": None,
                },
                "base_instructions": "You are Codex.",
                "support_verbosity": True,
                "default_verbosity": "low",
                "apply_patch_tool_type": "freeform",
                "web_search_tool_type": "text",
                "truncation_policy": {"mode": "tokens", "limit": 10000},
                "supports_parallel_tool_calls": True,
                "supports_image_detail_original": True,
                "context_window": 200000,
                "max_context_window": 200000,
                "comp_hash": "provider-specific",
                "effective_context_window_percent": 95,
                "experimental_supported_tools": ["computer_use"],
                "input_modalities": ["text", "image"],
                "supports_search_tool": True,
                "use_responses_lite": True,
                "tool_mode": "code_mode_only",
                "multi_agent_version": "v2",
            }
        ]
    }


def openrouter_response() -> dict[str, object]:
    return {
        "data": [
            {
                "id": "vendor/reasoner",
                "name": "Vendor: Reasoner",
                "description": "A reasoning model.",
                "context_length": 131072,
                "architecture": {"input_modalities": ["image", "text", "video"]},
                "supported_parameters": [
                    "tools",
                    "include_reasoning",
                    "reasoning_effort",
                    "verbosity",
                ],
                "reasoning": {
                    "supported_efforts": ["xhigh", "high", "medium", "low", "minimal"],
                    "default_effort": "high",
                },
            },
            {
                "id": "vendor/plain",
                "name": "Plain",
                "description": None,
                "context_length": 8192,
                "architecture": {"input_modalities": ["text"]},
                "supported_parameters": ["temperature"],
            },
        ]
    }


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_build_catalog_maps_openrouter_capabilities() -> None:
    bundled = bundled_catalog()
    catalog = generate_catalog.build_catalog(openrouter_response(), bundled)

    assert len(catalog["models"]) == 2
    reasoner, plain = catalog["models"]
    assert reasoner["slug"] == "vendor/reasoner"
    assert reasoner["priority"] == 1000
    assert reasoner["default_reasoning_level"] == "high"
    assert [item["effort"] for item in reasoner["supported_reasoning_levels"]] == [
        "low",
        "medium",
        "high",
        "xhigh",
    ]
    assert reasoner["input_modalities"] == ["text", "image"]
    assert reasoner["supports_image_detail_original"] is True
    assert reasoner["supports_parallel_tool_calls"] is True
    assert reasoner["support_verbosity"] is True
    assert reasoner["context_window"] == 131072
    assert reasoner["additional_speed_tiers"] == []
    assert reasoner["service_tiers"] == []
    assert "base_instructions" not in reasoner
    assert "comp_hash" not in reasoner
    assert "tool_mode" not in reasoner

    assert plain["priority"] == 1001
    assert plain["default_reasoning_level"] is None
    assert plain["supported_reasoning_levels"] == []
    assert plain["shell_type"] == "disabled"
    assert plain["apply_patch_tool_type"] is None
    assert plain["supports_parallel_tool_calls"] is False
    assert plain["support_verbosity"] is False
    assert plain["default_verbosity"] is None
    assert bundled["models"][0]["comp_hash"] == "provider-specific"


def test_duplicate_openrouter_model_ids_fail_closed() -> None:
    response = openrouter_response()
    response["data"].append(dict(response["data"][0]))

    with pytest.raises(generate_catalog.CatalogError, match="duplicate model id"):
        generate_catalog.build_catalog(response, bundled_catalog())


def test_cli_updates_then_reports_up_to_date(tmp_path: Path) -> None:
    openrouter = tmp_path / "openrouter.json"
    bundled = tmp_path / "bundled.json"
    output = tmp_path / "catalog.json"
    write_json(openrouter, openrouter_response())
    write_json(bundled, bundled_catalog())

    command = [
        sys.executable,
        str(SCRIPT),
        "--openrouter-json",
        str(openrouter),
        "--bundled-json",
        str(bundled),
        "--output",
        str(output),
        "--no-validate",
    ]
    first = subprocess.run(command, check=False, capture_output=True, text=True)
    assert first.returncode == 0
    assert first.stdout.startswith(f"updated: {output} (2 models;")
    first_mtime = output.stat().st_mtime_ns

    second = subprocess.run(command, check=False, capture_output=True, text=True)
    assert second.returncode == 0
    assert second.stdout.startswith(f"up to date: {output} (2 models;")
    assert output.stat().st_mtime_ns == first_mtime
    assert json.loads(output.read_text(encoding="utf-8"))["models"][0]["slug"] == (
        "vendor/reasoner"
    )


def test_config_selects_output_and_check_is_read_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "codex-home"
    home.mkdir()
    openrouter = tmp_path / "openrouter.json"
    bundled = tmp_path / "bundled.json"
    output = home / "custom-catalog.json"
    write_json(openrouter, openrouter_response())
    write_json(bundled, bundled_catalog())
    (home / "openrouter.config.toml").write_text(
        'model_catalog_json = "custom-catalog.json"\n', encoding="utf-8"
    )
    monkeypatch.setenv("CODEX_HOME", str(home))

    result = generate_catalog.run(
        [
            "--openrouter-json",
            str(openrouter),
            "--bundled-json",
            str(bundled),
            "--check",
            "--no-validate",
        ]
    )
    assert result == 1
    assert not output.exists()


def test_validation_failure_preserves_existing_catalog(tmp_path: Path) -> None:
    output = tmp_path / "catalog.json"
    output.write_text('{"models": []}\n', encoding="utf-8")
    payload = generate_catalog.render_catalog(
        generate_catalog.build_catalog(openrouter_response(), bundled_catalog())
    )

    with pytest.raises(generate_catalog.CatalogError, match="Codex rejected"):
        generate_catalog.install_catalog(
            output,
            payload,
            "/usr/bin/false",
            timeout=5,
            validate=True,
        )

    assert output.read_text(encoding="utf-8") == '{"models": []}\n'
    assert not list(tmp_path.glob(".catalog.json.*"))
