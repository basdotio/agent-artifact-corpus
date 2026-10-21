#!/usr/bin/env python3
"""Unit tests for the SSH/NETCONF ConnectionPool lifecycle.

Focus: reload must drop pooled connections WITHOUT killing the pool's
idle-cleanup thread, while shutdown must stop it.
"""

import asyncio
import sys
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import jmcp
from jnpr.junos.exception import RpcTimeoutError, UnlockError
from tests.test_device_data import get_device


class ConnectionPoolLifecycleTests(unittest.TestCase):
    def setUp(self):
        # Explicit idle_timeout so the test is independent of JMCP_POOL_IDLE_TIMEOUT.
        self.pool = jmcp.ConnectionPool(idle_timeout=300)

    def tearDown(self):
        # Always stop the background cleanup thread after each test.
        self.pool.close_all(shutdown=True)

    def _inject_fake_connection(self, name="R1"):
        fake_device = MagicMock()
        self.pool._connections[name] = {
            "device": fake_device,
            "lock": threading.Lock(),
            "last_used": 1.0,
        }
        return fake_device

    def test_pool_starts_with_running_cleanup_thread(self):
        self.assertTrue(self.pool._running)
        self.assertTrue(self.pool._cleanup_thread.is_alive())

    def test_reload_keeps_cleanup_thread_alive(self):
        # Regression: close_all(shutdown=False) is the reload path. It must NOT
        # disable the idle-cleanup loop (old code set _running=False here, which
        # permanently killed the janitor for the rest of the process's life).
        self.pool.close_all(shutdown=False)
        self.assertTrue(self.pool._running)
        self.assertTrue(self.pool._cleanup_thread.is_alive())

    def test_shutdown_stops_cleanup(self):
        self.pool.close_all(shutdown=True)
        self.assertFalse(self.pool._running)

    def test_reload_closes_connection_but_keeps_entry(self):
        # close_all closes the device but must NOT remove the entry from
        # _connections. Clearing would detach an entry an in-flight borrow holds,
        # orphaning the connection it is about to open. Entry stays, device=None.
        fake_device = self._inject_fake_connection("R1")
        self.pool.close_all(shutdown=False)
        fake_device.close.assert_called_once()
        self.assertIn("R1", self.pool._connections)
        self.assertIsNone(self.pool._connections["R1"]["device"])

    def test_close_all_acquires_per_router_lock(self):
        # Regression: close_all must take each entry's per-router lock before
        # closing it, so an in-flight operation is waited out rather than having
        # its live transport closed mid-RPC.
        fake_device = MagicMock()
        fake_lock = MagicMock()
        self.pool._connections["R1"] = {
            "device": fake_device,
            "lock": fake_lock,
            "last_used": 1.0,
        }
        self.pool.close_all(shutdown=False)
        fake_lock.acquire.assert_called_once()
        fake_lock.release.assert_called_once()
        fake_device.close.assert_called_once()

    @patch("jmcp.Device")
    def test_open_failure_closes_partial_device(self, mock_device_cls):
        # M3: if Device.open() raises (possibly after partially establishing the
        # transport), the local device must be closed so it is not leaked.
        failed_device = MagicMock()
        failed_device.open.side_effect = RuntimeError("open failed")
        mock_device_cls.return_value = failed_device
        orig = jmcp.devices
        jmcp.devices = {"router1": get_device("router1")}
        try:
            with self.assertRaises(RuntimeError):
                with self.pool.get_connection("router1"):
                    pass
        finally:
            jmcp.devices = orig
        failed_device.close.assert_called_once()
        self.assertIsNone(self.pool._connections["router1"]["device"])

    def test_rpc_timeout_evicts_session(self):
        # R2#2: RpcTimeoutError leaves device.connected True, but the poisoned
        # session must be evicted (closed + dropped) so it is not reused.
        dev = MagicMock()
        dev.connected = True
        self.pool._connections["router1"] = {
            "device": dev,
            "lock": threading.Lock(),
            "last_used": 1.0,
        }
        with self.assertRaises(RpcTimeoutError):
            with self.pool.get_connection("router1"):
                raise RpcTimeoutError(dev, None, 1)
        dev.close.assert_called_once()
        self.assertIsNone(self.pool._connections["router1"]["device"])

    def test_cleanup_idle_reaps_aged_connection(self):
        # The idle reaper (previously untested) must close a connection idle past
        # the timeout and drop the device.
        dev = MagicMock()
        dev.connected = True
        self.pool._connections["router1"] = {
            "device": dev,
            "lock": threading.Lock(),
            "last_used": time.time() - 10_000,  # well past idle_timeout=300
        }
        self.pool._cleanup_idle()
        dev.close.assert_called_once()
        self.assertIsNone(self.pool._connections["router1"]["device"])

    def test_last_used_refreshed_after_failed_operation(self):
        # Regression: a borrow whose operation raises but leaves the device
        # connected must still refresh last_used, or idle cleanup (which requires
        # last_used > 0) would never reap that connection.
        dev = MagicMock()
        dev.connected = True
        self.pool._connections["R1"] = {
            "device": dev,
            "lock": threading.Lock(),
            "last_used": 0.0,
        }
        try:
            with self.pool.get_connection("R1"):
                raise RuntimeError("operation failed mid-RPC")
        except RuntimeError:
            pass
        # device still connected -> not evicted, but last_used must be refreshed
        self.assertIs(self.pool._connections["R1"]["device"], dev)
        self.assertGreater(self.pool._connections["R1"]["last_used"], 0)


