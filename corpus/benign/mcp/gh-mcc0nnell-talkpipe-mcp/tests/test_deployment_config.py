"""Reproducible profile validation with no actual Platform secrets."""
import importlib.util
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "audit_tunnel", ROOT / "scripts" / "audit-tunnel-deployment.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class TunnelDeploymentAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="wac-profile-test-")
        self.profile_dir = Path(self.temp.name) / "profile"
        self.profile_dir.mkdir(mode=0o700)
        self.key_path = self.profile_dir / "windanvil-runtime-key"
        self.profile = self.profile_dir / "windanvil-commander.yaml"
        self.python = Path(sys.executable)
        self.blob = (
            "config_version: 1\ncontrol_plane:\n"
            '  base_url: "https://api.openai.com"\n'
            '  tunnel_id: "tunnel_0123456789abcdef0123456789abcdef"\n'
            '  api_key: "file:' + str(self.key_path) + '"\n'
            'health:\n  listen_addr: "127.0.0.1:0"\n'
            "admin_ui:\n  open_browser: false\n"
            "mcp:\n  commands:\n    - channel: main\n"
            '      command: "' + str(self.python) + " -u "
            + str(ROOT / "windanvil_commander_mcp.py") + '"\n'
        )
        self.save(self.blob)

    def tearDown(self):
        self.temp.cleanup()

    def save(self, blob):
        self.profile.write_text(blob)
        self.profile.chmod(0o600)

    def check(self):
        return MODULE.check(self.profile_dir, ROOT, self.python)

    def test_missing_key_is_not_false_connected(self):
        result = self.check()
        self.assertEqual(result["result"], "PASS")
        self.assertFalse(result["remote_connected"])
        self.assertEqual(result["runtime_key"], "not-provisioned")

    def test_secure_key_file_is_only_checked_by_metadata(self):
        self.key_path.write_text("test-only-not-a-real-secret")
        self.key_path.chmod(0o600)
        self.assertEqual(self.check()["runtime_key"], "file-present-secure-permissions")

    def test_world_readable_profile_denied(self):
        self.profile.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "not 0600"):
            self.check()

    def test_world_readable_key_denied(self):
        self.key_path.write_text("test-only")
        self.key_path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, "key mode"):
            self.check()

    def test_inline_or_unexpected_reference_denied(self):
        self.save(self.blob.replace("file:" + str(self.key_path), "sk-proj-test-inline"))
        with self.assertRaisesRegex(ValueError, "private file reference"):
            self.check()

    def test_offhost_command_denied(self):
        self.save(self.blob.replace("windanvil_commander_mcp.py", "talkpipe_mcp.py"))
        with self.assertRaisesRegex(ValueError, "outside"):
            self.check()

    def test_external_health_listener_denied(self):
        self.save(self.blob.replace("127.0.0.1:0", "0.0.0.0:3000"))
        with self.assertRaisesRegex(ValueError, "loopback"):
            self.check()

    def test_symlinked_key_denied(self):
        target = self.profile_dir / "unrelated-key"
        target.write_text("not-a-key")
        target.chmod(0o600)
        self.key_path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "unsafe"):
            self.check()


if __name__ == "__main__":
    unittest.main()
