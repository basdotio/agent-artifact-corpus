"""Every protocol detail this server relies on that hasn't been checked on a real hub.

Same mechanism as mcp-server-harmony: each assumption has an id that code
cites next to where it depends on it (``# ASSUMPTION S-MQTT-STATE``), tests
cite to document it, HARDWARE_VALIDATION.md cites in the step that confirms
it, and `doctor` prints. tests/test_assumptions.py keeps the README and
HARDWARE_VALIDATION.md in step with this list.

Sources, shortened in ``source``:
  [Y]  yomonpet/ha-sofabaton-hub (control + list topics; called "the official
       Sofabaton Hub integration" by m3tac0de's README, unconfirmed on sofabaton.com)
  [H]  RepairGuyDK/com.repairguydk.sofabatonx2 (Homey app: device topics)
  [M]  m3tac0de/home-assistant-sofabaton-x1s docs/protocol/live-hub-testing.md
       (benches against real X1S/X2 hubs)
  [S]  sofabaton-x-server 0.2.4, run here with no hub attached; its OpenAPI
       document is in tests/fixtures/

Confidence:
  high   - measured on a real hub by [M], or recorded from the real server [S]
  medium - one or two independent client implementations agree, no measurement
  low    - our own choice or guess; the simulator implements it, nothing confirms it

To record a hardware result, set ``status`` to "hardware-verified" (or
"hardware-contradicted" with what you saw in ``note``) and commit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Confidence = Literal["high", "medium", "low"]
Status = Literal["simulator-only", "hardware-verified", "hardware-contradicted"]


@dataclass(frozen=True)
class Assumption:
    id: str
    claim: str
    source: str
    confidence: Confidence
    status: Status = "simulator-only"
    note: str = ""


ASSUMPTIONS: tuple[Assumption, ...] = (
    # --- sofabaton-x-server (any model) -----------------------------------------------------
    Assumption(
        "S-REST-API",
        "sofabaton-x-server 0.2.x serves the routes and response fields we use under /api/v1.",
        "[S] OpenAPI document recorded from 0.2.4; test_openapi_contract.py checks every field we read",
        "high",
    ),
    Assumption(
        "S-REST-MODES",
        "mode 'observe' (the Sofabaton app holds the proxy) refuses commands with 409; with no hub session, "
        "catalog reads and send/start/stop get 503 (they look the id up first) and find-remote 409; all are "
        "RFC 9457 problem bodies carrying 'mode'.",
        "[S] 503 observed on 0.2.4 with no hub attached; the per-route mapping read from its routes_hub_data.py; "
        "observe mode itself not observed",
        "medium",
    ),
    Assumption(
        "S-REST-START",
        "A start/stop is confirmed when GET /activity shows the change; the power macro finishes within 30 s.",
        "[S] route semantics; 30 s is our timeout",
        "low",
    ),
    Assumption(
        "S-X1-NO-MQTT",
        "Only the X2 has MQTT; the X1 and X1S are reached through sofabaton-x-server only.",
        "[M] README (MQTT is X2-only); [Y] is X2-only",
        "high",
    ),
    # --- X2 MQTT --------------------------------------------------------------------------------
    Assumption(
        "S-MQTT-UP",
        'A key bound to an MQTT Wifi Device publishes {"device_id", "key_id"} to <MAC>/up, QoS 0, never retained.',
        "[M] measured; openHAB forum user report agrees",
        "high",
    ),
    Assumption(
        "S-MQTT-STATE",
        'Every activity change is published to activity/<MAC>/activity_control_up as {"activity_id", "state"} '
        "early in the power macro; activity_id 255 means everything off. This includes changes we request.",
        "[M] measured (incl. 'every transition'); [Y] parses the same shape",
        "high",
    ),
    Assumption(
        "S-MQTT-MAC-CASE",
        "Topics use the hub's MAC as UPPERCASE bare hex (02AB34CD56EF), for activity/ and device/ topics too.",
        "[M] measured for <MAC>/up and device/<MAC>/keys_control; activity/ topics inferred",
        "medium",
    ),
    Assumption(
        "S-MQTT-CONTROL",
        'Publishing {"data": {"activity_id", "state": "on"|"off"}} to activity/<MAC>/activity_control_down '
        "starts or stops an activity.",
        "[Y]",
        "medium",
    ),
    Assumption(
        "S-MQTT-KEYS",
        '{"data": {"activity_id", "key_id"}} to activity/<MAC>/keys_control presses a hard button, with key_id = '
        "the ButtonName code (VOL_UP = 182).",
        "[Y] (its key table matches sofabaton-x's ButtonName codes)",
        "medium",
    ),
    Assumption(
        "S-MQTT-MACRO",
        '{"data": {"activity_id", "key_id"}} to activity/<MAC>/macro_keys_control runs a macro.',
        "[Y]",
        "medium",
    ),
    Assumption(
        "S-MQTT-FAVORITE",
        "Favorites go to activity/<MAC>/favorites_keys_control with the *device* id in the activity_id field.",
        "[Y] only ('Due to firmware design issue')",
        "low",
    ),
    Assumption(
        "S-MQTT-DEVICE",
        '{"data": {"device_id", "key_id"}} to device/<MAC>/keys_control sends a device command.',
        "[M] measured ('the hub DOES honor device/<MAC>/keys_control'); [H] uses it",
        "high",
    ),
    Assumption(
        "S-MQTT-LISTS",
        'List requests ({"data": "activity_list"} etc.) are answered on activity/<MAC>/list, keys_list, '
        "macro_keys_list, favorites_keys_list, device/<MAC>/list and keys_list with the shapes in protocol.py.",
        "[Y] and [H] agree; no live capture seen",
        "medium",
    ),
    Assumption(
        "S-MQTT-IDS",
        "Nothing says the X2's MQTT ids equal sofabaton-x-server's; we never carry ids between the two.",
        "none: a design choice that avoids depending on it (hybrid tests use different id spaces)",
        "low",
    ),
    Assumption(
        "S-MQTT-SERIAL",
        "The hub handles one MQTT request at a time; requests are sent one by one, 200 ms apart.",
        "[Y] and [H] both serialize with a small gap ('the hub is single-threaded')",
        "medium",
    ),
    Assumption(
        "S-MQTT-REPLY-TIMEOUT",
        "The X2 answers a list request within 5 s.",
        "none: our timeout",
        "low",
    ),
    Assumption(
        "S-MQTT-SETTLE",
        "After an MQTT-announced activity change, the power macro finishes within SOFABATON_MQTT_SETTLE_S (6 s); "
        "presses over MQTT are held off until then.",
        "none: [M] notes commands sent mid-macro can interrupt it, and has no completion signal over MQTT",
        "low",
    ),
)

BY_ID = {a.id: a for a in ASSUMPTIONS}


def unverified() -> list[Assumption]:
    return [a for a in ASSUMPTIONS if a.status != "hardware-verified"]
