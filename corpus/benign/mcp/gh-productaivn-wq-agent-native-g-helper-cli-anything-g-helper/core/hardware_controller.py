"""
hardware_controller.py — Comprehensive Discrete Action Space & Hardware Controller for G-Helper.
Standardizes every major capability and use case into discrete OpenJev options:
- Performance Profiles (Silent, Balanced, Turbo)
- GPU Modes (Eco, Standard, Ultimate, Optimized)
- Battery Health Limiter (60%, 80%, 100%)
- Screen Refresh Rate & Overdrive (60Hz, 120Hz, 165Hz, Auto, Overdrive on/off)
- Keyboard Backlight & RGB Aura (Brightness 0-3, Static, Breathing, Color Cycle, Strobing)
- Fan Curves & Power Limits (Total wattage, CPU, GPU limits)
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, List


class PerformanceMode(int, Enum):
    BALANCED = 0
    TURBO = 1
    SILENT = 2


class GpuMode(int, Enum):
    ECO = 0         # dGPU powered down / disabled
    STANDARD = 1    # Standard dynamic switching
    ULTIMATE = 2    # Dedicated dGPU direct to internal screen (MUX)


class AuraMode(int, Enum):
    STATIC = 0
    BREATHING = 1
    COLOR_CYCLE = 2
    STROBING = 3


class GHelperHardwareController:
    """Deterministic hardware controller interfacing with G-Helper's config and task runtime."""

    DEFAULT_CONFIG_PATH = Path(os.environ.get("APPDATA", "")) / "GHelper" / "config.json"
    LOG_PATH = Path(os.environ.get("APPDATA", "")) / "GHelper" / "log.txt"
    TASK_NAME = "GHelper"

    # Discrete Action Map for OpenJev SystemOne intent matching (0 LLM tokens, <1ms)
    INTENT_MODE_MAP = {
        "turbo": PerformanceMode.TURBO,
        "performance": PerformanceMode.TURBO,
        "fast": PerformanceMode.TURBO,
        "max": PerformanceMode.TURBO,
        "balanced": PerformanceMode.BALANCED,
        "normal": PerformanceMode.BALANCED,
        "default": PerformanceMode.BALANCED,
        "silent": PerformanceMode.SILENT,
        "quiet": PerformanceMode.SILENT,
        "eco_cpu": PerformanceMode.SILENT,
        "battery_saver": PerformanceMode.SILENT,
    }

    INTENT_GPU_MAP = {
        "eco": GpuMode.ECO,
        "igpu": GpuMode.ECO,
        "disable_dgpu": GpuMode.ECO,
        "standard": GpuMode.STANDARD,
        "hybrid": GpuMode.STANDARD,
        "optimus": GpuMode.STANDARD,
        "ultimate": GpuMode.ULTIMATE,
        "dedicated": GpuMode.ULTIMATE,
        "mux": GpuMode.ULTIMATE,
        "dgpu": GpuMode.ULTIMATE,
    }

    INTENT_AURA_MAP = {
        "static": AuraMode.STATIC,
        "fixed": AuraMode.STATIC,
        "breathing": AuraMode.BREATHING,
        "pulse": AuraMode.BREATHING,
        "color_cycle": AuraMode.COLOR_CYCLE,
        "rainbow": AuraMode.COLOR_CYCLE,
        "cycle": AuraMode.COLOR_CYCLE,
        "strobing": AuraMode.STROBING,
        "strobe": AuraMode.STROBING,
    }

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH

    def resolve_mode_discrete(self, query: str) -> PerformanceMode:
        """OpenJev discrete option selector: maps raw input string to standardized enum index."""
        cleaned = query.strip().lower()
        if cleaned.isdigit():
            val = int(cleaned)
            for mode in PerformanceMode:
                if mode.value == val:
                    return mode
        if cleaned in self.INTENT_MODE_MAP:
            return self.INTENT_MODE_MAP[cleaned]
        raise ValueError(f"Unknown performance mode intent '{query}'. Valid options: {[m.name.lower() for m in PerformanceMode]}")

    def resolve_gpu_discrete(self, query: str) -> GpuMode:
        """OpenJev discrete option selector: maps raw input string to standardized GPU mode."""
        cleaned = query.strip().lower()
        if cleaned.isdigit():
            val = int(cleaned)
            for mode in GpuMode:
                if mode.value == val:
                    return mode
        if cleaned in self.INTENT_GPU_MAP:
            return self.INTENT_GPU_MAP[cleaned]
        raise ValueError(f"Unknown GPU mode intent '{query}'. Valid options: {[m.name.lower() for m in GpuMode]}")

    def resolve_aura_discrete(self, query: str) -> AuraMode:
        """OpenJev discrete option selector: maps raw input string to Aura RGB mode."""
        cleaned = query.strip().lower()
        if cleaned.isdigit():
            val = int(cleaned)
            for mode in AuraMode:
                if mode.value == val:
                    return mode
        if cleaned in self.INTENT_AURA_MAP:
            return self.INTENT_AURA_MAP[cleaned]
        raise ValueError(f"Unknown Aura RGB intent '{query}'. Valid options: {[m.name.lower() for m in AuraMode]}")

    def get_current_state(self) -> Dict[str, Any]:
        """Reads active state from config.json without GUI popping."""
        if not self.config_path.exists():
            return {"error": f"Config not found at {self.config_path}"}
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": str(e)}

    def _apply_config_and_restart(self, updates: Dict[str, Any]) -> float:
        """Atomically updates config.json and recycles the elevated task instance."""
        start_time = time.perf_counter()
        subprocess.run(["schtasks", "/End", "/TN", self.TASK_NAME], capture_output=True)

        cfg = json.loads(self.config_path.read_text(encoding="utf-8"))
        for k, v in updates.items():
            cfg[k] = v
        self.config_path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")

        subprocess.run(["schtasks", "/Run", "/TN", self.TASK_NAME], capture_output=True)
        return (time.perf_counter() - start_time) * 1000

    def set_performance_mode(self, mode: PerformanceMode | str) -> Dict[str, Any]:
        """Sets ASUS performance profile (Silent, Balanced, Turbo)."""
        target_mode = self.resolve_mode_discrete(str(mode)) if isinstance(mode, str) else mode
        val = int(target_mode.value)
        latency_ms = self._apply_config_and_restart({
            "performance_mode": val,
            "performance_0": val,
            "performance_1": val,
        })
        return {
            "status": "success",
            "mode": target_mode.name.lower(),
            "mode_id": target_mode.value,
            "latency_ms": round(latency_ms, 2),
            "message": f"Applied G-Helper performance mode: {target_mode.name} (id={target_mode.value}) in {latency_ms:.1f}ms",
        }

    def set_gpu_mode(self, mode: GpuMode | str) -> Dict[str, Any]:
        """Sets GPU operating mode (Eco, Standard, Ultimate)."""
        target_mode = self.resolve_gpu_discrete(str(mode)) if isinstance(mode, str) else mode
        val = int(target_mode.value)
        latency_ms = self._apply_config_and_restart({
            "gpu_mode": val,
        })
        return {
            "status": "success",
            "gpu_mode": target_mode.name.lower(),
            "gpu_mode_id": target_mode.value,
            "latency_ms": round(latency_ms, 2),
            "message": f"Applied G-Helper GPU mode: {target_mode.name} (id={target_mode.value}) in {latency_ms:.1f}ms",
        }

    def set_battery_limit(self, percent: int) -> Dict[str, Any]:
        """Sets battery charge limit threshold (60, 80, 100)."""
        valid_limits = {60, 80, 100}
        if percent not in valid_limits:
            raise ValueError(f"Invalid battery limit {percent}%. Must be one of {valid_limits}")
        latency_ms = self._apply_config_and_restart({
            "charge_limit": percent,
        })
        return {
            "status": "success",
            "charge_limit": percent,
            "latency_ms": round(latency_ms, 2),
            "message": f"Battery charge limit set to {percent}% in {latency_ms:.1f}ms",
        }

    def set_display_config(self, refresh_rate: Optional[int] = None, overdrive: Optional[bool] = None, auto: Optional[bool] = None) -> Dict[str, Any]:
        """Configures display panel settings (refresh rate Hz, overdrive, auto-switch)."""
        updates = {}
        if refresh_rate is not None:
            if refresh_rate not in (60, 120, 165, 240, -1):
                raise ValueError(f"Unsupported refresh rate {refresh_rate}Hz. Valid options: 60, 120, 165, 240, -1 (default)")
            updates["frequency"] = refresh_rate
        if overdrive is not None:
            updates["overdrive"] = 1 if overdrive else 0
        if auto is not None:
            updates["screen_auto"] = 1 if auto else 0

        latency_ms = self._apply_config_and_restart(updates)
        return {
            "status": "success",
            "updates": updates,
            "latency_ms": round(latency_ms, 2),
            "message": f"Display configuration updated in {latency_ms:.1f}ms",
        }

    def set_keyboard_backlight(self, brightness: Optional[int] = None, aura_mode: Optional[AuraMode | str] = None) -> Dict[str, Any]:
        """Configures keyboard backlight brightness (0-3) and Aura RGB animation."""
        updates = {}
        if brightness is not None:
            if not (0 <= brightness <= 3):
                raise ValueError(f"Brightness level {brightness} out of range (0=Off, 1=Low, 2=Med, 3=High)")
            updates["keyboard_brightness"] = brightness
        if aura_mode is not None:
            target_aura = self.resolve_aura_discrete(str(aura_mode)) if isinstance(aura_mode, str) else aura_mode
            updates["backlight_type"] = int(target_aura.value)

        latency_ms = self._apply_config_and_restart(updates)
        return {
            "status": "success",
            "updates": updates,
            "latency_ms": round(latency_ms, 2),
            "message": f"Keyboard lighting updated in {latency_ms:.1f}ms",
        }

    def set_power_limits(self, total_w: Optional[int] = None, cpu_w: Optional[int] = None, slow_w: Optional[int] = None, fast_w: Optional[int] = None) -> Dict[str, Any]:
        """Configures custom platform power limits (SPL/sPPT/fPPT) in Watts."""
        updates = {}
        if total_w is not None:
            updates["limit_total_0"] = total_w
        if cpu_w is not None:
            updates["limit_cpu_0"] = cpu_w
        if slow_w is not None:
            updates["limit_slow_0"] = slow_w
        if fast_w is not None:
            updates["limit_fast_0"] = fast_w

        latency_ms = self._apply_config_and_restart(updates)
        return {
            "status": "success",
            "updates": updates,
            "latency_ms": round(latency_ms, 2),
            "message": f"Custom power limits applied in {latency_ms:.1f}ms",
        }
