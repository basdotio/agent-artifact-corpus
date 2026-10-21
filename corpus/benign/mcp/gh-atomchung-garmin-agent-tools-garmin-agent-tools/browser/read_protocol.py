"""Selected-field, reusable, agent-mediated Garmin browser observation protocol."""
import json
import os
import re
import uuid
import stat
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator, model_validator

ROOT = Path(__file__).resolve().parent
from .state import state_root, ensure_state_root
PRIVATE = state_root() / "read"
RUNS = PRIVATE / "runs"
MAX_WAIT_SECONDS = 300
MAX_JSON_BYTES = 65536
MAX_WORKOUT_ID = 9007199254740991  # Exact positive integer transport through JS.
WorkoutId = Annotated[StrictInt, Field(ge=1, le=MAX_WORKOUT_ID)]


class ProtocolError(Exception):
    """Only fixed, non-sensitive names are used at output boundaries."""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("invalid_timestamp")
    return result


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReadInput(StrictModel):
    workout_id: WorkoutId


class ReadRequest(StrictModel):
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    operation: Literal["read_workout"] = "read_workout"
    workout_id: WorkoutId
    created_at: str
    expires_at: str

    @model_validator(mode="after")
    def bounded_interval(self):
        if (timestamp(self.expires_at) - timestamp(self.created_at)).total_seconds() != MAX_WAIT_SECONDS:
            raise ValueError("invalid_request_window")
        return self


def visible_label(value: str | None) -> str | None:
    if value is not None and (value != value.strip() or not value or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("invalid_visible_label")
    return value


class Step(StrictModel):
    name: str | None = Field(max_length=120)
    duration_seconds: StrictInt | None = Field(ge=0, le=604800)
    targets: list[Annotated[str, Field(min_length=1, max_length=160)]] | None = Field(max_length=8)

    @field_validator("name")
    @classmethod
    def valid_name(cls, value):
        return visible_label(value)

    @field_validator("targets")
    @classmethod
    def valid_targets(cls, value):
        if value is not None:
            for item in value:
                visible_label(item)
        return value


class CalendarEvidence(StrictModel):
    date: str | None = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    label: str | None = Field(max_length=160)

    @model_validator(mode="after")
    def explicit_evidence(self):
        visible_label(self.label)
        if self.date is not None:
            datetime.strptime(self.date, "%Y-%m-%d")
        if self.date is None and self.label is None:
            raise ValueError("missing_calendar_evidence")
        return self


class SelectedObservation(StrictModel):
    observed_at: str
    name: str | None = Field(max_length=120)
    sport: str | None = Field(max_length=80)
    steps: list[Step] | None = Field(max_length=32)
    calendar_evidence: Literal["unknown"] | CalendarEvidence = "unknown"
    watch_evidence: Literal["unknown"] = "unknown"
    api_authentication: Literal["unknown"] = "unknown"

    @field_validator("name", "sport")
    @classmethod
    def valid_label(cls, value):
        return visible_label(value)

    @field_validator("observed_at")
    @classmethod
    def valid_timestamp(cls, value):
        timestamp(value)
        return value


class BrowserResponse(SelectedObservation):
    request_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    operation: Literal["read_workout"] = "read_workout"
    workout_id: WorkoutId
    source_type: Literal["browser_ui"] = "browser_ui"
    agent_mediated: Literal[True] = True
    observation_method: Literal["cua_repl", "parent_browser_tool"] = "cua_repl"


class ReadResult(BrowserResponse):
    outcome: Literal["observed"] = "observed"
    external_writes_enabled: Literal[False] = False
    source_limit: Literal["Agent-reported fresh browser UI observation; not independently attested."] = "Agent-reported fresh browser UI observation; not independently attested."


def ensure_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700, parents=False, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ProtocolError("unsafe_directory")


def ensure_runtime() -> None:
    ensure_state_root()
    for path in (PRIVATE, RUNS):
        ensure_private_dir(path)


def create_run() -> Path:
    ensure_runtime()
    run_dir = RUNS / uuid.uuid4().hex
    run_dir.mkdir(mode=0o700, exist_ok=False)
    for name in ("queue", "ready", "receipts"):
        ensure_private_dir(run_dir / name)
    return run_dir


def validate_run(run_dir: Path) -> Path:
    # Exact fixed namespace, not arbitrary paths, aliases, traversal or symlinks.
    if not run_dir.is_absolute() or run_dir.parent != RUNS or not re.fullmatch(r"[0-9a-f]{32}", run_dir.name):
        raise ProtocolError("invalid_run_directory")
    for path in (PRIVATE, RUNS, run_dir, run_dir / "queue", run_dir / "ready", run_dir / "receipts"):
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
            raise ProtocolError("unsafe_directory")
    return run_dir


def request_directory(run_dir: Path, request_id: str) -> Path:
    validate_run(run_dir)
    if not re.fullmatch(r"[0-9a-f]{32}", request_id):
        raise ProtocolError("invalid_request_id")
    result = run_dir / "queue" / request_id
    info = result.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ProtocolError("unsafe_directory")
    return result


def create_request(run_dir: Path, workout_id: int) -> tuple[ReadRequest, Path]:
    validate_run(run_dir)
    args = ReadInput(workout_id=workout_id)
    created = utc_now()
    request = ReadRequest(request_id=uuid.uuid4().hex, workout_id=args.workout_id,
        created_at=created.isoformat(),
        expires_at=(created + timedelta(seconds=MAX_WAIT_SECONDS)).isoformat())
    directory = run_dir / "queue" / request.request_id
    directory.mkdir(mode=0o700, exist_ok=False)
    atomic_json(directory / "request.json", request.model_dump())
    atomic_json(run_dir / "ready" / (request.request_id + ".json"), {
        "request_id": request.request_id, "run_dir": str(run_dir),
        "request_dir": str(directory), "workout_id": request.workout_id,
        "created_at": request.created_at, "expires_at": request.expires_at,
        "client_id": os.environ.get("GARMIN_BROWSER_CLIENT_ID")})
    return request, directory


def atomic_json(path: Path, value: object) -> None:
    ensure_private_dir(path.parent)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()
    if len(payload) > MAX_JSON_BYTES:
        raise ProtocolError("oversized_json")
    fd, temp = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.link(temp, path)
        os.unlink(temp)
        directory_fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def read_private_json(path: Path) -> dict:
    ensure_private_dir(path.parent)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise ProtocolError("unsafe_file")
        raw = stream.read(MAX_JSON_BYTES + 1)
    if len(raw) > MAX_JSON_BYTES:
        raise ProtocolError("oversized_json")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ProtocolError("invalid_json_object")
    return value


def validate_response(value: dict, request: ReadRequest, *, now: datetime | None = None) -> BrowserResponse:
    response = BrowserResponse.model_validate(value)
    if response.name is None and not response.steps:
        raise ProtocolError("empty_observation")
    now = now or utc_now()
    if response.request_id != request.request_id:
        raise ProtocolError("request_id_mismatch")
    if response.workout_id != request.workout_id:
        raise ProtocolError("workout_id_mismatch")
    if now >= timestamp(request.expires_at):
        raise ProtocolError("request_expired")
    if not timestamp(request.created_at) <= timestamp(response.observed_at) <= now:
        raise ProtocolError("observation_not_fresh")
    return response
