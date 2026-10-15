"""Environment and TOML configuration without hard-coded deployment paths."""

import os
import tomllib
from pathlib import Path
from typing import Any


def settings(
    data_dir: str | None = None, config: str | None = None, schema_dir: str | None = None
) -> dict[str, Any]:
    options = {}
    if config:
        with Path(config).open("rb") as stream:
            raw = tomllib.load(stream)
        options = raw.get("hub", raw)
    return {
        "data_dir": data_dir or os.getenv("HUB_DATA_DIR") or options.get("data_dir", "./data"),
        "schema_dir": schema_dir or options.get("schema_dir"),
        "timezone": options.get("timezone", "Asia/Shanghai"),
        "actor": options.get("actor", "cli"),
        "token": os.getenv("HUB_TOKEN") or options.get("token"),
    }
