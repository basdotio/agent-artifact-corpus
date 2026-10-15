"""The MQTT side of a fake X2: an MQTT client that answers like the hub does.

A real X2 with "Connect to Home Assistant" set up keeps a client connection to
your broker, answers requests published under activity/<MAC>/ and
device/<MAC>/, and publishes activity changes and Wifi-Device presses. This
fake does the same against any broker (the in-package one, mosquitto,
amqtt), sharing its state with the fake REST server (hub_state.py).

Payload shapes are written out here from the research (PROTOCOL.md), not
imported from our client's protocol.py, so a mistake in one shows up as a
test failure instead of being copied into both. Each is tagged with its
assumption id. Requires the [mqtt] extra (aiomqtt).
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any

import aiomqtt

from .hub_state import Executed, FakeHubState

log = logging.getLogger(__name__)


@dataclass
class X2Faults:
    silent: set[str] = field(default_factory=set)  # request topic leaves to ignore, e.g. {"list_request"}
    malformed: set[str] = field(default_factory=set)  # reply topic leaves answered with broken JSON
    reply_delay: float = 0.0
    no_state_push: bool = False  # don't publish activity_control_up at all


class FakeX2:
    def __init__(
        self,
        state: FakeHubState,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
    ) -> None:
        self.state = state
        self.host, self.port = host, port
        self.username, self.password = username, password
        self.faults = X2Faults()
        self.received: list[tuple[str, Any]] = []  # (topic, parsed payload) of every request
        self.connected = asyncio.Event()
        self._client: aiomqtt.Client | None = None
        self._task: asyncio.Task[None] | None = None
        self._pending: set[asyncio.Task[None]] = set()
        state.on_change(self._on_change)
        state.on_press(self._on_press)

    @property
    def mac(self) -> str:
        return self.state.mac

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run(), name="fake-x2")
        await asyncio.wait_for(self.connected.wait(), 10)

    async def stop(self) -> None:
        for t in [self._task, *self._pending]:
            if t is not None:
                t.cancel()
                with contextlib.suppress(asyncio.CancelledError, aiomqtt.MqttError):
                    await t

    async def _run(self) -> None:
        mac = self.mac
        async with aiomqtt.Client(
            self.host,
            self.port,
            username=self.username,
            password=self.password,
            identifier=f"fake-x2-{mac}",
            protocol=aiomqtt.ProtocolVersion.V311,
        ) as client:
            self._client = client
            await client.subscribe(f"activity/{mac}/+")
            await client.subscribe(f"device/{mac}/+")
            self.connected.set()
            async for message in client.messages:
                topic = str(message.topic)
                try:
                    payload = json.loads(message.payload)
                except (TypeError, ValueError):
                    continue
                self._spawn(self._handle(topic, payload))

    def _spawn(self, coro: Any) -> None:
        task = asyncio.ensure_future(coro)
        self._pending.add(task)
        task.add_done_callback(self._pending.discard)

    async def _publish(self, topic: str, payload: Any) -> None:
        if self._client is None:
            return
        leaf = topic.rsplit("/", 1)[-1]
        body = b'{"data": [{"activity_id": 1' if leaf in self.faults.malformed else json.dumps(payload).encode()
        with contextlib.suppress(aiomqtt.MqttError):
            await self._client.publish(topic, body, qos=0, retain=False)  # hub never retains [M]

    # --- what the hub publishes on its own ------------------------------------------
    def _on_change(self, rest_id: int, state: str) -> None:
        """ASSUMPTION S-MQTT-STATE: flat {"activity_id", "state"}; 255 = everything off."""
        if self.faults.no_state_push:
            return
        mqtt_id = rest_id if rest_id == 255 else self.state.to_mqtt(rest_id)
        self._spawn(self._publish(f"activity/{self.mac}/activity_control_up", {"activity_id": mqtt_id, "state": state}))

    def _on_press(self, device_id: int, command_id: int) -> None:
        """ASSUMPTION S-MQTT-UP: {"device_id", "key_id"} on <MAC>/up."""
        payload = {"device_id": self.state.to_mqtt(device_id), "key_id": command_id}
        self._spawn(self._publish(f"{self.mac}/up", payload))

    # --- requests -----------------------------------------------------------------------
    async def _handle(self, topic: str, payload: Any) -> None:
        kind, leaf = topic.split("/", 1)[0], topic.rsplit("/", 1)[-1]
        if leaf in ("list", "keys_list", "macro_keys_list", "favorites_keys_list", "activity_control_up"):
            return  # our own publishes come back to us: ignore
        self.received.append((topic, payload))
        if leaf in self.faults.silent:
            return
        if self.faults.reply_delay:
            await asyncio.sleep(self.faults.reply_delay)
        data = payload.get("data") if isinstance(payload, dict) else None
        st, mac = self.state, self.mac
        if kind == "activity":
            await self._activity(leaf, data, st, mac)
        elif kind == "device":
            await self._device(leaf, data, st, mac)

    async def _activity(self, leaf: str, data: Any, st: FakeHubState, mac: str) -> None:
        items: list[dict[str, Any]]
        if leaf == "list_request":  # ASSUMPTION S-MQTT-LISTS
            items = [
                {
                    "activity_id": st.to_mqtt(a.activity_id),
                    "activity_name": a.name,
                    "state": "on" if st.running == a.activity_id else "off",
                }
                for a in st.activities
            ]
            await self._publish(f"activity/{mac}/list", {"data": items})
            return
        if not isinstance(data, dict):
            return
        if leaf == "favorites_keys_control":  # ASSUMPTION S-MQTT-FAVORITE: device id in activity_id
            device_id = st.from_mqtt(int(data.get("activity_id", -1)))
            if st.device(device_id) is not None:
                st.executed.append(Executed("mqtt", "favorite", device_id, int(data.get("key_id", -1))))
            return
        activity = st.activity(st.from_mqtt(int(data.get("activity_id", -1))))
        if activity is None:
            return  # unknown ids are ignored silently; what a real X2 does is unknown
        aid = st.to_mqtt(activity.activity_id)
        if leaf == "activity_control_down":  # ASSUMPTION S-MQTT-CONTROL
            on = str(data.get("state")) == "on"
            st.executed.append(Executed("mqtt", "start" if on else "stop", activity.activity_id))
            if on:
                st.set_running(activity.activity_id)
            elif st.running == activity.activity_id:
                st.set_running(None)
        elif leaf == "keys_request":
            await self._publish(
                f"activity/{mac}/keys_list", {"activity_id": aid, "data": [{"key_id": k} for k in activity.keys]}
            )
        elif leaf == "macro_keys_request":
            items = [{"key_id": cid, "key_name": label} for cid, label in activity.macros]
            await self._publish(f"activity/{mac}/macro_keys_list", {"activity_id": aid, "data": items})
        elif leaf == "favorites_keys_request":
            items = [
                {"key_id": cid, "key_name": label, "device_id": st.to_mqtt(did)}
                for did, cid, label in activity.favorites
            ]
            await self._publish(f"activity/{mac}/favorites_keys_list", {"activity_id": aid, "data": items})
        elif leaf == "keys_control":  # ASSUMPTION S-MQTT-KEYS
            st.executed.append(Executed("mqtt", "key", activity.activity_id, int(data.get("key_id", -1))))
        elif leaf == "macro_keys_control":  # ASSUMPTION S-MQTT-MACRO
            st.executed.append(Executed("mqtt", "macro", activity.activity_id, int(data.get("key_id", -1))))

    async def _device(self, leaf: str, data: Any, st: FakeHubState, mac: str) -> None:
        items: list[dict[str, Any]]
        if leaf == "list_request":
            items = [{"device_id": st.to_mqtt(d.device_id), "device_name": d.name} for d in st.devices]
            await self._publish(f"device/{mac}/list", {"data": items})
            return
        if not isinstance(data, dict):
            return
        device = st.device(st.from_mqtt(int(data.get("device_id", -1))))
        if device is None:
            return
        did = st.to_mqtt(device.device_id)
        if leaf == "keys_request":
            items = [{"key_id": cid, "key_name": label} for cid, label in device.commands]
            await self._publish(f"device/{mac}/keys_list", {"device_id": did, "key_count": len(items), "data": items})
        elif leaf == "keys_control":  # ASSUMPTION S-MQTT-DEVICE
            key = int(data.get("key_id", -1))
            st.executed.append(Executed("mqtt", "device_key", device.device_id, key))
            if device.mqtt_virtual:  # [H]: a virtual device's key also echoes on <MAC>/up
                await self._publish(f"{mac}/up", {"device_id": did, "key_id": key})
