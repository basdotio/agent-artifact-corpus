"""A project journal shared by Python, CLI and MCP. No credentials are stored here."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from collections.abc import Iterator, Mapping
from contextlib import contextmanager, suppress
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from .amounts import validate_spending_cap
from .client import OPERATION_KINDS, LeanWarpCloud, LeanWarpCloudError, OperationTimeout
from .edits import EDITING_KINDS, EditError, edited_sha256, edited_source
from .outcome import OperationOutcome
from .project import (
    ProjectError,
    ProjectIdentity,
    choose_environment,
    collect_lean_sources,
    environment_name,
    plan_upload,
    project_identity,
    selects,
    validate_selection,
)
from .resources import published_worker_resources

_MAX_JOURNAL_BYTES = 8 * 1024 * 1024
_TERMINAL_STATES = frozenset({"completed", "failed", "cancelled"})
# Each page holds at least one of the roughly 1,000 operations a workspace stores;
# this only stops a cursor that never ends.
_MAX_HISTORY_PAGES = 2000
# Polling shares this budget (see LeanWarpCloud.wait). Even one bounded overrun
# read keeps an inline wait under the common 60-second MCP client tool deadline.
MAX_INLINE_WAIT_SECONDS = 40
_JOURNAL_DAMAGED = (
    ".leanwarp/session.json is damaged; keep it, since it may record an unfinished request"
)
# A newer client may journal a kind this one does not know; the server, not the
# journal, decides which kinds exist, so any well-formed name is recoverable.
_OPERATION_KIND = re.compile(r"[a-z][a-z0-9_]{0,63}")
_OPERATION_EXPIRED = (
    "the last operation finished and LeanWarp no longer stores its result; "
    "submit it again to repeat the work"
)


class SessionError(RuntimeError):
    """Local recovery or project reconciliation is required before another write."""


class UsageError(ValueError):
    """An argument outside its supported range; nothing was sent."""


class WaitError(UsageError):
    """An inline wait outside its supported range; nothing was submitted."""


class ProjectSession:
    """One local project and one durable hosted workspace.

    Mutations journal their exact payload before sending. An ambiguous request is
    replayed only through recover(), never replaced by a new request. A process
    lock serializes CLI/MCP clients on this project; server revisions protect
    separate devices. Closing the HTTP client does not stop paid compute.
    """

    def __init__(self, cloud: LeanWarpCloud, root: str | Path = ".") -> None:
        self.cloud = cloud
        self.root = Path(root).resolve(strict=True)
        self.directory = self.root / ".leanwarp"
        self.path = self.directory / "session.json"
        # Which files the latest operation was asked about. It lives beside the
        # journal, not in it, so clients that predate it still read the journal.
        self.submitted = self.directory / "operation.json"

    @contextmanager
    def _locked(self) -> Iterator[dict[str, Any]]:
        if os.name != "posix":
            raise SessionError("project sessions require macOS, Linux or WSL")
        import fcntl

        self.directory.mkdir(mode=0o700, exist_ok=True)
        if self.directory.is_symlink() or not self.directory.is_dir():
            raise SessionError(".leanwarp must be a directory, not a symlink")
        fd = os.open(self.directory / "lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise SessionError(
                    "another LeanWarp command is using this project; let it finish"
                ) from error
            state = self._read()
            owner = self.cloud.account().get("owner_id")
            if not isinstance(owner, str) or not owner:
                raise SessionError("API returned an invalid account identity")
            if state.get("owner_id", owner) != owner:
                raise SessionError(
                    "this project was connected with another account; sign in with a key "
                    "from that account"
                )
            state["owner_id"] = owner
            yield state
        finally:
            os.close(fd)

    def _read(self) -> dict[str, Any]:
        try:
            fd = os.open(self.path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except FileNotFoundError:
            return {"schema": 1, "base_url": self.cloud.base_url, "files": {}, "pending": None}
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                raise SessionError("project journal must be a regular file")
            raw = stream.read(_MAX_JOURNAL_BYTES + 1)
        try:
            state = json.loads(raw) if len(raw) <= _MAX_JOURNAL_BYTES else None
        except ValueError as error:
            raise SessionError(_JOURNAL_DAMAGED) from error
        if (
            not isinstance(state, dict)
            or state.get("schema") != 1
            or state.get("base_url") != self.cloud.base_url
            or not isinstance(state.get("files"), dict)
            or not set(state).issubset(
                {
                    "schema",
                    "base_url",
                    "owner_id",
                    "files",
                    "pending",
                    "workspace_id",
                    "revision",
                    "environment",
                    "operation_id",
                    "operation_revision",
                }
            )
        ):
            raise SessionError(
                ".leanwarp/session.json belongs to another LeanWarp service or is damaged; "
                "keep it and sign in with a key for the service it was created with"
            )
        _validate_journal(state)
        return state

    def _save(self, state: dict[str, Any]) -> None:
        # Never persist an intent that recovery cannot read. Validation happens
        # before replacing the last good journal or sending the request.
        _validate_journal(state)
        raw = json.dumps(state, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(raw) > _MAX_JOURNAL_BYTES:
            raise SessionError("this request is too large to record for recovery")
        self._write(self.path, raw)

    def _write(self, path: Path, raw: bytes) -> None:
        """Replace a file in .leanwarp atomically and durably."""
        fd, name = tempfile.mkstemp(prefix="session-", dir=self.directory)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, path)
            directory_fd = os.open(self.directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        finally:
            Path(name).unlink(missing_ok=True)

    @staticmethod
    def _workspace(state: Mapping[str, Any]) -> str:
        workspace = state.get("workspace_id")
        if not isinstance(workspace, str) or not workspace:
            raise SessionError("this project is not connected; run `leanwarp connect`")
        return workspace

    @staticmethod
    def _ready(state: Mapping[str, Any]) -> None:
        if state.get("pending") is not None:
            raise SessionError(
                "an earlier request may not have reached LeanWarp; run `leanwarp recover` first"
            )

    def _environment(self, state: dict[str, Any]) -> None:
        identity = project_identity(self.root, allow_empty=True)
        environment = list(identity.journal())
        if environment == state.get("environment"):
            return
        if list(identity.journal(legacy=True)) != state.get("environment"):
            raise SessionError(
                "the project's toolchain or lockfile changed since it was connected; run "
                "`leanwarp stop`, `leanwarp disconnect` and `leanwarp connect`"
            )
        # Upgrade a byte-bound journal only while the original bytes still match.
        state["environment"] = environment
        self._save(state)

    def _previous_operation(self, state: Mapping[str, Any]) -> dict[str, Any] | None:
        """This project's last operation, or None once LeanWarp no longer stores it.

        LeanWarp keeps a window of finished history and never removes queued or
        running work, so a missing operation has finished and must not strand the
        project. Every other failure still propagates.
        """
        try:
            return self._checked_operation(state, self.cloud.operation(state["operation_id"]))
        except LeanWarpCloudError as error:
            if error.status_code == 404 and error.code == "not_found":
                return None
            raise

    @staticmethod
    def _checked_operation(state: Mapping[str, Any], result: dict[str, Any]) -> dict[str, Any]:
        # Workspace sync can advance revision after submission. Compare against
        # the saved submission, not the workspace's current revision. Older
        # journals have no operation_revision; keep their existing ID binding.
        revision = state.get("operation_revision")
        if result.get("operation_id") != state.get("operation_id") or (
            revision is not None
            and (type(result.get("revision")) is not int or result["revision"] != revision)
        ):
            raise SessionError(
                "LeanWarp returned a different operation than this project submitted; "
                "run `leanwarp status`"
            )
        return result

    def connect(
        self,
        *,
        resource_profile: str | None = None,
        max_resource_profile: str | None = None,
        max_spend_microusd: int | None = None,
        environment: str | None = None,
        bundle_id: str | None = None,
        workspace_id: str | None = None,
    ) -> dict[str, Any]:
        """Create this project's workspace once, without starting compute.

        With ``workspace_id``, connect to an existing workspace instead, such as
        one from another machine. Its current files become this project's
        baseline, so the next sync uploads only the files that differ; the
        result lists them. Its environment must match the project, unless
        ``environment`` names it explicitly.

        LeanWarp picks the environment that matches the project's toolchain and
        lockfile, or the newest one for a project that pins neither. Name an
        environment to run a project that matches none of them.

        A cap limits total workspace spending, including reserved credit. On an
        existing connection, an omitted cap keeps its current limit; a supplied
        cap must match. Change an existing cap in the account dashboard.
        """
        validate_selection(environment, bundle_id)
        try:
            validate_spending_cap(max_spend_microusd)
        except ValueError as error:
            raise UsageError(str(error)) from error
        if workspace_id is not None and (
            resource_profile is not None or max_resource_profile is not None or bundle_id
        ):
            raise UsageError("an existing workspace keeps its own environment and worker size")
        with self._locked() as state:
            self._ready(state)
            if workspace_id is not None and state.get("workspace_id") not in (None, workspace_id):
                raise SessionError(
                    f"this project is connected to workspace {state['workspace_id']}; run "
                    "`leanwarp stop` and `leanwarp disconnect` before connecting to another"
                )
            if state.get("workspace_id"):
                self._environment(state)
                workspace = self.cloud.workspace(self._workspace(state))
                if bundle_id is not None:
                    choose_environment(
                        project_identity(self.root, allow_empty=True),
                        self.cloud.versions()["versions"],
                        bundle_id=bundle_id,
                    )
                if not selects(workspace, environment or bundle_id):
                    raise SessionError(
                        f"this project is connected to {environment_name(workspace)}; run "
                        "`leanwarp stop` and `leanwarp disconnect` before choosing another "
                        "environment"
                    )
                _check_cap(workspace, max_spend_microusd)
                return workspace
            identity = project_identity(self.root)
            if workspace_id is not None:
                return self._attach(state, identity, workspace_id, environment, max_spend_microusd)
            choice = choose_environment(
                identity, self.cloud.versions()["versions"], environment, bundle_id=bundle_id
            )
            state["environment"] = list(identity.journal())
            arguments: dict[str, Any] = {
                "bundle_id": choice.build["bundle_id"],
                "max_spend_microusd": max_spend_microusd,
            }
            if resource_profile is not None:
                arguments["resource_profile"] = resource_profile
            if max_resource_profile is not None:
                arguments["max_resource_profile"] = max_resource_profile
            workspace = self._request(state, "create_workspace", arguments)
            return {**workspace, "environment_choice": choice.public()}

    def _attach(
        self,
        state: dict[str, Any],
        identity: ProjectIdentity,
        workspace_id: str,
        environment: str | None,
        max_spend_microusd: int | None,
    ) -> dict[str, Any]:
        workspace = self.cloud.workspace(workspace_id)
        if workspace.get("workspace_id") != workspace_id:
            raise SessionError("LeanWarp returned a different workspace; try again")
        _check_cap(workspace, max_spend_microusd)
        build = next(
            (
                build
                for build in self.cloud.versions()["versions"]
                if selects(build, str(workspace.get("bundle_id", "")))
            ),
            None,
        )
        if build is None:
            raise SessionError(
                f"workspace {workspace_id} runs {environment_name(workspace)}, which LeanWarp "
                "no longer serves; run `leanwarp connect` without a workspace to create one"
            )
        if environment is not None and not selects(workspace, environment):
            raise SessionError(
                f"workspace {workspace_id} runs {environment_name(workspace)}, not {environment}"
            )
        if environment is None and not identity.matches(build):
            raise SessionError(
                f"workspace {workspace_id} runs {environment_name(build)}, which does not match "
                "this project's toolchain or lockfile; to use it anyway, pass "
                f"`--environment {environment_name(build)}`"
            )
        revision, files = self._manifest(workspace_id)
        changes = self._changes(files)
        state.update(
            workspace_id=workspace_id,
            revision=revision,
            files=files,
            environment=list(identity.journal()),
        )
        self._save(state)
        return {**workspace, "connected_existing": True, **changes}

    def _manifest(self, workspace_id: str) -> tuple[int, dict[str, str]]:
        """The workspace's committed revision and each file's SHA-256."""
        remote = self.cloud.workspace_files(workspace_id)
        files = remote.get("files")
        if (
            remote.get("workspace_id") != workspace_id
            or type(remote.get("revision")) is not int
            or not 0 <= remote["revision"] <= 2**31 - 1
            or not isinstance(files, dict)
            or not all(
                isinstance(path, str)
                and isinstance(digest, str)
                and len(digest) == 64
                and all(c in "0123456789abcdef" for c in digest)
                for path, digest in files.items()
            )
        ):
            raise SessionError("LeanWarp's file list was incomplete; try again")
        return remote["revision"], dict(files)

    def _changes(self, remote: Mapping[str, str]) -> dict[str, list[str]]:
        """What the next sync uploads or deletes, measured against ``remote``."""
        local = {
            name: hashlib.sha256(text.encode()).hexdigest()
            for name, text in collect_lean_sources(self.root).items()
        }
        return {
            "upload": sorted(name for name in local if remote.get(name) != local[name]),
            "delete": sorted(set(remote) - set(local)),
        }

    def workspaces(self) -> dict[str, Any]:
        """The account's workspaces, marking the one this project is connected to."""
        if self.directory.is_symlink():
            raise SessionError(".leanwarp must be a directory, not a symlink")
        connected = self._read().get("workspace_id")
        listed = self.cloud.workspaces().get("workspaces")
        if not isinstance(listed, list) or not all(isinstance(item, dict) for item in listed):
            raise SessionError("LeanWarp's workspace list was incomplete; try again")
        return {
            "workspaces": [
                {**item, "this_project": item.get("workspace_id") == connected} for item in listed
            ]
        }

    def history_page(
        self, *, workspace_id: str | None = None, cursor: str | None = None
    ) -> dict[str, Any]:
        """One page of a workspace's operations with their results, newest first.

        Defaults to this project's workspace. Pass ``next_cursor`` for the next,
        older page; it is None after the last one.
        """
        if workspace_id is None:
            if self.directory.is_symlink():
                raise SessionError(".leanwarp must be a directory, not a symlink")
            workspace_id = self._workspace(self._read())
        page = self.cloud.operations(workspace_id, cursor=cursor)
        operations, following = page.get("operations"), page.get("next_cursor")
        if (
            not isinstance(operations, list)
            or not all(
                isinstance(item, dict) and item.get("workspace_id") == workspace_id
                for item in operations
            )
            or not (following is None or (isinstance(following, str) and operations))
        ):
            raise SessionError("LeanWarp's operation history was incomplete; try again")
        return {"workspace_id": workspace_id, "operations": operations, "next_cursor": following}

    def history(self, workspace_id: str | None = None) -> Iterator[dict[str, Any]]:
        """Every stored operation of a workspace with its result, newest first.

        LeanWarp keeps a window of finished history, so export what you want to
        keep. Pages are read as the iterator advances.
        """
        cursor = None
        for _ in range(_MAX_HISTORY_PAGES):
            page = self.history_page(workspace_id=workspace_id, cursor=cursor)
            workspace_id, cursor = page["workspace_id"], page["next_cursor"]
            yield from page["operations"]
            if cursor is None:
                return
        raise SessionError("LeanWarp's operation history did not end; try again")

    def delete(self, workspace_id: str) -> dict[str, Any]:
        """Delete a workspace with its files and results; account credit is kept.

        This cannot be undone, so the workspace is named explicitly, never
        implied. LeanWarp refuses while work is queued or running. Deleting this
        project's workspace also disconnects the project, discarding any request
        that awaits `recover`, since that request's workspace no longer exists.
        This also disconnects a workspace already deleted from the dashboard or
        by an earlier deletion whose response was lost.
        """
        with self._locked() as state:
            connected = state.get("workspace_id")
            if not connected:
                # An unresolved create could be the very workspace named here.
                self._ready(state)
            try:
                self.cloud.delete(workspace_id)
            except LeanWarpCloudError as error:
                # The account was checked by _locked. Only the explicitly named,
                # known connection can converge on absence; a typo or an unknown
                # workspace must still report the server's error.
                if not (
                    workspace_id == connected
                    and error.status_code == 404
                    and error.code == "not_found"
                ):
                    raise
            if workspace_id == connected:
                for key in ("workspace_id", "revision", "operation_id", "operation_revision"):
                    state.pop(key, None)
                state["files"] = {}
                state["pending"] = None
                self._save(state)
            return {
                "status": "deleted",
                "workspace_id": workspace_id,
                "disconnected": workspace_id == connected,
            }

    def doctor(self, *, environment: str | None = None) -> dict[str, Any]:
        """Report the saved connection or a proposed choice without writes or compute."""
        if self.directory.is_symlink():
            raise SessionError(".leanwarp must be a directory, not a symlink")
        state = self._read()
        catalog = self.cloud.versions()["versions"]
        resources = self.cloud.resources()
        report: dict[str, Any] = {
            "environments": _environment_names(catalog),
            "matching_bundles": [],
            **published_worker_resources(resources),
            "base_url": self.cloud.base_url,
            "connected": bool(state.get("workspace_id")),
            "recovery_required": state.get("pending") is not None,
        }
        if state.get("pending") is not None:
            return {
                **report,
                "compatible": False,
                "message": "run `leanwarp recover` before choosing an environment",
            }
        identity = project_identity(self.root, allow_empty=bool(state.get("workspace_id")))
        report.update(_project_report(self.root, identity, catalog))
        if state.get("workspace_id"):
            owner = self.cloud.account().get("owner_id")
            if not isinstance(owner, str) or not owner or owner != state.get("owner_id", owner):
                raise SessionError(
                    "this project belongs to another account; restore its credentials"
                )
            workspace = self.cloud.workspace(self._workspace(state))
            build = next(
                (build for build in catalog if selects(build, str(workspace.get("bundle_id", "")))),
                None,
            )
            if build is None:
                return {
                    **report,
                    "compatible": False,
                    "environment": environment_name(workspace),
                    "message": (
                        "the connected environment is no longer served; "
                        "stop and disconnect before reconnecting"
                    ),
                }
            choice = {
                "environment": environment_name(build),
                "lean_toolchain": build["lean_toolchain"],
                "match": "connected",
                "matches_project": identity.matches(build),
            }
            if list(identity.journal()) != state.get("environment") and list(
                identity.journal(legacy=True)
            ) != state.get("environment"):
                return {
                    **report,
                    "compatible": False,
                    "environment": choice,
                    "message": (
                        "the project's toolchain or lockfile changed; "
                        "stop, disconnect and reconnect"
                    ),
                }
            if not selects(workspace, environment):
                return {
                    **report,
                    "compatible": False,
                    "environment": choice,
                    "message": "stop and disconnect before choosing another environment",
                }
            return {**report, "compatible": True, "environment": choice}
        return {**report, **_choice_report(identity, catalog, environment)}

    def sync(self) -> dict[str, Any]:
        with self._locked() as state:
            self._ready(state)
            return self._sync(state)

    def _sync(self, state: dict[str, Any]) -> dict[str, Any]:
        _check_apply_recovery(self.directory)
        workspace = self._workspace(state)
        self._environment(state)
        sources = collect_lean_sources(self.root)
        hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name, text in sources.items()}
        files = {
            name: text for name, text in sources.items() if state["files"].get(name) != hashes[name]
        }
        deleted = sorted(set(state["files"]) - set(sources))
        if not files and not deleted:
            return {"workspace_id": workspace, "revision": state["revision"]}
        return self._request(
            state,
            "sync_files",
            {
                "workspace_id": workspace,
                "expected_revision": state["revision"],
                "files": files,
                "delete_paths": deleted,
            },
            hashes=hashes,
        )

    def submit(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        resource_profile: str | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Sync acknowledged source, then submit without hiding a second paid operation."""
        if kind not in OPERATION_KINDS:
            raise UsageError(f"{kind!r} is not a LeanWarp operation")
        if timeout_seconds is not None and (
            type(timeout_seconds) is not int or not 1 <= timeout_seconds <= 600
        ):
            raise UsageError(
                "the execution timeout must be a whole number of seconds from 1 to 600"
            )
        json.dumps(dict(payload), allow_nan=False)
        with self._locked() as state:
            self._ready(state)
            if state.get("operation_id"):
                previous = self._previous_operation(state)
                if previous is not None and previous.get("state") not in _TERMINAL_STATES:
                    raise SessionError(
                        "the previous operation is still running; run `leanwarp wait` or "
                        "`leanwarp cancel` first"
                    )
            self._sync(state)
            body: dict[str, Any] = {
                "workspace_id": self._workspace(state),
                "kind": kind,
                "expected_revision": state["revision"],
                "payload": dict(payload),
            }
            if resource_profile is not None:
                body["resource_profile"] = resource_profile
            if timeout_seconds is not None:
                body["timeout_seconds"] = timeout_seconds
            return self._request(state, "submit", body)

    def submit_and_wait(
        self,
        kind: str,
        payload: Mapping[str, Any],
        *,
        wait_seconds: float,
        resource_profile: str | None = None,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:
        """Submit, then poll briefly for the result in the same call.

        An acknowledged submission is durable, so neither an expired wait nor a
        failed poll raises: the still-running operation is returned and the caller
        continues with wait(). Polling never cancels server work.
        """
        if (
            isinstance(wait_seconds, bool)
            or not isinstance(wait_seconds, int | float)
            or not 0 <= wait_seconds <= MAX_INLINE_WAIT_SECONDS
        ):
            raise WaitError(
                f"the inline wait must be between 0 and {MAX_INLINE_WAIT_SECONDS} seconds; "
                "poll longer with wait"
            )
        operation = self.submit(
            kind, payload, resource_profile=resource_profile, timeout_seconds=timeout_seconds
        )
        if wait_seconds == 0 or operation.get("state") in _TERMINAL_STATES:
            return operation
        submitted = {
            "operation_id": operation["operation_id"],
            "operation_revision": operation["revision"],
        }
        # Poll this exact operation without the project lock, which another local
        # command may hold; the receipt check below binds the result to it.
        try:
            latest = self.cloud.wait(operation["operation_id"], timeout=wait_seconds)
        except OperationTimeout as error:
            latest = error.operation or operation
        except (httpx.TransportError, LeanWarpCloudError):
            latest = operation
        return self._checked_operation(submitted, latest)

    def _request(
        self,
        state: dict[str, Any],
        method: str,
        arguments: dict[str, Any],
        *,
        hashes: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        pending = {
            "method": method,
            # Own the JSON snapshot before saving or sending it. Caller-owned
            # lists and dictionaries must not diverge from the durable intent.
            "arguments": json.loads(json.dumps(arguments, ensure_ascii=False, allow_nan=False)),
            "idempotency_key": uuid4().hex,
            "hashes": hashes,
        }
        state["pending"] = pending
        self._save(state)
        return self._replay(state)

    def _replay(self, state: dict[str, Any]) -> dict[str, Any]:
        pending = state["pending"]
        if (
            not isinstance(pending, dict)
            or pending.get("method") not in {"create_workspace", "sync_files", "submit"}
            or not isinstance(pending.get("arguments"), dict)
            or not isinstance(pending.get("idempotency_key"), str)
        ):
            raise SessionError(_JOURNAL_DAMAGED)
        method = pending["method"]
        try:
            if method == "create_workspace":
                # Replay the exact creation body, including older journals that
                # omit defaults. Adding or stripping a cap changes its identity.
                result = self.cloud._request(
                    "POST",
                    "workspaces",
                    body=pending["arguments"],
                    idempotency_key=pending["idempotency_key"],
                )
            else:
                result = getattr(self.cloud, method)(
                    **pending["arguments"], idempotency_key=pending["idempotency_key"]
                )
        except LeanWarpCloudError as error:
            # Definite rejection has no accepted effect. Auth/transient/ambiguous
            # errors keep the intent recoverable, including a rotated key later.
            if error.status_code in {400, 404, 409, 413, 422}:
                state["pending"] = None
                self._save(state)
            raise
        # A successful but malformed response is still an uncertain request.
        # Preserve the exact journal and idempotency key for recovery.
        identifier = "operation_id" if method == "submit" else "workspace_id"
        if (
            not isinstance(result.get(identifier), str)
            or not 0 < len(result[identifier]) <= 256
            or type(result.get("revision")) is not int
            or not 0 <= result["revision"] <= 2**31 - 1
            or (
                method != "create_workspace" and result.get("workspace_id") != state["workspace_id"]
            )
            or (
                method == "submit"
                and (
                    result["revision"] != pending["arguments"]["expected_revision"]
                    or result.get("kind") != pending["arguments"]["kind"]
                )
            )
        ):
            raise SessionError("LeanWarp's response was incomplete; run `leanwarp recover`")
        if method == "create_workspace":
            state["workspace_id"] = result["workspace_id"]
            state["revision"] = result["revision"]
        elif method == "sync_files":
            state["revision"] = result["revision"]
            state["files"] = pending["hashes"]
        else:
            state["operation_id"] = result["operation_id"]
            state["operation_revision"] = result["revision"]
        if method == "submit":
            payload = pending["arguments"]["payload"]
            files = payload.get("files") if isinstance(payload.get("files"), list) else None
            sources = files if files is not None else [payload.get("file")]
            record = {"operation_id": result["operation_id"], "sources": sources}
            # Keep the exact request replayable until its apply binding is durable.
            # Replaying after either write is interrupted uses the same idempotency key.
            self._write(self.submitted, json.dumps(record, ensure_ascii=False).encode("utf-8"))
        state["pending"] = None
        self._save(state)
        return result

    def _submitted_sources(self, operation_id: str) -> list[str]:
        """The files this project asked the operation about, or none if unknown."""
        try:
            fd = os.open(self.submitted, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        except OSError:  # Absent, or a link: no record.
            return []
        with os.fdopen(fd, "rb") as stream:
            if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                return []
            raw = stream.read(_MAX_JOURNAL_BYTES + 1)
        try:
            record = json.loads(raw)
        except ValueError:
            return []
        if not isinstance(record, dict) or record.get("operation_id") != operation_id:
            return []
        sources = record.get("sources")
        if not isinstance(sources, list):
            return []
        return [source for source in sources if isinstance(source, str)]

    def recover(self) -> dict[str, Any]:
        """Replay the exact saved request even if local files have since changed."""
        with self._locked() as state:
            if state.get("pending") is None:
                return self._status(state)
            return self._replay(state)

    def _status(self, state: dict[str, Any]) -> dict[str, Any]:
        workspace = self._workspace(state)
        result = {
            "workspace": self.cloud.workspace(workspace),
            "local_revision": state.get("revision"),
            "recovery_required": state.get("pending") is not None,
        }
        if (self.directory / "apply-recovery.txt").exists():
            result["recovery_required"] = True
            result["apply_recovery"] = str(self.directory / "apply-recovery.txt")
        # Supplemental: status and recover must keep working without it, as with a
        # service from before usage was published.
        with suppress(LeanWarpCloudError, httpx.TransportError):
            result["history_usage"] = self.cloud.workspace_usage(workspace)
        if state.get("operation_id"):
            operation = self._previous_operation(state)
            if operation is None:
                result["operation_expired"] = True
            else:
                result["operation"] = operation
        return result

    def status(self) -> dict[str, Any]:
        with self._locked() as state:
            return self._status(state)

    def wait(self, *, timeout: float = 300) -> dict[str, Any]:
        with self._locked() as state:
            self._ready(state)
            operation = state.get("operation_id")
            if not isinstance(operation, str):
                raise SessionError("this project has not submitted an operation")
        # Do not hold the project lock while polling; another process may cancel.
        try:
            return self._checked_operation(state, self.cloud.wait(operation, timeout=timeout))
        except LeanWarpCloudError as error:
            if error.status_code == 404 and error.code == "not_found":
                raise SessionError(_OPERATION_EXPIRED) from error
            raise

    def cancel(self) -> dict[str, Any]:
        with self._locked() as state:
            self._ready(state)
            if not isinstance(state.get("operation_id"), str):
                raise SessionError("this project has not submitted an operation")
            try:
                return self._checked_operation(state, self.cloud.cancel(state["operation_id"]))
            except LeanWarpCloudError as error:
                if error.status_code == 404 and error.code == "not_found":
                    raise SessionError(_OPERATION_EXPIRED) from error
                raise

    def disconnect(self) -> dict[str, Any]:
        """Forget a stopped connection so this project can connect to another environment."""
        with self._locked() as state:
            self._ready(state)
            workspace_id = self._workspace(state)
            if state.get("operation_id"):
                operation = self._previous_operation(state)
                if operation is not None and operation.get("state") not in _TERMINAL_STATES:
                    raise SessionError(
                        "the previous operation is still running; run `leanwarp wait` or "
                        "`leanwarp cancel` first"
                    )
            workspace = self.cloud.workspace(workspace_id)
            if workspace.get("state") != "stopped":
                raise SessionError("run `leanwarp stop` before disconnecting this project")
            # Runtime state alone does not exclude queued or temporary work.
            # The server's guarded stop also checks work submitted elsewhere.
            stopped = self.cloud.stop(workspace_id)
            if stopped.get("workspace_id") != workspace_id or stopped.get("state") != "stopped":
                raise SessionError(
                    "LeanWarp did not confirm the stop; run `leanwarp status` and try again"
                )
            for key in ("workspace_id", "revision", "operation_id", "operation_revision"):
                state.pop(key, None)
            state["files"] = {}
            self._save(state)
            return {"status": "disconnected", "workspace_id": workspace_id}

    def apply(self) -> dict[str, Any]:
        """Write the latest suggest or sorry2lemma result into its file, then upload it.

        The edit applies only to the bytes the operation read: the operation must
        have completed at the revision this project last uploaded, and the file must
        be unchanged since then. Other changed files are uploaded with it, as by sync.
        If the upload fails after the file is written, running apply again uploads it.
        """
        with self._locked() as state:
            self._ready(state)
            _check_apply_recovery(self.directory)
            if not isinstance(state.get("operation_id"), str):
                raise SessionError("this project has not submitted an operation")
            operation = self._previous_operation(state)
            if operation is None:
                raise SessionError(_OPERATION_EXPIRED)
            kind = operation.get("kind")
            if kind not in EDITING_KINDS:
                raise SessionError("only a suggest or sorry2lemma result can be applied")
            if operation.get("state") != "completed":
                raise SessionError("the latest operation has not completed; run `leanwarp wait`")
            if operation.get("revision") != state["revision"]:
                raise SessionError(
                    "files were uploaded after this result was computed; run it again"
                )
            result = OperationOutcome(operation).result
            file = result.get("file") if result is not None else None
            if result is None or not isinstance(file, str) or file not in state["files"]:
                raise SessionError("the result names no file this project uploaded")
            # The result must edit the file this project asked about, not merely
            # one it uploaded.
            if file not in self._submitted_sources(operation["operation_id"]):
                raise SessionError(
                    f"this project did not ask the latest operation about {file}; "
                    "run the operation again"
                )
            if not OperationOutcome(operation).successful:
                raise SessionError("the latest result is not a verified edit")
            # Fail on a changed toolchain before the file is written, not after.
            self._environment(state)
            current = collect_lean_sources(self.root).get(file)
            digest = hashlib.sha256(current.encode()).hexdigest() if current is not None else None
            if digest == edited_sha256(str(kind), result):
                pass  # Written by an earlier apply whose upload did not finish.
            elif digest == state["files"][file] and current is not None:
                try:
                    edited = edited_source(str(kind), result, current)
                except EditError as error:
                    raise SessionError(str(error)) from None
                _replace_file(self.root / file, edited, expected=current, recovery=self.directory)
            else:
                raise SessionError(
                    f"{file} changed locally after the result was computed; run it again"
                )
            uploaded = self._sync(state)
            return {
                "status": "applied",
                "backup_directory": str(self.directory / "apply-backups"),
                "kind": kind,
                "file": file,
                "operation_id": operation["operation_id"],
                "workspace_id": uploaded.get("workspace_id"),
                "revision": uploaded.get("revision"),
            }

    def stop(self) -> dict[str, Any]:
        """Stop the worker, even while an earlier request awaits `recover`.

        Stopping changes no source or operation, so an unresolved request stays
        recorded for recovery instead of keeping compute running. Only a workspace
        whose creation is unresolved cannot be stopped, since its identity is unknown.
        """
        with self._locked() as state:
            if not state.get("workspace_id"):
                self._ready(state)
            result = self.cloud.stop(self._workspace(state))
            if state.get("pending") is not None:
                result = {**result, "recovery_required": True}
            return result

    def reconcile(self) -> dict[str, Any]:
        """Adopt the workspace's current revision after another client changed it.

        A sync is refused while the saved revision is older than the workspace's,
        which protects the other client's write. This deliberate step instead
        records the workspace's current files as the baseline, so the next sync
        uploads this project's files over them. It reports which paths that sync
        will upload or delete; nothing is uploaded here.
        """
        with self._locked() as state:
            self._ready(state)
            workspace = self._workspace(state)
            self._environment(state)
            revision, files = self._manifest(workspace)
            changes = self._changes(files)
            previous = state["revision"]
            state["revision"] = revision
            state["files"] = files
            self._save(state)
            return {
                "workspace_id": workspace,
                "revision": revision,
                "previous_revision": previous,
                **changes,
            }


def check_project(
    root: str | Path, catalog: list[dict[str, Any]], environment: str | None = None
) -> dict[str, Any]:
    """Whether a project runs on LeanWarp, before signing up: no key, writes or compute.

    ``catalog`` is the public environment list, from ``LeanWarpCloud(None).versions()``.
    """
    identity = project_identity(root)
    return {
        "environments": _environment_names(catalog),
        **_project_report(Path(root), identity, catalog),
        **_choice_report(identity, catalog, environment),
    }


def _environment_names(catalog: list[dict[str, Any]]) -> list[str]:
    return sorted({environment_name(build) for build in catalog})


def _project_report(
    root: Path, identity: ProjectIdentity, catalog: list[dict[str, Any]]
) -> dict[str, Any]:
    upload = plan_upload(root)
    return {
        "matching_bundles": [build for build in catalog if identity.matches(build)],
        "project": {
            "lean_toolchain": identity.toolchain,
            "lockfile": identity.manifest_sha256 is not None,
        },
        "upload": {
            "file_count": len(upload.sizes),
            "total_bytes": upload.total_bytes,
            "problems": list(upload.problems),
        },
    }


def _choice_report(
    identity: ProjectIdentity, catalog: list[dict[str, Any]], environment: str | None
) -> dict[str, Any]:
    try:
        selected = choose_environment(identity, catalog, environment)
    except ProjectError as error:
        return {"compatible": False, "message": str(error)}
    return {"compatible": True, "environment": selected.public()}


def _check_cap(workspace: Mapping[str, Any], max_spend_microusd: int | None) -> None:
    if max_spend_microusd is not None and (
        type(workspace.get("max_spend_microusd")) is not int
        or workspace["max_spend_microusd"] != max_spend_microusd
    ):
        raise SessionError(
            "this project's workspace has a different spending cap; "
            "change it in the account dashboard, or omit the cap to keep it"
        )


def _validate_journal(state: dict[str, Any]) -> None:
    def text(value: object) -> bool:
        return isinstance(value, str) and 0 < len(value) <= 256

    def revision(value: object) -> bool:
        return type(value) is int and 0 <= value <= 2**31 - 1

    def hashes(value: object) -> bool:
        return isinstance(value, dict) and all(
            text(k)
            and isinstance(v, str)
            and len(v) == 64
            and all(c in "0123456789abcdef" for c in v)
            for k, v in value.items()
        )

    valid = text(state.get("owner_id")) and hashes(state.get("files"))
    environment = state.get("environment")
    valid = (
        valid
        and isinstance(environment, list)
        and len(environment) == 2
        and all(map(text, environment))
    )
    if "workspace_id" in state:
        valid = valid and text(state["workspace_id"]) and revision(state.get("revision"))
    if "operation_id" in state:
        valid = valid and text(state["operation_id"]) and "workspace_id" in state
    if "operation_revision" in state:
        valid = valid and "operation_id" in state and revision(state["operation_revision"])
    pending = state.get("pending")
    if pending is not None:
        valid = valid and isinstance(pending, dict)
        if valid:
            valid = set(pending) == {"method", "arguments", "idempotency_key", "hashes"}
        if valid:
            method, args, key = pending["method"], pending["arguments"], pending["idempotency_key"]
            valid = (
                isinstance(method, str)
                and method in {"create_workspace", "sync_files", "submit"}
                and isinstance(args, dict)
                and isinstance(key, str)
                and len(key) == 32
                and all(c in "0123456789abcdef" for c in key)
            )
        if valid and method == "create_workspace":
            valid = (
                "bundle_id" in args
                and set(args).issubset(
                    {"bundle_id", "resource_profile", "max_resource_profile", "max_spend_microusd"}
                )
                and all(
                    text(args[k])
                    for k in ("bundle_id", "resource_profile", "max_resource_profile")
                    if k in args
                )
                and (
                    args.get("max_spend_microusd") is None
                    or (
                        type(args["max_spend_microusd"]) is int
                        and 0 <= args["max_spend_microusd"] <= 10**12
                    )
                )
                and "workspace_id" not in state
                and pending["hashes"] is None
            )
        elif valid:
            valid = (
                args.get("workspace_id") == state.get("workspace_id")
                and text(args.get("workspace_id"))
                and revision(args.get("expected_revision"))
            )
            if method == "sync_files":
                valid = (
                    valid
                    and set(args) == {"workspace_id", "expected_revision", "files", "delete_paths"}
                    and isinstance(args["files"], dict)
                    and all(text(k) and isinstance(v, str) for k, v in args["files"].items())
                    and isinstance(args["delete_paths"], list)
                    and all(map(text, args["delete_paths"]))
                    and hashes(pending["hashes"])
                )
            else:
                valid = (
                    valid
                    and set(args).issubset(
                        {
                            "workspace_id",
                            "kind",
                            "expected_revision",
                            "payload",
                            "resource_profile",
                            "timeout_seconds",
                        }
                    )
                    and isinstance(args.get("kind"), str)
                    and _OPERATION_KIND.fullmatch(args["kind"]) is not None
                    and isinstance(args.get("payload"), dict)
                    and pending["hashes"] is None
                    and (
                        "timeout_seconds" not in args
                        or (
                            type(args["timeout_seconds"]) is int
                            and 1 <= args["timeout_seconds"] <= 600
                        )
                    )
                )
    if not valid:
        raise SessionError(_JOURNAL_DAMAGED)


def _check_apply_recovery(directory: Path) -> None:
    marker = directory / "apply-recovery.txt"
    if marker.exists() or marker.is_symlink():
        raise SessionError(
            f"an interrupted or conflicting apply needs recovery; read {marker}, "
            "restore or reconcile the source, then remove that marker before retrying"
        )


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _replace_file(path: Path, text: str, *, expected: str, recovery: Path) -> None:
    """Preserve the displaced inode and publish without overwriting an editor save.

    A pathname briefly disappears between rename and exclusive link. A crash or
    conflict leaves recovery instructions, and prevents upload until reconciled.
    Backups remain even on success: an editor can still write through an old fd.
    """
    if path.is_symlink() or not path.is_file():
        raise SessionError(f"{path.name} is not a regular file")
    status = path.stat()
    if status.st_nlink > 1:
        raise SessionError(f"{path.name} has other hard links; apply the edit by hand")
    if not os.access(path, os.W_OK):
        raise SessionError(f"{path.name} is read-only")
    _check_apply_recovery(recovery)
    backups = recovery / "apply-backups"
    backups.mkdir(mode=0o700, exist_ok=True)
    if backups.is_symlink() or not backups.is_dir():
        raise SessionError("apply-backups must be a directory, not a symlink")
    backup = Path(tempfile.mkdtemp(prefix="apply-", dir=backups))
    original = backup / "original"
    descriptor, temporary = tempfile.mkstemp(prefix="proposed-", dir=backup)
    marker = recovery / "apply-recovery.txt"
    displaced = False
    rename_attempted = False
    complete = False
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(status.st_mode))
        if path.read_bytes() != expected.encode("utf-8"):
            raise SessionError(f"{path.name} changed while the edit was applied; run it again")
        # Persist instructions before moving any source. In particular, never
        # infer success from the patched hash after an interrupted replacement.
        with marker.open("x", encoding="utf-8") as stream:
            stream.write(
                f"Interrupted or conflicting LeanWarp apply.\nSource: {path}\n"
                f"Displaced source: {original}\nProposed edit: {temporary}\n\n"
                "Close editors first. Inspect the source and backup; reconcile or restore "
                "the desired bytes at the source path. Remove this marker only after "
                "reconciliation, then rerun the operation if the source changed. "
                "If the source was restored as a hard link, save it as a new file first. "
                "Keep the backup until all editors with the old file open are closed.\n"
            )
            stream.flush()
            os.fsync(stream.fileno())
        os.link(marker, backup / "RECOVERY.txt")
        _fsync_directory(backup)
        _fsync_directory(backups)
        _fsync_directory(recovery)
        # Rename captures whichever inode currently occupies the path, including
        # an atomic editor save after the comparison. Cross-device moves fail
        # here without touching the source; copying would reopen the loss race.
        rename_attempted = True
        os.rename(path, original)
        displaced = True
        _fsync_directory(backup)
        _fsync_directory(path.parent)
        moved = original.lstat()
        if not stat.S_ISREG(moved.st_mode) or moved.st_nlink != 1:
            raise SessionError(f"{path.name} changed while applying; inspect {marker}")
        if original.read_bytes() != expected.encode("utf-8"):
            raise SessionError(f"{path.name} changed while applying; inspect {marker}")
        # Unlike replace(), link() never destroys a concurrently recreated path.
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise SessionError(f"{path.name} changed while applying; inspect {marker}") from None
        os.unlink(temporary)
        _fsync_directory(path.parent)
        _fsync_directory(backup)
        if original.read_bytes() != expected.encode("utf-8"):
            raise SessionError(f"{path.name} changed while applying; inspect {marker}")
        complete = True
    finally:
        if rename_attempted and not displaced:
            # A signal can interrupt after rename succeeds but before Python
            # records success. Inspect the unique backup, not just the flag;
            # retain recovery instructions whenever that inspection is uncertain.
            try:
                original.lstat()
            except FileNotFoundError:
                pass
            except OSError:
                displaced = True
            else:
                displaced = True
        if displaced and not complete:
            # Restore only an absent pathname. A newer editor save always stays;
            # both versions remain available in the durable backup either way.
            with suppress(OSError):
                os.link(original, path, follow_symlinks=False)
                _fsync_directory(path.parent)
        if not displaced or complete:
            marker.unlink(missing_ok=True)
            _fsync_directory(recovery)
            with suppress(FileNotFoundError):
                os.unlink(temporary)
        if not displaced:
            (backup / "RECOVERY.txt").unlink(missing_ok=True)
            backup.rmdir()
