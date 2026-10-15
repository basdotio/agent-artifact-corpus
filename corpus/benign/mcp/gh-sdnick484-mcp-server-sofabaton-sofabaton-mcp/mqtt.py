"""The X2's MQTT side, as a client of your broker. X2 only.

What this gives an X2 beyond sofabaton-x-server:
  - live activity state: the hub publishes every change, including ones made on
    the physical remote, 1-2 s before the REST side confirms them;
  - control while the Sofabaton app holds sofabaton-x-server's proxy (the
    server is in "observe" mode then and refuses commands; MQTT doesn't care);
  - a working setup with no sofabaton-x-server at all;
  - presses of MQTT Wifi-Device keys, straight from <MAC>/up.

How it works (topics and payloads: protocol.py):
  - One long-lived connection to the broker, reconnecting with backoff. A
    rejected login is remembered (auth_failed) and retried slowly, since
    hammering a broker with a bad password helps nobody.
  - Requests are serialized: one at a time, 200 ms apart, because both
    community clients do that for the hub's single-threaded firmware
    (ASSUMPTION S-MQTT-SERIAL). A request waits up to reply_timeout for its
    reply topic, matched by the id the reply echoes, since MQTT has no
    request ids (ASSUMPTION S-MQTT-REPLY-TIMEOUT).
  - Retained messages are dropped: the hub never retains [M], so a retained
    activity change or press is a broker or bridge replaying old news.

This module knows nothing about tools or REST; client.py decides when to use it.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import secrets
import ssl
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from . import protocol as p
from .api import Press, PressPage, SofabatonError
from .config import MqttSettings
from .tasks import stop_task

log = logging.getLogger(__name__)

ClientFactory = Callable[..., Any]


@dataclass
class _Waiter:
    topic: str
    match: Callable[[Any], bool]
    future: asyncio.Future[Any]


class MqttHub:
    reply_timeout = 5.0  # ASSUMPTION S-MQTT-REPLY-TIMEOUT
    publish_gap = 0.2  # ASSUMPTION S-MQTT-SERIAL
    retry_delay = 1.0
    auth_retry_delay = 60.0
    ring_size = 200
    stop_timeout = 5.0  # shutdown waits at most this long for the connection task

    def __init__(self, settings: MqttSettings, mac: str, client_factory: ClientFactory | None = None) -> None:
        self.settings = settings
        self.mac = mac
        self.t = p.topics(mac)
        self._factory = client_factory
        self._client: Any = None
        self._task: asyncio.Task[None] | None = None
        self._lock = asyncio.Lock()
        self._waiters: list[_Waiter] = []
        self._state_changed = asyncio.Event()
        self.connected = False
        self.auth_failed = False
        self.last_error: str | None = None
        # The running activity in the X2's MQTT id space (None: off), once known.
        self.current: int | None = None
        self.state_known = False
        self.changed_at: float | None = None  # loop time of the last pushed change
        self.instance_id = secrets.token_hex(8)
        self._seq = 0
        self._presses: deque[Press] = deque(maxlen=self.ring_size)
        # doctor --dump sets this to a list to capture every message as received (MAC replaced by <MAC>),
        # so a recording shows what the X2 really sends, not what our parsers made of it.
        self.raw_log: list[dict[str, Any]] | None = None

    @property
    def broker(self) -> str:
        return f"{self.settings.host}:{self.settings.port}"

    # --- connection --------------------------------------------------------------------
    async def start(self) -> None:
        self._task = asyncio.create_task(self._run_forever(), name="sofabaton-mqtt")

    async def stop(self) -> None:
        # Not cancel-and-await: aiomqtt waits for every acknowledgement with asyncio.wait_for, which on
        # Python 3.11 can drop the cancel (see stop_task and tests/test_mqtt.py's shutdown tests).
        await stop_task(self._task, self.stop_timeout, "The MQTT connection")

    def _make_client(self) -> Any:
        import aiomqtt

        factory = self._factory or aiomqtt.Client
        s = self.settings
        return factory(
            s.host,
            s.port,
            username=s.username,
            password=s.password,
            identifier=f"mcp-server-sofabaton-{secrets.token_hex(3)}",
            protocol=aiomqtt.ProtocolVersion.V311,
            keepalive=30,
            tls_context=ssl.create_default_context() if s.tls else None,
        )

    @staticmethod
    def _is_auth_error(exc: BaseException) -> bool:
        rc = getattr(exc, "rc", None)
        value = getattr(rc, "value", rc)
        return value in (4, 5, 134, 135)  # bad credentials / not authorized (3.1.1 and 5 codes)

    async def _run_forever(self) -> None:
        import aiomqtt

        delay = self.retry_delay
        while True:
            try:
                async with self._make_client() as client:
                    self._client = client
                    for key in p.SUBSCRIBED:
                        await client.subscribe(self.t[key], qos=0)
                    self.connected, self.auth_failed, self.last_error = True, False, None
                    delay = self.retry_delay
                    log.info("MQTT: connected to %s for X2 %s", self.broker, self.mac)
                    async for message in client.messages:
                        self._dispatch(str(message.topic), message.payload, bool(message.retain))
            except aiomqtt.MqttError as exc:
                self.auth_failed = self._is_auth_error(exc)
                self.last_error = str(exc)
                log.warning("MQTT: %s (%s)", "login rejected" if self.auth_failed else "connection lost", exc)
            finally:
                self.connected = False
                self._client = None
                for w in self._waiters:
                    if not w.future.done():
                        w.future.set_exception(SofabatonError(f"The MQTT broker at {self.broker} disconnected."))
            await asyncio.sleep(self.auth_retry_delay if self.auth_failed else delay)
            delay = min(delay * 2, 60.0)

    # --- inbound ---------------------------------------------------------------------------
    def _dispatch(self, topic: str, raw: Any, retained: bool) -> None:
        if retained:
            log.debug("MQTT: dropping retained message on %s", topic)
            return
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            log.warning("MQTT: ignoring a message that isn't JSON on %s", topic)
            return
        if self.raw_log is not None:
            self.raw_log.append({"topic": topic.replace(self.mac, "<MAC>"), "payload": payload})
        if topic == self.t["state_up"]:
            self._on_state(payload)
        elif topic == self.t["press_up"]:
            self._on_press(payload)
        for w in list(self._waiters):
            if w.topic == topic and not w.future.done():
                with contextlib.suppress(Exception):
                    if w.match(payload):
                        w.future.set_result(payload)

    def _on_state(self, payload: Any) -> None:
        """ASSUMPTION S-MQTT-STATE: (activity_id, state); 255 = everything off."""
        parsed = p.unwrap_state(payload)
        if parsed is None:
            return
        activity_id, state = parsed
        if activity_id == p.ALL_OFF:
            self.current = None
        elif state == "on":
            self.current = activity_id
        elif state == "off" and self.current == activity_id:
            self.current = None
        else:
            return  # an "off" for something that isn't running: nothing changed
        self.state_known = True
        self.changed_at = asyncio.get_running_loop().time()
        self._state_changed.set()

    def _on_press(self, payload: Any) -> None:
        """ASSUMPTION S-MQTT-UP"""
        if not isinstance(payload, dict):
            return
        try:
            device_id, key_id = int(payload["device_id"]), int(payload["key_id"])
        except (KeyError, TypeError, ValueError):
            return
        self._seq += 1
        self._presses.append(
            {
                "seq": self._seq,
                "device_id": device_id,
                "command_id": key_id,
                "label": None,
                "press_type": "short",  # the hub sends no press type [M]
                "transport": "mqtt",
                "received_at": datetime.now(UTC).isoformat(timespec="seconds"),
            }
        )

    def presses(self, after: int | None, limit: int) -> PressPage:
        rows = list(self._presses)
        oldest = rows[0]["seq"] if rows else self._seq + 1
        expired = after is not None and after + 1 < oldest
        # Newest first by default; oldest first after a seq, to catch up in order.
        chosen = rows[-limit:][::-1] if after is None else [r for r in rows if r["seq"] > after][:limit]
        return {"instance_id": self.instance_id, "last_seq": self._seq, "expired": expired, "presses": chosen}

    # --- outbound --------------------------------------------------------------------------
    def _require(self) -> Any:
        if self._client is None or not self.connected:
            if self.auth_failed:
                raise SofabatonError(
                    f"The MQTT broker at {self.broker} rejected the login; check the user and password in "
                    "SOFABATON_MQTT_URL."
                )
            raise SofabatonError(
                f"Not connected to the MQTT broker at {self.broker} ({self.last_error or 'connecting'}); retrying in "
                "the background."
            )
        return self._client

    async def _publish(self, topic: str, payload: Any) -> None:
        client = self._require()
        await client.publish(topic, json.dumps(payload), qos=0, retain=False)

    async def publish(self, key: str, payload: Any) -> None:
        async with self._lock:
            try:
                await self._publish(self.t[key], payload)
            finally:
                await asyncio.sleep(self.publish_gap)

    async def request(self, req: str, payload: Any, reply: str, match: Callable[[Any], bool], what: str) -> Any:
        async with self._lock:
            future: asyncio.Future[Any] = asyncio.get_running_loop().create_future()
            waiter = _Waiter(self.t[reply], match, future)
            self._waiters.append(waiter)
            try:
                await self._publish(self.t[req], payload)
                return await asyncio.wait_for(future, self.reply_timeout)
            except TimeoutError as exc:
                raise SofabatonError(
                    f"The X2 didn't answer the {what} request over MQTT within {self.reply_timeout:.0f}s. Is its MQTT "
                    "link set up (Sofabaton app: Me -> Connect to Home Assistant) to this broker, and is the MAC "
                    "right? `doctor` checks both."
                ) from exc
            finally:
                self._waiters.remove(waiter)
                await asyncio.sleep(self.publish_gap)

    # --- lists (ASSUMPTION S-MQTT-LISTS) --------------------------------------------------
    async def activities(self) -> list[tuple[int, str, bool]]:
        """(mqtt id, name, on) for every activity; also refreshes our view of what's running."""
        reply = await self.request(
            "activity_list_req", p.activity_list_request(), "activity_list", lambda _: True, "activity list"
        )
        out: list[tuple[int, str, bool]] = []
        for item in p.items(reply):
            with contextlib.suppress(KeyError, TypeError, ValueError):
                out.append(
                    (
                        int(item["activity_id"]),
                        str(item.get("activity_name") or item["activity_id"]),
                        item.get("state") == "on",
                    )
                )
        on = [a for a, _, is_on in out if is_on]
        self.current, self.state_known = (on[0] if on else None), True
        return out

    async def devices(self) -> list[tuple[int, str]]:
        reply = await self.request(
            "device_list_req", p.device_list_request(), "device_list", lambda _: True, "device list"
        )
        out: list[tuple[int, str]] = []
        for item in p.items(reply):
            with contextlib.suppress(KeyError, TypeError, ValueError):
                out.append((int(item["device_id"]), str(item.get("device_name") or item["device_id"])))
        return out

    def _echoes(self, key: str, value: int) -> Callable[[Any], bool]:
        return lambda payload: isinstance(payload, dict) and str(payload.get(key)) == str(value)

    async def activity_keys(self, activity_id: int) -> list[int]:
        reply = await self.request(
            "keys_req",
            p.for_activity(activity_id),
            "keys_list",
            self._echoes("activity_id", activity_id),
            "button list",
        )
        return [int(i["key_id"]) for i in p.items(reply) if "key_id" in i]

    async def macros(self, activity_id: int) -> list[tuple[int, str | None]]:
        reply = await self.request(
            "macros_req",
            p.for_activity(activity_id),
            "macros_list",
            self._echoes("activity_id", activity_id),
            "macro list",
        )
        return [(int(i["key_id"]), i.get("key_name")) for i in p.items(reply) if "key_id" in i]

    async def favorites(self, activity_id: int) -> list[tuple[int, int, str | None]]:
        """(device id, key id, name) for each favorite."""
        reply = await self.request(
            "favorites_req",
            p.for_activity(activity_id),
            "favorites_list",
            self._echoes("activity_id", activity_id),
            "favorites list",
        )
        return [(int(i["device_id"]), int(i["key_id"]), i.get("key_name")) for i in p.items(reply) if "key_id" in i]

    async def device_keys(self, device_id: int) -> list[tuple[int, str | None]]:
        reply = await self.request(
            "device_keys_req",
            p.for_device(device_id),
            "device_keys_list",
            self._echoes("device_id", device_id),
            "command list",
        )
        return [(int(i["key_id"]), i.get("key_name")) for i in p.items(reply) if "key_id" in i]

    # --- waiting for the hub's own announcements -------------------------------------------
    async def wait_state(self, done: Callable[[int | None], bool], timeout: float) -> bool:
        """Wait until a pushed change makes done(current) true. False on timeout."""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while not (self.state_known and done(self.current)):
            remaining = deadline - loop.time()
            if remaining <= 0:
                return False
            self._state_changed.clear()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(self._state_changed.wait(), remaining)
        return True

    def settling_for(self, settle_s: float) -> float:
        """Seconds left in the settle window after the last pushed change (0 when settled)."""
        if self.changed_at is None:
            return 0.0
        return max(0.0, self.changed_at + settle_s - asyncio.get_running_loop().time())
