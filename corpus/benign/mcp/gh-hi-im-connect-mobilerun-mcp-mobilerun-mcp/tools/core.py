"""mobilerun-core's ``Device`` API (droidrun's canonical control surface) as MCP tools.

Each tool calls the same-named ``Device`` method with the same parameters, so code written
against mobilerun-core maps 1:1. On Android over adb the Device runs on this server's fast
transport (:mod:`mobilerun_mcp.fastconn`); on iOS, Portal-HTTP and Mobilerun Cloud devices it
uses core's own connections. Tools that change the screen also return post_action_observation.
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP

from ..observe import mutate
from ..session import DeviceSession, Runtime
from .common import Device, get_session


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def call(device: Device, method: str, *args: Any, **kwargs: Any) -> Any:
        session = get_session(rt, device)
        await session.ensure_connected()
        return _plain(await session.core.call(method, *args, **kwargs))

    async def act(device: Device, method: str, *args: Any, **kwargs: Any) -> dict:
        session: DeviceSession = get_session(rt, device)
        await session.ensure_connected()
        box: dict[str, Any] = {}

        async def run() -> None:
            box["result"] = _plain(await session.core.call(method, *args, **kwargs))

        observed = await mutate(session, run, {"action": method})
        return {**observed, "result": box.get("result")}

    # ---- snapshot ----------------------------------------------------------------------
    @mcp.tool(tags={"read"})
    async def ui(filter: bool = True, device: Device = None) -> dict:
        """Raw UI snapshot (a11y_tree, phone_state, device_context, ...), as Device.ui()."""
        return await call(device, "ui", filter=filter)

    @mcp.tool(tags={"read"})
    async def ui_json(filter: bool = True, indent: int | None = None, device: Device = None) -> str:
        """The UI snapshot serialized as JSON text."""
        return await call(device, "ui_json", filter=filter, indent=indent)

    @mcp.tool(tags={"read"})
    async def ui_with_recovery(filter: bool = True, device: Device = None) -> dict:
        """UI snapshot that retries past a dead or empty accessibility tree."""
        return await call(device, "ui_with_recovery", filter=filter)

    @mcp.tool(tags={"read"})
    async def capabilities(device: Device = None) -> dict:
        """Backend, platform and the actions this device supports."""
        return _plain(await get_session(rt, device).core.capabilities())

    @mcp.tool(tags={"read"})
    async def supports(action: str, device: Device = None) -> bool:
        """Whether this device supports a Device action (e.g. execute_script, get_clipboard)."""
        return bool(await call(device, "supports", action))

    @mcp.tool(tags={"read"})
    async def screen_size(device: Device = None) -> list[int]:
        """[width, height] in pixels."""
        return list(await call(device, "screen_size"))

    @mcp.tool(tags={"read"})
    async def current_app_id(device: Device = None) -> str | None:
        """Package / bundle id of the foreground app."""
        return await call(device, "current_app_id")

    @mcp.tool(tags={"read"})
    async def time(device: Device = None) -> str:
        """The device clock."""
        return await call(device, "time")

    # ---- nodes -------------------------------------------------------------------------
    @mcp.tool(tags={"read"})
    async def find_nodes(
        text: str | None = None,
        desc: str | None = None,
        resource_id: str | None = None,
        class_name: str | None = None,
        text_contains: str | None = None,
        desc_contains: str | None = None,
        any_contains: str | None = None,
        tree: dict | list | None = None,
        device: Device = None,
    ) -> list[dict]:
        """Nodes matching every given filter (exact text/desc/resource_id/class_name, or
        *_contains substrings), including off-screen ones."""
        return await call(
            device,
            "find_nodes",
            text=text,
            desc=desc,
            resource_id=resource_id,
            class_name=class_name,
            text_contains=text_contains,
            desc_contains=desc_contains,
            any_contains=any_contains,
            tree=tree,
        )

    @mcp.tool(tags={"read"})
    async def find_nodes_on_screen(
        text: str | None = None,
        desc: str | None = None,
        resource_id: str | None = None,
        class_name: str | None = None,
        text_contains: str | None = None,
        desc_contains: str | None = None,
        any_contains: str | None = None,
        tree: dict | list | None = None,
        device: Device = None,
    ) -> list[dict]:
        """Like find_nodes, limited to nodes inside the visible screen."""
        return await call(
            device,
            "find_nodes_on_screen",
            text=text,
            desc=desc,
            resource_id=resource_id,
            class_name=class_name,
            text_contains=text_contains,
            desc_contains=desc_contains,
            any_contains=any_contains,
            tree=tree,
        )

    @mcp.tool(tags={"write"})
    async def tap_text(text: str, device: Device = None) -> dict:
        """Tap the first on-screen node whose text/description contains text."""
        return await act(device, "tap_text", text)

    @mcp.tool(tags={"write"})
    async def tap_node(node: dict, stealth: bool = True, device: Device = None) -> dict:
        """Tap the center of a node returned by find_nodes / find_nodes_on_screen."""
        return await act(device, "tap_node", node, stealth=stealth)

    @mcp.tool(tags={"write"})
    async def tap_and_wait(target: str | dict, idle: float = 2.0, device: Device = None) -> dict:
        """Tap a text (or node) and wait until the UI has been idle for idle seconds."""
        return await act(device, "tap_and_wait", target, idle=idle)

    @mcp.tool(tags={"write"})
    async def scroll_until(
        text: str | None = None,
        text_contains: str | None = None,
        any_contains: str | None = None,
        resource_id: str | None = None,
        direction: str = "down",
        max_swipes: int = 10,
        distance: float = 0.35,
        settle: float = 0.5,
        device: Device = None,
    ) -> dict:
        """Scroll until a matching node is on screen; result is the node (or null)."""
        return await act(
            device,
            "scroll_until",
            text=text,
            text_contains=text_contains,
            any_contains=any_contains,
            resource_id=resource_id,
            direction=direction,
            max_swipes=max_swipes,
            distance=distance,
            settle=settle,
        )

    @mcp.tool(tags={"write"})
    async def clear_input(device: Device = None) -> dict:
        """Clear the focused text field."""
        return await act(device, "clear_input")

    # ---- assertions and waits ----------------------------------------------------------
    @mcp.tool(tags={"read"})
    async def assert_on(app_id: str, device: Device = None) -> dict:
        """Fail unless app_id is in the foreground."""
        await call(device, "assert_on", app_id)
        return {"ok": True, "app_id": app_id}

    @mcp.tool(tags={"read"})
    async def assert_text_visible(text: str, timeout: float = 5.0, device: Device = None) -> dict:
        """Fail unless text becomes visible on screen within timeout seconds."""
        await call(device, "assert_text_visible", text, timeout=timeout)
        return {"ok": True, "text": text}

    @mcp.tool(tags={"read"})
    async def wait_for_app(
        app_id: str, timeout: float = 10.0, poll: float = 0.5, device: Device = None
    ) -> bool:
        """Wait until app_id is in the foreground."""
        return bool(await call(device, "wait_for_app", app_id, timeout=timeout, poll=poll))

    @mcp.tool(tags={"read"})
    async def wait_for_idle(timeout: float = 5.0, poll: float = 0.5, device: Device = None) -> bool:
        """Wait until the UI stops changing."""
        return bool(await call(device, "wait_for_idle", timeout=timeout, poll=poll))

    @mcp.tool(tags={"read"})
    async def wait_for_screen_change(
        timeout: float = 10.0, poll: float = 0.5, device: Device = None
    ) -> bool:
        """Wait until the UI differs from now."""
        return bool(await call(device, "wait_for_screen_change", timeout=timeout, poll=poll))

    @mcp.tool(tags={"read"})
    async def wait_for_text(
        text: str, timeout: float = 10.0, poll: float = 0.5, device: Device = None
    ) -> bool:
        """Wait until a node containing text exists (off-screen nodes count)."""
        return bool(await call(device, "wait_for_text", text, timeout=timeout, poll=poll))

    @mcp.tool(tags={"read"})
    async def wait_for_nodes(
        timeout: float = 10.0,
        poll: float = 0.5,
        text: str | None = None,
        desc: str | None = None,
        resource_id: str | None = None,
        class_name: str | None = None,
        text_contains: str | None = None,
        desc_contains: str | None = None,
        any_contains: str | None = None,
        on_screen: bool = False,
        device: Device = None,
    ) -> list[dict]:
        """Poll find_nodes until something matches (or timeout, returning [])."""
        return await call(
            device,
            "wait_for_nodes",
            timeout=timeout,
            poll=poll,
            text=text,
            desc=desc,
            resource_id=resource_id,
            class_name=class_name,
            text_contains=text_contains,
            desc_contains=desc_contains,
            any_contains=any_contains,
            on_screen=on_screen,
        )

    # ---- apps and system ---------------------------------------------------------------
    @mcp.tool(tags={"write"})
    async def open_and_settle(
        app_id: str, timeout: float = 15.0, idle: float = 3.0, device: Device = None
    ) -> dict:
        """Start an app and wait until it is in front and idle."""
        return await act(device, "open_and_settle", app_id, timeout=timeout, idle=idle)

    @mcp.tool(tags={"write"})
    async def stop_app(app_id: str, clear_data: bool = False, device: Device = None) -> dict:
        """Force-stop an app; clear_data also wipes its data."""
        return await act(device, "stop_app", app_id, clear_data=clear_data)

    @mcp.tool(tags={"write"})
    async def install_app(
        path: str, replace: bool = False, grant_permissions: bool = True, device: Device = None
    ) -> dict:
        """Install an APK (host path) on the device."""
        return await act(
            device, "install_app", path, replace=replace, grant_permissions=grant_permissions
        )

    @mcp.tool(tags={"write"})
    async def uninstall_app(app_id: str, device: Device = None) -> dict:
        """Uninstall an app."""
        return await act(device, "uninstall_app", app_id)

    @mcp.tool(tags={"write"})
    async def grant_permission(package: str, permission: str, device: Device = None) -> dict:
        """Grant a runtime permission (android.permission.*) to an app."""
        await call(device, "grant_permission", package, permission)
        return {"ok": True, "package": package, "permission": permission}

    @mcp.tool(tags={"write"})
    async def open_deep_link(
        deep_link: str,
        package_name: str | None = None,
        action: str | None = None,
        device: Device = None,
    ) -> dict:
        """Dispatch a deep link / intent (default action VIEW), optionally pinned to a package."""
        return await act(
            device, "open_deep_link", deep_link, package_name=package_name, action=action
        )

    @mcp.tool(tags={"write"})
    async def execute_script(js: str, device: Device = None) -> Any:
        """Run JavaScript in the foreground browser page and return its JSON result."""
        return await call(device, "execute_script", js)

    @mcp.tool(tags={"read"})
    async def get_clipboard(device: Device = None) -> str:
        """The clipboard's text (Android needs the Mobilerun Keyboard as the active IME)."""
        return await call(device, "get_clipboard")

    @mcp.tool(tags={"write"})
    async def set_clipboard(value: str, device: Device = None) -> dict:
        """Put text on the clipboard."""
        await call(device, "set_clipboard", value)
        return {"ok": True, "chars": len(value)}
