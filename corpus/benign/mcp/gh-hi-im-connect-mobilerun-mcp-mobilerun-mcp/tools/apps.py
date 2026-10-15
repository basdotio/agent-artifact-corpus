"""Finding, launching and deep-linking apps."""

from __future__ import annotations

from fastmcp import FastMCP

from .. import catalog
from ..errors import fail
from ..observe import mutate
from ..parsers.intent_filters import deeplinks_from_filters, parse_activity_filters
from ..parsers.packages import rank_apps, resolve_app
from ..parsers.shortcuts import Shortcut, parse_shortcuts, split_uri
from ..parsers.system import is_chooser, parse_resolve_activity
from ..policy import check_app
from ..session import DeviceSession, Runtime
from ..shell import q, view_args
from .common import Device, enforce, get_session

PROBE_LIMIT = 12
BROWSERS = {
    "com.android.chrome",
    "org.chromium.webview_shell",
    "org.mozilla.firefox",
    "com.brave.browser",
    "com.opera.browser",
    "com.microsoft.emmx",
    "com.sec.android.app.sbrowser",
}
COLD_START_TIMEOUT = 30.0
BLOCKED_SCHEMES = ("intent:", "file:", "content:", "javascript:")
SOURCE_RANK = {"shortcut": 0, "resolved": 1, "catalog": 2, "discovered": 3}


async def resolve_component(session: DeviceSession, args: str) -> str | None:
    out = await session.shell(f"cmd package resolve-activity --brief {args}", check=False)
    return parse_resolve_activity(out)


async def start_intent(session: DeviceSession, args: str) -> str:
    out = await session.shell(f"am start {args}", check=False)
    if "Error" in out or "Exception" in out:
        fail(
            "unsupported",
            out.strip().splitlines()[-1][:200],
            "no installed app handles this intent",
        )
    return out


async def shortcuts(session: DeviceSession, package: str | None = None) -> list[Shortcut]:
    dump = await session.shell("dumpsys shortcut", timeout=60, check=False)
    return parse_shortcuts(dump, package)


async def launch(
    rt: Runtime,
    session: DeviceSession,
    package: str,
    label: str,
    activity: str | None = None,
    force: bool = True,
) -> dict:
    enforce(check_app(rt.config.policy, package, label))
    info = {"action": "launch_app", "package": package, "label": label}
    if not force:
        screen = await session.capture()
        if screen.phone.package == package:
            return {"ok": True, "already_foreground": True, **info}
    if not session.has_adb:
        return await mutate(
            session,
            lambda: session.start_app(package, activity),
            info,
            settle_timeout=COLD_START_TIMEOUT,
            expect_package=package,
        )
    if activity:
        component = activity if "/" in activity else f"{package}/{activity}"
    else:
        component = await resolve_component(
            session,
            f"-a android.intent.action.MAIN -c android.intent.category.LAUNCHER {q(package)}",
        )
    if not component or is_chooser(component):
        fail("app_not_found", f"{package} has no launcher activity", "is the app installed?")
    return await mutate(
        session,
        lambda: start_intent(session, f"-n {q(component)}"),
        {**info, "already_foreground": False},
        settle_timeout=COLD_START_TIMEOUT,
        expect_package=package,
    )


