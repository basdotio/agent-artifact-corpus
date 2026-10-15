"""One fake Sofabaton hub's state, shared by its two faces.

A real X2 can be reached two ways at once: through sofabaton-x-server's REST
API and through MQTT. To test that we use both correctly, the fake REST
server (fake_server.py) and the fake X2 MQTT client (fake_x2.py) share this
object, so starting an activity through one is visible through the other.

Ids: the REST API numbers activities 101+ (sofabaton-x-server docs). What the
X2 uses over MQTT is unknown (ASSUMPTION S-MQTT-IDS), so ``mqtt_id_offset``
can give MQTT a different id space. Our client resolves names per transport
and never carries an id from one to the other; the hybrid tests run with an
offset to prove it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from importlib import resources
from typing import Any, Literal

Model = Literal["X1", "X1S", "X2"]


@dataclass
class FakeActivity:
    activity_id: int
    name: str
    keys: list[int] = field(default_factory=list)  # hard buttons assigned (ButtonName codes)
    macros: list[tuple[int, str | None]] = field(default_factory=list)  # (command_id, label)
    favorites: list[tuple[int, int, str | None]] = field(default_factory=list)  # (device_id, command_id, label)


@dataclass
class FakeDevice:
    device_id: int
    name: str
    brand: str | None
    device_class: str | None
    commands: list[tuple[int, str]] = field(default_factory=list)  # (command_id, label)
    mqtt_virtual: bool = False  # an X2 "Wifi Device" of the MQTT kind: its presses publish to <MAC>/up


@dataclass
class Executed:
    """Something the fake hub did, whichever way it was asked."""

    via: Literal["rest", "mqtt"]
    what: str  # "start", "stop", "key", "macro", "favorite", "device_key", "find_remote"
    entity_id: int  # REST ids, always (MQTT ids are translated back)
    command_id: int | None = None


class FakeHubState:
    def __init__(
        self,
        *,
        model: Model,
        name: str,
        mac: str,
        activities: list[FakeActivity],
        devices: list[FakeDevice],
        mqtt_id_offset: int = 0,
    ) -> None:
        self.model = model
        self.name = name
        self.mac = mac
        self.activities = activities
        self.devices = devices
        self.mqtt_id_offset = mqtt_id_offset
        self.running: int | None = None  # REST id of the running activity
        self.executed: list[Executed] = []
        self._listeners: list[Callable[[int, str], None]] = []  # (REST activity id or 255, "on"/"off")
        self._press_listeners: list[Callable[[int, int], None]] = []  # (device id, command id)

    # --- lookups ----------------------------------------------------------------
    def activity(self, activity_id: int) -> FakeActivity | None:
        return next((a for a in self.activities if a.activity_id == activity_id), None)

    def device(self, device_id: int) -> FakeDevice | None:
        return next((d for d in self.devices if d.device_id == device_id), None)

    def to_mqtt(self, rest_id: int) -> int:
        return rest_id + self.mqtt_id_offset

    def from_mqtt(self, mqtt_id: int) -> int:
        return mqtt_id - self.mqtt_id_offset

    # --- state changes ------------------------------------------------------------
    def on_change(self, listener: Callable[[int, str], None]) -> None:
        self._listeners.append(listener)

    def set_running(self, activity_id: int | None, *, all_off: bool = False) -> None:
        """Change the running activity and tell listeners (the fake X2 publishes it)."""
        before = self.running
        self.running = activity_id
        if activity_id is not None:
            event: tuple[int, str] = (activity_id, "on")
        elif all_off:
            event = (255, "off")  # the OFF key: "everything off" [M][Y]
        else:
            event = (before if before is not None else 255, "off")
        for listener in list(self._listeners):
            listener(*event)

    def press_remote_off(self) -> None:
        """Someone pressed OFF on the physical remote."""
        self.set_running(None, all_off=True)

    def press_virtual_key(self, device_id: int, command_id: int) -> None:
        """Someone pressed a remote key bound to an MQTT Wifi Device (fake_x2 publishes <MAC>/up)."""
        for listener in list(self._press_listeners):
            listener(device_id, command_id)

    def on_press(self, listener: Callable[[int, int], None]) -> None:
        self._press_listeners.append(listener)


def load_state(fixture: str = "x2_living_room", **overrides: Any) -> FakeHubState:
    """Build a FakeHubState from sim/fixtures/<fixture>.json (hand-built, see its _comment)."""
    raw = json.loads(resources.files(__package__).joinpath("fixtures", f"{fixture}.json").read_text())
    activities = [
        FakeActivity(
            a["activity_id"],
            a["name"],
            a.get("keys", []),
            [tuple(m) for m in a.get("macros", [])],
            [tuple(f) for f in a.get("favorites", [])],
        )
        for a in raw["activities"]
    ]
    devices = [
        FakeDevice(
            d["device_id"],
            d["name"],
            d.get("brand"),
            d.get("device_class"),
            [tuple(c) for c in d.get("commands", [])],
            d.get("mqtt_virtual", False),
        )
        for d in raw["devices"]
    ]
    kwargs: dict[str, Any] = {"model": raw["model"], "name": raw["name"], "mac": raw["mac"]}
    kwargs.update(overrides)
    return FakeHubState(activities=activities, devices=devices, **kwargs)
