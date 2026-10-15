"""Recorded DNS answers, and NAT64 answers as the IPv4 addresses they encode.

On a network with DNS64 (IPv6 mobile networks, phone tethering) a public IPv4 host resolves to
64:ff9b::<its IPv4 address>. Python calls that prefix reserved, so the MCP server's and SDK's
public-address checks refuse every such host as "blocked": the cause of 123 failed benchmark
rows on 2026-10-06. Those answers are translated back to the IPv4 address they carry, which is
what the operating system connects to, so the code under test sees the same addresses on every
network. (The checks themselves should look inside the prefix; that is a separate change.)

Recorded answers:

The MCP server checks that every host resolves to a public address before it sends a request,
and that check runs above the HTTP cassette: with DNS briefly down, a request the cassette
could answer is refused as "blocked" (123 benchmark rows on 2026-10-06). Successful lookups are
stored; a lookup that fails is answered from the store when the host is in it, and raises as
before when it is not. The public-address check itself is unchanged.
"""

from __future__ import annotations

import json
import os
import socket
import tempfile
import threading
from pathlib import Path
import ipaddress
from typing import Any

NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _unwrap_nat64(infos: list[Any]) -> list[Any]:
    out, seen = [], set()
    for family, kind, proto, canon, addr in infos:
        if family == socket.AF_INET6:
            ip = ipaddress.ip_address(addr[0])
            if ip in NAT64:
                family, addr = socket.AF_INET, (str(ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF)), addr[1])
        key = (family, kind, proto, addr)
        if key not in seen:
            seen.add(key)
            out.append((family, kind, proto, canon, addr))
    return out

_lock = threading.Lock()


def install(path: Path) -> None:
    store: dict[str, list[list[Any]]] = json.loads(path.read_text()) if path.is_file() else {}
    original = socket.getaddrinfo

    def key(host: Any, port: Any, *args: Any, **kwargs: Any) -> str:
        return json.dumps([str(host), str(port), [str(a) for a in args], sorted((k, str(v)) for k, v in kwargs.items())])

    def getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> list[Any]:
        k = key(host, port, *args, **kwargs)
        try:
            infos = _unwrap_nat64(original(host, port, *args, **kwargs))
        except socket.gaierror:
            if k in store:
                return [(socket.AddressFamily(f), socket.SocketKind(t), p, c, tuple(a)) for f, t, p, c, a in store[k]]
            raise
        record = [[int(f), int(t), p, c, list(a)] for f, t, p, c, a in infos]
        if store.get(k) != record:
            with _lock:
                store[k] = record
                fd, tmp = tempfile.mkstemp(dir=str(path.parent))
                with os.fdopen(fd, "w") as handle:
                    json.dump(store, handle)
                os.replace(tmp, path)
        return infos

    socket.getaddrinfo = getaddrinfo  # type: ignore[assignment]
