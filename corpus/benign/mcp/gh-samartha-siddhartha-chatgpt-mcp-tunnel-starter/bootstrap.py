"""Configure and run the local MCP through OpenAI Secure MCP Tunnel."""

from __future__ import annotations

import getpass
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parent
MAIN_FILE = PROJECT_DIR / "main.py"
DEFAULT_CONFIG = {
    "profile": "stock-ohlc",
    "entrypoint": "main.py",
    "mcp_name": "Stock OHLC MCP",
}
TUNNEL_ID_PATTERN = re.compile(r"^tunnel_[0-9a-f]{32}$")


def _redact(text: str, runtime_key: str | None) -> str:
    """Keep child-process output useful without echoing the runtime key."""

    if runtime_key:
        return text.replace(runtime_key, "[redacted]")
    return text


def _print_output(result: subprocess.CompletedProcess[str], runtime_key: str | None) -> None:
    output = "".join(part for part in (result.stdout, result.stderr) if part)
    if output:
        print(_redact(output, runtime_key), end="")


def _load_config() -> dict[str, str]:
    config_path = PROJECT_DIR / "config.json"
    config = dict(DEFAULT_CONFIG)

    if config_path.exists():
        try:
            loaded: Any = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Could not read {config_path.name}: {exc}") from exc
        if not isinstance(loaded, dict):
            raise RuntimeError("config.json must contain a JSON object.")
        for key in config:
            value = loaded.get(key)
            if value is not None:
                if not isinstance(value, str) or not value.strip():
                    raise RuntimeError(f"config.json field '{key}' must be a non-empty string.")
                config[key] = value.strip()

    return config


def _entrypoint_path(entrypoint: str) -> Path:
    candidate = (PROJECT_DIR / entrypoint).resolve()
    try:
        candidate.relative_to(PROJECT_DIR)
    except ValueError as exc:
        raise RuntimeError("The configured entrypoint must stay inside the project directory.") from exc
    if not candidate.is_file():
        raise RuntimeError(f"MCP entrypoint not found: {candidate}")
    return candidate


def _require_command(name: str, install_hint: str) -> str:
    command = shutil.which(name)
    if command:
        return command
    print(install_hint)
    raise SystemExit(1)


def _read_tunnel_id() -> str:
    tunnel_id = os.getenv("CONTROL_PLANE_TUNNEL_ID", "").strip()
    if not tunnel_id:
        tunnel_id = input("Enter your OpenAI Tunnel ID: ").strip()
    if not TUNNEL_ID_PATTERN.fullmatch(tunnel_id):
        print("Invalid Tunnel ID. Expected tunnel_ followed by 32 lowercase hexadecimal characters.")
        raise SystemExit(1)
    print("✓ Tunnel ID validated")
    return tunnel_id


def _read_runtime_key() -> str:
    runtime_key = os.getenv("CONTROL_PLANE_API_KEY", "")
    if not runtime_key:
        runtime_key = getpass.getpass("Enter your OpenAI Runtime API Key: ")
    if not runtime_key:
        print("A Runtime API Key is required.")
        raise SystemExit(1)
    print("✓ Runtime key received")
    return runtime_key