def register(mcp: FastMCP, rt: Runtime) -> None:
    async def label_of(session: DeviceSession, package: str) -> str:
        match = next((a for a in await session.apps() if a.package == package), None)
        return match.label if match else package

    @mcp.tool(tags={"write"})
    async def launch_app(
        app_name: str | None = None,
        package_name: str | None = None,
        force: bool = False,
        package: str | None = None,
        device: Device = None,
    ) -> dict:
        """Open an app by name (fuzzy) or exact package_name. An ambiguous name returns ranked
        candidates instead of guessing. If the app is already in the foreground it is left as is
        (already_foreground=true) unless force=true."""
        session = get_session(rt, device)
        package = package_name or package
        if package:
            return await launch(rt, session, package, await label_of(session, package), force=force)
        if not app_name:
            fail("invalid_argument", "give app_name or package_name")
        best, ranked = resolve_app(app_name, await session.apps())
        if best is None:
            if not ranked:
                fail(
                    "app_not_found",
                    f'no installed app matches "{app_name}"',
                    "try lookup_app or list_apps",
                )
            return {
                "ok": False,
                "ambiguous": True,
                "message": f'"{app_name}" matches several apps; call again with package_name=',
                "candidates": [{**a.to_dict(), "score": s} for a, s in ranked],
            }
        return await launch(rt, session, best.package, best.label, force=force)

    @mcp.tool(tags={"write"})
    async def start_app(
        app_id: str | None = None,
        activity: str | None = None,
        package: str | None = None,
        device: Device = None,
    ) -> dict:
        """Start an app by id (Android package / iOS bundle id), optionally a specific activity."""
        app_id = app_id or package
        if not app_id:
            fail("invalid_argument", "give app_id")
        session = get_session(rt, device)
        return await launch(rt, session, app_id, await label_of(session, app_id), activity)

    @mcp.tool(tags={"read"})
    async def lookup_app(
        app_name: str | None = None, query: str | None = None, limit: int = 5, device: Device = None
    ) -> dict:
        """Search installed apps by name or package; returns ranked candidates with scores."""
        name = app_name or query
        if not name:
            fail("invalid_argument", "give app_name")
        apps = await get_session(rt, device).apps()
        ranked = rank_apps(name, apps, limit)
        return {"query": name, "candidates": [{**a.to_dict(), "score": s} for a, s in ranked]}

    @mcp.tool(tags={"read"})
    async def list_apps(
        include_system_apps: bool = False,
        include_protected_apps: bool = False,
        system: bool = False,
        device: Device = None,
    ) -> dict:
        """List installed apps (user apps only unless include_system_apps=true).
        include_protected_apps is honoured on Mobilerun Cloud devices only (as in mobilerun-core)."""
        session = get_session(rt, device)
        system = system or include_system_apps
        if session.target.kind == "cloud":
            raw = await session.core.call(
                "list_apps",
                include_system_apps=system,
                include_protected_apps=include_protected_apps,
            )
            return {"count": len(raw), "apps": raw}
        apps = await session.apps()
        shown = [a.to_dict() for a in apps if system or not a.system]
        return {"count": len(shown), "apps": shown}

    async def probe(session: DeviceSession, entry: dict) -> dict:
        uri = entry.get("uri") or entry.get("example")
        if not uri:
            return entry
        component = await resolve_component(session, view_args(uri))
        resolved = bool(component) and not is_chooser(component)
        source = entry["source"]
        if resolved and source == "catalog":
            source = "resolved"
        return {**entry, "source": source, "resolved": resolved, "component": component}

    @mcp.tool(tags={"read"})
    async def list_app_deeplinks(
        package_name: str | None = None,
        app_name: str | None = None,
        package: str | None = None,
        device: Device = None,
    ) -> dict:
        """Deep links into an app, best first. source: shortcut (launcher shortcut,
        app-shortcut://pkg/id, open with open_deeplink) > resolved (curated and verified on this
        device) > catalog (curated) > discovered (declared by the app's intent filters)."""
        session = get_session(rt, device)
        package = package_name or package
        if not package:
            if not app_name:
                fail("invalid_argument", "give package_name or app_name")
            best, _ = resolve_app(app_name, await session.apps())
            if best is None:
                fail("app_not_found", f'cannot pick one app for "{app_name}"', "use lookup_app")
            package = best.package
        dump = await session.shell(f"dumpsys package {q(package)}", timeout=60, check=False)
        discovered = [
            {**link.to_dict(), "source": "discovered"}
            for link in deeplinks_from_filters(parse_activity_filters(dump))
        ]
        curated = [{**e, "source": "catalog"} for e in catalog.entries_for(package)]
        entries = curated + discovered
        probed = [await probe(session, e) for e in entries[:PROBE_LIMIT]] + entries[PROBE_LIMIT:]
        found = [s.to_dict() for s in await shortcuts(session, package)] + probed
        found.sort(key=lambda e: SOURCE_RANK.get(str(e.get("source")), 9))
        return {"package": package, "count": len(found), "deeplinks": found}

    async def find_shortcut(session: DeviceSession, uri: str) -> Shortcut:
        pkg, sid = split_uri(uri) or ("", "")
        match = next((s for s in await shortcuts(session, pkg) if s.id == sid), None)
        if match is None:
            fail(
                "unsupported", f"no launcher shortcut {uri}", "list_app_deeplinks shows valid ones"
            )
        return match

    @mcp.tool(tags={"read"})
    async def resolve_deeplink(uri: str, device: Device = None) -> dict:
        """Which app would open this URI (or intent action such as android.settings.WIFI_SETTINGS)?
        handler_kind: app | browser_only | none."""
        session = get_session(rt, device)
        if split_uri(uri):
            shortcut = await find_shortcut(session, uri)
            return {
                "uri": uri,
                "resolved": True,
                "handler_kind": "app",
                "package": shortcut.package,
                "component": shortcut.component or None,
            }
        component = await resolve_component(session, view_args(uri))
        if not component:
            return {"uri": uri, "resolved": False, "handler_kind": "none"}
        package = component.split("/")[0]
        browser_only = is_chooser(component) is False and package in BROWSERS
        return {
            "uri": uri,
            "resolved": not is_chooser(component),
            "handler_kind": "browser_only" if browser_only else "app",
            "component": component,
            "package": package,
            "needs_chooser": is_chooser(component),
        }

    @mcp.tool(tags={"write"})
    async def open_deeplink(
        uri: str,
        package_name: str | None = None,
        app_name: str | None = None,
        package: str | None = None,
        device: Device = None,
    ) -> dict:
        """Jump straight to a screen via a URI, an app-shortcut://pkg/id from list_app_deeplinks,
        or an intent action. package_name / app_name pin the target app. intent:, file:,
        content: and javascript: URIs are refused."""
        if uri.lower().startswith(BLOCKED_SCHEMES):
            fail("not_permitted", f"{uri.split(':', 1)[0]}: URIs are not allowed")
        session = get_session(rt, device)
        package = package_name or package
        if not package and app_name:
            best, _ = resolve_app(app_name, await session.apps())
            if best is None:
                fail("app_not_found", f'cannot pick one app for "{app_name}"', "use lookup_app")
            package = best.package
        if split_uri(uri):
            shortcut = await find_shortcut(session, uri)
            enforce(check_app(rt.config.policy, shortcut.package))
            return await mutate(
                session,
                lambda: start_intent(session, shortcut.am_args()),
                {"action": "open_deeplink", "uri": uri, "handled_by": shortcut.package},
                settle_timeout=COLD_START_TIMEOUT,
                expect_package=shortcut.package,
            )
        component = await resolve_component(session, view_args(uri, package))
        if not component:
            fail("unsupported", f"no app handles {uri}", "try list_app_deeplinks")
        target = component.split("/")[0]
        if not is_chooser(component):
            enforce(check_app(rt.config.policy, target))
        return await mutate(
            session,
            lambda: start_intent(session, view_args(uri, package)),
            {"action": "open_deeplink", "uri": uri, "handled_by": component},
            settle_timeout=COLD_START_TIMEOUT,
            expect_package=target,
        )
