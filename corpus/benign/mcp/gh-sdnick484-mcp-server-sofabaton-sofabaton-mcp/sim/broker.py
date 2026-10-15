"""A small MQTT 3.1.1 broker, for tests and `simulate`. Not for production.

Why write one: the MQTT tests and the simulator should run with nothing
installed. It speaks the slice of MQTT 3.1.1 (the OASIS standard, so nothing
here is guessed) that our client and the fake X2 use: CONNECT with optional
username/password, SUBSCRIBE / UNSUBSCRIBE with + and # wildcards, PUBLISH at
QoS 0 and 1, retained messages, PINGREQ, DISCONNECT. Everything is delivered
at QoS 0. No persistence, no QoS 2, no wills, no MQTT 5.

The same tests also run against a real broker (mosquitto in CI) when
MQTT_TEST_BROKER is set, so they can't come to rely on this broker's quirks.

Test hooks: ``published`` logs every PUBLISH; ``kick()`` drops every client
(a broker restart); ``users`` turns on username/password checks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import struct
from dataclasses import dataclass, field

log = logging.getLogger(__name__)

CONNECT, CONNACK, PUBLISH, PUBACK, SUBSCRIBE, SUBACK = 1, 2, 3, 4, 8, 9
UNSUBSCRIBE, UNSUBACK, PINGREQ, PINGRESP, DISCONNECT = 10, 11, 12, 13, 14
RC_ACCEPTED, RC_BAD_PROTOCOL, RC_BAD_CREDENTIALS, RC_NOT_AUTHORIZED = 0, 1, 4, 5


def topic_matches(pattern: str, topic: str) -> bool:
    """MQTT filter matching: '+' is one level, '#' (last) is the rest."""
    p, t = pattern.split("/"), topic.split("/")
    if topic.startswith("$") and p[0] in ("+", "#"):
        return False
    for i, part in enumerate(p):
        if part == "#":
            return True
        if i >= len(t) or (part != "+" and part != t[i]):
            return False
    return len(p) == len(t)


def _varint(n: int) -> bytes:
    out = bytearray()
    while True:
        byte, n = n % 128, n // 128
        out.append(byte | (0x80 if n else 0))
        if not n:
            return bytes(out)


def _str(s: str) -> bytes:
    b = s.encode()
    return struct.pack("!H", len(b)) + b


def _packet(first: int, body: bytes) -> bytes:
    return bytes([first]) + _varint(len(body)) + body


@dataclass
class Published:
    topic: str
    payload: bytes
    retain: bool
    client_id: str


@dataclass
class _Session:
    client_id: str
    writer: asyncio.StreamWriter
    filters: set[str] = field(default_factory=set)

    async def deliver(self, topic: str, payload: bytes, retain: bool) -> None:
        if self.writer.is_closing():
            return
        self.writer.write(_packet((PUBLISH << 4) | (1 if retain else 0), _str(topic) + payload))
        with contextlib.suppress(ConnectionError):
            await self.writer.drain()


class Broker:
    def __init__(self, host: str = "127.0.0.1", port: int = 0, users: dict[str, str] | None = None) -> None:
        self.host, self.port = host, port
        self.users = users  # None: anyone may connect
        self.retained: dict[str, bytes] = {}
        self.published: list[Published] = []
        self.sessions: list[_Session] = []
        self._server: asyncio.Server | None = None

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._client, self.host, self.port)
        self.port = self._server.sockets[0].getsockname()[1]
        return self.port

    async def stop(self) -> None:
        await self.kick()
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

    async def kick(self) -> None:
        """Drop every client, like a broker restart."""
        for s in list(self.sessions):
            s.writer.close()
        self.sessions.clear()

    async def publish(self, topic: str, payload: bytes, retain: bool = False, client_id: str = "<broker>") -> None:
        self.published.append(Published(topic, payload, retain, client_id))
        if retain:
            if payload:
                self.retained[topic] = payload
            else:
                self.retained.pop(topic, None)
        for s in list(self.sessions):
            if any(topic_matches(f, topic) for f in s.filters):
                await s.deliver(topic, payload, retain=False)

    # --- one client connection ----------------------------------------------------
    async def _read_packet(self, reader: asyncio.StreamReader) -> tuple[int, int, bytes]:
        first = (await reader.readexactly(1))[0]
        length, mult = 0, 1
        while True:
            byte = (await reader.readexactly(1))[0]
            length += (byte & 0x7F) * mult
            if not byte & 0x80:
                break
            mult *= 128
        return first >> 4, first & 0x0F, await reader.readexactly(length)

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        session: _Session | None = None
        try:
            kind, _, body = await self._read_packet(reader)
            if kind != CONNECT:
                return
            session = self._connect(body, writer)
            if session is None:
                return
            while True:
                kind, flags, body = await self._read_packet(reader)
                if kind == PUBLISH:
                    await self._on_publish(session, flags, body, writer)
                elif kind == SUBSCRIBE:
                    await self._on_subscribe(session, body, writer)
                elif kind == UNSUBSCRIBE:
                    pid, rest = body[:2], body[2:]
                    while rest:
                        n = struct.unpack("!H", rest[:2])[0]
                        session.filters.discard(rest[2 : 2 + n].decode())
                        rest = rest[2 + n :]
                    writer.write(_packet(UNSUBACK << 4, pid))
                elif kind == PINGREQ:
                    writer.write(_packet(PINGRESP << 4, b""))
                elif kind == DISCONNECT:
                    return
                await writer.drain()
        except (asyncio.IncompleteReadError, ConnectionError):
            pass
        finally:
            if session is not None and session in self.sessions:
                self.sessions.remove(session)
            writer.close()

    def _connect(self, body: bytes, writer: asyncio.StreamWriter) -> _Session | None:
        n = struct.unpack("!H", body[:2])[0]
        pos = 2 + n
        level, flags = body[pos], body[pos + 1]
        pos += 4  # level, flags, keepalive
        n = struct.unpack("!H", body[pos : pos + 2])[0]
        client_id = body[pos + 2 : pos + 2 + n].decode()
        pos += 2 + n
        if flags & 0x04:  # will topic + message: skip both
            for _ in range(2):
                n = struct.unpack("!H", body[pos : pos + 2])[0]
                pos += 2 + n
        user = password = None
        if flags & 0x80:
            n = struct.unpack("!H", body[pos : pos + 2])[0]
            user = body[pos + 2 : pos + 2 + n].decode()
            pos += 2 + n
        if flags & 0x40:
            n = struct.unpack("!H", body[pos : pos + 2])[0]
            password = body[pos + 2 : pos + 2 + n].decode()
        rc = RC_ACCEPTED
        if level not in (3, 4):
            rc = RC_BAD_PROTOCOL
        elif self.users is not None and (user is None or self.users.get(user) != password):
            rc = RC_BAD_CREDENTIALS if user else RC_NOT_AUTHORIZED
        writer.write(_packet(CONNACK << 4, bytes([0, rc])))
        if rc != RC_ACCEPTED:
            return None
        session = _Session(client_id or f"anon-{id(writer)}", writer)
        self.sessions.append(session)
        return session

    async def _on_publish(self, session: _Session, flags: int, body: bytes, writer: asyncio.StreamWriter) -> None:
        qos, retain = (flags >> 1) & 0x03, bool(flags & 0x01)
        n = struct.unpack("!H", body[:2])[0]
        topic, pos = body[2 : 2 + n].decode(), 2 + n
        if qos:
            writer.write(_packet(PUBACK << 4, body[pos : pos + 2]))
            pos += 2
        await self.publish(topic, body[pos:], retain, session.client_id)

    async def _on_subscribe(self, session: _Session, body: bytes, writer: asyncio.StreamWriter) -> None:
        pid, rest, granted, new = body[:2], body[2:], bytearray(), []
        while rest:
            n = struct.unpack("!H", rest[:2])[0]
            pattern = rest[2 : 2 + n].decode()
            session.filters.add(pattern)
            new.append(pattern)
            granted.append(0)  # everything is delivered at QoS 0
            rest = rest[3 + n :]
        writer.write(_packet(SUBACK << 4, pid + bytes(granted)))
        await writer.drain()
        for topic, payload in list(self.retained.items()):
            if any(topic_matches(p, topic) for p in new):
                await session.deliver(topic, payload, retain=True)
