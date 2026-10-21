"""Local write preparation only. No Garmin, browser, network or approval creator."""
import hashlib
import json
import os
import re
import stat
import uuid
from datetime import date as Date, datetime, timezone
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

ROOT = Path(__file__).resolve().parent
from .state import state_root, ensure_state_root, private_location
PRIVATE = private_location(os.environ.get("GARMIN_WRITEPREP_RUNTIME", state_root() / "write"))
PREFIX = "AGENT MCP BROWSER TEST "


class ProtocolError(Exception):
    pass


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PreviewInput(StrictModel):
    name: str = Field(pattern=r"^(?:AGENT|DOT) MCP BROWSER TEST [A-Za-z0-9][A-Za-z0-9 -]{0,39}$")
    date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")

    @field_validator("date")
    @classmethod
    def calendar_date(cls, value):
        if Date.fromisoformat(value).isoformat() != value:
            raise ValueError("invalid_date")
        return value

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        if value != value.strip():
            raise ValueError("invalid_name")
        return value


class ApplyInput(StrictModel):
    preview_id: str = Field(pattern=r"^[0-9a-f]{32}$")
    proposal_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class OwnerConfirmation(ApplyInput):
    schema_version: Literal["owner-confirmation-v1"]
    name: str
    date: str
    owner_reply_reference: str = Field(min_length=1, max_length=512)
    owner_reply_at: str
    recorded_at: str
    expires_at: str
    browser_account_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")


class ObservedStep(StrictModel):
    name: str = Field(max_length=32, description="Raw visible step label; do not substitute the proposal label.")
    seconds: int = Field(ge=0, le=86400)
    target: str = Field(max_length=64, description="Raw visible target label; missing evidence never means NoTarget.")


class ObservedWorkout(StrictModel):
    workout_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=128)
    sport: str = Field(min_length=1, max_length=32, description="Raw visible sport label; English Run/Running are compared deterministically.")
    steps: list[ObservedStep] = Field(max_length=16)


class ObservedCalendar(StrictModel):
    workout_id: int = Field(gt=0)
    date: str = Field(pattern=r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


class BrowserObservation(ApplyInput):
    schema_version: Literal["selected-browser-observation-v1"]
    source_type: Literal["browser_ui"]
    agent_mediated: Literal[True]
    observed_at: str = Field(max_length=64)
    workout: ObservedWorkout | None = None
    calendar: ObservedCalendar | None = None
    browser_account_key: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @field_validator("agent_mediated", mode="before")
    @classmethod
    def true_boolean_only(cls, value):
        if value is not True:
            raise ValueError("invalid_agent_mediation")
        return value


def now():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or now()).isoformat()


def instant(value):
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ProtocolError("invalid_timestamp")
    return result


