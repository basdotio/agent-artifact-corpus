"""Validated FastMCP transport dispatch and inbound origin checks."""

import ipaddress
import re
import warnings
from awslabs.openapi_mcp_server import logger
from enum import Enum
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from urllib.parse import urlsplit


class TransportKind(str, Enum):
    """Supported server transports."""

    STDIO = 'stdio'
    STREAMABLE_HTTP = 'streamable-http'
    SSE = 'sse'

    @classmethod
    def parse(cls, value):
        """Parse supported transport names and the HTTP compatibility alias."""
        if value == 'http':
            value = cls.STREAMABLE_HTTP.value
        try:
            return cls(value)
        except ValueError as error:
            raise ValueError(f'Unknown transport: {value}') from error


def _is_loopback_host(host):
    if host.lower() == 'localhost':
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _is_valid_dns_host(host):
    if ':' in host:
        return _is_valid_ipv6(host)
    return all(
        label
        and len(label) <= 63
        and label[0].isalnum()
        and label[-1].isalnum()
        and all(character.isalnum() or character == '-' for character in label)
        for label in host.rstrip('.').split('.')
    ) and not host.endswith('.')


def _is_valid_ipv6(host):
    try:
        return ipaddress.ip_address(host).version == 6
    except ValueError:
        return False


def _normalize_origin(origin):
    if not isinstance(origin, str) or not origin or origin == 'null':
        raise ValueError(f'Invalid allowed origin: {origin!r}')
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError as error:
        raise ValueError(f'Invalid allowed origin: {origin!r}') from error
    if (
        parsed.scheme.lower() not in {'http', 'https'}
        or not parsed.hostname
        or not _is_valid_dns_host(parsed.hostname)
        or parsed.username is not None
        or parsed.password is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or any(character in origin for character in '*?\\')
        or any(ord(character) < 33 or ord(character) > 126 for character in origin)
        or not re.fullmatch(r'(?:[A-Za-z0-9.-]+|\[[0-9A-Fa-f:.]+\])(?::[0-9]+)?', parsed.netloc)
        or (':' in parsed.hostname and not _is_valid_ipv6(parsed.hostname))
    ):
        raise ValueError(f'Invalid allowed origin: {origin!r}')
    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    if ':' in host:
        host = f'[{host}]'
    if port == (80 if scheme == 'http' else 443):
        port = None
    return f'{scheme}://{host}' + (f':{port}' if port is not None else '')