class LoadCommitLockLeakTests(unittest.TestCase):
    """Regression: a failed commit whose rollback/unlock also fail must not
    leave a still-config-locked session in the pool."""

    def setUp(self):
        self._orig_devices = jmcp.devices.copy()
        jmcp.connection_pool.close_all(shutdown=False)

    def tearDown(self):
        jmcp.devices = self._orig_devices
        jmcp.connection_pool.close_all(shutdown=False)

    @patch("jmcp.check_config_blocklist", return_value=(False, ""))
    @patch("jmcp.Config")
    @patch("jmcp.Device")
    def test_failed_commit_then_unlock_error_evicts_locked_session(
        self, mock_device_cls, mock_config_cls, _mock_blocklist
    ):
        # Device the pool will hand out. close() drops the session, so the pool
        # must not reuse it afterwards.
        mock_device = MagicMock()
        mock_device.connected = True

        def _close():
            mock_device.connected = False

        mock_device.close.side_effect = _close
        mock_device_cls.return_value = mock_device

        # lock() ok, load() ok, diff() truthy, commit() fails, and unlock()
        # raises UnlockError — the REAL failure mode (UnlockError subclasses
        # RpcError, not any of the previously-allowlisted types).
        cfg = MagicMock()
        cfg.diff.return_value = "+ set system host-name x"
        cfg.commit.side_effect = RuntimeError("commit failed")
        cfg.unlock.side_effect = UnlockError(rsp=None)
        mock_config_cls.return_value = cfg

        jmcp.devices = {"router1": get_device("router1")}
        ctx = MagicMock()
        ctx.info = AsyncMock()
        ctx.warning = AsyncMock()
        ctx.error = AsyncMock()

        result = asyncio.run(
            jmcp.handle_load_and_commit_config(
                {
                    "router_name": "router1",
                    "config_text": "set system host-name x",
                    "config_format": "set",
                },
                ctx,
            )
        )

        self.assertIn("Failed to load/commit configuration", result[0].text)
        # Cleanup dropped the transport...
        mock_device.close.assert_called()
        # ...and the pool actually evicts it: the next borrow builds a fresh
        # Device instead of reusing the locked session.
        before = mock_device_cls.call_count
        with jmcp.connection_pool.get_connection("router1"):
            pass
        self.assertGreater(mock_device_cls.call_count, before)


if __name__ == "__main__":
    unittest.main()
