"""FastMCP 4 server. Defaults to simulation; returns dictionaries.

Real mode requires PRINTER_MODE=real. Execution additionally requires the
operator to set PRINTER_ALLOW_MOTION=1 before starting this process.
"""
import asyncio
import copy
import os
import threading
import time
import uuid

from fastmcp import FastMCP
from printer_client import MockPrinter, SSHPrinter, checked, run_prepared
from printer_watchdog import STARTUP_ZERO_WINDOW

mcp = FastMCP('Photonics Simple Printer')
mode = os.getenv('PRINTER_MODE', 'mock')
if mode not in ('mock', 'real'):
    raise ValueError('PRINTER_MODE must be mock or real')
printer = MockPrinter() if mode == 'mock' else SSHPrinter()
pending = {}
pending_lock = threading.Lock()
motion_lock = threading.Lock()


def preview_impl(steps, speed_mm_s, z_speed_mm_s=2.0):
    prepared = checked(printer, {'action': 'preview', 'steps': steps, 'speed_mm_s': speed_mm_s,
                                 'z_speed_mm_s': z_speed_mm_s})['plan']
    token = uuid.uuid4().hex
    now = time.monotonic()
    with pending_lock:
        for key in list(pending):
            if pending[key]['expires'] < now:
                del pending[key]
        if len(pending) >= 100:
            raise ValueError('Too many pending previews')
        pending[token] = {'steps': copy.deepcopy(steps), 'speed': speed_mm_s,
                          'plan': prepared, 'expires': now + 120}
    return {'ok': True, 'simulated': printer.simulated, 'token': token, 'expires_in_seconds': 120,
            'start': prepared['start'], 'targets': prepared['targets'], 'bounds': prepared['bounds'],
            'z_bounds': prepared['z_bounds'], 'z_speed_mm_s': prepared['z_speed_mm_s'],
            'step_speeds_mm_s': prepared['step_speeds_mm_s'],
            'startup_zero_window_seconds': STARTUP_ZERO_WINDOW,
            'speed_mm_s': prepared['speed_mm_s'], 'nominal_seconds': prepared['nominal_seconds']}


def execute_impl(token, operator_confirmed):
    if operator_confirmed is not True:
        raise ValueError('Operator confirmation of the reviewed path is required')
    if not printer.simulated and os.getenv('PRINTER_ALLOW_MOTION') != '1':
        raise ValueError('Real MCP motion disabled; operator must set PRINTER_ALLOW_MOTION=1 locally')
    if not motion_lock.acquire(blocking=False):
        raise ValueError('A sequence is already executing')
    try:
        with pending_lock:
            prepared = pending.pop(token, None)
        if prepared is None or prepared['expires'] < time.monotonic():
            raise ValueError('Preview token is missing, expired, or already used')
        return run_prepared(printer, prepared['steps'], prepared['speed'], prepared['plan'])
    finally:
        motion_lock.release()


@mcp.tool
async def printer_status() -> dict:
    """Read printer state, estimated live position and mesh; never moves."""
    return await asyncio.to_thread(checked, printer, {'action': 'status'})


@mcp.tool
async def preview_sequence(steps: list[dict], speed_mm_s: float = 20.0, z_speed_mm_s: float = 2.0) -> dict:
    """Validate all XYZ steps and return a 120-second, single-use preview token.

    Step example: {"axis": "x", "distance_mm": 50}. Negative distance moves back.
    Axes x/y/z are supported. Bounds: X/Y 0..200 mm, Z 0..235 mm.
    X/Y speed <=20 mm/s; Z speed <=2 mm/s. No heaters or homing.
    Live XYZ=0 with zero velocity may be missing telemetry for up to 0.5s at startup.
    """
    return await asyncio.to_thread(preview_impl, steps, speed_mm_s, z_speed_mm_s)


@mcp.tool
async def execute_sequence(token: str, operator_confirmed: bool = False) -> dict:
    """Execute the reviewed sequence once, only after the operator approves it.

    Uses on-printer status monitoring and automatic emergency-stop requests.
    Do not retry failed/uncertain movement without inspecting the hardware.
    """
    return await asyncio.to_thread(execute_impl, token, operator_confirmed)


@mcp.tool
async def emergency_stop() -> dict:
    """Dedicated emergency shutdown, independent of the movement lock; manual recovery required."""
    return await asyncio.to_thread(checked, printer, {'action': 'stop'})


if __name__ == '__main__':
    mcp.run(transport='stdio')
