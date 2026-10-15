"""The X2's MQTT protocol: topics and payloads, each tagged with the assumption it rests on.

X2 only. The X1 and X1S have no MQTT (ASSUMPTION S-X1-NO-MQTT); they're reached
through sofabaton-x-server's REST API instead (api.py).

You turn this on in the Sofabaton app (Me -> Connect to Home Assistant, then
your broker's address and login). From then on the hub keeps an MQTT
connection to *your* broker. Nothing here talks to the hub directly: we
publish requests to the broker and the hub answers on other topics.

Sources (see PROTOCOL.md for the full write-up and confidence per claim):
  [Y] yomonpet/ha-sofabaton-hub, a Home Assistant integration that m3tac0de's
      README calls "the official Sofabaton Hub integration" (not confirmed on
      sofabaton.com). Control and list topics.
  [H] RepairGuyDK's Homey app: device list, keys and control topics.
  [M] m3tac0de/home-assistant-sofabaton-x1s live-hub benches: <MAC>/up and
      activity_control_up shapes, uppercase MAC, QoS 0, never retained,
      device keys_control honored.

Every request and reply is JSON. Requests wrap their argument in {"data": ...};
replies carry their list in "data" and echo the id they answer for.
"""

from __future__ import annotations

import re
from typing import Any

# The MAC in topics is the hub's, as UPPERCASE bare hex: "02AB34CD56EF".
# [M] measured this for <MAC>/up ("the lowercase topic stays silent") and for
# device/<MAC>/keys_control; the activity/ topics are assumed to match.
# ASSUMPTION S-MQTT-MAC-CASE
_HEX = re.compile(r"[^0-9A-Fa-f]")


def normalize_mac(raw: str) -> str | None:
    """'aa:bb:cc:dd:ee:ff' / 'AA-BB-...' / 'aabbccddeeff' -> 'AABBCCDDEEFF', or None if not a MAC."""
    bare = _HEX.sub("", raw).upper()
    return bare if len(bare) == 12 else None


def topics(mac: str) -> dict[str, str]:
    """Every topic we use, for one hub. Keys are what the code refers to."""
    return {
        # Hub -> us: a press of a key bound to an MQTT "Wifi Device". ASSUMPTION S-MQTT-UP [M]
        "press_up": f"{mac}/up",
        # Hub -> us: every activity change, early in the power macro. ASSUMPTION S-MQTT-STATE [M][Y]
        "state_up": f"activity/{mac}/activity_control_up",
        # Us -> hub: start/stop an activity. ASSUMPTION S-MQTT-CONTROL [Y]
        "state_down": f"activity/{mac}/activity_control_down",
        # Lists: request -> reply. ASSUMPTION S-MQTT-LISTS [Y][H]
        "activity_list_req": f"activity/{mac}/list_request",
        "activity_list": f"activity/{mac}/list",
        "keys_req": f"activity/{mac}/keys_request",
        "keys_list": f"activity/{mac}/keys_list",
        "macros_req": f"activity/{mac}/macro_keys_request",
        "macros_list": f"activity/{mac}/macro_keys_list",
        "favorites_req": f"activity/{mac}/favorites_keys_request",
        "favorites_list": f"activity/{mac}/favorites_keys_list",
        "device_list_req": f"device/{mac}/list_request",
        "device_list": f"device/{mac}/list",
        "device_keys_req": f"device/{mac}/keys_request",
        "device_keys_list": f"device/{mac}/keys_list",
        # Us -> hub: presses. ASSUMPTION S-MQTT-KEYS, S-MQTT-MACRO, S-MQTT-FAVORITE, S-MQTT-DEVICE
        "key_ctl": f"activity/{mac}/keys_control",
        "macro_ctl": f"activity/{mac}/macro_keys_control",
        "favorite_ctl": f"activity/{mac}/favorites_keys_control",
        "device_key_ctl": f"device/{mac}/keys_control",
    }


# Topics we subscribe to (everything the hub publishes).
SUBSCRIBED = (
    "press_up",
    "state_up",
    "activity_list",
    "keys_list",
    "macros_list",
    "favorites_list",
    "device_list",
    "device_keys_list",
)

# activity_id 255 in activity_control_up means "everything off" (the OFF key). [M][Y]
ALL_OFF = 255


# --- request payloads -------------------------------------------------------------------
def activity_list_request() -> dict[str, Any]:
    return {"data": "activity_list"}


def device_list_request() -> dict[str, Any]:
    return {"data": "device_list"}


def for_activity(activity_id: int) -> dict[str, Any]:
    return {"data": {"activity_id": activity_id}}


def for_device(device_id: int) -> dict[str, Any]:
    return {"data": {"device_id": device_id}}


def activity_state(activity_id: int, on: bool) -> dict[str, Any]:
    return {"data": {"activity_id": activity_id, "state": "on" if on else "off"}}


def activity_key(activity_id: int, key_id: int) -> dict[str, Any]:
    """A hard button (key_id = the ButtonName code) or a macro, sent through an activity."""
    return {"data": {"activity_id": activity_id, "key_id": key_id}}


def favorite_key(device_id: int, key_id: int) -> dict[str, Any]:
    """A favorite. The firmware reads the *device* id from the activity_id field. [Y]
    ("Due to firmware design issue"). ASSUMPTION S-MQTT-FAVORITE"""
    return {"data": {"activity_id": device_id, "key_id": key_id}}


def device_key(device_id: int, key_id: int) -> dict[str, Any]:
    return {"data": {"device_id": device_id, "key_id": key_id}}


# --- reply parsing ----------------------------------------------------------------------
def unwrap_state(payload: Any) -> tuple[int, str] | None:
    """activity_control_up -> (activity_id, "on"/"off"), or None if it isn't one.

    The hub publishes it flat, {"activity_id", "state"}; [M] also accepts the
    request-side {"data": {...}} envelope, so we do too.
    """
    if not isinstance(payload, dict):
        return None
    if "activity_id" not in payload and isinstance(payload.get("data"), dict):
        payload = payload["data"]
    try:
        activity_id = int(payload["activity_id"])
    except (KeyError, TypeError, ValueError):
        return None
    return activity_id, str(payload.get("state") or "").strip().lower()


def items(payload: Any) -> list[dict[str, Any]]:
    """The list in a reply's "data" (dicts only; anything else is dropped)."""
    data = payload.get("data") if isinstance(payload, dict) else None
    return [d for d in data if isinstance(d, dict)] if isinstance(data, list) else []
