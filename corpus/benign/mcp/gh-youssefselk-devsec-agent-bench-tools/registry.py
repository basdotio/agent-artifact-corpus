"""Bounded tools shared by agent execution and the MCP protocol server."""

import json
import time
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError

from devsec_bench.models import TOOLS, StrictModel, ToolEvent
from devsec_bench.tools.policies import PolicyError, resolve_file

MAX_FILE_BYTES = 32768
MAX_OUTPUT_BYTES = 65536
MAX_FILES = 250


class RepositoryArgs(StrictModel):
    repository: str = "target"


class FileArgs(RepositoryArgs):
    path: str = Field(min_length=1, max_length=256)


class SearchArgs(RepositoryArgs):
    query: str = Field(min_length=1, max_length=200)


ARG_MODELS: dict[str, type[RepositoryArgs]] = {
    name: FileArgs
    if name in {"read_file", "read_manifest"}
    else SearchArgs
    if name == "search_code"
    else RepositoryArgs
    for name in TOOLS
}


class Registry:
    def __init__(
        self, root: Path, allowed: list[str], max_calls: int = 100, deadline: float | None = None
    ):
        if root.is_symlink() or not root.is_dir():
            raise PolicyError("Invalid authorized repository")
        self.root = root.resolve()
        self.allowed = set(allowed) & TOOLS
        self.max_calls = max_calls
        self.deadline = deadline
        self.events: list[ToolEvent] = []

    def schemas(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"Read-only repository tool: {name}",
                    "parameters": ARG_MODELS[name].model_json_schema(),
                },
            }
            for name in sorted(self.allowed)
        ]

    def call(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        start = time.monotonic()
        authorized = False
        error: str | None = None
        result: dict[str, Any]
        try:
            if self.deadline is not None and start >= self.deadline:
                raise TimeoutError("Execution timeout")
            if len(self.events) >= self.max_calls:
                raise PolicyError("Tool budget exhausted")
            if name not in self.allowed:
                raise PolicyError("Tool not permitted")
            args = ARG_MODELS[name].model_validate(arguments)
            if args.repository != "target":
                raise PolicyError("Repository not authorized")
            # Authorization includes path checks before any bytes are opened.
            if isinstance(args, FileArgs):
                resolve_file(self.root, args.path)
            authorized = True
            result = self._execute(name, args)
            if len(json.dumps(result).encode()) > MAX_OUTPUT_BYTES:
                raise ValueError("Tool output limit exceeded")
        except PolicyError as exc:
            authorized = False
            error = str(exc)
            result = {"error": error}
        except ValidationError:
            authorized = False
            error = "Invalid tool arguments"
            result = {"error": error}
        except (OSError, ValueError, TimeoutError):
            error = "Tool failed or resource limit exceeded"
            result = {"error": error}
        # No user-controlled argument values or returned file bodies enter a trace.
        self.events.append(
            ToolEvent(
                sequence=len(self.events) + 1,
                tool=name if name in TOOLS else "unknown",
                arguments={
                    key: "[omitted]" for key in ("repository", "path", "query") if key in arguments
                },
                authorized=authorized,
                error=error,
                bytes_returned=len(json.dumps(result).encode()),
                duration=time.monotonic() - start,
            )
        )
        return result

    def files(self) -> list[str]:
        files = []
        # Fixture loader bounds the tree; standalone tools stop at a bounded traversal.
        for count, path in enumerate(self.root.rglob("*")):
            if count >= 2000:
                raise ValueError("Repository traversal limit exceeded")
            relative = path.relative_to(self.root).as_posix()
            try:
                resolve_file(self.root, relative)
            except PolicyError:
                continue
            if path.is_file():
                files.append(relative)
            if len(files) > MAX_FILES:
                raise ValueError("Repository file limit exceeded")
        return sorted(files)

    def read(self, raw: str) -> str:
        path = resolve_file(self.root, raw)
        with path.open("rb") as stream:
            data = stream.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES or b"\x00" in data:
            raise ValueError("File read limit or binary file")
        return data.decode("utf-8").replace("\r\n", "\n")

    def _execute(self, name: str, args: RepositoryArgs) -> dict[str, Any]:
        if name == "list_files":
            return {"files": self.files()}
        if name in {"read_file", "read_manifest"}:
            assert isinstance(args, FileArgs)
            if name == "read_manifest" and Path(args.path).name not in {
                "requirements.txt",
                "pyproject.toml",
                "package.json",
                "config.yaml",
            }:
                raise PolicyError("Manifest not permitted")
            return {"path": args.path, "content": self.read(args.path)}
        if name == "search_code":
            assert isinstance(args, SearchArgs)
            matches = []
            for file in self.files():
                for line, source in enumerate(self.read(file).splitlines(), 1):
                    if args.query in source:
                        matches.append({"file": file, "line": line, "text": source})
                        if len(matches) == 50:
                            return {"matches": matches, "truncated": True}
            return {"matches": matches, "truncated": False}
        if name == "inspect_dependencies":
            files = self.files()
            requirements = self.read("requirements.txt") if "requirements.txt" in files else ""
            advisories = (
                json.loads(self.read("advisories.json")) if "advisories.json" in files else {}
            )
            dependencies = []
            for requirement in requirements.splitlines():
                if "==" in requirement and not requirement.startswith("#"):
                    package, version = requirement.strip().split("==", 1)
                    advisory = advisories.get(package, {})
                    dependencies.append(
                        {
                            "name": package,
                            "version": version,
                            "vulnerable": version in advisory.get("affected", []),
                            "fixed": advisory.get("fixed"),
                            "advisory": advisory.get("id"),
                        }
                    )
            return {"dependencies": dependencies, "source": "pinned local synthetic advisories"}
        if name == "inspect_git_diff":
            # Do not invoke git: configs, filters and external diff drivers can execute code.
            return {
                "diff": self.read("changes.diff") if "changes.diff" in self.files() else "",
                "source": "optional fixture changes.diff; no git process",
            }
        return {"repository": "target", "file_count": len(self.files()), "read_only": True}
