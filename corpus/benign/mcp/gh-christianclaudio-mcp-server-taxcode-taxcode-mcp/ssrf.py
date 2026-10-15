"""Shared SSRF checks for caller- or config-controlled outbound URLs.

Leaf servers that fetch a URL supplied by a tool argument or by configuration
should call :func:`validate_outbound_url` before the request. Rejection raises
:class:`SSRFValidationError`; it never returns the original URL unchanged after
a failed check.

HTTPS is required unless the host is listed in ``http_required_hosts``. Those
hosts are the only ones allowed to use ``http://``, and when ``allowed_hosts``
is also set the host must appear there too. Literal private, loopback,
link-local, multicast, reserved, and metadata addresses are blocked, including
obscured IPv4 forms (decimal, octal, hex, and short dotted forms).

DNS rebinding is a separate, request-time check. Use
:func:`validate_resolved_host` (off the event loop; see
``SSRFSafeAsyncTransport``) so a public name cannot resolve to an internal
address at connect time.
"""

from __future__ import annotations

import ipaddress
import re
import socket
from collections.abc import Collection
from typing import Literal
from urllib.parse import urlparse

SSRFReason = Literal[
    "empty",
    "invalid",
    "scheme",
    "missing_hostname",
    "userinfo",
    "blocked_hostname",
    "blocked_ip",
    "invalid_ip",
    "allowlist",
    "insecure_http",
    "dns_failure",
]

_BLOCKED_HOSTS = frozenset(
    {
        "localhost",
        "localhost.localdomain",
        "metadata.google.internal",
        "metadata.goog",
    }
)
_BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".localdomain")

_OBSCURE_IPV4_RE = re.compile(
    r"(?:0x[0-9a-f]+|\d+)(?:\.(?:0x[0-9a-f]+|\d+)){0,3}",
    flags=re.IGNORECASE,
)
_IPV4_WIDTHS: dict[int, tuple[int, ...]] = {
    1: (32,),
    2: (8, 24),
    3: (8, 8, 16),
    4: (8, 8, 8, 8),
}


class SSRFValidationError(ValueError):
    """Raised when an outbound URL or resolved address fails SSRF validation."""

    def __init__(
        self,
        message: str,
        *,
        reason: SSRFReason,
        hostname: str | None = None,
        resolved_ip: str | None = None,
    ) -> None:
        super().__init__(message)
        self.reason = reason
        self.hostname = hostname
        self.resolved_ip = resolved_ip


def validate_outbound_url(
    url: str,
    *,
    allowed_hosts: Collection[str] | str | None = None,
    http_required_hosts: Collection[str] | str | None = None,
) -> str:
    """Validate ``url`` and return it stripped of surrounding whitespace.

    Args:
        url: Absolute URL to fetch. Must be ``http`` or ``https``.
        allowed_hosts: Optional leaf-specific host allowlist. ``None`` does not
            restrict the host. A string is split on commas. An empty allowlist
            matches nothing.
        http_required_hosts: Hosts that must be contacted with ``http://``.
            Every other host must use ``https://``. When ``allowed_hosts`` is
            set, an HTTP host must be present in both lists.

    Raises:
        SSRFValidationError: The URL is unsafe. The exception message states
            why; callers must not treat a raise as success.
    """
    candidate = url.strip()
    if not candidate:
        raise SSRFValidationError("Outbound URL is empty.", reason="empty")
    if "\\" in candidate or any(ord(char) < 32 for char in candidate):
        raise SSRFValidationError(
            "Outbound URL contains illegal characters.",
            reason="invalid",
        )

    parsed = urlparse(candidate)
    scheme = parsed.scheme.lower()
    if scheme not in {"http", "https"}:
        shown = scheme or "(none)"
        raise SSRFValidationError(
            f"Outbound URL scheme {shown!r} is not permitted; only http and https are allowed.",
            reason="scheme",
        )
    if parsed.username is not None or parsed.password is not None:
        raise SSRFValidationError(
            "Outbound URL must not include userinfo credentials.",
            reason="userinfo",
        )

    raw_host = parsed.hostname
    if not raw_host:
        raise SSRFValidationError(
            "Outbound URL is missing a hostname.",
            reason="missing_hostname",
        )
    host = raw_host.rstrip(".").lower()
    if host in _BLOCKED_HOSTS or host.endswith(_BLOCKED_SUFFIXES):
        raise SSRFValidationError(
            f"Blocked internal, loopback, or metadata hostname: {host}",
            reason="blocked_hostname",
            hostname=host,
        )

    literal = _literal_ip(host)
    if literal is not None and _ip_is_blocked(literal):
        raise SSRFValidationError(
            f"Blocked private, link-local, loopback, or metadata address: {host}",
            reason="blocked_ip",
            hostname=host,
        )

    permitted = _host_set(allowed_hosts)
    if permitted is not None and host not in permitted:
        raise SSRFValidationError(
            f"Hostname {host!r} is not in the outbound host allowlist.",
            reason="allowlist",
            hostname=host,
        )

    if scheme == "http":
        http_hosts = _host_set(http_required_hosts)
        if http_hosts is None or host not in http_hosts:
            raise SSRFValidationError(
                "Outbound URL must use HTTPS. HTTP is permitted only for an explicitly "
                "configured allowlisted host.",
                reason="insecure_http",
                hostname=host,
            )
    return candidate


