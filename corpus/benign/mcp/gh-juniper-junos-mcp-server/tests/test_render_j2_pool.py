#!/usr/bin/env python3
"""Unit tests for the pooled render_and_apply_j2_template apply path.

Focus: the handler must borrow device connections from the ConnectionPool
(keeping the session cached for reuse) and must evict a session whose
exclusive-config unlock failed, instead of returning it to the pool locked.
"""

import asyncio
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import jmcp
from jnpr.junos.exception import UnlockError
from tests.test_device_data import get_device

TEMPLATE = "set system host-name {{ name }}"
VARS = "name: foo"


def _make_context():
    ctx = MagicMock()
    ctx.info = AsyncMock()
    ctx.debug = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.error = AsyncMock()
    return ctx


def _apply_args(**overrides):
    args = {
        "template_content": TEMPLATE,
        "vars_content": VARS,
        "router_name": "router1",
        "apply_config": True,
    }
    args.update(overrides)
    return args


class RenderJ2PoolTests(unittest.TestCase):
    def setUp(self):
        self._orig_devices = jmcp.devices.copy()
        jmcp.devices = {"router1": get_device("router1")}
        # connection_pool is a module-level singleton; drop any connection a
        # previous test cached so each test gets its own freshly-mocked device.
        jmcp.connection_pool.close_all(shutdown=False)

    def tearDown(self):
        jmcp.devices = self._orig_devices
        jmcp.connection_pool.close_all(shutdown=False)

    @patch("jmcp.Config")
    @patch("jmcp.Device")
    def test_apply_borrows_from_pool_and_keeps_session(
        self, mock_device_cls, mock_config_cls
    ):
        mock_device = MagicMock()
        mock_device.connected = True
        mock_device_cls.return_value = mock_device

        cu = MagicMock()
        cu.diff.return_value = "+ set system host-name foo"
        cu.commit_check.return_value = True
        cfg_cm = MagicMock()
        cfg_cm.__enter__.return_value = cu
        cfg_cm.__exit__.return_value = False
        mock_config_cls.return_value = cfg_cm

        result = asyncio.run(
            jmcp.handle_render_and_apply_j2_template(_apply_args(), _make_context())
        )

        self.assertIn(
            "✅ router1: Configuration committed successfully", result[0].text
        )
        cu.commit.assert_called_once()
        # The session came from the pool and stays cached for reuse.
        self.assertIs(
            jmcp.connection_pool._connections["router1"]["device"], mock_device
        )
        mock_device.close.assert_not_called()

    @patch("jmcp.Config")
    @patch("jmcp.Device")
    def test_unlock_failure_evicts_session(self, mock_device_cls, mock_config_cls):
        # commit fails AND Config.__exit__'s unlock raises UnlockError: the
        # session may still hold the exclusive config lock, so the handler must
        # drop the transport and the pool must evict it — not hand the locked
        # session to the next borrower.
        mock_device = MagicMock()
        mock_device.connected = True

        def _close():
            mock_device.connected = False

        mock_device.close.side_effect = _close
        mock_device_cls.return_value = mock_device

        cu = MagicMock()
        cu.diff.return_value = "+ set system host-name foo"
        cu.commit_check.return_value = True
        cu.commit.side_effect = RuntimeError("commit failed")
        cfg_cm = MagicMock()
        cfg_cm.__enter__.return_value = cu
        cfg_cm.__exit__.side_effect = UnlockError(rsp=None)
        mock_config_cls.return_value = cfg_cm

        result = asyncio.run(
            jmcp.handle_render_and_apply_j2_template(_apply_args(), _make_context())
        )

        self.assertIn("❌ router1: Failed to apply configuration", result[0].text)
        mock_device.close.assert_called()
        self.assertIsNone(jmcp.connection_pool._connections["router1"]["device"])

    @patch("jmcp.Config")
    @patch("jmcp.Device")
    def test_dry_run_rolls_back_and_keeps_session(
        self, mock_device_cls, mock_config_cls
    ):
        mock_device = MagicMock()
        mock_device.connected = True
        mock_device_cls.return_value = mock_device

        cu = MagicMock()
        # First diff shows pending changes; diff after rollback shows none.
        cu.diff.side_effect = ["+ set system host-name foo", None]
        cu.commit_check.return_value = True
        cfg_cm = MagicMock()
        cfg_cm.__enter__.return_value = cu
        cfg_cm.__exit__.return_value = False
        mock_config_cls.return_value = cfg_cm

        result = asyncio.run(
            jmcp.handle_render_and_apply_j2_template(
                _apply_args(dry_run=True), _make_context()
            )
        )

        self.assertIn("🔍 router1: Configuration check successful", result[0].text)
        cu.rollback.assert_called_once()
        cu.commit.assert_not_called()
        self.assertIs(
            jmcp.connection_pool._connections["router1"]["device"], mock_device
        )


if __name__ == "__main__":
    unittest.main()
