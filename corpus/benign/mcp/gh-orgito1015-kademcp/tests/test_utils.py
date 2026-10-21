"""Tests for tools.utils helpers."""

import asyncio
import os

import tools.utils as U
from tools.utils import clamp_int, decode_input, resolve_workspace_path, run_cmd


def test_clamp_int_bounds():
    assert clamp_int(-5, 15, 1, 18) == 1
    assert clamp_int(999, 15, 1, 18) == 18
    assert clamp_int(10, 15, 1, 18) == 10
    assert clamp_int("junk", 15, 1, 18) == 15
    assert clamp_int(None, 7, 1, 18) == 7


def test_workspace_confinement_allows_inside(tmp_path):
    old = U.WORKSPACE
    U.WORKSPACE = str(tmp_path)
    try:
        inside = tmp_path / "a.bin"
        inside.write_bytes(b"x")
        real, err = resolve_workspace_path(str(inside))
        assert err is None
        assert real == os.path.realpath(str(inside))
    finally:
        U.WORKSPACE = old


def test_workspace_confinement_rejects_outside(tmp_path):
    old = U.WORKSPACE
    U.WORKSPACE = str(tmp_path)
    try:
        real, err = resolve_workspace_path("/etc/passwd")
        assert real is None
        assert "outside the allowed workspace" in err
    finally:
        U.WORKSPACE = old


def test_no_workspace_is_unrestricted():
    old = U.WORKSPACE
    U.WORKSPACE = None
    try:
        real, err = resolve_workspace_path("/etc/passwd")
        assert err is None
        assert real == os.path.realpath("/etc/passwd")
    finally:
        U.WORKSPACE = old


def test_decode_input_hex_and_raw():
    assert decode_input("0x4142") == b"AB"
    assert decode_input("4142") == b"AB"          # assume_hex default
    assert decode_input("key ", assume_hex=False) == b"key "   # boundary space preserved


def test_run_cmd_timeout_kills_process_group():
    # sh spawns a child `sleep 30`; without a process-group kill the child lingers.
    out = asyncio.run(run_cmd("sh", "-c", "sleep 30 & wait", timeout=2))
    assert "timed out" in out