def validate_resolved_host(hostname: str) -> None:
    """Reject a hostname that is, or resolves to, a non-global address.

    ``example.com`` and names under it skip DNS so placeholder templates stay
    usable offline. Run this in a worker thread when calling from an event loop.
    """
    host = hostname.rstrip(".").lower()
    if host == "example.com" or host.endswith(".example.com"):
        return

    literal = _literal_ip(host)
    if literal is not None:
        if _ip_is_blocked(literal):
            raise SSRFValidationError(
                f"Blocked private, link-local, loopback, or metadata address: {host}",
                reason="blocked_ip",
                hostname=host,
            )
        return

    try:
        resolved = socket.getaddrinfo(host, None)
    except socket.gaierror as exc:
        raise SSRFValidationError(
            f"Could not resolve hostname: {host}",
            reason="dns_failure",
            hostname=host,
        ) from exc

    found = False
    for _, _, _, _, sockaddr in resolved:
        found = True
        resolved_ip = ipaddress.ip_address(sockaddr[0])
        if _ip_is_blocked(resolved_ip):
            raise SSRFValidationError(
                f"Blocked hostname {host!r} resolving to a non-global address: {sockaddr[0]}",
                reason="blocked_ip",
                hostname=host,
                resolved_ip=str(sockaddr[0]),
            )
    if not found:
        raise SSRFValidationError(
            f"Could not resolve hostname: {host}",
            reason="dns_failure",
            hostname=host,
        )


def _host_set(hosts: Collection[str] | str | None) -> frozenset[str] | None:
    """Normalize an allowlist. ``None`` means unrestricted; a string is comma-separated."""
    if hosts is None:
        return None
    items = hosts.split(",") if isinstance(hosts, str) else hosts
    return frozenset(item.strip().lower().rstrip(".") for item in items if item.strip())


def _ip_is_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Return True for addresses that must not be used as outbound destinations.

    Multicast can report ``is_global`` in this Python, so it is checked explicitly.
    Shared address space such as ``100.64.0.0/10`` is not marked private and is
    rejected because it is not globally routable.
    """
    return bool(
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
        or not ip.is_global
    )


def _literal_ip(hostname: str) -> ipaddress.IPv4Address | ipaddress.IPv6Address | None:
    """Parse a hostname that is an IP literal, including obscured IPv4 forms."""
    try:
        return ipaddress.ip_address(hostname)
    except ValueError:
        return _obscure_ipv4(hostname)


def _obscure_ipv4(text: str) -> ipaddress.IPv4Address | None:
    """Decode decimal, octal, hex, and short-form IPv4 literals.

    Returns ``None`` when ``text`` is not shaped like an IPv4 literal. Raises
    when it is shaped like one but the value is not a legal address, so those
    forms cannot fall through as ordinary hostnames.
    """
    if _OBSCURE_IPV4_RE.fullmatch(text) is None:
        return None
    parts = text.split(".")
    widths = _IPV4_WIDTHS[len(parts)]
    packed = 0
    for part, width in zip(parts, widths, strict=True):
        try:
            value = _parse_ipv4_component(part)
        except ValueError as exc:
            raise SSRFValidationError(
                f"Outbound URL hostname is not a valid IP address: {text}",
                reason="invalid_ip",
                hostname=text,
            ) from exc
        if value >= (1 << width):
            raise SSRFValidationError(
                f"Outbound URL hostname is not a valid IP address: {text}",
                reason="invalid_ip",
                hostname=text,
            )
        packed = (packed << width) | value
    return ipaddress.IPv4Address(packed)


def _parse_ipv4_component(part: str) -> int:
    """Parse one IPv4 component, honoring ``0x`` hex and leading-zero octal."""
    if part.lower().startswith("0x"):
        return int(part, 16)
    if len(part) > 1 and part.startswith("0"):
        return int(part, 8)
    return int(part, 10)
