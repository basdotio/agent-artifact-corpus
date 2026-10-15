"""Explicit, single-device configuration. No LAN discovery; secrets stay private."""

import ipaddress
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:  # mcp 1.x
    from mcp.server.fastmcp.exceptions import ToolError
except ImportError:
    try:  # mcp 2.x only shows ToolError messages to clients; other errors are masked.
        from mcp.server.mcpserver.exceptions import ToolError
    except ImportError:
        ToolError = Exception


class ShieldError(ToolError):
    """An actionable error safe to return to an MCP client."""

    def __init__(self, message, kind="unknown"):
        # The kind is part of the text: MCP clients only see the message.
        super().__init__(message if kind == "unknown" else f"{message} [{kind}]")
        self.message = message
        self.kind = kind
        self.reason_code = kind
        self.operation = None


def private_host(host: str) -> str:
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ShieldError(
            "Device host must be a private LAN IP (ANDROID_TV_HOST, SHIELD_HOST or APPLE_TV_HOST), not a URL or hostname"
        ) from None
    if (
        not (address.is_private or address.is_loopback)
        or address.is_unspecified
        or address.is_multicast
    ):
        raise ShieldError("Use a private LAN IP address; public endpoints are not supported")
    return host


def port(value: str) -> int:
    try:
        number = int(value)
    except ValueError:
        raise ShieldError("Ports must be integers") from None
    if not 1 <= number <= 65535:
        raise ShieldError("Port must be between 1 and 65535")
    return number


def device_env(name, legacy, default="", convert=str):
    """Accept the portable name and the original name without selecting two targets."""
    current, old = os.environ.get(name), os.environ.get(legacy)
    if current is not None and old is not None and convert(current) != convert(old):
        raise ShieldError(f"{name} and {legacy} conflict; configure only one device")
    return convert(current if current is not None else old if old is not None else default)


def packages(value: str) -> tuple[str, ...]:
    names = tuple(item.strip() for item in value.split(",") if item.strip())
    for name in names:
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:\.[A-Za-z][A-Za-z0-9_]*)+", name):
            raise ShieldError("NVIDIA_MCP_EXTRA_LAUNCHERS must list Android package names")
    return names


def setting_ids(value: str) -> tuple[str, ...]:
    names = tuple(item.strip() for item in value.split(",") if item.strip())
    if any(not re.fullmatch(r"[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+", name) for name in names):
        raise ShieldError("NVIDIA_MCP_ALLOW_SETTINGS must list exact Kodi setting ids")
    return names


def fingerprint(value: str) -> str:
    """Normalise a SHA-256 certificate fingerprint (hex, optionally colon-separated)."""
    value = value.strip().replace(":", "").lower()
    if not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ShieldError("Trusted APK signers must be SHA-256 certificate fingerprints")
    return value


def signers(value: str, path: str = "") -> frozenset[str]:
    items = [item for item in value.split(",") if item.strip()]
    if path:
        try:
            lines = Path(path).expanduser().read_text(encoding="utf-8").splitlines()
        except OSError:
            raise ShieldError("NVIDIA_MCP_TRUSTED_SIGNERS_FILE cannot be read") from None
        items += [line.split("#", 1)[0] for line in lines if line.split("#", 1)[0].strip()]
    return frozenset(fingerprint(item) for item in items)


def count(value: str) -> int:
    if not value.strip().isdigit() or int(value) > 100_000:
        raise ShieldError("Retention settings must be whole numbers")
    return int(value)


def state_path() -> Path:
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "nvidia-mcp"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "nvidia-mcp"
    # Empty or relative XDG_DATA_HOME is invalid (XDG spec); it must not mean the cwd.
    data = os.environ.get("XDG_DATA_HOME", "")
    return Path(data if os.path.isabs(data) else Path.home() / ".local/share") / "nvidia-mcp"


