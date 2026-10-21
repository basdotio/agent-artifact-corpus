"""Offline validation of the private Commander tunnel plugin package."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location(
    "package_commander_plugin", ROOT / "scripts/package-commander-plugin.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
TEST_ID = "tunnel_0123456789abcdef0123456789abcdef"


class CommanderPluginPackageTests(unittest.TestCase):
    def test_valid_tunnel_id_yields_minimal_private_bundle(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bundle.zip"
            MODULE.build(TEST_ID, path)
            with zipfile.ZipFile(path) as z:
                self.assertEqual(len(z.namelist()), 3)
                self.assertTrue(all(x.startswith("windanvil-commander/") for x in z.namelist()))
                self.assertTrue(all(not x.startswith("/") and "../" not in x for x in z.namelist()))
                manifest = json.loads(z.read("windanvil-commander/plugin.json"))
                self.assertEqual(manifest["name"], "windanvil-commander")
                self.assertLessEqual(len(
                    manifest["extensions"]["com.openai"]["interface"]["shortDescription"]), 30)
                mcp = json.loads(z.read("windanvil-commander/mcp.json"))
                server = mcp["mcpServers"]["windanvil-commander"]
                self.assertEqual(server["extensions"]["com.openai"]["tunnelId"], TEST_ID)
                self.assertEqual(server["type"], "streamable-http")
                self.assertNotIn("url", server)
                self.assertNotIn("server_url", server)
                data = b"".join(z.read(x) for x in z.namelist())
                self.assertNotIn(b"api_key:", data)
                self.assertNotIn(b"sk-proj-", data)
                self.assertNotIn(b"-----BEGIN", data)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_invalid_identifiers_denied(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "bundle.zip"
            for supplied in ("", "tunnel_abc", "tunnel_0123456789abcdef0123456789ABCDEF",
                             "https://example.com/mcp", "tunnel_0123456789abcdef0123456789abcdef\nx"):
                with self.subTest(value=supplied), self.assertRaises(ValueError):
                    MODULE.build(supplied, p)

    def test_reproducible_no_secret_archive(self):
        with tempfile.TemporaryDirectory() as folder:
            a, b = Path(folder) / "a.zip", Path(folder) / "b.zip"
            MODULE.build(TEST_ID, a)
            MODULE.build(TEST_ID, b)
            self.assertEqual(a.read_bytes(), b.read_bytes())


if __name__ == "__main__":
    unittest.main()
