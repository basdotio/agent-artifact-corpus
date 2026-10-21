"""Tests for tools.reversing (offline: run_cmd is stubbed to capture argv)."""

import asyncio
import os
import tempfile

import tools.reversing as rev


def run_capturing_disasm(arch):
    calls = []

    async def fake_run_cmd(*a, **k):
        calls.append(a)
        if a[:2] == ("objdump", "-f"):
            return "architecture: i386:x86-64, flags 0x00000112"
        return "(disassembly)"

    orig = rev.run_cmd
    rev.run_cmd = fake_run_cmd
    tf = tempfile.NamedTemporaryFile(suffix=".bin", delete=False)
    tf.write(b"\x7fELF")
    tf.close()
    try:
        asyncio.run(rev.handle_reversing("disassemble", {"filepath": tf.name, "arch": arch}))
    finally:
        rev.run_cmd = orig
        os.unlink(tf.name)
    return [c for c in calls if c[:2] == ("objdump", "-d")][0]


def test_arm_sets_machine_no_intel():
    dcall = run_capturing_disasm("arm")
    assert "-m" in dcall and "arm" in dcall and "intel" not in dcall


def test_x86_64_sets_machine_and_intel():
    dcall = run_capturing_disasm("x86_64")
    assert "i386:x86-64" in dcall and "intel" in dcall


def test_mips_sets_machine_no_intel():
    dcall = run_capturing_disasm("mips")
    assert "mips" in dcall and "intel" not in dcall


def test_auto_detects_x86_and_uses_intel():
    dcall = run_capturing_disasm("auto")
    # fake objdump -f reports x86-64, so auto should apply intel and not force -m
    assert "intel" in dcall
