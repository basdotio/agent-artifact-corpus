"""
test_utils_run_cmd.py — unit tests for _utils.run_cmd.

subprocess.run(timeout=X) is not an actual hard bound on Windows -- after
killing a timed-out process it makes an UNTIMED recovery communicate() call
to drain stdout/stderr, which can hang forever if a descendant still holds
the pipe handles open. This was hit for real: a child stuck in an infinite
loop blocked its caller for 30+ minutes instead of the configured 15s.
run_cmd runs the subprocess call in a daemon thread and bounds the CALLER's
wait with .join(timeout+grace), so run_cmd itself can never hang past that
bound -- the same "bound the caller, not the hung work" approach the
gateway's run_tool timeout uses.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

_TOOLS_DIR = Path(__file__).parent.parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import _utils  # noqa: E402


class TestRunCmdBasics:
    def test_success_returns_stdout_and_zero_returncode(self):
        result = _utils.run_cmd([sys.executable, "-c", "print('hello')"])
        assert result["returncode"] == 0
        assert "hello" in result["stdout"]

    def test_nonzero_exit_returned_not_raised(self):
        result = _utils.run_cmd([sys.executable, "-c", "import sys; sys.exit(3)"])
        assert result["returncode"] == 3

    def test_stderr_captured(self):
        result = _utils.run_cmd(
            [sys.executable, "-c", "import sys; sys.stderr.write('oops')"]
        )
        assert "oops" in result["stderr"]

    def test_missing_executable_raises_command_not_found(self):
        with pytest.raises(RuntimeError, match="CommandNotFound"):
            _utils.run_cmd(["this-executable-does-not-exist-xyz"])

    def test_env_vars_passed_through_to_child(self):
        result = _utils.run_cmd(
            [sys.executable, "-c", "import os; print(os.environ.get('MY_TEST_VAR', ''))"],
            env={"MY_TEST_VAR": "abc123"},
        )
        assert "abc123" in result["stdout"]

    def test_cwd_respected(self, tmp_path):
        marker = tmp_path / "marker.txt"
        marker.write_text("here", encoding="utf-8")
        result = _utils.run_cmd(
            [sys.executable, "-c", "import os; print(os.listdir('.'))"],
            cwd=tmp_path,
        )
        assert "marker.txt" in result["stdout"]

    def test_undecodable_output_is_replaced_not_raised(self):
        # 0x9d is undefined in cp1252 and invalid as a lone UTF-8 byte, so it
        # can't be decoded under either locale. Before errors="replace" this
        # raised UnicodeDecodeError out of run_cmd (a curly quote in a child's
        # output crashed a long batch run). Surrounding text must survive intact.
        result = _utils.run_cmd([
            sys.executable, "-c",
            "import sys; sys.stdout.buffer.write(b'before\\x9dafter'); "
            "sys.stderr.buffer.write(b'err\\x9d')",
        ])
        assert result["returncode"] == 0
        assert result["stdout"] == "before�after"
        assert result["stderr"] == "err�"


class TestRunCmdTimeout:
    def test_real_timeout_raises_within_reasonable_bound(self):
        start = time.monotonic()
        with pytest.raises(RuntimeError, match="TimeoutExceeded"):
            _utils.run_cmd([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
        elapsed = time.monotonic() - start
        # Should fire close to the 1s timeout, not wait out the full grace window.
        assert elapsed < 5

    def test_underlying_subprocess_hang_still_bounded_by_grace_period(self, monkeypatch):
        # Simulates the real Windows bug: subprocess.run() itself never
        # returns, even past its own timeout= argument. run_cmd must still
        # return control to the caller instead of hanging forever.
        def fake_run(*a, **k):
            time.sleep(9999)  # never returns within any test's patience

        monkeypatch.setattr(_utils.subprocess, "run", fake_run)

        start = time.monotonic()
        with pytest.raises(RuntimeError, match="TimeoutExceeded"):
            _utils.run_cmd(["irrelevant"], timeout=1)
        elapsed = time.monotonic() - start

        # Bounded by timeout(1) + the hardcoded grace period, not truly infinite.
        assert elapsed < 15

    def test_timeout_error_message_names_the_command(self):
        with pytest.raises(RuntimeError, match="sleep"):
            _utils.run_cmd([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
