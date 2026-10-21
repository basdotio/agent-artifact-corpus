"""
test_hardware_controller.py — Comprehensive unit tests for all G-Helper hardware domains.
"""

import json
import pytest
from cli_anything_g_helper.core.hardware_controller import (
    GHelperHardwareController,
    PerformanceMode,
    GpuMode,
    AuraMode,
)


def test_resolve_mode_discrete_valid():
    ctrl = GHelperHardwareController()
    assert ctrl.resolve_mode_discrete("turbo") == PerformanceMode.TURBO
    assert ctrl.resolve_mode_discrete("performance") == PerformanceMode.TURBO
    assert ctrl.resolve_mode_discrete("1") == PerformanceMode.TURBO
    assert ctrl.resolve_mode_discrete("balanced") == PerformanceMode.BALANCED
    assert ctrl.resolve_mode_discrete("0") == PerformanceMode.BALANCED
    assert ctrl.resolve_mode_discrete("silent") == PerformanceMode.SILENT
    assert ctrl.resolve_mode_discrete("quiet") == PerformanceMode.SILENT
    assert ctrl.resolve_mode_discrete("2") == PerformanceMode.SILENT


def test_resolve_mode_discrete_invalid():
    ctrl = GHelperHardwareController()
    with pytest.raises(ValueError):
        ctrl.resolve_mode_discrete("unknown_mode_xyz")


def test_resolve_gpu_discrete_valid():
    ctrl = GHelperHardwareController()
    assert ctrl.resolve_gpu_discrete("eco") == GpuMode.ECO
    assert ctrl.resolve_gpu_discrete("mux") == GpuMode.ULTIMATE
    assert ctrl.resolve_gpu_discrete("ultimate") == GpuMode.ULTIMATE
    assert ctrl.resolve_gpu_discrete("standard") == GpuMode.STANDARD
    assert ctrl.resolve_gpu_discrete("hybrid") == GpuMode.STANDARD


def test_resolve_gpu_discrete_invalid():
    ctrl = GHelperHardwareController()
    with pytest.raises(ValueError):
        ctrl.resolve_gpu_discrete("nuclear_option")


def test_resolve_aura_discrete_valid():
    ctrl = GHelperHardwareController()
    assert ctrl.resolve_aura_discrete("static") == AuraMode.STATIC
    assert ctrl.resolve_aura_discrete("breathing") == AuraMode.BREATHING
    assert ctrl.resolve_aura_discrete("color_cycle") == AuraMode.COLOR_CYCLE
    assert ctrl.resolve_aura_discrete("rainbow") == AuraMode.COLOR_CYCLE
    assert ctrl.resolve_aura_discrete("strobing") == AuraMode.STROBING


def test_get_current_state(tmp_path):
    fake_config = tmp_path / "config.json"
    fake_config.write_text(json.dumps({"performance_mode": 1, "charge_limit": 80, "gpu_mode": 1}), encoding="utf-8")
    ctrl = GHelperHardwareController(config_path=fake_config)
    state = ctrl.get_current_state()
    assert state["performance_mode"] == 1
    assert state["charge_limit"] == 80
    assert state["gpu_mode"] == 1


def test_display_validation(tmp_path):
    fake_config = tmp_path / "config.json"
    fake_config.write_text(json.dumps({}), encoding="utf-8")
    ctrl = GHelperHardwareController(config_path=fake_config)
    with pytest.raises(ValueError):
        ctrl.set_display_config(refresh_rate=999)


def test_keyboard_validation(tmp_path):
    fake_config = tmp_path / "config.json"
    fake_config.write_text(json.dumps({}), encoding="utf-8")
    ctrl = GHelperHardwareController(config_path=fake_config)
    with pytest.raises(ValueError):
        ctrl.set_keyboard_backlight(brightness=10)
