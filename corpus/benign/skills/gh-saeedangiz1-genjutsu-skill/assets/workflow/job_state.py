"""Crash-safe local job state and conservative guards around billed requests.

The lock file stays on disk: OS advisory locks are released on process exit.
A saved POST intent is never silently cleared, even when its response is lost.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

_SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")


def _name(value):
    if not isinstance(value, str) or not _SAFE_NAME.fullmatch(value):
        raise ValueError("State names must be simple identifiers (letters, digits, _ or -).")
    return value


def _now():
    return datetime.now(timezone.utc).isoformat()


def _canonical(data):
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _identity(data):
    return hashlib.sha256(_canonical(data).encode("utf-8")).hexdigest()


def atomic_json(path, data):
    """Flush a JSON replacement beside its target before an atomic rename."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    fd, temporary = tempfile.mkstemp(prefix="." + path.name + "-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def job_lock(folder, name="job"):
    """Acquire a fail-fast, cross-process advisory lock for this local folder."""
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (".lock-" + _name(name))
    stream = path.open("a+b")
    acquired = False
    try:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValueError("This job is busy in another worker; resume after it finishes.") from exc
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValueError("This job is busy in another worker; resume after it finishes.") from exc
        acquired = True
        yield
    finally:
        if acquired:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        stream.close()


def _submission_path(folder, stage):
    return Path(folder) / (".submission-" + _name(stage) + ".json")


def load_submission(folder, stage, identity=None):
    """Return an accepted POST response, or reject an unresolved/changed intent."""
    path = _submission_path(folder, stage)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("Saved submission state is unreadable; reconcile it with the provider before continuing.") from exc
    if not isinstance(data, dict) or data.get("stage") != stage or data.get("version") != 1:
        raise ValueError("Saved submission state is invalid; reconcile it with the provider before continuing.")
    if identity is not None and data.get("identity") != _identity(identity):
        raise ValueError("This job's submitted inputs or prompt changed. Use a new job for a deliberate variation.")
    response = data.get("response")
    if data.get("state") == "accepted" and isinstance(response, dict) and response:
        return response
    raise ValueError(
        "A billed POST intent is already saved but its acceptance is unresolved. "
        "Do not resubmit: reconcile the request with the provider, then collect its saved request ID."
    )


def durable_submit(folder, stage, payload, send, identity=None):
    """Persist intent before calling send(); return an accepted response on resume.

    send is a no-argument callback returning a validated provider response dict.
    Any exception after intent persistence leaves an ambiguous record. The next
    invocation refuses a second POST, including after a crash or timed-out call.
    """
    _name(stage)
    bound_identity = payload if identity is None else identity
    with job_lock(folder, "submit-" + hashlib.sha256(stage.encode("utf-8")).hexdigest()[:32]):
        previous = load_submission(folder, stage, bound_identity)
        if previous is not None:
            return previous
        path = _submission_path(folder, stage)
        record = {
            "version": 1,
            "stage": stage,
            "state": "pending",
            "identity": _identity(bound_identity),
            "payload_sha256": _identity(payload),
            "payload": payload,
            "started_at": _now(),
        }
        atomic_json(path, record)
        try:
            response = send()
            if not isinstance(response, dict) or not response:
                raise ValueError("Provider returned an empty or invalid response.")
            _canonical(response)
            record.update(state="accepted", response=response, accepted_at=_now())
            atomic_json(path, record)
            return response
        except BaseException as exc:
            record.pop("response", None)
            record.update(state="ambiguous", error_type=type(exc).__name__, failed_at=_now())
            try:
                atomic_json(path, record)
            except OSError:
                pass  # The pre-send pending record still blocks a repeated POST.
            if isinstance(exc, (KeyboardInterrupt, SystemExit)):
                raise
            raise ValueError(
                "Submission acceptance is uncertain; the saved POST intent blocks automatic resubmission. "
                "Reconcile this job with the provider before continuing."
            ) from exc
