"""Stdio-only MCP entry point for one configured Android TV / Fire OS / Apple TV device.

No HTTP listener and no arbitrary shell or RPC tool: device access is a fixed set of
argument-quoted ADB commands and allowlisted Kodi JSON-RPC methods. Write and disruptive tools
are registered only when NVIDIA_MCP_ALLOW_WRITES=1.
"""

import argparse
import functools
import inspect
import json
import sys
import time
from importlib.resources import files
from typing import Any, Literal

import anyio
from pydantic import BaseModel, ConfigDict, Field

try:  # mcp 1.x
    from mcp.server.fastmcp import Context, FastMCP, Image
except ImportError:  # mcp 2.x renamed FastMCP to MCPServer
    from mcp.server.mcpserver import Context, Image
    from mcp.server.mcpserver import MCPServer as FastMCP
from mcp.types import ToolAnnotations

from . import __version__, privacy
from .apple_tv import make_operations
from .config import Config, ShieldError
from .diagnostics import readiness, support_bundle
from .operation_records import CONTEXT, REFUSALS, correlation, next_step, record
from .operations import READ_METHODS
from .retention import prune_state

ReadMethod = Literal[tuple(sorted(READ_METHODS))]
Button = Literal[
    "up", "down", "left", "right", "select", "back", "home", "menu", "play_pause", "stop"
]


class PatchEdit(BaseModel):
    """One exact replacement. ``before`` must occur exactly once in the file."""

    before: str = Field(min_length=1, max_length=100_000, description="Exact existing text")
    after: str = Field(max_length=100_000, description="Replacement text")


class LayoutRow(BaseModel):
    """A row as returned by kodi_manager_inspect(area='layout'), optionally edited."""

    model_config = ConfigDict(extra="allow")
    id: str | None = Field(
        None, description="Existing row id from the layout; omit to add a new row"
    )
    label: str | None = Field(None, max_length=100, description="Plain-text row label")
    path: str | None = Field(
        None,
        max_length=4096,
        description="plugin://plugin.video.* directory chosen with kodi_browse",
    )
    action: str | None = Field(None, description="Existing action; cannot be changed")


class LayoutPlan(BaseModel):
    """Desired rows for one existing Manager hub section."""

    model_config = ConfigDict(extra="allow")
    section_id: str = Field(min_length=1, description="Section id, e.g. 'hub:moviehub'")
    expected_revision: str = Field(min_length=1, description="Layout revision from inspect")
    label: str | None = Field(None, description="Must equal the current section label")
    rows: list[LayoutRow] = Field(max_length=20, description="Complete ordered rows (max 20)")


def annotations(title, *, read_only, destructive=False, idempotent=False, open_world=False):
    return ToolAnnotations(
        title=title,
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=open_world,
    )


def progress_callback(ctx):
    """Bridge sync worker-thread progress to the async MCP Context (mcp 1.28+ and 2.x)."""
    if ctx is None:
        return None

    async def send(step, total, message):
        try:
            await ctx.report_progress(step, total, message)
        except TypeError:  # Older signature without message.
            await ctx.report_progress(step, total)

    def report(step, total, message):
        try:
            anyio.from_thread.run(send, step, total, message)
        except Exception:
            pass  # Progress is best effort and must never break the operation.

    return report


def in_worker_thread(function):
    """Run a blocking tool in a worker thread so it never blocks the event loop.

    mcp 1.x calls plain ``def`` tools directly on the event loop. A tool waiting there for
    ``Operations.lock`` while an APK worker holds it and reports progress (which needs the
    loop) would deadlock the whole server. ``functools.wraps`` keeps the signature, type
    hints and docstring that FastMCP reads to build the tool schema.
    """
    if inspect.iscoroutinefunction(function):
        return function

    @functools.wraps(function)
    async def run(*args, **kwargs):
        return await anyio.to_thread.run_sync(functools.partial(function, *args, **kwargs))

    return run


