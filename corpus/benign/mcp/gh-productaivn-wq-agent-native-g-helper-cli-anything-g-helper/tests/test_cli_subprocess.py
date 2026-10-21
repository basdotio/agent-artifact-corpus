import subprocess
import json
import sys

def test_cli_help():
    cmd = [sys.executable, "-m", "cli_anything_g_helper.cli", "--help"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "cli-anything-" in res.stdout or "g_helper" in res.stdout

def test_cli_json_envelope():
    cmd = [sys.executable, "-m", "cli_anything_g_helper.cli", "--json", "session", "undo"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    data = json.loads(res.stdout)
    assert "status" in data
    assert data["status"] == "success"
    assert "data" in data
