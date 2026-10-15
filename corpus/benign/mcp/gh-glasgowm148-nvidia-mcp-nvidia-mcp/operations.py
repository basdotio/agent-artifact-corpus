"""Device operations. UI disruption and offline file changes have distinct guards."""

import ast
import difflib
import json
import re
import shlex
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath
from urllib.parse import parse_qs, unquote, urlsplit

from defusedxml.ElementTree import fromstring

from . import privacy
from .apks import ApkOperations
from .config import ShieldError
from .files import MAX_FILE, Files, digest, relative
from .operation_records import CONTEXT, History, correlation, record, references

READ_METHODS = {
    "JSONRPC.Version",
    "Application.GetProperties",
    "GUI.GetProperties",
    "Addons.GetAddonDetails",
    "Profiles.GetProfiles",
    "Profiles.GetCurrentProfile",
    "Player.GetActivePlayers",
    "Player.GetProperties",
    "Player.GetItem",
    "Settings.GetSettingValue",
    "Settings.GetSettings",
    "Settings.GetCategories",
    "Settings.GetSections",
    "XBMC.GetInfoLabels",
    "XBMC.GetInfoBooleans",
    "VideoLibrary.GetMovies",
    "VideoLibrary.GetTVShows",
    "VideoLibrary.GetSeasons",
    "VideoLibrary.GetEpisodes",
    "VideoLibrary.GetRecentlyAddedMovies",
    "VideoLibrary.GetRecentlyAddedEpisodes",
}
LIBRARY_DEFAULT = 50
LIBRARY_MAX = 500
# kodi_read results are model context; Settings.GetSettings alone is several hundred KB.
READ_MAX = 250_000
BUTTONS = {
    "up": "19",
    "down": "20",
    "left": "21",
    "right": "22",
    "select": "23",
    "back": "4",
    "home": "3",
    "menu": "82",
    "play_pause": "85",
    "stop": "86",
}
KODI = "org.xbmc.kodi"
# Dot-separated segments only: "." or ".." would be resolved as a URL path segment and
# reach a different Manager endpoint (or a different add-on folder).
ADDON_ID = re.compile(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)*")
# The single set of home-screen packages treated as "nothing else is being watched".
# Extend with NVIDIA_MCP_EXTRA_LAUNCHERS (comma-separated package names).
LAUNCHERS = frozenset(
    {
        "com.google.android.tvlauncher",
        "com.amazon.tv.launcher",
        "com.google.android.apps.tv.launcherx",
        "com.android.tv.launcher",
        "com.spocky.projengmenu",
    }
)
# Kodi core settings that weaken security, expose services or can leave the household TV
# blank, silent or unreadable with no way to undo it from the remote (rollback needs ADB).
# kodi_set_setting refuses them.
PROTECTED_PREFIXES = (
    "services.",  # web server, auth, ports, event server, zeroconf, UPnP, AirPlay, SMB...
    "videoscreen.",  # resolution, screen, refresh-rate whitelist, 3D/stereo, calibration
    "masterlock.",
    "system.",
    "debug.",
    "pvrparental.",
    "network.httpproxy",
    "network.usehttpproxy",
)
PROTECTED_SETTINGS = frozenset(
    {
        "addons.unknownsources",
        "addons.updatemode",
        "general.addonupdates",
        "lookandfeel.skin",
        "audiooutput.audiodevice",
        "audiooutput.passthroughdevice",
        "videoplayer.adjustrefreshrate",
        "locale.language",
    }
)
# Harmless exceptions inside protected prefixes.
UNPROTECTED_SETTINGS = frozenset({"debug.showloginfo"})


def protected_setting(setting, allowed=()):
    """True when a core setting is on the security/service denylist and not explicitly allowed."""
    name = setting.lower()
    if name in UNPROTECTED_SETTINGS or name in {a.lower() for a in allowed}:
        return False
    return name in PROTECTED_SETTINGS or name.startswith(PROTECTED_PREFIXES)


# kodi_browse refuses plugin routes whose path segments, query keys or values contain an
# action verb. Matching is per word (camelCase/snake_case/dotted split), by prefix.
UNSAFE_STEMS = (
    "play",
    "resolve",
    "toggle",
    "refresh",
    "clear",
    "clean",
    "delete",
    "remove",
    "install",
    "uninstall",
    "setting",
    "auth",
    "login",
    "logout",
    "maintenance",
    "manager",
    "rescan",
    "reset",
    "update",
    "input",
    "keyboard",
    "dialog",
    "context",
    "execute",
    "runscript",
    "download",
    "sync",
    "mark",
    "unmark",
    "rate",
    "subscribe",
    "unsubscribe",
    "favourite",
    "favorite",
)
UNSAFE_WORDS = frozenset({"sign", "signin", "signout", "signup", "run", "add", "rename", "edit"})
SAFE_WORDS = frozenset(
    {"playlist", "playlists", "author", "authors", "updated", "inputstream", "rated", "rating"}
)
# Display text, not routing; only their names are checked.
FREE_TEXT_KEYS = frozenset({"name", "title", "label", "plot", "tagline", "originaltitle"})


def unsafe_words(value):
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", unquote(value))
    return [
        word
        for word in re.split(r"[^a-z0-9]+", value.lower())
        if word
        and word not in SAFE_WORDS
        and (word in UNSAFE_WORDS or word.startswith(UNSAFE_STEMS))
    ]


def unsafe_plugin_route(url):
    """Words in a plugin:// path or query that suggest playback, auth or a mutating utility."""
    p = urlsplit(url)
    found = unsafe_words(p.path)
    for key, values in parse_qs(p.query, keep_blank_values=True).items():
        found += unsafe_words(key)
        if key.lower() not in FREE_TEXT_KEYS:
            for value in values:
                found += unsafe_words(value)
    return found


# Words that make a skin string or window property name look like it holds an account value
# (``Window(Home).Property(fenlight.debrid.rd)``, ``Skin.String(PVRAccessCode)``).
STORED_SECRET_WORDS = frozenset(
    {
        "access",
        "account",
        "ad",
        "alldebrid",
        "apikey",
        "auth",
        "code",
        "cookie",
        "credential",
        "credentials",
        "debrid",
        "email",
        "key",
        "login",
        "oauth",
        "pass",
        "password",
        "pin",
        "pm",
        "premiumize",
        "rd",
        "realdebrid",
        "secret",
        "session",
        "tb",
        "token",
        "torbox",
        "trakt",
        "user",
    }
)
STORED_VALUE = re.compile(r"(?:property|skin\.string)\(([^()]*)\)", re.I)


def name_words(value):
    """Lower-case words of an identifier, split on separators and camelCase."""
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", value)
    value = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", value)
    return [w for w in re.split(r"[^a-z0-9]+", value.lower()) if w]


def secret_info_labels(labels):
    """Info labels/booleans that would read or test add-on settings or credential-like strings.

    Kodi 20+ ``Addon.SettingStr(addon,id)`` returns raw add-on settings (tokens included), and
    skins/add-ons keep secrets in ``Skin.String``/``Window.Property`` values. Result keys are the
    label text, so value redaction by key cannot be relied on for these. Booleans matter too:
    ``String.StartsWith(Addon.SettingStr(...),a)`` leaks a token one character at a time.
    """
    if not isinstance(labels, list):
        return []
    found = []
    for label in labels:
        value = str(label)
        words = [w for w in re.split(r"[\s(),$\[\]]+", value) if w]
        stored = [w for name in STORED_VALUE.findall(value) for w in name_words(name)]
        if (
            re.search(r"addon\.setting", value, re.I)
            or any(privacy.is_secret(w) for w in words)
            or any(w in STORED_SECRET_WORDS for w in stored)
        ):
            found.append(value)
    return found


