"""SSRF validation for outbound HTTP(S) fetches.

Rules:
- Only HTTP and HTTPS URLs are allowed.
- Empty hosts, localhost, *.localhost, and URL credentials are rejected.
- URL structure, including port ranges, is validated before any request.
- IP literals are checked directly.
- Hostnames are converted to their ASCII IDNA representation before DNS.
- DNS resolution uses AF_UNSPEC + SOCK_STREAM, matching normal HTTP
  connection resolution while avoiding duplicate socket-type results.
- Every resolved address must pass the outbound IP policy. Mixed public/private
  DNS answers are rejected fail-closed.
- Reserved address space is rejected explicitly in addition to non-global,
  multicast, and unspecified destinations.
- IPv4-mapped IPv6 addresses are evaluated using their embedded IPv4 address.
- IPv4 addresses embedded in the RFC 6052 well-known NAT64 prefix and in
  6to4 addresses are evaluated using the same IPv4 policy.
- Numeric IPv4 forms such as ``2130706433`` intentionally fall through to
  DNS resolution; the resolved destination is then subjected to the same
  IP policy.

Transport boundary and limitations:
- transport.py validates DNS immediately before connecting to a numeric IP.
  The connection retains the original hostname for TLS verification and SNI.
- RFC 6052 network-specific translation prefixes are not decoded because their
  prefix is deployment-specific and cannot be inferred reliably from an
  arbitrary IPv6 address.
- The DNS timeout bounds how long this coroutine waits, but cancellation does
  not necessarily terminate an underlying resolver worker immediately.
- Hostname normalization uses HTTPX's own IDNA implementation.
"""

import asyncio
import ipaddress
import socket
from urllib.parse import urlsplit

import httpx

_DNS_TIMEOUT_S = 5.0

_NAT64_WELL_KNOWN_PREFIX = ipaddress.ip_network("64:ff9b::/96")
_SIX_TO_FOUR_PREFIX = ipaddress.ip_network("2002::/16")

_IPAddress = ipaddress.IPv4Address | ipaddress.IPv6Address


class SecurityError(ValueError):
    """Raised when a URL is not safe for outbound fetching."""


def _embedded_nat64_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address:
    """Return the IPv4 address embedded in the well-known NAT64 prefix."""
    return ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)


def _embedded_6to4_ipv4(ip: ipaddress.IPv6Address) -> ipaddress.IPv4Address:
    """Return the IPv4 gateway address embedded in a 6to4 address."""
    return ipaddress.IPv4Address((int(ip) >> 80) & 0xFFFFFFFF)


def _is_blocked(ip: _IPAddress) -> bool:
    """Return whether an IP address is unsafe for outbound fetching."""
    if isinstance(ip, ipaddress.IPv6Address):
        mapped_ipv4 = ip.ipv4_mapped
        if mapped_ipv4 is not None:
            return _is_blocked(mapped_ipv4)

        if ip in _NAT64_WELL_KNOWN_PREFIX:
            return _is_blocked(_embedded_nat64_ipv4(ip))

        if ip in _SIX_TO_FOUR_PREFIX:
            return _is_blocked(_embedded_6to4_ipv4(ip))

    return not ip.is_global or ip.is_reserved or ip.is_multicast or ip.is_unspecified


def normalize_hostname(host: str) -> str:
    """Normalize a hostname using HTTPX semantics, without resolving DNS."""
    try:
        authority = f"[{host}]" if ":" in host else host
        return httpx.URL(f"https://{authority}/").raw_host.decode("ascii")
    except (UnicodeError, httpx.InvalidURL) as exc:
        raise SecurityError(f"invalid hostname: {host!r}") from exc


async def _resolve_host(host: str) -> set[_IPAddress]:
    """Resolve a hostname to unique SOCK_STREAM-capable IP addresses.

    Extracted as a module-level function so tests can replace DNS resolution
    without patching the running event loop. Resolution failures and timeouts
    fail closed.
    """
    loop = asyncio.get_running_loop()

    try:
        infos = await asyncio.wait_for(
            loop.getaddrinfo(
                normalize_hostname(host),
                None,
                family=socket.AF_UNSPEC,
                type=socket.SOCK_STREAM,
            ),
            timeout=_DNS_TIMEOUT_S,
        )
    except TimeoutError as exc:
        # Must precede OSError: TimeoutError is an OSError subclass.
        raise SecurityError(f"DNS resolution timed out: {host}") from exc
    except OSError as exc:
        raise SecurityError(f"DNS failed for {host}: {exc}") from exc

    addresses: set[_IPAddress] = set()

    for info in infos:
        raw_address = info[4][0]

        try:
            address = ipaddress.ip_address(raw_address)
        except ValueError as exc:
            raise SecurityError(
                f"DNS returned an invalid address for {host}: {raw_address!r}"
            ) from exc

        addresses.add(address)

    if not addresses:
        raise SecurityError(f"DNS returned no addresses for {host}")

    return addresses


async def validate_url(url: str) -> set[_IPAddress]:
    """Validate a URL before it is used for outbound fetching.

    Raises:
        SecurityError: If the URL is malformed or could resolve to an unsafe
            destination.
    """
    if any(ord(char) < 32 or ord(char) == 127 for char in url) or "\\" in url:
        raise SecurityError("control characters and backslashes in URL not allowed")
    try:
        parsed = urlsplit(url)
        hostname = parsed.hostname
        _ = parsed.port
    except ValueError as exc:
        raise SecurityError(f"invalid URL: {exc}") from exc

    if parsed.scheme.lower() not in {"http", "https"}:
        raise SecurityError(f"scheme not allowed: {parsed.scheme!r}")

    if parsed.username is not None or parsed.password is not None:
        raise SecurityError("credentials in URL not allowed")

    host = (hostname or "").rstrip(".").lower()

    if "%" in host:
        raise SecurityError("escaped or scoped host not allowed")

    if not host or host == "localhost" or host.endswith(".localhost"):
        raise SecurityError("blocked host")

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        addresses = await _resolve_host(host)
    else:
        if _is_blocked(literal):
            raise SecurityError(f"blocked IP: {literal}")
        return {literal}

    # Mixed A/AAAA answer: one blocked destination rejects the whole URL.
    for address in addresses:
        if _is_blocked(address):
            raise SecurityError(f"DNS -> blocked IP: {address}")

    return addresses
