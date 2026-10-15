"""Opt-in Apple TV operations; reuse Kodi/Manager contracts and Shield defaults."""

import base64
import re
import time
from urllib.parse import urlencode

from .apple_bridge import AppleBridge
from .config import ShieldError
from .files import MAX_FILE, Files, digest, relative
from .operations import MEDIA_KEYS, Operations
from .transport import Transport


def unsupported(*args, **kwargs):
    raise ShieldError(
        "This operation requires Android ADB and is unavailable on Apple TV", "unsupported"
    )


class AppleTransport(Transport):
    def __init__(self, config):
        if config.http_route != "direct":
            raise ShieldError("Apple TV requires direct HTTP; no ADB forwarding", "unsupported")
        super().__init__(config, "direct")
        self.apple = AppleBridge(config)

    adb = shell = exec_out = stream_to_file = is_file = unsupported

    def close(self):
        try:
            self.apple.close()
        finally:
            super().close()


class AppleFiles(Files):
    def __init__(self, transport, state_reader):
        super().__init__(transport)
        self.state_reader = state_reader

    def device_id(self):
        state = self.state_reader()
        identifier = state.get("device_id")
        if (
            state.get("platform") != "tvos"
            or not isinstance(identifier, str)
            or not re.fullmatch(r"[a-f0-9]{32}", identifier)
        ):
            raise ShieldError(
                "Requires tvOS Kodi Manager 0.7.16+ with valid device identity", "unsupported"
            )
        return "apple_" + identifier

    def read(self, path):
        path = relative(path)
        before = self.state_reader()
        value = self.t.manager(
            "/api/portable/file?"
            + urlencode(
                {
                    "path": path,
                    "device_id": before["device_id"],
                    "profile_root": before["profile_root"],
                }
            )
        )
        if isinstance(value, dict) and not {"device_id", "profile_root"} <= value.keys():
            raise ShieldError(
                "File reads require Kodi Manager 0.7.17+ ownership metadata", "unsupported"
            )
        try:
            if (
                value["path"] != path
                or value["device_id"] != before["device_id"]
                or value["profile_root"] != before["profile_root"]
                or not isinstance(value["base64"], str)
                or len(value["base64"]) > 800_000
            ):
                raise ValueError()
            data = base64.b64decode(value["base64"], validate=True)
            if (
                len(data) > MAX_FILE
                or type(value["bytes"]) is not int
                or value["bytes"] != len(data)
                or value["sha256"] != digest(data)
            ):
                raise ValueError()
            after = self.state_reader()
            if before.get("device_id") != after.get("device_id") or before.get(
                "profile_root"
            ) != after.get("profile_root"):
                raise ShieldError(
                    "Device/profile changed during file read; inspect again", "device_mismatch"
                )
            return data
        except (ValueError, KeyError, TypeError):
            raise ShieldError(
                "Manager file response failed size/checksum validation", "invalid_response"
            ) from None

    write = location = tail = unsupported


