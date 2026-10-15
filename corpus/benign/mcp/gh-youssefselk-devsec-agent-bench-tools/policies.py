"""Independent deterministic path policy; no agent prompts enforce access."""

import re
from pathlib import Path, PureWindowsPath

SECRET_NAMES = frozenset(
    {
        "id_rsa",
        "id_ed25519",
        "credentials",
        "credentials.json",
        "secrets.yaml",
        "secrets.yml",
        "secrets.json",
        ".npmrc",
        ".pypirc",
        ".netrc",
    }
)
PRIVATE_DIRS = frozenset({".git", ".ssh", ".aws", ".azure", ".config", "__pycache__"})
ALLOWED_SUFFIXES = frozenset(
    {".py", ".txt", ".json", ".yaml", ".yml", ".toml", ".md", ".diff", ".lock"}
)


class PolicyError(ValueError):
    """A deterministic authorization denial."""


def resolve_file(root: Path, raw: str) -> Path:
    if not raw or len(raw) > 256 or "\x00" in raw or ":" in raw or "\\" in raw:
        raise PolicyError("Invalid relative path")
    relative = Path(raw)
    if relative.is_absolute() or PureWindowsPath(raw).is_absolute() or ".." in relative.parts:
        raise PolicyError("Path escapes repository")
    for part in relative.parts:
        lower = part.lower()
        if (
            lower in PRIVATE_DIRS
            or lower in SECRET_NAMES
            or lower.startswith(".env")
            or lower.endswith((".pem", ".key", ".p12", ".pfx"))
        ):
            raise PolicyError("Secret or private path denied")
        if lower.rstrip(" .") != lower:
            raise PolicyError("Ambiguous path denied")
    candidate = root
    for part in relative.parts:
        candidate /= part
        if candidate.is_symlink() or candidate.resolve() != candidate.absolute():
            raise PolicyError("Symlink or junction denied")
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise PolicyError("Path escapes repository")
    if resolved.suffix.lower() not in ALLOWED_SUFFIXES:
        raise PolicyError("File type denied")
    return resolved


def sanitize(value: str) -> str:
    """Defense in depth; durable traces never store file/tool response bodies."""
    value = re.sub(r"\b(?:sk-|gh[pousr]_)[A-Za-z0-9_-]{8,}", "[REDACTED]", value)
    value = re.sub(r"(?i)(bearer\s+)[^\s\"']+", r"\1[REDACTED]", value)
    value = re.sub(
        r"(?i)((?:password|api_key|access_token|deploy_token|secret)[\"']?\s*[:=]\s*)[^\n,}]+",
        r"\1[REDACTED]",
        value,
    )
    return value
