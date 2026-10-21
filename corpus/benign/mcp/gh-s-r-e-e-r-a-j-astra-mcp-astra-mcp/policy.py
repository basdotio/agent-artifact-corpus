# Developer: Sreeraj
# GitHub: https://github.com/s-r-e-e-r-a-j

import ipaddress
import re
from pathlib import Path
from urllib.parse import urlparse

from astra_mcp.config import ToolConfig


def validate_arguments(tool: ToolConfig, arguments: object) -> dict[str, str | int | float | bool]:
    if not isinstance(arguments, dict):
        raise ValueError("Arguments must be an object")
    schema = {parameter.name: parameter for parameter in tool.parameters}
    unknown = set(arguments) - set(schema)
    if unknown:
        raise ValueError(f"Unknown arguments: {', '.join(sorted(unknown))}")
    result: dict[str, str | int | float | bool] = {}
    for name, parameter in schema.items():
        if name not in arguments:
            if parameter.required:
                raise ValueError(f"Missing required argument: {name}")
            continue
        value = arguments[name]
        if parameter.kind == "string":
            valid = isinstance(value, str)
        elif parameter.kind == "integer":
            valid = isinstance(value, int) and not isinstance(value, bool)
        elif parameter.kind == "number":
            valid = isinstance(value, (int, float)) and not isinstance(value, bool)
        else:
            valid = isinstance(value, bool)
        if not valid:
            raise ValueError(f"Argument {name} must be {parameter.kind}")
        if isinstance(value, str) and ("\x00" in value or "\r" in value or "\n" in value):
            raise ValueError(f"Argument {name} contains forbidden control characters")
        result[name] = value
    return result


def expand_argument(template: str, arguments: dict[str, str | int | float | bool]) -> str:
    names = re.findall(r"\{([A-Za-z_][A-Za-z0-9_]*)\}", template)
    unknown = set(names) - set(arguments)
    if unknown:
        raise ValueError(f"Undefined template placeholders: {', '.join(sorted(unknown))}")
    expanded = template
    for name in names:
        expanded = expanded.replace("{" + name + "}", str(arguments[name]))
    if "{" in expanded or "}" in expanded:
        raise ValueError("Malformed template placeholder")
    return expanded


def validate_path(value: str, allowed_paths: tuple[str, ...]) -> Path:
    path = Path(value).expanduser().resolve()
    if not allowed_paths:
        raise ValueError("Path arguments are blocked because allowed_paths is empty")
    roots = tuple(Path(root).expanduser().resolve() for root in allowed_paths)
    if not any(path == root or root in path.parents for root in roots):
        raise ValueError("Path is outside the configured allowed_paths")
    return path


def validate_url_host(value: str, allowed_hosts: tuple[str, ...]) -> None:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("Only HTTP and HTTPS URLs are accepted")
    if not allowed_hosts or parsed.hostname.lower() not in {host.lower() for host in allowed_hosts}:
        raise ValueError("URL host is not in the configured allowed_hosts")



def validate_host(value: str, allowed_hosts: tuple[str, ...]) -> None:
    candidate = value.strip().lower().rstrip(".")
    if not candidate or any(character in candidate for character in "/\\\\@?#"):
        raise ValueError("Target must be a hostname or IP address without a URL or path")
    try:
        normalized = str(ipaddress.ip_address(candidate))
    except ValueError:
        normalized = candidate
    allowed = set()
    for host in allowed_hosts:
        normalized_host = host.strip().lower().rstrip(".")
        try:
            normalized_host = str(ipaddress.ip_address(normalized_host))
        except ValueError:
            pass
        allowed.add(normalized_host)
    if not allowed or normalized not in allowed:
        raise ValueError("Target is not in the configured allowed_hosts")
