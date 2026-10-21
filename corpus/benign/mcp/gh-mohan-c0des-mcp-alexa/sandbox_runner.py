"""Runs ONE approved script inside guard rails. Used by script_writer.run_script.

Usage:  python sandbox_runner.py <script.py>      (env: SANDBOX_WORKSPACE=<folder>)

Guards (a Python audit hook, so they also catch tricks the static check misses):
  - writes, deletes, renames and moves are only allowed INSIDE the workspace folder
  - no network, no subprocesses, no shell commands
  - reading well-known secret locations (.ssh, .aws, .env, ...) is blocked
This is defence in depth for a hackathon demo, not a perfect jail.
"""
import os
import runpy
import sys
from pathlib import Path

WORKSPACE = os.path.normcase(os.path.realpath(os.environ["SANDBOX_WORKSPACE"]))
SECRET_DIRS = {".ssh", ".aws", ".gnupg", ".kube", ".azure"}
SECRET_FILES = {"credentials", "id_rsa", "id_ed25519", "login data", "cookies"}

BLOCKED_EVENTS = {
    "subprocess.Popen", "os.system", "os.exec", "os.posix_spawn", "os.spawn", "os.startfile",
    "socket.connect", "socket.bind", "socket.sendto", "socket.getaddrinfo", "socket.gethostbyname",
}
# event name -> positions of the path arguments that must stay inside the workspace
PATH_ARGS = {
    "os.remove": [0], "os.rmdir": [0], "os.mkdir": [0], "os.truncate": [0], "os.chmod": [0],
    "os.rename": [0, 1], "os.symlink": [1], "os.link": [0, 1],
    "shutil.copyfile": [1], "shutil.copytree": [1], "shutil.move": [0, 1], "shutil.rmtree": [0],
    "shutil.copymode": [1], "shutil.copystat": [1], "shutil.make_archive": [0],
    "shutil.unpack_archive": [1],
}
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC


def _norm(p) -> str:
    return os.path.normcase(os.path.realpath(os.fsdecode(p)))


def _inside(p) -> bool:
    n = _norm(p)
    return n == WORKSPACE or n.startswith(WORKSPACE + os.sep)


def _secret(p) -> bool:
    n = _norm(p)
    parts = {x.lower() for x in Path(n).parts}
    return bool(parts & SECRET_DIRS) or Path(n).name.lower() in SECRET_FILES or Path(n).name.lower().startswith(".env")


def _deny(what: str):
    raise PermissionError(f"Blocked by sandbox: {what}")


def _hook(event: str, args: tuple) -> None:
    if event in BLOCKED_EVENTS:
        _deny(event)
    if event == "open":
        path, mode, flags = (list(args) + [None, None])[:3]
        if isinstance(path, int):
            return
        writing = any(c in str(mode or "") for c in "wax+") or (isinstance(flags, int) and flags & WRITE_FLAGS)
        if writing and not _inside(path):
            _deny(f"writing outside the workspace ({os.fsdecode(path)})")
        if not writing and _secret(path):
            _deny(f"reading a protected location ({os.fsdecode(path)})")
    elif event in PATH_ARGS:
        for i in PATH_ARGS[event]:
            if i < len(args) and isinstance(args[i], (str, bytes, os.PathLike)) and not _inside(args[i]):
                _deny(f"{event} outside the workspace ({os.fsdecode(args[i])})")


if __name__ == "__main__":
    script = os.path.realpath(sys.argv[1])
    sys.addaudithook(_hook)
    sys.argv = [script]
    runpy.run_path(script, run_name="__main__")