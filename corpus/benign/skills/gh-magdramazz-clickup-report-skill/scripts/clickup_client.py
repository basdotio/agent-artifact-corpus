"""Shared helpers for the clickup-report skill: config storage and a read-only
ClickUp API v2 client.

Standard library only, so the skill runs anywhere Python 3.8+ runs, whatever
language or framework the user's own project is written in.

Config lives OUTSIDE any project, in the user's config folder:
  Windows:      %APPDATA%\\clickup-report\\config.json
  macOS/Linux:  $XDG_CONFIG_HOME/clickup-report/config.json  (default ~/.config)
Set CLICKUP_REPORT_CONFIG_DIR to use another folder (useful for tests).
"""
import json
import os
import stat
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API = "https://api.clickup.com/api/v2"
CONFIG_DIR_ENV = "CLICKUP_REPORT_CONFIG_DIR"
TOKEN_ENV = "CLICKUP_API_TOKEN"
USER_AGENT = "clickup-report-skill/1.0"


class ClickUpError(Exception):
    """An API call failed. The message never contains the token."""


def utf8_stdout():
    """Windows consoles default to a legacy code page; task names often are not ASCII."""
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


def config_dir():
    override = os.environ.get(CONFIG_DIR_ENV)
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / "clickup-report"
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "clickup-report"


def config_path():
    return config_dir() / "config.json"


def load_config():
    path = config_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_config(cfg):
    """Write atomically and, on POSIX, readable by the owner only (the file holds a token)."""
    folder = config_dir()
    folder.mkdir(parents=True, exist_ok=True)
    if os.name != "nt":
        os.chmod(folder, stat.S_IRWXU)
    path = config_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    if os.name != "nt":
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
    os.replace(tmp, path)
    return path


def resolve_token(cfg):
    """The saved token wins; the environment variable is only a fallback."""
    token = (cfg or {}).get("token") or os.environ.get(TOKEN_ENV, "")
    return token.strip()


def mask(token):
    if not token:
        return "(none)"
    if len(token) <= 10:
        return "****"
    return token[:4] + "…" + token[-4:]


def get(path, token, query=None, retries=3):
    """GET a ClickUp v2 endpoint. Retries on rate limit (429) and 5xx."""
    url = API + path
    if query:
        url += "?" + urllib.parse.urlencode(query, doseq=True)
    request = urllib.request.Request(url, headers={
        "Authorization": token,
        "Accept": "application/json",
        "User-Agent": USER_AGENT,
    })
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", "replace")[:300]
            if err.code == 429 and attempt < retries:
                reset = err.headers.get("X-RateLimit-Reset", "")
                wait = int(reset) - int(time.time()) if reset.isdigit() else 5 * 2 ** attempt
                time.sleep(min(max(wait, 1), 65))
                continue
            if err.code >= 500 and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            hint = {
                401: "the token was rejected (wrong, expired or revoked)",
                403: "the token has no access to this workspace or task",
                404: "not found (check the workspace/team id)",
            }.get(err.code, "")
            raise ClickUpError(f"HTTP {err.code} on GET {path}: {hint} {body}".strip())
        except urllib.error.URLError as err:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise ClickUpError(f"network error on GET {path}: {err.reason}")
    raise ClickUpError(f"GET {path} failed after {retries} retries")


def emit(obj):
    """Print one JSON object; the calling agent parses this output."""
    print(json.dumps(obj, indent=2, ensure_ascii=False))
