"""Run upstream's synthetic compositing behavior through the unified suite."""
from pathlib import Path
import runpy
import unittest


class CompositeRegression(unittest.TestCase):
    def test_depth_foreground_preserves_source_background(self):
        runpy.run_path(str(Path(__file__).resolve().parents[1] / 'assets' / 'workflow' / 'test_composite.py'))