class AppleOperations(Operations):
    def __init__(self, transport):
        super().__init__(transport)
        self.files = AppleFiles(transport, self.state)
        self.apple_plans = {}
        self.expected_manager_id = None

    def state(self):
        value = self.t.manager("/api/portable/state")
        if not isinstance(value, dict):
            raise ShieldError("Manager device state is unreadable", "invalid_response")
        root = value.get("profile_root")
        if (
            not isinstance(root, str)
            or not (root == "userdata" or root.startswith("userdata/profiles/"))
            or not isinstance(value.get("profile"), str)
        ):
            raise ShieldError("Manager active profile is unreadable", "invalid_response")
        relative(root)
        if value.get("active") is not None and type(value.get("active")) is not bool:
            raise ShieldError(
                "Kodi is not confirmed active; invalid native state", "invalid_response"
            )
        identifier = value.get("device_id")
        if (
            value.get("platform") != "tvos"
            or not isinstance(identifier, str)
            or not re.fullmatch(r"[a-f0-9]{32}", identifier)
        ):
            raise ShieldError("Apple TV mode requires tvOS Kodi Manager 0.7.16+", "unsupported")
        with self.lock:
            if self.expected_manager_id is not None and identifier != self.expected_manager_id:
                raise ShieldError(
                    "Manager instance changed at the configured address; reconnect and inspect",
                    "device_mismatch",
                )
            self.expected_manager_id = identifier
        return value

    def media_idle(self):
        state = self.t.apple.snapshot()
        if state.get("playback") in ("playing", "paused", "loading", "seeking"):
            raise ShieldError(
                "Apple TV media is playing or paused; no disruptive action performed", "playing"
            )
        if state.get("playback") not in ("idle", "stopped") or state.get("power") != "on":
            raise ShieldError(
                "Apple TV playback/power state is unknown or asleep", "playback_unknown"
            )
        return state

    def guard_tv(self, operation, **kwargs):
        self.media_idle()
        state = self.state()
        if state.get("active") is not True:
            raise ShieldError(
                "Kodi is not confirmed active on Apple TV; open it on the TV first",
                "foreground_unknown",
            )
        players = self.t.rpc("Player.GetActivePlayers")
        if not isinstance(players, list):
            raise ShieldError("Kodi playback state is unreadable", "playback_unknown")
        if players:
            raise ShieldError("Kodi is playing or paused; wait until viewing finishes", "playing")
        return state

    def viewing_state(self):
        try:
            value = self.guard_tv("inspect")
            return {
                "state": "idle",
                "verdict": "idle",
                "foreground": "Kodi",
                "device_id": value["device_id"],
            }
        except ShieldError as exc:
            return {
                "state": "playing" if exc.kind == "playing" else "unknown",
                "verdict": "playing" if exc.kind == "playing" else "unknown",
                "reason": exc.message,
            }

    def shield_status(self):
        result = {"platform": "apple_tv", "capabilities": apple_capabilities(self.c)}
        try:
            result["device"] = self.t.apple.snapshot()
        except ShieldError as exc:
            result["device"] = {"unavailable": exc.kind, "message": exc.message}
        return self.safe(result)

    def kodi_status(self):
        result = super().kodi_status()
        result["capabilities"].update(apple_capabilities(self.c))
        result["capabilities"]["file_access"] = (
            "Manager active-profile VFS" if self.c.manager_token else "unavailable"
        )
        return result

    def profile_userdata(self):
        value = self.state().get("profile_root")
        if not isinstance(value, str) or not (
            value == "userdata" or value.startswith("userdata/profiles/")
        ):
            raise ShieldError("Manager active profile path is unreadable", "invalid_response")
        return relative(value)

    def logs(self, previous=False, lines=250):
        if previous:
            raise ShieldError(
                "Previous log requires Android file access; current log is available", "unsupported"
            )
        if not 1 <= lines <= 1000:
            raise ShieldError("Choose 1–1000 log lines")
        result = self.t.manager("/api/kodi/logs")
        return self.safe(
            {
                "lines": result.get("lines", [])[-min(lines, 500) :],
                "note": "Manager's bounded redacted current Kodi log",
            }
        )

    def layout_preview(self, plan):
        with self.lock:
            state = self.guard_tv("layout")
            result = super().layout_preview(plan)
            self.apple_plans = {
                key: value for key, value in self.apple_plans.items() if key in self.plans
            }
            self.apple_plans[result["preview_id"]] = (state["device_id"], state.get("profile_root"))
            return result

    def layout_apply(self, preview_id):
        with self.lock:
            state = self.guard_tv("layout")
            if self.apple_plans.get(preview_id) != (state["device_id"], state.get("profile_root")):
                raise ShieldError(
                    "Preview belongs to another Apple TV or expired; preview again",
                    "device_mismatch",
                )
            result = super().layout_apply(preview_id)
            self.apple_plans.pop(preview_id, None)
            return result

    def remote(self, button, allow_during_playback=False):
        with self.lock:
            return self._remote(button, allow_during_playback)

    def _remote(self, button, allow_during_playback):
        self.writes()
        if button in MEDIA_KEYS:
            if allow_during_playback:
                self.require_interrupt_opt_in("allow_during_playback")
            if not allow_during_playback or self.state().get("active") is not True:
                raise ShieldError(
                    "Playback controls require explicit interruption permission and active Kodi"
                )
            players = self.t.rpc("Player.GetActivePlayers")
            if (
                not isinstance(players, list)
                or len(players) != 1
                or not isinstance(players[0], dict)
            ):
                raise ShieldError("Exactly one Kodi player is required", "playback_unknown")
            player = players[0].get("playerid")
            if type(player) is not int:
                raise ShieldError("Kodi player is unreadable", "playback_unknown")
            method = "Player.PlayPause" if button == "play_pause" else "Player.Stop"
            self.t.rpc(method, {"playerid": player})
        else:
            self.guard_tv("remote")
            if button == "home":
                self.t.apple.button(button)
            else:
                methods = {
                    "up": "Input.Up",
                    "down": "Input.Down",
                    "left": "Input.Left",
                    "right": "Input.Right",
                    "select": "Input.Select",
                    "back": "Input.Back",
                    "menu": "Input.ContextMenu",
                }
                if button not in methods:
                    raise ShieldError("Unknown remote button")
                self.t.rpc(methods[button])
        return {"button": button, "platform": "apple_tv"}

    def lifecycle(self, action, allow_offline=False, interrupt_other_app=False):
        self.writes()
        if allow_offline:
            raise ShieldError("Apple TV has no offline force-stop recovery", "unsupported")
        with self.lock:
            self.media_idle()
            if action == "start":
                if interrupt_other_app:
                    self.require_interrupt_opt_in("interrupt_other_app")
                try:
                    active = self.state().get("active") is True
                except ShieldError as exc:
                    if exc.kind not in ("unreachable", "timeout"):
                        raise
                    active = False
                if not active and not interrupt_other_app:
                    raise ShieldError(
                        "Starting Kodi may switch apps; explicit interruption opt-in is required",
                        "other_app",
                    )
                if active:
                    return {"state": "already_active"}
                self.t.apple.launch(self.c.apple_kodi_app_id)
                return {
                    "state": "launch_requested",
                    "note": "Inspect Kodi startup; launch is not readiness",
                }
            if action not in ("stop", "restart"):
                raise ShieldError("Unknown Kodi lifecycle action")
            self.guard_tv("lifecycle")
            if action == "restart":
                self.t.apple.can_launch(self.c.apple_kodi_app_id)
            try:
                self.t.rpc("Application.Quit")
            except ShieldError as exc:
                # As on Android: no answer still means the quit request was sent.
                if exc.kind not in ("unreachable", "timeout", "response_timeout"):
                    raise
            end = time.monotonic() + self.quit_wait
            while time.monotonic() < end:
                try:
                    self.t.rpc("JSONRPC.Version")
                except ShieldError as exc:
                    if exc.kind in ("unreachable", "timeout"):
                        if action == "restart":
                            self.media_idle()
                            self.t.apple.launch(self.c.apple_kodi_app_id)
                        return {
                            "state": "restart_requested" if action == "restart" else "http_stopped",
                            "note": "HTTP disappearance does not prove process termination; tvOS has no force-stop recovery",
                        }
                    # A stalled answer while exiting is neither "still running" nor "gone".
                    if exc.kind != "response_timeout":
                        raise
                time.sleep(self.quit_poll)
            raise ShieldError(
                "Kodi still answers after quit; Apple TV force-stop is unavailable", "exit_hung"
            )

    stopped = connect = force_stop = unsupported

    def kodi_running(self):
        try:
            self.t.rpc("JSONRPC.Ping")
            return True
        except ShieldError as exc:
            if exc.kind in ("unreachable", "timeout"):
                return False
            raise


def apple_capabilities(config):
    return {
        "platform": "apple_tv",
        "adb": False,
        "apk_install": False,
        "offline_file_writes": False,
        "manager_required_for_skin": True,
        "paired_controls_configured": bool(config.apple_credentials),
        "physical_validation": False,
    }


def make_operations(config):
    if config.platform == "apple_tv":
        return AppleOperations(AppleTransport(config))
    if config.platform != "android":
        raise ShieldError("Unknown device platform")
    return Operations(Transport(config))