def field(result, key, method):
    """Read a JSON-RPC result field, turning a missing key into an actionable error."""
    if not isinstance(result, dict) or key not in result:
        raise ShieldError(
            f"Kodi {method} returned no '{key}'; check the setting/add-on id and Kodi version",
            "invalid_response",
        )
    return result[key]


def text(data):
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        raise ShieldError("File is not UTF-8 text; it cannot be shown or patched") from None


PACKAGE_ACTIVITY = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)/([\w.$]+)")
# Android 10+ runs the screensaver as an activity; nobody is watching it.
DREAM_ACTIVITY = re.compile(r"(?:^|\.)DreamActivity$|(?:^|\.)dreams?\.", re.I)
SLEEPING = re.compile(r"\b(?:isSleeping|mSleeping)=true\b")


def foreground_state(transport):
    """Return ``(screen, package)`` for what is in front of the viewer.

    ``screen`` is ``"app"`` (one resumed activity), ``"screensaver"`` (a dream activity is
    resumed) or ``"asleep"`` (no resumed activity and Android reports the display sleeping;
    package is None). Anything else is ambiguous and refused.
    """
    text = transport.shell("dumpsys", "activity", "activities", limit=2_000_000)
    lines = [
        line
        for line in text.splitlines()
        if re.match(r"\s*(?:mResumedActivity|topResumedActivity|ResumedActivity)\s*[:=]", line)
    ]
    # Older Android / Fire OS dumps may expose only the focused activity. Never use a
    # stale focus entry to override a modern resumed entry, including an explicit null.
    if not lines:
        lines = [
            line for line in text.splitlines() if re.match(r"\s*mFocusedActivity\s*[:=]", line)
        ]
    if any(
        not PACKAGE_ACTIVITY.search(line) and not re.search(r"[:=]\s*null\s*$", line)
        for line in lines
    ):
        raise ShieldError(
            "Foreground TV app is unreadable; no disruptive action performed", "foreground_unknown"
        )
    found = {(m[1], m[2]) for line in lines if (m := PACKAGE_ACTIVITY.search(line))}
    packages = {package for package, _ in found}
    if len(packages) == 1:
        package = packages.pop()
        if any(DREAM_ACTIVITY.search(activity) for _, activity in found):
            return "screensaver", package
        return "app", package
    if not packages and SLEEPING.search(text):
        return "asleep", None
    raise ShieldError(
        "Foreground TV app is unknown; no disruptive action performed", "foreground_unknown"
    )


# android.media.session.PlaybackState values where nobody is watching or listening:
# NONE, STOPPED and ERROR. Paused, playing, buffering, seeking etc. all count as viewing.
IDLE_MEDIA_STATES = frozenset({0, 1, 7})
MEDIA_KEYS = frozenset({"play_pause", "stop"})


def media_sessions(transport):
    """Active Android media sessions as (package, PlaybackState) pairs.

    Independent of Kodi's HTTP API. Refuses when the dump cannot be read.
    """
    text = transport.shell("dumpsys", "media_session", limit=1_000_000)
    if "MEDIA SESSION SERVICE" not in text:
        raise ShieldError(
            "Android media playback state is unknown; no disruptive action performed",
            "playback_unknown",
        )
    sessions, package, active, state_seen = [], None, False, False
    for line in text.splitlines():
        line = line.strip()
        if match := re.match(r"package=([A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+)$", line):
            if active and not state_seen:
                raise ShieldError("Android media playback state is unreadable", "playback_unknown")
            package, active, state_seen = match[1], False, False
        elif line.startswith("active="):
            if line not in ("active=true", "active=false"):
                raise ShieldError("Android media playback state is unreadable", "playback_unknown")
            active = line == "active=true"
        elif package and active and (match := re.match(r"state=PlaybackState \{state=(\d+)", line)):
            sessions.append((package, int(match[1])))
            state_seen = True
    if active and not state_seen:
        raise ShieldError("Android media playback state is unreadable", "playback_unknown")
    return sessions


def media_playing(transport, package=None):
    """Packages whose active media session reports anything other than stopped/none/error."""
    return sorted(
        {
            name
            for name, state in media_sessions(transport)
            if state not in IDLE_MEDIA_STATES and (package is None or name == package)
        }
    )


WAKEFULNESS = re.compile(r"\bmWakefulness=(\w+)")


def wakefulness(transport):
    """Android's power state from ``dumpsys power``: Awake, Dreaming, Dozing or Asleep."""
    match = WAKEFULNESS.search(transport.shell("dumpsys", "power", limit=1_000_000))
    if not match:
        raise ShieldError("Android power state is unknown", "wakefulness_unknown")
    return match[1]


# viewing_state verdicts in which every guarded action may go ahead (nobody is watching).
UNATTENDED = frozenset({"idle", "screensaver", "asleep"})


# What Kodi logs on a clean exit once its settings are on disk (CApplication::Stop). Kodi 22
# on the Shield can then hang at "Stopping all" for minutes; a force-stop after that point
# loses nothing Kodi would have saved.
EXIT_SAVE_STEPS = ("Stopping the application...", "Saving settings", "Saving skin settings")
EXIT_DONE = "Stopping all"
LOG_MESSAGE = re.compile(r"<general>: (.*?)\s*$")


def settings_saved_on_exit(log):
    """kodi.log lines proving the running Kodi saved its settings while exiting, else []."""
    lines = log.splitlines()
    # kodi.log starts afresh with every Kodi start; only the current process's exit counts.
    started = [i for i, line in enumerate(lines) if "<general>: Starting Kodi (" in line]
    lines = lines[started[-1] + 1 :] if started else lines
    messages = [(m[1], line.strip()) for line in lines if (m := LOG_MESSAGE.search(line))]
    begin = max((i for i, (msg, _) in enumerate(messages) if msg == EXIT_SAVE_STEPS[0]), default=-1)
    if begin < 0:
        return []
    evidence, wanted = [], [*EXIT_SAVE_STEPS, EXIT_DONE]
    for msg, line in messages[begin:]:
        if wanted and msg == wanted[0]:
            evidence.append(line)
            wanted.pop(0)
    return evidence if not wanted else []


def setting_source(node):
    """Kodi Manager's store for a listed setting, normalized like its dashboard does:
    ``raw`` (schemaless settings.xml) or ``settings.db`` (Fen Light); None for the schema."""
    raw = node.get("raw")
    value = node.get("source") or (raw.get("source") if isinstance(raw, dict) else None)
    if not isinstance(value, str):
        return None
    if "settings.db" in value:
        return "settings.db"
    return "raw" if value == "raw" else None


