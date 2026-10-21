#!/usr/bin/env python3
"""Tests for gpu_preflight.py (pack-shared, localops; generated into every GPU member).

Run: python -m unittest discover -s scripts -p "test_*.py"
Stdlib only. Every machine reading is patched: no server, registry, perf counter or GPU is touched.
"""
import json
import shutil
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gpu_preflight as gp  # noqa: E402

GIB = gp.GIB


class Base(unittest.TestCase):
    def setUp(self):
        self.state = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.state, True)
        patches = {
            "state_dir": lambda: self.state,
            "lmstudio": lambda: {"reachable": True, "loaded": []},
            "comfyui": lambda port: {"reachable": False},
            "vram_total_registry": lambda: 16 * GIB,
            "dedicated_usage": lambda: 1 * GIB,
            "commit_charge": lambda: (10 * GIB, 64 * GIB),
            "estimate": lambda m, c, g: {"source": "fixture", "gpu_bytes": 4 * GIB, "total_bytes": 6 * GIB},
        }
        for name, fn in patches.items():
            p = mock.patch.object(gp, name, side_effect=fn)
            p.start()
            self.addCleanup(p.stop)
        (self.state / "gpu-config.json").write_text(json.dumps(
            {"headroom_bytes": GIB, "commit_headroom_bytes": 4 * GIB}), encoding="utf-8")

    def args(self, **kw):
        base = dict(model="some-model", context_length=8192, gpu=None, mode="interactive",
                    holder="lmstudiorunner", comfy_port=8188)
        base.update(kw)
        return Namespace(**base)

    def lease(self, holder: str, minutes: float, **extra):
        t = datetime.now(timezone.utc)
        body = {"holder": holder, "purpose": "fixture", "started": t.isoformat(),
                "expires": (t + timedelta(minutes=minutes)).isoformat()}
        body.update(extra)
        (self.state / "gpu-lease.json").write_text(json.dumps(body), encoding="utf-8")


class Verdicts(Base):
    def test_free_card_goes_and_prints_lease_fields(self):
        v = gp.verdict(self.args())
        self.assertEqual(v["verdict"], "go", v["reasons"])
        self.assertEqual(v["flags"], [])
        self.assertEqual(v["lease_fields"], {"est_vram_bytes": 4 * GIB, "est_ram_bytes": 2 * GIB})

    def test_lease_held_by_another_holder_is_gpu_busy_and_names_ram(self):
        self.lease("comfyrunner", 30, est_ram_bytes=8 * GIB)
        v = gp.verdict(self.args())
        self.assertEqual(v["verdict"], "refuse")
        self.assertEqual(v["flags"], ["GPU-BUSY"])
        self.assertIn(str(8 * GIB), v["reasons"][0])

    def test_lease_without_ram_estimate_says_unknown(self):
        self.lease("whisperrunner", 30)
        v = gp.verdict(self.args())
        self.assertIn("est_ram_bytes unknown", v["reasons"][0])

    def test_busy_comfyui_is_gpu_busy_once(self):
        self.lease("obsrunner", 30, est_ram_bytes=GIB)
        with mock.patch.object(gp, "comfyui", return_value={"reachable": True, "running": 1, "pending": 0,
                                                             "vram_total": 16 * GIB, "vram_free": 2 * GIB}):
            v = gp.verdict(self.args())
        self.assertEqual(v["verdict"], "refuse")
        self.assertEqual(v["flags"], ["GPU-BUSY"])

    def test_over_budget_reduces_without_busy_flag(self):
        with mock.patch.object(gp, "estimate", return_value={"source": "fixture", "gpu_bytes": 15 * GIB,
                                                              "total_bytes": 15 * GIB}):
            v = gp.verdict(self.args())
        self.assertEqual(v["verdict"], "reduce")
        self.assertEqual(v["flags"], [])

    def test_occupancy_read_without_model_has_no_lease_fields(self):
        v = gp.verdict(self.args(model=None))
        self.assertIsNone(v["lease_fields"])

    def test_selftest_passes(self):
        with mock.patch("builtins.print"):
            self.assertEqual(gp.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
