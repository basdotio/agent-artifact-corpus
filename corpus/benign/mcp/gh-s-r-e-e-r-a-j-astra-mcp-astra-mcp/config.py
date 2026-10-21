# Developer: Sreeraj
# GitHub: https://github.com/s-r-e-e-r-a-j

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Parameter:
    name: str
    kind: str
    description: str
    required: bool


@dataclass(frozen=True)
class ToolConfig:
    name: str
    description: str
    executable: str
    enabled: bool
    timeout_seconds: int
    fixed_args: tuple[str, ...]
    parameters: tuple[Parameter, ...]
    working_directory: str | None
    allowed_paths: tuple[str, ...]
    allowed_hosts: tuple[str, ...]


@dataclass(frozen=True)
class ServerConfig:
    default_timeout_seconds: int
    max_timeout_seconds: int
    max_output_bytes: int
    max_concurrency: int
    enable_dynamic_command_tool: bool
    enable_interactive_command_tool: bool
    enable_shell_tool: bool
    shell_executable: str
    audit_log: str
    tools: tuple[ToolConfig, ...]


def _string(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def load_config(path: str | Path) -> ServerConfig:
    config_path = Path(path).expanduser().resolve()
    with config_path.open("rb") as stream:
        raw = tomllib.load(stream)
    server = raw.get("server", {})
    default_timeout = int(server.get("default_timeout_seconds", 30))
    max_timeout = int(server.get("max_timeout_seconds", 120))
    max_output = int(server.get("max_output_bytes", 200000))
    max_concurrency = int(server.get("max_concurrency", 4))
    if min(default_timeout, max_timeout, max_output, max_concurrency) < 1:
        raise ValueError("Server limits must be positive")
    if default_timeout > max_timeout:
        raise ValueError("default_timeout_seconds cannot exceed max_timeout_seconds")
    tools: list[ToolConfig] = []
    names: set[str] = set()
    for item in raw.get("tools", []):
        name = _string(item.get("name"), "tool name")
        if name in names:
            raise ValueError(f"Duplicate tool name: {name}")
        names.add(name)
        executable = _string(item.get("executable"), f"{name}.executable")
        if "/" in executable and not Path(executable).is_absolute():
            raise ValueError(f"{name}.executable must be a command name or absolute path")
        parameters_raw = item.get("parameters", {})
        if not isinstance(parameters_raw, dict):
            raise ValueError(f"{name}.parameters must be a table")
        parameters: list[Parameter] = []
        for parameter_name, spec in parameters_raw.items():
            if not isinstance(parameter_name, str) or not parameter_name.isidentifier():
                raise ValueError(f"Invalid parameter name in {name}: {parameter_name}")
            if not isinstance(spec, dict):
                raise ValueError(f"{name}.{parameter_name} must be a table")
            kind = spec.get("type", "string")
            if kind == "int":
                kind = "integer"
            if kind not in {"string", "integer", "number", "boolean"}:
                raise ValueError(f"Unsupported parameter type: {kind}")
            parameters.append(Parameter(
                parameter_name,
                kind,
                str(spec.get("description", "")),
                bool(spec.get("required", False)),
            ))
        fixed_args_raw = item.get("fixed_args", [])
        if not isinstance(fixed_args_raw, list) or not all(isinstance(arg, str) for arg in fixed_args_raw):
            raise ValueError(f"{name}.fixed_args must be a list of strings")
        timeout = int(item.get("timeout_seconds", default_timeout))
        if timeout < 1 or timeout > max_timeout:
            raise ValueError(f"{name}.timeout_seconds must be between 1 and {max_timeout}")
        working_directory = item.get("working_directory")
        if working_directory is not None and not isinstance(working_directory, str):
            raise ValueError(f"{name}.working_directory must be a string")
        allowed_paths = item.get("allowed_paths", [])
        allowed_hosts = item.get("allowed_hosts", [])
        if not all(isinstance(value, str) for value in allowed_paths + allowed_hosts):
            raise ValueError(f"{name}.allowed_paths and allowed_hosts must contain strings")
        tools.append(ToolConfig(
            name=name,
            description=str(item.get("description", "")),
            executable=executable,
            enabled=bool(item.get("enabled", False)),
            timeout_seconds=timeout,
            fixed_args=tuple(fixed_args_raw),
            parameters=tuple(parameters),
            working_directory=working_directory,
            allowed_paths=tuple(allowed_paths),
            allowed_hosts=tuple(allowed_hosts),
        ))
    return ServerConfig(
        default_timeout_seconds=default_timeout,
        max_timeout_seconds=max_timeout,
        max_output_bytes=max_output,
        max_concurrency=max_concurrency,
        enable_dynamic_command_tool=bool(server.get("enable_dynamic_command_tool", False)),
        enable_interactive_command_tool=bool(server.get("enable_interactive_command_tool", False)),
        enable_shell_tool=bool(server.get("enable_shell_tool", False)),
        shell_executable=str(server.get("shell_executable", "/bin/bash")),
        audit_log=os.environ.get("ASTRA_MCP_AUDIT_LOG", str(server.get("audit_log", "./audit.jsonl"))),
        tools=tuple(tools),
    )


def config_path_from_environment() -> Path:
    return Path(os.environ.get("ASTRA_MCP_CONFIG", "./tools.toml"))
