"""droidrun's official mobilerun-mcp tool surface (Mobilerun Cloud platform), ported to Python.

Port of the tool layer and SDK backend of https://github.com/droidrun/mobilerun-mcp
(Apache-2.0, Copyright droidrun): same tool names, parameters, operation dispatch and validation,
calling the Mobilerun Cloud API through the Python ``mobilerun_sdk`` (MOBILERUN_CLOUD_API_KEY).

Device tools (``deviceId``) also serve local devices: a ``deviceId`` that is not a Mobilerun
Cloud id (an adb serial, ``ios``, a Portal URL...) runs the same operation on that device through
this server's session. Operations that only exist on the platform (reset, eSIM, proxies, rename,
create/terminate) report ``unsupported`` for local devices.

The task tools (list_devices, run_task, get_task, list_tasks, stop_task, get_task_media,
send_task_message) are registered elsewhere; their Cloud half is the ``cloud_*`` helpers here.
"""

from __future__ import annotations

import asyncio
import base64
import json
import posixpath
import time
from collections.abc import Awaitable, Callable
from typing import Annotated, Any, Literal

from fastmcp import FastMCP
from pydantic import Field

from ..errors import McpToolError, fail
from ..session import DeviceSession, Runtime
from ..shell import q
from ..targets import CLOUD, resolve_target

# ---- client ---------------------------------------------------------------------------------


def _default_factory(api_key: str) -> Any:
    from mobilerun_sdk import AsyncMobilerun

    return AsyncMobilerun(api_key=api_key)


CLIENT_FACTORY: Callable[[str], Any] = _default_factory
_clients: dict[str, Any] = {}


def client(rt: Runtime) -> Any:
    """Cached ``AsyncMobilerun`` for MOBILERUN_CLOUD_API_KEY."""
    key = rt.config.cloud_api_key
    if not key:
        fail(
            "unsupported",
            "this operation needs Mobilerun Cloud",
            "set MOBILERUN_CLOUD_API_KEY (a dr_sk_... key from cloud.mobilerun.ai)",
        )
    if key not in _clients:
        _clients[key] = CLIENT_FACTORY(key)
    return _clients[key]


def dump(value: Any) -> Any:
    """SDK models -> JSON-able data (camelCase wire names, as the TS server returns)."""
    if hasattr(value, "to_dict"):
        return value.to_dict(mode="json", warnings=False)
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, list):
        return [dump(v) for v in value]
    if isinstance(value, dict):
        return {k: dump(v) for k, v in value.items()}
    return value


def _code(status: int | None) -> str:
    if status in (400, 422):
        return "invalid_input"
    if status in (401, 403):
        return "forbidden"
    if status == 404:
        return "not_found"
    if status == 429:
        return "rate_limited"
    return "upstream_error"


async def call(awaitable: Awaitable[Any]) -> Any:
    """Await an SDK call; map SDK/API errors to ``[code] message`` tool errors."""
    from mobilerun_sdk import APIError, APIStatusError

    try:
        return dump(await awaitable)
    except APIStatusError as exc:
        fail(_code(exc.status_code), str(exc))
    except APIError as exc:
        fail("upstream_error", str(exc))


def kw(**values: Any) -> dict[str, Any]:
    """Drop unset (None) values, like ``undefined`` fields in the TS SDK calls."""
    return {k: v for k, v in values.items() if v is not None}


def require(value: Any, name: str, operation: str, prefix: str = "operation") -> Any:
    if value is None:
        fail("invalid_argument", f"{prefix}={operation} requires {name}")
    return value


def disallowed(operation: str, allowed: tuple[str, ...], given: dict[str, Any]) -> None:
    extra = [k for k, v in given.items() if v is not None and k not in allowed]
    if extra:
        fail(
            "invalid_argument",
            f"field {', '.join(extra)} is not valid for operation={operation}; "
            f"allowed fields: {', '.join(allowed) or '(none)'}",
        )


def is_cloud(device_id: str) -> bool:
    return resolve_target(device_id).kind == CLOUD


def cloud_id(device_id: str) -> str:
    return resolve_target(device_id).id


def local_only(operation: str) -> None:
    fail(
        "unsupported",
        f"{operation} needs a Mobilerun Cloud device",
        "pass a Mobilerun Cloud deviceId (cloud:<uuid>)",
    )


def display(display_id: int | None) -> dict[str, Any]:
    return {"x_device_display_id": display_id} if display_id is not None else {}


# ---- get_device_ui_state compaction (tools/ui-state.ts) -------------------------------------

MAX_NODES = 200
MAX_BYTES = 28_000
TEXT_MAX = 120


def _clip(value: Any, limit: int = TEXT_MAX) -> str | None:
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    return text[: limit - 1] + "…" if len(text) > limit else text


def _short_id(resource_id: str | None) -> str | None:
    if not resource_id:
        return None
    return _clip(resource_id.rsplit("/", 1)[-1], 60)


def _flags(node: dict) -> str | None:
    flags = []
    if node.get("isClickable"):
        flags.append("clickable")
    if node.get("isLongClickable"):
        flags.append("longClickable")
    if node.get("isScrollable"):
        flags.append("scrollable")
    if node.get("isCheckable"):
        flags.append("checked" if node.get("isChecked") else "checkable")
    if node.get("isSelected"):
        flags.append("selected")
    if node.get("isFocused"):
        flags.append("focused")
    if node.get("isPassword"):
        flags.append("password")
    if node.get("isEnabled") is False:
        flags.append("disabled")
    if node.get("isVisibleToUser") is False:
        flags.append("hidden")
    return ",".join(flags) or None


def _useful(node: dict) -> bool:
    return bool(
        _clip(node.get("text"))
        or _clip(node.get("contentDescription"))
        or node.get("isClickable")
        or node.get("isLongClickable")
        or node.get("isScrollable")
        or node.get("isCheckable")
    )


def _matches(node: dict, flt: dict) -> bool:
    if flt.get("resourceId"):
        raw = node.get("resourceId") or ""
        if raw != flt["resourceId"] and _short_id(raw) != flt["resourceId"]:
            return False
    if flt.get("contains"):
        hay = "\n".join(
            str(node.get(k) or "") for k in ("text", "contentDescription", "resourceId")
        ).lower()
        if flt["contains"].lower() not in hay:
            return False
    return True


def _compact(node: dict) -> dict:
    b = node.get("boundsInScreen") or {}
    left, top = b.get("left") or 0, b.get("top") or 0
    right = b.get("right") if b.get("right") is not None else left
    bottom = b.get("bottom") if b.get("bottom") is not None else top
    out: dict[str, Any] = {"xy": [round((left + right) / 2), round((top + bottom) / 2)]}
    text = "•••" if node.get("isPassword") else _clip(node.get("text"))
    for key, value in (
        ("t", text),
        ("d", _clip(node.get("contentDescription"))),
        ("id", _short_id(node.get("resourceId"))),
        ("c", (node.get("className") or "").rsplit(".", 1)[-1] or None),
        ("f", _flags(node)),
    ):
        if value:
            out[key] = value
    return {k: out[k] for k in ("t", "d", "id", "c", "xy", "f") if k in out}