def _normalize_bind_host(value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Server host must not be empty')
    host = value.strip()
    if host.startswith('['):
        if not host.endswith(']') or not _is_valid_ipv6(host[1:-1]):
            raise ValueError('Server host must be a valid IP address or hostname')
        host = host[1:-1]
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        if not re.fullmatch(r'[A-Za-z0-9.-]+', host) or not _is_valid_dns_host(host):
            raise ValueError('Server host must be a valid IP address or hostname')
        return host.lower()


def validate_transport_config(config):
    """Validate transport-facing configuration before API or spec I/O."""
    kind = TransportKind.parse(config.transport)
    if (
        isinstance(config.port, bool)
        or not isinstance(config.port, int)
        or not 1 <= config.port <= 65535
    ):
        raise ValueError('Server port must be an integer between 1 and 65535')
    host = _normalize_bind_host(config.host)
    if (
        kind is not TransportKind.STDIO
        and not _is_loopback_host(host)
        and not config.allow_remote_bind
    ):
        raise ValueError(
            'Non-loopback server host requires --allow-remote-bind or ALLOW_REMOTE_BIND=true'
        )
    if kind is TransportKind.STREAMABLE_HTTP:
        path = config.http_path
        if (
            not isinstance(path, str)
            or not path.startswith('/')
            or path.startswith('//')
            or any(character in path for character in '?#\\')
            or any(ord(character) < 32 or character.isspace() for character in path)
        ):
            raise ValueError(
                'HTTP path must be an absolute endpoint path without URL, query, or fragment'
            )
    for origin in config.allowed_origins:
        _normalize_origin(origin)
    return kind


class ExplicitOriginMiddleware:
    """Enforce explicit Host and Origin allowlists on network transports."""

    def __init__(self, app, allowed_origins, loopback_only, allowed_hosts=None):
        """Initialize inbound allowlists used for each HTTP request."""
        self.app = app
        self.allowed_origins = {_normalize_origin(origin) for origin in allowed_origins}
        self.loopback_only = loopback_only
        self.allowed_hosts = (
            {_normalize_host_header(host) for host in allowed_hosts}
            if allowed_hosts is not None
            else None
        )

    async def __call__(self, scope, receive, send):
        """Reject requests with untrusted or malformed inbound headers."""
        if scope['type'] != 'http':
            await self.app(scope, receive, send)
            return

        header_values = {}
        for name, value in scope.get('headers', []):
            header_values.setdefault(name.lower(), []).append(value)
        origins = header_values.get(b'origin', [])
        hosts = header_values.get(b'host', [])
        if len(origins) > 1 or len(hosts) != 1:
            await PlainTextResponse('Invalid Host or Origin', status_code=421)(scope, receive, send)
            return
        try:
            request_host = _normalize_host_header(hosts[0].decode('ascii'))
        except (UnicodeDecodeError, ValueError):
            await PlainTextResponse('Invalid Host', status_code=421)(scope, receive, send)
            return
        if self.allowed_hosts is not None and request_host.lower() not in self.allowed_hosts:
            await PlainTextResponse('Misdirected Request', status_code=421)(scope, receive, send)
            return

        origin = origins[0] if origins else None
        if origin is None:
            await self.app(scope, receive, send)
            return

        try:
            origin_text = origin.decode('ascii')
            normalized = _normalize_origin(origin_text)
            origin_host = urlsplit(normalized).hostname or ''
        except (UnicodeDecodeError, ValueError):
            await PlainTextResponse('Forbidden Origin', status_code=403)(scope, receive, send)
            return

        if self.allowed_origins:
            allowed = normalized in self.allowed_origins
        else:
            allowed = (
                self.loopback_only
                and _is_loopback_host(origin_host)
                and _is_loopback_host(request_host)
            )
        if not allowed:
            await PlainTextResponse('Forbidden Origin', status_code=403)(scope, receive, send)
            return
        await self.app(scope, receive, send)


def _normalize_host_header(value):
    if not value or any(character.isspace() for character in value):
        raise ValueError('Invalid Host header')
    if value.startswith('['):
        closing = value.find(']')
        if closing < 0:
            raise ValueError('Invalid Host header')
        host = value[1:closing]
        suffix = value[closing + 1 :]
        if suffix and not re.fullmatch(r':[0-9]+', suffix):
            raise ValueError('Invalid Host header')
        if not _is_valid_ipv6(host):
            raise ValueError('Invalid Host header')
        return ipaddress.ip_address(host).compressed
    if value.count(':') > 1:
        raise ValueError('Invalid Host header')
    host, separator, port = value.partition(':')
    if not host or (separator and (not port.isdigit() or int(port) > 65535)):
        raise ValueError('Invalid Host header')
    if not re.fullmatch(r'[A-Za-z0-9.-]+', host):
        raise ValueError('Invalid Host header')
    try:
        return ipaddress.ip_address(host).compressed
    except ValueError:
        return host.lower()


def is_remote_binding(config):
    """Return whether a configured network transport binds beyond loopback."""
    return TransportKind.parse(
        config.transport
    ) is not TransportKind.STDIO and not _is_loopback_host(config.host.strip().strip('[]'))


def _allowed_hosts(config):
    hosts = ['127.0.0.1', 'localhost', '[::1]']
    configured_host = _normalize_bind_host(config.host)
    if configured_host not in {'0.0.0.0', '::', ''}:
        hosts.append(f'[{configured_host}]' if ':' in configured_host else configured_host)
    for origin in config.allowed_origins:
        hostname = urlsplit(_normalize_origin(origin)).hostname
        if hostname:
            hosts.append(f'[{hostname}]' if ':' in hostname else hostname)
    return list(dict.fromkeys(hosts))


def run_transport(server, config):
    """Run a configured FastMCP server through the public transport API."""
    kind = validate_transport_config(config)
    if kind is TransportKind.STDIO:
        server.run(transport=kind.value)
        return
    if kind is TransportKind.SSE:
        warning = 'SSE transport is deprecated; prefer streamable HTTP transport'
        logger.warning(warning)
        warnings.warn(warning, DeprecationWarning, stacklevel=2)
        path = '/sse'
    else:
        path = config.http_path
    allowed_hosts = _allowed_hosts(config)
    server.run(
        transport=kind.value,
        host=_normalize_bind_host(config.host),
        port=config.port,
        path=path,
        host_origin_protection=True,
        allowed_hosts=allowed_hosts,
        allowed_origins=list(config.allowed_origins),
        middleware=[
            Middleware(
                ExplicitOriginMiddleware,
                allowed_origins=list(config.allowed_origins),
                loopback_only=not bool(config.allowed_origins),
                allowed_hosts=allowed_hosts,
            )
        ],
    )
