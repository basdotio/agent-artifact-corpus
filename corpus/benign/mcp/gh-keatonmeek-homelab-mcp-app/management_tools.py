"""Owner-authenticated adapters; operating-system privileges belong to the Unix broker."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

from pydantic import Field

MAX_FRAME = 1048576
MAX_FILE_BYTES = 131072
# Match the entire absolute path for clients using full-match schema validation.
# [\s\S] preserves valid POSIX filenames containing newlines without regex flags.
AbsolutePath = Annotated[str, Field(min_length=1, max_length=4096, pattern=r"^/[\s\S]*$")]
JobID = Annotated[str, Field(pattern=r"^[0-9a-f]{32}$")]
Timeout = Annotated[int, Field(strict=True, ge=1, le=3600)]
OutputLimit = Annotated[int, Field(strict=True, ge=1024, le=131072)]
Command = Annotated[str, Field(min_length=1, max_length=32768)]


class BrokerClient:
    """One bounded, newline-delimited JSON request per local socket connection."""

    def __init__(self, socket_path: Path | str):
        self.socket_path = str(socket_path)

    async def call(self, method: str, **params) -> dict:
        writer = None
        try:
            timeout = params.get("timeout", 30)
            if type(timeout) is not int or not 1 <= timeout <= 3600:
                return {"error": "invalid_timeout"}
            payload = json.dumps({"method": method, "params": params}, ensure_ascii=True).encode() + b"\n"
            if len(payload) > MAX_FRAME:
                return {"error": "broker_request_too_large"}
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path, limit=MAX_FRAME + 1), 5
            )
            writer.write(payload)
            await asyncio.wait_for(writer.drain(), 5)
            line = await asyncio.wait_for(reader.readline(), timeout + 10)
            if len(line) > MAX_FRAME or not line.endswith(b"\n"):
                return {"error": "invalid_broker_response"}
            result = json.loads(line)
            if not isinstance(result, dict):
                return {"error": "invalid_broker_response"}
            return result
        except (OSError, ValueError, UnicodeError, asyncio.TimeoutError):
            return {"error": "broker_unavailable_or_request_failed"}
        finally:
            if writer is not None:
                writer.close()
                try:
                    await asyncio.wait_for(writer.wait_closed(), 1)
                except (OSError, asyncio.TimeoutError):
                    pass


def register(server, broker: BrokerClient) -> None:
    """Register all execution/file/job tools only after explicit operator opt-in."""

    async def command_run(command: Command, cwd: AbsolutePath = "/", timeout: Timeout = 30,
                          output_limit: OutputLimit = 65536) -> dict:
        """Execute Bash with the broker OS account's privileges (root only if explicitly deployed that way). Can modify or delete any accessible data. Obtain task-specific approval for sensitive/destructive actions; chat confirmation is not a server-side control. Never put secrets in commands; output redaction is best effort."""
        return await broker.call("command_run", command=command, cwd=cwd, timeout=timeout, output_limit=output_limit)

    async def command_start(command: Command, cwd: AbsolutePath = "/", timeout: Timeout = 300,
                            output_limit: OutputLimit = 65536) -> dict:
        """Start a Bash job with the broker OS account's privileges, with the same risks as command_run. Job IDs last only for the broker lifetime. Approval and secret-handling requirements also apply to asynchronous jobs."""
        return await broker.call("command_start", command=command, cwd=cwd, timeout=timeout, output_limit=output_limit)

    async def job_status(job_id: JobID) -> dict:
        """Read job metadata from this broker lifetime without returning job output."""
        return await broker.call("job_status", job_id=job_id)

    async def job_output(job_id: JobID) -> dict:
        """Read bounded job output with best-effort redaction. Do not request secret-bearing output."""
        return await broker.call("job_output", job_id=job_id)

    async def job_cancel(job_id: JobID) -> dict:
        """Terminate a job's process group. May interrupt writes and leave partial state; cannot undo completed changes or stop deliberately detached descendants."""
        return await broker.call("job_cancel", job_id=job_id)

    async def file_read(path: AbsolutePath, offset: Annotated[int, Field(strict=True, ge=0)] = 0,
                        limit: Annotated[int, Field(strict=True, ge=1, le=65536)] = 65536) -> dict:
        """Read bounded UTF-8 text from an absolute regular-file path using the broker OS account's privileges. Symlinks/devices are refused. Do not read credentials or private keys; output redaction is not guaranteed."""
        return await broker.call("file_read", path=path, offset=offset, limit=limit)

    async def file_write(path: AbsolutePath, text: Annotated[str, Field(max_length=131072)],
                         create_parents: bool = False, mode: Annotated[int, Field(strict=True, ge=0, le=511)] = 384) -> dict:
        """Create or atomically replace up to 128 KiB of UTF-8 text using the broker OS account's privileges. Existing regular files are backed up beside the target and metadata preserved. Sensitive/destructive writes require task-specific approval. Backups consume space and need intentional cleanup."""
        try:
            if len(text.encode("utf-8")) > MAX_FILE_BYTES:
                return {"error": "file_text_exceeds_131072_utf8_bytes"}
        except UnicodeError:
            return {"error": "invalid_utf8_text"}
        return await broker.call("file_write", path=path, text=text, create_parents=create_parents, mode=mode)

    async def file_move(path: AbsolutePath, destination: AbsolutePath, overwrite: bool = False) -> dict:
        """Move a file/directory using the broker OS account's privileges. Existing file targets require explicit overwrite and are backed up. Directory overwrite and symlinks are refused. Cross-filesystem moves are not atomic; there is no automatic rollback."""
        return await broker.call("file_move", path=path, destination=destination, overwrite=overwrite)

    for function in (command_run, command_start, job_cancel, file_write, file_move):
        server.tool(function, annotations={"readOnlyHint": False, "destructiveHint": True,
                    "idempotentHint": False, "openWorldHint": True})
    for function in (job_status, job_output, file_read):
        server.tool(function, annotations={"readOnlyHint": True, "destructiveHint": False,
                    "openWorldHint": False})