@dataclass(frozen=True)
class Config:
    host: str
    adb_port: int = 5555
    adb_path: str = "adb"
    kodi_port: int = 8080
    username: str = field(default="", repr=False)
    password: str = field(default="", repr=False)
    manager_port: int = 8765
    manager_token: str = field(default="", repr=False)
    mount: Path | None = None
    state: Path = field(default_factory=state_path)
    allow_writes: bool = False
    allow_plugin_browse: bool = False
    # Second, human-set opt-in for model-supplied "interrupt anyway" flags.
    allow_interrupt: bool = False
    # Human-set opt-in for kodi_lifecycle's model-supplied allow_offline_recovery flag.
    allow_offline_recovery: bool = False
    extra_launchers: tuple[str, ...] = ()
    # Exact protected Kodi setting ids an advanced user allows kodi_set_setting to change.
    allow_settings: tuple[str, ...] = ()
    # SHA-256 APK signer fingerprints trusted for *new* app installs. Human-configured only.
    trusted_signers: frozenset[str] = frozenset()
    # Local state retention (see retention.py). 0 days disables backup pruning.
    retention_days: int = 90
    keep_file_backups: int = 50
    keep_apk_backups: int = 3
    remote_root: str = "/sdcard/Android/data/org.xbmc.kodi/files/.kodi"
    aapt2_path: str = "aapt2"
    apksigner_path: str = "apksigner"
    java_path: str = "java"
    http_route: str = "direct"
    platform: str = "android"
    apple_credentials: Path | None = field(default=None, repr=False)
    apple_kodi_app_id: str = ""

    @classmethod
    def from_env(cls):
        platform = os.environ.get("NVIDIA_MCP_PLATFORM", "android")
        if platform not in ("android", "apple_tv"):
            raise ShieldError("NVIDIA_MCP_PLATFORM must be android or apple_tv")
        if platform == "apple_tv":
            host = private_host(os.environ.get("APPLE_TV_HOST", ""))
            if any(
                os.environ.get(name) not in (None, host)
                for name in ("ANDROID_TV_HOST", "SHIELD_HOST")
            ):
                raise ShieldError(
                    "Apple TV and Android host settings conflict; configure one target"
                )
        else:
            host = device_env("ANDROID_TV_HOST", "SHIELD_HOST", convert=private_host)
        route = os.environ.get("KODI_HTTP_ROUTE", "direct")
        if route not in ("direct", "forward", "auto"):
            raise ShieldError("KODI_HTTP_ROUTE must be direct, forward or auto")
        if platform == "apple_tv" and route != "direct":
            raise ShieldError(
                "Apple TV uses direct Kodi/Manager HTTP; ADB forwarding is unavailable"
            )
        root = os.environ.get("KODI_REMOTE_ROOT", cls.remote_root)
        if not re.fullmatch(
            r"/(?:sdcard|storage/emulated/0)/[A-Za-z0-9_./-]+", root
        ) or ".." in root.split("/"):
            raise ShieldError(
                "KODI_REMOTE_ROOT must be an absolute path inside Android shared storage"
            )
        mount = os.environ.get("KODI_MOUNT")
        return cls(
            host=host,
            platform=platform,
            apple_credentials=Path(os.environ["APPLE_TV_CREDENTIALS_FILE"]).expanduser().resolve()
            if os.environ.get("APPLE_TV_CREDENTIALS_FILE")
            else None,
            apple_kodi_app_id=os.environ.get("APPLE_TV_KODI_APP_ID", ""),
            adb_port=device_env("ANDROID_TV_ADB_PORT", "SHIELD_ADB_PORT", "5555", port),
            adb_path=os.environ.get("ADB_PATH", "adb"),
            kodi_port=port(os.environ.get("KODI_PORT", "8080")),
            username=os.environ.get("KODI_USERNAME", ""),
            password=os.environ.get("KODI_PASSWORD", ""),
            manager_port=port(os.environ.get("KODI_MANAGER_PORT", "8765")),
            manager_token=os.environ.get("KODI_MANAGER_TOKEN", ""),
            mount=Path(mount).expanduser().resolve() if mount else None,
            state=Path(os.environ.get("NVIDIA_MCP_STATE_DIR") or state_path())
            .expanduser()
            .resolve(),
            allow_writes=os.environ.get("NVIDIA_MCP_ALLOW_WRITES", "0") == "1",
            allow_plugin_browse=os.environ.get("NVIDIA_MCP_ALLOW_PLUGIN_BROWSE", "0") == "1",
            allow_interrupt=os.environ.get("NVIDIA_MCP_ALLOW_INTERRUPT", "0") == "1",
            allow_offline_recovery=os.environ.get("NVIDIA_MCP_ALLOW_OFFLINE_RECOVERY", "0") == "1",
            extra_launchers=packages(os.environ.get("NVIDIA_MCP_EXTRA_LAUNCHERS", "")),
            allow_settings=setting_ids(os.environ.get("NVIDIA_MCP_ALLOW_SETTINGS", "")),
            trusted_signers=signers(
                os.environ.get("NVIDIA_MCP_TRUSTED_SIGNERS", ""),
                os.environ.get("NVIDIA_MCP_TRUSTED_SIGNERS_FILE", ""),
            ),
            retention_days=count(os.environ.get("NVIDIA_MCP_RETENTION_DAYS", "90")),
            keep_file_backups=count(os.environ.get("NVIDIA_MCP_KEEP_FILE_BACKUPS", "50")),
            keep_apk_backups=count(os.environ.get("NVIDIA_MCP_KEEP_APK_BACKUPS", "3")),
            remote_root=root.rstrip("/"),
            aapt2_path=os.environ.get("AAPT2_PATH", "aapt2"),
            apksigner_path=os.environ.get("APKSIGNER_PATH", "apksigner"),
            java_path=os.environ.get("JAVA_PATH", "java"),
            http_route=route,
        )

    @property
    def serial(self):
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"{host}:{self.adb_port}"

    def url(self, manager=False):
        host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{host}:{self.manager_port if manager else self.kodi_port}"
