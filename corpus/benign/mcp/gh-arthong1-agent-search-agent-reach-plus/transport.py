"""Bounded HTTP and CLI execution; credentials stay out of errors."""
from __future__ import annotations

import asyncio
import importlib.util
import ipaddress
import json
import os
import re
import shutil
import socket
import sys
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import httpx

from .process_owner import ProcessOwner

MAX_BYTES = 2_000_000
ROOT = Path(os.environ.get("AGENT_REACH_PLUS_HOME", str(Path.home() / ".agent-reach/tools/agent-reach-plus")))


def bound_executable(name: str) -> str | None:
    """Resolve installer-recorded tools even when desktop PATH lacks Homebrew."""
    try:
        candidate = json.loads((ROOT / "bindings.json").read_text(encoding="utf-8")).get(name)
        if isinstance(candidate, str) and Path(candidate).is_absolute() and Path(candidate).is_file():
            return candidate
    except (OSError, ValueError, AttributeError):
        pass
    executable = shutil.which(name + ".exe") if sys.platform == "win32" else None
    executable = executable or shutil.which(name)
    if executable:
        return executable
    if sys.platform == "darwin":
        for directory in ("/opt/homebrew/opt/node@24/bin", "/usr/local/opt/node@24/bin", "/opt/homebrew/bin", "/usr/local/bin"):
            candidate = Path(directory) / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate)
    return None


class ReachError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = redact(message)
        super().__init__(self.message)


def redact(text: str) -> str:
    text = re.sub(r"(?i)(Bearer\s+)[^\s,\"']+", r"\1[REDACTED]", str(text))
    return re.sub(r"(?i)((?:api[_-]?key|tavilyApiKey|auth_token|ct0|token|cookie|password)\s*[=:]\s*[\"']?)[^\s&\"',;]+", r"\1[REDACTED]", text)


def validate_query(query: str) -> str:
    if not isinstance(query, str):
        raise ReachError("invalid_input", "query must be a string")
    query = query.strip()
    if not query or len(query) > 1000 or query.startswith("-") or any(ord(c) < 32 for c in query):
        raise ReachError("invalid_input", "query must be 1-1000 characters without controls or leading options")
    return query


def validate_limit(limit: int, max_value: int = 20) -> int:
    if type(limit) is not int or not 1 <= limit <= max_value:
        raise ReachError("invalid_input", f"limit must be an integer from 1 to {max_value}")
    return limit


async def resolve_public_url(url: str) -> tuple[str, str]:
    if not isinstance(url, str) or len(url) > 4096 or any(ord(c) < 33 for c in url) or "\\" in url:
        raise ReachError("invalid_url", "use a public http(s) URL")
    try:
        p = urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname or p.username is not None or p.password is not None or p.port not in (None, 80, 443):
            raise ValueError()
        host = p.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError()
        addresses = await asyncio.wait_for(asyncio.to_thread(socket.getaddrinfo, host, p.port or (443 if p.scheme == "https" else 80), type=socket.SOCK_STREAM), 8)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError()
    except (ValueError, OSError, asyncio.TimeoutError) as e:
        raise ReachError("invalid_url", "URL must resolve to a public internet address on port 80/443") from e
    addresses.sort(key=lambda a: ":" in a[4][0])
    return url, addresses[0][4][0]


async def validate_url(url: str) -> str:
    return (await resolve_public_url(url))[0]


async def fetch_bytes(url: str, params=None, headers=None) -> bytes:
    defaults = {"User-Agent": "Agent-Reach-Plus/0.1", "Accept": "text/plain,application/json,*/*"}
    defaults.update(headers or {})
    try:
        async with httpx.AsyncClient(timeout=25, follow_redirects=False, trust_env=False) as client:
            for _ in range(5):
                url, address = await resolve_public_url(url)
                parsed = httpx.URL(url)
                request_url = parsed.copy_with(host=address)
                request_headers = {**defaults, "Host": parsed.netloc.decode("ascii")}
                async with client.stream("GET", request_url, params=params, headers=request_headers, extensions={"sni_hostname": parsed.host}) as response:
                    if response.is_redirect:
                        url = urljoin(url, response.headers.get("location", ""))
                        params = None
                        continue
                    if response.status_code in (401, 403):
                        raise ReachError("access_denied", "source requires login or denied this request")
                    if response.status_code == 429:
                        raise ReachError("rate_limited", "source rate limit reached; retry later")
                    response.raise_for_status()
                    chunks, size = [], 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise ReachError("output_too_large", "source exceeds 2 MB response limit")
                        chunks.append(chunk)
                    return b"".join(chunks)
    except httpx.TimeoutException as e:
        raise ReachError("timeout", "HTTP request timeout") from e
    except httpx.HTTPError as e:
        raise ReachError("http_error", f"source HTTP failure ({type(e).__name__})") from e
    raise ReachError("redirect_limit", "too many HTTP redirects")


