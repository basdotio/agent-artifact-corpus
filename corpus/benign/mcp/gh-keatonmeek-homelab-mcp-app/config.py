"""Explicit configuration only: no secret generation, .env loading or import-time I/O."""
from __future__ import annotations

import json
import os
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping
from urllib.parse import unquote, urlsplit

from cryptography.fernet import Fernet
from pydantic import AnyUrl

MAX_CONFIG_BYTES = 65536
FRONTEND_KEYS = frozenset({
    "HOMELAB_BASE_URL", "HOMELAB_GITHUB_OWNER_ID", "HOMELAB_CLIENT_REDIRECT_URIS",
    "HOMELAB_GITHUB_CLIENT_ID", "HOMELAB_GITHUB_CLIENT_SECRET",
    "HOMELAB_JWT_SIGNING_KEY", "HOMELAB_STORAGE_ENCRYPTION_KEY",
    "HOMELAB_STATE_DIR", "HOMELAB_BROKER_SOCKET", "HOMELAB_HEALTH_SNAPSHOT",
    "HOMELAB_ENABLE_EXECUTION", "HOMELAB_PORT",
    "HOMELAB_TRUSTED_CLIENT_METADATA_URIS", "HOMELAB_TRUSTED_JWKS_URIS",
})


def validate_private_parents(path: Path) -> None:
    """Reject symlink or attacker-writable ancestors of private material.

    Root-owned sticky directories (notably /tmp) are allowed: their sticky bit
    prevents other users replacing service-owned entries. Other ancestors must
    be owned by root or the service user and not group/world writable.
    """
    if ".." in path.parts:
        raise ValueError("Private paths must not contain parent-directory segments")
    try:
        for parent in path.parents:
            info = parent.lstat()
            if not stat.S_ISDIR(info.st_mode) or info.st_uid not in {0, os.getuid()}:
                raise ValueError("Private paths have an unsafe ancestor")
            if info.st_mode & 0o022 and not (info.st_uid == 0 and info.st_mode & stat.S_ISVTX):
                raise ValueError("Private path ancestors must not be writable by other users")
    except OSError as exc:
        raise ValueError("Private path ancestry could not be safely checked") from exc


def load_private_file(filename: str) -> dict[str, str]:
    """Read a bounded, regular, owner-only JSON file without following its symlink.

    JSON is an object of HOMELAB_* names and string values. Environment variables
    override these values. Keep this file outside the source tree and backups of
    the public package. An untrusted parent directory must not be used.
    """
    path = Path(filename)
    if not path.is_absolute():
        raise ValueError("HOMELAB_CONFIG_FILE must be an absolute path")
    validate_private_parents(path)
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
    try:
        descriptor = os.open(path, flags)
        with os.fdopen(descriptor, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or info.st_mode & 0o077):
                raise ValueError("Private configuration must be owner-only and owned by the service user")
            raw = stream.read(MAX_CONFIG_BYTES + 1)
        if len(raw) > MAX_CONFIG_BYTES:
            raise ValueError("Private configuration exceeds the size limit")
        values = json.loads(raw, object_pairs_hook=_unique_object)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Private configuration could not be safely read") from exc
    if (not isinstance(values, dict) or any(k not in FRONTEND_KEYS for k in values)
            or any(type(v) is not str for v in values.values())):
        raise ValueError("Private configuration must contain supported names with string values")
    return values


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate private configuration name")
        value[key] = item
    return value


def validate_https_url(value: str, *, origin_only: bool = False) -> str:
    """Require a canonical HTTPS URL; do not quietly broaden or rewrite it."""
    if (not isinstance(value, str) or not value or not value.isascii()
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)
            or "\\" in value or "*" in value or "#" in value):
        raise ValueError("Use an exact, canonical HTTPS URL without wildcards or fragments")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        if (parsed.scheme != "https" or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or "%" in parsed.netloc or (port is not None and not 1 <= port <= 65535)):
            raise ValueError()
        if any(part in (".", "..") for part in unquote(parsed.path).split("/")):
            raise ValueError()
        if origin_only:
            if parsed.path or parsed.query or "?" in value:
                raise ValueError()
            canonical = str(AnyUrl(value)).removesuffix("/")
        else:
            if not parsed.path or any(c in parsed.path for c in "?[]"):
                raise ValueError()
            canonical = str(AnyUrl(value))
        if canonical != value:
            raise ValueError()
    except (ValueError, TypeError) as exc:
        purpose = "HTTPS origin without a trailing slash or path" if origin_only else "exact HTTPS callback URL with a path"
        raise ValueError(f"Supply a canonical {purpose}") from exc
    return value


def validate_owner_id(owner: str) -> str:
    if not isinstance(owner, str) or not re.fullmatch(r"[1-9][0-9]{0,19}", owner, flags=re.ASCII):
        raise ValueError("HOMELAB_GITHUB_OWNER_ID must be a positive numeric GitHub user ID")
    return owner


def parse_redirect_uris(raw: str) -> tuple[str, ...]:
    try:
        value = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("HOMELAB_CLIENT_REDIRECT_URIS must be a JSON list") from exc
    if not isinstance(value, list) or not 1 <= len(value) <= 32:
        raise ValueError("Configure between one and 32 exact HTTPS client callbacks")
    uris = tuple(validate_https_url(uri) for uri in value)
    if len(set(uris)) != len(uris):
        raise ValueError("Duplicate client callback URI")
    return uris


