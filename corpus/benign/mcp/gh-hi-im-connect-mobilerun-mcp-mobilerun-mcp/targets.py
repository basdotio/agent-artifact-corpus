"""Device addressing: which backend a `device` string refers to.

Grammar (the same `device` argument every tool accepts):

- ``<adb serial>``                      Android over adb (USB serial, ``host:port``, ``emulator-5554``)
- ``cloud:<uuid>`` or a bare UUID       Mobilerun Cloud device
- ``ios`` / ``ios:<url>``               iOS through mobilerun-ios / ios-portal HTTP
- ``http(s)://host:port`` or
  ``android-http:<url>``                Android through the Portal's HTTP API only (no adb)
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass

ANDROID_ADB = "android-adb"
ANDROID_HTTP = "android-http"
IOS_HTTP = "ios-http"
CLOUD = "cloud"
KINDS = (ANDROID_ADB, ANDROID_HTTP, IOS_HTTP, CLOUD)

CORE_BACKEND = {
    ANDROID_ADB: "local-android-adb",
    ANDROID_HTTP: "local-android-http",
    IOS_HTTP: "local-ios-http",
    CLOUD: "cloud",
}
DEFAULT_IOS_URL = "http://127.0.0.1:6643"
_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


@dataclass(frozen=True)
class Target:
    kind: str
    id: str
    url: str | None = None
    token: str | None = None

    @property
    def has_adb(self) -> bool:
        return self.kind == ANDROID_ADB

    @property
    def platform(self) -> str:
        return "ios" if self.kind == IOS_HTTP else "android"


def resolve_target(device: str, env: Mapping[str, str] | None = None) -> Target:
    env = os.environ if env is None else env
    value = device.strip()
    lowered = value.lower()
    if lowered.startswith("cloud:"):
        return Target(CLOUD, value.split(":", 1)[1].strip())
    if _UUID.match(value):
        return Target(CLOUD, value)
    if lowered == "ios" or lowered.startswith("ios:"):
        url = value.split(":", 1)[1].strip() if ":" in value else ""
        url = url or env.get("MOBILERUN_IOS_PORTAL_URL") or DEFAULT_IOS_URL
        return Target(IOS_HTTP, url, url=url, token=env.get("MOBILERUN_IOS_PORTAL_TOKEN") or None)
    if lowered.startswith("android-http:"):
        url = value.split(":", 1)[1].strip()
        return Target(ANDROID_HTTP, url, url=url, token=env.get("MOBILERUN_ANDROID_PORTAL_TOKEN"))
    if lowered.startswith(("http://", "https://")):
        return Target(
            ANDROID_HTTP, value, url=value, token=env.get("MOBILERUN_ANDROID_PORTAL_TOKEN")
        )
    return Target(ANDROID_ADB, value)
