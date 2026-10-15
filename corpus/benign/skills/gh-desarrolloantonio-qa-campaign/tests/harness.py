"""Shared plumbing for the harness's own tests (SKILL.md R8).

Every test here runs against `stub_adb.py`, its own `qa.config.json`, its own HOME and its own lock
folder: no device is touched, nothing outside the temp folder is written, and the whole suite passes
with every phone unplugged. What is being tested is the harness's own contract — what it refuses, what
it counts, and what it says it proved.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
UI = os.path.join(REPO, "harness", "android", "ui.py")
NET = os.path.join(REPO, "harness", "net.sh")
REDCHECK = os.path.join(REPO, "harness", "redcheck.py")
FAKE_SERVER = os.path.join(REPO, "harness", "fake_server.py")

PKG = "com.example.app"


class Case(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="qa-harness-test-")
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.adb = os.path.join(self.dir, "adb")
        shutil.copy(os.path.join(HERE, "stub_adb.py"), self.adb)
        os.chmod(self.adb, 0o755)
        self.log = os.path.join(self.dir, "adb.log")
        self.config_path = os.path.join(self.dir, "qa.config.json")
        self.write_config()

    # ── the device the tests describe ──────────────────────────────────────────────────────────────
    def write_config(self, **over):
        config = {
            "campaign": "harness self-test",
            "android": {"package": PKG},
            "devices": {"phone": "emulator-5554"},
            "server": {"url": "http://10.0.2.2:18099"},
        }
        config.update(over)
        with open(self.config_path, "w") as fh:
            json.dump(config, fh)

    def with_dump(self, xml, name="dump.xml"):
        path = os.path.join(self.dir, name)
        with open(path, "w") as fh:
            fh.write(xml)
        return path

    def env(self, **over):
        env = dict(os.environ)
        env.pop("ANDROID_SERIAL", None)
        env.update({
            "HOME": self.dir,
            "QA_LOCK_DIR": os.path.join(self.dir, "locks"),
            "QA_CONFIG": self.config_path,
            "ADB": self.adb,
            "STUB_LOG": self.log,
            "STUB_SERIAL": "emulator-5554",
            "STUB_FRONT": PKG,
        })
        env.update({k: str(v) for k, v in over.items()})
        return env

    # ── running the thing under test ───────────────────────────────────────────────────────────────
    def run_ui(self, *args, **over):
        return self._run(["python3", UI, *args], over)

    def run_net(self, *args, **over):
        return self._run(["bash", NET, *args], over)

    def run_redcheck(self, *args, **over):
        return self._run(["python3", REDCHECK, *args], over)

    def _run(self, cmd, over):
        cwd = over.pop("cwd", self.dir)
        return subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                              cwd=cwd, env=self.env(**over))

    # ── what the harness did, and did not, send to the device ──────────────────────────────────────
    def adb_calls(self):
        if not os.path.isfile(self.log):
            return []
        with open(self.log) as fh:
            return [line.strip() for line in fh if line.strip()]

    def assertNoInput(self, why="the harness refused, so nothing may have been sent"):
        sent = [c for c in self.adb_calls() if "input tap" in c or "input swipe" in c or "input text" in c]
        self.assertEqual([], sent, why)

    def assertSaid(self, result, text):
        self.assertIn(text, result.stdout + result.stderr,
                      f"expected {text!r}\n--- stdout ---\n{result.stdout}\n--- stderr ---\n{result.stderr}")
