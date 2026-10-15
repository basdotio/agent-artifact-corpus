"""Credential input for local tools. Tokens never become command-line arguments."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path

from .client import LeanWarpCloud
from .endpoints import api_origin
from .session import SessionError


def credentials_path() -> Path:
    return (
        Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config")))
        / "leanwarp"
        / "credentials.json"
    )


def load_client() -> LeanWarpCloud:
    key = os.environ.get("LEANWARP_API_KEY")
    if key is not None:
        return LeanWarpCloud(key)
    path = credentials_path()
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    except FileNotFoundError as error:
        raise SessionError(
            "not signed in; run `leanwarp auth login` or set LEANWARP_API_KEY"
        ) from error
    with os.fdopen(fd, "rb") as stream:
        metadata = os.fstat(stream.fileno())
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o077:
            raise SessionError(
                f"{path} must be a regular file readable only by you; run `leanwarp auth login` "
                "to replace it"
            )
        raw = stream.read(8193)
    try:
        data = json.loads(raw) if len(raw) <= 8192 else None
        if not isinstance(data, dict) or set(data) not in ({"api_key"}, {"api_key", "base_url"}):
            raise ValueError
        key = data["api_key"]
        if not isinstance(key, str):
            raise ValueError
        if "base_url" in data and data["base_url"] != api_origin(key):
            raise ValueError
    except (ValueError, TypeError, AttributeError) as error:
        raise SessionError(
            f"{path} is not a valid credential file; run `leanwarp auth login` to replace it"
        ) from error
    return LeanWarpCloud(key)


def save_credentials(api_key: str) -> None:
    # Validate and authenticate before replacing a working configuration.
    with LeanWarpCloud(api_key) as cloud:
        cloud.versions()
    path = credentials_path()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.parent.is_symlink() or path.is_symlink():
        raise SessionError(f"{path} must not be a symlink")
    fd, name = tempfile.mkstemp(prefix="credentials-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump({"api_key": api_key}, stream)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)