def compact_ui_state(device_id: str, raw: dict, flt: dict, offset: int | None = None) -> dict:
    phone = raw.get("phone_state") or {}
    active = (
        flt if (flt.get("contains") or flt.get("resourceId") or flt.get("includeAll")) else None
    )
    start = max(0, int(offset or 0))
    root = raw.get("a11y_tree")
    root = root if isinstance(root, dict) else None
    dead = not root or not isinstance(root.get("children"), list) or not root["children"]
    nodes: list[dict] = []
    total = 0
    queue = [root] if root else []
    head = 0
    while head < len(queue):
        node = queue[head]
        head += 1
        if _matches(node, flt) and (flt.get("includeAll") or _useful(node)):
            if total >= start and len(nodes) < MAX_NODES:
                nodes.append(_compact(node))
            total += 1
        if isinstance(node.get("children"), list):
            queue.extend(c for c in node["children"] if isinstance(c, dict))

    def build(byte_truncated: bool) -> dict:
        next_offset = start + len(nodes)
        has_more = next_offset < total
        out = {
            "deviceId": device_id,
            "app": phone.get("currentApp"),
            "activity": phone.get("activityName"),
            "keyboardVisible": bool(phone.get("keyboardVisible")),
            "editing": bool(phone.get("isEditable")),
            "focused": phone.get("focusedElement"),
            "screen": (raw.get("device_context") or {}).get("screen_bounds"),
            "nodeCount": len(nodes),
            "total": total,
            "offset": start,
            "deadTree": dead,
            "truncated": has_more,
            "byteTruncated": byte_truncated,
            "hasMore": has_more,
        }
        if has_more:
            out["nextOffset"] = next_offset
        if active:
            out["filter"] = {k: v for k, v in active.items() if v is not None}
        out["nodes"] = nodes
        return {k: v for k, v in out.items() if v is not None}

    out = build(False)
    while len(json.dumps(out, ensure_ascii=False).encode()) > MAX_BYTES and len(nodes) > 1:
        nodes = nodes[: -(-len(nodes) * 9 // 10) - 1]
        out = build(True)
    return out


# ---- task helpers (tools/tasks.ts), called by the task tool module ---------------------------

DEVICE_STATES = (
    "creating",
    "assigned",
    "ready",
    "rebooting",
    "migrating",
    "resetting",
    "terminated",
    "maintenance",
    "unknown",
)
DEFAULT_LIST_STATES = [s for s in DEVICE_STATES if s != "terminated"]
MAX_TRAJECTORY_EVENTS = 50
SUMMARY_DROP = (
    "trajectory",
    "agentId",
    "accessibility",
    "reasoning",
    "subagentModel",
    "temperature",
    "continueOnFailure",
    "executionTimeout",
    "memoryNamespace",
    "tmpDevice",
    "heartbeatAt",
    "vpnCountry",
)
GLOBAL_ONLY_ORDER_BY = {"finishedAt", "status"}
DEVICE_ONLY_ORDER_BY = {"updatedAt", "assignedAt"}


async def cloud_list_devices(
    rt: Runtime,
    state: list[str] | None = None,
    type: str | None = None,
    name: str | None = None,
    country: str | None = None,
    page: int | None = None,
    pageSize: int | None = None,
) -> Any:
    return await call(
        client(rt).devices.list(
            **kw(
                state=list(state) if state else DEFAULT_LIST_STATES,
                type=type,
                name=name,
                country=country,
                page=page,
                page_size=pageSize,
            )
        )
    )


async def cloud_run_task(
    rt: Runtime,
    deviceId: str,
    task: str,
    llmModel: str | None = None,
    maxSteps: int | None = None,
    outputSchema: dict | None = None,
    stealth: bool | None = None,
    vision: bool | None = None,
    apps: list[str] | None = None,
    credentials: list[dict] | None = None,
    files: list[str] | None = None,
) -> Any:
    if not task:
        fail("invalid_argument", "task must not be empty")
    return await call(
        client(rt).tasks.run(
            **kw(
                device_id=cloud_id(deviceId),
                task=task,
                llm_model=llmModel,
                max_steps=maxSteps,
                output_schema=outputSchema,
                stealth=stealth,
                vision=vision,
                apps=apps,
                credentials=credentials,
                files=files,
            )
        )
    )


def compact_trajectory(events: list, offset: int | None = None, limit: int | None = None) -> dict:
    start = max(0, int(offset or 0))
    capped = min(max(1, int(limit or MAX_TRAJECTORY_EVENTS)), MAX_TRAJECTORY_EVENTS)
    page = events[start : start + capped]
    next_offset = start + len(page)
    out: dict[str, Any] = {
        "total": len(events),
        "offset": start,
        "eventCount": len(page),
        "hasMore": next_offset < len(events),
    }
    if out["hasMore"]:
        out["nextOffset"] = next_offset
    out["events"] = page
    return out


async def cloud_get_task(
    rt: Runtime,
    task_id: str,
    view: str = "summary",
    offset: int | None = None,
    limit: int | None = None,
) -> Any:
    tasks = client(rt).tasks
    if view == "status":
        return await call(tasks.get_status(task_id))
    if view == "trajectory":
        raw = await call(tasks.get_trajectory(task_id))
        events = (raw or {}).get("trajectory") or []
        return compact_trajectory(events, offset, limit)
    if view != "summary":
        fail("invalid_argument", "view must be summary, status or trajectory")
    raw = await call(tasks.retrieve(task_id))
    task = (raw or {}).get("task") or {}
    return {k: v for k, v in task.items() if k not in SUMMARY_DROP}


async def cloud_list_tasks(
    rt: Runtime,
    deviceId: str | None = None,
    orderBy: str | None = None,
    orderByDirection: str | None = None,
    page: int | None = None,
    pageSize: int | None = None,
    query: str | None = None,
    status: str | None = None,
) -> Any:
    if deviceId:
        if query is not None:
            fail(
                "invalid_argument",
                "list_tasks: `query` is only valid without `deviceId` "
                "(device-scoped listing has no search).",
            )
        if status is not None:
            fail(
                "invalid_argument",
                "list_tasks: `status` is only valid without `deviceId` "
                "(device-scoped listing has no status filter).",
            )
        if orderBy in GLOBAL_ONLY_ORDER_BY:
            fail(
                "invalid_argument",
                f'list_tasks: orderBy="{orderBy}" is only valid without '
                "`deviceId`; device-scoped orderBy is one of id, createdAt, updatedAt, assignedAt.",
            )
        result = await call(
            client(rt).devices.tasks.list(
                cloud_id(deviceId),
                **kw(
                    order_by=orderBy,
                    order_by_direction=orderByDirection,
                    page=page,
                    page_size=pageSize,
                ),
            )
        )
        items = result.get("items")
        return {
            "items": None
            if items is None
            else [{k: i.get(k) for k in ("taskId", "createdAt", "updatedAt")} for i in items],
            "pagination": result.get("pagination"),
            "deviceScoped": True,
        }
    if orderBy in DEVICE_ONLY_ORDER_BY:
        fail(
            "invalid_argument",
            f'list_tasks: orderBy="{orderBy}" is only valid with `deviceId` '
            "set; global orderBy is one of id, createdAt, finishedAt, status.",
        )
    result = await call(
        client(rt).tasks.list(
            **kw(
                order_by=orderBy,
                order_by_direction=orderByDirection,
                page=page,
                page_size=pageSize,
                query=query,
                status=status,
            )
        )
    )
    return {
        "items": result.get("items"),
        "pagination": result.get("pagination"),
        "deviceScoped": False,
    }


async def cloud_stop_task(rt: Runtime, task_id: str) -> Any:
    return await call(client(rt).tasks.stop(task_id))


async def cloud_send_task_message(rt: Runtime, task_id: str, message: str) -> Any:
    if not message:
        fail("invalid_argument", "message must not be empty")
    return await call(client(rt).tasks.send_message(task_id, message=message))


async def cloud_get_task_media(
    rt: Runtime, task_id: str, kind: str = "screenshot", index: int | None = None
) -> Any:
    tasks = client(rt).tasks
    if kind == "screenshot":
        if index is None:
            return await call(tasks.screenshots.list(task_id))
        return await call(tasks.screenshots.retrieve(index, task_id=task_id))
    if kind != "ui_state":
        fail("invalid_argument", "kind must be screenshot or ui_state")
    if index is None:
        return await call(tasks.ui_states.list(task_id))
    return await call(tasks.ui_states.retrieve(index, task_id=task_id))


# ---- local device helpers ---------------------------------------------------------------------

READY_TIMEOUT = 120.0
MAX_INLINE_FILE_BYTES = 256 * 1024
MAX_INLINE_BASE64_CHARS = -(-MAX_INLINE_FILE_BYTES * 4 // 3)
GLOBAL_TO_BUTTON = {1: "back", 2: "home", 3: "recents"}


async def _session(rt: Runtime, device_id: str) -> DeviceSession:
    session = rt.session(device_id)
    await session.ensure_connected()
    return session


async def _local_apps(session: DeviceSession, system: bool, protected: bool) -> list[dict]:
    if session.has_adb:
        return [
            {
                "package_name": a.package,
                "label": a.label,
                "version_name": a.version,
                "is_system_app": a.system,
            }
            for a in await session.apps(refresh=True)
            if system or not a.system
        ]
    return await session.core.call(
        "list_apps", include_system_apps=system, include_protected_apps=protected
    )


async def _wait_ready(session: DeviceSession) -> None:
    deadline = time.monotonic() + READY_TIMEOUT
    while True:
        session._connected = False  # force a fresh probe
        try:
            await session.ensure_connected()
            return
        except McpToolError:
            if time.monotonic() > deadline:
                raise
            await asyncio.sleep(3)


async def _local_device(rt: Runtime, device_id: str) -> dict:
    session = rt.session(device_id)
    target = session.target
    info: dict[str, Any] = {"id": device_id, "kind": target.kind, "platform": target.platform}
    try:
        await session.ensure_connected()
        info["state"] = "ready"
        info["capabilities"] = await session.core.capabilities()
    except McpToolError as exc:
        info["state"] = "unreachable"
        info["error"] = str(exc)
    if info["state"] == "ready" and session.has_adb:
        props = await session.shell(
            "getprop ro.product.model; getprop ro.build.version.release; "
            "getprop ro.product.cpu.abi; getprop persist.sys.locale; getprop persist.sys.timezone",
            check=False,
        )
        keys = ("model", "androidVersion", "abi", "locale", "timezone")
        info.update(
            {k: v.strip() for k, v in zip(keys, props.splitlines(), strict=False) if v.strip()}
        )
    return info


async def _portal_json(session: DeviceSession, name: str, **payload: Any) -> Any:
    session.require_adb(name)
    result = await session.portal.action(name, **payload)
    try:
        return json.loads(result)
    except (TypeError, ValueError):
        return result


# ---- registration -----------------------------------------------------------------------------

FIELD_TYPES = Literal[
    "email",
    "username",
    "password",
    "api_token",
    "phone_number",
    "two_factor_secret",
    "backup_codes",
]


def register(mcp: FastMCP, rt: Runtime) -> None:  # noqa: C901 - one flat tool table
    # ---- devices (tools/devices.ts) ----------------------------------------------------------
    @mcp.tool(tags={"read"})
    async def get_device(deviceId: str) -> Any:
        """Fetch one device by id (a Mobilerun Cloud id, or a local device: adb serial, ios...)."""
        if is_cloud(deviceId):
            return await call(client(rt).devices.retrieve(cloud_id(deviceId)))
        return await _local_device(rt, deviceId)

    @mcp.tool(tags={"read"})
    async def get_device_screenshot(deviceId: str) -> Any:
        """Capture a device screenshot and return the raw result ({deviceId, screenshot}); for
        cloud devices the SDK result (base64 payload or signed URL), for local ones base64 PNG."""
        if is_cloud(deviceId):
            shot = await call(client(rt).devices.state.screenshot(cloud_id(deviceId)))
            return {"deviceId": deviceId, "screenshot": shot}
        session = await _session(rt, deviceId)
        png = await session.screenshot()
        return {"deviceId": deviceId, "screenshot": base64.b64encode(png).decode("ascii")}

    @mcp.tool(tags={"read"})
    async def get_device_ui_state(
        deviceId: str,
        contains: str | None = None,
        resourceId: str | None = None,
        includeAll: bool | None = None,
        offset: Annotated[int | None, Field(ge=0)] = None,
    ) -> Any:
        """Read the on-screen UI as structured text: current app/activity, keyboard state, and a
        compact list of labeled/actionable elements (text, resourceId, className, tap center
        `xy`, flags). Returns one page of nodes plus `total`, `nodeCount`, `hasMore`; page with
        `offset` = the returned `nextOffset`. contains: case-insensitive substring over text,
        contentDescription and resourceId. resourceId: full or short id. includeAll: keep layout
        containers too."""
        if is_cloud(deviceId):
            raw = await call(client(rt).devices.state.ui(cloud_id(deviceId), filter=True))
        else:
            raw = await (await _session(rt, deviceId)).raw_state()
        flt = {"contains": contains, "resourceId": resourceId, "includeAll": includeAll}
        return compact_ui_state(deviceId, raw or {}, flt, offset)

    @mcp.tool(tags={"read"})
    async def list_apps_on_device(
        deviceId: str,
        includeSystemApps: bool | None = None,
        includeProtectedApps: bool | None = None,
    ) -> Any:
        """List apps installed on a device (package_name, label, version_name, version_code,
        is_system_app). Excludes OEM/system bundles by default."""
        if is_cloud(deviceId):
            return await call(
                client(rt).devices.apps.list(
                    cloud_id(deviceId),
                    **kw(
                        include_system_apps=includeSystemApps,
                        include_protected_apps=includeProtectedApps,
                    ),
                )
            )
        session = await _session(rt, deviceId)
        return await _local_apps(session, bool(includeSystemApps), bool(includeProtectedApps))

    @mcp.tool(tags={"write"})
    async def create_device(
        deviceType: Literal[
            "dedicated_physical_device", "dedicated_premium_device", "dedicated_ios_device"
        ]
        | None = None,
        name: Annotated[str | None, Field(max_length=64)] = None,
        country: Annotated[str | None, Field(pattern=r"^[A-Za-z]{2}$")] = None,
    ) -> Any:
        """Provision a new Mobilerun Cloud device (billing is enforced by the API). Provisioning
        takes a while: poll get_device with the returned id until state is "ready"."""
        return await call(
            client(rt).devices.create(
                **kw(
                    device_type=deviceType,
                    name=name,
                    query_country=country.upper() if country else None,
                )
            )
        )

    @mcp.tool(tags={"write"})
    async def terminate_device(deviceId: str) -> Any:
        """Terminate a Mobilerun Cloud device. Irreversible: confirm with the user first."""
        if not is_cloud(deviceId):
            local_only("terminate_device")
        await call(client(rt).devices.terminate(cloud_id(deviceId)))
        return {"status": "termination_requested", "deviceId": deviceId}

    # ---- manage_device ------------------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def manage_device(
        operation: Literal["reboot", "reset", "rename", "wait_ready", "get_capabilities", "count"],
        deviceId: str | None = None,
        name: Annotated[str | None, Field(max_length=64)] = None,
    ) -> Any:
        """Device lifecycle operations. Operations: reboot, reset (factory reset, destructive;
        cloud only), rename (needs name; cloud only), wait_ready (blocks until ready),
        get_capabilities (cloud: fingerprint of carrier/display/identifiers/model; local:
        backend capabilities), count (claimed cloud-device counts by state, no deviceId)."""
        disallowed(operation, ("name",) if operation == "rename" else (), {"name": name})
        if operation == "count":
            return await call(client(rt).devices.count())
        device = require(deviceId, "deviceId", operation)
        if is_cloud(device):
            devices = client(rt).devices
            did = cloud_id(device)
            if operation == "reboot":
                await call(devices.reboot(did))
                return {"status": "reboot_requested", "deviceId": device}
            if operation == "reset":
                await call(devices.reset(did))
                return {"status": "reset_requested", "deviceId": device}
            if operation == "rename":
                await call(devices.set_name(did, name=require(name, "name", operation)))
                return await call(devices.retrieve(did))
            if operation == "wait_ready":
                await call(devices.wait_ready(did))
                return await call(devices.retrieve(did))
            return await call(devices.fingerprint(did))
        if operation in ("reset", "rename"):
            local_only(operation)
        session = rt.session(device)
        if operation == "reboot":
            session.require_adb("reboot")
            await session.shell("reboot", check=False)
            session._connected = False
            return {"status": "reboot_requested", "deviceId": device}
        if operation == "wait_ready":
            await _wait_ready(session)
            return await _local_device(rt, device)
        await session.ensure_connected()
        return await session.core.capabilities()

    # ---- device_action ------------------------------------------------------------------------
    action_fields = {
        "tap": ("x", "y", "stealth"),
        "swipe": ("startX", "startY", "endX", "endY", "duration", "stealth"),
        "keyboard_write": ("text", "clear", "errorRate", "stealth", "wpm"),
        "keyboard_key": ("key",),
        "keyboard_clear": (),
        "global_action": ("action",),
    }

    @mcp.tool(tags={"write"})
    async def device_action(
        operation: Literal[
            "tap", "swipe", "keyboard_write", "keyboard_key", "keyboard_clear", "global_action"
        ],
        deviceId: str,
        displayId: int | None = None,
        x: float | None = None,
        y: float | None = None,
        startX: float | None = None,
        startY: float | None = None,
        endX: float | None = None,
        endY: float | None = None,
        duration: Annotated[int | None, Field(gt=0)] = None,
        stealth: bool | None = None,
        text: str | None = None,
        clear: bool | None = None,
        errorRate: float | None = None,
        wpm: float | None = None,
        key: int | None = None,
        action: int | None = None,
    ) -> Any:
        """Low-level device input. Operations: tap (x, y), swipe (startX, startY, endX, endY,
        duration ms), keyboard_write (text, clear?, errorRate?, wpm?, stealth?), keyboard_key
        (key: Android keycode), keyboard_clear, global_action (action: Android global-action
        code, e.g. 1 back, 2 home, 3 recents). stealth requests human-like timing. displayId
        targets one display on multi-display cloud devices."""
        given = {
            "x": x,
            "y": y,
            "startX": startX,
            "startY": startY,
            "endX": endX,
            "endY": endY,
            "duration": duration,
            "stealth": stealth,
            "text": text,
            "clear": clear,
            "errorRate": errorRate,
            "wpm": wpm,
            "key": key,
            "action": action,
        }
        disallowed(operation, action_fields[operation], given)
        if is_cloud(deviceId):
            await _cloud_action(operation, cloud_id(deviceId), displayId, given)
        else:
            await _local_action(operation, await _session(rt, deviceId), given)
        return {"status": "ok", "operation": operation, "deviceId": deviceId}

    async def _cloud_action(operation: str, did: str, display_id: int | None, g: dict) -> None:
        dev = client(rt).devices
        extra = display(display_id)
        if operation == "tap":
            await call(
                dev.actions.tap(
                    did,
                    x=int(require(g["x"], "x", operation)),
                    y=int(require(g["y"], "y", operation)),
                    **kw(stealth=g["stealth"]),
                    **extra,
                )
            )
        elif operation == "swipe":
            await call(
                dev.actions.swipe(
                    did,
                    start_x=int(require(g["startX"], "startX", operation)),
                    start_y=int(require(g["startY"], "startY", operation)),
                    end_x=int(require(g["endX"], "endX", operation)),
                    end_y=int(require(g["endY"], "endY", operation)),
                    duration=require(g["duration"], "duration", operation),
                    **kw(stealth=g["stealth"]),
                    **extra,
                )
            )
        elif operation == "keyboard_write":
            await call(
                dev.keyboard.write(
                    did,
                    text=require(g["text"], "text", operation),
                    **kw(
                        clear=g["clear"],
                        error_rate=g["errorRate"],
                        wpm=int(g["wpm"]) if g["wpm"] is not None else None,
                        stealth=g["stealth"],
                    ),
                    **extra,
                )
            )
        elif operation == "keyboard_key":
            await call(dev.keyboard.key(did, key=require(g["key"], "key", operation), **extra))
        elif operation == "keyboard_clear":
            await call(dev.keyboard.clear(did, **extra))
        else:
            await call(
                dev.actions.global_(did, action=require(g["action"], "action", operation), **extra)
            )

    async def _local_action(operation: str, session: DeviceSession, g: dict) -> None:
        if operation == "tap":
            x, y = int(require(g["x"], "x", operation)), int(require(g["y"], "y", operation))
            if g["stealth"]:
                await session.core.call("tap", x, y, stealth=True)
            else:
                await session.tap_xy(x, y)
        elif operation == "swipe":
            await session.swipe_xy(
                int(require(g["startX"], "startX", operation)),
                int(require(g["startY"], "startY", operation)),
                int(require(g["endX"], "endX", operation)),
                int(require(g["endY"], "endY", operation)),
                int(require(g["duration"], "duration", operation)),
            )
        elif operation == "keyboard_write":
            text = require(g["text"], "text", operation)
            if g["stealth"]:
                wpm = int(g["wpm"]) if g["wpm"] else None
                await session.core.call("type", text, clear=bool(g["clear"]), wpm=wpm, stealth=True)
            else:
                await session.input_text(text, bool(g["clear"]))
        elif operation == "keyboard_key":
            code = int(require(g["key"], "key", operation))
            if session.has_adb:
                await session.shell(f"input keyevent {code}")
            else:
                await session.core.call("key", code)
        elif operation == "keyboard_clear":
            await session.core.call("clear_input")
        else:
            code = int(require(g["action"], "action", operation))
            if (
                session.has_adb
                and session.portal is not None
                and session.portal.transport == "http"
            ):
                await session.portal.action("global", action=code)
            elif code in GLOBAL_TO_BUTTON:
                await session.press(GLOBAL_TO_BUTTON[code])
            else:
                fail(
                    "unsupported", f"global action {code} needs the Portal HTTP API on this device"
                )

    # ---- manage_device_apps -------------------------------------------------------------------
    app_fields = {
        "install": ("packageName", "bundleId"),
        "delete": ("packageName",),
        "start": ("packageName", "activity"),
        "stop": ("packageName",),
        "list_packages": ("includeSystemPackages", "includeProtectedPackages"),
    }

    @mcp.tool(tags={"write"})
    async def manage_device_apps(
        operation: Literal["install", "delete", "start", "stop", "list_packages"],
        deviceId: str,
        packageName: str | None = None,
        bundleId: str | None = None,
        activity: str | None = None,
        includeSystemPackages: bool | None = None,
        includeProtectedPackages: bool | None = None,
    ) -> Any:
        """Mutate apps on a device. Operations: install (packageName and/or bundleId; on a local
        device packageName may be a host path to an .apk), delete (packageName), start
        (packageName, activity?), stop (packageName), list_packages (installed package names,
        includeSystemPackages?, includeProtectedPackages?)."""
        given = {
            "packageName": packageName,
            "bundleId": bundleId,
            "activity": activity,
            "includeSystemPackages": includeSystemPackages,
            "includeProtectedPackages": includeProtectedPackages,
        }
        disallowed(operation, app_fields[operation], given)
        if operation == "install" and not packageName and not bundleId:
            fail("invalid_argument", "operation=install requires packageName and/or bundleId")
        if is_cloud(deviceId):
            apps = client(rt).devices.apps
            did = cloud_id(deviceId)
            if operation == "install":
                await call(apps.install(did, **kw(package_name=packageName, bundle_id=bundleId)))
                return {
                    "status": "install_requested",
                    "deviceId": deviceId,
                    **kw(packageName=packageName, bundleId=bundleId),
                }
            if operation == "list_packages":
                return await call(
                    client(rt).devices.packages.list(
                        did,
                        **kw(
                            include_system_packages=includeSystemPackages,
                            include_protected_packages=includeProtectedPackages,
                        ),
                    )
                )
            pkg = require(packageName, "packageName", operation)
            if operation == "delete":
                await call(apps.delete(pkg, device_id=did))
            elif operation == "start":
                await call(apps.start(pkg, device_id=did, **kw(activity=activity)))
            else:
                await call(apps.stop(pkg, device_id=did))
            return {
                "status": "ok",
                "operation": operation,
                "deviceId": deviceId,
                "packageName": pkg,
            }
        session = await _session(rt, deviceId)
        if operation == "install":
            source = packageName or bundleId
            if not source.lower().endswith((".apk", ".ipa", ".apks", ".zip")):
                fail(
                    "unsupported",
                    "store installs by package name need a Mobilerun Cloud device",
                    "on a local device pass packageName as a host path to an .apk",
                )
            await session.core.call("install_app", source)
            return {
                "status": "install_requested",
                "deviceId": deviceId,
                **kw(packageName=packageName, bundleId=bundleId),
            }
        if operation == "list_packages":
            apps_ = await _local_apps(
                session, bool(includeSystemPackages), bool(includeProtectedPackages)
            )
            return [a.get("package_name") or a.get("packageName") for a in apps_]
        pkg = require(packageName, "packageName", operation)
        if operation == "delete":
            await session.core.call("uninstall_app", pkg)
        elif operation == "start":
            await session.start_app(pkg, activity)
        else:
            await session.core.call("stop_app", pkg)
        return {"status": "ok", "operation": operation, "deviceId": deviceId, "packageName": pkg}

    # ---- manage_device_files ------------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def manage_device_files(
        operation: Literal["list", "upload", "download", "delete"],
        deviceId: str,
        path: Annotated[str, Field(min_length=1)],
        contentBase64: Annotated[str | None, Field(max_length=MAX_INLINE_BASE64_CHARS)] = None,
        fileName: str | None = None,
        contentType: str | None = None,
    ) -> Any:
        """Device filesystem access. Operations: list (entries at `path`), upload (write
        `contentBase64` to `path`; decoded payload capped at 256KB), download (read `path`,
        base64; capped the same way), delete (`path`)."""
        allowed = ("contentBase64", "fileName", "contentType") if operation == "upload" else ()
        disallowed(
            operation,
            allowed,
            {"contentBase64": contentBase64, "fileName": fileName, "contentType": contentType},
        )
        cloud = is_cloud(deviceId)
        if operation == "upload":
            data = require(contentBase64, "contentBase64", operation)
            if len(data) > MAX_INLINE_BASE64_CHARS:
                fail(
                    "invalid_argument",
                    "upload payload exceeds the 256KB inline limit — use a smaller file.",
                )
        if cloud:
            files = client(rt).devices.files
            did = cloud_id(deviceId)
            if operation == "list":
                return await call(files.list(did, path=path))
            if operation == "upload":
                raw = base64.b64decode(data)
                name = fileName or posixpath.basename(path) or "upload"
                upload = (name, raw, contentType) if contentType else (name, raw)
                await call(files.upload(did, path=path, file=upload))
                return {"status": "uploaded", "deviceId": deviceId, "path": path}
            if operation == "download":
                content = await call(files.download(did, path=path))
                content = content if isinstance(content, str) else json.dumps(content)
                if len(content) > MAX_INLINE_BASE64_CHARS:
                    fail(
                        "invalid_argument",
                        f'device file at "{path}" exceeds the 256KB inline transfer limit.',
                    )
                return {"content": content}
            await call(files.delete(did, path=path))
            return {"status": "deleted", "deviceId": deviceId, "path": path}
        session = await _session(rt, deviceId)
        session.require_adb("manage_device_files")
        if operation == "list":
            out = await session.shell(f"ls -la {q(path)}", check=False)
            return {"path": path, "entries": [ln for ln in out.splitlines() if ln.strip()]}
        if operation == "upload":
            await session.shell(f"echo {q(data)} | base64 -d > {q(path)}")
            return {"status": "uploaded", "deviceId": deviceId, "path": path}
        if operation == "download":
            size = (await session.shell(f"stat -c %s {q(path)}", check=False)).strip()
            if not size.isdigit():
                fail("element_not_found", f"no file at {path}: {size[:200]}")
            if int(size) > MAX_INLINE_FILE_BYTES:
                fail(
                    "invalid_argument",
                    f'device file at "{path}" exceeds the 256KB inline transfer limit.',
                )
            content = (await session.shell(f"base64 {q(path)}", timeout=60)).replace("\n", "")
            return {"content": content.replace("\r", "")}
        await session.shell(f"rm -rf {q(path)}")
        return {"status": "deleted", "deviceId": deviceId, "path": path}

    # ---- configure_device ---------------------------------------------------------------------
    configure_fields = {
        "get_language": (),
        "set_language": ("locale", "restart"),
        "get_timezone": (),
        "set_timezone": ("timezone",),
        "get_location": (),
        "set_location": ("latitude", "longitude"),
        "get_time": (),
        "get_overlay": (),
        "set_overlay": ("visible",),
        "proxy_connect": (
            "proxyName",
            "smartIp",
            "socks5Host",
            "socks5Port",
            "socks5User",
            "socks5Password",
        ),
        "proxy_disconnect": (),
        "get_proxy_status": (),
    }

    @mcp.tool(tags={"write"})
    async def configure_device(
        operation: Literal[
            "get_language",
            "set_language",
            "get_timezone",
            "set_timezone",
            "get_location",
            "set_location",
            "get_time",
            "get_overlay",
            "set_overlay",
            "proxy_connect",
            "proxy_disconnect",
            "get_proxy_status",
        ],
        deviceId: str,
        locale: str | None = None,
        restart: bool | None = None,
        timezone: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        visible: bool | None = None,
        proxyName: str | None = None,
        smartIp: bool | None = None,
        socks5Host: str | None = None,
        socks5Port: int | None = None,
        socks5User: str | None = None,
        socks5Password: str | None = None,
    ) -> Any:
        """Read/write device settings. Operations: get_language/set_language (locale: BCP-47;
        restart? applies it now), get_timezone/set_timezone (IANA tz), get_location/set_location
        (latitude, longitude; cloud only), get_time, get_overlay/set_overlay (visible: the
        Portal debug overlay), proxy_connect (proxyName? and/or smartIp? (default true), or
        socks5Host+socks5Port+socks5User?+socks5Password?; cloud only), proxy_disconnect,
        get_proxy_status."""
        given = {
            "locale": locale,
            "restart": restart,
            "timezone": timezone,
            "latitude": latitude,
            "longitude": longitude,
            "visible": visible,
            "proxyName": proxyName,
            "smartIp": smartIp,
            "socks5Host": socks5Host,
            "socks5Port": socks5Port,
            "socks5User": socks5User,
            "socks5Password": socks5Password,
        }
        disallowed(operation, configure_fields[operation], given)
        ok = {"status": "ok", "operation": operation, "deviceId": deviceId}
        if is_cloud(deviceId):
            return await _cloud_configure(operation, cloud_id(deviceId), given, ok)
        return await _local_configure(operation, deviceId, given, ok)

    async def _cloud_configure(operation: str, did: str, g: dict, ok: dict) -> Any:
        dev = client(rt).devices
        if operation == "get_language":
            return await call(dev.language.get(did))
        if operation == "set_language":
            await call(
                dev.language.set(
                    did,
                    locale=require(g["locale"], "locale", operation),
                    **kw(restart=g["restart"]),
                )
            )
            return ok
        if operation == "get_timezone":
            return await call(dev.timezone.get(did))
        if operation == "set_timezone":
            await call(
                dev.timezone.set(did, timezone=require(g["timezone"], "timezone", operation))
            )
            return ok
        if operation == "get_location":
            loc = await call(dev.location.get(did))
            return {"latitude": loc.get("latitude"), "longitude": loc.get("longitude")}
        if operation == "set_location":
            await call(
                dev.location.set(
                    did,
                    latitude=require(g["latitude"], "latitude", operation),
                    longitude=require(g["longitude"], "longitude", operation),
                )
            )
            return ok
        if operation == "get_time":
            return {"time": await call(dev.state.time(did))}
        if operation == "get_overlay":
            return await call(dev.actions.overlay_visible(did))
        if operation == "set_overlay":
            await call(
                dev.actions.set_overlay_visible(
                    did, visible=require(g["visible"], "visible", operation)
                )
            )
            return ok
        if operation == "proxy_connect":
            socks5 = None
            if g["socks5Host"] and g["socks5Port"] is not None:
                socks5 = kw(
                    host=g["socks5Host"],
                    port=g["socks5Port"],
                    user=g["socks5User"],
                    password=g["socks5Password"],
                )
            smart = g["smartIp"] if g["smartIp"] is not None else True
            await call(
                dev.proxy.connect(did, **kw(name=g["proxyName"], smart_ip=smart, socks5=socks5))
            )
            return ok
        if operation == "proxy_disconnect":
            await call(dev.proxy.disconnect(did))
            return ok
        return await call(dev.proxy.status(did))

    async def _local_configure(operation: str, device_id: str, g: dict, ok: dict) -> Any:
        if operation in (
            "get_location",
            "set_location",
            "proxy_connect",
            "proxy_disconnect",
            "get_proxy_status",
        ):
            local_only(operation)
        session = await _session(rt, device_id)
        if operation == "get_time":
            return {"time": await session.core.call("time")}
        session.require_adb(operation)
        if operation == "get_language":
            out = await session.shell(
                "getprop persist.sys.locale; getprop ro.product.locale", check=False
            )
            locale = next((v.strip() for v in out.splitlines() if v.strip()), "")
            return {"locale": locale}
        if operation == "set_language":
            loc = require(g["locale"], "locale", operation)
            await session.shell(f"setprop persist.sys.locale {q(loc)}")
            if g["restart"]:
                await session.shell("stop; start", check=False)
                session._connected = False
            return ok
        if operation == "get_timezone":
            return {"timezone": (await session.shell("getprop persist.sys.timezone")).strip()}
        if operation == "set_timezone":
            tz = require(g["timezone"], "timezone", operation)
            await session.shell(f"setprop persist.sys.timezone {q(tz)}")
            return ok
        if operation == "get_overlay":
            return await _portal_json(session, "overlay/visible")
        await _portal_json(
            session, "overlay/set-visible", visible=require(g["visible"], "visible", operation)
        )
        return ok

    # ---- manage_esim ----------------------------------------------------------------------------
    esim_fields = {
        "list": (),
        "activate": ("enable", "smDpAddr", "confirmationCode", "matchingId"),
        "enable": ("subId",),
        "remove": ("subId",),
    }

    @mcp.tool(tags={"write"})
    async def manage_esim(
        operation: Literal["list", "activate", "enable", "remove"],
        deviceId: str,
        enable: bool | None = None,
        smDpAddr: str | None = None,
        confirmationCode: str | None = None,
        matchingId: str | None = None,
        subId: int | None = None,
    ) -> Any:
        """eSIM subscription management (Mobilerun Cloud devices). Operations: list, activate
        (smDpAddr, enable, confirmationCode?/matchingId?), enable (subId), remove (subId)."""
        disallowed(
            operation,
            esim_fields[operation],
            {
                "enable": enable,
                "smDpAddr": smDpAddr,
                "confirmationCode": confirmationCode,
                "matchingId": matchingId,
                "subId": subId,
            },
        )
        if not is_cloud(deviceId):
            local_only("manage_esim")
        esim = client(rt).devices.esim
        did = cloud_id(deviceId)
        if operation == "list":
            return await call(esim.list(did))
        if operation == "activate":
            return await call(
                esim.activate(
                    did,
                    enable=require(enable, "enable", operation),
                    sm_dp_addr=require(smDpAddr, "smDpAddr", operation),
                    **kw(confirmation_code=confirmationCode, matching_id=matchingId),
                )
            )
        sub = require(subId, "subId", operation)
        if operation == "enable":
            await call(esim.enable(did, sub_id=sub))
        else:
            await call(esim.remove(did, sub_id=sub))
        return {"status": "ok", "operation": operation, "deviceId": deviceId, "subId": sub}

    # ---- credentials (tools/credentials.ts) -------------------------------------------------
    def meta(cred: dict) -> dict:
        """Strip field values: credential values never leave the vault through this tool."""
        return {
            "credentialName": cred.get("credentialName"),
            "packageName": cred.get("packageName"),
            "userId": cred.get("userId"),
            "secretPath": cred.get("secretPath"),
            "fields": [{"fieldType": f.get("fieldType")} for f in cred.get("fields") or []],
        }

    def written(result: dict) -> dict:
        return {
            "data": meta(result.get("data") or {}),
            "message": result.get("message"),
            "success": result.get("success"),
        }

    @mcp.tool(tags={"read"})
    async def list_credentials(packageName: str | None = None) -> Any:
        """List saved credentials (metadata only; values never leave credentials storage).
        Optional packageName scopes to one app."""
        creds = client(rt).credentials
        if packageName:
            result = await call(creds.packages.list(packageName))
            return {"items": result.get("data")}
        result = await call(creds.list())
        return {"items": result.get("items"), "pagination": result.get("pagination")}

    @mcp.tool(tags={"read"})
    async def list_credential_packages() -> Any:
        """List app packages that have any credential configured. Each entry is {packageName}."""
        names: dict[str, None] = {}
        page_size = 100
        for page in range(1, 21):
            result = await call(client(rt).credentials.list(page=page, page_size=page_size))
            items = result.get("items") or []
            for item in items:
                if isinstance(item, dict) and "packageName" in item:
                    names[item["packageName"]] = None
            pages = (result.get("pagination") or {}).get("pages")
            if not pages or page >= pages or len(items) < page_size:
                break
        return {"items": [{"packageName": n} for n in names], "derived": True}

    @mcp.tool(tags={"write"})
    async def manage_credentials(
        operation: Literal[
            "init_package",
            "create_credential",
            "delete_credential",
            "add_field",
            "update_field",
            "delete_field",
        ],
        packageName: Annotated[str | None, Field(min_length=1, max_length=256)] = None,
        credentialName: Annotated[str | None, Field(min_length=1, max_length=256)] = None,
        fieldType: FIELD_TYPES | None = None,
        value: Annotated[str | None, Field(min_length=1, max_length=4096)] = None,
        fields: Annotated[list[dict[str, Any]] | None, Field(min_length=1)] = None,
    ) -> Any:
        """Write path for the credentials vault. Operations: init_package (packageName),
        create_credential (packageName, credentialName, fields[{fieldType, value}]),
        delete_credential (packageName, credentialName), add_field / update_field (packageName,
        credentialName, fieldType, value), delete_field (packageName, credentialName, fieldType).
        Values are write-only: responses carry metadata only."""

        def need(v: Any, name: str) -> Any:
            return require(v, name, operation, "manage_credentials operation")

        pk = client(rt).credentials.packages
        if operation == "init_package":
            return await call(pk.create(package_name=need(packageName, "packageName")))
        pkg = need(packageName, "packageName")
        if operation == "create_credential":
            return written(
                await call(
                    pk.credentials.create(
                        pkg,
                        credential_name=need(credentialName, "credentialName"),
                        fields=need(fields, "fields"),
                    )
                )
            )
        name = need(credentialName, "credentialName")
        if operation == "delete_credential":
            return written(await call(pk.credentials.delete(name, package_name=pkg)))
        ftype = need(fieldType, "fieldType")
        f = pk.credentials.fields
        if operation == "add_field":
            return written(
                await call(
                    f.create(name, package_name=pkg, field_type=ftype, value=need(value, "value"))
                )
            )
        if operation == "update_field":
            return written(
                await call(
                    f.update(
                        ftype, package_name=pkg, credential_name=name, value=need(value, "value")
                    )
                )
            )
        return written(await call(f.delete(ftype, package_name=pkg, credential_name=name)))

    # ---- webhooks -----------------------------------------------------------------------------
    secret_note = (
        "Show the returned plaintext data.secret to the user now, exactly once, and tell them "
        "to store it securely."
    )

    def with_secret(result: Any, note: str) -> dict:
        if isinstance(result, dict):
            return {**result, "secretHandling": note}
        return {"result": result, "secretHandling": note}

    @mcp.tool(tags={"write"})
    async def webhooks(
        operation: Literal[
            "create",
            "list",
            "get",
            "update",
            "rotate_secret",
            "test",
            "list_deliveries",
            "get_delivery",
            "delivery_stats",
            "list_event_types",
        ],
        endpointId: str | None = None,
        deliveryId: str | None = None,
        url: Annotated[str | None, Field(max_length=2048)] = None,
        eventTypes: Annotated[list[str] | None, Field(max_length=100)] = None,
        description: Annotated[str | None, Field(max_length=500)] = None,
        state: Literal["ACTIVE", "DISABLED"] | None = None,
        status: Literal["active", "failing", "blocked", "disabled"] | None = None,
        page: Annotated[int | None, Field(gt=0)] = None,
        pageSize: Annotated[int | None, Field(gt=0, le=100)] = None,
        since: str | None = None,
    ) -> Any:
        """Manage outbound webhooks and inspect deliveries. Operations: create (url; returns a
        one-time secret), list (status?), get, update (eventTypes/state/description), rotate_secret
        (returns a one-time secret), test, list_deliveries, get_delivery (endpointId,
        deliveryId), delivery_stats (since?), list_event_types."""
        wh = client(rt).webhooks

        def need(v: Any, name: str) -> Any:
            return require(v, name, operation, "webhooks operation")

        if operation == "create":
            result = await call(
                wh.create(
                    url=need(url, "url"), **kw(event_types=eventTypes, description=description)
                )
            )
            return with_secret(result, secret_note + " Never place it in workflow action data.")
        if operation == "list":
            return await call(wh.list(**kw(status=status, page=page, page_size=pageSize)))
        if operation == "delivery_stats":
            return await call(wh.deliveries.stats(**kw(since=since)))
        if operation == "list_event_types":
            return await call(wh.event_types())
        endpoint = need(endpointId, "endpointId")
        if operation == "get":
            return await call(wh.retrieve(endpoint))
        if operation == "update":
            body = kw(event_types=eventTypes, state=state, description=description)
            if not body:
                fail(
                    "invalid_argument",
                    "webhooks operation=update requires eventTypes, state, or description",
                )
            return await call(wh.update(endpoint, **body))
        if operation == "rotate_secret":
            result = await call(wh.rotate_secret(endpoint))
            return with_secret(result, secret_note + " The previous secret is already invalid.")
        if operation == "test":
            return await call(wh.test_delivery(endpoint))
        if operation == "list_deliveries":
            return await call(
                wh.deliveries.list_for_webhook(endpoint, **kw(page=page, page_size=pageSize))
            )
        return await call(
            wh.deliveries.retrieve_attempts(need(deliveryId, "deliveryId"), id=endpoint)
        )

    # ---- proxies ------------------------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def proxies(
        operation: Literal["list", "get", "create", "update", "delete", "lookup"],
        proxyId: str | None = None,
        protocol: Literal["socks5", "wireguard"] | None = None,
        name: str | None = None,
        host: str | None = None,
        port: Annotated[int | None, Field(gt=0)] = None,
        user: str | None = None,
        password: str | None = None,
        config: str | None = None,
        lookupUser: str | None = None,
        lookupPassword: str | None = None,
    ) -> Any:
        """Manage device-bound proxy configs (socks5 or wireguard). Operations: list (protocol?),
        get, create / update (protocol + name + socks5 host/port/user/password or wireguard
        config), delete, lookup (host, port, lookupUser?, lookupPassword?: resolve IP/geo/carrier
        for a socks5 endpoint)."""
        px = client(rt).proxies

        def need(v: Any, n: str) -> Any:
            return require(v, n, operation, "proxies operation")

        def params() -> dict:
            proto = need(protocol, "protocol")
            if proto == "socks5":
                return {
                    "protocol": "socks5",
                    "name": need(name, "name"),
                    "host": need(host, "host"),
                    "port": need(port, "port"),
                    "user": need(user, "user"),
                    "password": need(password, "password"),
                }
            return {
                "protocol": "wireguard",
                "name": need(name, "name"),
                "config": need(config, "config"),
            }

        if operation == "list":
            return await call(px.list(**kw(protocol=protocol)))
        if operation == "lookup":
            return await call(
                px.lookup(
                    socks5=kw(
                        host=need(host, "host"),
                        port=need(port, "port"),
                        user=lookupUser,
                        password=lookupPassword,
                    )
                )
            )
        if operation == "create":
            return await call(px.create(**params()))
        pid = need(proxyId, "proxyId")
        if operation == "get":
            return await call(px.retrieve(pid))
        if operation == "update":
            return await call(px.update(pid, **params()))
        return await call(px.delete(pid))

    # ---- connect ------------------------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def connect(
        operation: Literal[
            "list_countries",
            "list_proxies",
            "get_proxy",
            "buy_proxy",
            "cancel_proxy",
            "ping_proxy",
            "list_connections",
            "list_users",
            "get_user",
            "list_user_connections",
        ],
        proxyId: str | None = None,
        userId: str | None = None,
        country: str | None = None,
        type: Literal["residential"] | None = None,
        page: Annotated[int | None, Field(gt=0)] = None,
        pageSize: Annotated[int | None, Field(gt=0, le=100)] = None,
        status: Literal["active", "closed"] | None = None,
        protocol: Literal["tcp", "udp", "unknown"] | None = None,
        provider: str | None = None,
        dstHost: str | None = None,
        dstPort: int | None = None,
        sessionId: str | None = None,
        startedAfter: str | None = None,
        startedBefore: str | None = None,
        endedAfter: str | None = None,
        endedBefore: str | None = None,
        order: Literal["asc", "desc"] | None = None,
        orderBy: Literal["startedAt", "endedAt", "bytesIn", "bytesOut", "totalBytes", "durationMs"]
        | None = None,
    ) -> Any:
        """droidrun-connect residential SOCKS5 proxies and their users (distinct from the
        device-bound `proxies` tool). Operations: list_countries, list_proxies, get_proxy,
        buy_proxy (COMMERCE: provisions and bills), cancel_proxy (COMMERCE), ping_proxy,
        list_connections, list_users, get_user, list_user_connections."""
        cn = client(rt).connect

        def need(v: Any, n: str) -> Any:
            return require(v, n, operation, "connect operation")

        conn = kw(
            status=status,
            protocol=protocol,
            country=country,
            provider=provider,
            dst_host=dstHost,
            dst_port=dstPort,
            session_id=sessionId,
            started_after=startedAfter,
            started_before=startedBefore,
            ended_after=endedAfter,
            ended_before=endedBefore,
            order=order,
            order_by=orderBy,
            page=page,
            page_size=pageSize,
        )
        if operation == "list_countries":
            return await call(cn.countries.list(**kw(type=type, page=page, page_size=pageSize)))
        if operation == "list_proxies":
            return await call(cn.proxies.list(**kw(country=country, page=page, page_size=pageSize)))
        if operation == "get_proxy":
            return await call(cn.proxies.retrieve(need(proxyId, "proxyId")))
        if operation == "buy_proxy":
            return await call(
                cn.proxies.buy(country=need(country, "country"), type=type or "residential")
            )
        if operation == "cancel_proxy":
            await call(cn.proxies.cancel(need(proxyId, "proxyId")))
            return {"success": True}
        if operation == "ping_proxy":
            return await call(cn.proxies.ping(need(proxyId, "proxyId")))
        if operation == "list_connections":
            return await call(cn.proxies.list_connections(need(proxyId, "proxyId"), **conn))
        if operation == "list_users":
            return await call(cn.users.list(**kw(proxy_id=proxyId, page=page, page_size=pageSize)))
        if operation == "get_user":
            return await call(cn.users.retrieve(need(userId, "userId")))
        return await call(cn.users.list_connections(need(userId, "userId"), **conn))

    # ---- apps (uploaded APKs) -----------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def apps(
        operation: Literal[
            "list",
            "get",
            "versions",
            "create_upload_url",
            "confirm_upload",
            "mark_failed",
            "delete",
        ],
        id: str | None = None,
        query: str | None = None,
        platform: Literal["all", "android", "ios"] | None = None,
        status: Literal["all", "queued", "available", "failed"] | None = None,
        sortBy: Literal["createdAt", "name"] | None = None,
        order: Literal["asc", "desc"] | None = None,
        page: Annotated[int | None, Field(gt=0)] = None,
        pageSize: Annotated[int | None, Field(gt=0, le=100)] = None,
        bundleId: str | None = None,
        displayName: str | None = None,
        versionCode: int | None = None,
        versionName: str | None = None,
        sizeBytes: Annotated[int | None, Field(gt=0)] = None,
        files: Annotated[list[dict[str, Any]] | None, Field(min_length=1)] = None,
        uploadPlatform: Literal["android", "ios"] | None = None,
        country: str | None = None,
        description: str | None = None,
        developerName: str | None = None,
        iconURL: str | None = None,
        targetSdk: int | None = None,
    ) -> Any:
        """Manage uploaded apps (APKs) in Mobilerun Cloud. Operations: list, get, versions,
        create_upload_url (bundleId, displayName, versionCode, versionName, sizeBytes,
        files[{fileName, contentType, sha256?}]: returns pre-signed PUT URLs; PUT the bytes, then
        confirm_upload, or mark_failed), confirm_upload, mark_failed, delete."""
        ap = client(rt).apps

        def need(v: Any, n: str) -> Any:
            return require(v, n, operation, "apps operation")

        if operation == "list":
            return await call(
                ap.list(
                    **kw(
                        query=query,
                        platform=platform,
                        status=status,
                        sort_by=sortBy,
                        order=order,
                        page=page,
                        page_size=pageSize,
                    )
                )
            )
        if operation == "create_upload_url":
            need(sizeBytes, "sizeBytes")
            return await call(
                ap.create_signed_upload_url(
                    bundle_id=need(bundleId, "bundleId"),
                    display_name=need(displayName, "displayName"),
                    version_code=need(versionCode, "versionCode"),
                    version_name=need(versionName, "versionName"),
                    files=need(files, "files"),
                    **kw(
                        platform=uploadPlatform,
                        country=country,
                        description=description,
                        developer_name=developerName,
                        icon_url=iconURL,
                        target_sdk=targetSdk,
                    ),
                    extra_body={"sizeBytes": sizeBytes},
                )
            )
        app_id = need(id, "id")
        if operation == "get":
            return await call(ap.retrieve(app_id))
        if operation == "versions":
            return await call(ap.list_versions(app_id))
        if operation == "confirm_upload":
            return await call(ap.confirm_upload(app_id))
        if operation == "mark_failed":
            return await call(ap.mark_failed(app_id))
        return await call(ap.delete(app_id))

    # ---- platform_catalog ---------------------------------------------------------------------
    @mcp.tool(tags={"read"})
    async def platform_catalog(catalog: Literal["models", "timezones", "app_event_types"]) -> Any:
        """Read-only platform reference data: models (LLM model ids), timezones (IANA strings for
        create_trigger), app_event_types (every selectable app/system event type)."""
        if catalog == "models":
            return await call(client(rt).models.list())
        if catalog == "timezones":
            return await call(client(rt).workflows.timezones.list())
        return await _event_catalog()

    # ---- workflows ----------------------------------------------------------------------------
    async def _event_catalog(**query: Any) -> Any:
        # GET /events/catalog (TS SDK 5.1 workflows.events.catalog.list; absent from the
        # Python SDK, so called through the client's raw request API).
        params = kw(**query)
        return await call(
            client(rt).get(
                "/events/catalog", cast_to=object, options={"params": params} if params else {}
            )
        )

    list_allowed = {
        "action_catalog": ("service",),
        "app_event_catalog": (),
        "action": ("service", "search", "page", "pageSize"),
        "trigger": ("activation", "eventType", "search", "page", "pageSize"),
        "flow": ("enabled", "search", "triggerId", "page", "pageSize"),
        "execution": ("flowId", "triggerId", "status", "limit"),
        "service": (),
        "service_methods": ("service",),
    }

    @mcp.tool(tags={"read"})
    async def list_workflow_resources(
        resource: Literal[
            "action_catalog",
            "app_event_catalog",
            "action",
            "trigger",
            "flow",
            "execution",
            "service",
            "service_methods",
        ],
        service: Literal["tasks_api", "devices_api", "agents_api", "webhooks"] | None = None,
        search: str | None = None,
        activation: Literal["event", "schedule", "custom"] | None = None,
        eventType: str | None = None,
        enabled: bool | None = None,
        triggerId: str | None = None,
        flowId: str | None = None,
        status: Literal["pending", "running", "success", "failed"] | None = None,
        page: Annotated[int | None, Field(gt=0)] = None,
        pageSize: Annotated[int | None, Field(gt=0, le=100)] = None,
        limit: Annotated[int | None, Field(gt=0, le=100)] = None,
    ) -> Any:
        """List one kind of workflow resource. resource (filters): action_catalog (service),
        app_event_catalog (none; call before create_trigger with activation=event), action
        (service, search, page, pageSize), trigger (activation, eventType, search, page,
        pageSize), flow (enabled, search, triggerId, page, pageSize), execution (flowId,
        triggerId, status, limit), service (none), service_methods (service, required)."""
        filters = {
            "service": service,
            "search": search,
            "activation": activation,
            "eventType": eventType,
            "enabled": enabled,
            "triggerId": triggerId,
            "flowId": flowId,
            "status": status,
            "page": page,
            "pageSize": pageSize,
            "limit": limit,
        }
        allowed = list_allowed[resource]
        extra = [k for k, v in filters.items() if v is not None and k not in allowed]
        if extra:
            fail(
                "invalid_argument",
                f"filter {', '.join(extra)} is not valid for "
                f"resource={resource}; allowed filters: {', '.join(allowed) or '(none)'}",
            )
        if resource == "service_methods" and service is None:
            fail("invalid_argument", "resource=service_methods requires filter: service")
        wf = client(rt).workflows
        if resource == "action_catalog":
            return await call(wf.action_catalog.list(**kw(service=service, page_size=100)))
        if resource == "app_event_catalog":
            return await _event_catalog()
        if resource == "action":
            return await call(
                wf.actions.list(**kw(service=service, search=search, page=page, page_size=pageSize))
            )
        if resource == "trigger":
            return await call(
                wf.triggers.list(
                    **kw(
                        activation=activation,
                        event_type=eventType,
                        search=search,
                        page=page,
                        page_size=pageSize,
                    )
                )
            )
        if resource == "flow":
            flag = None if enabled is None else ("true" if enabled else "false")
            return await call(
                wf.flows.list(
                    **kw(
                        enabled=flag,
                        search=search,
                        trigger_id=triggerId,
                        page=page,
                        page_size=pageSize,
                    )
                )
            )
        if resource == "execution":
            return await call(
                wf.executions.list(
                    **kw(flow_id=flowId, trigger_id=triggerId, status=status, page_size=limit)
                )
            )
        if resource == "service":
            result = await call(wf.actions.services.list())
            return {"items": result.get("data") if isinstance(result, dict) else result}
        result = await call(wf.actions.services.list_methods(service))
        return {"items": result.get("data") if isinstance(result, dict) else result}

    @mcp.tool(tags={"read"})
    async def get_workflow_resource(
        resource: Literal["action_catalog", "action", "trigger", "flow", "execution"], id: str
    ) -> Any:
        """Fetch one workflow resource by id (full config/params)."""
        wf = client(rt).workflows
        getter = {
            "action_catalog": wf.action_catalog.retrieve,
            "action": wf.actions.retrieve,
            "trigger": wf.triggers.retrieve,
            "flow": wf.flows.retrieve,
            "execution": wf.executions.retrieve,
        }[resource]
        try:
            return await call(getter(id))
        except McpToolError as exc:
            fail(exc.code, f"{resource} {id}: {str(exc).split('] ', 1)[-1]}")

    @mcp.tool(tags={"write"})
    async def create_action(
        catalogEntryId: str,
        name: str,
        description: str | None = None,
        isAsync: bool | None = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Create an action from a catalog entry. `params` is action-specific (per the entry's
        paramsSchema)."""
        return await call(
            client(rt).workflows.actions.create(
                catalog_entry_id=catalogEntryId,
                name=name,
                **kw(description=description, params=params),
            )
        )

    @mcp.tool(tags={"write"})
    async def create_trigger(
        name: str,
        activation: Literal["event", "schedule", "custom"],
        eventType: str | None = None,
        scheduleRule: dict[str, Any] | None = None,
        customPayloadSchema: dict[str, Any] | None = None,
        timezone: str | None = None,
        description: str | None = None,
        conditions: dict[str, Any] | None = None,
    ) -> Any:
        """Create a trigger. activation=event needs eventType; =schedule needs scheduleRule
        ({type: once|cron|recurring, dateTime|expression|rrule, jitter?}) + timezone for
        cron/recurring; =custom optionally constrained by customPayloadSchema."""
        if scheduleRule is not None and scheduleRule.get("type") not in (
            "once",
            "cron",
            "recurring",
        ):
            fail("invalid_argument", "scheduleRule.type must be once, cron or recurring")
        return await call(
            client(rt).workflows.triggers.create(
                name=name,
                activation=activation,
                **kw(
                    event_type=eventType,
                    schedule_rule=scheduleRule,
                    custom_payload_schema=customPayloadSchema,
                    timezone=timezone,
                    description=description,
                    conditions=conditions,
                ),
            )
        )

    @mcp.tool(tags={"write"})
    async def create_flow(
        name: str,
        triggerId: str,
        actions: list[dict[str, Any]],
        deviceIds: Annotated[list[str], Field(min_length=1)],
        description: str | None = None,
        cooldownSeconds: Annotated[int | None, Field(ge=0)] = None,
        cooldownScope: Literal["flow", "device"] | None = None,
    ) -> Any:
        """Create a flow binding a trigger to ordered actions ([{actionId, position (1-based)}]);
        target devices go in the top-level deviceIds."""
        for entry in actions:
            if set(entry) - {"actionId", "position"} or "actionId" not in entry:
                fail("invalid_argument", "each action entry is only {actionId, position}")
        return await call(
            client(rt).workflows.flows.create(
                name=name,
                trigger_id=triggerId,
                actions=actions,
                device_ids=deviceIds,
                **kw(
                    description=description,
                    cooldown_seconds=cooldownSeconds,
                    cooldown_scope=cooldownScope,
                ),
            )
        )

    @mcp.tool(tags={"write"})
    async def manage_flow(
        operation: Literal[
            "clone",
            "unblock",
            "add_action",
            "remove_action",
            "replace_actions",
            "execution_metrics",
        ],
        flowId: str | None = None,
        name: str | None = None,
        deviceIds: list[str] | None = None,
        actionId: str | None = None,
        position: Annotated[int | None, Field(gt=0)] = None,
        continueOnError: bool | None = None,
        nameOverride: str | None = None,
        overrides: dict[str, Any] | None = None,
        parentFlowActionId: str | None = None,
        children: list[dict[str, Any]] | None = None,
        flowActionId: str | None = None,
        actions: list[dict[str, Any]] | None = None,
        triggerId: str | None = None,
        from_: Annotated[str | None, Field(alias="from")] = None,
        to: str | None = None,
    ) -> Any:
        """Flow lifecycle beyond create_flow. Operations: clone (flowId, name?, deviceIds?),
        unblock (flowId), add_action (flowId, actionId, position, continueOnError?, nameOverride?,
        overrides?, parentFlowActionId?, children?), remove_action (flowActionId, flowId),
        replace_actions (flowId, actions[]: replaces the whole list), execution_metrics (flowId?,
        triggerId?, from?, to?)."""
        flows = client(rt).workflows.flows

        def need(v: Any, n: str) -> Any:
            return require(v, n, operation, "manage_flow operation")

        if operation == "execution_metrics":
            return await call(
                client(rt).workflows.executions.get_metrics(
                    **kw(flow_id=flowId, trigger_id=triggerId, from_=from_, to=to)
                )
            )
        if operation == "clone":
            return await call(
                flows.clone(need(flowId, "flowId"), **kw(name=name, device_ids=deviceIds))
            )
        if operation == "unblock":
            return await call(flows.unblock(need(flowId, "flowId")))
        if operation == "add_action":
            fid = need(flowId, "flowId")
            return await call(
                flows.actions.add(
                    fid,
                    action_id=need(actionId, "actionId"),
                    position=need(position, "position"),
                    **kw(
                        continue_on_error=continueOnError,
                        name_override=nameOverride,
                        overrides=overrides,
                        parent_flow_action_id=parentFlowActionId,
                        children=children,
                    ),
                )
            )
        if operation == "remove_action":
            return await call(
                flows.actions.remove(
                    need(flowActionId, "flowActionId"), flow_id=need(flowId, "flowId")
                )
            )
        fid = need(flowId, "flowId")
        result = await call(flows.actions.replace(fid, actions=need(actions, "actions")))
        return {"items": result.get("data") if isinstance(result, dict) else result}

    @mcp.tool(tags={"write"})
    async def workflow_events(
        operation: Literal["ingest", "dry_run", "list_event_types", "register_events"],
        eventType: str | None = None,
        payload: dict[str, Any] | None = None,
        source: Literal["device", "system", "webhook"] | None = None,
        page: Annotated[int | None, Field(gt=0)] = None,
        pageSize: Annotated[int | None, Field(gt=0, le=100)] = None,
        events: Annotated[list[dict[str, Any]] | None, Field(min_length=1)] = None,
    ) -> Any:
        """Ingest, simulate and catalog custom app/system events for trigger evaluation.
        Operations: ingest (eventType, payload?), dry_run (eventType, payload?: which flows
        would fire, no side effects), list_event_types (source?, page?, pageSize?),
        register_events (events[{eventType, label, description?, payloadSchema?, source?}])."""
        wf = client(rt).workflows

        def need(v: Any, n: str) -> Any:
            return require(v, n, operation, "workflow_events operation")

        if operation == "list_event_types":
            return await _event_catalog(source=source, page=page, pageSize=pageSize)
        if operation == "register_events":
            evs = need(events, "events")
            for ev in evs:
                if not ev.get("eventType") or not ev.get("label"):
                    fail("invalid_argument", "each event needs eventType and label")
            return await call(
                client(rt).post("/events/catalog/register", cast_to=object, body={"events": evs})
            )
        et = need(eventType, "eventType")
        if operation == "ingest":
            return await call(wf.events.ingest(event_type=et, **kw(payload=payload)))
        return await call(wf.events.dry_run(event_type=et, **kw(payload=payload)))