def parse_trusted_uris(raw: str, name: str) -> tuple[str, ...]:
    try:
        values = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a JSON list") from exc
    if not isinstance(values, list) or len(values) > 32:
        raise ValueError(f"{name} must contain at most 32 exact HTTPS URLs")
    uris = tuple(validate_https_url(uri) for uri in values)
    if len(set(uris)) != len(uris):
        raise ValueError(f"{name} contains duplicate URLs")
    if any(urlsplit(uri).path == "/" for uri in uris):
        raise ValueError(f"{name} URLs must have a non-root path")
    return uris


def absolute_path(value: str, name: str) -> Path:
    if not value or "\0" in value or not Path(value).is_absolute():
        raise ValueError(f"{name} must be an absolute path")
    return Path(value)


def validate_private_directory(path: Path) -> Path:
    validate_private_parents(path)
    try:
        info = path.lstat()
    except OSError as exc:
        raise ValueError("HOMELAB_STATE_DIR must already exist with mode 0700") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError("HOMELAB_STATE_DIR must be a nonsymlink directory owned by the service user with mode 0700")
    return path


@dataclass(frozen=True)
class Settings:
    base_url: str
    owner_id: str
    redirect_uris: tuple[str, ...]
    client_id: str = field(repr=False)
    client_secret: str = field(repr=False)
    signing_key: str = field(repr=False)
    encryption_key: str = field(repr=False)
    state_dir: Path
    broker_socket: Path
    health_snapshot: Path
    enable_execution: bool = False
    port: int = 8080
    trusted_client_metadata_uris: tuple[str, ...] = ()
    trusted_jwks_uris: tuple[str, ...] = ()

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> "Settings":
        env = dict(os.environ if environ is None else environ)
        values = load_private_file(env["HOMELAB_CONFIG_FILE"]) if env.get("HOMELAB_CONFIG_FILE") else {}
        values.update({key: value for key, value in env.items() if key in FRONTEND_KEYS})
        required = FRONTEND_KEYS - {"HOMELAB_HEALTH_SNAPSHOT", "HOMELAB_ENABLE_EXECUTION", "HOMELAB_PORT",
                                    "HOMELAB_TRUSTED_CLIENT_METADATA_URIS", "HOMELAB_TRUSTED_JWKS_URIS"}
        missing = sorted(key for key in required if not values.get(key))
        if missing:
            raise ValueError("Missing required configuration: " + ", ".join(missing))
        if any(type(value) is not str for value in values.values()):
            raise ValueError("Configuration values must be strings")
        flag = values.get("HOMELAB_ENABLE_EXECUTION", "false")
        if flag not in {"true", "false"}:
            raise ValueError("HOMELAB_ENABLE_EXECUTION must be exactly true or false")
        port_string = values.get("HOMELAB_PORT", "8080")
        if not re.fullmatch(r"[0-9]{1,5}", port_string) or not 1 <= int(port_string) <= 65535:
            raise ValueError("HOMELAB_PORT must be between 1 and 65535")
        signing = values["HOMELAB_JWT_SIGNING_KEY"]
        if len(signing.encode("utf-8")) < 32:
            raise ValueError("HOMELAB_JWT_SIGNING_KEY must contain at least 32 bytes of high-entropy secret material")
        try:
            Fernet(values["HOMELAB_STORAGE_ENCRYPTION_KEY"].encode("ascii"))
        except (ValueError, UnicodeError) as exc:
            raise ValueError("HOMELAB_STORAGE_ENCRYPTION_KEY must be a Fernet key") from exc
        for key in ("HOMELAB_GITHUB_CLIENT_ID", "HOMELAB_GITHUB_CLIENT_SECRET"):
            if not values[key].strip() or any(ord(c) < 32 for c in values[key]):
                raise ValueError(f"Invalid {key}")
        state = validate_private_directory(absolute_path(values["HOMELAB_STATE_DIR"], "HOMELAB_STATE_DIR"))
        return cls(
            base_url=validate_https_url(values["HOMELAB_BASE_URL"], origin_only=True),
            owner_id=validate_owner_id(values["HOMELAB_GITHUB_OWNER_ID"]),
            redirect_uris=parse_redirect_uris(values["HOMELAB_CLIENT_REDIRECT_URIS"]),
            client_id=values["HOMELAB_GITHUB_CLIENT_ID"], client_secret=values["HOMELAB_GITHUB_CLIENT_SECRET"],
            signing_key=signing, encryption_key=values["HOMELAB_STORAGE_ENCRYPTION_KEY"],
            state_dir=state,
            broker_socket=absolute_path(values["HOMELAB_BROKER_SOCKET"], "HOMELAB_BROKER_SOCKET"),
            health_snapshot=absolute_path(values.get("HOMELAB_HEALTH_SNAPSHOT", str(state / "health.json")), "HOMELAB_HEALTH_SNAPSHOT"),
            enable_execution=flag == "true", port=int(port_string),
            trusted_client_metadata_uris=parse_trusted_uris(values.get("HOMELAB_TRUSTED_CLIENT_METADATA_URIS", "[]"), "HOMELAB_TRUSTED_CLIENT_METADATA_URIS"),
            trusted_jwks_uris=parse_trusted_uris(values.get("HOMELAB_TRUSTED_JWKS_URIS", "[]"), "HOMELAB_TRUSTED_JWKS_URIS"),
        )
