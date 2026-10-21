"""Offline tests of the Commander tunnel watchdog; no Platform credentials needed."""
import contextlib
import importlib.util
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parent.parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tunnel = load("supervise_commander_tunnel", ROOT / "scripts/supervise-commander-tunnel.py")
cron = load("manage_tunnel_cron", ROOT / "scripts/manage-tunnel-cron.py")


class TunnelSupervisorTests(unittest.TestCase):
    def test_only_loopback_health_url_allowed(self):
        for value in ("http://127.0.0.1:40031", "http://127.0.0.1:5/"):
            self.assertEqual(tunnel.valid_health_base(value).rstrip("/"),
                             value.rstrip("/"))
        for value in ("http://0.0.0.0:40031", "https://127.0.0.1:40031",
                      "http://localhost:40031", "http://127.0.0.1:0",
                      "http://127.0.0.1:65536", "http://127.0.0.1:40031/mcp",
                      "http://127.0.0.1:40031@evil.example", "file:///tmp/health"):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                tunnel.valid_health_base(value)

    def test_health_file_mode_and_symlink_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "health.url"
            path.write_text("http://127.0.0.1:40031")
            path.chmod(0o600)
            with mock.patch.object(tunnel, "HEALTH_FILE", path):
                self.assertEqual(tunnel.read_health_url(), "http://127.0.0.1:40031")
                path.chmod(0o644)
                with self.assertRaises(RuntimeError):
                    tunnel.read_health_url()
            target = Path(folder) / "target"
            target.write_text("http://127.0.0.1:40031")
            target.chmod(0o600)
            path.unlink()
            path.symlink_to(target)
            with mock.patch.object(tunnel, "HEALTH_FILE", path):
                with self.assertRaises(RuntimeError):
                    tunnel.read_health_url()

    def test_readiness_checks_both_endpoints(self):
        response = mock.MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with mock.patch.object(tunnel.urllib.request, "urlopen", return_value=response) as openurl:
            self.assertTrue(tunnel.readiness("http://127.0.0.1:4545"))
            self.assertEqual([call.args[0].full_url for call in openurl.call_args_list],
                             ["http://127.0.0.1:4545/healthz",
                              "http://127.0.0.1:4545/readyz"])

    def test_existing_legacy_session_never_creates_duplicate(self):
        with tempfile.TemporaryDirectory() as folder:
            state = Path(folder)
            state.chmod(0o700)
            with mock.patch.multiple(tunnel, STATE=state, LOCK=state / "lock"), \
                 mock.patch.object(tunnel, "verify_configuration"), \
                 mock.patch.object(tunnel, "running_pids", return_value=[42]), \
                 mock.patch.object(tunnel, "read_health_url", return_value=None), \
                 mock.patch.object(tunnel.subprocess, "Popen") as spawn, \
                 contextlib.redirect_stdout(io.StringIO()) as out:
                with mock.patch.object(sys, "argv", ["supervisor", "start"]):
                    tunnel.main()
                self.assertIn("legacy-session-running", out.getvalue())
                spawn.assert_not_called()


class TunnelCronTests(unittest.TestCase):
    def test_template_has_only_two_fixed_entries(self):
        lines = [line for line in (ROOT / "ops/tunnel-cron.example").read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual(len(lines), 2)
        self.assertTrue(lines[0].startswith("@reboot "))
        self.assertTrue(lines[1].startswith("*/5 "))
        for line in lines:
            self.assertIn("/scripts/supervise-commander-tunnel.py start", line)
            self.assertNotIn("api_key", line)

    def test_cron_install_preserves_unrelated_jobs_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            state = base / "state"
            state.mkdir(mode=0o700)
            original = "*/2 * * * * /home/commander/.local/bin/commander-watchdog\n"
            active = [original]
            written = []

            def fake_run(cmd, **kwargs):
                if cmd == ["crontab", "-l"]:
                    return subprocess.CompletedProcess(cmd, 0, active[0], "")
                if len(cmd) == 2 and cmd[0] == "crontab":
                    text = Path(cmd[1]).read_text()
                    written.append(text)
                    active[0] = text
                    return subprocess.CompletedProcess(cmd, 0, "", "")
                raise AssertionError(cmd)

            with mock.patch.multiple(cron, HOME=base, STATE=state), \
                 mock.patch.object(cron.subprocess, "run", side_effect=fake_run), \
                 contextlib.redirect_stdout(io.StringIO()):
                cron.reconcile("install")
                cron.reconcile("check")
                cron.reconcile("install")
            self.assertEqual(len(written), 1)
            self.assertIn(original.strip(), active[0])
            self.assertEqual(active[0].count("supervise-commander-tunnel.py start"), 2)
            logfile = state / "windanvil-tunnel-cron.log"
            self.assertEqual(logfile.stat().st_mode & 0o777, 0o600)

    def test_unknown_cron_entry_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            with mock.patch.multiple(cron, HOME=base, STATE=base), \
                 mock.patch.object(cron.subprocess, "run",
                     return_value=subprocess.CompletedProcess(
                         [], 0, "* * * * * /tmp/scripts/supervise-commander-tunnel.py start\n", "")):
                with self.assertRaisesRegex(RuntimeError, "unexpected"):
                    cron.reconcile("install")


if __name__ == "__main__":
    unittest.main()
