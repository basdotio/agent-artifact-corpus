"""Platform definitions: supported vendors/models and their whitelisted commands.

Only commands listed here can be executed through the MCP server. This keeps
the server strictly read-only and prevents arbitrary command execution.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommandDef:
    """A single whitelisted command for a platform."""

    name: str  # canonical name used by MCP clients
    command: str  # command template; may contain a {target} placeholder
    description: str
    requires_target: bool = False


@dataclass(frozen=True)
class Platform:
    """A device platform (vendor + OS) with its command whitelist."""

    key: str
    vendor: str
    model: str
    description: str
    commands: tuple[CommandDef, ...]
    # Commands sent once after the shell is opened (e.g. disable paging).
    setup_commands: tuple[str, ...] = ()
    # Regex that must match at the very end of the output buffer to signal
    # that the command finished and the prompt is back.
    prompt_pattern: str = r"[A-Za-z0-9._\-]+[#>]\s*$"


def _c(name: str, command: str, description: str, requires_target: bool = False) -> CommandDef:
    return CommandDef(name=name, command=command, description=description, requires_target=requires_target)


# ---------------------------------------------------------------------------
# Shared command sets
# ---------------------------------------------------------------------------

def _cisco_like_commands() -> tuple[CommandDef, ...]:
    return (
        _c("show ip route", "show ip route", "Show the IPv4 routing table"),
        _c("show interface", "show interface", "Show interface status and statistics"),
        _c("show running-config", "show running-config", "Show the current running configuration"),
        _c("show ip bgp", "show ip bgp", "Show the BGP routing table"),
        _c("show ip bgp summary", "show ip bgp summary", "Show BGP neighbor summary"),
        _c("show version", "show version", "Show device version and hardware information"),
        _c("show log", "show log", "Show the device log"),
        _c("ping", "ping {target}", "Ping a target host or IP address", requires_target=True),
    )


_CISCO_PROMPT = r"[A-Za-z0-9._\-]+[#>]\s*$"
_JUNOS_PROMPT = r"[A-Za-z0-9._\-@]+[#>]\s*$"
_HUAWEI_PROMPT = r"[\[<>][A-Za-z0-9._\-]+[\]>]\s*$"
_MIKROTIK_PROMPT = r"\[[^\]\r\n]*\] [>!]\s*$"

# ---------------------------------------------------------------------------
# Platform registry
# ---------------------------------------------------------------------------

PLATFORMS: dict[str, Platform] = {}


def _register(platform: Platform) -> Platform:
    PLATFORMS[platform.key] = platform
    return platform


# --- MikroTik ---------------------------------------------------------------

_register(
    Platform(
        key="mikrotik-ros6",
        vendor="mikrotik",
        model="RouterOS 6",
        description="MikroTik RouterOS 6",
        commands=(
            _c("/ip route print", "/ip route print", "Show the IPv4 routing table"),
            _c("/ip address print", "/ip address print", "Show IP addresses on all interfaces"),
            _c("/interface print", "/interface print", "Show all interfaces"),
            _c("/routing bgp peer print", "/routing bgp peer print", "Show BGP peers"),
            _c("/routing bgp session print", "/routing bgp session print", "Show BGP sessions"),
            _c("/ip firewall address-list print", "/ip firewall address-list print", "Show firewall address lists"),
            _c("/routing filter print", "/routing filter print", "Show routing filter rules"),
            _c("/log print", "/log print", "Show the device log"),
            _c("/ping", "/ping {target} count=5", "Ping a target host or IP address (5 packets)", requires_target=True),
            _c("/ip neighbor print", "/ip neighbor print", "Show IPv4 neighbors"),
            _c("/ip arp print", "/ip arp print", "Show the ARP table"),
            _c("/export", "/export", "Export the full running configuration"),
            _c("/file print", "/file print", "List files stored on the device"),
        ),
        setup_commands=(),
        prompt_pattern=_MIKROTIK_PROMPT,
    )
)

_register(
    Platform(
        key="mikrotik-ros7",
        vendor="mikrotik",
        model="RouterOS 7",
        description="MikroTik RouterOS 7",
        commands=(
            _c("/ip route print", "/ip route print", "Show the IPv4 routing table"),
            _c("/ip address print", "/ip address print", "Show IP addresses on all interfaces"),
            _c("/interface print", "/interface print", "Show all interfaces"),
            _c("/routing bgp session print", "/routing bgp session print", "Show BGP sessions"),
            _c("/routing bgp connection print", "/routing bgp connection print", "Show BGP connections"),
            _c("/routing route print", "/routing route print", "Show routes from the routing table"),
            _c("/ip firewall address-list print", "/ip firewall address-list print", "Show firewall address lists"),
            _c("/routing filter rule print", "/routing filter rule print", "Show routing filter rules"),
            _c("/routing filter print", "/routing filter print", "Show routing filter configuration"),
            _c("/log print", "/log print", "Show the device log"),
            _c("/ping", "/ping {target} count=5", "Ping a target host or IP address (5 packets)", requires_target=True),
            _c("/ip neighbor print", "/ip neighbor print", "Show IPv4 neighbors"),
            _c("/ip arp print", "/ip arp print", "Show the ARP table"),
            _c("/export", "/export", "Export the full running configuration"),
            _c("/file print", "/file print", "List files stored on the device"),
        ),
        setup_commands=(),
        prompt_pattern=_MIKROTIK_PROMPT,
    )
)

# --- Ruckus -----------------------------------------------------------------

_register(
    Platform(
        key="ruckus-fastiron",
        vendor="ruckus",
        model="FastIron",
        description="Ruckus FastIron switch",
        commands=_cisco_like_commands(),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

# --- Cisco ------------------------------------------------------------------

_register(
    Platform(
        key="cisco-ios",
        vendor="cisco",
        model="IOS",
        description="Cisco IOS router/switch",
        commands=_cisco_like_commands(),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

_register(
    Platform(
        key="cisco-iosxe",
        vendor="cisco",
        model="IOS XE",
        description="Cisco IOS XE router/switch",
        commands=_cisco_like_commands(),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

_register(
    Platform(
        key="cisco-iosxr",
        vendor="cisco",
        model="IOS XR",
        description="Cisco IOS XR router",
        commands=(
            _c("show route", "show route", "Show the routing table"),
            _c("show interface", "show interface", "Show interface status and statistics"),
            _c("show running-config", "show running-config", "Show the current running configuration"),
            _c("show bgp", "show bgp", "Show the BGP routing table"),
            _c("show bgp summary", "show bgp summary", "Show BGP neighbor summary"),
            _c("show version", "show version", "Show device version and hardware information"),
            _c("show log", "show log", "Show the device log"),
            _c("ping", "ping {target}", "Ping a target host or IP address", requires_target=True),
        ),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

_register(
    Platform(
        key="cisco-nxos",
        vendor="cisco",
        model="NX-OS",
        description="Cisco NX-OS switch",
        commands=_cisco_like_commands(),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

# --- Juniper ----------------------------------------------------------------

_register(
    Platform(
        key="juniper-junos",
        vendor="juniper",
        model="Junos",
        description="Juniper Junos router/switch",
        commands=(
            _c("show route", "show route", "Show the routing table"),
            _c("show interfaces", "show interfaces", "Show interface status and statistics"),
            _c("show configuration", "show configuration", "Show the current configuration"),
            _c("show bgp summary", "show bgp summary", "Show BGP neighbor summary"),
            _c("show bgp neighbor", "show bgp neighbor", "Show detailed BGP neighbor information"),
            _c("show version", "show version", "Show device version and hardware information"),
            _c("show log", "show log", "Show the device log"),
            _c("ping", "ping {target}", "Ping a target host or IP address", requires_target=True),
        ),
        setup_commands=("set cli pagination disable",),
        prompt_pattern=_JUNOS_PROMPT,
    )
)

# --- Aruba ------------------------------------------------------------------

_register(
    Platform(
        key="aruba-aos-cx",
        vendor="aruba",
        model="AOS-CX",
        description="Aruba AOS-CX switch",
        commands=(
            _c("show ip route", "show ip route", "Show the IPv4 routing table"),
            _c("show interface", "show interface", "Show interface status and statistics"),
            _c("show running-config", "show running-config", "Show the current running configuration"),
            _c("show bgp", "show bgp", "Show the BGP routing table"),
            _c("show bgp summary", "show bgp summary", "Show BGP neighbor summary"),
            _c("show version", "show version", "Show device version and hardware information"),
            _c("show log", "show log", "Show the device log"),
            _c("ping", "ping {target}", "Ping a target host or IP address", requires_target=True),
        ),
        setup_commands=("terminal length 0",),
        prompt_pattern=_CISCO_PROMPT,
    )
)

# --- Huawei ------------------------------------------------------------------

_register(
    Platform(
        key="huawei-vrp",
        vendor="huawei",
        model="VRP",
        description="Huawei VRP router/switch",
        commands=(
            _c("display ip routing-table", "display ip routing-table", "Show the IPv4 routing table"),
            _c("display interface", "display interface", "Show interface status and statistics"),
            _c("display current-configuration", "display current-configuration", "Show the current configuration"),
            _c("display bgp routing-table", "display bgp routing-table", "Show the BGP routing table"),
            _c("display bgp peer", "display bgp peer", "Show BGP peer information"),
            _c("display version", "display version", "Show device version and hardware information"),
            _c("display logbuffer", "display logbuffer", "Show the device log buffer"),
            _c("ping", "ping {target}", "Ping a target host or IP address", requires_target=True),
        ),
        setup_commands=("screen-length 0 temporary",),
        prompt_pattern=_HUAWEI_PROMPT,
    )
)


def get_platform(key: str) -> Platform | None:
    """Return the platform definition for a key, or None if unknown."""
    return PLATFORMS.get(key)


def list_platforms() -> list[Platform]:
    """Return all registered platforms in a stable order."""
    return sorted(PLATFORMS.values(), key=lambda p: p.key)