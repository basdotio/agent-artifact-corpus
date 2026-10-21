"""Fail-closed WindAnvil Blade Unix-domain socket client.

Only HEALTH, STATUS and fixed-capability EXEC are supported. Authority,
signature verification, grant consumption and receipts are Blade's job.
This adapter cannot admit bundles or mint grants.
"""
from __future__ import annotations

import os
from pathlib import Path
import re
import socket
import stat
import struct

DEFAULT_SOCKET = Path.home() / "runtime" / "blade" / "blade.sock"
PIPELINE = re.compile(r"[a-zA-Z0-9_][a-zA-Z0-9_-]{0,63}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
MAX_RESPONSE = 65536


class BladeBlocked(Exception):
    """Operation was not provably authorized by the connected Blade runtime."""


def _socket_path() -> Path:
    return Path(os.environ.get("WINDANVIL_LOCAL_SOCKET", str(DEFAULT_SOCKET)))


def _exchange(command: str) -> str:
    endpoint = _socket_path()
    try:
        info = endpoint.lstat()
    except OSError as exc:
        raise BladeBlocked("blade_socket_unavailable") from exc
    if not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
        raise BladeBlocked("blade_socket_identity_or_permissions_invalid")

    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            client.settimeout(8)
            client.connect(str(endpoint))
            # Linux peer credentials prevent same-path socket replacement by another UID.
            if not hasattr(socket, "SO_PEERCRED"):
                raise BladeBlocked("blade_peer_verification_unavailable")
            _pid, uid, _gid = struct.unpack("3i", client.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
            if uid != os.getuid():
                raise BladeBlocked("blade_peer_identity_invalid")
            check = endpoint.lstat()
            if check.st_ino != info.st_ino or check.st_dev != info.st_dev:
                raise BladeBlocked("blade_socket_changed_during_connect")
            client.sendall((command + "\n").encode("ascii"))
            client.shutdown(socket.SHUT_WR)
            chunks: list[bytes] = []
            total = 0
            while chunk := client.recv(4096):
                total += len(chunk)
                if total > MAX_RESPONSE:
                    raise BladeBlocked("blade_response_too_large")
                chunks.append(chunk)
    except (OSError, TimeoutError) as exc:
        raise BladeBlocked("blade_connection_or_execution_failed") from exc

    raw = b"".join(chunks)
    try:
        wire = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BladeBlocked("blade_response_encoding_invalid") from exc
    if wire.startswith("ERR\t"):
        raise BladeBlocked("blade_rejected_operation")
    if not wire.startswith("OK") or (len(wire) > 2 and wire[2] not in "\t\n"):
        raise BladeBlocked("blade_response_protocol_invalid")
    return wire[3:] if len(wire) > 2 else ""


def health() -> str:
    return _exchange("HEALTH")


def status() -> str:
    return _exchange("STATUS")


def talkpipe_run(pipeline: str, pipeline_sha256: str) -> str:
    if not isinstance(pipeline, str) or not PIPELINE.fullmatch(pipeline):
        raise BladeBlocked("pipeline_name_invalid")
    if not isinstance(pipeline_sha256, str) or not DIGEST.fullmatch(pipeline_sha256):
        raise BladeBlocked("pipeline_digest_invalid")
    envelope = (
        "schema=windanvil.blade.talkpipe-exec/v1"
        f";pipeline={pipeline};pipeline_sha256={pipeline_sha256}"
    )
    # Keep execute fixed to talkpipe.run and the existing Blade wire grammar.
    return _exchange("EXEC\ttalkpipe.run\t" + envelope)

HOST_OPS = frozenset({"system.info", "dir.list", "file.read", "file.find", "content.search"})
HOST_PATH = re.compile(r"(?:[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127})(?:/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,127})*\Z")


def host_inspect(operation: str, path: str = "", needle: str = "") -> str:
    if operation not in HOST_OPS:
        raise BladeBlocked("host_inspection_operation_denied")
    if not isinstance(path, str) or len(path) > 512:
        raise BladeBlocked("host_inspection_path_denied")
    if path and not HOST_PATH.fullmatch(path):
        raise BladeBlocked("host_inspection_path_denied")
    if operation == "system.info" and path:
        raise BladeBlocked("host_inspection_path_denied")
    if operation == "file.read" and not path:
        raise BladeBlocked("host_inspection_path_denied")
    search = operation in {"file.find", "content.search"}
    if search:
        if not isinstance(needle, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", needle):
            raise BladeBlocked("host_inspection_needle_denied")
    elif needle:
        raise BladeBlocked("host_inspection_needle_denied")
    envelope = "schema=windanvil.blade.host-inspect/v1;operation=" + operation + ";path=" + path
    if search:
        envelope += ";needle=" + needle
    return _exchange("EXEC\thost.inspect\t" + envelope)



def process_list() -> str:
    return _exchange(
        "EXEC\tprocess.inspect\t"
        "schema=windanvil.blade.process-inspect/v1;operation=process.list"
    )



GIT_INSPECT_OPERATIONS = frozenset({"git.status", "git.history"})


def git_inspect(operation: str) -> str:
    if not isinstance(operation, str) or operation not in GIT_INSPECT_OPERATIONS:
        raise BladeBlocked("git_inspection_operation_denied")
    return _exchange(
        "EXEC\tgit.inspect\t"
        "schema=windanvil.blade.git-inspect/v1;operation=" + operation
    )



FILE_CREATE_NAME = re.compile(
    r"[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}(?:/[A-Za-z0-9_][A-Za-z0-9_.-]{0,127})*\Z"
)


def file_create(path: str, content: str) -> str:
    if not isinstance(path, str) or len(path) > 384 or not FILE_CREATE_NAME.fullmatch(path):
        raise BladeBlocked("file_create_path_denied")
    if not isinstance(content, str):
        raise BladeBlocked("file_create_text_required")
    encoded = content.encode("utf-8")
    if len(encoded) > 2048:
        raise BladeBlocked("file_create_payload_too_large")
    return _exchange(
        "EXEC\tfile.create\t"
        "schema=windanvil.blade.file-create/v1;path=" + path + ";hex=" + encoded.hex()
    )



PROCESS_PROBES = frozenset({"kernel", "uptime", "disk"})


def process_probe(probe: str) -> str:
    if not isinstance(probe, str) or probe not in PROCESS_PROBES:
        raise BladeBlocked("process_probe_not_allowlisted")
    return _exchange(
        "EXEC\tprocess.probe\t"
        "schema=windanvil.blade.process-probe/v1;probe=" + probe
    )
