"""Standalone standard-library bootstrap, copied outside plugin caches by installers."""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path


def file_hash(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def validate(home, pointer="active.json"):
    document = json.loads((home / pointer).read_text())
    if document.get("protocol") != 1 or document.get("contract_major") != 1:
        raise ValueError("Incompatible runtime pointer; reinstall a compatible plugin")
    release = document["release"]
    if not isinstance(release, str) or Path(release).name != release or release in (".", ".."):
        raise ValueError("Invalid payload identity")
    root = (home / "payloads" / release).resolve(strict=True)
    if not root.is_relative_to((home / "payloads").resolve()):
        raise ValueError("Payload escapes runtime home")
    for name, digest in document["files"].items():
        path = (root / name).resolve(strict=True)
        if not path.is_relative_to(root) or file_hash(path) != digest:
            raise ValueError(f"Runtime integrity check failed: {name}")
    python = root / document["python"]
    # A venv interpreter may legitimately link to a system Python.
    if Path(document["python"]).is_absolute() or ".." in Path(document["python"]).parts:
        raise ValueError("Invalid interpreter path")
    if not python.is_file():
        raise ValueError("Runtime interpreter is missing")
    return root, document


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--doctor", action="store_true")
    parser.add_argument("--rollback", action="store_true")
    parser.add_argument("--cli", action="store_true", help="Run the installed host-agent CLI")
    args, remaining = parser.parse_known_args()
    try:
        root, manifest = validate(
            args.home, "last-healthy.json" if args.rollback else "active.json"
        )
        if args.rollback:
            # Atomic pointer replacement. Activation/draining is checked by the coordinator.
            temporary = args.home / ("rollback-" + str(os.getpid()) + ".json")
            temporary.write_text(json.dumps(manifest))
            temporary.replace(args.home / "active.json")
        if args.doctor or args.rollback:
            print(
                json.dumps(
                    {
                        "ready": True,
                        "release": manifest["release"],
                        "contract_major": manifest["contract_major"],
                    }
                )
            )
            return
        os.environ["AGENTIC_MCP_HOME"] = str(args.home.resolve())
        module = manifest["cli_module"] if args.cli else manifest["module"]
        os.execv(
            str(root / manifest["python"]),
            [str(root / manifest["python"]), "-m", module, *remaining],
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(
            f"Agentic MCP runtime unavailable: {exc}. Run this launcher with --doctor; "
            "use --rollback for a verified previous payload or rerun the tool installer.",
            file=sys.stderr,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