class Operations:
    def __init__(self, transport):
        self.t = transport
        self.c = transport.c
        self.files = Files(transport)
        self.lock = threading.RLock()
        self.plans = {}
        self.known_secrets = (self.c.password, self.c.manager_token)
        self.apks = ApkOperations(self)
        self.history = History(self.c.state)
        # kodi_lifecycle: how long to wait for Kodi to exit after Application.Quit.
        self.quit_wait = 30
        self.quit_poll = 1.0
        # After Kodi exits, Android may start a new, empty org.xbmc.kodi process for a receiver
        # within a couple of seconds; look again once this long after the exit.
        self.respawn_grace = 3.0

    def safe(self, result):
        return privacy.scrub(result, self.known_secrets)

    def writes(self):
        if not self.c.allow_writes:
            raise ShieldError(
                "Write tools are disabled. Set NVIDIA_MCP_ALLOW_WRITES=1 in your MCP client and restart the server",
                "write_disabled",
            )

    def idle(self, allow_offline=False):
        try:
            players = self.t.rpc("Player.GetActivePlayers")
        except ShieldError as exc:
            # Offline recovery is for a Kodi whose HTTP server does not answer. An
            # authentication or protocol error means Kodi is alive and may be playing.
            if not allow_offline or exc.kind not in ("unreachable", "timeout"):
                raise ShieldError(
                    "Playback state is unknown; no disruptive action performed"
                    + (
                        ""
                        if not allow_offline
                        else ". Offline recovery applies only when Kodi HTTP is unreachable"
                    ),
                    "playback_unknown",
                ) from None
            if media_playing(self.t, KODI):
                raise ShieldError(
                    "Kodi HTTP is unavailable but Android reports Kodi media is playing or "
                    "paused; no disruptive action performed",
                    "playing",
                ) from None
            return "Kodi HTTP unavailable; explicitly permitted offline recovery"
        if not isinstance(players, list):
            raise ShieldError(
                "Playback state is unknown; no disruptive action performed", "playback_unknown"
            )
        if players:
            raise ShieldError("Kodi is playing. Wait until viewing has finished", "playing")
        return "idle"

    def pids(self, package=KODI):
        """Exact app process probe, with a bounded toolbox/toybox ps fallback."""
        out = self.t.shell(
            "sh",
            "-c",
            "if command -v pidof >/dev/null 2>&1; then pidof "
            + shlex.quote(package)
            + ' || [ "$?" -eq 1 ]; else echo __NO_PIDOF__; fi',
        ).strip()
        if out != "__NO_PIDOF__":
            if out and not re.fullmatch(r"\d+(?:\s+\d+)*", out):
                raise ShieldError("Android process state is unreadable", "process_unknown")
            return set(out.split())
        # Android 5/6 toolbox lacks pidof and ps -A. Plain ps includes app processes on
        # those builds; verify its schema before accepting an empty result as stopped.
        sdk = self.t.shell("getprop", "ro.build.version.sdk").strip()
        if not sdk.isdigit():
            raise ShieldError("Android process state is unreadable", "process_unknown")
        # Modern toybox's plain ps lists only this shell's processes; request all.
        argv = ("ps",) if int(sdk) <= 23 else ("ps", "-A", "-o", "PID,NAME")
        lines = self.t.shell(*argv, limit=500_000).splitlines()
        columns = lines[0].split() if lines else []
        if "PID" not in columns or not columns or columns[-1] != "NAME":
            raise ShieldError("Android process state is unreadable", "process_unknown")
        pids, index = set(), columns.index("PID")
        for line in lines[1:]:
            row = line.split()
            if not row:
                continue
            if len(row) < len(columns) or not row[index].isdigit():
                raise ShieldError("Android process state is unreadable", "process_unknown")
            if row[-1] == package or row[-1].startswith(package + ":"):
                pids.add(row[index])
        return pids

    def running(self, package=KODI):
        return bool(self.pids(package))

    def kodi_running(self):
        return self.running(KODI)

    def kodi_pids(self):
        return self.pids(KODI)

    def launchers(self):
        return LAUNCHERS | set(getattr(self.c, "extra_launchers", ()) or ())

    def require_interrupt_opt_in(self, flag):
        if not getattr(self.c, "allow_interrupt", False):
            raise ShieldError(
                f"{flag}=true was refused: interrupting viewing also needs the user to set "
                "NVIDIA_MCP_ALLOW_INTERRUPT=1 in the MCP client and restart the server. "
                "No action performed",
                "interrupt_not_permitted",
            )

    def require_offline_opt_in(self):
        if not getattr(self.c, "allow_offline_recovery", False):
            raise ShieldError(
                "allow_offline_recovery=true was refused: acting on Kodi while its HTTP "
                "server is unreachable also needs the user to set "
                "NVIDIA_MCP_ALLOW_OFFLINE_RECOVERY=1 in the MCP client and restart the server. "
                "No action performed",
                "offline_recovery_not_permitted",
            )

    def guard_tv(
        self,
        kind,
        *,
        allow_playback=False,
        allow_other_app=False,
        allow_offline=False,
        assume_running=False,
        package=None,
        override_flag=None,
        check_http=True,
    ):
        """One guard for every UI-disruptive action.

        Combines Kodi playback state, Android media sessions (any app, including background
        audio), the Android foreground app (checked against one shared launcher set; a
        screensaver or sleeping display counts as nobody watching) and whether Kodi / a target
        package is running. ``kind`` is one of remote, lifecycle, setting, layout, browse, apk.
        Offline file edits need a stopped Kodi (``stopped``) instead.

        Overrides are model-controlled, so they are honoured only with
        NVIDIA_MCP_ALLOW_INTERRUPT=1 (``allow_offline`` with NVIDIA_MCP_ALLOW_OFFLINE_RECOVERY=1). ``allow_playback`` (shield_remote's
        allow_during_playback) skips every viewing check. ``allow_other_app`` (kodi_lifecycle's
        interrupt_other_app) skips only the checks for other apps: Kodi's own playback is still
        refused. ``override_flag`` names the tool's flag for error messages, if it has one.
        ``check_http=False`` is only for a Kodi that is already exiting (its HTTP server is
        closed): Android's media sessions and foreground app are then the whole check.
        """
        if allow_playback or allow_other_app:
            self.require_interrupt_opt_in(override_flag or "override")
        if allow_offline:
            self.require_offline_opt_in()
        allow_other_app = allow_other_app or allow_playback
        state = {"kind": kind, "override": allow_other_app}
        if assume_running:
            # Skip the ADB probe: the playback query establishes the state on its own.
            running = True
        else:
            running = self.kodi_running()
        if kind in ("layout", "browse") and not running:
            raise ShieldError("Kodi is not running; start it first", "kodi_stopped")
        if not check_http:
            state["playback"] = "Kodi exiting; HTTP closed"
        elif running and not allow_playback:
            state["playback"] = self.idle(allow_offline)
        screen, app = foreground_state(self.t)
        state["screen"], state["foreground"] = screen, app
        if app == KODI and not running and check_http:
            # The process probe can miss a Kodi that has just been opened. The resumed
            # activity is authoritative: check its playback before doing anything.
            running = True
            if not allow_playback:
                state["playback"] = self.idle(allow_offline)
        if not allow_playback:
            # Background audio (Spotify, a paused film under a screensaver) has no foreground
            # activity; Android's media sessions are the only independent signal.
            playing = media_playing(self.t)
            if KODI in playing:
                raise ShieldError(
                    "Android reports Kodi media playing or paused. Wait until viewing has "
                    "finished; no disruptive action performed",
                    "playing",
                )
            if playing and not allow_other_app:
                raise ShieldError(
                    f"Another app's media is playing or paused ({', '.join(playing[:3])}). "
                    "Wait until it has finished; no disruptive action performed",
                    "other_app_playing",
                )
        if screen == "asleep" and kind == "remote":
            raise ShieldError(
                "The Shield is asleep; a button press would wake it and can switch the TV on "
                "through HDMI-CEC. No button sent",
                "asleep",
            )
        if screen == "app" and app not in self.launchers() | {KODI} and not allow_other_app:
            hint = (
                f" Only with the viewer's permission (and NVIDIA_MCP_ALLOW_INTERRUPT=1) may "
                f"{override_flag}=true be used."
                if override_flag
                else " Wait until the viewer is back on the home screen or in Kodi."
            )
            raise ShieldError(
                f"Another TV app ({app}) is in the foreground; no disruptive action performed."
                + hint,
                "other_app_foreground",
            )
        if package and (running if package == KODI else self.running(package)):
            raise ShieldError("Stop the target app before installing its APK", "app_running")
        state["kodi_running"] = running
        return state

    def viewing_state(self):
        """What the TV is doing, from the same signals the guard reads, without acting.

        Returns ``players`` (Kodi JSON-RPC), ``media_sessions`` (Android), ``foreground``,
        ``screen``, ``wakefulness``, ``kodi_running``, ``unavailable`` (signal -> error kind)
        and a ``verdict``: idle, playing, paused, other_app, screensaver, asleep or unknown.
        Any verdict outside idle/screensaver/asleep is one the guard would refuse; a signal
        that cannot be read makes the verdict unknown rather than idle.
        """
        unavailable = {}

        def read(name, function):
            try:
                return function()
            except ShieldError as exc:
                unavailable[name] = exc.kind
                return None

        running = read("kodi_running", self.kodi_running)
        screen_app = read("foreground", lambda: foreground_state(self.t))
        screen, app = screen_app if screen_app else (None, None)
        players, speeds = [], []
        if running is not False or app == KODI:
            players = read("players", lambda: self.t.rpc("Player.GetActivePlayers"))
            if players is not None and not isinstance(players, list):
                unavailable["players"], players = "invalid_response", None
            for player in players or []:
                props = read(
                    "player_speed",
                    lambda p=player: self.t.rpc(
                        "Player.GetProperties",
                        {"playerid": p.get("playerid"), "properties": ["speed"]},
                    ),
                )
                if isinstance(props, dict) and isinstance(props.get("speed"), int | float):
                    speeds.append(props["speed"])
        sessions = read("media_sessions", lambda: media_sessions(self.t))
        awake = read("wakefulness", lambda: wakefulness(self.t))
        active = [(name, state) for name, state in sessions or [] if state not in IDLE_MEDIA_STATES]
        kodi_states = [state for name, state in active if name == KODI]
        if players:
            if speeds and len(speeds) == len(players):
                paused = all(speed == 0 for speed in speeds)
            else:
                paused = bool(kodi_states) and all(state == 2 for state in kodi_states)
            verdict = "paused" if paused else "playing"
        elif kodi_states:
            verdict = "paused" if all(state == 2 for state in kodi_states) else "playing"
        elif active:
            verdict = "other_app"
        elif sessions is None or players is None or screen is None:
            verdict = "unknown"
        elif screen == "asleep":
            verdict = "asleep"
        elif screen == "screensaver":
            verdict = "screensaver"
        elif app not in self.launchers() | {KODI}:
            verdict = "other_app"
        elif awake in ("Asleep", "Dozing"):
            verdict = "asleep"
        elif awake == "Dreaming":
            verdict = "screensaver"
        else:
            verdict = "idle"
        return {
            "verdict": verdict,
            "players": players,
            "media_sessions": None
            if sessions is None
            else [{"package": name, "state": state} for name, state in sessions],
            "foreground": app,
            "screen": screen,
            "wakefulness": awake,
            "kodi_running": running,
            "unavailable": unavailable,
        }

    def nothing_playing(self, transfer):
        """Refuse a large transfer (not otherwise disruptive) while anyone watches or listens.

        Pulling hundreds of MB over the Shield's network link competes with a stream, and a
        paused film is about to resume. Android's media sessions are read on every call;
        Kodi's player list is added when its HTTP server answers (it may be stopped).
        """
        playing = media_playing(self.t)
        try:
            players = self.t.rpc("Player.GetActivePlayers")
        except ShieldError:
            players = None
        if isinstance(players, list) and players and KODI not in playing:
            playing = [KODI, *playing]
        if playing:
            raise ShieldError(
                f"Media is playing or paused ({', '.join(playing[:3])}); {transfer} would "
                "compete with it for the network. Try again when viewing has finished; "
                "nothing kept and no TV changes",
                "playing",
            )

    def stopped(self):
        if self.kodi_running():
            raise ShieldError(
                "Stop Kodi before editing files; Kodi can overwrite changes while running",
                "app_running",
            )

    def audit(self, operation, target, backup_id=None):
        # Existing call sites keep their contract. Targets never enter operation history.
        context = CONTEXT.get()
        if context is not None:
            context["backup_refs"].extend(references({"backup_id": backup_id})["backup_refs"])
            return
        try:
            self.history.append(
                record(operation, correlation(), time.monotonic(), result={"backup_id": backup_id})
            )
        except Exception:
            self.history.available = False

    def shield_status(self):
        from .diagnostics import health

        props = {}
        for key in (
            "ro.product.model",
            "ro.build.version.release",
            "ro.build.version.sdk",
            "ro.product.cpu.abi",
        ):
            props[key] = self.t.shell("getprop", key)
        memory = self.t.shell("cat", "/proc/meminfo", limit=64000)
        storage = self.t.shell("df", "-k", "/data", "/sdcard", limit=16000)
        telemetry = {}
        for name, args in {
            "uptime": ("cat", "/proc/uptime"),
            "thermal": ("dumpsys", "thermalservice"),
        }.items():
            try:
                telemetry[name] = self.t.shell(*args, limit=64000)
            except ShieldError:
                telemetry[name] = ""
        return {
            "properties": props,
            "storage": storage,
            "memory": memory.splitlines()[:6],
            "kodi_running": self.kodi_running(),
            "health": health(memory, storage, telemetry["uptime"], telemetry["thermal"]),
        }

    def kodi_status(self):
        result = {}
        connection_error = None
        queries = {
            "application": ("Application.GetProperties", {"properties": ["version", "name"]}),
            "screen": (
                "GUI.GetProperties",
                {"properties": ["currentwindow", "currentcontrol", "skin"]},
            ),
            "profile": ("Profiles.GetCurrentProfile", {}),
            "players": ("Player.GetActivePlayers", {}),
        }
        for name, (method, params) in queries.items():
            if connection_error:
                result[name] = {"unavailable": connection_error}
                continue
            try:
                result[name] = self.t.rpc(method, params)
            except ShieldError as exc:
                result[name] = {"unavailable": str(exc)}
                # Every later query would fail (or wait out the deadline) the same way.
                if exc.kind in (
                    "unreachable",
                    "timeout",
                    "response_timeout",
                    "authentication_denied",
                ):
                    connection_error = str(exc)
        result["capabilities"] = {
            "writes_enabled": self.c.allow_writes,
            "plugin_browse_enabled": self.c.allow_plugin_browse,
            "manager_configured": bool(self.c.manager_token),
            "file_access": "mounted share" if self.c.mount else "ADB",
        }
        return self.safe(result)

    def rpc_read(self, method, params):
        if method not in READ_METHODS:
            raise ShieldError("Method is outside the read-only allowlist; use a dedicated tool")
        if method == "Settings.GetSettingValue" and privacy.SECRET.search(
            str(params.get("setting", ""))
        ):
            raise ShieldError(
                "Credential values are not exposed; inspect redacted settings instead"
            )
        if len(json.dumps(params)) > 12_000:
            raise ShieldError("Parameters exceed size limit")
        if (method == "XBMC.GetInfoLabels" and secret_info_labels(params.get("labels"))) or (
            method == "XBMC.GetInfoBooleans" and secret_info_labels(params.get("booleans"))
        ):
            raise ShieldError(
                "Info labels or booleans that read or test add-on settings or credential-like "
                "skin strings/window properties are refused; use kodi_addon_settings, which "
                "redacts credentials",
                "secret_read",
            )
        if method.startswith("VideoLibrary."):
            params = dict(params)
            limits = params.get("limits") or {}
            start = limits.get("start", 0) if isinstance(limits, dict) else 0
            end = limits.get("end") if isinstance(limits, dict) else None
            if not isinstance(start, int) or start < 0:
                start = 0
            if not isinstance(end, int) or end <= start or end - start > LIBRARY_MAX:
                end = start + (LIBRARY_DEFAULT if end is None else LIBRARY_MAX)
            params["limits"] = {"start": start, "end": end}
        result = self.safe(self.t.rpc(method, params))
        while (
            method.startswith("VideoLibrary.")
            and len(json.dumps(result)) > READ_MAX
            and params["limits"]["end"] - params["limits"]["start"] > 1
        ):
            # Art, cast and file properties make items large: fetch a smaller page instead of
            # refusing the whole read.
            start = params["limits"]["start"]
            end = start + (params["limits"]["end"] - start) // 2
            params["limits"] = {"start": start, "end": end}
            result = self.safe(self.t.rpc(method, params))
            if isinstance(result, dict):
                result["note"] = (
                    f"Reduced to items {start}-{end} to stay under 250 KB; request the next "
                    "page from limits.end, or ask for fewer properties"
                )
        if len(json.dumps(result)) > READ_MAX:
            raise ShieldError(
                "Kodi returned more than 250 KB; request fewer properties or items "
                "(use kodi_settings to search settings)",
                "too_large",
            )
        return result

    def addons(self, enabled_only=False):
        params = {
            # type is returned automatically, not a valid Addon.Fields property.
            "properties": ["name", "version", "enabled"],
            "limits": {"start": 0, "end": 500},
        }
        if enabled_only:
            params["enabled"] = True
        return self.safe(self.t.rpc("Addons.GetAddons", params))

    def read_file(self, path):
        data = self.files.read(path)
        return {
            "path": relative(path),
            "sha256": digest(data),
            "bytes": len(data),
            "content": privacy.file_text(text(data), self.known_secrets),
            "note": "Content is redacted; checksum describes the original file. Use exact non-secret anchors for patches.",
        }

    def logs(self, previous=False, lines=250):
        if not 1 <= lines <= 1000:
            raise ShieldError("Choose 1–1000 log lines")
        content = privacy.text(
            self.files.tail("temp/kodi.old.log" if previous else "temp/kodi.log", lines),
            self.known_secrets,
        )
        patterns = {
            "crash": r"fatal|segmentation|crash|signal 11|SIGSEGV",
            "python": r"PythonToCppException|Traceback|Error Type:",
            "stream": r"curl.*(?:error|timeout)|read.*error|EOF|buffering|CVideoPlayer.*error",
            "shutdown": r"service.*stop.*timeout|script.*stopp|thread.*join",
            "storage": r"write error|no space|permission denied|read.only file",
        }
        return {
            "lines": content,
            "signals": {k: len(re.findall(v, content, re.I)) for k, v in patterns.items()},
            "note": "Signals are clues, not a root-cause verdict. This is a bounded tail, not the whole log.",
        }

    def lifecycle(self, action, allow_offline=False, interrupt_other_app=False):
        self.writes()
        with self.lock:
            # A stopped Kodi cannot be playing, and its HTTP API is down, so the
            # playback check would always report "unknown". Skip it only then.
            state = self.guard_tv(
                "lifecycle",
                allow_other_app=interrupt_other_app,
                allow_offline=allow_offline,
                assume_running=action != "start",
                override_flag="interrupt_other_app",
            )
            result = {"requested": action}
            if action in ("stop", "restart"):
                if state.get("playback") == "idle":
                    result.update(self.quit_kodi(action, interrupt_other_app))
                else:
                    # Explicitly permitted offline recovery: Kodi HTTP cannot take a quit.
                    self.force_stop(action)
                    result["stopped_by"] = "force-stop (Kodi HTTP unreachable)"
            if action in ("start", "restart"):
                self.t.shell("am", "start", "-n", "org.xbmc.kodi/.Splash")
                self.audit("kodi_start", KODI)
            result["note"] = (
                "Run kodi_status to verify startup; launching an activity does not confirm "
                "Kodi is ready."
                if action != "stop"
                else "Kodi has exited."
            )
            return result

    def wait_for_exit(self, action, pids=None):
        """True once the Kodi that was asked to quit has gone. With ``pids`` (the processes that
        were running when Application.Quit was sent) a different, newer Kodi process does not
        count as the old one still exiting."""
        deadline = time.monotonic() + self.quit_wait
        while True:
            try:
                if not self.kodi_running():
                    return True
                if pids and not (self.kodi_pids() & pids):
                    return True
            except ShieldError as exc:
                raise ShieldError(
                    f"Kodi was asked to quit but its state could not be confirmed ({exc})"
                    + ("; it was not started again" if action == "restart" else "")
                    + ". Check shield_status before trying again",
                    "stop_unconfirmed",
                ) from None
            if time.monotonic() >= deadline:
                return False
            time.sleep(self.quit_poll)

    def quit_kodi(self, action, interrupt_other_app):
        """Application.Quit lets Kodi save settings; force-stop only a provably saved, hung exit."""
        try:
            pids = self.kodi_pids()
        except ShieldError:
            pids = set()
        try:
            self.t.rpc("Application.Quit")
        except ShieldError as exc:
            # Kodi often closes its HTTP server before answering, or stalls while exiting
            # (response_timeout) or cuts the reply short (invalid_response); either way the
            # request was sent and the exit is checked below.
            if exc.kind not in ("unreachable", "timeout", "response_timeout", "invalid_response"):
                raise ShieldError(
                    f"Kodi refused Application.Quit ({exc.message}); Kodi was left running",
                    "quit_failed",
                ) from None
        self.audit("kodi_quit", KODI)
        if self.wait_for_exit(action, pids):
            result = {"stopped_by": "Application.Quit"}
            if pids:
                result.update(self.stop_respawned(pids, action))
            return result
        not_started = "; it was not started again" if action == "restart" else ""
        try:
            evidence = settings_saved_on_exit(self.files.tail("temp/kodi.log", 400))
        except ShieldError:
            evidence = []
        if not evidence:
            reason = "kodi.log does not show it finished saving its settings"
        else:
            try:
                self.guard_tv(
                    "lifecycle",
                    allow_other_app=interrupt_other_app,
                    assume_running=True,
                    override_flag="interrupt_other_app",
                    check_http=False,
                )
                reason = None
            except ShieldError as exc:
                reason = f"the TV guard refused a force-stop: {exc.message}"
        if reason:
            raise ShieldError(
                f"Kodi did not exit within {self.quit_wait} s of Application.Quit and was left "
                f"as it is ({reason}){not_started}. Its HTTP server is usually closed by now. "
                "Check kodi_logs and shield_status; if it stays stuck, ask the person at the TV "
                "to force-stop Kodi (Settings > Apps > Kodi > Force stop)",
                "exit_hung",
            )
        self.force_stop(action)
        return {
            "stopped_by": "force-stop after a hung exit",
            "exit_evidence": privacy.text("\n".join(evidence), self.known_secrets).splitlines(),
        }

    def stop_respawned(self, pids, action):
        """After the quitting Kodi has gone, stop a new Kodi process Android started by itself.

        On the Shield (2026-10-11) a new org.xbmc.kodi process appeared 2 s after Kodi exited, with
        no activity and no CPU time used; it is not the Kodi that was asked to quit, so it is
        neither a hung exit nor something being watched. It is force-stopped only while Kodi is
        not the app in front: a Kodi someone opened again is left running."""
        grace = min(self.respawn_grace, self.quit_wait)
        if grace > 0:
            time.sleep(grace)
        current = self.kodi_pids()
        if not current:
            return {}
        new = sorted(current - pids)
        not_started = "; it was not started again" if action == "restart" else ""
        try:
            _screen, package = foreground_state(self.t)
        except ShieldError as exc:
            raise ShieldError(
                f"Kodi exited after Application.Quit, but a new Kodi process ({', '.join(new)}) "
                f"started and the app in front could not be checked ({exc.message}); it was left "
                f"running{not_started}. Check shield_status",
                "respawned",
            ) from None
        if package == KODI:
            raise ShieldError(
                f"Kodi exited after Application.Quit, but Kodi was opened again ({', '.join(new)}) "
                f"and is on screen; it was left running{not_started}",
                "restarted",
            )
        self.force_stop(action)
        return {"respawned_process_stopped": new}

    def force_stop(self, action):
        self.t.shell("am", "force-stop", KODI)
        self.audit("kodi_stop", KODI)
        try:
            still_running = self.kodi_running()
        except ShieldError as exc:
            raise ShieldError(
                f"Kodi was force-stopped but its state could not be confirmed ({exc})"
                + ("; it was not started again" if action == "restart" else "")
                + ". Check shield_status before trying again",
                "stop_unconfirmed",
            ) from None
        if still_running:
            raise ShieldError(
                "Kodi was still running after force-stop"
                + ("; restart abandoned" if action == "restart" else "")
                + ". Check kodi_status and shield_status",
                "stop_failed",
            )

    def remote(self, button, allow_during_playback=False):
        self.writes()
        if button not in BUTTONS:
            raise ShieldError("Unknown remote button")
        with self.lock:
            state = self.guard_tv(
                "remote",
                allow_playback=allow_during_playback,
                override_flag="allow_during_playback",
            )
            if button in MEDIA_KEYS:
                if not allow_during_playback:
                    # The guard found nothing playing, so a media key can only reach whichever
                    # app last held a media session and start its audio.
                    raise ShieldError(
                        f"Nothing is playing, so {button} would only wake another app's media; "
                        "no button sent",
                        "nothing_playing",
                    )
                if state["foreground"] in self.launchers() | {KODI, None}:
                    try:
                        players = self.t.rpc("Player.GetActivePlayers")
                    except ShieldError:
                        players = None
                    if isinstance(players, list) and players:
                        # Address Kodi's player directly rather than Android's media-button
                        # routing, which can pick a background app.
                        method = "Player.PlayPause" if button == "play_pause" else "Player.Stop"
                        for player in players:
                            self.t.rpc(method, {"playerid": player["playerid"]})
                        self.audit("remote", button)
                        return {"sent": button, "via": "Kodi JSON-RPC " + method}
            self.t.shell("input", "keyevent", BUTTONS[button])
            self.audit("remote", button)
        return {"sent": button}

    def connect(self):
        self.t.adb("connect", self.c.serial, device=False)
        # A new adb connection drops the old adb forwards; cached forward URLs are stale.
        reset = getattr(self.t, "reset_forwards", None)
        if callable(reset):
            reset()
        return {"state": self.t.adb("get-state").decode().strip()}

    def rebuild_layout(self):
        self.writes()
        with self.lock:
            self.guard_tv("layout")
            result = self.t.manager("/api/widgets/layout/rebuild", "POST", {})
            self.audit("rebuild_layout", "active profile")
            return self.safe(result)

    PATCH_SUFFIXES = (".py", ".xml", ".json", ".properties", ".txt")

    def _patch_plan(self, path, expected_sha256, edits):
        """Validate and compute a patch without writing. Returns (before, after) bytes."""
        relative(path)
        suffix = PurePosixPath(path).suffix
        if suffix not in self.PATCH_SUFFIXES:
            raise ShieldError("Only Kodi text configuration/source files can be patched")
        if path.startswith("addons/") and suffix in (".py", ".pyo"):
            raise ShieldError(
                "Add-on Python code cannot be patched by an agent; update the add-on instead",
                "addon_code",
            )
        edits = [e.model_dump() if hasattr(e, "model_dump") else e for e in edits or []]
        if not re.fullmatch(r"[a-f0-9]{64}", expected_sha256) or not 1 <= len(edits) <= 20:
            raise ShieldError("Provide a SHA-256 and 1–20 exact edits")
        before = self.files.read(path)
        if digest(before) != expected_sha256:
            raise ShieldError("File changed since inspection; patch cancelled")
        content = original = text(before)
        for edit in edits:
            old, new = (edit.get("before"), edit.get("after")) if isinstance(edit, dict) else (0, 0)
            if (
                not isinstance(old, str)
                or not old
                or not isinstance(new, str)
                or content.count(old) != 1
            ):
                raise ShieldError(
                    "Each before anchor must occur exactly once; no fuzzy replacements"
                )
            if privacy.contains_secret(old) or privacy.contains_secret(new):
                raise ShieldError(
                    "Edits that touch credentials or secret settings are refused", "secret_edit"
                )
            content = content.replace(old, new, 1)
        data = content.encode("utf-8")
        if len(data) > MAX_FILE:
            raise ShieldError("Patched file exceeds the size limit")
        try:
            if suffix == ".py":
                ast.parse(content)
            elif suffix == ".xml":
                fromstring(content)
            elif suffix == ".json":
                json.loads(content)
        except Exception:
            raise ShieldError("Patched file failed syntax validation; no write performed") from None
        changed_lines = [
            line[1:]
            for line in difflib.unified_diff(
                original.splitlines(), content.splitlines(), lineterm="", n=0
            )
            if line[:1] in "+-" and not line.startswith(("+++", "---"))
        ]
        try:
            touched = privacy.secret_fields(original, suffix) != privacy.secret_fields(
                content, suffix
            )
        except Exception:
            touched = True  # The original is unparseable; be conservative.
        if touched or any(privacy.contains_secret(line) for line in changed_lines):
            raise ShieldError(
                "Edits that touch credentials or secret settings are refused", "secret_edit"
            )
        return before, data, len(edits)

    def patch_preview(self, path, expected_sha256, edits):
        with self.lock:
            before, data, count = self._patch_plan(path, expected_sha256, edits)
        old = privacy.text(text(before), self.known_secrets).splitlines()
        new = privacy.text(text(data), self.known_secrets).splitlines()
        diff = list(difflib.unified_diff(old, new, "a/" + path, "b/" + path, lineterm="", n=2))
        return {
            "dry_run": True,
            "path": path,
            "before_sha256": digest(before),
            "after_sha256": digest(data),
            "edits": count,
            "changed": before != data,
            "diff": "\n".join(diff[:400]) + ("\n... (diff truncated)" if len(diff) > 400 else ""),
            "note": "Diff is redacted. Apply with kodi_patch_apply using the same arguments.",
        }

    def patch_apply(self, path, expected_sha256, edits):
        self.writes()
        with self.lock:
            before, data, _ = self._patch_plan(path, expected_sha256, edits)
            self.stopped()
            backup = self.files.snapshot(path, before)
            try:
                self.files.write(path, data, expected_sha256)
            except Exception:
                raise ShieldError(
                    "Patch failed; original backup is "
                    + backup
                    + ". Inspect current file before restoring"
                ) from None
            self.audit("patch_file", path, backup)
            return {
                "path": path,
                "sha256": digest(data),
                "backup_id": backup,
                "restart_required": True,
            }

    def patch_file(self, path, expected_sha256, edits, dry_run=True):
        """Deprecated combined entry point kept for existing agents."""
        if dry_run:
            return self.patch_preview(path, expected_sha256, edits)
        return self.patch_apply(path, expected_sha256, edits)

    def restore_file(self, backup_id, expected_current_sha256):
        self.writes()
        with self.lock:
            self.stopped()
            path, data = self.files.restore_data(backup_id)
            current = self.files.read(path)
            if digest(current) != expected_current_sha256:
                raise ShieldError("Current checksum differs; restore cancelled")
            safety = self.files.snapshot(path, current)
            self.files.write(path, data, expected_current_sha256)
            self.audit("restore_file", path, safety)
            return {"path": path, "sha256": digest(data), "undo_backup_id": safety}

    def directory(self, path, start=0, limit=24):
        if not self.c.allow_plugin_browse:
            raise ShieldError(
                "Directory execution is opt-in: set NVIDIA_MCP_ALLOW_PLUGIN_BROWSE=1. Installed add-ons may fetch remote metadata"
            )
        if not 0 <= start <= 10_000 or not 1 <= limit <= 48 or len(path) > 12_000:
            raise ShieldError("Directory preview bounds exceeded")
        p = urlsplit(path)
        if p.username or p.password or p.fragment or any(ord(c) < 32 for c in path):
            raise ShieldError("Invalid directory path")
        if p.scheme == "plugin":
            if not p.netloc.startswith("plugin.video."):
                raise ShieldError("Only video add-on directories can be previewed")
            words = unsafe_plugin_route(path)
            if words:
                raise ShieldError(
                    "Interactive/playback/utility action cannot be previewed (route contains: "
                    + ", ".join(sorted(set(words))[:5])
                    + ")",
                    "unsafe_route",
                )
            self.guard_tv("browse")
            addon = field(
                self.t.rpc(
                    "Addons.GetAddonDetails", {"addonid": p.netloc, "properties": ["enabled"]}
                ),
                "addon",
                "Addons.GetAddonDetails",
            )
            if not addon.get("enabled"):
                raise ShieldError("Video add-on is not enabled")
        elif not (
            p.scheme in ("videodb", "library")
            or path.startswith("special://profile/playlists/video/")
        ):
            raise ShieldError(
                "Choose an installed video plugin, video library or profile video playlist"
            )
        else:
            self.guard_tv("browse")
        result = self.t.rpc(
            "Files.GetDirectory",
            {
                "directory": path,
                "media": "video",
                "properties": [
                    "title",
                    "art",
                    "plot",
                    "year",
                    "season",
                    "episode",
                    "playcount",
                    "resume",
                ],
                "limits": {"start": start, "end": start + limit},
            },
        )
        return self.safe(result)

    def set_core_setting(self, setting, value):
        self.writes()
        if privacy.SECRET.search(setting) or not re.fullmatch(r"[a-zA-Z0-9_.-]+", setting):
            raise ShieldError("Credential settings cannot be changed through this tool")
        if protected_setting(setting, getattr(self.c, "allow_settings", ())):
            raise ShieldError(
                f"{setting} is a protected setting (web server, add-on sources and updates, "
                "master lock, system, debug, proxy, skin, display, audio output device, "
                "refresh-rate switching or language) and cannot be changed by an agent. Change "
                "it on the TV, or the user can list this exact id in NVIDIA_MCP_ALLOW_SETTINGS",
                "protected_setting",
            )
        if type(value) not in (bool, int, float, str) or len(str(value)) > 500:
            raise ShieldError("Use a short primitive setting value")
        with self.lock:
            self.guard_tv("setting", assume_running=True)
            old = field(
                self.t.rpc("Settings.GetSettingValue", {"setting": setting}),
                "value",
                "Settings.GetSettingValue",
            )
            path = self.profile_userdata() + "/guisettings.xml"
            backup = self.files.snapshot(path, self.files.read(path))
            accepted = self.t.rpc("Settings.SetSettingValue", {"setting": setting, "value": value})
            new = field(
                self.t.rpc("Settings.GetSettingValue", {"setting": setting}),
                "value",
                "Settings.GetSettingValue",
            )
            if accepted is not True or new != value:
                raise ShieldError("Kodi did not confirm the new setting; backup is " + backup)
            self.audit("set_core_setting", setting, backup)
            return self.safe(
                {"setting": setting, "previous": old, "current": new, "backup_id": backup}
            )

    def manager_read(self, area, addon_id=None):
        endpoints = {
            "layout": "/api/widgets/layout",
            "sources": "/api/widgets/sources",
            "health": "/api/health",
            "pipeline": "/api/pipeline",
            "fixes": "/api/fixes",
            "backups": "/api/stack/backups",
        }
        if addon_id is not None:
            if area != "backups" or not ADDON_ID.fullmatch(addon_id):
                raise ShieldError("An add-on ID is supported only for backup listing")
            return self.safe(self.t.manager(f"/api/addons/{addon_id}/backups"))
        return self.safe(self.t.manager(endpoints[area]))

    def widget_cache(self):
        """Kodi Manager 0.6+ widget cache: status plus cached row definitions (read-only)."""
        try:
            status = self.t.manager("/api/widget-cache")
            rows = self.t.manager("/api/widget-cache/rows")
        except ShieldError as exc:
            # Only a missing route means an older Manager; other errors keep their own remedy.
            if exc.kind == "unsupported":
                raise ShieldError(
                    "Kodi Manager did not offer the widget-cache API; it needs Kodi Manager 0.6+",
                    "unsupported",
                ) from None
            raise
        return self.safe({"status": status, "rows": rows})

    def widget_cache_refresh(self):
        self.writes()
        with self.lock:
            self.guard_tv("layout", assume_running=True)
            result = self.t.manager("/api/widget-cache/refresh", "POST", {})
            self.audit("widget_cache_refresh", "active profile")
            return self.safe(result)

    def backup_file(self, path):
        data = self.files.read(path)
        return {
            "backup_id": self.files.snapshot(path, data),
            "sha256": digest(data),
            "bytes": len(data),
        }

    def settings_page(self, tree, query, start, limit):
        if not 0 <= start <= 10_000 or not 1 <= limit <= 50 or len(query) > 200:
            raise ShieldError("Choose 1–50 settings per page and a short search query")
        rows = []

        def visit(node):
            if isinstance(node, dict):
                if "id" in node and "value" in node:
                    if (
                        query.lower()
                        in (str(node["id"]) + " " + str(node.get("label", ""))).lower()
                    ):
                        rows.append(
                            {
                                k: v
                                for k, v in node.items()
                                if k
                                in (
                                    "id",
                                    "label",
                                    "type",
                                    "value",
                                    "default",
                                    "options",
                                    "editable",
                                    "secret",
                                    "value_source",
                                    "warning",
                                )
                            }
                        )
                        source = setting_source(node)
                        if source:
                            rows[-1]["source"] = source
                else:
                    for value in node.values():
                        visit(value)
            elif isinstance(node, list):
                for value in node:
                    visit(value)

        visit(tree)
        page = {
            "settings": rows[start : start + limit],
            "total": len(rows),
            "start": start,
            "next_start": start + limit if start + limit < len(rows) else None,
        }
        if isinstance(tree, dict):
            # Kodi Manager: whether this add-on accepts edits at all, and why not.
            for key in ("editable", "read_only_reason"):
                if key in tree:
                    page[key] = tree[key]
        return self.safe(page)

    def core_settings(self, query="", start=0, limit=25):
        return self.settings_page(
            self.t.rpc("Settings.GetSettings", {"level": "expert"}), query, start, limit
        )

    def addon_settings(self, addon_id, query="", start=0, limit=25):
        if not ADDON_ID.fullmatch(addon_id):
            raise ShieldError("Invalid add-on ID")
        if self.c.manager_token:
            return self.settings_page(
                self.t.manager(f"/api/addons/{addon_id}/settings"), query, start, limit
            )
        root = fromstring(
            self.files.read(f"{self.profile_userdata()}/addon_data/{addon_id}/settings.xml")
        )
        rows = [
            {
                "id": n.get("id"),
                "value": n.get("value", n.text or ""),
                "value_source": "saved XML; defaults/schema not included",
            }
            for n in root.iter("setting")
            if n.get("id")
        ]
        return self.settings_page(rows, query, start, limit)

    def profile_userdata(self):
        """Resolve the actual profile instead of silently editing the master profile.

        Kodi's profiles.xml stores each id as a child element and ``lastloaded`` as the
        position of the profile in the file, not its id (they differ once a profile has been
        deleted). The master profile is always the first entry.
        """
        root = fromstring(self.files.read("userdata/profiles.xml"))
        profiles = root.findall("profile")
        try:
            label = field(
                self.t.rpc("Profiles.GetCurrentProfile"), "label", "Profiles.GetCurrentProfile"
            )
        except ShieldError:
            if self.kodi_running():
                raise ShieldError(
                    "Kodi is running but its active profile cannot be queried; no profile assumed"
                ) from None
            last = (root.findtext("lastloaded") or "0").strip()
            index = int(last) if last.isdigit() else -1
            matches = [profiles[index]] if 0 <= index < len(profiles) else []
        else:
            matches = [p for p in profiles if p.findtext("name") == label]
        if len(matches) != 1:
            raise ShieldError(
                "Cannot uniquely resolve the active Kodi profile; inspect profiles.xml"
            )
        profile = matches[0]
        path = (profile.findtext("directory") or "").strip().rstrip("/")
        if profile is profiles[0]:
            if path in ("special://masterprofile", ""):
                return "userdata"
        else:
            if path.startswith("special://masterprofile/"):
                path = path[len("special://masterprofile/") :]
            if path.startswith("profiles/") and ".." not in PurePosixPath(path).parts:
                return relative("userdata/" + path)
        raise ShieldError("Unsupported profile directory; use explicit Kodi-relative file tools")

    def set_addon_setting(self, addon_id, expected_version, setting, value):
        self.writes()
        if (
            not ADDON_ID.fullmatch(addon_id)
            or not re.fullmatch(r"[A-Za-z0-9_.-]+", setting)
            or privacy.SECRET.search(setting)
        ):
            raise ShieldError("Invalid or credential-related add-on setting")
        if type(value) not in (bool, int, float, str) or len(str(value)) > 500:
            raise ShieldError("Use a short primitive setting value")
        with self.lock:
            metadata = fromstring(self.files.read(f"addons/{addon_id}/addon.xml"))
            if metadata.get("id") != addon_id or metadata.get("version") != expected_version:
                raise ShieldError("Installed add-on version differs from the inspected version")
            if self.c.manager_token:
                self.guard_tv("setting", assume_running=True)
                change = {"id": setting, "value": value}
                # Schemaless (raw) and Fen Light settings.db rows are written only when the
                # change names their store; look it up so callers need not know it.
                listed = self.t.manager(f"/api/addons/{addon_id}/settings")
                sources = set()

                def visit(node):
                    if isinstance(node, dict):
                        if node.get("id") == setting and "value" in node:
                            sources.add(setting_source(node) or "settings.xml")
                        else:
                            for child in node.values():
                                visit(child)
                    elif isinstance(node, list):
                        for child in node:
                            visit(child)

                visit(listed)
                if len(sources) > 1:
                    raise ShieldError(
                        "This add-on lists the setting in more than one store "
                        f"({', '.join(sorted(sources))}); edit it in Kodi Manager",
                        "invalid_request",
                    )
                if sources and sources != {"settings.xml"}:
                    change["source"] = sources.pop()
                result = self.t.manager(
                    f"/api/addons/{addon_id}/settings", "PATCH", {"changes": [change]}
                )
                self.audit("set_addon_setting", addon_id + ":" + setting, result.get("backup_id"))
                return self.safe(result)
            self.stopped()
            path = f"{self.profile_userdata()}/addon_data/{addon_id}/settings.xml"
            before = self.files.read(path)
            root = fromstring(before)
            nodes = [n for n in root.iter("setting") if n.get("id") == setting]
            if len(nodes) != 1:
                raise ShieldError(
                    "Only existing, unambiguous saved settings can be edited without Manager"
                )
            node = nodes[0]
            new = str(value).lower() if isinstance(value, bool) else str(value)
            if "value" in node.attrib:
                node.set("value", new)
            else:
                node.text = new
            node.attrib.pop("default", None)
            data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
            backup = self.files.snapshot(path, before)
            self.files.write(path, data, digest(before))
            self.audit("set_addon_setting", addon_id + ":" + setting, backup)
            return {"changed_count": 1, "backup_id": backup, "restart_required": True}

    def layout_preview(self, plan):
        if (
            not isinstance(plan, dict)
            or not plan.get("section_id")
            or not plan.get("expected_revision")
            or not isinstance(plan.get("rows"), list)
            or len(plan["rows"]) > 20
            or len(json.dumps(plan)) > 100_000
        ):
            raise ShieldError(
                "Provide a section_id, expected_revision and up to 20 complete rows from manager layout"
            )
        self.idle()
        with self.lock:
            result = self.t.manager("/api/widgets/layout/preview", "POST", plan)
            preview_id = uuid.uuid4().hex
            profile = self.t.rpc("Profiles.GetCurrentProfile").get("label")
            if not profile:
                raise ShieldError("Cannot bind preview to the active profile")
            self.plans[preview_id] = (time.monotonic(), json.loads(json.dumps(plan)), profile)
            self.plans = {k: v for k, v in self.plans.items() if time.monotonic() - v[0] < 600}
            return self.safe({"preview_id": preview_id, "expires_seconds": 600, "preview": result})

    def layout_apply(self, preview_id):
        self.writes()
        with self.lock:
            self.guard_tv("layout", assume_running=True)
            saved = self.plans.get(preview_id)
            if not saved or time.monotonic() - saved[0] > 600:
                raise ShieldError(
                    "Preview expired or belongs to another MCP session; preview again"
                )
            if self.t.rpc("Profiles.GetCurrentProfile").get("label") != saved[2]:
                raise ShieldError(
                    "Kodi profile changed after preview; preview the intended profile again"
                )
            result = self.t.manager("/api/widgets/layout/apply", "POST", saved[1])
            del self.plans[preview_id]
            self.audit("apply_layout", saved[1]["section_id"], result.get("backup_id"))
            return self.safe(result)

    def configuration_backup(self, addon_id=None):
        self.writes()
        with self.lock:
            self.guard_tv("layout", assume_running=True)
            endpoint = "/api/stack/backup"
            if addon_id is not None:
                if not ADDON_ID.fullmatch(addon_id):
                    raise ShieldError("Invalid add-on ID")
                endpoint = f"/api/addons/{addon_id}/backup"
            result = self.t.manager(endpoint, "POST", {})
            self.audit("configuration_backup", addon_id or "checkpoint", result.get("backup_id"))
            return self.safe(result)

    def configuration_restore(self, backup_id, addon_id=None):
        self.writes()
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", backup_id):
            raise ShieldError("Invalid configuration backup ID")
        with self.lock:
            self.guard_tv("layout", assume_running=True)
            endpoint = "/api/stack/restore"
            if addon_id is not None:
                if not ADDON_ID.fullmatch(addon_id):
                    raise ShieldError("Invalid add-on ID")
                endpoint = f"/api/addons/{addon_id}/restore"
            result = self.t.manager(endpoint, "POST", {"backup_id": backup_id})
            self.audit("configuration_restore", addon_id or "checkpoint", backup_id)
            return self.safe(result)
