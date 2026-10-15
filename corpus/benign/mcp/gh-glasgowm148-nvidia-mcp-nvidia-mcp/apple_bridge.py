"""Optional pyatv control of one explicit LAN host, with private paired credentials.

No multicast discovery, shell access, SDK auto-installation or pairing MCP tool.
The persistent event loop belongs to this transport and is closed with it.
"""

import asyncio
import json
import logging
import os
import re
import threading
import uuid
from contextlib import contextmanager
from ipaddress import IPv4Address

from .config import ShieldError

_PAIR_LOG_LOCK = threading.RLock()


@contextmanager
def private_pairing_logs():
    """pyatv debug traces include PINs/keys; silence its namespace during pairing."""
    with _PAIR_LOG_LOCK:
        package = logging.getLogger("pyatv")
        loggers = [package] + [
            value
            for name, value in list(logging.root.manager.loggerDict.items())
            if name.startswith("pyatv.") and isinstance(value, logging.Logger)
        ]
        levels = [(logger, logger.level) for logger in loggers]
        try:
            for logger in loggers:
                logger.setLevel(logging.CRITICAL + 1)
            yield  # Newly imported SDK loggers inherit the silent package level.
        finally:
            for logger, level in levels:
                logger.setLevel(level)


class AppleBridge:
    def __init__(self, config):
        self.c = config
        self.loop = None
        self.thread = None
        self.device = None
        self.identity = None
        self.lock = threading.Lock()
        self.connection_lock = None
        self.action_lock = None
        self.closing = False
        self.closed = False

    def _run(self, function, timeout=30):
        with self.lock:
            if self.closing or self.closed:
                raise ShieldError("Apple TV transport is closed", "cancelled")
            if self.loop is None:
                self.loop = asyncio.new_event_loop()
                self.thread = threading.Thread(target=self.loop.run_forever, daemon=True)
                self.thread.start()

            async def serialized():
                if self.action_lock is None:
                    self.action_lock = asyncio.Lock()
                async with self.action_lock:
                    return await function()

            future = asyncio.run_coroutine_threadsafe(serialized(), self.loop)
        try:
            return future.result(timeout)
        except ShieldError:
            raise
        except KeyboardInterrupt:
            future.cancel()
            raise ShieldError(
                "Apple TV operation cancelled; inspect before retrying", "cancelled"
            ) from None
        except TimeoutError:
            future.cancel()
            raise ShieldError(
                "Apple TV control timed out; inspect state before retrying writes", "timeout"
            ) from None
        except Exception:
            future.cancel()
            raise ShieldError(
                "Apple TV control failed; check pairing and device capabilities", "device_error"
            ) from None

    @staticmethod
    def sdk():
        try:
            import pyatv
            from pyatv.const import FeatureName, FeatureState, Protocol

            return pyatv, FeatureName, FeatureState, Protocol
        except ImportError:
            raise ShieldError(
                "Install this release with the apple-tv extra; see docs/apple-tv.md",
                "missing_dependency",
            ) from None

    def credentials(self):
        if not self.c.apple_credentials:
            raise ShieldError(
                "Configure APPLE_TV_CREDENTIALS_FILE and privately pair Companion and AirPlay",
                "pairing_required",
            )
        try:
            with self.c.apple_credentials.open("rb") as handle:
                raw = handle.read(64_001)
            if len(raw) > 64_000:
                raise ValueError()
            value = json.loads(raw)
            if (
                not isinstance(value, dict)
                or not isinstance(value.get("identifier"), str)
                or not 1 <= len(value["identifier"]) <= 200
            ):
                raise ValueError()
            services = value["services"]
            if not isinstance(services, dict) or any(
                key not in ("Companion", "AirPlay")
                or not isinstance(secret, str)
                or not 1 <= len(secret) <= 8000
                for key, secret in services.items()
            ):
                raise ValueError()
            return value
        except (OSError, ValueError, KeyError, TypeError):
            raise ShieldError(
                "Apple TV credentials are missing or invalid; pair privately", "pairing_required"
            ) from None

    async def target(self):
        try:
            IPv4Address(self.c.host)
        except ValueError:
            raise ShieldError(
                "Apple TV paired controls require its private IPv4 address", "unsupported"
            ) from None
        pyatv, _names, _states, _protocols = self.sdk()
        targets = await pyatv.scan(asyncio.get_running_loop(), hosts=[self.c.host], timeout=3)
        if len(targets) != 1:
            raise ShieldError(
                "Exactly one Apple TV must answer at the configured host", "unreachable"
            )
        return targets[0]

    async def connected(self):
        if self.connection_lock is None:
            self.connection_lock = asyncio.Lock()
        async with self.connection_lock:
            return await self._connected()

    async def _connected(self):
        value = self.credentials()
        if self.identity is not None and value["identifier"] != self.identity:
            raise ShieldError("Apple TV credentials changed; restart the server", "device_mismatch")
        if set(value["services"]) != {"Companion", "AirPlay"}:
            raise ShieldError(
                "Pair both Companion and AirPlay for controls and playback guards",
                "pairing_required",
            )
        if self.device is not None:
            return self.device
        pyatv, _names, _states, protocols = self.sdk()
        target = await self.target()
        if value["identifier"] not in target.all_identifiers:
            raise ShieldError(
                "A different Apple TV answered at the configured address", "device_mismatch"
            )
        for name, credentials in value["services"].items():
            if not target.set_credentials(getattr(protocols, name), credentials):
                raise ShieldError(
                    "The Apple TV no longer advertises its paired protocol", "pairing_required"
                )
        self.device = await pyatv.connect(target, asyncio.get_running_loop())
        self.identity = value["identifier"]
        return self.device

    async def supported(self, name):
        _sdk, names, states, _protocols = self.sdk()
        device = await self.connected()
        if device.features.get_feature(getattr(names, name)).state != states.Available:
            raise ShieldError("Apple TV does not currently provide " + name, "unsupported")
        return device

    def snapshot(self):
        async def read():
            # pyatv metadata/power getters use push caches. Reconnect and complete
            # protocol initialization before a guard; never reuse an old idle cache.
            await self.disconnect()
            device = await self.connected()
            # pyatv 0.16 collapses missing state and metadata-less paused players
            # to Idle. Use the pinned MRP adapter to retain that distinction.
            state = self.confirmed_playback(device.metadata)
            deadline = asyncio.get_running_loop().time() + 3
            while state == "unknown" and asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(0.1)
                state = self.confirmed_playback(device.metadata)
            power = device.power.power_state.name.lower()
            return {
                "identifier": self.identity,
                "playback": state,
                "power": power,
                "model": device.device_info.model_str,
                "os_version": device.device_info.version,
            }

        return self._run(read)

    def confirmed_playback(self, metadata):
        """Read-only adapter for pinned pyatv 0.16 MRP; missing internals fail closed."""
        _sdk, _names, _states, protocols = self.sdk()
        if getattr(metadata, "main_protocol", None) != getattr(protocols, "MRP", None):
            return "unknown"
        try:
            raw = metadata.get(protocols.MRP).psm.playing._playback_state
        except (AttributeError, KeyError, TypeError):
            return "unknown"
        # MRP PlaybackState enum: Playing=1, Paused=2, Stopped=3,
        # Interrupted=4, Seeking=5. None is uninitialized, never confirmed idle.
        return {1: "playing", 2: "paused", 3: "stopped", 4: "loading", 5: "seeking"}.get(
            raw, "unknown"
        )

    def apps(self):
        async def read():
            device = await self.supported("AppList")
            apps = await device.apps.app_list()
            return [
                {"name": str(app.name)[:100], "id": str(app.identifier)[:200]} for app in apps[:50]
            ]

        return self._run(read)

    def launch(self, app_id):
        if not re.fullmatch(r"[A-Za-z0-9.-]{3,200}", app_id):
            raise ShieldError("Set APPLE_TV_KODI_APP_ID to Kodi's installed signing bundle ID")

        async def send():
            device = await self.supported("LaunchApp")
            await self.supported("AppList")
            apps = await device.apps.app_list()
            if app_id not in {app.identifier for app in apps}:
                raise ShieldError(
                    "Configured Kodi bundle ID is not in the installed app list", "not_found"
                )
            await device.apps.launch_app(app_id)

        self._run(send)

    def can_launch(self, app_id):
        if not re.fullmatch(r"[A-Za-z0-9.-]{3,200}", app_id):
            raise ShieldError("Set APPLE_TV_KODI_APP_ID to Kodi's installed signing bundle ID")

        async def inspect():
            device = await self.supported("LaunchApp")
            await self.supported("AppList")
            if app_id not in {app.identifier for app in await device.apps.app_list()}:
                raise ShieldError("Configured Kodi bundle ID is not installed", "not_found")

        self._run(inspect)

    def button(self, name):
        methods = {
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "select": "select",
            "back": "menu",
            "menu": "menu",
            "home": "home",
        }
        if name not in methods:
            raise ShieldError("Unsupported Apple TV remote button")

        async def send():
            method = methods[name]
            device = await self.supported(method.title())
            await getattr(device.remote_control, method)()

        self._run(send)

    def power(self, on):
        async def send():
            device = await self.supported("TurnOn" if on else "TurnOff")
            await (device.power.turn_on() if on else device.power.turn_off())

        self._run(send)

    def pair(self, protocol, read_pin):
        with private_pairing_logs():
            return self._pair(protocol, read_pin)

    def _pair(self, protocol, read_pin):
        if protocol not in ("Companion", "AirPlay"):
            raise ShieldError("Choose Companion or AirPlay for pairing", "pairing_invalid")

        async def begin():
            pyatv, _names, _states, protocols = self.sdk()
            target = await self.target()
            if not self.c.apple_credentials:
                raise ShieldError("Set APPLE_TV_CREDENTIALS_FILE to a private computer path")
            existing = (
                self.credentials()
                if self.c.apple_credentials.exists()
                else {"identifier": target.identifier, "services": {}}
            )
            if (
                not isinstance(existing["identifier"], str)
                or not 1 <= len(existing["identifier"]) <= 200
            ):
                raise ShieldError(
                    "Apple TV did not provide a stable pairing identity", "pairing_failed"
                )
            if existing["identifier"] not in target.all_identifiers:
                raise ShieldError(
                    "Pairing target differs from the saved Apple TV", "device_mismatch"
                )
            handler = await pyatv.pair(
                target, getattr(protocols, protocol), asyncio.get_running_loop()
            )
            try:
                if not handler.device_provides_pin:
                    raise ShieldError(
                        "This Apple TV cannot show the required private pairing PIN", "unsupported"
                    )
                await handler.begin()
                return handler, existing
            except BaseException:
                await handler.close()
                raise

        handler, existing = self._run(begin)
        try:
            # getpass must own the calling terminal thread: cancelling an
            # executor future cannot interrupt its blocked stdin or restore echo.
            try:
                pin = read_pin()
            except (EOFError, KeyboardInterrupt):
                raise ShieldError("Apple TV pairing cancelled", "pairing_cancelled") from None
            except Exception:
                raise ShieldError(
                    "Private PIN input failed; pair again in a terminal", "pairing_invalid"
                ) from None
            if not isinstance(pin, str) or not re.fullmatch(r"[0-9]{4}", pin):
                raise ShieldError("Enter the four-digit Apple TV PIN privately", "pairing_invalid")

            async def finish():
                handler.pin(int(pin))
                await handler.finish()
                if not handler.has_paired or not handler.service.credentials:
                    raise ShieldError("Apple TV pairing was not confirmed", "pairing_failed")
                existing["services"][protocol] = handler.service.credentials
                self.save_credentials(existing)
                return {"paired": protocol, "credential_file": str(self.c.apple_credentials)}

            return self._run(finish)
        finally:
            self._run(handler.close, timeout=5)

    def save_credentials(self, value):
        path = self.c.apple_credentials
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        temporary = path.with_name("." + path.name + "." + uuid.uuid4().hex)
        try:
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)

    def close(self):
        with self.lock:
            if self.closing or self.closed:
                return
            self.closing = True
            loop, thread = self.loop, self.thread
        try:
            if loop is not None:

                async def shutdown():
                    tasks = [
                        task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                    ]
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await self.disconnect()

                future = asyncio.run_coroutine_threadsafe(shutdown(), loop)
                try:
                    future.result(5)
                except Exception:
                    future.cancel()
                loop.call_soon_threadsafe(loop.stop)
                thread.join(timeout=5)
                if not thread.is_alive():
                    loop.close()
        finally:
            with self.lock:
                self.loop = self.thread = None
                self.closed, self.closing = True, False

    async def disconnect(self):
        device, self.device = self.device, None
        if device:
            pending = device.close()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
