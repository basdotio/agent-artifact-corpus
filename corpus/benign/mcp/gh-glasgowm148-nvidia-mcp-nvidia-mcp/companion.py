"""Export the pinned optional Kodi Manager without connecting to a TV."""

import hashlib
import json
from importlib.resources import files
from pathlib import Path

from .config import ShieldError


def companion_metadata():
    return json.loads(files("nvidia_mcp").joinpath("companion/manifest.json").read_text())


def export_manager(directory):
    metadata = companion_metadata()
    name = metadata["filename"]
    if name != Path(name).name or not name.endswith(".zip"):
        raise ShieldError("Invalid bundled companion manifest")
    payload = files("nvidia_mcp").joinpath("companion", name).read_bytes()
    checksum = hashlib.sha256(payload).hexdigest()
    if checksum != metadata["sha256"]:
        raise ShieldError("Bundled companion checksum failed")
    root = Path(directory).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    target = root / name
    # Exclusive creation: never overwrite another file, including through a symlink.
    try:
        with target.open("xb") as handle:
            handle.write(payload)
    except FileExistsError:
        if target.is_symlink() or not target.is_file() or target.read_bytes() != payload:
            raise ShieldError("Export destination already contains a different file") from None
    except OSError:
        raise ShieldError("Cannot write companion export directory") from None
    return {
        "path": str(target),
        "sha256": checksum,
        "version": metadata["version"],
        "installed_on_device": False,
        "source": metadata["source"],
    }