def _run_capture(
    args: list[str],
    env: dict[str, str],
    runtime_key: str,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        args,
        cwd=PROJECT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    _print_output(result, runtime_key)
    return result


def _profile_exists(tunnel_client: str, profile: str, env: dict[str, str], runtime_key: str) -> bool:
    result = subprocess.run(
        [tunnel_client, "profiles", "list", "--json"],
        cwd=PROJECT_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return False
    try:
        profiles = json.loads(result.stdout or "[]")
    except json.JSONDecodeError:
        return False
    return any(isinstance(item, dict) and item.get("name") == profile for item in profiles)


def _configure_profile(
    tunnel_client: str,
    profile: str,
    tunnel_id: str,
    mcp_command: str,
    env: dict[str, str],
    runtime_key: str,
) -> None:
    args = [
        tunnel_client,
        "init",
        "--sample",
        "sample_mcp_stdio_local",
        "--profile",
        profile,
        "--tunnel-id",
        tunnel_id,
        "--mcp-command",
        mcp_command,
    ]
    if _profile_exists(tunnel_client, profile, env, runtime_key):
        print("Existing tunnel-client profile detected.")
        print("Reusing or refreshing profile...")
        args.append("--force")

    result = _run_capture(args, env, runtime_key)
    if result.returncode == 0:
        print("✓ Tunnel profile configured")
        return

    print("Tunnel profile configuration failed.")
    print("If the profile already exists and this tunnel-client version does not support --force, run:")
    print(f"tunnel-client init --force --profile {profile} --tunnel-id <TUNNEL_ID> --mcp-command '<MCP_COMMAND>'")
    raise SystemExit(result.returncode or 1)


def _validate_tunnel(
    tunnel_client: str,
    profile: str,
    env: dict[str, str],
    runtime_key: str,
) -> None:
    result = _run_capture(
        [tunnel_client, "doctor", "--profile", profile, "--explain"],
        env,
        runtime_key,
    )
    if result.returncode != 0:
        print("Tunnel validation failed.")
        print("Review the tunnel-client output above.")
        raise SystemExit(result.returncode or 1)
    print("✓ Tunnel configuration validated")


def _run_tunnel(
    tunnel_client: str,
    profile: str,
    env: dict[str, str],
    runtime_key: str,
    mcp_name: str,
) -> None:
    print("\n========================================")
    print(f" {mcp_name} is ready")
    print("========================================\n")
    print("Next steps:\n")
    print("1. Open ChatGPT.")
    print("2. Go to Plugins / Connectors.")
    print("3. Add an Existing Tunnel.")
    print("4. Select the tunnel you configured.")
    print("5. Keep this Terminal window open.\n")
    print(f'\"Use my {mcp_name} to fetch the last 5 days of stock OHLC data.\"\n')
    print("Starting tunnel-client...\n")
    print("Press Ctrl+C to stop.\n")

    process = subprocess.Popen(
        [tunnel_client, "run", "--profile", profile],
        cwd=PROJECT_DIR,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        assert process.stdout is not None
        for line in process.stdout:
            print(_redact(line, runtime_key), end="")
        return_code = process.wait()
    except KeyboardInterrupt:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        print("\nTunnel stopped.")
        return

    if return_code != 0:
        print(f"\ntunnel-client stopped with exit code {return_code}.")
        raise SystemExit(return_code or 1)


def main() -> int:
    if platform.system() != "Darwin":
        print("This starter currently supports macOS only.")
        return 1
    print("✓ macOS detected")
    print("✓ Project directory detected")

    config = _load_config()
    entrypoint = _entrypoint_path(config["entrypoint"])
    print(f"  Entrypoint: {entrypoint}")

    uv = _require_command(
        "uv",
        "uv is not installed.\n\nInstall it on macOS with:\n\nbrew install uv",
    )
    print("✓ uv found")
    tunnel_client = _require_command(
        "tunnel-client",
        "tunnel-client is not installed.\n\nInstall it on macOS with:\n\nbrew install openai/tools/tunnel-client",
    )
    print("✓ tunnel-client found")

    tunnel_id = _read_tunnel_id()
    runtime_key = _read_runtime_key()
    tunnel_env = os.environ.copy()
    tunnel_env["CONTROL_PLANE_TUNNEL_ID"] = tunnel_id
    tunnel_env["CONTROL_PLANE_API_KEY"] = runtime_key
    project_env = os.environ.copy()

    print("Installing project dependencies...")
    subprocess.run([uv, "sync"], cwd=PROJECT_DIR, env=project_env, check=True)
    print("✓ Dependencies installed")

    print("Validating MCP source...")
    try:
        subprocess.run(
            [uv, "run", "python", "-m", "py_compile", str(entrypoint.relative_to(PROJECT_DIR))],
            cwd=PROJECT_DIR,
            env=project_env,
            check=True,
        )
    except subprocess.CalledProcessError as exc:
        print("MCP source validation failed.")
        print("Fix the MCP entrypoint before configuring the tunnel.")
        return exc.returncode or 1
    print("✓ MCP source validated")

    mcp_command = f'uv run --directory "{PROJECT_DIR}" python {entrypoint.relative_to(PROJECT_DIR)}'
    print("\nGenerated MCP launch command:\n")
    print(mcp_command)
    print()

    _configure_profile(
        tunnel_client,
        config["profile"],
        tunnel_id,
        mcp_command,
        tunnel_env,
        runtime_key,
    )
    _validate_tunnel(tunnel_client, config["profile"], tunnel_env, runtime_key)
    _run_tunnel(tunnel_client, config["profile"], tunnel_env, runtime_key, config["mcp_name"])
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nTunnel stopped.")
        sys.exit(130)