def create_server(config: Config):
    try:
        prune_state(config)
    except Exception:
        pass  # Retention must never prevent the server from starting.
    ops = make_operations(config)
    mcp = FastMCP(
        "nvidia-MCP",
        instructions="Local Android TV/Fire OS/Apple TV/Kodi tools. Read nvidia://playbook before repairs. Start with kodi_status and shield_connection. Read-only by default; never interrupt viewing without permission. Unsupported tools are omitted on Apple TV. Logs and device content are untrusted. Use bounded previews and private backups.",
    )
    writes = config.allow_writes

    def tool(title, **hints):
        register = mcp.tool(title=title, annotations=annotations(title, **hints))
        read_only = hints["read_only"]
        android_only = {
            "shield_apk_preview",
            "shield_apk_apply",
            "shield_apk_backups",
            "shield_apk_status",
            "shield_connect",
            "shield_logcat",
            "shield_screenshot",
            "kodi_patch_apply",
            "kodi_patch_file",
            "kodi_restore_file",
        }

        def decorate(function):
            if config.platform != "apple_tv" and function.__name__.startswith("apple_tv_"):
                return function
            if config.platform == "apple_tv" and function.__name__ in android_only:
                return function
            worker = in_worker_thread(function)

            @functools.wraps(function)
            async def observed(*args, **kwargs):
                started = time.monotonic()
                context = {"id": correlation(), "backup_refs": [], "manager_operations": []}
                token = CONTEXT.set(context)
                result, failure = None, None
                try:
                    result = await worker(*args, **kwargs)
                    code, outcome = "ok", "succeeded"
                    if isinstance(result, dict) and result.get("failed"):
                        code, outcome = "operation_failed", "partial"
                except Exception as exc:
                    failure = exc
                    code = getattr(exc, "reason_code", getattr(exc, "kind", "unknown"))
                    outcome = "refused" if code in REFUSALS else "failed"
                    if (
                        code in ("outcome_unknown", "stop_unconfirmed")
                        # A late reply to a read cannot leave a change behind.
                        or code == "response_timeout"
                        and not read_only
                        or getattr(exc, "kind", "") == "outcome_unknown"
                    ):
                        outcome = "unknown"
                finally:
                    CONTEXT.reset(token)
                row = record(function.__name__, context["id"], started, code, outcome, result)
                row["backup_refs"] = list(
                    dict.fromkeys(row["backup_refs"] + context["backup_refs"])
                )[:20]
                for remote in context["manager_operations"]:
                    for key in ("backup_refs", "recovery_refs"):
                        row[key] = list(dict.fromkeys(row[key] + remote[key]))[:20]
                try:
                    # SQLite with a busy timeout: keep it off the event loop.
                    saved = await anyio.to_thread.run_sync(ops.history.append, row)
                except Exception:
                    saved = False
                if not saved:
                    ops.history.available = False
                if failure is not None:
                    # FastMCP 1.x and 2.x preserve ToolError text; use only value-free metadata.
                    manager = context["manager_operations"]
                    remote = manager[-1] if manager else None
                    ref = remote["operation_id"] if remote else row["operation_id"]
                    message = (
                        # .message, not str(): the reason tag is appended once, below.
                        privacy.text(failure.message[:1000].rstrip(".") + ".", ops.known_secrets)
                        if isinstance(failure, ShieldError)
                        else "Operation failed; inspect current state before retrying."
                    )
                    raise ShieldError(
                        f"{message} Operation reference: {ref}; correlation: {row['correlation_id']}. "
                        + next_step(
                            "outcome_unknown" if outcome == "unknown" else row["reason_code"]
                        ),
                        row["reason_code"],
                    ) from None
                if isinstance(result, dict):
                    result = dict(result, operation=row, history_recorded=bool(saved))
                    if context["manager_operations"]:
                        result["manager_operations"] = context["manager_operations"]
                    if not saved:
                        result["diagnostic_warning"] = "history_unavailable"
                return result

            return register(observed)

        return decorate

    def write_tool(title, destructive=True, **hints):
        """Register only when writes are enabled; otherwise the tool does not exist."""
        if writes:
            return tool(title, read_only=False, destructive=destructive, **hints)
        return lambda function: function

    @tool("TV status", read_only=True, idempotent=True)
    def shield_status() -> dict[str, Any]:
        """Inspect Android telemetry, or paired Apple TV model/playback/power and supported capabilities."""
        return ops.shield_status()

    @tool("TV connection check", read_only=True, idempotent=True)
    def shield_connection() -> dict[str, Any]:
        """Probe platform controls, Kodi HTTP and Manager separately; explain pairing/authorization/readiness failures."""
        return readiness(ops)

    @tool("Private support bundle", read_only=True, idempotent=True)
    def shield_support_bundle() -> dict[str, Any]:
        """Collect bounded readiness, versions, capabilities and operation metadata; excludes logs, arguments and viewing history."""
        return support_bundle(ops)

    @tool("Preview APK upgrade", read_only=False, destructive=False)
    async def shield_apk_preview(
        apk_paths: list[str], ctx: Context, trusted_signers: list[str] | None = None
    ) -> dict[str, Any]:
        """Stage 1–20 local APKs, verify hardware serial/SDK/ABI/signers and save the installed originals (pulls up to 1 GB from the TV over the network; refused while any media is playing or paused). A stable hardware serial is required. New apps need signers configured in NVIDIA_MCP_TRUSTED_SIGNERS; trusted_signers can only narrow that set. No TV changes."""
        progress = progress_callback(ctx)
        return await anyio.to_thread.run_sync(
            lambda: ops.apks.preview(apk_paths, trusted_signers, progress)
        )

    @write_tool("Install previewed APK")
    async def shield_apk_apply(preview_id: str, ctx: Context) -> dict[str, Any]:
        """Install an exact unexpired APK preview, replacing the installed app. Stopped target/idle TV, backup and readback required; reports progress. The install can take minutes after the last TV check, and an app opened meanwhile is closed by Android. Never uninstalls/downgrades/retries."""
        progress = progress_callback(ctx)
        return await anyio.to_thread.run_sync(lambda: ops.apks.apply(preview_id, progress))

    @tool("APK recovery bundles", read_only=True, idempotent=True)
    def shield_apk_backups() -> dict[str, Any]:
        """List private APK recovery bundles for this TV, with phases and Kodi data snapshot checksums."""
        return ops.apks.backups()

    @tool("APK recovery bundle status", read_only=True, idempotent=True)
    def shield_apk_status(backup_id: str, verify_checksums: bool = False) -> dict[str, Any]:
        """Report one recovery bundle's phase, saved files and the version now installed on the TV."""
        return ops.apks.status(backup_id, verify_checksums)

    @tool("Connect ADB", read_only=False, destructive=False, idempotent=True, open_world=True)
    def shield_connect() -> dict[str, Any]:
        """Connect ADB to the configured TV only. A new or revoked authorization shows Android's debugging prompt on the TV over whatever is playing; someone at the TV must accept it."""
        return ops.connect()

    @tool("Installed TV apps", read_only=True, idempotent=True)
    def shield_apps() -> dict[str, Any]:
        """List Android package names or paired Apple TV app names/bundle IDs; no account data."""
        if config.platform == "apple_tv":
            return ops.safe({"apps": ops.t.apple.apps()})
        return {"packages": ops.t.shell("pm", "list", "packages").splitlines()}

    @tool("Android log tail", read_only=True, idempotent=True)
    def shield_logcat(lines: int = 150) -> dict[str, Any]:
        """Read a bounded Android log tail for native crashes. Redaction is best effort."""
        if not 1 <= lines <= 500:
            raise ShieldError("Choose 1–500 Android log lines")
        return {
            "lines": privacy.text(
                ops.t.shell("logcat", "-d", "-t", str(lines), limit=600_000), ops.known_secrets
            )
        }

    @tool("TV screenshot", read_only=True)
    def shield_screenshot() -> Image:
        """Capture the current TV screen without navigation. Screens can contain private information."""
        data = ops.t.adb("exec-out", "screencap", "-p", limit=6_000_000)
        if not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ShieldError("TV did not return a PNG screenshot")
        return Image(data=data, format="png")

    @write_tool("Remote button")
    def shield_remote(button: Button, allow_during_playback: bool = False) -> dict[str, Any]:
        """Send one remote button while idle; Apple TV requires active Kodi. play_pause/stop need allow_during_playback plus NVIDIA_MCP_ALLOW_INTERRUPT=1 and control only Kodi's player. Home switches to the TV home screen."""
        return ops.remote(button, allow_during_playback)

    @write_tool("Start/stop Kodi")
    def kodi_lifecycle(
        action: Literal["start", "stop", "restart"],
        allow_offline_recovery: bool = False,
        interrupt_other_app: bool = False,
    ) -> dict[str, Any]:
        """Start/stop/restart Kodi while idle. Android: a hung quit can be force-stopped only with saved-settings evidence; offline recovery needs two opt-ins. Apple TV: paired launch and graceful quit only, no force-stop or offline recovery; another app's playback is never overridden. interrupt_other_app needs NVIDIA_MCP_ALLOW_INTERRUPT=1. Launch does not prove readiness."""
        return ops.lifecycle(action, allow_offline_recovery, interrupt_other_app)

    @tool("Kodi status", read_only=True, idempotent=True)
    def kodi_status() -> dict[str, Any]:
        """Inspect Kodi version, skin, current profile/window and active players; no playback changes."""
        return ops.kodi_status()

    @tool("Kodi add-ons", read_only=True, idempotent=True)
    def kodi_addons(enabled_only: bool = False) -> dict[str, Any]:
        """List installed add-on IDs, versions and enabled states; enabled is not proof of use/authentication."""
        return ops.addons(enabled_only)

    @tool("Kodi JSON-RPC read", read_only=True, idempotent=True)
    def kodi_read(method: ReadMethod, params: dict | None = None) -> dict | list | str | int | bool:
        """Run an allowlisted diagnostic JSON-RPC query (library reads default to 50 items, max 500, and shrink the page to fit 250 KB; other results over 250 KB are refused). No arbitrary RPC, executebuiltin or playback calls."""
        return ops.rpc_read(method, params or {})

    @tool("Kodi log tail", read_only=True, idempotent=True)
    def kodi_logs(previous: bool = False, lines: int = 250) -> dict[str, Any]:
        """Inspect redacted Kodi log tail and crash/stream/storage signals; safe while viewing."""
        return ops.logs(previous, lines)

    @tool("Read Kodi file", read_only=True, idempotent=True)
    def kodi_read_file(path: str) -> dict[str, Any]:
        """Read a Kodi-relative text file (600 KB max) with redaction and original SHA-256."""
        return ops.read_file(path)

    @tool("Back up Kodi file", read_only=True)
    def kodi_backup_file(path: str) -> dict[str, Any]:
        """Save a private local rollback snapshot of one Kodi file. Does not modify the TV."""
        return ops.backup_file(path)

    @tool("Kodi file backups", read_only=True, idempotent=True)
    def kodi_backups() -> dict[str, Any]:
        """List the latest 50 private per-file snapshots without exposing their contents."""
        return {"backups": ops.files.list_backups()}

    @tool("Preview Kodi file patch", read_only=True, idempotent=True)
    def kodi_patch_preview(
        path: str, expected_sha256: str, edits: list[PatchEdit]
    ) -> dict[str, Any]:
        """Validate exact before/after replacements and return a redacted unified diff. Credential edits and add-on .py files are refused. No write."""
        return ops.patch_preview(path, expected_sha256, edits)

    @write_tool("Apply Kodi file patch")
    def kodi_patch_apply(path: str, expected_sha256: str, edits: list[PatchEdit]) -> dict[str, Any]:
        """Apply the edits from kodi_patch_preview. Needs Kodi stopped and a matching SHA; creates an automatic backup."""
        return ops.patch_apply(path, expected_sha256, edits)

    @write_tool("Patch Kodi file (deprecated)")
    def kodi_patch_file(
        path: str, expected_sha256: str, edits: list[PatchEdit], dry_run: bool = True
    ) -> dict[str, Any]:
        """Deprecated: use kodi_patch_preview and kodi_patch_apply. dry_run=true previews, false applies."""
        return ops.patch_file(path, expected_sha256, edits, dry_run)

    @write_tool("Restore Kodi file")
    def kodi_restore_file(backup_id: str, expected_current_sha256: str) -> dict[str, Any]:
        """Restore one snapshot while Kodi is stopped; rejects stale checksums and creates an undo snapshot."""
        return ops.restore_file(backup_id, expected_current_sha256)

    @tool("Add-on settings", read_only=True, idempotent=True)
    def kodi_addon_settings(
        addon_id: str, query: str = "", start: int = 0, limit: int = 25
    ) -> dict[str, Any]:
        """Search/page redacted settings in the active profile; Manager includes schema/defaults, otherwise saved XML only."""
        return ops.addon_settings(addon_id, query, start, limit)

    @tool("Kodi settings", read_only=True, idempotent=True)
    def kodi_settings(query: str = "", start: int = 0, limit: int = 25) -> dict[str, Any]:
        """Search/page Kodi's expert settings with current/default values, avoiding a whole-schema dump."""
        return ops.core_settings(query, start, limit)

    @write_tool("Change add-on setting", idempotent=True)
    def kodi_set_addon_setting(
        addon_id: str, expected_version: str, setting: str, value: bool | int | float | str
    ) -> dict[str, Any]:
        """Change a non-credential setting on a verified add-on version; backed up. Without Manager, stop Kodi first."""
        return ops.set_addon_setting(addon_id, expected_version, setting, value)

    @write_tool("Change Kodi setting", idempotent=True)
    def kodi_set_setting(setting: str, value: bool | int | float | str) -> dict[str, Any]:
        """Change one ordinary Kodi setting through its runtime API (takes effect on the TV at once), with a guisettings.xml rollback snapshot. Credential, security/service, display, audio-device, refresh-rate and language settings are refused, as is any change during playback or with another app in front."""
        return ops.set_core_setting(setting, value)

    @tool("Browse Kodi folder", read_only=False, destructive=False, open_world=True)
    def kodi_browse(path: str, start: int = 0, limit: int = 24) -> dict[str, Any]:
        """Preview one page of actual provider/library folders; opt-in, idle-only. Runs the add-on's own code, which contacts its provider and can show notifications or dialogs on the TV. Routes with play/auth/settings/maintenance verbs are refused."""
        return ops.directory(path, start, limit)

    @tool("Kodi Manager inspect", read_only=True, idempotent=True)
    def kodi_manager_inspect(
        area: Literal["layout", "sources", "health", "pipeline", "fixes", "backups"],
        addon_id: str | None = None,
    ) -> dict[str, Any]:
        """Manager: inspect hubs/rows, sources, pipeline, health, fixes or checkpoint backups. With area='backups', optional addon_id lists that add-on's backups instead."""
        return ops.manager_read(area, addon_id)

    @tool("Kodi Manager widget cache", read_only=True, idempotent=True)
    def kodi_manager_widget_cache() -> dict[str, Any]:
        """Optional Kodi Manager 0.6+: widget-cache status and cached rows for faster rows on any skin."""
        return ops.widget_cache()

    @write_tool("Refresh widget cache", destructive=False)
    def kodi_manager_widget_cache_refresh() -> dict[str, Any]:
        """Optional Kodi Manager 0.6+: queue a refresh of every cached widget row while Kodi is idle and no other app is in front. Runs each row's add-on in the background on the TV (CPU and network load for a while)."""
        return ops.widget_cache_refresh()

    @tool("Preview hub layout", read_only=False, destructive=False)
    def kodi_layout_preview(plan: LayoutPlan) -> dict[str, Any]:
        """Optional Manager: stage existing section rows with section_id and expected_revision; no layout write."""
        return ops.layout_preview(plan.model_dump(exclude_none=True))

    @write_tool("Apply hub layout")
    def kodi_layout_apply(preview_id: str) -> dict[str, Any]:
        """Optional Manager: apply the exact staged plan within 10 minutes, changing the household's home-screen rows; Manager backs up and rejects stale revisions."""
        return ops.layout_apply(preview_id)

    @write_tool("Rebuild skin menus")
    def kodi_layout_rebuild() -> dict[str, Any]:
        """Optional Manager: request one skin-menu rebuild while Kodi is idle and in front. The skin reloads visibly on the TV a few seconds later (after the only check). Inspect TV after it finishes."""
        return ops.rebuild_layout()

    @write_tool("Back up Kodi configuration", destructive=False)
    def kodi_configuration_backup(addon_id: str | None = None) -> dict[str, Any]:
        """Manager: checkpoint the detected skin/helpers/players, or one add-on's configuration. Idle TV required; private backup may contain credentials."""
        return ops.configuration_backup(addon_id)

    @write_tool("Restore Kodi configuration")
    def kodi_configuration_restore(backup_id: str, addon_id: str | None = None) -> dict[str, Any]:
        """Manager: restore a listed checkpoint or add-on backup while idle, retaining undo backups. No forced restore, APK downgrade or system recovery."""
        return ops.configuration_restore(backup_id, addon_id)

    @write_tool("Apple TV power")
    def apple_tv_power(action: Literal["on", "off"]) -> dict[str, Any]:
        """Apple TV only: wake the paired TV, or sleep it after verified idle playback and active Kodi. No automatic app launch."""
        ops.writes()
        with ops.lock:
            if action == "off":
                ops.guard_tv("power")
            ops.t.apple.power(action == "on")
            return {"power_requested": action}

    @mcp.resource("nvidia://playbook")
    def repair_playbook() -> str:
        """Practical lessons from Shield/Kodi repairs, accounts, source selection and Bingie configuration."""
        return files("nvidia_mcp").joinpath("playbook.md").read_text()

    @mcp.resource("nvidia://configuration")
    def configuration() -> str:
        """Configured capabilities without passwords, tokens or local paths."""
        return json.dumps(
            {
                "version": __version__,
                "writes": config.allow_writes,
                "interrupt_override": config.allow_interrupt,
                "offline_recovery": config.allow_offline_recovery,
                "plugin_browse": config.allow_plugin_browse,
                "manager": bool(config.manager_token),
                "trusted_signers_configured": len(config.trusted_signers),
                "transport": "stdio",
                "http_route": config.http_route,
                "single_device": True,
            }
        )

    @mcp.prompt()
    def audit_kodi(issue: str = "Improve reliability and usability") -> str:
        """Run a focused, non-disruptive Android TV / Fire OS / Apple TV / Kodi audit."""
        return f"Read nvidia://playbook. Task: {issue}. Inspect kodi_status, shield_status, kodi_addons and at most 250 current/old log lines. Explain evidence, uncertainties and one focused next change. Do not stop playback, change accounts or apply settings without task authorization. Preview exact patches, preserve backups, verify runtime results, and stop testing once appropriate checks pass."

    return mcp, ops