def canonical(value):
    return (json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def account_key_from_profile_url(profile_url):
    """Fingerprint an already observed OWN View Profile link; never retain it.

    This is parent-reported identity consistency, not authentication or an
    independent browser attestation. The observed link, not a display name or
    workout author's profile, must come from the current owner's account menu.
    """
    if (type(profile_url) is not str or len(profile_url) > 1024
            or any(ord(char) <= 32 or ord(char) >= 127 for char in profile_url)):
        raise ProtocolError("unknown_browser_account")
    try:
        url = urlsplit(profile_url)
        match = re.fullmatch(r"/app/profile/([A-Za-z0-9._~%-]{1,160})/?", url.path)
        valid = (url.scheme == "https" and url.hostname == "connect.garmin.com"
                 and url.port in (None, 443) and not url.username and not url.password
                 and not url.query and not url.fragment and match)
    except ValueError:
        valid = False
    if not valid:
        raise ProtocolError("unknown_browser_account")
    canonical = "https://connect.garmin.com/app/profile/" + match[1]
    return digest(("garmin-browser-account-v1\0" + canonical).encode("utf-8"))


def private_dir(path):
    path.mkdir(mode=0o700, exist_ok=True)
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise ProtocolError("unsafe_directory")


def runtime(path=PRIVATE):
    path = private_location(path)
    if path == PRIVATE and path.parent == state_root():
        ensure_state_root()
    if not path.is_absolute() or path.is_symlink():
        raise ProtocolError("unsafe_runtime")
    private_dir(path)
    for name in ("proposals", "approvals", "claims", "journal", "queue", "execution", "outcomes", "receipts", "observations"):
        private_dir(path / name)
    return path


def fsync_dir(path):
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def save_once(path, raw, immutable=False):
    """O_EXCL, fsync(file), fsync(directory); never overwrite or remove evidence.

    A crash during publication may leave an incomplete file. That fails closed;
    the existing claim still forbids redispatch. 0400 is defense in depth only.
    """
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            if immutable:
                os.fchmod(stream.fileno(), 0o400)
            os.fsync(stream.fileno())
    finally:
        fsync_dir(path.parent)


def read_bytes(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or stat.S_IMODE(info.st_mode) not in (0o600, 0o400) or info.st_nlink != 1):
            raise ProtocolError("unsafe_file")
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ProtocolError("oversized_file")
    return raw


def read_json(path):
    return json.loads(read_bytes(path))


def proposal_body(args, preview_id, created_at):
    return {"schema_version": "garmin-browser-test-proposal-v1", "preview_id": preview_id,
        "created_at": created_at, "name": args.name, "date": args.date,
        "purpose": "Connectivity test only; not a training recommendation.",
        "sport": "running", "total_seconds": 1200,
        "steps": [{"name": name, "seconds": seconds, "target": "NoTarget"}
                  for name, seconds in (("warmup", 300), ("run", 600), ("cooldown", 300))],
        "effects": [{"operation": "create_owned_new_workout", "name": args.name},
                    {"operation": "schedule_newly_created_workout", "date": args.date}],
        "existing_workout_edits": False, "deletions": False, "device_delivery": False}


def preview_test(path, arguments):
    path = runtime(path)
    args = PreviewInput.model_validate(arguments)
    preview_id = uuid.uuid4().hex
    body = proposal_body(args, preview_id, stamp())
    raw = canonical(body)
    save_once(path / "proposals" / (preview_id + ".json"), raw)
    return {"status": "preview_prepared", "preview_id": preview_id,
        "proposal_sha256": digest(raw), "proposal": body,
        "canonical_proposal_utf8": raw.decode(), "external_writes": False,
        "owner_confirmation": "not_granted_by_preview"}


def load_proposal(path, args):
    raw = read_bytes(path / "proposals" / (args.preview_id + ".json"))
    if digest(raw) != args.proposal_sha256:
        raise ProtocolError("proposal_integrity_mismatch")
    body = json.loads(raw)
    fields = PreviewInput(name=body["name"], date=body["date"])
    instant(body["created_at"])
    if body != proposal_body(fields, args.preview_id, body["created_at"]) or canonical(body) != raw:
        raise ProtocolError("proposal_shape_mismatch")
    return body


def current_confirmation(path, args, body):
    """Reads only. No function or tool creates real owner confirmation."""
    try:
        record = OwnerConfirmation.model_validate(read_json(path / "approvals" / (args.preview_id + ".json")))
    except FileNotFoundError:
        return None
    if record.browser_account_key is None:
        return None
    binding = {"preview_id": args.preview_id, "proposal_sha256": args.proposal_sha256,
               "name": body["name"], "date": body["date"]}
    if any(getattr(record, key) != value for key, value in binding.items()):
        return None
    current = now()
    reply, recorded, expiry = map(instant, (record.owner_reply_at, record.recorded_at, record.expires_at))
    if not (instant(body["created_at"]) <= reply <= recorded <= current < expiry
            and record.owner_reply_reference.strip() == record.owner_reply_reference
            and all(ord(c) >= 32 for c in record.owner_reply_reference)):
        return None
    return record.model_dump()


def journal(path, preview_id, event, data):
    save_once(path / "journal" / (preview_id + "-" + event + ".json"),
        canonical({"preview_id": preview_id, "event": event, "at": stamp(), **data}), immutable=True)


def state(path, args):
    result = {"preview_id": args.preview_id, "proposal_sha256": args.proposal_sha256,
              "external_success": False, "automatic_retry": False, "account_identity": "unknown"}
    # Observation receipts are append-only. A later read-only reconciliation may
    # supersede a partial outcome without changing that original outcome/evidence.
    observed = observation_state(path, args)
    outcome = path / "outcomes" / (args.preview_id + ".json")
    if observed is not None:
        # A newer adverse outcome also remains authoritative. A malformed outcome
        # cannot be hidden by an otherwise matching older observation.
        prefer_observation = not outcome.exists()
        if not prefer_observation and "recorded_at" in observed:
            try:
                prior = read_json(outcome)
                valid_prior = (set(prior) == {"preview_id", "proposal_sha256", "status", "at", "external_success",
                                             "automatic_retry", "reconciliation_required"}
                               and prior["preview_id"] == args.preview_id
                               and prior["proposal_sha256"] == args.proposal_sha256
                               and prior["status"] in ("partial", "uncertain")
                               and prior["external_success"] is False and prior["automatic_retry"] is False
                               and prior["reconciliation_required"] is True)
                prefer_observation = (valid_prior
                    and instant(prior["at"]) < instant(observed["recorded_at"]))
            except Exception:
                prefer_observation = False
        if prefer_observation or not observed["browser_readback_match"]:
            if observed["browser_readback_match"]:
                result.pop("external_success")
            return {**result, **observed}
    if outcome.exists():
        try:
            data = read_json(outcome)
            valid = (set(data) == {"preview_id", "proposal_sha256", "status", "at", "external_success",
                                  "automatic_retry", "reconciliation_required"}
                     and data["preview_id"] == args.preview_id
                     and data["proposal_sha256"] == args.proposal_sha256
                     and data["status"] in ("partial", "uncertain")
                     and data["external_success"] is False and data["automatic_retry"] is False
                     and data["reconciliation_required"] is True)
            instant(data["at"])
        except Exception:
            valid = False
        result.update(status=data["status"] if valid else "uncertain", reconciliation_required=True)
    elif (path / "execution" / (args.preview_id + ".json")).exists():
        result.update(status="uncertain", reconciliation_required=True)
    elif (path / "queue" / (args.preview_id + ".json")).exists():
        result.update(status="pending_parent_cua", reconciliation_required=False)
    else:
        result.update(status="uncertain", reconciliation_required=True)
    return result


def apply_test(path, arguments):
    path = runtime(path)
    args = ApplyInput.model_validate(arguments)
    body = load_proposal(path, args)
    claim = path / "claims" / (args.preview_id + ".json")
    if claim.exists():
        return {**state(path, args), "redispatched": False}
    approval = current_confirmation(path, args, body)
    if approval is None:
        return {"status": "awaiting_owner_confirmation", **args.model_dump(),
                "external_success": False, "queued": False, "automatic_retry": False}
    data = {**args.model_dump(), "at": stamp(), "approval": approval}
    try:
        save_once(claim, canonical(data), immutable=True)
    except FileExistsError:
        return {**state(path, args), "redispatched": False}
    # No operation before these durable writes can enqueue or contact a service.
    # Any exception/crash after the claim permanently prevents redispatch.
    journal(path, args.preview_id, "dispatch_claimed", data)
    save_once(path / "queue" / (args.preview_id + ".json"),
        canonical({**data, "proposal": body, "worker": "trusted_parent_cua_only",
                   "status": "pending", "external_success": False}), immutable=True)
    return {**state(path, args), "queued": True, "redispatched": False}


def claim_execution(path, arguments, *, browser_account_key=None):
    """Trusted parent integration, NOT an MCP tool. Call before any UI mutation.

    Still performs NO browser/network operation. A claim is consumed forever even
    if the caller crashes before receiving this return value.
    """
    path = runtime(path)
    args = ApplyInput.model_validate(arguments)
    body = load_proposal(path, args)
    queue = read_json(path / "queue" / (args.preview_id + ".json"))
    confirmation = current_confirmation(path, args, body)
    if (queue["proposal"] != body or queue["proposal_sha256"] != args.proposal_sha256
            or confirmation is None or queue["approval"] != confirmation
            or browser_account_key != confirmation["browser_account_key"]):
        raise ProtocolError("execution_not_authorized")
    # Verify immutable dispatch evidence exists before claiming execution.
    read_json(path / "claims" / (args.preview_id + ".json"))
    read_json(path / "journal" / (args.preview_id + "-dispatch_claimed.json"))
    data = {**args.model_dump(), "at": stamp(), "status": "write_may_have_started",
            "browser_account_key": browser_account_key}
    save_once(path / "execution" / (args.preview_id + ".json"), canonical(data), immutable=True)
    journal(path, args.preview_id, "external_write_intent", data)
    return body


def record_worker_outcome(path, arguments, status):
    """External parent partial/uncertain receipt helper, never an MCP tool."""
    path = runtime(path)
    args = ApplyInput.model_validate(arguments)
    load_proposal(path, args)
    if status not in ("partial", "uncertain"):
        raise ProtocolError("unsupported_outcome")
    read_json(path / "execution" / (args.preview_id + ".json"))
    data = {**args.model_dump(), "status": status, "at": stamp(), "external_success": False,
            "automatic_retry": False, "reconciliation_required": True}
    save_once(path / "outcomes" / (args.preview_id + ".json"), canonical(data), immutable=True)
    journal(path, args.preview_id, "outcome", data)
    return data


def execution_evidence(path, args, body):
    execution = read_json(path / "execution" / (args.preview_id + ".json"))
    approval = OwnerConfirmation.model_validate(read_json(path / "queue" / (args.preview_id + ".json"))["approval"])
    if (set(execution) != {"preview_id", "proposal_sha256", "at", "status", "browser_account_key"}
            or execution["preview_id"] != args.preview_id
            or execution["proposal_sha256"] != args.proposal_sha256
            or approval.browser_account_key is None
            or execution["browser_account_key"] != approval.browser_account_key
            or execution["status"] != "write_may_have_started"
            or not (instant(body["created_at"]) <= instant(execution["at"]) <= now())):
        raise ProtocolError("invalid_execution_evidence")
    intent = read_json(path / "journal" / (args.preview_id + "-external_write_intent.json"))
    if intent != {**execution, "event": "external_write_intent"}:
        raise ProtocolError("invalid_execution_evidence")
    return execution


def classify_observation(args, body, execution, observation, recorded_at):
    observed = instant(observation.observed_at)
    recorded = instant(recorded_at)
    bound = (observation.preview_id == args.preview_id
             and observation.proposal_sha256 == args.proposal_sha256)
    fresh = (instant(body["created_at"]) <= instant(execution["at"]) < observed <= recorded <= now())
    workout, calendar = observation.workout, observation.calendar
    account_match = (observation.browser_account_key is not None
                     and observation.browser_account_key == execution["browser_account_key"])
    match = bool(bound and fresh and account_match and workout and calendar
                 and workout.name == body["name"]
                 and {"run": "running", "running": "running"}.get(normalized_label(workout.sport)) == body["sport"]
                 and normalized_steps(workout.steps) == body["steps"]
                 and calendar.workout_id == workout.workout_id
                 and calendar.date == body["date"])
    return {"status": "browser_observed_scheduled" if match else "uncertain",
            "browser_readback_match": match, "source_type": "browser_ui", "agent_mediated": True,
            "verification": "agent_reported_browser_ui_not_independently_verified",
            "independently_verified": False, "api_authentication": "unknown", "watch": "unknown",
            "automatic_retry": False, "reconciliation_required": not match,
            "account_identity": "matched_parent_reported" if account_match else "unknown_or_mismatched"}


def normalized_label(value):
    return " ".join(value.casefold().split())


def normalized_steps(steps):
    """Compare known English UI labels while preserving raw receipt values."""
    names = {"warm up": "warmup", "warmup": "warmup", "run": "run",
             "cool down": "cooldown", "cooldown": "cooldown"}
    targets = {"no target": "NoTarget", "notarget": "NoTarget"}
    return [{"name": names.get(normalized_label(step.name)), "seconds": step.seconds,
             "target": targets.get(normalized_label(step.target))} for step in steps]


def record_browser_observation(path, arguments, selected):
    """Trusted-parent local helper AFTER execution claim; NOT an approval/MCP tool.

    Accept only bounded selected UI fields. Never accept DOMs, provider bodies,
    cookies or credentials. This records the parent's report, not an independent
    browser inspection. Mismatch/missing data stays uncertain; no automatic retry.
    """
    path = runtime(path)
    args = ApplyInput.model_validate(arguments)
    body = load_proposal(path, args)
    execution = execution_evidence(path, args, body)
    observation = BrowserObservation.model_validate(selected)
    recorded_at = stamp()
    result = classify_observation(args, body, execution, observation, recorded_at)
    receipt_id = uuid.uuid4().hex
    data = {"schema_version": "browser-observation-receipt-v1", "receipt_id": receipt_id,
            **args.model_dump(), "recorded_at": recorded_at,
            "observation": observation.model_dump(), **result}
    # The immutable journal must also exist before any readback can claim a match.
    save_once(path / "observations" / (args.preview_id + "-" + receipt_id + ".json"),
              canonical(data), immutable=True)
    journal(path, args.preview_id, "browser_observation-" + receipt_id, data)
    return data


def observation_state(path, args):
    files = sorted((path / "observations").glob(args.preview_id + "-*.json"))
    if not files:
        return None
    failed = {"status": "uncertain", "browser_readback_match": False,
              "reconciliation_required": True, "automatic_retry": False,
              "independently_verified": False, "api_authentication": "unknown", "watch": "unknown",
              "account_identity": "unknown"}
    try:
        body = load_proposal(path, args)
        execution = execution_evidence(path, args, body)
        receipts = []
        for file in files:
            data = read_json(file)
            receipt_id = data["receipt_id"]
            if not re.fullmatch(r"[0-9a-f]{32}", receipt_id):
                return failed
            if file.name != args.preview_id + "-" + receipt_id + ".json":
                return failed
            observation = BrowserObservation.model_validate(data["observation"])
            expected = {"schema_version": "browser-observation-receipt-v1", "receipt_id": receipt_id,
                        **args.model_dump(), "recorded_at": data["recorded_at"],
                        "observation": observation.model_dump(),
                        **classify_observation(args, body, execution, observation, data["recorded_at"])}
            event = "browser_observation-" + receipt_id
            evidence = read_json(path / "journal" / (args.preview_id + "-" + event + ".json"))
            journal_at = instant(evidence["at"])
            if (data != expected or evidence != {"event": event, "at": evidence["at"], **data}
                    or not instant(data["recorded_at"]) <= journal_at <= now()):
                return failed
            receipts.append(data)
        latest = max(receipts, key=lambda item: (instant(item["recorded_at"]), item["receipt_id"]))
        return {key: latest[key] for key in ("status", "browser_readback_match", "source_type",
            "agent_mediated", "verification", "independently_verified", "api_authentication", "watch",
            "automatic_retry", "reconciliation_required", "receipt_id", "recorded_at", "account_identity")}
    except Exception:
        return failed