async def get_json(url: str, params=None, headers=None):
    try:
        return json.loads(await fetch_bytes(url, params, headers))
    except (ValueError, UnicodeError) as e:
        raise ReachError("invalid_response", "source did not return valid JSON") from e


def cli_argv(name: str) -> list[str]:
    if name == "yt-dlp":
        if importlib.util.find_spec("yt_dlp"):
            return [sys.executable, "-m", "yt_dlp"]
        raise ReachError("setup_required", "yt-dlp module is not installed")
    if name == "twitter":
        if importlib.util.find_spec("twitter_cli"):
            return [sys.executable, "-m", "agent_reach_plus.twitter_guard"]
        raise ReachError("setup_required", "Twitter guard module unavailable; stock executable fallback is disabled")
    if name in ("mcporter", "opencli"):
        package = "mcporter" if name == "mcporter" else "@jackwener/opencli"
        bases = [ROOT / "node-tools/node_modules", ROOT / "work/node-tools/node_modules"]
        if os.environ.get("APPDATA"):
            bases.append(Path(os.environ["APPDATA"]) / "npm/node_modules")
        for base in bases:
            folder = base / package
            if (folder / "package.json").is_file():
                metadata = json.loads((folder / "package.json").read_text(encoding="utf-8"))
                entry = metadata["bin"]
                entry = entry[name] if isinstance(entry, dict) else entry
                node = bound_executable("node")
                if node and (folder / entry).is_file():
                    return [node, str(folder / entry)]
    elif name in ("gh", "bili", "twitter", "rdt"):
        local = Path(sys.executable).parent / (name + (".exe" if sys.platform == "win32" else ""))
        executable = str(local) if local.is_file() else bound_executable(name)
        if executable and Path(executable).suffix.lower() not in (".cmd", ".bat", ".ps1"):
            return [executable]
    raise ReachError("setup_required", f"{name} backend is not installed; see setup guide")


def has_cli(name: str) -> bool:
    try:
        cli_argv(name)
        return True
    except ReachError:
        return False


async def run_cli(name: str, args: list[str], timeout=45, env=None) -> str:
    child_env = dict(os.environ)
    child_env.update({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    child_env.pop("OPENCLI_DAEMON_PORT", None)
    child_env.update(env or {})
    command = cli_argv(name) + args
    owner = ProcessOwner()
    try:
        process = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.DEVNULL, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=child_env, **owner.launch_options())
        owner.attach(process)
    except BaseException:
        owner.close()
        if "process" in locals() and process.returncode is None:
            process.kill()
        raise

    async def collect(stream):
        parts, size = [], 0
        while chunk := await stream.read(65536):
            size += len(chunk)
            if size > MAX_BYTES:
                raise ReachError("output_too_large", "CLI output exceeds 2 MB limit")
            parts.append(chunk)
        return b"".join(parts).decode("utf-8", errors="replace")

    tasks = [asyncio.create_task(collect(process.stdout)), asyncio.create_task(collect(process.stderr))]
    try:
        async with asyncio.timeout(timeout):
            out, err = await asyncio.gather(*tasks)
            await process.wait()
        if process.returncode:
            # Raw CLI errors may contain credentials. Return classification, never stderr.
            combined = (out + err).lower()
            code = "rate_limited" if "429" in combined else "setup_required" if any(x in combined for x in ("login", "cookie", "auth", "connect", "extension")) else "backend_error"
            raise ReachError(code, f"{name} failed (exit {process.returncode}); check backend/login or retry later")
        return out
    except TimeoutError as e:
        raise ReachError("timeout", f"{name} timeout after {timeout}s") from e
    finally:
        owner.close()
        if process.returncode is None:
            try:
                process.kill()
            except ProcessLookupError:
                pass
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await asyncio.wait_for(process.wait(), timeout=2)
        except TimeoutError:
            pass


run_cli.twitter_env_only = True


def bounded(data, max_chars: int = 30000) -> dict:
    text = json.dumps(data, ensure_ascii=False, default=str)
    if len(text) <= max_chars:
        return {"truncated": False, "data": data}
    return {"truncated": True, "preview": text[:max_chars], "original_chars": len(text)}