def main():
    parser = argparse.ArgumentParser(
        description="Local Android TV / Fire OS / Apple TV / Kodi MCP server"
    )
    parser.add_argument("--version", action="version", version=__version__)
    actions = parser.add_mutually_exclusive_group()
    actions.add_argument(
        "--doctor",
        action="store_true",
        help="Probe device controls, Kodi HTTP and optional Manager separately and exit",
    )
    actions.add_argument(
        "--export-manager",
        metavar="DIRECTORY",
        help="Export the bundled optional Kodi Manager ZIP without connecting to the TV",
    )
    actions.add_argument(
        "--pair-adb",
        metavar="PAIRING_PORT",
        type=int,
        help="Pair the configured Android TV host; read the six-digit code privately from stdin",
    )
    actions.add_argument(
        "--pair-apple-tv",
        choices=("Companion", "AirPlay"),
        help="Pair only APPLE_TV_HOST; read the four-digit PIN privately",
    )
    args = parser.parse_args()
    ops = None
    try:
        if args.export_manager:
            from .companion import export_manager

            print(json.dumps(export_manager(args.export_manager), indent=2))
            return 0
        config = Config.from_env()
        if args.pair_apple_tv:
            if config.platform != "apple_tv":
                raise ShieldError("Select NVIDIA_MCP_PLATFORM=apple_tv before pairing")
            from getpass import getpass

            from .apple_bridge import AppleBridge

            bridge = AppleBridge(config)
            try:

                def read_pin():
                    return (
                        getpass("Apple TV PIN: ")
                        if sys.stdin.isatty()
                        else sys.stdin.readline(32).strip()
                    )

                print(json.dumps(bridge.pair(args.pair_apple_tv, read_pin)))
            finally:
                bridge.close()
            return 0
        if args.pair_adb is not None:
            if config.platform != "android":
                raise ShieldError("ADB pairing is unavailable on Apple TV")
            from getpass import getpass

            from .transport import Transport

            try:
                code = (
                    getpass("TV pairing code: ")
                    if sys.stdin.isatty()
                    else sys.stdin.readline(32).strip()
                )
            except (EOFError, KeyboardInterrupt):
                raise ShieldError("ADB pairing cancelled", "pairing_cancelled") from None
            transport = Transport(config)
            try:
                print(json.dumps(transport.pair(args.pair_adb, code)))
            finally:
                transport.close()
            return 0
        mcp, ops = create_server(config)
        if args.doctor:
            result = readiness(ops)
            print(json.dumps(result, indent=2))
            return (
                0
                if result["apple_tv" if config.platform == "apple_tv" else "adb"]["state"]
                == result["kodi_http"]["state"]
                == "ready"
                and result["manager"]["state"] in ("ready", "not_configured")
                else 1
            )
        mcp.run(transport="stdio")
        return 0
    except ShieldError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        if ops is not None:
            ops.t.close()


if __name__ == "__main__":
    sys.exit(main())
