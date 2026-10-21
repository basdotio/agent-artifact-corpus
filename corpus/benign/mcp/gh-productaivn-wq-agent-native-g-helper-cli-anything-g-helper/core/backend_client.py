"""Real backend execution client binding to g_helper."""
import subprocess
import json
import urllib.request
import urllib.error

class BackendEngineClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8080"):
        self.base_url = base_url

    def get_status(self) -> dict:
        try:
            req = urllib.request.Request(f"{self.base_url}/stats.json", headers={"User-Agent": "AgentHarness"})
            with urllib.request.urlopen(req, timeout=3) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            return {"status": "offline", "error": str(e), "base_url": self.base_url}

    def execute_headless_command(self, cmd: list) -> subprocess.CompletedProcess:
        """Executes native backend headlessly without desktop window."""
        return subprocess.run(cmd, capture_output=True, text=True)
